# backend/db_handler.py
import os
import psycopg2
from psycopg2 import pool
import logging
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional

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

def get_site_setting(setting_name: str, default_value: str = '') -> str:
    """Get a site setting value from the database"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT value FROM site_settings WHERE key = %s",
            (setting_name,)
        )
        result = cursor.fetchone()
        cursor.close()
        
        if result:
            return result[0] if result[0] is not None else default_value
        return default_value
        
    except Exception as e:
        logger.error(f"Error getting site setting {setting_name}: {e}")
        return default_value
    finally:
        if conn:
            release_db_connection(conn)

def get_expiring_warranties(days: int) -> List[Dict]:
    """Get warranties expiring within the specified number of days"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Calculate the date range
        today = datetime.now().date()
        end_date = today + timedelta(days=days)
        
        # Query for non-lifetime warranties expiring within the specified days
        # Include warranties expiring from today up to the target date
        cursor.execute("""
            SELECT 
                id, product_name, expiration_date, user_id,
                purchase_date, vendor, warranty_type, notes
            FROM warranties 
            WHERE is_lifetime = false 
            AND expiration_date BETWEEN %s AND %s
            ORDER BY user_id, expiration_date, product_name
        """, (today, end_date))
        
        results = cursor.fetchall()
        cursor.close()
        
        warranties = []
        for row in results:
            warranty = {
                'id': row[0],
                'product_name': row[1],
                'expiration_date': row[2].isoformat() if row[2] else None,
                'user_id': row[3],
                'purchase_date': row[4].isoformat() if row[4] else None,
                'vendor': row[5],
                'warranty_type': row[6],
                'notes': row[7]
            }
            warranties.append(warranty)
        
        logger.info(f"Found {len(warranties)} warranties expiring in {days} days")
        return warranties
        
    except Exception as e:
        logger.error(f"Error getting expiring warranties for {days} days: {e}")
        return []
    finally:
        if conn:
            release_db_connection(conn)

def get_all_expiring_warranties(max_days: int = 30) -> Dict[int, List[Dict]]:
    """Get all warranties expiring within max_days, grouped by days until expiration"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        today = datetime.now().date()
        max_date = today + timedelta(days=max_days)
        
        cursor.execute("""
            SELECT 
                id, product_name, expiration_date, user_id,
                purchase_date, vendor, warranty_type, notes,
                (expiration_date - %s) as days_until_expiry
            FROM warranties 
            WHERE is_lifetime = false 
            AND expiration_date BETWEEN %s AND %s
            ORDER BY expiration_date, product_name
        """, (today, today, max_date))
        
        results = cursor.fetchall()
        cursor.close()
        
        # Group by days until expiry
        grouped_warranties = {}
        for row in results:
            days_until = row[8].days if row[8] else 0
            
            if days_until not in grouped_warranties:
                grouped_warranties[days_until] = []
            
            warranty = {
                'id': row[0],
                'product_name': row[1],
                'expiration_date': row[2].isoformat() if row[2] else None,
                'user_id': row[3],
                'purchase_date': row[4].isoformat() if row[4] else None,
                'vendor': row[5],
                'warranty_type': row[6],
                'notes': row[7],
                'days_until_expiry': days_until
            }
            grouped_warranties[days_until].append(warranty)
        
        return grouped_warranties
        
    except Exception as e:
        logger.error(f"Error getting all expiring warranties: {e}")
        return {}
    finally:
        if conn:
            release_db_connection(conn)

def update_site_setting(setting_name: str, setting_value: str) -> bool:
    """Update a site setting in the database"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO site_settings (key, value) 
            VALUES (%s, %s)
            ON CONFLICT (key) 
            DO UPDATE SET value = EXCLUDED.value, updated_at = CURRENT_TIMESTAMP
        """, (setting_name, setting_value))
        
        conn.commit()
        cursor.close()
        return True
        
    except Exception as e:
        logger.error(f"Error updating site setting {setting_name}: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            release_db_connection(conn) 