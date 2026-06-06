import time
import uuid
import httpx
import math

BASE_URL = "http://localhost:8000/api/v1"

def print_section(title):
    print("\n" + "=" * 60)
    print(f" {title.upper()}")
    print("=" * 60)

def main():
    suffix = str(uuid.uuid4())[:8]
    coord_email = f"coord_{suffix}@test.com"
    bank_email = f"bank_{suffix}@test.com"
    donor_email = f"donor_{suffix}@test.com"
    patient_email = f"patient_{suffix}@test.com"
    password = "SecurePassword123"

    print(f"Generated user emails for map test run: {suffix}")

    with httpx.Client(base_url=BASE_URL, timeout=10.0) as client:
        # ──────────────────────────────────────────────────────────────────────
        # 1. REGISTRATION & LOGIN
        # ──────────────────────────────────────────────────────────────────────
        print_section("1. User Registration & Login")
        
        users_to_register = [
            {"email": coord_email, "full_name": "Coordinator Map", "role": "coordinator"},
            {"email": bank_email, "full_name": "Mumbai Blood Bank", "role": "blood_bank"},
            {"email": donor_email, "full_name": "Pune Donor", "role": "donor"},
            {"email": patient_email, "full_name": "Mumbai Patient", "role": "patient"},
        ]

        tokens = {}
        user_ids = {}

        for user in users_to_register:
            reg_resp = client.post("/auth/register", json={
                "email": user["email"],
                "password": password,
                "full_name": user["full_name"],
                "role": user["role"]
            })
            if reg_resp.status_code != 201:
                print(f"Failed to register {user['email']}: {reg_resp.status_code} - {reg_resp.text}")
                return
            reg_data = reg_resp.json()
            user_ids[user["role"]] = reg_data["id"]
            print(f"Registered {user['role']} (ID: {reg_data['id']}) successfully.")

            # Login
            login_resp = client.post("/auth/login", json={
                "email": user["email"],
                "password": password
            })
            if login_resp.status_code != 200:
                print(f"Failed to login {user['email']}: {login_resp.status_code} - {login_resp.text}")
                return
            tokens[user["role"]] = login_resp.json()["access_token"]
            print(f"Logged in {user['role']} successfully.")

        # ──────────────────────────────────────────────────────────────────────
        # 2. PROFILE CREATION WITH GEOLOCATION COORDINATES
        # ──────────────────────────────────────────────────────────────────────
        print_section("2. Geolocation Profile Creation")

        # Blood Bank Profile (Mumbai: 19.0760, 72.8777)
        bank_headers = {"Authorization": f"Bearer {tokens['blood_bank']}"}
        bank_profile_resp = client.post("/blood-bank/profile", json={
            "hospital_name": "Mumbai Central Hospital Blood Bank",
            "latitude": 19.0760,
            "longitude": 72.8777,
            "contact_phone": "022-1234567",
            "address": "Mumbai Central, Mumbai, Maharashtra"
        }, headers=bank_headers)

        if bank_profile_resp.status_code != 201:
            print(f"Failed to create Blood Bank profile: {bank_profile_resp.status_code} - {bank_profile_resp.text}")
            return
        print("Blood Bank profile created successfully:")
        print(bank_profile_resp.json())

        # Retrieve profile me
        me_resp = client.get("/blood-bank/profile/me", headers=bank_headers)
        assert me_resp.status_code == 200
        assert me_resp.json()["hospital_name"] == "Mumbai Central Hospital Blood Bank"
        print("Successfully fetched /profile/me for Blood Bank.")

        # Update profile me
        update_resp = client.patch("/blood-bank/profile/me", json={
            "contact_phone": "022-7654321"
        }, headers=bank_headers)
        assert update_resp.status_code == 200
        assert update_resp.json()["contact_phone"] == "022-7654321"
        print("Successfully updated /profile/me for Blood Bank.")

        # Donor Profile (Pune: 18.5204, 73.8567)
        donor_headers = {"Authorization": f"Bearer {tokens['donor']}"}
        donor_profile_resp = client.post("/donors/me", json={
            "blood_group": "O+",
            "age": 28,
            "weight": 75.0,
            "city": "Pune",
            "state": "Maharashtra",
            "latitude": 18.5204,
            "longitude": 73.8567
        }, headers=donor_headers)
        
        if donor_profile_resp.status_code != 201:
            print(f"Failed to create Donor profile: {donor_profile_resp.status_code} - {donor_profile_resp.text}")
            return
        donor_id = donor_profile_resp.json()["id"]
        print(f"Donor profile created. Donor ID: {donor_id}")

        # Patient Profile (Mumbai: 19.0760, 72.8777)
        patient_headers = {"Authorization": f"Bearer {tokens['patient']}"}
        patient_profile_resp = client.post("/patients/me", json={
            "blood_group_required": "O+",
            "units_required": 1,
            "urgency": "medium",
            "hospital_name": "Mumbai Central Hospital",
            "city": "Mumbai",
            "state": "Maharashtra",
            "latitude": 19.0760,
            "longitude": 72.8777
        }, headers=patient_headers)

        if patient_profile_resp.status_code != 201:
            print(f"Failed to create Patient profile: {patient_profile_resp.status_code} - {patient_profile_resp.text}")
            return
        patient_id = patient_profile_resp.json()["id"]
        print(f"Patient profile created. Patient ID: {patient_id}")

        # ──────────────────────────────────────────────────────────────────────
        # 3. VERIFY NEAREST BLOOD BANK ENDPOINT
        # ──────────────────────────────────────────────────────────────────────
        print_section("3. Nearest Blood Bank Search")

        nearest_resp = client.get("/blood-bank/nearest?latitude=19.0760&longitude=72.8777&limit=5", headers=patient_headers)
        if nearest_resp.status_code != 200:
            print(f"Nearest blood bank query failed: {nearest_resp.status_code} - {nearest_resp.text}")
            return
        nearest_banks = nearest_resp.json()
        print(f"Nearest blood banks returned: {len(nearest_banks)}")
        found_our_bank = False
        for b in nearest_banks:
            print(f"  Bank: {b['hospital_name']} | Distance: {b['distance_km']}km | Lat/Lon: {b['latitude']}/{b['longitude']}")
            if b["hospital_name"] == "Mumbai Central Hospital Blood Bank":
                found_our_bank = True
                assert b["distance_km"] == 0.0
        
        if found_our_bank:
            print("Success: Mumbai Central Hospital Blood Bank found with distance 0.0 km!")
        else:
            print("ERROR: Did not find Mumbai Central Hospital Blood Bank in nearest query.")
            return

        # ──────────────────────────────────────────────────────────────────────
        # 4. VERIFY ML DONOR RANKING USES HAVERSINE DISTANCE
        # ──────────────────────────────────────────────────────────────────────
        print_section("4. ML Donor Ranking with Haversine Pune-Mumbai Distance")

        coord_headers = {"Authorization": f"Bearer {tokens['coordinator']}"}
        ml_resp = client.post("/ml/rank-donors", json={
            "patient_blood_group": "O+",
            "urgency": "medium",
            "units_required": 1,
            "patient_city": "Mumbai",
            "patient_latitude": 19.0760,
            "patient_longitude": 72.8777,
            "limit": 50
        }, headers=coord_headers)

        if ml_resp.status_code != 200:
            print(f"ML Donor Ranking endpoint failed: {ml_resp.status_code} - {ml_resp.text}")
            return
        
        ranked_donors = ml_resp.json()
        print(f"Ranked donors returned: {len(ranked_donors)}")
        for rd in ranked_donors:
            print(f"  Returned Donor ID: {rd['donor_id']} | Dist: {rd['distance_km']} km | Prob: {rd['match_probability']}")
        
        # Verify Jane Pune Donor is scored with exact distance
        pune_donor = next((d for d in ranked_donors if d["donor_id"] == donor_id), None)
        if pune_donor:
            print(f"Success: Jane Pune Donor is ranked!")
            print(f"  Distance calculated by backend: {pune_donor['distance_km']} km")
            print(f"  Match Probability: {pune_donor['match_probability']}")
            # Pune to Mumbai distance should be around 119-120 km.
            # If the fallback (different cities Mumbai vs Pune) was used, it would be exactly 150.0 km.
            # So if it is ~119.67 km, it verifies Haversine was used!
            dist = pune_donor['distance_km']
            print(f"  Checking distance {dist} km is Haversine Pune-Mumbai (~119.7 km)...")
            assert 118.0 <= dist <= 121.0, f"Distance {dist} km is not Pune-Mumbai exact Haversine distance!"
            print("Success: Verified that ML donor ranking uses exact Haversine distance (~120 km) instead of fallback (150 km)!")
        else:
            print(f"Warning: Jane Pune Donor was not found in ranking results.")

        # ──────────────────────────────────────────────────────────────────────
        # 4b. VERIFY ML DONOR RANKING VIA REQUEST_ID
        # ──────────────────────────────────────────────────────────────────────
        print_section("4b. ML Donor Ranking via request_id")

        # Create active request to use for DB ranking
        req_resp = client.post("/requests/", json={
            "blood_group": "O+",
            "units_required": 1,
            "urgency": "medium"
        }, headers=patient_headers)
        assert req_resp.status_code == 201
        created_req = req_resp.json()
        req_id = created_req["id"]
        print(f"Created active request for DB ranking test. Request ID: {req_id}")

        ml_db_resp = client.post("/ml/rank-donors", json={
            "request_id": req_id,
            "limit": 50
        }, headers=coord_headers)

        if ml_db_resp.status_code != 200:
            print(f"ML Donor Ranking via request_id failed: {ml_db_resp.status_code} - {ml_db_resp.text}")
            return
        
        ranked_donors_db = ml_db_resp.json()
        print(f"Ranked donors via request_id returned: {len(ranked_donors_db)}")
        assert len(ranked_donors_db) > 0, "No donors ranked for request_id!"
        
        pune_donor_db = next((d for d in ranked_donors_db if d["donor_id"] == donor_id), None)
        assert pune_donor_db is not None, "Pune donor missing in request_id-based ranking"
        print(f"  Pune donor distance in DB ranking: {pune_donor_db['distance_km']} km")
        assert 118.0 <= pune_donor_db['distance_km'] <= 121.0
        print("Success: Verified that ML donor ranking via request_id resolves coordinates and matches successfully!")

        # ──────────────────────────────────────────────────────────────────────
        # 5. VERIFY COORDINATOR GEOJSON MAP-DATA ENDPOINT
        # ──────────────────────────────────────────────────────────────────────
        print_section("5. Coordinator GeoJSON Map-Data")

        print("Active request created to verify in map-data.")

        map_resp = client.get("/ml/map-data", headers=coord_headers)
        if map_resp.status_code != 200:
            print(f"Coordinator map-data query failed: {map_resp.status_code} - {map_resp.text}")
            return
        
        geojson = map_resp.json()
        print("GeoJSON response received. Feature count:", len(geojson.get("features", [])))
        assert geojson["type"] == "FeatureCollection"
        
        features = geojson["features"]
        types_found = set()
        for f in features:
            props = f["properties"]
            geom = f["geometry"]
            print(f"  Feature type: {props['type']} | Coords: {geom['coordinates']}")
            types_found.add(props["type"])
            assert geom["type"] == "Point"
            assert len(geom["coordinates"]) == 2

        assert "donor" in types_found, "Donor features missing in map-data"
        assert "patient" in types_found, "Patient request features missing in map-data"
        assert "blood_bank" in types_found, "Blood Bank features missing in map-data"
        print("Success: Verified all types of geo features (donor, patient/request, blood_bank) are correctly populated in GeoJSON!")

        print_section("ALL MAP & GEOLOCATION TESTS COMPLETED SUCCESSFULLY!")

if __name__ == "__main__":
    main()
