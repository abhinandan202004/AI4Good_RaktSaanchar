from sqlalchemy.orm import Session
from fastapi.encoders import jsonable_encoder
from app.modules.donors.repository import DonorRepository
from app.modules.donors.service import DonorService
from app.modules.patients.repository import PatientRepository
from app.modules.patients.service import PatientService
from app.modules.blood_requests.repository import BloodRequestRepository
from app.modules.blood_requests.service import BloodRequestService
from app.modules.blood_bank.repository import BloodBankRepository
from app.modules.blood_bank.service import BloodBankService
from app.modules.blood_bank.models import BloodBankProfile
from app.modules.notifications.service import NotificationService
from app.modules.coordinator.service import CoordinatorService
import logging

logger = logging.getLogger(__name__)

class PlatformAdapter:

    @staticmethod
    def get_donor_profile(db: Session, user_id: int):
        try:
            donor_svc = DonorService(DonorRepository(db))
            profile = donor_svc.get_my_profile(user_id)
            return jsonable_encoder(profile)
        except Exception as e:
            logger.warning("Error fetching donor profile: %s", e)
            return {"error": "Donor profile not found."}

    @staticmethod
    def get_donor_leaderboard(db: Session):
        try:
            donor_svc = DonorService(DonorRepository(db))
            leaderboard = donor_svc.leaderboard(limit=10)
            return jsonable_encoder(leaderboard)
        except Exception as e:
            logger.warning("Error fetching leaderboard: %s", e)
            return {"error": "Could not retrieve leaderboard."}

    @staticmethod
    def get_validation_reports(db: Session, user_id: int):
        try:
            bank_svc = BloodBankService(BloodBankRepository(db), NotificationService(db))
            reports = bank_svc.get_donor_reports(user_id)
            return jsonable_encoder(reports)
        except Exception as e:
            logger.warning("Error fetching validation reports: %s", e)
            return {"error": "Could not retrieve validation reports."}

    @staticmethod
    def get_patient_profile(db: Session, user_id: int):
        try:
            patient_svc = PatientService(PatientRepository(db))
            profile = patient_svc.get_my_profile(user_id)
            return jsonable_encoder(profile)
        except Exception as e:
            logger.warning("Error fetching patient profile: %s", e)
            return {"error": "Patient profile not found."}

    @staticmethod
    def get_my_requests(db: Session, user_id: int):
        try:
            donor_repo = DonorRepository(db)
            req_svc = BloodRequestService(db, BloodRequestRepository(db), donor_repo)
            requests = req_svc.get_my_requests(user_id)
            return jsonable_encoder(requests)
        except Exception as e:
            logger.warning("Error fetching my requests: %s", e)
            return {"error": "Could not retrieve requests."}

    @staticmethod
    def get_notifications(db: Session, user_id: int):
        try:
            notif_svc = NotificationService(db)
            notifications = notif_svc.get_notifications(user_id)
            return jsonable_encoder(notifications)
        except Exception as e:
            logger.warning("Error fetching notifications: %s", e)
            return {"error": "Could not retrieve notifications."}

    @staticmethod
    def get_inventory(db: Session, user_id: int, user_role: str):
        try:
            bank_svc = BloodBankService(BloodBankRepository(db), NotificationService(db))
            if user_role == "blood_bank":
                profile = bank_svc.get_profile(user_id)
                inventory = bank_svc.get_inventory(profile.id)
            else:
                inventory = bank_svc.get_all_inventory()
            return jsonable_encoder(inventory)
        except Exception as e:
            logger.warning("Error fetching inventory: %s", e)
            return {"error": "Could not retrieve inventory."}

    @staticmethod
    def get_nearest_blood_banks(db: Session, user_id: int):
        try:
            bank_svc = BloodBankService(BloodBankRepository(db), NotificationService(db))
            lat, lon = None, None
            
            # Try to get donor coordinates
            donor = DonorRepository(db).get_by_user_id(user_id)
            if donor and donor.latitude is not None:
                lat, lon = donor.latitude, donor.longitude
            else:
                # Try patient coordinates
                patient = PatientRepository(db).get_by_user_id(user_id)
                if patient and patient.latitude is not None:
                    lat, lon = patient.latitude, patient.longitude

            if lat is not None and lon is not None:
                nearest = bank_svc.get_nearest_blood_banks(lat, lon, limit=5)
                return jsonable_encoder(nearest)
            else:
                # Fallback: get all profiles
                profiles = db.query(BloodBankProfile).all()
                return [{"hospital_name": p.hospital_name, "city": p.city, "address": p.address} for p in profiles]
        except Exception as e:
            logger.warning("Error fetching nearest blood banks: %s", e)
            return {"error": "Could not retrieve nearest blood banks."}

    @staticmethod
    def get_dashboard(db: Session):
        try:
            coord_svc = CoordinatorService(db, NotificationService(db))
            dashboard = coord_svc.get_dashboard()
            return jsonable_encoder(dashboard)
        except Exception as e:
            logger.warning("Error fetching coordinator dashboard: %s", e)
            return {"error": "Could not retrieve dashboard statistics."}

    @staticmethod
    def get_active_requests(db: Session):
        try:
            coord_svc = CoordinatorService(db, NotificationService(db))
            active = coord_svc.get_active_requests()
            return jsonable_encoder(active)
        except Exception as e:
            logger.warning("Error fetching active requests: %s", e)
            return {"error": "Could not retrieve active requests."}
