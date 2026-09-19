-- schema_kos.sql
-- Database schema for Sistem Manajemen Internal Kos

DROP TABLE IF EXISTS audit_logs CASCADE;
DROP TABLE IF EXISTS dokumen_penghuni CASCADE;
DROP TABLE IF EXISTS checkin_checkout CASCADE;
DROP TABLE IF EXISTS maintenance_logs CASCADE;
DROP TABLE IF EXISTS maintenance_tasks CASCADE;
DROP TABLE IF EXISTS keluhan CASCADE;
DROP TABLE IF EXISTS pembayaran CASCADE;
DROP TABLE IF EXISTS tagihan CASCADE;
DROP TABLE IF EXISTS kontrak_sewa CASCADE;
DROP TABLE IF EXISTS inventaris CASCADE;
DROP TABLE IF EXISTS kamar CASCADE;
DROP TABLE IF EXISTS lokasi_kos CASCADE;
DROP TABLE IF EXISTS penghuni CASCADE;
DROP TABLE IF EXISTS users CASCADE;
DROP TABLE IF EXISTS roles CASCADE;

CREATE TABLE roles (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE
);

INSERT INTO roles (name) VALUES ('Owner'), ('Admin'), ('Teknisi');

CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role_id INT NOT NULL REFERENCES roles(id),
    status VARCHAR(20) DEFAULT 'ACTIVE', -- ACTIVE/INACTIVE
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE lokasi_kos (
    id SERIAL PRIMARY KEY,
    nama_lokasi VARCHAR(100) NOT NULL,
    alamat TEXT
);

INSERT INTO lokasi_kos (nama_lokasi, alamat) VALUES 
('Gimina Kost Jatinangor', 'Jatinangor, Sumedang'),
('Gimina Kost Gunung Batu', 'Gunung Batu, Bandung');

CREATE TABLE penghuni (
    id SERIAL PRIMARY KEY,
    full_name VARCHAR(150) NOT NULL,
    nik VARCHAR(50) UNIQUE,
    phone VARCHAR(20) NOT NULL,
    email VARCHAR(100) UNIQUE,
    password_hash TEXT,
    origin_address TEXT,
    occupation VARCHAR(100),
    preferred_location_id INT REFERENCES lokasi_kos(id),
    status VARCHAR(20) DEFAULT 'PENDING', -- PENDING/ACTIVE/INACTIVE/REJECTED
    verified_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE kamar (
    id SERIAL PRIMARY KEY,
    location_id INT NOT NULL REFERENCES lokasi_kos(id),
    room_number VARCHAR(20) NOT NULL,
    room_type VARCHAR(50),
    monthly_rate DECIMAL(12, 2) NOT NULL,
    status VARCHAR(20) DEFAULT 'AVAILABLE', -- AVAILABLE/OCCUPIED/MAINTENANCE
    facilities TEXT,
    notes TEXT,
    UNIQUE(location_id, room_number)
);

CREATE TABLE inventaris (
    id SERIAL PRIMARY KEY,
    location_id INT NOT NULL REFERENCES lokasi_kos(id),
    nama_barang VARCHAR(150) NOT NULL,
    jumlah INT NOT NULL DEFAULT 1,
    kondisi VARCHAR(50) DEFAULT 'Baik', -- Baik/Rusak/Perbaikan
    keterangan TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE kontrak_sewa (
    id SERIAL PRIMARY KEY,
    tenant_id INT NOT NULL REFERENCES penghuni(id),
    room_id INT NOT NULL REFERENCES kamar(id),
    start_date DATE NOT NULL,
    end_date DATE,
    monthly_rate DECIMAL(12, 2) NOT NULL,
    due_day INT CHECK (due_day BETWEEN 1 AND 31),
    status VARCHAR(20) DEFAULT 'ACTIVE' -- ACTIVE/ENDED/CANCELLED
);

CREATE TABLE tagihan (
    id SERIAL PRIMARY KEY,
    contract_id INT NOT NULL REFERENCES kontrak_sewa(id),
    period VARCHAR(20) NOT NULL, -- e.g., '2023-08'
    amount DECIMAL(12, 2) NOT NULL,
    due_date DATE NOT NULL,
    status VARCHAR(20) DEFAULT 'UNPAID' -- UNPAID/PENDING/PAID/OVERDUE
);

CREATE TABLE pembayaran (
    id SERIAL PRIMARY KEY,
    invoice_id INT NOT NULL REFERENCES tagihan(id),
    paid_at TIMESTAMP,
    amount DECIMAL(12, 2) NOT NULL,
    method VARCHAR(50),
    proof_url TEXT,
    status VARCHAR(20) DEFAULT 'PENDING' -- PENDING/PAID/REJECTED
);

CREATE TABLE keluhan (
    id SERIAL PRIMARY KEY,
    tenant_id INT NOT NULL REFERENCES penghuni(id),
    room_id INT NOT NULL REFERENCES kamar(id),
    category VARCHAR(50) NOT NULL,
    title VARCHAR(100) NOT NULL,
    description TEXT NOT NULL,
    attachment_url TEXT,
    priority VARCHAR(20) DEFAULT 'NORMAL', -- LOW/NORMAL/HIGH
    status VARCHAR(20) DEFAULT 'NEW', -- NEW/REVIEWED/IN_PROGRESS/RESOLVED/CLOSED/REJECTED
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE maintenance_tasks (
    id SERIAL PRIMARY KEY,
    complaint_id INT NOT NULL REFERENCES keluhan(id),
    technician_id INT REFERENCES users(id),
    assigned_at TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    status VARCHAR(20) DEFAULT 'PENDING'
);

CREATE TABLE maintenance_logs (
    id SERIAL PRIMARY KEY,
    task_id INT NOT NULL REFERENCES maintenance_tasks(id),
    note TEXT,
    cost DECIMAL(12, 2),
    attachment_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE checkin_checkout (
    id SERIAL PRIMARY KEY,
    tenant_id INT NOT NULL REFERENCES penghuni(id),
    room_id INT NOT NULL REFERENCES kamar(id),
    checkin_date DATE NOT NULL,
    checkout_date DATE,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE dokumen_penghuni (
    id SERIAL PRIMARY KEY,
    tenant_id INT NOT NULL REFERENCES penghuni(id),
    document_type VARCHAR(50) NOT NULL, -- e.g., 'KTP', 'KK'
    document_url TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE audit_logs (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(id),
    action VARCHAR(100) NOT NULL,
    table_name VARCHAR(50),
    record_id INT,
    old_data JSON,
    new_data JSON,
    ip_address VARCHAR(45),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE daftar_tunggu (
    id SERIAL PRIMARY KEY,
    lokasi_id INT NOT NULL REFERENCES lokasi_kos(id),
    tipe_kamar VARCHAR(100) NOT NULL,
    nama_lengkap VARCHAR(150) NOT NULL,
    no_hp VARCHAR(20) NOT NULL,
    status_tanggal VARCHAR(50),
    tanggal_masuk DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
