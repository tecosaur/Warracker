"""
Warranty Expiration Notification System
Updated: 2025-01-24 - Fixed scheduler initialization in application factory

This module handles all notification-related functionality for the Warracker application,
including email notifications, scheduling, and Apprise integration.
"""

import os
import threading
import time
import atexit
import smtplib
import logging
from datetime import datetime, date, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from threading import Lock
from decimal import Decimal

import pytz
from pytz import timezone as pytz_timezone

try:
    from apscheduler.schedulers.background import BackgroundScheduler
    BACKGROUND_SCHEDULER_AVAILABLE = True
except ImportError:
    BACKGROUND_SCHEDULER_AVAILABLE = False
    BackgroundScheduler = None

try:
    from apscheduler.schedulers.gevent import GeventScheduler
    GEVENT_SCHEDULER_AVAILABLE = True
except ImportError:
    GEVENT_SCHEDULER_AVAILABLE = False
    GeventScheduler = None

# Import database functions
try:
    from .db_handler import get_site_setting
    DB_HANDLER_IMPORTED = True
except ImportError:
    try:
        from db_handler import get_site_setting
        DB_HANDLER_IMPORTED = True
    except ImportError:
        DB_HANDLER_IMPORTED = False
        def get_site_setting(key, default=None):
            return default

# Configure logging
logger = logging.getLogger(__name__)

# Global variables for notification management
notification_lock = threading.Lock()
last_notification_sent = {}
scheduler = None
scheduler_initialized = False
scheduler_retry_attempted = False

# Apprise integration (will be set by app.py if available)
APPRISE_AVAILABLE = False
apprise_handler = None

def set_apprise_handler(handler):
    """Set the Apprise handler if available"""
    global APPRISE_AVAILABLE, apprise_handler
    APPRISE_AVAILABLE = handler is not None
    apprise_handler = handler

def get_expiring_warranties(get_db_connection, release_db_connection):
    """Get warranties that are expiring soon for notification purposes"""
    conn = None
    try:
        # Add retry logic for database connections in scheduled context
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                conn = get_db_connection()
                # Test the connection
                with conn.cursor() as test_cur:
                    test_cur.execute("SELECT 1")
                    test_cur.fetchone()
                break  # Connection is good, exit retry loop
            except Exception as conn_error:
                logger.warning(f"Database connection attempt {attempt + 1} failed in get_expiring_warranties: {conn_error}")
                if conn:
                    try:
                        release_db_connection(conn)
                    except:
                        pass
                conn = None
                
                if attempt < max_retries - 1:
                    logger.info(f"Retrying database connection in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                else:
                    logger.error("All database connection attempts failed in get_expiring_warranties")
                    return []
        
        today = date.today()

        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    u.id, -- Select user_id
                    u.email,
                    u.first_name,
                    w.product_name,
                    w.expiration_date,
                    COALESCE(up.expiring_soon_days, 30) AS expiring_soon_days
                FROM
                    warranties w
                JOIN
                    users u ON w.user_id = u.id
                LEFT JOIN
                    user_preferences up ON u.id = up.user_id
                WHERE
                    w.is_lifetime = FALSE
                    AND w.expiration_date > %s
                    AND w.expiration_date <= (%s::date + (COALESCE(up.expiring_soon_days, 30) || ' days')::interval)::date
                    AND u.is_active = TRUE
                    AND COALESCE(up.email_notifications, TRUE) = TRUE;
            """, (today, today))

            expiring_warranties = []
            for row in cur.fetchall():
                user_id, email, first_name, product_name, expiration_date, expiring_soon_days = row
                expiration_date_str = expiration_date.strftime('%Y-%m-%d')
                expiring_warranties.append({
                    'user_id': user_id,
                    'email': email,
                    'first_name': first_name or 'User',  # Default if first_name is NULL
                    'product_name': product_name,
                    'expiration_date': expiration_date_str,
                })

            return expiring_warranties

    except Exception as e:
        logger.error(f"Error retrieving expiring warranties: {e}")
        return []  # Return an empty list on error
    finally:
        if conn:
            release_db_connection(conn)

def format_expiration_email(user, warranties, get_db_connection, release_db_connection):
    """
    Format an email notification for expiring warranties.
    Returns a MIMEMultipart email object with both text and HTML versions.
    """
    subject = "Warracker: Upcoming Warranty Expirations"
    
    # Get email base URL from settings with correct precedence
    # Priority: Environment Variable > Database Setting > Hardcoded Default
    email_base_url = os.environ.get('APP_BASE_URL')
    if email_base_url is None:
        # Fall back to database setting if environment variable is not set
        conn = None
        email_base_url = 'http://localhost:8080'  # Default fallback
        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                cur.execute("SELECT value FROM site_settings WHERE key = 'email_base_url'")
                result = cur.fetchone()
                if result:
                    email_base_url = result[0]
                else:
                    logger.warning("email_base_url setting not found, using default.")
        except Exception as e:
            logger.error(f"Error fetching email_base_url from settings: {e}. Using default.")
        finally:
            if conn:
                release_db_connection(conn)
    
    # Ensure base URL doesn't end with a slash
    email_base_url = email_base_url.rstrip('/')
    
    # Create both plain text and HTML versions of the email body
    text_body = f"Hello {user['first_name']},\\n\\n"
    text_body += "The following warranties are expiring soon:\\n\\n"
    
    html_body = f"""\
    <html>
      <head></head>
      <body>
        <p>Hello {user['first_name']},</p>
        <p>The following warranties are expiring soon:</p>
        <table border="1" style="border-collapse: collapse;">
          <thead>
            <tr>
              <th style="padding: 8px; text-align: left;">Product Name</th>
              <th style="padding: 8px; text-align: left;">Expiration Date</th>
            </tr>
          </thead>
          <tbody>
    """

    for warranty in warranties:
        text_body += f"- {warranty['product_name']} (expires on {warranty['expiration_date']})\\n"
        html_body += f"""\
            <tr>
              <td style="padding: 8px;">{warranty['product_name']}</td>
              <td style="padding: 8px;">{warranty['expiration_date']}</td>
            </tr>
        """

    text_body += "\\nLog in to Warracker to view details:\\n"
    text_body += f"{email_base_url}\\n\\n"
    text_body += "Manage your notification settings:\\n"
    text_body += f"{email_base_url}/settings-new.html\\n"

    html_body += f"""\
          </tbody>
        </table>
        <p>Log in to <a href="{email_base_url}">Warracker</a> to view details.</p> 
        <p>Manage your notification settings <a href="{email_base_url}/settings-new.html">here</a>.</p>
      </body>
    </html>
    """

    # Create a MIMEMultipart object for both text and HTML
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = os.environ.get('SMTP_USERNAME', 'notifications@warracker.com')
    msg['To'] = user['email']

    part1 = MIMEText(text_body, 'plain')
    part2 = MIMEText(html_body, 'html')

    msg.attach(part1)
    msg.attach(part2)

    return msg

def send_expiration_notifications(manual_trigger=False, get_db_connection=None, release_db_connection=None):
    """
    Main function to send warranty expiration notifications.
    Retrieves expiring warranties, groups them by user, and sends emails.
    
    Args:
        manual_trigger (bool): Whether this function was triggered manually (vs scheduled)
        get_db_connection: Database connection function
        release_db_connection: Database connection release function
    """
    if get_db_connection is None or release_db_connection is None:
        logger.error("Database connection functions not provided to send_expiration_notifications")
        return
        
    # Use a lock to prevent concurrent executions
    if not notification_lock.acquire(blocking=False):
        logger.info("Notification job already running, skipping this execution")
        return
        
    # Add a small delay for manual triggers to prevent collision with scheduled job
    if manual_trigger:
        time.sleep(0.1)
        
    try:
        logger.info("Starting expiration notification process")
        
        # If not manually triggered, check if notifications should be sent today based on preferences
        if not manual_trigger:
            conn = None
            try:
                # Add retry logic for database connections in scheduled context
                max_retries = 3
                retry_delay = 2
                
                for attempt in range(max_retries):
                    try:
                        conn = get_db_connection()
                        # Test the connection
                        with conn.cursor() as test_cur:
                            test_cur.execute("SELECT 1")
                            test_cur.fetchone()
                        break  # Connection is good, exit retry loop
                    except Exception as conn_error:
                        logger.warning(f"Database connection attempt {attempt + 1} failed: {conn_error}")
                        if conn:
                            try:
                                release_db_connection(conn)
                            except:
                                pass
                        conn = None
                        
                        if attempt < max_retries - 1:
                            logger.info(f"Retrying database connection in {retry_delay} seconds...")
                            time.sleep(retry_delay)
                        else:
                            logger.error("All database connection attempts failed")
                            return
                
                with conn.cursor() as cur:
                    # Get today's date and current time in UTC
                    utc_now = datetime.utcnow()
                    
                    # Get user IDs that should receive notifications today
                    # First check if the required columns exist
                    cur.execute("""
                        SELECT column_name FROM information_schema.columns 
                        WHERE table_name='user_preferences' 
                        AND column_name IN ('notification_channel', 'apprise_notification_time', 'apprise_notification_frequency')
                    """)
                    existing_columns = [row[0] for row in cur.fetchall()]
                    
                    has_notification_channel = 'notification_channel' in existing_columns
                    has_apprise_notification_time = 'apprise_notification_time' in existing_columns
                    has_apprise_notification_frequency = 'apprise_notification_frequency' in existing_columns
                    
                    # Build query dynamically based on available columns
                    select_fields = [
                        "u.id", 
                        "u.email", 
                        "u.first_name", 
                        "up.notification_time",
                        "up.timezone",
                        "up.notification_frequency"
                    ]
                    
                    if has_apprise_notification_time:
                        select_fields.append("up.apprise_notification_time")
                    else:
                        select_fields.append("'09:00' as apprise_notification_time")
                    
                    if 'apprise_timezone' in existing_columns:
                        select_fields.append("up.apprise_timezone")
                    else:
                        select_fields.append("up.timezone as apprise_timezone")

                    if has_apprise_notification_frequency:
                        select_fields.append("up.apprise_notification_frequency")
                    else:
                        select_fields.append("'daily' as apprise_notification_frequency")
                    
                    if has_notification_channel:
                        select_fields.append("up.notification_channel")
                        where_clause = "WHERE u.is_active = TRUE AND up.notification_channel != 'none'"
                    else:
                        select_fields.append("'email' as notification_channel")
                        where_clause = "WHERE u.is_active = TRUE"
                    
                    eligible_users_query = f"""
                        SELECT {', '.join(select_fields)}
                        FROM users u
                        JOIN user_preferences up ON u.id = up.user_id
                        {where_clause}
                    """
                    cur.execute(eligible_users_query)
                    eligible_users = cur.fetchall()
                    
                    if not eligible_users:
                        logger.info("No users are eligible for notifications")
                        return
                    
                    logger.info(f"DEBUG: Found {len(eligible_users)} eligible users for notification checking")
                    
                    # Check if we should send notifications based on time and timezone
                    users_to_notify_email = set()
                    users_to_notify_apprise = set()
                    for user in eligible_users:
                        try:
                            user_id, email, first_name, notification_time, timezone, frequency, apprise_notification_time, apprise_timezone, apprise_frequency, channel = user
                        except ValueError as e:
                            logger.error(f"Column unpacking error for user {user}: {e}. Expected 10 columns, got {len(user)}")
                            continue
                        
                        try:
                            # Convert UTC time to user's timezone
                            user_tz = pytz_timezone(timezone or 'UTC')
                            user_local_time = utc_now.replace(tzinfo=pytz.UTC).astimezone(user_tz)
                            
                            # Check email notifications
                            if channel in ['email', 'both']:
                                # Check if notification should be sent based on frequency
                                should_send = False
                                if frequency == 'daily':
                                    should_send = True
                                elif frequency == 'weekly' and user_local_time.weekday() == 0:  # Monday
                                    should_send = True
                                elif frequency == 'monthly' and user_local_time.day == 1:
                                    should_send = True
                                    
                                if should_send:
                                    # Parse notification time
                                    time_hour, time_minute = map(int, notification_time.split(':'))
                                    
                                    # Get current hour and minute in user's timezone
                                    current_hour = user_local_time.hour
                                    current_minute = user_local_time.minute
                                    
                                    # Calculate minutes difference
                                    user_minutes = time_hour * 60 + time_minute
                                    current_minutes = current_hour * 60 + current_minute
                                    
                                    # Calculate time difference (positive = current time is after notification time)
                                    time_diff = current_minutes - user_minutes
                                    
                                    # Handle day rollovers: if current time is much earlier, we crossed midnight
                                    if time_diff < -720:  # More than 12 hours behind, probably crossed midnight
                                        time_diff += 1440
                                    elif time_diff > 720:  # More than 12 hours ahead, probably went backward over midnight  
                                        time_diff -= 1440
                                    
                                    # Only send if we're within 2 minutes AFTER the notification time
                                    # This prevents sending before the time and limits duplicates
                                    if 0 <= time_diff <= 2:
                                        # Check if we already sent notification today
                                        current_date = user_local_time.strftime('%Y-%m-%d')
                                        last_sent_key = f"email_{user_id}_{current_date}"
                                        
                                        if last_sent_key not in last_notification_sent:
                                            users_to_notify_email.add(user_id)
                                            last_notification_sent[last_sent_key] = True
                                            logger.info(f"User {email} eligible for email notification at their local time {notification_time} ({timezone}). Time diff: {time_diff} minutes")
                                        else:
                                            logger.debug(f"User {email} already received email notification today ({current_date})")
                                    else:
                                        logger.debug(f"User {email} not in email notification window. Target: {notification_time}, Current: {current_hour:02d}:{current_minute:02d}, Diff: {time_diff} minutes")

                            # Check Apprise notifications
                            if channel in ['apprise', 'both']:
                                apprise_user_tz = pytz_timezone(apprise_timezone or 'UTC')
                                apprise_local_time = utc_now.replace(tzinfo=pytz.UTC).astimezone(apprise_user_tz)

                                should_send_apprise = False
                                if apprise_frequency == 'daily':
                                    should_send_apprise = True
                                elif apprise_frequency == 'weekly' and apprise_local_time.weekday() == 0:
                                    should_send_apprise = True
                                elif apprise_frequency == 'monthly' and apprise_local_time.day == 1:
                                    should_send_apprise = True

                                if should_send_apprise:
                                    time_hour, time_minute = map(int, apprise_notification_time.split(':'))
                                    current_hour = apprise_local_time.hour
                                    current_minute = apprise_local_time.minute
                                    user_minutes = time_hour * 60 + time_minute
                                    current_minutes = current_hour * 60 + current_minute
                                    
                                    # Calculate time difference (positive = current time is after notification time)
                                    time_diff = current_minutes - user_minutes
                                    
                                    # Handle day rollovers: if current time is much earlier, we crossed midnight
                                    if time_diff < -720:  # More than 12 hours behind, probably crossed midnight
                                        time_diff += 1440
                                    elif time_diff > 720:  # More than 12 hours ahead, probably went backward over midnight  
                                        time_diff -= 1440
                                    
                                    # Only send if we're within 2 minutes AFTER the notification time
                                    if 0 <= time_diff <= 2:
                                        # Check if we already sent Apprise notification today
                                        current_date = apprise_local_time.strftime('%Y-%m-%d')
                                        last_sent_key = f"apprise_{user_id}_{current_date}"
                                        
                                        if last_sent_key not in last_notification_sent:
                                            users_to_notify_apprise.add(user_id)
                                            last_notification_sent[last_sent_key] = True
                                            logger.info(f"User {email} eligible for Apprise notification at their local time {apprise_notification_time} ({apprise_timezone}). Time diff: {time_diff} minutes")
                                        else:
                                            logger.debug(f"User {email} already received Apprise notification today ({current_date})")
                                    else:
                                        logger.debug(f"User {email} not in Apprise notification window. Target: {apprise_notification_time}, Current: {current_hour:02d}:{current_minute:02d}, Diff: {time_diff} minutes")

                        except Exception as e:
                            logger.error(f"Error processing timezone for user {email}: {e}")
                            continue
                    
                    if not users_to_notify_email and not users_to_notify_apprise:
                        logger.info("No users are scheduled for notifications at their local time")
                        logger.info(f"DEBUG: Checked {len(eligible_users)} total users for notification eligibility")
                        for user in eligible_users[:3]:  # Log first 3 users for debugging
                            try:
                                user_id, email, first_name, notification_time, timezone, frequency, apprise_notification_time, apprise_timezone, apprise_frequency, channel = user
                                user_tz = pytz_timezone(timezone or 'UTC')
                                user_local_time = utc_now.replace(tzinfo=pytz.UTC).astimezone(user_tz)
                                
                                # Calculate timing for both email and apprise
                                email_diff = "N/A"
                                apprise_diff = "N/A"
                                
                                if channel in ['email', 'both']:
                                    try:
                                        time_hour, time_minute = map(int, notification_time.split(':'))
                                        user_minutes = time_hour * 60 + time_minute
                                        current_minutes = user_local_time.hour * 60 + user_local_time.minute
                                        email_diff = current_minutes - user_minutes
                                        if email_diff < -720: email_diff += 1440
                                        elif email_diff > 720: email_diff -= 1440
                                    except: pass
                                
                                if channel in ['apprise', 'both']:
                                    try:
                                        apprise_tz = pytz_timezone(apprise_timezone or 'UTC')
                                        apprise_local = utc_now.replace(tzinfo=pytz.UTC).astimezone(apprise_tz)
                                        time_hour, time_minute = map(int, apprise_notification_time.split(':'))
                                        user_minutes = time_hour * 60 + time_minute
                                        current_minutes = apprise_local.hour * 60 + apprise_local.minute
                                        apprise_diff = current_minutes - user_minutes
                                        if apprise_diff < -720: apprise_diff += 1440
                                        elif apprise_diff > 720: apprise_diff -= 1440
                                    except: pass
                                
                                logger.info(f"DEBUG User {email}: channel={channel}, email_time={notification_time}(diff:{email_diff}), apprise_time={apprise_notification_time}(diff:{apprise_diff}), current_local={user_local_time.strftime('%H:%M')}, timezone={timezone}")
                            except Exception as e:
                                logger.info(f"DEBUG User {email}: Error processing - {e}")
                        return
                    
                    logger.info(f"Found {len(users_to_notify_email)} users eligible for email notifications, {len(users_to_notify_apprise)} users eligible for Apprise notifications")
            except Exception as e:
                logger.error(f"Error determining notification eligibility: {e}")
                return
            finally:
                if conn:
                    release_db_connection(conn)
        
        expiring_warranties = get_expiring_warranties(get_db_connection, release_db_connection)
        if not expiring_warranties:
            logger.info("No expiring warranties found.")
            return

        # Group warranties by user
        users_warranties = {}
        for warranty in expiring_warranties:
            user_id = warranty['user_id']
            email = warranty['email']
            if email not in users_warranties:
                users_warranties[email] = {
                    'user_id': user_id,
                    'first_name': warranty['first_name'],
                    'warranties': []
                }
            users_warranties[email]['warranties'].append(warranty)
        
        # Get SMTP settings from environment variables with fallbacks
        smtp_host = os.environ.get('SMTP_HOST', 'localhost')
        smtp_port = int(os.environ.get('SMTP_PORT', '1025'))
        smtp_username = os.environ.get('SMTP_USERNAME', 'notifications@warracker.com')
        smtp_password = os.environ.get('SMTP_PASSWORD', '')
        
        # Explicit SMTP_USE_TLS from environment, defaulting to true if port is 587
        smtp_use_tls_env = os.environ.get('SMTP_USE_TLS', 'not_set').lower()
        
        # Connect to SMTP server
        try:
            logger.info(f"Attempting SMTP connection to {smtp_host}:{smtp_port}")
            if smtp_port == 465:
                logger.info("Using SMTP_SSL for port 465.")
                server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=10)
            else:
                logger.info(f"Using SMTP for port {smtp_port}.")
                server = smtplib.SMTP(smtp_host, smtp_port, timeout=10)
                
                should_use_starttls = False
                if smtp_port == 587:
                    should_use_starttls = (smtp_use_tls_env != 'false')
                    logger.info(f"Port is 587. SMTP_USE_TLS set to '{smtp_use_tls_env}'. should_use_starttls: {should_use_starttls}")
                elif smtp_use_tls_env == 'true':
                    should_use_starttls = True
                    logger.info(f"Port is {smtp_port}. SMTP_USE_TLS explicitly 'true'. should_use_starttls: {should_use_starttls}")
                else:
                    logger.info(f"Port is {smtp_port}. SMTP_USE_TLS set to '{smtp_use_tls_env}'. should_use_starttls: {should_use_starttls}")

                if should_use_starttls:
                    logger.info("Attempting to start TLS (server.starttls()).")
                    server.starttls()
                    logger.info("STARTTLS successful.")
                else:
                    logger.info("Not using STARTTLS based on port and SMTP_USE_TLS setting.")
            
            # Login if credentials are provided
            if smtp_username and smtp_password:
                logger.info(f"Logging in with username: {smtp_username}")
                server.login(smtp_username, smtp_password)
                logger.info("SMTP login successful.")

            # Send emails to each user
            utc_now = datetime.utcnow()
            timestamp = int(utc_now.timestamp())
            
            emails_sent = 0
            
            # For manual triggers, get users who have email notifications enabled
            email_enabled_users = set()
            if manual_trigger:
                conn_manual = None
                try:
                    conn_manual = get_db_connection()
                    with conn_manual.cursor() as cur:
                        # Check if notification_channel column exists
                        cur.execute("""
                            SELECT column_name FROM information_schema.columns 
                            WHERE table_name='user_preferences' AND column_name='notification_channel'
                        """)
                        has_channel_column = bool(cur.fetchone())
                        
                        if has_channel_column:
                            # Get users who have email or both channels enabled
                            cur.execute("""
                                SELECT DISTINCT u.id 
                                FROM users u
                                JOIN user_preferences up ON u.id = up.user_id
                                WHERE u.is_active = TRUE 
                                AND up.notification_channel IN ('email', 'both')
                            """)
                            email_enabled_users = set(row[0] for row in cur.fetchall())
                            logger.info(f"Manual trigger: Found {len(email_enabled_users)} users with email notifications enabled")
                        else:
                            # Fallback for installations without notification_channel column
                            logger.info("Manual trigger: notification_channel column not found, enabling email for all users (fallback mode)")
                            email_enabled_users = set(user_data.get('user_id') for user_data in users_warranties.values())
                except Exception as e:
                    logger.error(f"Error checking email preferences for manual trigger: {e}")
                    # Fallback to all users in case of error
                    email_enabled_users = set(user_data.get('user_id') for user_data in users_warranties.values())
                finally:
                    if conn_manual:
                        release_db_connection(conn_manual)
            
            for email, user_data in users_warranties.items():
                user_id_to_check = user_data.get('user_id')
                
                # Check if user should receive notifications
                if not manual_trigger and user_id_to_check not in users_to_notify_email:
                    logger.debug(f"Skipping email for {email} (user_id: {user_id_to_check}) - not in current email notification window.")
                    continue
                
                # For manual triggers, check if user has email notifications enabled
                if manual_trigger and user_id_to_check not in email_enabled_users:
                    logger.debug(f"Manual trigger: Skipping email for {email} (user_id: {user_id_to_check}) - email notifications not enabled for this user.")
                    continue
                
                # For manual triggers, check if we've sent recently
                if manual_trigger and email in last_notification_sent:
                    last_sent = last_notification_sent[email]
                    if timestamp - last_sent < 120:
                        logger.info(f"Manual trigger: Skipping notification for {email} - already sent within the last 2 minutes")
                        continue
                
                msg = format_expiration_email(
                    {'first_name': user_data['first_name'], 'email': email},
                    user_data['warranties'],
                    get_db_connection,
                    release_db_connection
                )
                try:
                    server.sendmail(smtp_username, email, msg.as_string())
                    last_notification_sent[email] = timestamp
                    emails_sent += 1
                    logger.info(f"Expiration notification email sent to {email} for {len(user_data['warranties'])} warranties at {datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')}")
                except Exception as e:
                    logger.error(f"Error sending email to {email}: {e}")
            
            logger.info(f"Email notification process completed. Sent {emails_sent} emails out of {len(users_warranties)} eligible users.")
            server.quit()
            
        except Exception as e:
            logger.error(f"Error connecting to SMTP server: {e}")
            logger.error(f"SMTP details - Host: {smtp_host}, Port: {smtp_port}, Username: {smtp_username}")

        # Send Apprise notifications if available and enabled (but not for manual triggers)
        # Manual Apprise notifications should use the dedicated /api/admin/apprise/send-expiration endpoint
        if APPRISE_AVAILABLE and apprise_handler is not None and not manual_trigger:
            try:
                # Get the Apprise notification settings
                notification_mode = get_site_setting('apprise_notification_mode', 'global')
                warranty_scope = get_site_setting('apprise_warranty_scope', 'all')
                logger.info(f"Apprise notification mode set to: '{notification_mode}', warranty scope: '{warranty_scope}'")
                
                # Filter warranties for users eligible for Apprise at this time
                if manual_trigger:
                    # For manual triggers, get users who have Apprise notifications enabled
                    conn = None
                    try:
                        conn = get_db_connection()
                        with conn.cursor() as cur:
                            # Check if notification_channel column exists
                            cur.execute("""
                                SELECT column_name FROM information_schema.columns 
                                WHERE table_name='user_preferences' AND column_name='notification_channel'
                            """)
                            has_channel_column = bool(cur.fetchone())
                            
                            if has_channel_column:
                                # Get users who have Apprise or both channels enabled
                                cur.execute("""
                                    SELECT DISTINCT u.id 
                                    FROM users u
                                    JOIN user_preferences up ON u.id = up.user_id
                                    WHERE u.is_active = TRUE 
                                    AND up.notification_channel IN ('apprise', 'both')
                                """)
                                apprise_eligible_user_ids = [row[0] for row in cur.fetchall()]
                            else:
                                # Fallback for installations without notification_channel column
                                apprise_eligible_user_ids = list(users_warranties.keys())
                                logger.info("Manual trigger: notification_channel column not found, enabling for all users (fallback mode)")
                    finally:
                        if conn:
                            release_db_connection(conn)
                else:
                    # For scheduled notifications, use users_to_notify_apprise
                    apprise_eligible_user_ids = list(users_to_notify_apprise)
                
                if not apprise_eligible_user_ids:
                    logger.info("No users eligible for Apprise notifications")
                    apprise_results = {"sent": 0, "errors": 0, "skipped": "No eligible users"}
                else:
                    # Filter expiring warranties for eligible users
                    warranties_for_apprise_users = [w for w in expiring_warranties if w['user_id'] in apprise_eligible_user_ids]
                    
                    # Apply warranty scope filtering
                    if warranty_scope == 'admin':
                        # Get admin user ID (first check if there's an owner, otherwise find first admin)
                        admin_user_id = None
                        conn_scope = None
                        try:
                            conn_scope = get_db_connection()
                            with conn_scope.cursor() as cur:
                                # First try to find the owner
                                cur.execute("SELECT id FROM users WHERE is_owner = TRUE LIMIT 1")
                                owner_result = cur.fetchone()
                                if owner_result:
                                    admin_user_id = owner_result[0]
                                else:
                                    # Fallback to first admin if no owner found
                                    cur.execute("SELECT id FROM users WHERE is_admin = TRUE ORDER BY id LIMIT 1")
                                    admin_result = cur.fetchone()
                                    if admin_result:
                                        admin_user_id = admin_result[0]
                        except Exception as e:
                            logger.error(f"Error finding admin user ID for warranty scope filtering: {e}")
                        finally:
                            if conn_scope:
                                release_db_connection(conn_scope)
                        
                        if admin_user_id:
                            original_count = len(warranties_for_apprise_users)
                            warranties_for_apprise_users = [w for w in warranties_for_apprise_users if w['user_id'] == admin_user_id]
                            logger.info(f"Warranty scope 'admin': Filtered from {original_count} to {len(warranties_for_apprise_users)} warranties (admin user ID: {admin_user_id})")
                        else:
                            logger.warning("Warranty scope 'admin' requested but no admin user found, including all warranties")
                    elif warranty_scope == 'all':
                        logger.info(f"Warranty scope 'all': Including all {len(warranties_for_apprise_users)} eligible warranties")
                    else:
                        logger.warning(f"Unknown warranty scope '{warranty_scope}', defaulting to 'all' warranties")
                    
                    if not warranties_for_apprise_users:
                        logger.info("No expiring warranties for users eligible for Apprise at this time")
                        apprise_results = {"sent": 0, "errors": 0, "skipped": "No expiring warranties for eligible users"}
                    else:
                        logger.info(f"Processing Apprise notifications in {notification_mode.upper()} mode for {len(warranties_for_apprise_users)} warranties")
                        
                        if notification_mode == 'global':
                            # GLOBAL MODE: Send one consolidated notification
                            logger.info("Sending GLOBAL Apprise notification")
                            success = apprise_handler.send_global_expiration_notification(warranties_for_apprise_users)
                            apprise_results = {"sent": 1 if success else 0, "errors": 0 if success else 1, "mode": "global"}
                        
                        elif notification_mode == 'individual':
                            # INDIVIDUAL MODE: Send one notification per user
                            logger.info("Sending INDIVIDUAL Apprise notifications")
                            sent_count = 0
                            error_count = 0
                            
                            # Group warranties by user
                            user_warranties = {}
                            for w in warranties_for_apprise_users:
                                uid = w['user_id']
                                if uid not in user_warranties:
                                    user_warranties[uid] = []
                                user_warranties[uid].append(w)
                            
                            # Send notification for each user
                            for user_id, warranties in user_warranties.items():
                                try:
                                    success = apprise_handler.send_individual_expiration_notification(user_id, warranties, get_db_connection, release_db_connection)
                                    if success:
                                        sent_count += 1
                                    else:
                                        error_count += 1
                                except Exception as e:
                                    logger.error(f"Error sending individual Apprise notification for user {user_id}: {e}")
                                    error_count += 1
                            
                            apprise_results = {"sent": sent_count, "errors": error_count, "mode": "individual"}
                        
                        else:
                            logger.warning(f"Unknown Apprise notification mode: '{notification_mode}'. Skipping Apprise notifications.")
                            apprise_results = {"sent": 0, "errors": 1, "skipped": f"Unknown mode: {notification_mode}"}
                
                logger.info(f"Apprise notification process completed. Results: {apprise_results}")
            except Exception as e:
                logger.error(f"Error sending Apprise notifications: {e}")
        elif manual_trigger:
            logger.debug("Manual trigger: Skipping Apprise notifications (use dedicated Apprise endpoint for manual Apprise notifications)")
        else:
            logger.debug("Apprise notifications not available, skipping")

    except Exception as e:
        logger.error(f"Error in send_expiration_notifications: {e}")
    finally:
        notification_lock.release()

def should_run_scheduler():
    """Check if this is the main process that should run the scheduler"""
    worker_id = os.environ.get('GUNICORN_WORKER_ID', '0')
    worker_name = os.environ.get('GUNICORN_WORKER_PROCESS_NAME', '')
    worker_class = os.environ.get('GUNICORN_WORKER_CLASS', '')
    memory_mode = os.environ.get('WARRACKER_MEMORY_MODE', '').lower()
    
    # For gunicorn - only run in worker 0
    if worker_name == 'worker-0' or worker_id == '0':
        logger.info(f"Scheduler will run in Gunicorn worker (ID: {worker_id}, Name: {worker_name})")
        return True
    
    # Special case: Ultra-light mode with single worker - always run scheduler
    if memory_mode == 'ultra-light':
        logger.info(f"Scheduler will run in ultra-light mode (single worker expected)")
        return True
    
    # For development server or single-worker mode
    if __name__ == '__main__':
        logger.info("Scheduler will run in development server")
        return True
    
    # Check if we're not in a multi-worker environment (fallback)
    if not worker_class:
        logger.info("Scheduler will run - no multi-worker environment detected")
        return True
    
    # If we have worker class but no specific worker identification, 
    # assume single worker mode for sync workers (common in Docker)
    if worker_class == 'sync' and not worker_name and worker_id == '0':
        logger.info(f"Scheduler will run in single sync worker mode (worker_class: {worker_class})")
        return True
    
    logger.info(f"Scheduler will NOT run in this worker (ID: {worker_id}, Name: {worker_name}, Class: {worker_class}, Mode: {memory_mode})")
    return False

def init_scheduler(get_db_connection, release_db_connection):
    """Initialize the scheduler if this is the appropriate worker"""
    global scheduler, scheduler_initialized
    
    if should_run_scheduler():
        try:
            # Initialize scheduler if not already done
            if scheduler is None:
                # First try GeventScheduler if gevent is available and we're in a gevent worker
                worker_class = os.environ.get('GUNICORN_WORKER_CLASS', '')
                
                if GEVENT_SCHEDULER_AVAILABLE and worker_class == 'gevent':
                    try:
                        scheduler = GeventScheduler(
                            job_defaults={
                                'coalesce': True,
                                'max_instances': 1,
                                'misfire_grace_time': 300
                            }
                        )
                        logger.info("Using GeventScheduler for gevent worker compatibility")
                    except Exception as gevent_error:
                        logger.warning(f"Failed to initialize GeventScheduler: {gevent_error}")
                        logger.info("Falling back to BackgroundScheduler")
                        if BACKGROUND_SCHEDULER_AVAILABLE:
                            scheduler = BackgroundScheduler(
                                job_defaults={
                                    'coalesce': True,
                                    'max_instances': 1,
                                    'misfire_grace_time': 300
                                }
                            )
                            logger.info("Using BackgroundScheduler (GeventScheduler fallback)")
                        else:
                            logger.error("BackgroundScheduler not available for fallback")
                            return False
                else:
                    if BACKGROUND_SCHEDULER_AVAILABLE:
                        scheduler = BackgroundScheduler(
                            job_defaults={
                                'coalesce': True,
                                'max_instances': 1,
                                'misfire_grace_time': 300
                            }
                        )
                        if worker_class == 'gevent':
                            logger.info("Using BackgroundScheduler with gevent worker (GeventScheduler not available)")
                        else:
                            logger.info(f"Using BackgroundScheduler with {worker_class} worker")
                    else:
                        logger.error("No scheduler available (BackgroundScheduler not found)")
                        return False
            
            # Create a wrapper function that includes the database functions
            def notification_wrapper():
                return send_expiration_notifications(
                    manual_trigger=False,
                    get_db_connection=get_db_connection,
                    release_db_connection=release_db_connection
                )
            
            # Check for scheduled notifications every 2 minutes for more precise timing
            scheduler.add_job(func=notification_wrapper, trigger="interval", minutes=2, id='notification_job')
            scheduler.start()
            logger.info("✅ Email notification scheduler started - checking every 2 minutes")
            
            # Add a shutdown hook
            atexit.register(lambda: scheduler.shutdown())
            scheduler_initialized = True
            return True
        except Exception as e:
            logger.error(f"❌ Failed to start scheduler: {e}")
            scheduler_initialized = False
            return False
    else:
        logger.info("ℹ️ Scheduler not started in this worker")
        scheduler_initialized = False
        return False

def ensure_scheduler_initialized(get_db_connection, release_db_connection):
    """Ensure scheduler is initialized on the first request if it wasn't at startup"""
    global scheduler_initialized, scheduler_retry_attempted
    if not scheduler_initialized and not scheduler_retry_attempted:
        logger.info("Retrying scheduler initialization on first request...")
        scheduler_initialized = init_scheduler(get_db_connection, release_db_connection)
        scheduler_retry_attempted = True

def get_scheduler_status():
    """Get current scheduler status for admin endpoints"""
    global scheduler_initialized, scheduler_retry_attempted
    
    worker_id = os.environ.get('GUNICORN_WORKER_ID', 'unknown')
    worker_name = os.environ.get('GUNICORN_WORKER_PROCESS_NAME', 'unknown')
    worker_class = os.environ.get('GUNICORN_WORKER_CLASS', 'unknown')
    
    scheduler_jobs = []
    scheduler_running = False
    
    if scheduler and hasattr(scheduler, 'get_jobs'):
        try:
            jobs = scheduler.get_jobs()
            scheduler_running = scheduler.running
            scheduler_jobs = [
                {
                    'id': job.id,
                    'next_run_time': job.next_run_time.isoformat() if job.next_run_time else None,
                    'trigger': str(job.trigger)
                }
                for job in jobs
            ]
        except Exception as e:
            logger.error(f"Error getting scheduler jobs: {e}")
    
    return {
        'scheduler_initialized': scheduler_initialized,
        'scheduler_retry_attempted': scheduler_retry_attempted,
        'scheduler_running': scheduler_running,
        'scheduler_jobs': scheduler_jobs,
        'worker_info': {
            'worker_id': worker_id,
            'worker_name': worker_name,
            'worker_class': worker_class,
            'should_run_scheduler': should_run_scheduler()
        },
        'environment_vars': {
            key: value for key, value in os.environ.items() 
            if key.startswith('GUNICORN_') or key in ['WARRACKER_MEMORY_MODE']
        }
    }

def trigger_notifications_manually(get_db_connection, release_db_connection):
    """Manually trigger warranty expiration notifications"""
    try:
        logger.info("Manual notification trigger requested")
        send_expiration_notifications(
            manual_trigger=True,
            get_db_connection=get_db_connection,
            release_db_connection=release_db_connection
        )
        return {'message': 'Notifications triggered successfully'}, 200
    except Exception as e:
        error_msg = f"Error triggering notifications: {str(e)}"
        logger.error(error_msg)
        return {'message': 'Failed to trigger notifications', 'error': error_msg}, 500
