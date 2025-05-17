#!/usr/bin/env python3
import os
import sys
import psycopg2
import logging
import time

from psycopg2.extensions import AsIs

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# PostgreSQL connection details
DB_HOST = os.environ.get('DB_HOST', 'warrackerdb')
DB_NAME = os.environ.get('DB_NAME', 'warranty_db')
DB_USER = os.environ.get('DB_USER', 'warranty_user')
DB_PASSWORD = os.environ.get('DB_PASSWORD', 'warranty_password')

def create_db_connection(max_retries=5, retry_delay=5):
    """Create a database connection with retry logic"""
    attempt = 0
    last_exception = None
    
    while attempt < max_retries:
        try:
            logger.info(f"Attempting to connect to database (attempt {attempt+1}/{max_retries})")
            conn = psycopg2.connect(
                host=DB_HOST,
                database=DB_NAME,
                user=DB_USER,
                password=DB_PASSWORD
            )
            logger.info("Database connection successful")
            return conn
        except Exception as e:
            last_exception = e
            logger.error(f"Database connection error: {e}")
            logger.info(f"Retrying in {retry_delay} seconds...")
            time.sleep(retry_delay)
            attempt += 1
    
    # If we got here, all connection attempts failed
    logger.error(f"Failed to connect to database after {max_retries} attempts")
    raise last_exception

def fix_permissions():
    """Run the fix permissions SQL script"""
    conn = None
    try:
        conn = create_db_connection()
        conn.autocommit = True  # Important for ALTER ROLE commands
        cursor = conn.cursor()
        
        # Read the fix permissions SQL script
        script_path = os.path.join(os.path.dirname(__file__), 'fix_permissions.sql')
        with open(script_path, 'r') as f:
            sql_script = f.read()
        
        # Execute the script
        logger.info("Executing fix permissions SQL script...")
        cursor.execute(
            sql_script,
            {
                "db_name": AsIs(DB_NAME),
                "db_user": AsIs(DB_USER),
            }
        )
        
        logger.info("Permissions fixed successfully")
        
    except Exception as e:
        logger.error(f"Error fixing permissions: {e}")
        sys.exit(1)
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    fix_permissions() 
