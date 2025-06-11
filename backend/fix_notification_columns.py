#!/usr/bin/env python3
"""
Fix missing notification columns in user_preferences table.
This script can be run manually to fix the notification column issues.
"""

import os
import psycopg2
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database connection details from environment
DB_HOST = os.environ.get('DB_HOST', 'localhost')
DB_PORT = os.environ.get('DB_PORT', '5432')
DB_NAME = os.environ.get('DB_NAME', 'warranty_db')
DB_USER = os.environ.get('DB_USER', 'warranty_user')
DB_PASSWORD = os.environ.get('DB_PASSWORD', 'warranty_password')

def fix_notification_columns():
    """Fix missing notification columns in user_preferences table."""
    try:
        logger.info("Connecting to database...")
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        conn.autocommit = False
        
        with conn.cursor() as cur:
            logger.info("Checking existing columns...")
            
            # Check what columns exist
            cur.execute("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name='user_preferences' 
                AND column_name IN ('notification_channel', 'apprise_notification_time', 'apprise_notification_frequency')
            """)
            existing_columns = [row[0] for row in cur.fetchall()]
            logger.info(f"Existing notification columns: {existing_columns}")
            
            # Add notification_channel if missing
            if 'notification_channel' not in existing_columns:
                logger.info("Adding notification_channel column...")
                cur.execute("""
                    ALTER TABLE user_preferences 
                    ADD COLUMN notification_channel VARCHAR(10) NOT NULL DEFAULT 'email'
                """)
                logger.info("✓ Added notification_channel column")
            else:
                logger.info("✓ notification_channel column already exists")
            
            # Add apprise_notification_time if missing
            if 'apprise_notification_time' not in existing_columns:
                logger.info("Adding apprise_notification_time column...")
                cur.execute("""
                    ALTER TABLE user_preferences 
                    ADD COLUMN apprise_notification_time VARCHAR(5) NOT NULL DEFAULT '09:00'
                """)
                logger.info("✓ Added apprise_notification_time column")
            else:
                logger.info("✓ apprise_notification_time column already exists")
            
            # Add apprise_notification_frequency if missing
            if 'apprise_notification_frequency' not in existing_columns:
                logger.info("Adding apprise_notification_frequency column...")
                cur.execute("""
                    ALTER TABLE user_preferences 
                    ADD COLUMN apprise_notification_frequency VARCHAR(10) NOT NULL DEFAULT 'daily'
                """)
                logger.info("✓ Added apprise_notification_frequency column")
            else:
                logger.info("✓ apprise_notification_frequency column already exists")
            
            conn.commit()
            logger.info("✅ All notification columns are now properly configured!")
            
    except Exception as e:
        logger.error(f"❌ Error fixing notification columns: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    fix_notification_columns() 