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
        """Send notification to all available donors of a given blood group. Returns count."""
        donors = (
            self.db.query(Donor)
            .filter(
                Donor.blood_group == blood_group,
                Donor.is_available == True,
            )
            .all()
        )
        for donor in donors:
            self.create(donor.user_id, title, body, NotificationType.alert)
        return len(donors)

    def broadcast_to_all_donors(self, title: str, body: str) -> int:
        """Send to all available donors regardless of blood group."""
        donors = self.db.query(Donor).filter(Donor.is_available == True).all()
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

        if is_urgent:
            # URGENT: Broadcast to compatible available donors & blood banks within 100 Km radius
            title = f"🚨 URGENT: {blood_group.value} Needed!"
            body = f"URGENT: {units} unit(s) of {blood_group.value} requested at {hospital} ({urgency.upper()} Urgency). Accept now!"

            # 1. Alert compatible donors within 100 Km
            donors = (
                self.db.query(Donor)
                .filter(
                    Donor.blood_group.in_(compatible_groups),
                    Donor.is_available == True,
                )
                .all()
            )
            for d in donors:
                # Calculate distance
                in_range = False
                if patient_lat is not None and patient_lon is not None and d.latitude is not None and d.longitude is not None:
                    dist = _haversine_distance(patient_lat, patient_lon, d.latitude, d.longitude)
                    if dist <= 100.0:
                        in_range = True
                elif patient_city and d.city and patient_city.strip().lower() == d.city.strip().lower():
                    # Fallback to city
                    in_range = True
                
                if in_range:
                    self.create(d.user_id, title, body, NotificationType.alert)

            # 2. Alert blood banks within 100 Km
            from app.modules.blood_bank.models import BloodBankProfile
            banks = self.db.query(BloodBankProfile).all()
            for b in banks:
                in_range = False
                if patient_lat is not None and patient_lon is not None and b.latitude is not None and b.longitude is not None:
                    dist = _haversine_distance(patient_lat, patient_lon, b.latitude, b.longitude)
                    if dist <= 100.0:
                        in_range = True
                elif patient_city and b.address and patient_city.strip().lower() in b.address.strip().lower():
                    # Fallback
                    in_range = True

                if in_range:
                    self.create(b.user_id, f"🚨 URGENT Blood Bank Alert: {blood_group.value} Requested", body, NotificationType.alert)

        else:
            # NON-URGENT: Check blood bank inventories within 100 Km first
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
            inventory_found = False
            if nearby_bank_ids:
                matching_inventory = (
                    self.db.query(BloodInventory)
                    .filter(
                        BloodInventory.blood_bank_id.in_(nearby_bank_ids),
                        BloodInventory.blood_group.in_(compatible_groups),
                        BloodInventory.quantity_ml >= 450.0,  # at least 1 unit (450ml)
                    )
                    .first()
                )
                if matching_inventory:
                    inventory_found = True
                    # Notify the patient that blood is available at a nearby blood bank
                    self.send_to_user(
                        patient_user_id,
                        "🏥 Blood Available at Blood Bank",
                        f"Compatible blood is available at {matching_inventory.blood_bank.blood_bank_profile.hospital_name if hasattr(matching_inventory.blood_bank, 'blood_bank_profile') and matching_inventory.blood_bank.blood_bank_profile else 'a nearby blood bank'}. Please visit to coordinate.",
                        NotificationType.request,
                    )
                    # Notify the blood bank
                    self.send_to_user(
                        matching_inventory.blood_bank_id,
                        "📢 Matching Request in Your Area",
                        f"A request for {units} unit(s) of {blood_group.value} has been created at {hospital}. You have compatible stock available.",
                        NotificationType.alert,
                    )

            if not inventory_found:
                # Fallback: Find top 20 compatible donors using ML ranker
                from app.modules.ml import service as ml_service
                ranked_donors = ml_service.rank_donors(
                    db=self.db,
                    patient_blood_group=blood_group.value,
                    urgency=urgency,
                    units_required=units,
                    patient_city=patient_city,
                    patient_latitude=patient_lat,
                    patient_longitude=patient_lon,
                    limit=20,
                )
                
                title = f"📅 Donation Match Opportunity: {blood_group.value}"
                body = f"{units} unit(s) of {blood_group.value} requested at {hospital}. You are matched as a top candidate. Open app to schedule!"
                
                for rd in ranked_donors:
                    self.create(rd["user_id"], title, body, NotificationType.request)

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
