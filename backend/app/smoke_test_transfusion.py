import sys
import os

# Set DATABASE_URL to test.db for local SQLite testing
os.environ["DATABASE_URL"] = "sqlite:///./test.db"
os.environ["UPLOAD_DIR"] = "./uploads"

from fastapi.testclient import TestClient
from app.main import app
from app.core.database import SessionLocal, Base, engine
from app.modules.users.models import User, UserRole
from app.core.security import hash_password

client = TestClient(app)

def main():
    print("================================================================================")
    print(" 1. RESET AND SETUP TRANSFUSION SMOKE TEST")
    print("================================================================================")
    
    # Recreate tables to ensure schema is up-to-date
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    
    # Setup test user
    db = SessionLocal()
    try:
        user = User(
            email="patient_transfusion@test.com",
            phone="+9999999999",
            hashed_password=hash_password("password123"),
            full_name="Patient Transfusion",
            role=UserRole.patient,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        user_id = user.id
        print(f"Created patient user with ID: {user_id}")
    finally:
        db.close()

    # Login to get JWT token
    login_resp = client.post("/api/v1/auth/login", json={
        "email": "patient_transfusion@test.com",
        "password": "password123"
    })
    assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("Logged in successfully.")

    print("\n================================================================================")
    print(" 2. TEST INVALID INPUT RANGE VALIDATION (422)")
    print("================================================================================")
    
    # Send out of range age (age 1 is invalid, ge=2)
    invalid_data = {
        "age": 1,
        "gender": "Male",
        "weight_kg": 45.0,
        "thalassemia_type": "Major",
        "current_hb_level": 7.0,
        "target_hb_level": 10.0,
        "ferritin_level": 500.0,
        "days_since_last_transfusion": 20,
        "previous_units_received": 2,
        "average_units_per_transfusion": 2.0,
        "transfusions_last_12_months": 10,
        "spleen_status": "Normal",
        "symptom_severity": "Moderate",
        "blood_group": "O+"
    }
    
    resp = client.post("/api/v1/transfusion/predict", json=invalid_data, headers=headers)
    assert resp.status_code == 422, f"Expected 422 for invalid age, got {resp.status_code}: {resp.text}"
    print("Validation successfully rejected out-of-range age (1).")

    # Send out of range current_hb_level (4.0 is invalid, ge=4.5)
    invalid_data["age"] = 25
    invalid_data["current_hb_level"] = 4.0
    resp = client.post("/api/v1/transfusion/predict", json=invalid_data, headers=headers)
    assert resp.status_code == 422, f"Expected 422 for invalid hb level, got {resp.status_code}: {resp.text}"
    print("Validation successfully rejected out-of-range hb_level (4.0).")

    print("\n================================================================================")
    print(" 3. TEST VALID INFERENCE & HISTORY STORE (201)")
    print("================================================================================")
    
    valid_data = {
        "age": 25,
        "gender": "Male",
        "weight_kg": 70.0,
        "thalassemia_type": "Major",
        "current_hb_level": 7.0,
        "target_hb_level": 10.0,
        "ferritin_level": 1000.0,
        "days_since_last_transfusion": 21,
        "previous_units_received": 2,
        "average_units_per_transfusion": 2.0,
        "transfusions_last_12_months": 12,
        "spleen_status": "Normal",
        "symptom_severity": "Moderate",
        "blood_group": "O+"
    }
    
    resp = client.post("/api/v1/transfusion/predict", json=valid_data, headers=headers)
    assert resp.status_code == 201, f"Expected 201, got {resp.status_code}: {resp.text}"
    pred_res = resp.json()
    print("Prediction result received:")
    print(pred_res)
    assert "predicted_units_required" in pred_res
    assert "recommended_next_transfusion_in_days" in pred_res
    assert pred_res["predicted_units_required"] in [1, 2, 3, 4]
    
    print("\n================================================================================")
    print(" 4. GET PREDICTION HISTORY (200)")
    print("================================================================================")
    
    resp = client.get("/api/v1/transfusion/history", headers=headers)
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    history = resp.json()
    assert len(history) == 1, f"Expected history size 1, got {len(history)}"
    assert history[0]["id"] == pred_res["id"]
    print("Success: Retrieved 1 prediction history record successfully.")

    print("\n================================================================================")
    print(" ALL TRANSFUSION SERVICE FUNCTIONAL TESTS PASSED SUCCESSFULLY!")
    print("================================================================================")

if __name__ == "__main__":
    main()
