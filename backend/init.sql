-- backend/init.sql

CREATE TABLE warranties (
    id SERIAL PRIMARY KEY,
    item_name VARCHAR(255) NOT NULL,
    serial_number VARCHAR(255),
    purchase_date DATE,
    expiration_date DATE NOT NULL,
    warranty_provider VARCHAR(255),
    invoice_image VARCHAR(255), -- Filename or path to the uploaded invoice image
    notes TEXT,               -- Any additional notes about the warranty
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Optionally add indexes for faster querying (if needed)
-- CREATE INDEX idx_expiration_date ON warranties (expiration_date);
-- CREATE INDEX idx_item_name ON warranties (item_name);