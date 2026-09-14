-- ============================================================
-- Vehicle Service & Maintenance Management Agent
-- Database Schema for Supabase PostgreSQL
-- ============================================================

-- Drop tables if they already exist (in reverse dependency order)
DROP TABLE IF EXISTS notifications CASCADE;
DROP TABLE IF EXISTS appointments CASCADE;
DROP TABLE IF EXISTS service_centers CASCADE;
DROP TABLE IF EXISTS maintenance_records CASCADE;
DROP TABLE IF EXISTS maintenance_schedules CASCADE;
DROP TABLE IF EXISTS service_history CASCADE;
DROP TABLE IF EXISTS vehicles CASCADE;
DROP TABLE IF EXISTS users CASCADE;

-- 1. users table
CREATE TABLE users (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(150) UNIQUE NOT NULL,
    phone VARCHAR(20),
    location VARCHAR(200),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. vehicles table
CREATE TABLE vehicles (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    make VARCHAR(50) NOT NULL,
    model VARCHAR(50) NOT NULL,
    variant VARCHAR(50),
    year INT,
    registration_number VARCHAR(50) UNIQUE NOT NULL,
    current_mileage INT NOT NULL,
    last_service_date DATE NOT NULL,
    last_service_mileage INT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. service_history table
CREATE TABLE service_history (
    id BIGSERIAL PRIMARY KEY,
    vehicle_id BIGINT NOT NULL REFERENCES vehicles(id) ON DELETE CASCADE,
    service_date DATE NOT NULL,
    service_mileage INT NOT NULL,
    service_type VARCHAR(100) NOT NULL,
    description TEXT,
    cost NUMERIC(10, 2),
    service_center VARCHAR(150) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 4. maintenance_schedules table
CREATE TABLE maintenance_schedules (
    id BIGSERIAL PRIMARY KEY,
    vehicle_id BIGINT NOT NULL REFERENCES vehicles(id) ON DELETE CASCADE,
    service_type VARCHAR(100) NOT NULL,
    interval_km INT NOT NULL,
    interval_months INT NOT NULL,
    last_service_mileage INT NOT NULL,
    last_service_date DATE NOT NULL
);

-- 5. maintenance_records table
CREATE TABLE maintenance_records (
    id BIGSERIAL PRIMARY KEY,
    vehicle_id BIGINT NOT NULL REFERENCES vehicles(id) ON DELETE CASCADE,
    maintenance_type VARCHAR(100) NOT NULL,
    status VARCHAR(50) NOT NULL, -- NOT_DUE, APPROACHING, DUE, OVERDUE
    due_date DATE,
    due_mileage INT,
    completed_date DATE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 6. service_centers table
CREATE TABLE service_centers (
    id BIGSERIAL PRIMARY KEY,
    center_id VARCHAR(100) UNIQUE NOT NULL,
    name VARCHAR(200) NOT NULL,
    address TEXT NOT NULL,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    phone VARCHAR(50)
);

-- 7. appointments table
CREATE TABLE appointments (
    id BIGSERIAL PRIMARY KEY,
    vehicle_id BIGINT NOT NULL REFERENCES vehicles(id) ON DELETE CASCADE,
    service_center_id VARCHAR(100) NOT NULL REFERENCES service_centers(center_id) ON DELETE CASCADE,
    appointment_date DATE NOT NULL,
    appointment_time VARCHAR(20) NOT NULL,
    service_type VARCHAR(100) NOT NULL,
    status VARCHAR(50) DEFAULT 'CONFIRMED',
    booking_reference VARCHAR(50) UNIQUE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    -- Collision prevention constraint
    CONSTRAINT uq_appointment_slot UNIQUE (service_center_id, appointment_date, appointment_time)
);

-- 8. notifications table
CREATE TABLE notifications (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    appointment_id BIGINT REFERENCES appointments(id) ON DELETE SET NULL,
    notification_type VARCHAR(50) DEFAULT 'BOOKING_CONFIRMATION',
    message TEXT NOT NULL,
    status VARCHAR(50) DEFAULT 'SENT',
    sent_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for frequent lookups
CREATE INDEX idx_vehicles_user_id ON vehicles(user_id);
CREATE INDEX idx_service_history_vehicle_id ON service_history(vehicle_id);
CREATE INDEX idx_maintenance_schedules_vehicle_id ON maintenance_schedules(vehicle_id);
CREATE INDEX idx_appointments_vehicle_id ON appointments(vehicle_id);
CREATE INDEX idx_appointments_booking_ref ON appointments(booking_reference);
CREATE INDEX idx_notifications_user_id ON notifications(user_id);
