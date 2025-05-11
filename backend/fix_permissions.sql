-- Script to fix PostgreSQL permissions for warranty_user

-- Grant superuser privileges
ALTER ROLE warranty_user WITH SUPERUSER;

-- Grant role management privileges
ALTER ROLE warranty_user WITH CREATEROLE;

-- Ensure all database objects are accessible
GRANT ALL PRIVILEGES ON DATABASE %(db_name)s TO warranty_user;
GRANT ALL PRIVILEGES ON SCHEMA public TO warranty_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO warranty_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO warranty_user;
GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA public TO warranty_user;

-- Make warranty_user the owner of all tables
DO $$
DECLARE
    rec RECORD;
BEGIN
    FOR rec IN SELECT tablename FROM pg_tables WHERE schemaname = 'public'
    LOOP
        EXECUTE 'ALTER TABLE public.' || quote_ident(rec.tablename) || ' OWNER TO warranty_user';
    END LOOP;
END $$;

-- Make warranty_user the owner of all sequences
DO $$
DECLARE
    rec RECORD;
BEGIN
    FOR rec IN SELECT sequencename FROM pg_sequences WHERE schemaname = 'public'
    LOOP
        EXECUTE 'ALTER SEQUENCE public.' || quote_ident(rec.sequencename) || ' OWNER TO warranty_user';
    END LOOP;
END $$;

-- Make warranty_user the owner of all functions
DO $$
DECLARE
    rec RECORD;
BEGIN
    FOR rec IN SELECT proname, p.oid FROM pg_proc p JOIN pg_namespace n ON p.pronamespace = n.oid WHERE n.nspname = 'public'
    LOOP
        BEGIN
            EXECUTE 'ALTER FUNCTION public.' || quote_ident(rec.proname) || '(' || pg_get_function_arguments(rec.oid) || ') OWNER TO warranty_user';
        EXCEPTION WHEN OTHERS THEN
            RAISE NOTICE 'Error changing ownership of function %%: %%', rec.proname, SQLERRM;
        END;
    END LOOP;
END $$; 
