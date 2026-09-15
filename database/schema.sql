-- Database Schema for Vehicle Maintenance & Service Management System

CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(150) UNIQUE NOT NULL,
    phone VARCHAR(20),
    location VARCHAR(200),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE vehicles (
    id SERIAL PRIMARY KEY,
    user_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    label VARCHAR(50),
    make VARCHAR(50) NOT NULL,
    model VARCHAR(50) NOT NULL,
    variant VARCHAR(100),
    year INT,
    registration_number VARCHAR(30) UNIQUE NOT NULL,
    current_mileage INT NOT NULL DEFAULT 0,
    last_service_date DATE,
    last_service_mileage INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE service_history (
    id SERIAL PRIMARY KEY,
    vehicle_id INT NOT NULL REFERENCES vehicles(id) ON DELETE CASCADE,
    service_date DATE NOT NULL,
    service_mileage INT NOT NULL,
    service_type VARCHAR(100) NOT NULL,
    description TEXT,
    cost NUMERIC(10, 2) DEFAULT 0.0,
    service_center VARCHAR(150),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE maintenance_schedules (
    id SERIAL PRIMARY KEY,
    vehicle_id INT UNIQUE NOT NULL REFERENCES vehicles(id) ON DELETE CASCADE,
    service_type VARCHAR(100) NOT NULL DEFAULT 'Periodic Maintenance Service',
    interval_km INT NOT NULL DEFAULT 5000,
    interval_months INT NOT NULL DEFAULT 6,
    last_service_mileage INT DEFAULT 0,
    last_service_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE maintenance_records (
    id SERIAL PRIMARY KEY,
    vehicle_id INT NOT NULL REFERENCES vehicles(id) ON DELETE CASCADE,
    maintenance_status VARCHAR(50) NOT NULL,
    remaining_km INT,
    target_service_date DATE,
    calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE service_centers (
    id SERIAL PRIMARY KEY,
    center_id VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(150) NOT NULL,
    brand VARCHAR(50) NOT NULL,
    city VARCHAR(100) NOT NULL,
    address TEXT NOT NULL,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    phone VARCHAR(50),
    rating NUMERIC(2, 1) DEFAULT 4.5,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE appointments (
    id SERIAL PRIMARY KEY,
    vehicle_id INT NOT NULL REFERENCES vehicles(id) ON DELETE CASCADE,
    service_center_id VARCHAR(50) NOT NULL REFERENCES service_centers(center_id) ON DELETE CASCADE,
    appointment_date DATE NOT NULL,
    appointment_time VARCHAR(20) NOT NULL,
    service_type VARCHAR(100) NOT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'CONFIRMED',
    booking_reference VARCHAR(50) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_appointment_slot UNIQUE (service_center_id, appointment_date, appointment_time)
);

CREATE TABLE notifications (
    id SERIAL PRIMARY KEY,
    user_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    appointment_id INT REFERENCES appointments(id) ON DELETE SET NULL,
    notification_type VARCHAR(50) NOT NULL,
    message TEXT NOT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'SENT',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
