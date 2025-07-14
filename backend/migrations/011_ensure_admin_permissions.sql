-- Migration: Ensure Admin Permissions

-- Grant elevated privileges to db_user (removed SUPERUSER)
-- ALTER ROLE %(db_user)s WITH SUPERUSER;

-- Ensure all tables are accessible
GRANT ALL PRIVILEGES ON DATABASE %(db_name)s TO %(db_user)s;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO %(db_user)s;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO %(db_user)s;
GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA public TO %(db_user)s;

-- Ensure role can create and manage roles
-- ALTER ROLE %(db_user)s WITH CREATEROLE;

-- Create a function to ensure the db_user is the owner of all database objects
DO $$
BEGIN
    -- Make db_user the owner of all tables
    EXECUTE (
        SELECT 'ALTER TABLE ' || quote_ident(tablename) || ' OWNER TO %(db_user)s;'
        FROM pg_tables
        WHERE schemaname = 'public'
    );
    
    -- Make db_user the owner of all sequences
    EXECUTE (
        SELECT 'ALTER SEQUENCE ' || quote_ident(sequencename) || ' OWNER TO %(db_user)s;'
        FROM pg_sequences
        WHERE schemaname = 'public'
    );
    
    -- Make db_user the owner of all functions
    EXECUTE (
        SELECT 'ALTER FUNCTION ' || quote_ident(proname) || '(' || 
               pg_get_function_arguments(p.oid) || ') OWNER TO %(db_user)s;'
        FROM pg_proc p
        JOIN pg_namespace n ON p.pronamespace = n.oid
        WHERE n.nspname = 'public'
    );
EXCEPTION WHEN OTHERS THEN
    -- Log error but continue
    RAISE NOTICE 'Error setting ownership: %%', SQLERRM;
END $$; 
