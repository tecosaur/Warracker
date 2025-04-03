-- backend/init.sql

-- Grant superuser privileges to warranty_user
ALTER ROLE warranty_user WITH SUPERUSER;

-- The rest of the file content (CREATE TABLE, INSERT INTO) should be removed.
-- The migration system (apply_migrations.py) will handle table creation.