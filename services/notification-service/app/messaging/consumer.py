"""
RabbitMQ Consumer — notification-service
Listens to all platform events and dispatches email + push notifications.
"""
import json
import logging
import math
from typing import Optional

import aio_pika

from app.core.config import settings
from app.notifier import Notifier
from app.push_service import PushService

logger = logging.getLogger(__name__)
EXCHANGE_NAME = "raktsaanchar"

_COMPATIBLE_REVERSE = {
    "O-":  ["O-"],
    "O+":  ["O-", "O+"],
    "A-":  ["O-", "A-"],
    "A+":  ["O-", "O+", "A-", "A+"],
    "B-":  ["O-", "B-"],
    "B+":  ["O-", "O+", "B-", "B+"],
    "AB-": ["O-", "A-", "B-", "AB-"],
    "AB+": ["O-", "O+", "A-", "A+", "B-", "B+", "AB-", "AB+"],
}


def _haversine(lat1, lon1, lat2, lon2) -> float:
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _get_core_db():
    from app.core.database import CoreSessionLocal
    return CoreSessionLocal()


def _get_notif_db():
    from app.core.database import SessionLocal
    return SessionLocal()


def _create_notification(db, user_id: int, title: str, body: str, notif_type: str = "system"):
    from app.modules.notifications.models import Notification, NotificationType
    try:
        nt = NotificationType(notif_type)
    except ValueError:
        nt = NotificationType.system
    notif = Notification(user_id=user_id, title=title, body=body, type=nt)
    db.add(notif)
    db.commit()


async def handle_otp_send(event: dict) -> None:
    """Send OTP email."""
    email = event.get("email", "")
    full_name = event.get("full_name", "User")
    otp_code = event.get("otp_code", "")
    if email and otp_code:
        from app.email_service import EmailService
        EmailService.send_email(
            to=email,
            subject="RaktSaanchar — Your Verification Code",
            body=f"Hello {full_name},\n\nYour verification code is: {otp_code}\n\nExpires in 10 minutes.\n\nRaktSaanchar Team",
        )


async def handle_blood_request_created(event: dict) -> None:
    """
    On new blood request:
    1. Notify patient (in-app + push)
    2. Notify coordinators/admins (in-app + email + push)
    3. Notify pre-ranked donors from ml-service (in-app + email + push)
    4. Handle blood bank notifications (urgent proximity / inventory match)
    """
    blood_group = event.get("blood_group", "")
    urgency = event.get("urgency", "medium")
    units = event.get("units_required", 1)
    patient_user_id = event.get("patient_user_id")
    hospital = event.get("hospital", "Local Hospital")
    patient_city = event.get("patient_city")
    patient_lat = event.get("patient_lat")
    patient_lon = event.get("patient_lon")
    request_id = event.get("request_id")
    top_donors = event.get("top_donors", [])
    is_urgent = urgency.lower() in ("high", "critical")

    notif_db = _get_notif_db()
    core_db = _get_core_db()

    try:
        # 1. Notify patient
        if patient_user_id:
            _create_notification(notif_db, patient_user_id, "🩸 Request Submitted",
                                 "Your blood request has been submitted and we are finding a donor.", "request")
            PushService.send_push(patient_user_id, "🩸 Request Submitted",
                                  "We are finding a matching donor for your blood request.")

        # 2. Notify coordinators
        from sqlalchemy import text
        coordinators = core_db.execute(
            text("SELECT id, email, phone FROM users WHERE role IN ('coordinator','admin') AND is_active = true")
        ).fetchall()

        coord_email_body = (
            f"A new blood request has been submitted.\n\n"
            f"Request ID: #{request_id}\nBlood Group: {blood_group}\n"
            f"Units: {units}\nUrgency: {urgency.upper()}\nHospital: {hospital}\nCity: {patient_city}\n\n"
            f"Log in to the Coordinator Dashboard to manage this request.\n\nRaktSaanchar Team"
        )
        for coord in coordinators:
            _create_notification(notif_db, coord.id,
                                 f"📢 New Request #{request_id} ({blood_group})",
                                 f"New {urgency.upper()} request for {units}u {blood_group} at {hospital}", "alert")
            Notifier.send(
                user_id=coord.id, email=coord.email,
                subject=f"RaktSaanchar: New Request #{request_id} ({blood_group})",
                email_body=coord_email_body,
                push_title=f"📢 New Request #{request_id}",
                push_message=f"{units}u {blood_group} at {hospital} ({urgency.upper()})",
                priority="high" if is_urgent else "default",
            )

        # 3. Notify top donors from ml-service ranking
        compatible_groups = _COMPATIBLE_REVERSE.get(blood_group, [blood_group])
        if is_urgent:
            donor_title = f"🚨 URGENT Blood Request: {blood_group}"
            donor_push_msg = f"Urgent {blood_group} request at {hospital}. Open app NOW to accept!"
            priority = "urgent"
        else:
            donor_title = f"📅 Donation Match: {blood_group}"
            donor_push_msg = f"{units}u {blood_group} requested at {hospital}. You are a top match!"
            priority = "high"

        for donor_info in top_donors:
            if donor_info.get("blood_group") not in compatible_groups:
                continue
            donor_user_id = donor_info.get("user_id")
            if not donor_user_id:
                continue
            # Distance check for urgent
            if is_urgent and patient_lat is not None and patient_lon is not None:
                d_lat = donor_info.get("latitude")
                d_lon = donor_info.get("longitude")
                if d_lat is not None and d_lon is not None:
                    if _haversine(patient_lat, patient_lon, d_lat, d_lon) > 100.0:
                        continue

            _create_notification(notif_db, donor_user_id, donor_title, donor_push_msg, "request")
            donor_row = core_db.execute(
                text("SELECT email FROM users WHERE id = :uid"), {"uid": donor_user_id}
            ).fetchone()
            donor_email = donor_row.email if donor_row else None
            donor_email_body = (
                f"Dear Donor,\n\nA blood donation opportunity matching your profile:\n\n"
                f"Blood Group: {blood_group}\nUnits: {units}\nUrgency: {urgency.upper()}\nHospital: {hospital}\n\n"
                f"Open the RaktSaanchar app to accept.\n\nRaktSaanchar Team"
            )
            Notifier.send(
                user_id=donor_user_id, email=donor_email,
                subject=f"RaktSaanchar: {'URGENT ' if is_urgent else ''}Blood Donation Match ({blood_group})",
                email_body=donor_email_body,
                push_title=donor_title, push_message=donor_push_msg,
                priority=priority,
            )

        # 4. Blood bank notifications handled by core-service directly via events
        #    (kept minimal here — just log)
        logger.info("✅ Processed blood_request.created event for request #%s", request_id)

    except Exception as exc:
        logger.warning("Error handling blood_request.created: %s", exc)
    finally:
        notif_db.close()
        core_db.close()


async def handle_blood_request_matched(event: dict) -> None:
    donor_user_id = event.get("donor_user_id")
    patient_user_id = event.get("patient_user_id")
    db = _get_notif_db()
    try:
        if donor_user_id:
            _create_notification(db, donor_user_id, "✅ Match Found",
                                 "You have been matched to a blood request. Open app to accept or decline.", "request")
            PushService.send_push(donor_user_id, "✅ Match Found", "You have been matched to a blood request!")
        if patient_user_id:
            _create_notification(db, patient_user_id, "🔍 Donor Found",
                                 "A donor has been matched to your request. Waiting for acceptance.", "request")
            PushService.send_push(patient_user_id, "🔍 Donor Found", "A donor has been matched to your request!")
    finally:
        db.close()


async def handle_blood_request_accepted(event: dict) -> None:
    donor_user_id = event.get("donor_user_id")
    patient_user_id = event.get("patient_user_id")
    db = _get_notif_db()
    try:
        if patient_user_id:
            _create_notification(db, patient_user_id, "💚 Donor Accepted",
                                 "Your matched donor has accepted the request!", "request")
            PushService.send_high(patient_user_id, "💚 Donor Accepted!", "Your donor has accepted. Chat now to coordinate!")
        if donor_user_id:
            _create_notification(db, donor_user_id, "💚 Request Confirmed",
                                 "You have accepted the blood donation request. Please report to the hospital.", "request")
            PushService.send_push(donor_user_id, "💚 Request Confirmed", "You accepted. Please report to the hospital!")
    finally:
        db.close()


async def handle_blood_request_fulfilled(event: dict) -> None:
    donor_user_id = event.get("donor_user_id")
    patient_user_id = event.get("patient_user_id")
    db = _get_notif_db()
    try:
        if patient_user_id:
            _create_notification(db, patient_user_id, "🎉 Request Fulfilled",
                                 "Your blood request has been fulfilled. Thank you!", "request")
            PushService.send_push(patient_user_id, "🎉 Request Fulfilled!", "Your blood request has been fulfilled!")
        if donor_user_id:
            _create_notification(db, donor_user_id, "🏅 Donation Complete",
                                 "Your donation has been marked complete. You are a hero!", "badge")
            PushService.send_push(donor_user_id, "🏅 Donation Complete!", "Thank you for your life-saving donation!")
    finally:
        db.close()


async def handle_badge_awarded(event: dict) -> None:
    donor_user_id = event.get("donor_user_id")
    badge_name = event.get("badge_name", "Badge")
    badge_icon = event.get("badge_icon", "🏅")
    if donor_user_id:
        db = _get_notif_db()
        try:
            _create_notification(db, donor_user_id,
                                 f"{badge_icon} Badge Earned: {badge_name}",
                                 f"Congratulations! You earned the '{badge_name}' badge!", "badge")
            PushService.send_push(donor_user_id,
                                  f"{badge_icon} Badge Earned!",
                                  f"You earned: {badge_name}. Keep donating!")
        finally:
            db.close()


async def handle_blood_request_validation_rejected(event: dict) -> None:
    """
    Fired when a blood bank submits a REJECTED validation report.
    Pushes a high-priority notification to the patient to raise a new blood request.
    The now-invalid donor is already excluded from future matching via is_available=False.
    """
    patient_user_id = event.get("patient_user_id")
    request_id = event.get("request_id")
    issue_category = event.get("issue_category")

    if not patient_user_id:
        return

    db = _get_notif_db()
    try:
        detail = f" ({issue_category.replace('_', ' ').title()})" if issue_category else ""
        _create_notification(
            db, patient_user_id,
            "⚠️ Donation Validation Failed",
            f"The blood donated for your request #{request_id} did not pass the lab validation{detail}. "
            f"Please raise a new blood request — a different donor will be matched for you.",
            "request",
        )
        PushService.send_high(
            patient_user_id,
            "⚠️ Donation Validation Failed",
            f"Your blood request #{request_id} needs a new donor. Please open the app and create a new request.",
        )
        logger.info("✅ Notified patient %s of validation_rejected for request #%s", patient_user_id, request_id)
    except Exception as exc:
        logger.warning("Error handling blood_request.validation_rejected: %s", exc)
    finally:
        db.close()


# ── Event routing ─────────────────────────────────────────────────────────────

EVENT_HANDLERS = {
    "otp.send":                          handle_otp_send,
    "blood_request.created":             handle_blood_request_created,
    "blood_request.matched":             handle_blood_request_matched,
    "blood_request.accepted":            handle_blood_request_accepted,
    "blood_request.fulfilled":           handle_blood_request_fulfilled,
    "badge.awarded":                     handle_badge_awarded,
    "blood_request.validation_rejected": handle_blood_request_validation_rejected,
}


async def start_consumer() -> None:
    try:
        connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)
        channel = await connection.channel()
        await channel.set_qos(prefetch_count=5)

        exchange = await channel.declare_exchange(
            EXCHANGE_NAME, aio_pika.ExchangeType.TOPIC, durable=True
        )

        queue = await channel.declare_queue("notification-service.all-events", durable=True)

        # Bind to all relevant routing keys
        for routing_key in EVENT_HANDLERS.keys():
            await queue.bind(exchange, routing_key=routing_key)

        async def on_message(message: aio_pika.IncomingMessage):
            async with message.process():
                try:
                    event = json.loads(message.body.decode())
                    event_type = event.get("event", message.routing_key)
                    handler = EVENT_HANDLERS.get(event_type)
                    if handler:
                        await handler(event)
                    else:
                        logger.debug("No handler for event type: %s", event_type)
                except Exception as exc:
                    logger.warning("Error processing notification event: %s", exc)

        await queue.consume(on_message)
        logger.info("✅ notification-service consumer started, listening to all events")

    except Exception as exc:
        logger.warning("⚠️ notification-service consumer failed: %s", exc)
