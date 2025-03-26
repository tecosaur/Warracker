-- backend/init.sql

-- Grant superuser privileges to warranty_user
ALTER ROLE warranty_user WITH SUPERUSER;

-- Create migrations tracking table
CREATE TABLE IF NOT EXISTS migrations (
    id SERIAL PRIMARY KEY,
    filename VARCHAR(255) NOT NULL UNIQUE,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert records for migrations applied in this script
INSERT INTO migrations (filename) VALUES ('001_add_serial_numbers.sql')
ON CONFLICT (filename) DO NOTHING;
INSERT INTO migrations (filename) VALUES ('002_add_purchase_price.sql')
ON CONFLICT (filename) DO NOTHING;

CREATE TABLE warranties (
    id SERIAL PRIMARY KEY,
    product_name VARCHAR(255) NOT NULL,
    purchase_date DATE NOT NULL,
    warranty_years INTEGER NOT NULL,
    expiration_date DATE,
    invoice_path TEXT,
    manual_path TEXT,
    product_url TEXT,
    purchase_price DECIMAL(10, 2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_expiration_date ON warranties(expiration_date);
CREATE INDEX idx_product_name ON warranties(product_name);

-- Add serial numbers table
CREATE TABLE serial_numbers (
    id SERIAL PRIMARY KEY,
    warranty_id INTEGER NOT NULL,
    serial_number VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (warranty_id) REFERENCES warranties(id) ON DELETE CASCADE
);

CREATE INDEX idx_warranty_id ON serial_numbers(warranty_id);
CREATE INDEX idx_serial_number ON serial_numbers(serial_number);