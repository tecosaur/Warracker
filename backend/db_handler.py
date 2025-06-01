# backend/db_handler.py
import os
import psycopg2
from psycopg2 import pool
import logging
import time

logger = logging.getLogger(__name__)

# PostgreSQL connection details
DB_HOST = os.environ.get('DB_HOST', 'warrackerdb')
DB_NAME = os.environ.get('DB_NAME', 'warranty_db')
DB_USER = os.environ.get('DB_USER', 'warranty_user')
DB_PASSWORD = os.environ.get('DB_PASSWORD', 'warranty_password')

connection_pool = None # Global connection pool for this module

def init_db_pool(max_retries=5, retry_delay=5):
    global connection_pool # Ensure we're modifying the global variable in this module
    attempt = 0
    last_exception = None
    
    if connection_pool is not None:
        logger.info("[DB_HANDLER] Database connection pool already initialized.")
        return connection_pool

    while attempt < max_retries:
        try:
            logger.info(f"[DB_HANDLER] Attempting to initialize database pool (attempt {attempt+1}/{max_retries})")
            # Optimized connection pool for memory efficiency
            connection_pool = pool.SimpleConnectionPool(
                1, 4, # Reduced from 1,10 to 1,4 for memory efficiency
                host=DB_HOST,
                database=DB_NAME,
                user=DB_USER,
                password=DB_PASSWORD,
                # Memory optimization settings
                connect_timeout=10,  # Connection timeout
                application_name='warracker_optimized'  # Identify connections
            )
            logger.info("[DB_HANDLER] Database connection pool initialized successfully.")
            return connection_pool # Return the pool for external check if needed
        except Exception as e:
            last_exception = e
            logger.error(f"[DB_HANDLER] Database connection pool initialization error: {e}")
            logger.info(f"[DB_HANDLER] Retrying in {retry_delay} seconds...")
            time.sleep(retry_delay)
            attempt += 1
    
    logger.error(f"[DB_HANDLER] Failed to initialize database pool after {max_retries} attempts.")
    if last_exception:
        raise last_exception
    else:
        raise Exception("Unknown error creating database pool")

def get_db_connection():
    global connection_pool
    if connection_pool is None:
        logger.error("[DB_HANDLER] Database connection pool is None. Attempting to re-initialize.")
        init_db_pool() # Attempt to initialize it
        if connection_pool is None: # If still None after attempt
            logger.critical("[DB_HANDLER] CRITICAL: Database pool re-initialization failed.")
            raise Exception("Database connection pool is not initialized and could not be re-initialized.")
    try:
        return connection_pool.getconn()
    except Exception as e:
        logger.error(f"[DB_HANDLER] Error getting connection from pool: {e}")
        raise

def release_db_connection(conn):
    global connection_pool
    if connection_pool:
        try:
            connection_pool.putconn(conn)
        except Exception as e:
            logger.error(f"[DB_HANDLER] Error releasing connection to pool: {e}. Connection state: {conn.closed if conn else 'N/A'}")
            # If putconn fails, the connection might be broken or the pool is in a bad state.
            # Attempt to close the connection directly as a fallback.
            if conn and not conn.closed:
                try:
                    conn.close()
                    logger.info("[DB_HANDLER] Connection closed directly after putconn failure.")
                except Exception as close_err:
                    logger.error(f"[DB_HANDLER] Error closing connection directly after putconn failed: {close_err}")
    else:
        logger.warning("[DB_HANDLER] Connection pool is None, cannot release connection to pool. Attempting to close directly.")
        if conn and not conn.closed:
            try:
                conn.close()
            except Exception as e:
                logger.error(f"[DB_HANDLER] Error closing connection directly (pool was None): {e}") 