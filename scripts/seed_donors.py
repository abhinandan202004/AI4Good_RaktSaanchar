"""
seed_donors.py -- RaktSaanchar Dev Seed Script
===============================================
Inserts sample donor users + donor profiles into the running database.

Requirements:
  pip install psycopg2-binary passlib[bcrypt]

Usage (from project root, with docker-compose up):
  python scripts/seed_donors.py

  # Or override DB host for a remote instance:
  DB_HOST=my-server python scripts/seed_donors.py

The script is idempotent -- it skips any donor whose e-mail already exists.
"""

import os
import sys
from datetime import datetime, timezone, timedelta
from passlib.context import CryptContext

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:
    sys.exit("psycopg2-binary not installed.  Run: pip install psycopg2-binary passlib[bcrypt]")

# ── Config ────────────────────────────────────────────────────────────────────
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "5433"))   # docker-compose maps 5433→5432
DB_NAME = os.getenv("DB_NAME", "raktsaanchar")
DB_USER = os.getenv("DB_USER", "rakt")
DB_PASS = os.getenv("DB_PASS", "rakt")

DEFAULT_PASSWORD = os.getenv("SEED_PASSWORD", "Test@1234")

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ── Blood group display value → SQLAlchemy enum *name* stored in Postgres ────
# SQLAlchemy persists the enum member NAME (e.g. "A_pos"), not the value ("A+").
BLOOD_GROUP_MAP = {
    "A+":  "A_pos",
    "A-":  "A_neg",
    "B+":  "B_pos",
    "B-":  "B_neg",
    "AB+": "AB_pos",
    "AB-": "AB_neg",
    "O+":  "O_pos",
    "O-":  "O_neg",
}


def to_pg_blood_group(display: str) -> str:
    try:
        return BLOOD_GROUP_MAP[display]
    except KeyError:
        raise ValueError(f"Unknown blood group: '{display}'.  Valid: {list(BLOOD_GROUP_MAP)}")


# ── Donor seed data ───────────────────────────────────────────────────────────
DONORS = [
    {
        "full_name": "Arjun Sharma",
        "email": "arjun.sharma@seed.dev",
        "phone": "+911234567801",
        "blood_group": "A+",
        "age": 28,
        "weight": 72.5,
        "city": "Bengaluru",
        "state": "Karnataka",
        "latitude": 12.9716,
        "longitude": 77.5946,
        "is_available": True,
        "total_donations": 5,
        "points": 500,
        "reliability_score": 0.95,
    },
    {
        "full_name": "Priya Nair",
        "email": "priya.nair@seed.dev",
        "phone": "+911234567802",
        "blood_group": "O-",
        "age": 24,
        "weight": 58.0,
        "city": "Bengaluru",
        "state": "Karnataka",
        "latitude": 12.9352,
        "longitude": 77.6245,
        "is_available": True,
        "total_donations": 8,
        "points": 800,
        "reliability_score": 0.98,
    },
    {
        "full_name": "Rahul Mehta",
        "email": "rahul.mehta@seed.dev",
        "phone": "+911234567803",
        "blood_group": "B+",
        "age": 32,
        "weight": 80.0,
        "city": "Mumbai",
        "state": "Maharashtra",
        "latitude": 19.0760,
        "longitude": 72.8777,
        "is_available": True,
        "total_donations": 12,
        "points": 1200,
        "reliability_score": 0.90,
        "last_donated_at": datetime.now(timezone.utc) - timedelta(days=120),
    },
    {
        "full_name": "Sanya Kapoor",
        "email": "sanya.kapoor@seed.dev",
        "phone": "+911234567804",
        "blood_group": "AB+",
        "age": 27,
        "weight": 65.0,
        "city": "Delhi",
        "state": "Delhi",
        "latitude": 28.7041,
        "longitude": 77.1025,
        "is_available": False,  # on cooldown
        "total_donations": 3,
        "points": 300,
        "reliability_score": 0.88,
        "last_donated_at": datetime.now(timezone.utc) - timedelta(days=45),
    },
    {
        "full_name": "Vikram Reddy",
        "email": "vikram.reddy@seed.dev",
        "phone": "+911234567805",
        "blood_group": "O+",
        "age": 35,
        "weight": 88.0,
        "city": "Hyderabad",
        "state": "Telangana",
        "latitude": 17.3850,
        "longitude": 78.4867,
        "is_available": True,
        "total_donations": 20,
        "points": 2000,
        "reliability_score": 1.0,
    },
    {
        "full_name": "Meera Iyer",
        "email": "meera.iyer@seed.dev",
        "phone": "+911234567806",
        "blood_group": "A-",
        "age": 30,
        "weight": 60.5,
        "city": "Chennai",
        "state": "Tamil Nadu",
        "latitude": 13.0827,
        "longitude": 80.2707,
        "is_available": True,
        "total_donations": 7,
        "points": 700,
        "reliability_score": 0.92,
    },
    {
        "full_name": "Karan Singh",
        "email": "karan.singh@seed.dev",
        "phone": "+911234567807",
        "blood_group": "B-",
        "age": 22,
        "weight": 70.0,
        "city": "Pune",
        "state": "Maharashtra",
        "latitude": 18.5204,
        "longitude": 73.8567,
        "is_available": True,
        "total_donations": 1,
        "points": 100,
        "reliability_score": 0.80,
    },
    {
        "full_name": "Divya Pillai",
        "email": "divya.pillai@seed.dev",
        "phone": "+911234567808",
        "blood_group": "AB-",
        "age": 29,
        "weight": 55.0,
        "city": "Kochi",
        "state": "Kerala",
        "latitude": 9.9312,
        "longitude": 76.2673,
        "is_available": True,
        "total_donations": 4,
        "points": 400,
        "reliability_score": 0.87,
    },
    {
        "full_name": "Aditya Joshi",
        "email": "aditya.joshi@seed.dev",
        "phone": "+911234567809",
        "blood_group": "O+",
        "age": 26,
        "weight": 75.0,
        "city": "Bengaluru",
        "state": "Karnataka",
        "latitude": 12.9100,
        "longitude": 77.6500,
        "is_available": True,
        "total_donations": 9,
        "points": 900,
        "reliability_score": 0.94,
    },
    {
        "full_name": "Neha Gupta",
        "email": "neha.gupta@seed.dev",
        "phone": "+911234567810",
        "blood_group": "A+",
        "age": 31,
        "weight": 62.0,
        "city": "Jaipur",
        "state": "Rajasthan",
        "latitude": 26.9124,
        "longitude": 75.7873,
        "is_available": True,
        "total_donations": 6,
        "points": 600,
        "reliability_score": 0.91,
    },
]

# ── Helpers ───────────────────────────────────────────────────────────────────

def connect():
    return psycopg2.connect(
        host=DB_HOST, port=DB_PORT,
        dbname=DB_NAME, user=DB_USER, password=DB_PASS,
    )


def upsert_auth_user(cur, donor: dict, hashed_pw: str) -> int | None:
    """Insert user into auth schema. Returns new id or None if already exists."""
    cur.execute("SELECT id FROM auth.users WHERE email = %s", (donor["email"],))
    row = cur.fetchone()
    if row:
        print(f"  [SKIP] auth user already exists: {donor['email']} (id={row['id']})")
        return row["id"]

    cur.execute(
        """
        INSERT INTO auth.users
            (email, phone, hashed_password, full_name, role,
             is_active, is_verified, created_at, updated_at)
        VALUES
            (%(email)s, %(phone)s, %(hashed_password)s, %(full_name)s, 'donor',
             TRUE, TRUE, NOW(), NOW())
        RETURNING id
        """,
        {
            "email": donor["email"],
            "phone": donor["phone"],
            "hashed_password": hashed_pw,
            "full_name": donor["full_name"],
        },
    )
    auth_id = cur.fetchone()["id"]
    print(f"  [AUTH]  Created auth user '{donor['full_name']}' id={auth_id}")
    return auth_id


def upsert_core_user(cur, donor: dict, auth_id: int) -> int:
    """Mirror user into core schema (same id if possible, else auto)."""
    cur.execute("SELECT id FROM core.users WHERE email = %s", (donor["email"],))
    row = cur.fetchone()
    if row:
        print(f"  [SKIP] core user already exists: {donor['email']} (id={row['id']})")
        return row["id"]

    # Try to keep ids in sync with auth schema for simpler debugging
    cur.execute(
        """
        INSERT INTO core.users
            (id, email, phone, hashed_password, full_name, role,
             is_active, is_verified, created_at, updated_at)
        VALUES
            (%(id)s, %(email)s, %(phone)s, %(hashed_password)s, %(full_name)s, 'donor',
             TRUE, TRUE, NOW(), NOW())
        ON CONFLICT (id) DO UPDATE
            SET email = EXCLUDED.email
        RETURNING id
        """,
        {
            "id": auth_id,
            "email": donor["email"],
            "phone": donor["phone"],
            "hashed_password": "hashed_in_auth_schema",  # not used for auth
            "full_name": donor["full_name"],
        },
    )
    core_id = cur.fetchone()["id"]
    print(f"  [CORE]  Created core user '{donor['full_name']}' id={core_id}")
    return core_id


def upsert_donor_profile(cur, donor: dict, user_id: int):
    """Insert donor profile into core schema."""
    cur.execute("SELECT id FROM core.donors WHERE user_id = %s", (user_id,))
    if cur.fetchone():
        print(f"  [SKIP] donor profile already exists for user_id={user_id}")
        return

    last_donated = donor.get("last_donated_at")
    # Postgres stores the enum member *name* (A_pos, O_neg…), not the display value
    pg_blood_group = to_pg_blood_group(donor["blood_group"])

    cur.execute(
        """
        INSERT INTO core.donors
            (user_id, blood_group, age, weight, city, state,
             latitude, longitude, is_available,
             reliability_score, response_rate, no_show_count,
             total_donations, points,
             last_donated_at, created_at, updated_at)
        VALUES
            (%(user_id)s, %(blood_group)s::bloodgroup, %(age)s, %(weight)s,
             %(city)s, %(state)s, %(latitude)s, %(longitude)s,
             %(is_available)s,
             %(reliability_score)s, 1.0, 0,
             %(total_donations)s, %(points)s,
             %(last_donated_at)s, NOW(), NOW())
        RETURNING id
        """,
        {
            "user_id": user_id,
            "blood_group": pg_blood_group,
            "age": donor["age"],
            "weight": donor["weight"],
            "city": donor["city"],
            "state": donor["state"],
            "latitude": donor["latitude"],
            "longitude": donor["longitude"],
            "is_available": donor["is_available"],
            "reliability_score": donor["reliability_score"],
            "total_donations": donor["total_donations"],
            "points": donor["points"],
            "last_donated_at": last_donated,
        },
    )
    donor_id = cur.fetchone()["id"]
    print(f"  [DONOR] Created donor profile id={donor_id} blood={donor['blood_group']} ({pg_blood_group}) city={donor['city']}")


# -- Main ----------------------------------------------------------------------

def main():
    print(f"Connecting to PostgreSQL at {DB_HOST}:{DB_PORT}/{DB_NAME} ...")
    try:
        conn = connect()
    except Exception as e:
        sys.exit(f"Connection failed: {e}\n\nMake sure docker-compose is running.")

    conn.autocommit = False
    hashed_pw = pwd_ctx.hash(DEFAULT_PASSWORD)

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            print(f"\nSeeding {len(DONORS)} donors (password: '{DEFAULT_PASSWORD}') ...\n")
            for donor in DONORS:
                print(f"-- {donor['full_name']} ({donor['blood_group']}, {donor['city']}) --")
                auth_id  = upsert_auth_user(cur, donor, hashed_pw)
                core_id  = upsert_core_user(cur, donor, auth_id)
                upsert_donor_profile(cur, donor, core_id)
                print()

        conn.commit()
        print(f"[OK] Done!  {len(DONORS)} donors seeded successfully.")
        print(f"     All donors can log in with password: {DEFAULT_PASSWORD}")
        print(f"     e.g.  email: arjun.sharma@seed.dev  password: {DEFAULT_PASSWORD}")

    except Exception as e:
        conn.rollback()
        print(f"\n[ERROR] {e}")
        import traceback; traceback.print_exc()
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
