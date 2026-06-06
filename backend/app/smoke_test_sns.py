import os
import sys
import json
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import models
from app.modules.users.models import User, UserRole
from app.modules.donors.models import Donor
from app.modules.patients.models import Patient
from app.modules.blood_requests.models import BloodRequest
from app.modules.notifications.models import Notification
from app.modules.chat.models import ChatRoom, ChatMessage
from app.modules.leaderboard.models import Badge, DonorBadge
from app.modules.blood_bank.models import BloodInventory, BloodUnit, BloodValidationReport, BloodBankProfile
from app.core.database import SessionLocal
from app.core.config import settings
from app.core.sns_service import SnsService
from app.modules.notifications.service import NotificationService

# Force SNS Enabled for test run
settings.AWS_SNS_ENABLED = True
settings.AWS_SNS_BUDGET_LIMIT = 0.05  # low budget to trigger cost block
settings.AWS_SNS_ESTIMATED_COST_PER_SMS = 0.02

# Create database tables for local running (especially with SQLite)
from app.core.database import Base, engine
from app.modules.notifications.models import Notification
from app.modules.blood_bank.models import BloodInventory
Base.metadata.create_all(bind=engine)

# Clear tracker
SnsService.reset_tracker()

db = SessionLocal()
try:
    print("================================================================================")
    print(" 1. RESET AND SETUP MOCK USERS & PROFILES")
    print("================================================================================")
    # Clear existing requests, donors, banks, and coordinators for a clean test env
    db.query(BloodRequest).delete()
    db.query(Donor).delete()
    db.query(BloodBankProfile).delete()
    db.query(Patient).delete()
    db.query(User).delete()
    db.commit()

    # Create Patient, Donor, Blood Bank, and Coordinator
    patient_user = User(email="patient_sns@test.com", phone="+1111111111", hashed_password="pw", full_name="Patient SNS", role=UserRole.patient)
    donor_user = User(email="donor_sns@test.com", phone="+2222222222", hashed_password="pw", full_name="Donor SNS", role=UserRole.donor)
    bank_user = User(email="bank_sns@test.com", phone="+3333333333", hashed_password="pw", full_name="Bank SNS", role=UserRole.blood_bank)
    coord_user = User(email="coord_sns@test.com", phone="+4444444444", hashed_password="pw", full_name="Coord SNS", role=UserRole.coordinator)
    
    db.add_all([patient_user, donor_user, bank_user, coord_user])
    db.commit()

    # Create Patient Profile
    patient = Patient(user_id=patient_user.id, blood_group_required="O-", units_required=1, urgency="critical", city="Mumbai", latitude=19.0760, longitude=72.8777)
    # Create Donor Profile
    donor = Donor(user_id=donor_user.id, blood_group="O-", is_available=True, latitude=19.0760, longitude=72.8777)
    # Create Blood Bank Profile
    bank = BloodBankProfile(user_id=bank_user.id, hospital_name="Mumbai SNS Bank", contact_phone="123", address="Mumbai", latitude=19.0760, longitude=72.8777)
    
    db.add_all([patient, donor, bank])
    db.commit()

    print("Pre-seeded database for SNS smoke test successfully.")

    print("\n================================================================================")
    print(" 2. RUN SnsService WITH BUDGET CONTROLS")
    print("================================================================================")
    print(f"Current spent budget: ${SnsService.get_spent_budget():.4f}")
    
    # Send first SNS notification
    res = SnsService.send_sns_notification(phone=donor_user.phone, subject="Test Subject 1", message="Message 1")
    print(f"SMS 1 dispatch result: {res} (Expected: True)")
    print(f"Spent budget after SMS 1: ${SnsService.get_spent_budget():.4f} (Expected: $0.02)")
    assert res == True
    assert abs(SnsService.get_spent_budget() - 0.02) < 0.0001

    # Send second SNS notification
    res = SnsService.send_sns_notification(phone=bank_user.phone, subject="Test Subject 2", message="Message 2")
    print(f"SMS 2 dispatch result: {res} (Expected: True)")
    print(f"Spent budget after SMS 2: ${SnsService.get_spent_budget():.4f} (Expected: $0.04)")
    assert res == True
    assert abs(SnsService.get_spent_budget() - 0.04) < 0.0001

    # Send third SNS notification -> Budget is 0.05, 0.04 + 0.02 = 0.06 > 0.05. It should block!
    res = SnsService.send_sns_notification(phone=coord_user.phone, subject="Test Subject 3", message="Message 3")
    print(f"SMS 3 dispatch result: {res} (Expected: False due to budget limit)")
    print(f"Spent budget after SMS 3: ${SnsService.get_spent_budget():.4f} (Expected to remain $0.04)")
    assert res == False
    assert abs(SnsService.get_spent_budget() - 0.04) < 0.0001

    print("Cost Safeguard Budget limits verification passed!")

    print("\n================================================================================")
    print(" 3. TEST E2E DISPATCH DURING REQUEST CREATION")
    print("================================================================================")
    # Reset budget tracker and set limit higher for full flow
    SnsService.reset_tracker()
    settings.AWS_SNS_BUDGET_LIMIT = 40.0
    
    # Create critical blood request
    req = BloodRequest(patient_id=patient.id, blood_group="O-", units_required=1, urgency="critical", status="pending")
    db.add(req)
    db.commit()

    # Trigger notifications
    notif_svc = NotificationService(db)
    notif_svc.notify_request_created(req)

    spent_after_creation = SnsService.get_spent_budget()
    print(f"Budget spent after request creation: ${spent_after_creation:.4f}")
    # We expected:
    # 1. 1 alert to Donor
    # 2. 1 alert to Blood Bank
    # 3. 1 alert to Coordinator
    # Total = 3 dispatches = 3 * 0.02 = 0.06
    print(f"Total spent: ${spent_after_creation:.4f} (Expected: $0.06)")
    assert abs(spent_after_creation - 0.06) < 0.0001

    print("E2E Patient Request creation dispatches to Donors, Blood Banks, and Coordinators verified!")
    print("\nALL AWS SNS NOTIFICATION FUNCTIONAL TESTS COMPLETED SUCCESSFULLY!")

finally:
    db.close()
