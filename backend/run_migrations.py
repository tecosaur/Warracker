#!/usr/bin/env python3
import os
import sys
import psycopg2
import logging
from psycopg2 import pool
import time

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

def run_migrations():
    """Run all migration scripts in order"""
    conn = None
    try:
        conn = create_db_connection()
        conn.autocommit = False
        cursor = conn.cursor()
        
        # Get list of migration files
        migration_dir = os.path.join(os.path.dirname(__file__), 'migrations')
        migration_files = sorted([f for f in os.listdir(migration_dir) if f.endswith('.sql')])
        
        # Create migrations table if it doesn't exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS migrations (
                id SERIAL PRIMARY KEY,
                filename VARCHAR(255) NOT NULL UNIQUE,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Get already applied migrations
        cursor.execute('SELECT filename FROM migrations')
        applied_migrations = {row[0] for row in cursor.fetchall()}
        
        # Apply new migrations
        for migration_file in migration_files:
            if migration_file in applied_migrations:
                logger.info(f"Migration {migration_file} already applied, skipping")
                continue
                
            logger.info(f"Applying migration: {migration_file}")
            migration_path = os.path.join(migration_dir, migration_file)
            
            with open(migration_path, 'r') as f:
                migration_sql = f.read()
                
            try:
                cursor.execute(migration_sql)
                cursor.execute('INSERT INTO migrations (filename) VALUES (%s)', (migration_file,))
                logger.info(f"Migration {migration_file} applied successfully")
            except Exception as e:
                conn.rollback()
                logger.error(f"Error applying migration {migration_file}: {e}")
                raise
        
        conn.commit()
        logger.info("All migrations applied successfully")
        
    except Exception as e:
        logger.error(f"Migration error: {e}")
        if conn:
            conn.rollback()
        sys.exit(1)
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    run_migrations() 