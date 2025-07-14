-- Migration: Grant CREATEROLE to db_user before admin role configuration

ALTER ROLE %(db_user)s WITH CREATEROLE; 