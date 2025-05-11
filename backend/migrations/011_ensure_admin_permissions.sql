-- Migration: Ensure Admin Permissions

-- Grant superuser privileges to warranty_user
ALTER ROLE warranty_user WITH SUPERUSER;

-- Ensure all tables are accessible
GRANT ALL PRIVILEGES ON DATABASE %(db_name)s TO warranty_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO warranty_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO warranty_user;
GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA public TO warranty_user;

-- Ensure role can create and manage roles
ALTER ROLE warranty_user WITH CREATEROLE;

-- Create a function to ensure the warranty_user is the owner of all database objects
DO $$
BEGIN
    -- Make warranty_user the owner of all tables
    EXECUTE (
        SELECT 'ALTER TABLE ' || quote_ident(tablename) || ' OWNER TO warranty_user;'
        FROM pg_tables
        WHERE schemaname = 'public'
    );
    
    -- Make warranty_user the owner of all sequences
    EXECUTE (
        SELECT 'ALTER SEQUENCE ' || quote_ident(sequencename) || ' OWNER TO warranty_user;'
        FROM pg_sequences
        WHERE schemaname = 'public'
    );
    
    -- Make warranty_user the owner of all functions
    EXECUTE (
        SELECT 'ALTER FUNCTION ' || quote_ident(proname) || '(' || 
               pg_get_function_arguments(p.oid) || ') OWNER TO warranty_user;'
        FROM pg_proc p
        JOIN pg_namespace n ON p.pronamespace = n.oid
        WHERE n.nspname = 'public'
    );
EXCEPTION WHEN OTHERS THEN
    -- Log error but continue
    RAISE NOTICE 'Error setting ownership: %%', SQLERRM;
END $$; 
