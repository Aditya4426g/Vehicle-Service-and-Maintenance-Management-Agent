-- ============================================================
-- Vehicle Service & Maintenance Management Agent
-- Seed Data for Supabase PostgreSQL
-- ============================================================

-- 1. Seed user (Rahul)
INSERT INTO users (id, name, email, phone, location)
VALUES (
    1,
    'Rahul',
    'rahul@example.com',
    '+91 9876543210',
    'Indiranagar, Bangalore'
) ON CONFLICT (id) DO NOTHING;

-- 2. Seed vehicle (Tata Nexon)
-- Current mileage: 9,800 km, Last service: 5,000 km, Service interval: 5,000 km
INSERT INTO vehicles (
    id,
    user_id,
    make,
    model,
    variant,
    year,
    registration_number,
    current_mileage,
    last_service_date,
    last_service_mileage
)
VALUES (
    1,
    1,
    'Tata',
    'Nexon',
    'XZ+ Petrol',
    2023,
    'KA-01-MJ-2023',
    9800,
    '2024-03-15',
    5000
) ON CONFLICT (id) DO NOTHING;

-- 3. Seed service history
INSERT INTO service_history (
    id,
    vehicle_id,
    service_date,
    service_mileage,
    service_type,
    description,
    cost,
    service_center
)
VALUES
(
    1,
    1,
    '2023-09-10',
    1000,
    '1st Free Inspection',
    'General inspection, fluid top-up, wash',
    0.00,
    'ABC Motors Tata Authorized'
),
(
    2,
    1,
    '2024-03-15',
    5000,
    'Periodic Maintenance Service',
    'Engine oil change, oil filter replacement, brake inspection',
    2850.00,
    'XYZ Auto Care Service Center'
) ON CONFLICT (id) DO NOTHING;

-- 4. Seed maintenance schedules
INSERT INTO maintenance_schedules (
    id,
    vehicle_id,
    service_type,
    interval_km,
    interval_months,
    last_service_mileage,
    last_service_date
)
VALUES (
    1,
    1,
    'Periodic Maintenance Service',
    5000,
    6,
    5000,
    '2024-03-15'
) ON CONFLICT (id) DO NOTHING;

-- 5. Seed maintenance record (Current status: APPROACHING)
INSERT INTO maintenance_records (
    id,
    vehicle_id,
    maintenance_type,
    status,
    due_date,
    due_mileage
)
VALUES (
    1,
    1,
    'Periodic Maintenance Service',
    'APPROACHING',
    '2024-09-15',
    10000
) ON CONFLICT (id) DO NOTHING;

-- 6. Seed service centers with stable center_id
INSERT INTO service_centers (
    id,
    center_id,
    name,
    address,
    latitude,
    longitude,
    phone
)
VALUES
(
    1,
    'osm_101',
    'ABC Motors Tata Authorized',
    '12th Main Road, Indiranagar, Bangalore',
    12.9716,
    77.5946,
    '+91 80 25251122'
),
(
    2,
    'osm_102',
    'XYZ Auto Care Service Center',
    '80 Feet Road, Koramangala, Bangalore',
    12.9352,
    77.6245,
    '+91 80 41412233'
),
(
    3,
    'osm_103',
    'Prerana Motors Tata Service',
    'Hosur Main Road, Kudlu Gate, Bangalore',
    12.8912,
    77.6411,
    '+91 80 67673344'
) ON CONFLICT (id) DO NOTHING;

-- 7. Seed past appointment
INSERT INTO appointments (
    id,
    vehicle_id,
    service_center_id,
    appointment_date,
    appointment_time,
    service_type,
    status,
    booking_reference
)
VALUES (
    1,
    1,
    'osm_102',
    '2024-03-15',
    '10:00 AM',
    'Periodic Maintenance Service',
    'COMPLETED',
    'BK09990'
) ON CONFLICT (id) DO NOTHING;

-- 8. Seed sample notification
INSERT INTO notifications (
    id,
    user_id,
    appointment_id,
    notification_type,
    message,
    status
)
VALUES (
    1,
    1,
    1,
    'BOOKING_CONFIRMATION',
    'Your service appointment for Tata Nexon was confirmed for 15 Mar 2024 at 10:00 AM.',
    'SENT'
) ON CONFLICT (id) DO NOTHING;

-- Reset sequence IDs for serial primary keys
SELECT setval(pg_get_serial_sequence('users', 'id'), coalesce(max(id), 1)) FROM users;
SELECT setval(pg_get_serial_sequence('vehicles', 'id'), coalesce(max(id), 1)) FROM vehicles;
SELECT setval(pg_get_serial_sequence('service_history', 'id'), coalesce(max(id), 1)) FROM service_history;
SELECT setval(pg_get_serial_sequence('maintenance_schedules', 'id'), coalesce(max(id), 1)) FROM maintenance_schedules;
SELECT setval(pg_get_serial_sequence('maintenance_records', 'id'), coalesce(max(id), 1)) FROM maintenance_records;
SELECT setval(pg_get_serial_sequence('service_centers', 'id'), coalesce(max(id), 1)) FROM service_centers;
SELECT setval(pg_get_serial_sequence('appointments', 'id'), coalesce(max(id), 1)) FROM appointments;
SELECT setval(pg_get_serial_sequence('notifications', 'id'), coalesce(max(id), 1)) FROM notifications;
