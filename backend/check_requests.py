import os
from sqlalchemy import create_engine, text

def main():
    db_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@127.0.0.1:5432/rakt")
    engine = create_engine(db_url)
    
    try:
        with engine.connect() as conn:
            requests = conn.execute(text("SELECT id, status, urgency, blood_group, assigned_donor_id, assigned_blood_bank_id FROM blood_requests")).fetchall()
            print("Current Blood Requests:")
            for r in requests:
                print(f"ID: {r[0]} | Status: {r[1]} | Urgency: {r[2]} | Group: {r[3]} | Donor ID: {r[4]} | Bank ID: {r[5]}")
                
            users = conn.execute(text("SELECT id, email, role FROM users")).fetchall()
            print("\nUsers:")
            for u in users:
                print(f"ID: {u[0]} | Email: {u[1]} | Role: {u[2]}")
                
            banks = conn.execute(text("SELECT user_id, hospital_name FROM blood_bank_profiles")).fetchall()
            print("\nBlood Banks:")
            for b in banks:
                print(f"User ID: {b[0]} | Hospital: {b[1]}")
                
            units = conn.execute(text("SELECT id, inventory_id, donor_id, blood_group, volume_ml, status, is_safe FROM blood_units")).fetchall()
            print("\nBlood Units:")
            for u in units:
                print(f"ID: {u[0]} | Inv ID: {u[1]} | Donor ID: {u[2]} | Group: {u[3]} | Vol: {u[4]} | Status: {u[5]} | Safe: {u[6]}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
