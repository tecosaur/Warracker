-- Migration: Configure PostgreSQL Admin Role

-- Create a new database role for admin operations
DO $$ 
BEGIN
    -- Check if the admin_role exists, if not create it
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'warracker_admin') THEN
        CREATE ROLE warracker_admin WITH LOGIN PASSWORD 'change_this_password_in_production';
    END IF;
END
$$;

-- Grant privileges to the admin role
GRANT ALL PRIVILEGES ON DATABASE %(db_name)s TO warracker_admin;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO warracker_admin;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO warracker_admin;
GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA public TO warracker_admin;

-- Grant specific role management permissions
ALTER ROLE warracker_admin WITH CREATEROLE;

-- Ensure the warranty_user can still access all application tables
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO warranty_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO warranty_user;
GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA public TO warranty_user;

-- Make warracker_admin the owner of all existing users
-- Note: This would require superuser privileges to execute
-- ALTER ROLE warranty_user OWNER TO warracker_admin; 
