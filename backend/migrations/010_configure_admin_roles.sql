-- Migration: Configure PostgreSQL Admin Role

-- Create a new database role for admin operations
DO $$ 
BEGIN
    -- Check if the db_admin_user exists, if not create it
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '%(db_admin_user)s') THEN
        CREATE ROLE %(db_admin_user)s WITH LOGIN PASSWORD '%(db_admin_password)s';
    END IF;
END
$$;

-- Grant privileges to the admin role
GRANT ALL PRIVILEGES ON DATABASE %(db_name)s TO %(db_admin_user)s;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO %(db_admin_user)s;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO %(db_admin_user)s;
GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA public TO %(db_admin_user)s;

-- Grant specific role management permissions
ALTER ROLE %(db_admin_user)s WITH CREATEROLE;

-- Ensure the db_user can still access all application tables
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO %(db_user)s;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO %(db_user)s;
GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA public TO %(db_user)s;

-- Make db_admin_user the owner of all existing users
-- Note: This would require superuser privileges to execute
-- ALTER ROLE %(db_user)s OWNER TO %(db_admin_user)s; 
