-- Seed Data for Vehicle Maintenance & Service Management System

-- Insert primary user
INSERT INTO users (id, name, email, phone, location)
VALUES (1, 'Rahul', 'jaxiver377@gmail.com', '+91 9876543210', 'Indiranagar, Bangalore')
ON CONFLICT (id) DO NOTHING;

-- Insert vehicles including Rahul's Tata Nexon
INSERT INTO vehicles (id, user_id, label, make, model, variant, year, registration_number, current_mileage, last_service_date, last_service_mileage)
VALUES 
(1, 1, 'Vehicle A', 'Tata', 'Nexon', 'XZ+ Petrol', 2023, 'KA-01-MJ-2023', 9800, '2024-03-15', 5000),
(2, 1, 'Vehicle B', 'Tata', 'Punch', 'Creative Petrol', 2022, 'KA-05-TP-2468', 18400, '2024-08-12', 15000)
ON CONFLICT (id) DO NOTHING;

-- Insert service centers with stable IDs
INSERT INTO service_centers (id, center_id, name, brand, city, address, latitude, longitude, phone, rating)
VALUES
(1, 'osm_101', 'Tata Motors Authorized Service - Prerana Motors', 'Tata', 'Bangalore', 'Hosur Main Road, Kudlu Gate, Bangalore', 12.8912, 77.6411, '+91 80 67673344', 4.6),
(2, 'osm_102', 'Tata Motors Authorized Service - ABC Motors', 'Tata', 'Bangalore', '12th Main Road, Indiranagar, Bangalore', 12.9716, 77.5946, '+91 80 25251122', 4.8)
ON CONFLICT (center_id) DO NOTHING;

-- Insert maintenance schedule
INSERT INTO maintenance_schedules (id, vehicle_id, service_type, interval_km, interval_months, last_service_mileage, last_service_date)
VALUES
(1, 1, 'Periodic Maintenance Service', 5000, 6, 5000, '2024-03-15')
ON CONFLICT (vehicle_id) DO NOTHING;

-- Insert maintenance record with APPROACHING status
INSERT INTO maintenance_records (id, vehicle_id, maintenance_status, remaining_km, target_service_date)
VALUES
(1, 1, 'APPROACHING', 200, '2024-09-15')
ON CONFLICT (id) DO NOTHING;
