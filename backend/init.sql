-- backend/init.sql

CREATE TABLE warranties (
    id SERIAL PRIMARY KEY,
    product_name VARCHAR(255) NOT NULL,
    purchase_date DATE NOT NULL,
    warranty_years INTEGER NOT NULL,
    expiration_date DATE,
    invoice_path TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_expiration_date ON warranties(expiration_date);
CREATE INDEX idx_product_name ON warranties(product_name);