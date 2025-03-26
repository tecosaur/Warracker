#!/usr/bin/env python3
import os
import glob
import psycopg2
import logging
import time
import sys

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

def get_db_connection(max_attempts=5, attempt_delay=5):
    """Get a connection to the PostgreSQL database with retry logic"""
    for attempt in range(1, max_attempts + 1):
        try:
            logger.info(f"Attempting to connect to database (attempt {attempt}/{max_attempts})")
            
            # Get connection details from environment variables or use defaults
            db_host = os.environ.get('DB_HOST', 'localhost')
            db_port = os.environ.get('DB_PORT', '5432')
            db_name = os.environ.get('DB_NAME', 'warranty_db')
            db_user = os.environ.get('DB_USER', 'warranty_user')
            db_password = os.environ.get('DB_PASSWORD', 'warranty_password')
            
            conn = psycopg2.connect(
                host=db_host,
                port=db_port,
                dbname=db_name,
                user=db_user,
                password=db_password
            )
            
            # Set autocommit to False for transaction control
            conn.autocommit = False
            
            logger.info("Database connection successful")
            return conn
            
        except Exception as e:
            logger.error(f"Database connection error (attempt {attempt}/{max_attempts}): {e}")
            
            if attempt < max_attempts:
                logger.info(f"Retrying in {attempt_delay} seconds...")
                time.sleep(attempt_delay)
            else:
                logger.error("Maximum connection attempts reached. Could not connect to database.")
                raise

def apply_migrations():
    """Apply all SQL migration files in the migrations directory"""
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Create migrations table if it doesn't exist
        cur.execute("""
            CREATE TABLE IF NOT EXISTS migrations (
                id SERIAL PRIMARY KEY,
                filename VARCHAR(255) NOT NULL UNIQUE,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        
        # Get list of migration files
        migration_dir = os.path.dirname(os.path.abspath(__file__))
        migration_files = sorted(glob.glob(os.path.join(migration_dir, '*.sql')))
        
        if not migration_files:
            logger.info("No migration files found.")
            return
        
        # Get list of already applied migrations
        cur.execute("SELECT filename FROM migrations")
        applied_migrations = set([row[0] for row in cur.fetchall()])
        
        # Apply each migration file if not already applied
        for migration_file in migration_files:
            filename = os.path.basename(migration_file)
            
            if filename in applied_migrations:
                logger.info(f"Migration {filename} already applied, skipping.")
                continue
            
            logger.info(f"Applying migration: {filename}")
            
            try:
                # Read and execute the SQL file
                with open(migration_file, 'r') as f:
                    sql = f.read()
                
                cur.execute(sql)
                
                # Record the migration as applied
                cur.execute(
                    "INSERT INTO migrations (filename) VALUES (%s)",
                    (filename,)
                )
                
                conn.commit()
                logger.info(f"Migration {filename} applied successfully")
                
            except Exception as e:
                conn.rollback()
                logger.error(f"Error applying migration {filename}: {e}")
                logger.error(f"\nQUERY: {sql}\n")
                raise
        
    except Exception as e:
        logger.error(f"Migration error: {e}")
        if conn:
            conn.rollback()
        raise
        
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    try:
        apply_migrations()
        logger.info("Migrations completed successfully")
    except Exception as e:
        logger.error(f"Migration process failed: {e}")
        sys.exit(1) 