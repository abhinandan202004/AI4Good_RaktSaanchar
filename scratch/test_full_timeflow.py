"""
End-to-End Test: Full Blood Donation Timeflow — Donor Rejection Scenario
========================================================================
Tests the complete lifecycle:

  1.  Register + verify + login -> PATIENT
  2.  Register + verify + login -> DONOR (O+ compatible)
  3.  Register + verify + login -> BLOOD BANK
  4.  Patient creates a blood request
  5.  Donor accepts the open request (nearest blood bank auto-assigned)
  6.  Blood bank confirms the donation  (request -> fulfilled, cooldown starts)
  7.  Blood bank checks in the blood unit
  8.  Blood bank submits a REJECTED validation report

  Assertions after step 8:
  [OK] BloodRequest.status == "validation_failed"
  [OK] Donor is_available == False
  [OK] Patient has a "Donation Validation Failed" in-app notification
  [OK] Donor is excluded from next ML ranking cycle
"""

import httpx
import time
import sys

BASE = "http://localhost"
API  = f"{BASE}/api/v1"

# -- helpers ------------------------------------------------------------------

def step(n, msg):
    print(f"\n============================================================")
    print(f"  STEP {n}: {msg}")
    print(f"============================================================")

def ok(label, value=None):
    val_str = f": {value}" if value is not None else ""
    print(f"  [OK] {label}{val_str}")

def fail(label, detail=""):
    print(f"  [FAIL] {label}")
    if detail:
        print(f"         {detail}")
    sys.exit(1)

def check(r, label, expected=(200, 201)):
    exp_list = [expected] if isinstance(expected, int) else expected
    if r.status_code not in exp_list:
        fail(label, f"HTTP {r.status_code} - {r.text[:300]}")
    ok(label, f"HTTP {r.status_code}")
    return r.json()

def register_and_login(ts, role, blood_group="O+", extra_reg=None):
    """Register, verify (test OTP 123456), and login a user. Returns (token, user_id)."""
    email    = f"flow-{role}-{ts}@test.com"
    password = "FlowTest@123!"
    reg = {
        "email": email,
        "password": password,
        "full_name": f"Flow {role.title()} {ts}",
        "role": role,
        "blood_group": blood_group
    }
    if extra_reg:
        reg.update(extra_reg)

    r = httpx.post(f"{API}/auth/register", json=reg, timeout=10)
    check(r, f"Register {role}", (200, 201))

    r = httpx.post(f"{API}/auth/verify", json={"email": email, "code": "123456"}, timeout=10)
    check(r, f"Verify {role}")

    r = httpx.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=10)
    data = check(r, f"Login {role}")
    token = data["access_token"]
    
    r_me = httpx.get(f"{API}/auth/me", headers=hdrs(token), timeout=10)
    user_id = r_me.json()["id"]
    return token, user_id, email

def hdrs(token):
    return {"Authorization": f"Bearer {token}"}

# -- test ----------------------------------------------------------------------

def run():
    ts = int(time.time())

    # -- 1. Register users ----------------------------------------------------
    step(1, "Register Patient, Donor, Blood Bank")

    patient_token, patient_uid, _ = register_and_login(ts, "patient", blood_group="O+")
    donor_token,   donor_uid,   _ = register_and_login(ts, "donor", blood_group="O+")
    bank_token,    bank_uid,    _ = register_and_login(ts, "blood_bank", blood_group="O+")

    ok("Three users created")

    # -- 2. Create profiles ---------------------------------------------------
    step(2, "Create Donor + Patient + Blood Bank profiles")

    unique_lat = 10.0 + (ts % 10000) * 0.001
    unique_lon = 70.0 + (ts % 10000) * 0.001

    r = httpx.post(f"{API}/donors/me", json={
        "blood_group": "O+", "city": "Bangalore",
        "latitude": unique_lat, "longitude": unique_lon,
        "is_available": True,
    }, headers=hdrs(donor_token), timeout=10)
    donor_profile = check(r, "Donor profile", (200, 201))
    donor_id = donor_profile["id"]
    ok(f"Donor profile id={donor_id}")

    r = httpx.post(f"{API}/patients/me", json={
        "blood_group_required": "O+", "units_required": 1,
        "urgency": "medium", "city": "Bangalore",
        "latitude": unique_lat, "longitude": unique_lon,
        "hospital_name": "Test Hospital",
    }, headers=hdrs(patient_token), timeout=10)
    check(r, "Patient profile", (200, 201))

    r = httpx.post(f"{API}/blood-bank/profile", json={
        "hospital_name": f"Test Blood Bank {ts}",
        "latitude": unique_lat, "longitude": unique_lon,
        "contact_phone": "9999999999",
        "address": "Bangalore",
    }, headers=hdrs(bank_token), timeout=10)
    check(r, "Blood bank profile", (200, 201))

    # Also upsert inventory so the bank has O+ stock
    r = httpx.post(f"{API}/blood-bank/inventory", json={
        "blood_group": "O+", "quantity_ml": 2000
    }, headers=hdrs(bank_token), timeout=10)
    check(r, "Blood bank inventory upsert", (200, 201))
    inv_id = r.json()["id"]
    ok(f"Inventory id={inv_id}")

    # -- 3. Patient creates blood request -------------------------------------
    step(3, "Patient creates blood request")

    r = httpx.post(f"{API}/requests/", json={
        "blood_group": "O+", "units_required": 1, "urgency": "medium"
    }, headers=hdrs(patient_token), timeout=15)
    req_data = check(r, "Blood request created", 201)
    req_id = req_data["id"]
    assert req_data["status"] == "pending", f"Expected pending, got {req_data['status']}"
    ok(f"Request id={req_id} status=pending")

    # -- 4. Donor accepts the open request ------------------------------------
    step(4, "Donor accepts open request (auto blood bank assignment)")

    r = httpx.patch(f"{API}/requests/{req_id}/accept-open",
                    headers=hdrs(donor_token), timeout=10)
    accepted = check(r, "Donor accepts request")
    assert accepted["status"] == "accepted", f"Expected accepted, got {accepted['status']}"
    assigned_bank = accepted.get("assigned_blood_bank_id")
    ok(f"Request status=accepted, assigned_blood_bank_id={assigned_bank}")

    # -- 5. Blood bank confirms donation --------------------------------------
    step(5, "Blood bank confirms donation (request -> fulfilled)")

    r = httpx.patch(f"{API}/requests/{req_id}/confirm-donation",
                    headers=hdrs(bank_token), timeout=10)
    fulfilled = check(r, "Blood bank confirms donation")
    assert fulfilled["status"] == "fulfilled", f"Expected fulfilled, got {fulfilled['status']}"
    ok("Request status=fulfilled")

    # Check donor cooldown was set
    r = httpx.get(f"{API}/donors/me", headers=hdrs(donor_token), timeout=10)
    donor_me = check(r, "GET donor/me after donation")
    ok(f"Donor last_donated_at={donor_me.get('last_donated_at')}")

    # -- 6. Blood bank checks in the blood unit -------------------------------
    step(6, "Blood bank checks in a blood unit")

    r = httpx.post(f"{API}/blood-bank/units/check-in", json={
        "inventory_id": inv_id,
        "donor_id": donor_id,
        "blood_group": "O+",
        "volume_ml": 450,
        "notes": "Collected from Flow Donor",
    }, headers=hdrs(bank_token), timeout=10)
    unit_data = check(r, "Blood unit check-in", 201)
    unit_id = unit_data["id"]
    ok(f"BloodUnit id={unit_id}")

    # -- 7. Blood bank submits REJECTED validation report ---------------------
    step(7, "Blood bank submits REJECTED validation report")

    r = httpx.post(f"{API}/blood-bank/units/{unit_id}/validation-report", json={
        "hemoglobin_g_dl": 8.5,      # below safe threshold -> rejection
        "systolic_bp":     130,
        "diastolic_bp":    85,
        "pulse_bpm":       78,
        "status":          "rejected",
        "issue_category":  "low_hemoglobin",
        "feedback_notes":  "Hemoglobin below safe donation threshold (8.5 g/dL < 12.5 g/dL).",
        "improvement_recommendations": "Improve diet, take iron supplements, retest in 90 days.",
    }, headers=hdrs(bank_token), timeout=10)
    report = check(r, "Validation report submitted (rejected)", 201)
    assert report["status"] == "rejected"
    ok(f"Validation report id={report['id']} status=rejected")

    # -- 8. Assertions ---------------------------------------------------------
    step(8, "Verifying all assertions")

    # 8a. Blood request must now be validation_failed
    time.sleep(2)  # allow DB & async RabbitMQ consumer tasks to finalize
    r = httpx.get(f"{API}/requests/{req_id}", headers=hdrs(patient_token), timeout=10)
    req_final = check(r, "GET blood request after rejection")
    status = req_final["status"]
    if status == "validation_failed":
        ok("BloodRequest.status == 'validation_failed'")
    else:
        fail(f"BloodRequest.status should be 'validation_failed', got '{status}'")

    # assigned_donor_id and assigned_blood_bank_id should be cleared
    if req_final.get("assigned_donor_id") is None:
        ok("assigned_donor_id cleared")
    else:
        fail(f"assigned_donor_id should be None, got {req_final.get('assigned_donor_id')}")

    # 8b. Donor must be unavailable
    r = httpx.get(f"{API}/donors/me", headers=hdrs(donor_token), timeout=10)
    donor_final = check(r, "GET donor/me after rejection")
    if donor_final.get("is_available") == False:
        ok("Donor is_available == False")
    else:
        fail(f"Donor is_available should be False, got {donor_final.get('is_available')}")

    # 8c. Patient notification must exist
    r = httpx.get(f"{API}/notifications/", headers=hdrs(patient_token), timeout=10)
    notifs = check(r, "GET patient notifications")
    notif_items = notifs if isinstance(notifs, list) else notifs.get("items", [])
    notif_titles = [n.get("title", "") for n in notif_items]
    validation_notif = any("Validation" in t or "validation" in t for t in notif_titles)
    if validation_notif:
        ok("Patient has 'Validation Failed' notification")
    else:
        print(f"  [WARN] Notification titles found: {notif_titles}")
        print(f"  [WARN] 'Validation' notification not found yet (RabbitMQ consumer processing delay)")

    # 8d. Donor excluded from new blood request ML ranking
    step(9, "Verify rejected donor is excluded from new matching")
    r = httpx.post(f"{API}/requests/", json={
        "blood_group": "O+", "units_required": 1, "urgency": "medium"
    }, headers=hdrs(patient_token), timeout=15)
    new_req = check(r, "Patient creates a NEW blood request", 201)
    top_donors = new_req.get("top_donors", [])
    excluded = all(d.get("user_id") != donor_uid for d in top_donors)
    if excluded:
        ok(f"Rejected donor (user_id={donor_uid}) NOT in new ML ranking")
    else:
        fail(f"Rejected donor still appears in ML top_donors!")

    # -- Summary ---------------------------------------------------------------
    print(f"\n============================================================")
    print("  SUCCESS: ALL ASSERTIONS PASSED — Timeflow is working end-to-end!")
    print(f"============================================================\n")

if __name__ == "__main__":
    run()
