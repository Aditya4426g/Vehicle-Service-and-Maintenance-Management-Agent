"""
test_database_schema.py - Schema and Seed SQL Integrity Test.
Verifies table definitions, required columns, foreign keys, and seed integrity.
"""
import os
import re

DATABASE_DIR = os.path.join(os.path.dirname(__file__), "..", "database")
SCHEMA_SQL_PATH = os.path.join(DATABASE_DIR, "schema.sql")
SEED_SQL_PATH = os.path.join(DATABASE_DIR, "seed.sql")

EXPECTED_TABLES = [
    "users",
    "vehicles",
    "service_history",
    "maintenance_schedules",
    "maintenance_records",
    "service_centers",
    "appointments",
    "notifications"
]


def test_schema_file_exists():
    """Verify schema.sql exists and is non-empty."""
    assert os.path.exists(SCHEMA_SQL_PATH), "schema.sql is missing"
    with open(SCHEMA_SQL_PATH, "r", encoding="utf-8") as f:
        content = f.read()
    assert len(content) > 100, "schema.sql is empty or too short"


def test_seed_file_exists():
    """Verify seed.sql exists and is non-empty."""
    assert os.path.exists(SEED_SQL_PATH), "seed.sql is missing"
    with open(SEED_SQL_PATH, "r", encoding="utf-8") as f:
        content = f.read()
    assert len(content) > 100, "seed.sql is empty or too short"


def test_all_tables_defined():
    """Verify all 8 required tables are created in schema.sql."""
    with open(SCHEMA_SQL_PATH, "r", encoding="utf-8") as f:
        content = f.read().lower()

    for table in EXPECTED_TABLES:
        pattern = rf"create\s+table\s+{table}\b"
        assert re.search(pattern, content), f"Table '{table}' not found in schema.sql"


def test_foreign_keys_and_collision_constraint():
    """Verify critical foreign keys and appointment collision constraints."""
    with open(SCHEMA_SQL_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    # Foreign key checks
    assert "REFERENCES users(id)" in content, "Missing foreign key to users(id)"
    assert "REFERENCES vehicles(id)" in content, "Missing foreign key to vehicles(id)"
    assert "REFERENCES service_centers(center_id)" in content, "Missing foreign key to service_centers(center_id)"
    assert "REFERENCES appointments(id)" in content, "Missing foreign key to appointments(id)"

    # Collision check constraint
    assert "uq_appointment_slot UNIQUE (service_center_id, appointment_date, appointment_time)" in content, \
        "Missing unique appointment collision constraint"


def test_seed_data_integrity():
    """Verify seed.sql contains realistic records for Rahul and Tata Nexon."""
    with open(SEED_SQL_PATH, "r", encoding="utf-8") as f:
        seed = f.read()

    assert "Rahul" in seed, "Seed data missing user 'Rahul'"
    assert "Tata" in seed and "Nexon" in seed, "Seed data missing Tata Nexon"
    assert "9800" in seed, "Seed data missing current mileage 9,800 km"
    assert "5000" in seed, "Seed data missing last service mileage 5,000 km"
    assert "APPROACHING" in seed, "Seed data missing APPROACHING status record"
    assert "osm_101" in seed and "osm_102" in seed, "Seed data missing stable service center IDs"


if __name__ == "__main__":
    print("Running database schema & seed integrity tests...")
    test_schema_file_exists()
    print("[PASS] schema.sql exists")
    test_seed_file_exists()
    print("[PASS] seed.sql exists")
    test_all_tables_defined()
    print("[PASS] All 8 required tables present")
    test_foreign_keys_and_collision_constraint()
    print("[PASS] Foreign keys and collision constraint present")
    test_seed_data_integrity()
    print("[PASS] Seed data integrity verified")
