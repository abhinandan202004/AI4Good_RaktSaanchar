"""
NotificationService
-------------------
Creates in-app notifications and provides broadcast helpers.
Used by blood_bank and coordinator modules to send alerts.
"""
import math
from typing import Optional

from sqlalchemy.orm import Session

from app.modules.notifications.models import Notification, NotificationType
from app.modules.donors.models import Donor, BloodGroup
from app.modules.users.models import User, UserRole
from app.core.sns_service import SnsService

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

def _haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


class NotificationService:
    def __init__(self, db: Session):
        self.db = db

    # ── Core ──────────────────────────────────────────────────────────────────

    def create(
        self,
        user_id: int,
        title: str,
        body: str,
        notif_type: NotificationType = NotificationType.system,
    ) -> Notification:
        notif = Notification(
            user_id=user_id,
            title=title,
            body=body,
            type=notif_type,
        )
        self.db.add(notif)
        self.db.commit()
        self.db.refresh(notif)
        return notif

    def send_to_user(
        self,
        user_id: int,
        title: str,
        body: str,
        notif_type: NotificationType = NotificationType.system,
    ) -> Notification:
        return self.create(user_id, title, body, notif_type)

    # ── Broadcast helpers ────────────────────────────────────────────────────

    def broadcast_to_donors(
        self,
        blood_group: BloodGroup,
        title: str,
        body: str,
    ) -> int:
        """Send notification to all available/eligible donors of a given blood group. Returns count."""
        from datetime import datetime, timedelta, timezone
        from sqlalchemy import or_
        cooldown_limit = datetime.now(timezone.utc) - timedelta(days=90)
        donors = (
            self.db.query(Donor)
            .filter(
                Donor.blood_group == blood_group,
                Donor.is_available == True,
                or_(
                    Donor.last_donated_at == None,
                    Donor.last_donated_at <= cooldown_limit
                )
            )
            .all()
        )
        for donor in donors:
            self.create(donor.user_id, title, body, NotificationType.alert)
        return len(donors)

    def broadcast_to_all_donors(self, title: str, body: str) -> int:
        """Send to all available/eligible donors regardless of blood group."""
        from datetime import datetime, timedelta, timezone
        from sqlalchemy import or_
        cooldown_limit = datetime.now(timezone.utc) - timedelta(days=90)
        donors = (
            self.db.query(Donor)
            .filter(
                Donor.is_available == True,
                or_(
                    Donor.last_donated_at == None,
                    Donor.last_donated_at <= cooldown_limit
                )
            )
            .all()
        )
        for donor in donors:
            self.create(donor.user_id, title, body, NotificationType.alert)
        return len(donors)

    # ── Request lifecycle events ─────────────────────────────────────────────

    def notify_request_created(self, request):
        # 1. Notify the patient
        patient_user_id = None
        if request.patient and request.patient.user:
            patient_user_id = request.patient.user.id
        else:
            from app.modules.patients.models import Patient
            patient = self.db.query(Patient).filter(Patient.id == request.patient_id).first()
            if patient:
                patient_user_id = patient.user_id

        if patient_user_id:
            self.send_to_user(
                patient_user_id,
                "🩸 Request Submitted",
                "Your blood request has been submitted and we are finding a donor.",
                NotificationType.request,
            )

        blood_group = request.blood_group
        urgency = request.urgency
        units = request.units_required
        
        # Get patient details
        patient_lat = None
        patient_lon = None
        patient_city = None
        hospital = "Local Hospital"
        
        if request.patient:
            patient_lat = request.patient.latitude
            patient_lon = request.patient.longitude
            patient_city = request.patient.city
            hospital = request.patient.hospital_name or "Local Hospital"
        else:
            from app.modules.patients.models import Patient
            patient = self.db.query(Patient).filter(Patient.id == request.patient_id).first()
            if patient:
                patient_lat = patient.latitude
                patient_lon = patient.longitude
                patient_city = patient.city
                hospital = patient.hospital_name or "Local Hospital"

        # Resolve compatible donor blood groups
        compatible_groups = _COMPATIBLE_REVERSE.get(blood_group.value, [blood_group.value])

        # Routing decision based on Urgency
        is_urgent = urgency.lower() in ("high", "critical")

        # Notify Coordinators (invoked for all requests)
        coord_title = f"📢 New Request Created: #{request.id} ({blood_group.value})"
        coord_body = f"A new request for {units} unit(s) of {blood_group.value} has been created at {hospital} ({urgency.upper()} Urgency)."
        
        # Email & SMS templates for Coordinator
        coord_email_subject = f"RaktSaanchar: New Request Created #{request.id} ({blood_group.value})"
        coord_email_body = (
            f"Dear Coordinator/Admin,\n\n"
            f"A new blood request has been submitted to the system.\n\n"
            f"Request Details:\n"
            f"  - Request ID: #{request.id}\n"
            f"  - Blood Group Required: {blood_group.value}\n"
            f"  - Units Required: {units}\n"
            f"  - Urgency Level: {urgency.upper()}\n"
            f"  - Location/Hospital: {hospital}\n"
            f"  - City: {patient_city}\n\n"
            f"The system has automatically calculated the top matching donors and initiated notifications. "
            f"Please log in to the Coordinator Dashboard to review the matches and manage the dispatch status.\n\n"
            f"Best regards,\n"
            f"RaktSaanchar System"
        )
        coord_sms_message = f"RaktSaanchar: New request #{request.id} ({blood_group.value}) created at {hospital} ({urgency.upper()} Urgency)."

        coordinators = (
            self.db.query(User)
            .filter(User.role.in_([UserRole.coordinator, UserRole.admin]))
            .all()
        )
        for c in coordinators:
            self.create(c.id, coord_title, coord_body, NotificationType.alert)
            SnsService.send_sns_notification(
                phone=c.phone,
                email=c.email,
                subject=coord_email_subject,
                message=coord_body,
                sms_message=coord_sms_message,
                email_body=coord_email_body
            )

        # 2. ALWAYS rank compatible donors using the ML model and notify them
        from app.modules.ml import service as ml_service
        ranked_donors = ml_service.rank_donors(
            db=self.db,
            patient_blood_group=blood_group.value,
            urgency=urgency,
            units_required=units,
            patient_city=patient_city,
            patient_latitude=patient_lat,
            patient_longitude=patient_lon,
            limit=10,
        )
        
        if is_urgent:
            donor_title = f"🚨 URGENT Blood Request: {blood_group.value}"
            donor_body = f"An urgent request for {units} unit(s) of {blood_group.value} has been created at {hospital}."
            donor_email_subject = f"RaktSaanchar: URGENT Blood Request Match ({blood_group.value})"
            donor_email_body = (
                f"Dear Donor,\n\n"
                f"There is an URGENT blood request match in your area.\n\n"
                f"Request Details:\n"
                f"  - Blood Group Required: {blood_group.value}\n"
                f"  - Units Required: {units}\n"
                f"  - Urgency Level: {urgency.upper()}\n"
                f"  - Location/Hospital: {hospital}\n\n"
                f"You have been ranked as one of our top matched candidates. "
                f"Please open the RaktSaanchar application immediately to accept this request and coordinate donation details.\n\n"
                f"Your quick response can save a life!\n\n"
                f"Best regards,\n"
                f"The RaktSaanchar Team"
            )
            donor_sms_message = f"RaktSaanchar: URGENT {blood_group.value} request at {hospital}. Open app to accept!"
        else:
            donor_title = f"📅 Donation Match Opportunity: {blood_group.value}"
            donor_body = f"{units} unit(s) of {blood_group.value} requested at {hospital}. You are matched as a top candidate. Open app to schedule!"
            donor_email_subject = f"RaktSaanchar: Blood Donation Match Opportunity ({blood_group.value})"
            donor_email_body = (
                f"Dear Donor,\n\n"
                f"A new blood donation opportunity matching your profile has been created.\n\n"
                f"Request Details:\n"
                f"  - Blood Group Required: {blood_group.value}\n"
                f"  - Units Required: {units}\n"
                f"  - Urgency Level: {urgency.upper()}\n"
                f"  - Location/Hospital: {hospital}\n\n"
                f"Please open the RaktSaanchar application to review the request and schedule a donation.\n\n"
                f"Thank you for your continued support in helping save lives.\n\n"
                f"Best regards,\n"
                f"The RaktSaanchar Team"
            )
            donor_sms_message = f"RaktSaanchar: {units} unit(s) of {blood_group.value} requested at {hospital}. You are matched as a top candidate. Open app to schedule!"
        
        for rd in ranked_donors:
            if rd["blood_group"] not in compatible_groups:
                continue
            in_range = True
            donor_user = self.db.query(User).filter(User.id == rd["user_id"]).first()
            if is_urgent and donor_user and donor_user.donor_profile:
                d = donor_user.donor_profile
                if patient_lat is not None and patient_lon is not None and d.latitude is not None and d.longitude is not None:
                    dist = _haversine_distance(patient_lat, patient_lon, d.latitude, d.longitude)
                    if dist > 100.0:
                        in_range = False
                elif patient_city and d.city and patient_city.strip().lower() != d.city.strip().lower():
                    in_range = False

            if in_range:
                self.create(rd["user_id"], donor_title, donor_body, NotificationType.request)
                if donor_user:
                    SnsService.send_sns_notification(
                        phone=donor_user.phone,
                        email=donor_user.email,
                        subject=donor_email_subject,
                        message=donor_body,
                        sms_message=donor_sms_message,
                        email_body=donor_email_body
                    )

        # 3. Handle Blood Bank notifications
        if is_urgent:
            # Urgent: Alert blood banks within 100 Km
            from app.modules.blood_bank.models import BloodBankProfile
            banks = self.db.query(BloodBankProfile).all()
            
            bank_email_subject = f"RaktSaanchar: URGENT Blood Bank Alert ({blood_group.value})"
            bank_email_body = (
                f"Dear Blood Bank Administrator,\n\n"
                f"An URGENT blood request has been created within your operating radius (100 Km).\n\n"
                f"Request Details:\n"
                f"  - Request ID: #{request.id}\n"
                f"  - Blood Group Required: {blood_group.value}\n"
                f"  - Units Required: {units}\n"
                f"  - Urgency Level: {urgency.upper()}\n"
                f"  - Location/Hospital: {hospital}\n\n"
                f"Please check your current inventory and coordinate if you can supply compatible units. "
                f"Log in to your Dashboard to accept and manage this request.\n\n"
                f"Best regards,\n"
                f"The RaktSaanchar Team"
            )
            bank_sms_message = f"RaktSaanchar: Urgent request for {blood_group.value} at {hospital} within your area. Open app to view."

            for b in banks:
                in_range = False
                if patient_lat is not None and patient_lon is not None and b.latitude is not None and b.longitude is not None:
                    dist = _haversine_distance(patient_lat, patient_lon, b.latitude, b.longitude)
                    if dist <= 100.0:
                        in_range = True
                elif patient_city and b.address and patient_city.strip().lower() in b.address.strip().lower():
                    in_range = True

                if in_range:
                    bank_title = f"🚨 URGENT Blood Bank Alert: {blood_group.value} Requested"
                    self.create(b.user_id, bank_title, donor_body, NotificationType.alert)
                    # Dispatch via Amazon SNS
                    bank_user = self.db.query(User).filter(User.id == b.user_id).first()
                    if bank_user:
                        SnsService.send_sns_notification(
                            phone=bank_user.phone,
                            email=bank_user.email,
                            subject=bank_email_subject,
                            message=donor_body,
                            sms_message=bank_sms_message,
                            email_body=bank_email_body
                        )
        else:
            # Non-urgent: Check blood bank inventories within 100 Km first
            from app.modules.blood_bank.models import BloodBankProfile, BloodInventory
            
            # Find blood banks within 100 Km
            banks = self.db.query(BloodBankProfile).all()
            nearby_bank_ids = []
            for b in banks:
                if patient_lat is not None and patient_lon is not None and b.latitude is not None and b.longitude is not None:
                    if _haversine_distance(patient_lat, patient_lon, b.latitude, b.longitude) <= 100.0:
                        nearby_bank_ids.append(b.user_id)
                elif patient_city and b.address and patient_city.strip().lower() in b.address.strip().lower():
                    nearby_bank_ids.append(b.user_id)

            # Check inventory for compatible blood groups in these nearby banks
            if nearby_bank_ids:
                matching_inventory = (
                    self.db.query(BloodInventory)
                    .filter(
                        BloodInventory.blood_bank_id.in_(nearby_bank_ids),
                        BloodInventory.blood_group.in_(compatible_groups),
                        BloodInventory.quantity_ml >= 450.0,
                    )
                    .first()
                )
                
                if matching_inventory:
                    # Notify the patient that compatible blood is available at a nearby blood bank
                    self.send_to_user(
                        patient_user_id,
                        "🏥 Blood Available at Blood Bank",
                        f"Compatible blood is available at {matching_inventory.blood_bank.blood_bank_profile.hospital_name if hasattr(matching_inventory.blood_bank, 'blood_bank_profile') and matching_inventory.blood_bank.blood_bank_profile else 'a nearby blood bank'}. Please visit to coordinate.",
                        NotificationType.request,
                    )
                    # Notify the blood bank
                    bank_title = "📢 Matching Request in Your Area"
                    bank_body = f"A request for {units} unit(s) of {blood_group.value} has been created at {hospital}. You have compatible stock available."
                    self.send_to_user(
                        matching_inventory.blood_bank_id,
                        bank_title,
                        bank_body,
                        NotificationType.alert,
                    )
                    
                    bank_email_subject = f"RaktSaanchar: Matching Blood Request in Your Area ({blood_group.value})"
                    bank_email_body = (
                        f"Dear Blood Bank Administrator,\n\n"
                        f"A new blood request has been submitted in your area. Our system indicates you have compatible stock available ({blood_group.value}).\n\n"
                        f"Request Details:\n"
                        f"  - Request ID: #{request.id}\n"
                        f"  - Blood Group Required: {blood_group.value}\n"
                        f"  - Units Required: {units}\n"
                        f"  - Urgency Level: {urgency.upper()}\n"
                        f"  - Location/Hospital: {hospital}\n\n"
                        f"Please review your dashboard and prepare the dispatch if accepted.\n\n"
                        f"Best regards,\n"
                        f"The RaktSaanchar Team"
                    )
                    bank_sms_message = f"RaktSaanchar: Compatible stock found for request at {hospital}. Open dashboard to review."

                    # Dispatch via Amazon SNS
                    bank_user = self.db.query(User).filter(User.id == matching_inventory.blood_bank_id).first()
                    if bank_user:
                        SnsService.send_sns_notification(
                            phone=bank_user.phone,
                            email=bank_user.email,
                            subject=bank_email_subject,
                            message=bank_body,
                            sms_message=bank_sms_message,
                            email_body=bank_email_body
                        )

    def notify_request_matched(self, donor_user_id: int, patient_user_id: int):
        self.send_to_user(
            donor_user_id,
            "✅ Match Found",
            "You have been matched to a blood request. Please accept or decline.",
            NotificationType.request,
        )
        self.send_to_user(
            patient_user_id,
            "🔍 Donor Found",
            "A donor has been matched to your request. Waiting for acceptance.",
            NotificationType.request,
        )

    def notify_request_accepted(self, patient_user_id: int, donor_user_id: int):
        self.send_to_user(
            patient_user_id,
            "💚 Donor Accepted",
            "Your matched donor has accepted the request!",
            NotificationType.request,
        )
        self.send_to_user(
            donor_user_id,
            "💚 Request Confirmed",
            "You have accepted the blood donation request. Please report to the hospital.",
            NotificationType.request,
        )

    def notify_request_fulfilled(self, patient_user_id: int, donor_user_id: int):
        self.send_to_user(
            patient_user_id,
            "🎉 Request Fulfilled",
            "Your blood request has been fulfilled. Thank you!",
            NotificationType.request,
        )
        self.send_to_user(
            donor_user_id,
            "🏅 Donation Complete",
            "Your donation has been marked complete. You are a hero!",
            NotificationType.badge,
        )

    def notify_request_escalated(self, coordinator_user_id: int, request_id: int):
        self.send_to_user(
            coordinator_user_id,
            "🚨 Request Escalated",
            f"Blood request #{request_id} has been escalated and needs immediate attention.",
            NotificationType.alert,
        )

    def notify_badge_awarded(self, donor_user_id: int, badge_name: str, icon: str = "🏅"):
        self.send_to_user(
            donor_user_id,
            f"{icon} Badge Earned: {badge_name}",
            f"Congratulations! You've earned the '{badge_name}' badge. Keep donating!",
            NotificationType.badge,
        )

    def notify_validation_report(self, donor_user_id: int, status: str, issue_category: Optional[str] = None):
        if status == "approved":
            self.send_to_user(
                donor_user_id,
                "🎉 Donation Lab Report: All Clear!",
                "Your donation has passed all lab tests and is safe for clinical use. Thank you!",
                NotificationType.alert,
            )
        else:
            issue_msg = issue_category.replace("_", " ").title() if issue_category else "health criteria"
            self.send_to_user(
                donor_user_id,
                "🩸 Donation Report & Action Items",
                f"Your recent donation report noted some health issues ({issue_msg}). Check recommendations to improve your eligibility.",
                NotificationType.alert,
            )
