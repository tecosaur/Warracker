from flask import Flask, request, jsonify, send_from_directory, session, redirect, url_for, Response
try:
    # Try relative import for Docker environment
    from backend.extensions import oauth
    from backend.db_handler import init_db_pool, get_db_connection, release_db_connection
except ImportError:
    # Fallback to direct import for development
    from extensions import oauth
    from db_handler import init_db_pool, get_db_connection, release_db_connection
import psycopg2 # Added import
import os
from datetime import datetime, timedelta, date
from werkzeug.utils import secure_filename
from flask_cors import CORS
import logging
import time
from decimal import Decimal
import jwt
from flask_bcrypt import Bcrypt
import re
from functools import wraps
import uuid
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from backend import notifications
import atexit
from pytz import timezone as pytz_timezone
import pytz
import threading
import json
import csv  # Added for CSV import
import io   # Added for CSV import
from dateutil.relativedelta import relativedelta
import mimetypes

app = Flask(__name__)

# Memory optimization configurations
app.config['JSON_SORT_KEYS'] = False  # Disable JSON key sorting to save CPU/memory
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = False  # Disable pretty printing in production
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 31536000  # Cache static files for 1 year
app.config['PROPAGATE_EXCEPTIONS'] = True  # Better error handling

# Configure Flask to use less memory for sessions
app.config['SESSION_COOKIE_SECURE'] = False  # Set to True in production with HTTPS
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = 3600  # 1 hour session timeout

# Optimize request handling
app.config['MAX_COOKIE_SIZE'] = 4093  # Slightly under 4KB limit
app.config['USE_X_SENDFILE'] = True  # Let nginx handle file serving

# CORS configuration
CORS(app, supports_credentials=True)  # Enable CORS with credentials
bcrypt = Bcrypt(app)

oauth.init_app(app) # Initialize Authlib OAuth with the app instance

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import Apprise notification handler (after logger is defined)
try:
    try:
        # Try Docker environment path first
        from backend.apprise_handler import AppriseNotificationHandler
    except ImportError:
        # Fallback to development path
        from apprise_handler import AppriseNotificationHandler
    
    apprise_handler = AppriseNotificationHandler()
    APPRISE_AVAILABLE = True
    logger.info("Apprise notification handler imported successfully")
except ImportError as e:
    APPRISE_AVAILABLE = False
    apprise_handler = None
    logger.warning(f"Apprise not available: {e}. Notification features will be disabled.")

# App configurations
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your_default_secret_key_please_change_in_prod')
app.config['JWT_EXPIRATION_DELTA'] = timedelta(hours=int(os.environ.get('JWT_EXPIRATION_HOURS', '24')))

if app.config['SECRET_KEY'] == 'your_default_secret_key_please_change_in_prod':
    logger.warning("SECURITY WARNING: Using default SECRET_KEY. Please set a strong SECRET_KEY environment variable in production.")

# Initialize DB Pool (this will set the global connection_pool in db_handler.py)
try:
    init_db_pool() # Call the function from db_handler
    logger.info("Database connection pool initialization attempted from app.py.")
except Exception as e:
    logger.critical(f"CRITICAL: Failed to initialize database pool on startup: {e}. Application might not function correctly.")
    # Depending on your requirements, you might want to exit or attempt to run in a degraded mode.
    # For now, we log critical and continue, but subsequent DB calls will likely fail.

# Email change token settings
EMAIL_CHANGE_TOKEN_EXPIRATION_HOURS = 24 # Token valid for 24 hours
EMAIL_CHANGE_VERIFICATION_ENDPOINT = '/verify-email-change.html' # Frontend page for verification

UPLOAD_FOLDER = '/data/uploads'
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'zip', 'rar'}

# Default max upload size in MB
DEFAULT_MAX_UPLOAD_MB = 32
try:
    MAX_UPLOAD_MB = int(os.environ.get('MAX_UPLOAD_MB', DEFAULT_MAX_UPLOAD_MB))
    if MAX_UPLOAD_MB <= 0:
        MAX_UPLOAD_MB = DEFAULT_MAX_UPLOAD_MB
        logger.warning(f"MAX_UPLOAD_MB was invalid, defaulting to {DEFAULT_MAX_UPLOAD_MB}MB.")
except ValueError:
    MAX_UPLOAD_MB = DEFAULT_MAX_UPLOAD_MB
    logger.warning(f"MAX_UPLOAD_MB was not a valid integer, defaulting to {DEFAULT_MAX_UPLOAD_MB}MB.")

MAX_CONTENT_LENGTH = MAX_UPLOAD_MB * 1024 * 1024  # Convert MB to bytes
logger.info(f"Max upload file size set to: {MAX_UPLOAD_MB}MB ({MAX_CONTENT_LENGTH} bytes)")

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

# PostgreSQL connection pool
DB_HOST = os.environ.get('DB_HOST', 'warrackerdb')
DB_NAME = os.environ.get('DB_NAME', 'warranty_db')
DB_USER = os.environ.get('DB_USER', 'warranty_user')
DB_PASSWORD = os.environ.get('DB_PASSWORD', 'warranty_password')
DB_ADMIN_USER = os.environ.get('DB_ADMIN_USER', 'warracker_admin')
DB_ADMIN_PASSWORD = os.environ.get('DB_ADMIN_PASSWORD', 'change_this_password_in_production')

# Create a connection pool with retry logic
# This block is now moved earlier, before get_db_connection is defined.
# The actual initialization of the global 'connection_pool' variable
# and the call to 'init_oidc_client' will happen after all necessary
# function definitions.

# Old position of create_db_pool, get_db_connection, release_db_connection
# and the try/except block for connection_pool and init_oidc_client call.
# These are now defined *before* this spot.

# Function to initialize OIDC client based on settings
def init_oidc_client(current_app_instance, db_conn_func, db_release_func): # Keep parameters
    logger.info("[APP.PY OIDC_INIT] Attempting to initialize OIDC client...")
    conn = None
    oidc_db_settings = {}
    try:
        conn = db_conn_func() # USE THE PASSED-IN FUNCTION
        if conn:
            with conn.cursor() as cur:
                # Your logic to fetch OIDC settings from site_settings table
                cur.execute("SELECT key, value FROM site_settings WHERE key LIKE 'oidc_%%'")
                for row in cur.fetchall():
                    oidc_db_settings[row[0]] = row[1]
                logger.info(f"[APP.PY OIDC_INIT] Fetched OIDC settings from DB: {oidc_db_settings}")
        else:
            logger.error("[APP.PY OIDC_INIT] Database connection failed via db_conn_func, cannot fetch OIDC settings from DB.")
    except Exception as e:
        logger.error(f"[APP.PY OIDC_INIT] Error fetching OIDC settings from DB: {e}. Proceeding without DB settings.")
    finally:
        if conn:
            db_release_func(conn)

    oidc_enabled_from_db = oidc_db_settings.get('oidc_enabled')
    oidc_enabled_str = oidc_enabled_from_db if oidc_enabled_from_db is not None else os.environ.get('OIDC_ENABLED', 'false')
    is_enabled = oidc_enabled_str.lower() == 'true'
    current_app_instance.config['OIDC_ENABLED'] = is_enabled
    logger.info(f"[APP.PY OIDC_INIT] OIDC enabled status: {is_enabled}")

    if is_enabled:
        provider_name = oidc_db_settings.get('oidc_provider_name', os.environ.get('OIDC_PROVIDER_NAME', 'oidc'))
        client_id = oidc_db_settings.get('oidc_client_id', os.environ.get('OIDC_CLIENT_ID'))
        client_secret = oidc_db_settings.get('oidc_client_secret', os.environ.get('OIDC_CLIENT_SECRET'))
        issuer_url = oidc_db_settings.get('oidc_issuer_url', os.environ.get('OIDC_ISSUER_URL'))
        scope = oidc_db_settings.get('oidc_scope', os.environ.get('OIDC_SCOPE', 'openid email profile'))

        current_app_instance.config['OIDC_PROVIDER_NAME'] = provider_name

        if client_id and client_secret and issuer_url:
            logger.info(f"[APP.PY OIDC_INIT] Registering OIDC client '{provider_name}' with Authlib.")
            oauth.register( # This uses the oauth instance from backend.extensions
                name=provider_name,
                client_id=client_id,
                client_secret=client_secret,
                server_metadata_url=f"{issuer_url.rstrip('/')}/.well-known/openid-configuration",
                client_kwargs={'scope': scope},
                override=True # Allow re-registration
            )
            logger.info(f"[APP.PY OIDC_INIT] OIDC client '{provider_name}' registered successfully.")
        else:
            logger.warning("[APP.PY OIDC_INIT] OIDC is enabled, but critical parameters (client_id, client_secret, or issuer_url) are missing. OIDC login will be unavailable.")
            current_app_instance.config['OIDC_ENABLED'] = False # Correctly disable if params missing
    else:
        current_app_instance.config['OIDC_PROVIDER_NAME'] = None
        logger.info("[APP.PY OIDC_INIT] OIDC is disabled.")

# Initialize DB Pool and then OIDC client (this is the new placement for the try/except block)
with app.app_context(): # Ensure app context is available for url_for, etc. if used by init_oidc_client indirectly
    init_oidc_client(app, get_db_connection, release_db_connection) # Pass the actual DB functions

# Initialize database (definition of init_db, not the call)
def init_db():
    """Initialize the database with required tables"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Create users table if it doesn't exist - Handled by migrations
        # cur.execute("""
        # CREATE TABLE IF NOT EXISTS users (
        #     id SERIAL PRIMARY KEY,
        #     username VARCHAR(50) UNIQUE NOT NULL,
        #     email VARCHAR(100) UNIQUE NOT NULL,
        #     password_hash VARCHAR(255) NOT NULL,
        #     first_name VARCHAR(50),
        #     last_name VARCHAR(50),
        #     is_active BOOLEAN DEFAULT TRUE,
        #     is_admin BOOLEAN DEFAULT FALSE,
        #     created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        #     updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        # )
        # """)
        
        # Create user_preferences table if it doesn't exist - Handled by migrations
        # cur.execute("""
        # CREATE TABLE IF NOT EXISTS user_preferences (
        #     id SERIAL PRIMARY KEY,
        #     user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        #     email_notifications BOOLEAN NOT NULL DEFAULT TRUE,
        #     default_view VARCHAR(10) NOT NULL DEFAULT 'grid',
        #     theme VARCHAR(10) NOT NULL DEFAULT 'light',
        #     expiring_soon_days INTEGER NOT NULL DEFAULT 30,
        #     notification_frequency VARCHAR(10) NOT NULL DEFAULT 'daily',
        #     notification_time VARCHAR(5) NOT NULL DEFAULT '09:00',
        #     created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        #     updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        #     UNIQUE(user_id)
        # )
        # """)
        
        # Check if timezone column exists and add if it doesn't - Handled by migrations (e.g., 008_add_timezone_column.sql)
        # cur.execute("""
        # DO $$
        # BEGIN
        #     IF NOT EXISTS (
        #         SELECT column_name
        #         FROM information_schema.columns
        #         WHERE table_name = 'user_preferences' AND column_name = 'timezone'
        #     ) THEN
        #         ALTER TABLE user_preferences
        #         ADD COLUMN timezone VARCHAR(50) NOT NULL DEFAULT 'UTC';
        #         RAISE NOTICE 'Added timezone column to user_preferences table';
        #     END IF;
        # END $$;
        # """)
        
        # Create warranties table if it doesn't exist - Handled by migrations
        # cur.execute("""
        #     CREATE TABLE IF NOT EXISTS warranties (
        #         id SERIAL PRIMARY KEY,
        #         user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        #         item_name VARCHAR(100) NOT NULL,
        #         purchase_date DATE NOT NULL,
        #         expiration_date DATE NOT NULL,
        #         purchase_price DECIMAL(10,2),
        #         serial_number VARCHAR(100),
        #         category VARCHAR(50),
        #         notes TEXT,
        #         created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        #         updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        #     )
        # """)
        
        # Create warranty_documents table if it doesn't exist - Handled by migrations
        # cur.execute("""
        #     CREATE TABLE IF NOT EXISTS warranty_documents (
        #         id INTEGER PRIMARY KEY,
        #         warranty_id INTEGER NOT NULL REFERENCES warranties(id) ON DELETE CASCADE,
        #         file_name VARCHAR(255) NOT NULL,
        #         file_path VARCHAR(255) NOT NULL,
        #     )
        # """)
        
        conn.commit() # Commit any changes if init_db did anything
        cur.close()
    except Exception as e:
        logger.error(f"Database initialization error in init_db: {str(e)}")
        # Decide if to raise, for now, just log as per original short init_db
    finally:
        if conn: # conn might not be defined if get_db_connection failed
            release_db_connection(conn)


# Authentication helper functions
# ... (generate_token, decode_token, token_required, admin_required, etc. remain the same)
# They use get_db_connection, which should now work.

# --- Ensure create_db_pool was defined before this point ---
# The following is the original position of the try-except block that initialized connection_pool
# and called init_oidc_client. It has been moved up.

# Original try-except block for connection_pool and init_oidc_client:
# try:
#    connection_pool = create_db_pool()
#    # Initialize OIDC client after app and DB pool are available
#    # This ensures DB can be queried for settings.
#    if connection_pool: # Only if DB connection is likely
#        with app.app_context(): # Needed if get_db_connection uses app context implicitly or for safety
#             init_oidc_client(app, get_db_connection, release_db_connection)
#    else:
#        logger.error("Database connection pool not available. OIDC client initialization might be incomplete or use defaults/env vars only.")
#        # Fallback or minimal OIDC init if DB is not available at startup
#        with app.app_context():
#            init_oidc_client(app, lambda: None, lambda conn: None) # Pass dummy DB funcs
#
# except Exception as e:
#    logger.error(f"Fatal database connection error during startup: {e}")
#    connection_pool = None
#    logger.warning("Database connection pool failed. OIDC client initialization might be incomplete or use defaults/env vars only.")
#    with app.app_context():
#        init_oidc_client(app, lambda: None, lambda conn: None)


# def get_db_connection(): # Original position, now moved up
# ...

# def release_db_connection(conn): # Original position, now moved up
# ...

# def allowed_file(filename): # Original position, can stay or move with other helpers
# ...

# def init_db(): # Original position, now moved up (definition)
# ... (rest of the file)
# The actual call to init_db() for production is at the end of the file, that's fine.
# Example of where create_db_pool was defined:
# def create_db_pool(max_retries=5, retry_delay=5):
#    attempt = 0
#    last_exception = None
#    
#    while attempt < max_retries:
#        try:
#            logger.info(f"Attempting to connect to database (attempt {attempt+1}/{max_retries})")
#            connection_pool = pool.SimpleConnectionPool(
#                1, 10,  # min, max connections
#                host=DB_HOST,
#                database=DB_NAME,
#                user=DB_USER,
#                password=DB_PASSWORD
#            )
#            logger.info("Database connection successful")
#            return connection_pool
#        except Exception as e:
#            last_exception = e
#            logger.error(f"Database connection error: {e}")
#            logger.info(f"Retrying in {retry_delay} seconds...")
#            time.sleep(retry_delay)
#            attempt += 1
#    
#    # If we got here, all connection attempts failed
#    logger.error(f"Failed to connect to database after {max_retries} attempts")
#    raise last_exception

# Create a connection pool with retry logic
# try:
#    connection_pool = create_db_pool()
#    # Initialize OIDC client after app and DB pool are available
#    # This ensures DB can be queried for settings.
#    if connection_pool: # Only if DB connection is likely
#        with app.app_context(): # Needed if get_db_connection uses app context implicitly or for safety
#             init_oidc_client(app, get_db_connection, release_db_connection)
#    else:
#        logger.error("Database connection pool not available. OIDC client initialization might be incomplete or use defaults/env vars only.")
#        # Fallback or minimal OIDC init if DB is not available at startup
#        with app.app_context():
#            init_oidc_client(app, lambda: None, lambda conn: None) # Pass dummy DB funcs
#
# except Exception as e:
#    logger.error(f"Fatal database connection error during startup: {e}")
#    connection_pool = None
#    logger.warning("Database connection pool failed. OIDC client initialization might be incomplete or use defaults/env vars only.")
#    with app.app_context():
#        init_oidc_client(app, lambda: None, lambda conn: None)


def get_admin_db_connection():
    """Get a database connection with admin privileges for user management"""
    try:
        # Connect using the admin role for administrative tasks
        conn = psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_ADMIN_USER,
            password=DB_ADMIN_PASSWORD
        )
        return conn
    except Exception as e:
        logger.error(f"Admin database connection error: {e}")
        raise

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Initialize database
def init_db():
    """Initialize the database with required tables"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Create users table if it doesn't exist - Handled by migrations
        # cur.execute("""
        # CREATE TABLE IF NOT EXISTS users (
        #     id SERIAL PRIMARY KEY,
        #     username VARCHAR(50) UNIQUE NOT NULL,
        #     email VARCHAR(100) UNIQUE NOT NULL,
        #     password_hash VARCHAR(255) NOT NULL,
        #     first_name VARCHAR(50),
        #     last_name VARCHAR(50),
        #     is_active BOOLEAN DEFAULT TRUE,
        #     is_admin BOOLEAN DEFAULT FALSE,
        #     created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        #     updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        # )
        # """)
        
        # Create user_preferences table if it doesn't exist - Handled by migrations
        # cur.execute("""
        # CREATE TABLE IF NOT EXISTS user_preferences (
        #     id SERIAL PRIMARY KEY,
        #     user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        #     email_notifications BOOLEAN NOT NULL DEFAULT TRUE,
        #     default_view VARCHAR(10) NOT NULL DEFAULT 'grid',
        #     theme VARCHAR(10) NOT NULL DEFAULT 'light',
        #     expiring_soon_days INTEGER NOT NULL DEFAULT 30,
        #     notification_frequency VARCHAR(10) NOT NULL DEFAULT 'daily',
        #     notification_time VARCHAR(5) NOT NULL DEFAULT '09:00',
        #     created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        #     updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        #     UNIQUE(user_id)
        # )
        # """)
        
        # Check if timezone column exists and add if it doesn't - Handled by migrations (e.g., 008_add_timezone_column.sql)
        # cur.execute("""
        # DO $$
        # BEGIN
        #     IF NOT EXISTS (
        #         SELECT column_name
        #         FROM information_schema.columns
        #         WHERE table_name = 'user_preferences' AND column_name = 'timezone'
        #     ) THEN
        #         ALTER TABLE user_preferences
        #         ADD COLUMN timezone VARCHAR(50) NOT NULL DEFAULT 'UTC';
        #         RAISE NOTICE 'Added timezone column to user_preferences table';
        #     END IF;
        # END $$;
        # """)
        
        # Create warranties table if it doesn't exist - Handled by migrations
        # cur.execute("""
        #     CREATE TABLE IF NOT EXISTS warranties (
        #         id SERIAL PRIMARY KEY,
        #         user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        #         item_name VARCHAR(100) NOT NULL,
        #         purchase_date DATE NOT NULL,
        #         expiration_date DATE NOT NULL,
        #         purchase_price DECIMAL(10,2),
        #         serial_number VARCHAR(100),
        #         category VARCHAR(50),
        #         notes TEXT,
        #         created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        #         updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        #     )
        # """)
        
        # Create warranty_documents table if it doesn't exist - Handled by migrations
        # cur.execute("""
        #     CREATE TABLE IF NOT EXISTS warranty_documents (
        #         id INTEGER PRIMARY KEY,
        #         warranty_id INTEGER NOT NULL REFERENCES warranties(id) ON DELETE CASCADE,
        #         file_name VARCHAR(255) NOT NULL,
        #         file_path VARCHAR(255) NOT NULL,
        #     )
        # """)
        
        conn.commit() # Commit any changes if init_db did anything
        cur.close()
    except Exception as e:
        logger.error(f"Database initialization error in init_db: {str(e)}")
        # Decide if to raise, for now, just log as per original short init_db
    finally:
        if conn: # conn might not be defined if get_db_connection failed
            release_db_connection(conn)

# Authentication helper functions
def generate_token(user_id):
    """Generate a JWT token for the user"""
    payload = {
        'exp': datetime.utcnow() + app.config['JWT_EXPIRATION_DELTA'],
        'iat': datetime.utcnow(),
        'sub': user_id
    }
    return jwt.encode(payload, app.config['SECRET_KEY'], algorithm='HS256')

def decode_token(token):
    """Decode a JWT token and return the user_id"""
    try:
        payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
        return payload['sub']
    except jwt.ExpiredSignatureError:
        return None  # Token has expired
    except jwt.InvalidTokenError:
        return None  # Invalid token

def token_required(f):
    """Decorator to protect routes that require authentication"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        # Get token from Authorization header
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
        
        # If no token in header, check form data for POST requests
        if not token and request.method == 'POST':
            token = request.form.get('auth_token')  # Check form data
        
        # If still no token, check URL query parameters
        if not token:
            token = request.args.get('token')  # Check query parameters
            
        # If no token is provided
        if not token:
            logger.warning(f"Authentication attempt without token: {request.path}")
            return jsonify({'message': 'Authentication token is missing!'}), 401
        
        # Decode the token
        user_id = decode_token(token)
        if not user_id:
            logger.warning(f"Invalid token used for: {request.path}")
            return jsonify({'message': 'Invalid or expired token!'}), 401
        
        # Check if user exists
        conn = None
        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                cur.execute('SELECT id, username, email, is_admin FROM users WHERE id = %s AND is_active = TRUE', (user_id,))
                user = cur.fetchone()
                
                if not user:
                    return jsonify({'message': 'User not found or inactive!'}), 401
                
                # Add user info to request context
                request.user = {
                    'id': user[0],
                    'username': user[1],
                    'email': user[2],
                    'is_admin': user[3]
                }
                
                return f(*args, **kwargs)
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return jsonify({'message': 'Authentication error!'}), 500
        finally:
            if conn:
                release_db_connection(conn)
    
    return decorated

def admin_required(f):
    """Decorator to protect routes that require admin privileges"""
    @wraps(f)
    def decorated(*args, **kwargs):
        logger.info("Admin required check started")
        token_required_result = token_required(lambda: None)()
        
        if isinstance(token_required_result, tuple) and token_required_result[1] != 200:
            logger.error(f"Token validation failed: {token_required_result}")
            return token_required_result
        
        logger.info(f"User info: {request.user}")
        if not request.user.get('is_admin', False):
            logger.error(f"User {request.user.get('username')} is not an admin")
            return jsonify({'message': 'Admin privileges required!'}), 403
        
        logger.info(f"Admin check passed for user {request.user.get('username')}")
        return f(*args, **kwargs)
    
    return decorated

def is_valid_email(email):
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def is_valid_password(password):
    """Validate password strength"""
    # At least 8 characters, 1 uppercase, 1 lowercase, 1 number
    if len(password) < 8:
        return False
    if not re.search(r'[A-Z]', password):
        return False
    if not re.search(r'[a-z]', password):
        return False
    if not re.search(r'[0-9]', password):
        return False
    return True

def is_valid_timezone(tz):
    """Validate if a timezone string is valid"""
    try:
        pytz.timezone(tz)
        return True
    except pytz.exceptions.UnknownTimeZoneError:
        return False

def convert_decimals(obj):
    """Recursively convert Decimal objects to float in dicts/lists for JSON serialization."""
    if isinstance(obj, dict):
        return {k: convert_decimals(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_decimals(i) for i in obj]
    elif isinstance(obj, Decimal):
        return float(obj)
    else:
        return obj

# OIDC Routes
# These routes are now handled by the oidc_bp Blueprint in backend/oidc_handler.py

# @app.route('/api/oidc/login')
# def oidc_login():
#     if not app.config.get('OIDC_ENABLED'):
#         logger.warning("OIDC login attempt while OIDC is disabled in settings.")
#         # Optionally redirect to login with a message, or just return an error
#         return jsonify({'message': 'OIDC (SSO) login is not enabled.'}), 403 # Forbidden or 503 Service Unavailable
# 
#     oidc_provider_name_from_config = app.config.get('OIDC_PROVIDER_NAME')
#     if not oidc_provider_name_from_config:
#         logger.error("OIDC is enabled but provider name not configured in app.config.")
#         return jsonify({'message': 'OIDC provider not configured correctly.'}), 500
# 
#     # Construct the redirect_uri. Ensure your OIDC provider has this exact URI whitelisted.
#     # It should point to your backend's callback endpoint.
#     # For local development, this might be http://localhost:5000/api/oidc/callback
#     # For production, it will be your production URL.
#     # Using url_for with _external=True helps generate the full URL.
#     # The frontend will redirect to this /api/oidc/login, which then redirects to the IdP.
#     redirect_uri = url_for('oidc_callback', _external=True) # This would refer to the callback in this file if not removed
#     
#     # Ensure the redirect_uri uses HTTPS in production if your app is served over HTTPS
#     # This might require checking request.scheme or an environment variable.
#     if os.environ.get('FLASK_ENV') == 'production' and not redirect_uri.startswith('https'):
#         redirect_uri = redirect_uri.replace('http://', 'https://', 1)
#         
#     logger.info(f"OIDC login redirect_uri: {redirect_uri}")
#     return oauth.create_client(oidc_provider_name_from_config).authorize_redirect(redirect_uri)

# @app.route('/api/oidc/callback')
# def oidc_callback():
#    if not app.config.get('OIDC_ENABLED'):
#        logger.warning("OIDC callback received while OIDC is disabled in settings.")
        frontend_login_url = os.environ.get('FRONTEND_URL', app.config.get('APP_BASE_URL', 'http://localhost:8080')).rstrip('/') + "/login.html"
        return redirect(f"{frontend_login_url}?oidc_error=oidc_disabled")

    oidc_provider_name_from_config = app.config.get('OIDC_PROVIDER_NAME')
    if not oidc_provider_name_from_config:
        logger.error("OIDC is enabled but provider name not configured in app.config for callback.")
        frontend_login_url = os.environ.get('FRONTEND_URL', app.config.get('APP_BASE_URL', 'http://localhost:8080')).rstrip('/') + "/login.html"
        return redirect(f"{frontend_login_url}?oidc_error=oidc_misconfigured")
        
    client = oauth.create_client(oidc_provider_name_from_config)
    try:
        token = client.authorize_access_token()
    except Exception as e:
        logger.error(f"OIDC callback error authorizing access token: {e}")
        # Redirect to frontend login page with error
        # This URL should be configurable or a known frontend path
        frontend_login_url = os.environ.get('FRONTEND_URL', 'http://localhost:8080').rstrip('/') + "/login.html"
        return redirect(f"{frontend_login_url}?oidc_error=token_exchange_failed")

    if not token:
        logger.error("OIDC callback: Failed to retrieve access token.")
        frontend_login_url = os.environ.get('FRONTEND_URL', 'http://localhost:8080').rstrip('/') + "/login.html"
        return redirect(f"{frontend_login_url}?oidc_error=token_missing")

    userinfo = token.get('userinfo')
    if not userinfo:
        # If userinfo is not directly in the token, try fetching it
        try:
            userinfo = client.userinfo(token=token) # Authlib 0.15+
        except Exception as e:
            logger.error(f"OIDC callback error fetching userinfo: {e}")
            frontend_login_url = os.environ.get('FRONTEND_URL', 'http://localhost:8080').rstrip('/') + "/login.html"
            return redirect(f"{frontend_login_url}?oidc_error=userinfo_fetch_failed")
            
    if not userinfo:
        logger.error("OIDC callback: Failed to retrieve userinfo.")
        frontend_login_url = os.environ.get('FRONTEND_URL', 'http://localhost:8080').rstrip('/') + "/login.html"
        return redirect(f"{frontend_login_url}?oidc_error=userinfo_missing")

    # --- User Provisioning/Login Logic ---
    # This is a critical part and needs careful implementation.
    # 1. Extract OIDC subject (sub) and issuer (iss) from userinfo or token.
    #    These uniquely identify the user at the OIDC provider.
    oidc_subject = userinfo.get('sub')
    oidc_issuer = userinfo.get('iss') # Or from token['iss'] if available

    if not oidc_subject:
        logger.error("OIDC callback: 'sub' (subject) missing in userinfo.")
        frontend_login_url = os.environ.get('FRONTEND_URL', 'http://localhost:8080').rstrip('/') + "/login.html"
        return redirect(f"{frontend_login_url}?oidc_error=subject_missing")

    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # Check if a user with this OIDC subject and issuer already exists
            # You'll need to add oidc_sub and oidc_issuer columns to your users table.
            # For now, we'll assume these columns exist.
            # A migration will be needed for this.
            cur.execute("SELECT id, username, email, is_admin FROM users WHERE oidc_sub = %s AND oidc_issuer = %s AND is_active = TRUE", 
                        (oidc_subject, oidc_issuer))
            user_db_data = cur.fetchone()
            
            user_id = None
            is_new_user = False

            if user_db_data:
                user_id = user_db_data[0]
                logger.info(f"OIDC Login: Existing user found with ID {user_id} for sub {oidc_subject}")
            else:
                # User does not exist, provision a new one
                is_new_user = True
                email = userinfo.get('email')
                if not email:
                    logger.error("OIDC callback: 'email' missing in userinfo for new user.")
                    frontend_login_url = os.environ.get('FRONTEND_URL', 'http://localhost:8080').rstrip('/') + "/login.html"
                    return redirect(f"{frontend_login_url}?oidc_error=email_missing_for_new_user")

                # Check if email is already in use by a non-OIDC account
                cur.execute("SELECT id FROM users WHERE email = %s AND (oidc_sub IS NULL OR oidc_issuer IS NULL)", (email,))
                existing_local_user = cur.fetchone()
                if existing_local_user:
                    logger.warning(f"OIDC Signup: Email {email} already exists for a local account. OIDC user cannot be created.")
                    # This is a conflict. Decide how to handle:
                    # - Ask user to link accounts (complex)
                    # - Deny OIDC signup
                    frontend_login_url = os.environ.get('FRONTEND_URL', 'http://localhost:8080').rstrip('/') + "/login.html"
                    return redirect(f"{frontend_login_url}?oidc_error=email_conflict_local_account")

                username = userinfo.get('preferred_username') or userinfo.get('name') or email.split('@')[0]
                # Ensure username is unique if your system requires it
                # This might involve appending a random string if a conflict occurs
                
                # Check if username already exists
                cur.execute("SELECT id FROM users WHERE username = %s", (username,))
                if cur.fetchone():
                    username = f"{username}_{str(uuid.uuid4())[:8]}" # Append random chars for uniqueness

                first_name = userinfo.get('given_name', '')
                last_name = userinfo.get('family_name', '')
                
                # For OIDC users, we don't store a local password_hash, or store a placeholder.
                # The 'password_hash' column in 'users' table must allow NULL or have a default.
                # Or, add a flag 'is_oidc_user' to users table.
                # For now, let's assume password_hash can be NULL.
                
                # Check if this is the first user (who will be an admin)
                cur.execute('SELECT COUNT(*) FROM users')
                user_count = cur.fetchone()[0]
                is_admin = user_count == 0

                cur.execute(
                    """INSERT INTO users (username, email, first_name, last_name, is_admin, oidc_sub, oidc_issuer, is_active) 
                       VALUES (%s, %s, %s, %s, %s, %s, %s, TRUE) RETURNING id""",
                    (username, email, first_name, last_name, is_admin, oidc_subject, oidc_issuer)
                )
                user_id = cur.fetchone()[0]
                logger.info(f"OIDC Signup: New user created with ID {user_id} for sub {oidc_subject}")
            
            if user_id:
                # Generate your application's session token
                app_token = generate_token(user_id)
                
                # Update last login
                cur.execute('UPDATE users SET last_login = %s WHERE id = %s', (datetime.utcnow(), user_id))
                
                # Store session info (optional, if you use user_sessions table for OIDC too)
                ip_address = request.remote_addr
                user_agent = request.headers.get('User-Agent', '')
                session_token_uuid = str(uuid.uuid4()) # Different from app_token
                expires_at = datetime.utcnow() + app.config['JWT_EXPIRATION_DELTA']
                
                cur.execute(
                    'INSERT INTO user_sessions (user_id, session_token, expires_at, ip_address, user_agent, login_method) VALUES (%s, %s, %s, %s, %s, %s)',
                    (user_id, session_token_uuid, expires_at, ip_address, user_agent, 'oidc')
                )
                
                conn.commit()

                # Redirect to frontend with the token.
                # The frontend should then store this token and use it for API calls.
                frontend_url = os.environ.get('FRONTEND_URL', app.config.get('APP_BASE_URL', 'http://localhost:8080')).rstrip('/')
                # A dedicated redirect handler page on the frontend is good practice.
                redirect_target = f"{frontend_url}/auth-redirect.html?token={app_token}"
                if is_new_user:
                    redirect_target += "&new_user=true"
                
                logger.info(f"[OIDC_CALLBACK] Attempting to redirect to frontend target: {redirect_target}")
                return redirect(redirect_target)
            else:
                logger.error("[OIDC_CALLBACK] User ID not established after DB operations.")
                frontend_login_url = os.environ.get('FRONTEND_URL', 'http://localhost:8080').rstrip('/') + "/login.html"
                return redirect(f"{frontend_login_url}?oidc_error=user_processing_failed")

    except psycopg2.Error as db_err:
        logger.error(f"OIDC callback: Database error: {db_err}")
        if conn:
            conn.rollback()
        frontend_login_url = os.environ.get('FRONTEND_URL', 'http://localhost:8080').rstrip('/') + "/login.html"
        return redirect(f"{frontend_login_url}?oidc_error=db_error")
    except Exception as e:
        logger.error(f"OIDC callback: General error: {e}", exc_info=True)
        if conn:
            conn.rollback()
        frontend_login_url = os.environ.get('FRONTEND_URL', 'http://localhost:8080').rstrip('/') + "/login.html"
        return redirect(f"{frontend_login_url}?oidc_error=internal_error")
    finally:
        if conn:
            release_db_connection(conn)

# Authentication routes
@app.route('/api/auth/register', methods=['POST'])
def register():
    conn = None
    try:
        data = request.get_json()
        
        # Check if registration is enabled
        conn = get_db_connection()
        with conn.cursor() as cur:
            # Check if settings table exists
            cur.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'site_settings'
                )
            """)
            table_exists = cur.fetchone()[0]
            
            registration_enabled = True
            if table_exists:
                # Get registration_enabled setting
                cur.execute("SELECT value FROM site_settings WHERE key = 'registration_enabled'")
                result = cur.fetchone()
                
                if result:
                    registration_enabled = result[0].lower() == 'true'
            
            # Check if there are any users (first user can register regardless of setting)
            cur.execute('SELECT COUNT(*) FROM users')
            user_count = cur.fetchone()[0]
            
            # If registration is disabled and this is not the first user, return error
            if not registration_enabled and user_count > 0:
                return jsonify({'message': 'Registration is currently disabled!'}), 403
        
        # Validate required fields
        required_fields = ['username', 'email', 'password']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({'message': f'{field} is required!'}), 400
        
        username = data['username']
        email = data['email']
        password = data['password']
        first_name = data.get('first_name', '')
        last_name = data.get('last_name', '')
        
        # Validate email format
        if not is_valid_email(email):
            return jsonify({'message': 'Invalid email format!'}), 400
        
        # Validate password strength
        if not is_valid_password(password):
            return jsonify({'message': 'Password must be at least 8 characters and include uppercase, lowercase, and numbers!'}), 400
        
        # Hash the password
        password_hash = bcrypt.generate_password_hash(password).decode('utf-8')
        
        with conn.cursor() as cur:
            # Check if username or email already exists
            cur.execute('SELECT id FROM users WHERE username = %s OR email = %s', (username, email))
            existing_user = cur.fetchone()
            
            if existing_user:
                return jsonify({'message': 'Username or email already exists!'}), 409
            
            # Check if this is the first user (who will be an admin)
            cur.execute('SELECT COUNT(*) FROM users')
            user_count = cur.fetchone()[0]
            is_admin = user_count == 0
            
            # Insert new user
            cur.execute(
                'INSERT INTO users (username, email, password_hash, first_name, last_name, is_admin) VALUES (%s, %s, %s, %s, %s, %s) RETURNING id',
                (username, email, password_hash, first_name, last_name, is_admin)
            )
            user_id = cur.fetchone()[0]
            
            # Generate token
            token = generate_token(user_id)
            
            # Update last login
            cur.execute('UPDATE users SET last_login = %s WHERE id = %s', (datetime.utcnow(), user_id))
            
            # Store session info
            ip_address = request.remote_addr
            user_agent = request.headers.get('User-Agent', '')
            session_token = str(uuid.uuid4())
            expires_at = datetime.utcnow() + app.config['JWT_EXPIRATION_DELTA']
            
            cur.execute(
                'INSERT INTO user_sessions (user_id, session_token, expires_at, ip_address, user_agent, login_method) VALUES (%s, %s, %s, %s, %s, %s)',
                (user_id, session_token, expires_at, ip_address, user_agent, 'local')
            )
            
            conn.commit()
            
            return jsonify({
                'message': 'User registered successfully!',
                'token': token,
                'user': {
                    'id': user_id,
                    'username': username,
                    'email': email,
                    'is_admin': is_admin
                }
            }), 201
    except Exception as e:
        logger.error(f"Registration error: {e}")
        if conn:
            conn.rollback()
        return jsonify({'message': 'Registration failed!'}), 500
    finally:
        if conn:
            release_db_connection(conn)

@app.route('/api/auth/login', methods=['POST'])
def login():
    conn = None
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data.get('username') or not data.get('password'):
            return jsonify({'message': 'Username and password are required!'}), 400
        
        username = data['username']
        password = data['password']
        
        conn = get_db_connection()
        with conn.cursor() as cur:
            # Check if user exists - include is_admin in the query
            cur.execute('SELECT id, username, email, password_hash, is_active, is_admin FROM users WHERE username = %s OR email = %s', (username, username))
            user = cur.fetchone()
            
            if not user or not bcrypt.check_password_hash(user[3], password):
                return jsonify({'message': 'Invalid username or password!'}), 401
            
            if not user[4]:  # is_active
                return jsonify({'message': 'Account is inactive!'}), 401
            
            user_id = user[0]
            
            # Generate token
            token = generate_token(user_id)
            
            # Update last login
            cur.execute('UPDATE users SET last_login = %s WHERE id = %s', (datetime.utcnow(), user_id))
            
            # Store session info
            ip_address = request.remote_addr
            user_agent = request.headers.get('User-Agent', '')
            session_token = str(uuid.uuid4())
            expires_at = datetime.utcnow() + app.config['JWT_EXPIRATION_DELTA']
            
            cur.execute(
                'INSERT INTO user_sessions (user_id, session_token, expires_at, ip_address, user_agent, login_method) VALUES (%s, %s, %s, %s, %s, %s)',
                (user_id, session_token, expires_at, ip_address, user_agent, 'local')
            )
            
            conn.commit()
            
            return jsonify({
                'message': 'Login successful!',
                'token': token,
                'user': {
                    'id': user_id,
                    'username': user[1],
                    'email': user[2],
                    'is_admin': user[5]  # Include is_admin flag
                }
            }), 200
    except Exception as e:
        logger.error(f"Login error: {e}")
        if conn:
            conn.rollback()
        return jsonify({'message': 'Login failed!'}), 500
    finally:
        if conn:
            release_db_connection(conn)

@app.route('/api/auth/logout', methods=['POST'])
@token_required
def logout():
    conn = None
    try:
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
        else:
            return jsonify({'message': 'No token provided!'}), 400
        
        user_id = request.user['id']
        
        conn = get_db_connection()
        with conn.cursor() as cur:
            # Invalidate all sessions for this user
            cur.execute('DELETE FROM user_sessions WHERE user_id = %s', (user_id,))
            conn.commit()
            
            return jsonify({'message': 'Logout successful!'}), 200
    except Exception as e:
        logger.error(f"Logout error: {e}")
        if conn:
            conn.rollback()
        return jsonify({'message': 'Logout failed!'}), 500
    finally:
        if conn:
            release_db_connection(conn)

@app.route('/api/auth/validate-token', methods=['GET'])
@token_required
def validate_token():
    """Validate JWT token and return user info"""
    try:
        # If we got here, the token is valid (token_required decorator validated it)
        return jsonify({
            'valid': True,
            'user': {
                'id': request.user['id'],
                'username': request.user['username'],
                'email': request.user['email'],
                'is_admin': request.user['is_admin']
            },
            'message': 'Token is valid'
        }), 200
    except Exception as e:
        logger.error(f"Token validation error: {e}")
        return jsonify({
            'valid': False,
            'message': 'Invalid token'
        }), 401

@app.route('/api/auth/user', methods=['GET'])
@token_required
def get_user():
    conn = None
    try:
        user_id = request.user['id'] # Get user ID from the decorator

        # --- ADD DATABASE QUERY ---
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute(
                'SELECT id, username, email, first_name, last_name, is_admin FROM users WHERE id = %s',
                (user_id,)
            )
            user_data = cur.fetchone()
        # --- END DATABASE QUERY ---

        if not user_data:
             return jsonify({'message': 'User not found!'}), 404

        # Map database columns to a dictionary
        columns = ['id', 'username', 'email', 'first_name', 'last_name', 'is_admin']
        user_info = dict(zip(columns, user_data))

        # Return the full user information
        return jsonify(user_info), 200

    except Exception as e:
        logger.error(f"Get user error: {e}")
        # Optionally rollback if there was an error during DB interaction
        # if conn:
        #     conn.rollback() # Not strictly needed for SELECT, but good practice if errors occur
        return jsonify({'message': 'Failed to retrieve user information!'}), 500
    finally:
        # Release the connection back to the pool
        if conn:
            release_db_connection(conn)

@app.route('/api/auth/password/reset-request', methods=['POST'])
def request_password_reset():
    conn = None
    try:
        data = request.get_json()
        
        if not data.get('email'):
            return jsonify({'message': 'Email is required!'}), 400
        
        email = data['email']
        
        conn = get_db_connection()
        with conn.cursor() as cur:
            # Check if user exists
            cur.execute('SELECT id FROM users WHERE email = %s', (email,))
            user = cur.fetchone()
            
            if not user:
                # Don't reveal if email exists or not for security
                return jsonify({'message': 'If your email is registered, you will receive a password reset link.'}), 200
            
            user_id = user[0]
            
            # Generate reset token
            reset_token = str(uuid.uuid4())
            expires_at = datetime.utcnow() + timedelta(hours=24)
            
            # Delete any existing tokens for this user
            cur.execute('DELETE FROM password_reset_tokens WHERE user_id = %s', (user_id,))
            
            # Insert new token
            cur.execute(
                'INSERT INTO password_reset_tokens (user_id, token, expires_at) VALUES (%s, %s, %s)',
                (user_id, reset_token, expires_at)
            )
            
            conn.commit()

            # Get email base URL from settings
            email_base_url = 'http://localhost:8080' # Default fallback
            try:
                cur.execute("SELECT value FROM site_settings WHERE key = 'email_base_url'")
                result = cur.fetchone()
                if result:
                    email_base_url = result[0]
                else:
                    logger.warning("email_base_url setting not found for password reset, using default.")
            except Exception as e:
                 logger.error(f"Error fetching email_base_url from settings for password reset: {e}. Using default.")
            
            # Ensure base URL doesn't end with a slash
            email_base_url = email_base_url.rstrip('/')

            # Construct the full reset link
            reset_link = f"{email_base_url}/reset-password.html?token={reset_token}" # Use base URL and correct page
            
            # Send password reset email
            logger.info(f"Password reset requested for user {user_id}. Preparing to send email.")
            try:
                send_password_reset_email(email, reset_link)
                logger.info(f"Password reset email initiated for {email}")
            except Exception as e:
                logger.error(f"Failed to send password reset email to {email}: {e}")
                # Even if email fails, don't tell the user. 
                # This prevents leaking information about registered emails or email server issues.
                # The user journey remains the same: "If registered, you'll get an email."
            
            # Always return success to the user, regardless of email success/failure
            return jsonify({
                'message': 'If your email is registered, you will receive a password reset link.'
            }), 200

    except Exception as e:
        logger.error(f"Password reset request error: {e}")
        if conn:
            conn.rollback()
        return jsonify({'message': 'Password reset request failed!'}), 500
    finally:
        if conn:
            release_db_connection(conn)

# Note: The actual reset_password function is defined earlier in the file.
# The duplicated block that caused the error has been removed.


# Update existing endpoints to use authentication

@app.route('/api/warranties', methods=['GET'])
@token_required
def get_warranties():
    conn = None
    try:
        user_id = request.user['id']
        # is_admin = request.user.get('is_admin', False) # Removed admin check

        conn = get_db_connection()
        with conn.cursor() as cur:
            # Always fetch warranties belonging to the logged-in user
            # Removed the if is_admin: block
            # Replaced warranty_years with warranty_duration_years, warranty_duration_months, warranty_duration_days
            cur.execute('''
                SELECT id, product_name, purchase_date, expiration_date, invoice_path, manual_path, other_document_path, product_url, notes,
                       purchase_price, user_id, created_at, updated_at, is_lifetime, vendor, warranty_type,
                       warranty_duration_years, warranty_duration_months, warranty_duration_days, product_photo_path
                FROM warranties 
                WHERE user_id = %s 
                ORDER BY CASE WHEN is_lifetime THEN 1 ELSE 0 END, expiration_date NULLS LAST, product_name
            ''', (user_id,))
                
            warranties = cur.fetchall()
            columns = [desc[0] for desc in cur.description]
            warranties_list = []
            
            for row in warranties:
                warranty_dict = dict(zip(columns, row))
                # Convert date objects to ISO format strings for JSON serialization
                for key, value in warranty_dict.items():
                    if isinstance(value, (datetime, date)):
                        warranty_dict[key] = value.isoformat()
                    # Convert Decimal objects to float for JSON serialization
                    elif isinstance(value, Decimal):
                        warranty_dict[key] = float(value)
                
                # Get serial numbers for this warranty
                warranty_id = warranty_dict['id']
                cur.execute('SELECT serial_number FROM serial_numbers WHERE warranty_id = %s', (warranty_id,))
                serial_numbers = [row[0] for row in cur.fetchall()]
                warranty_dict['serial_numbers'] = serial_numbers
                
                # Get tags for this warranty (show all associated tags the user can see via warranty access)
                cur.execute('''
                    SELECT t.id, t.name, t.color
                    FROM tags t
                    JOIN warranty_tags wt ON t.id = wt.tag_id
                    WHERE wt.warranty_id = %s -- Removed user_id/is_admin filter here
                    ORDER BY t.name
                ''', (warranty_id,))
                tags = [{'id': t[0], 'name': t[1], 'color': t[2]} for t in cur.fetchall()]
                warranty_dict['tags'] = tags
                
                warranties_list.append(warranty_dict)
                
            return jsonify(warranties_list)
    except Exception as e:
        logger.error(f"Error retrieving warranties: {e}")
        return jsonify({"error": "Failed to retrieve warranties"}), 500
    finally:
        if conn:
            release_db_connection(conn)

@app.route('/api/warranties', methods=['POST'])
@token_required
def add_warranty():
    conn = None
    try:
        # Validate input data
        if not request.form.get('product_name'):
            return jsonify({"error": "Product name is required"}), 400
            
        if not request.form.get('purchase_date'):
            return jsonify({"error": "Purchase date is required"}), 400

        # Handle lifetime warranty
        is_lifetime = request.form.get('is_lifetime', 'false').lower() == 'true'
        expiration_date = None
        warranty_duration_years = 0
        warranty_duration_months = 0
        warranty_duration_days = 0

        if not is_lifetime:
            # Check if exact expiration date is provided
            exact_expiration_date = request.form.get('exact_expiration_date')
            
            if exact_expiration_date:
                # Use exact expiration date provided by user
                try:
                    expiration_date = datetime.strptime(exact_expiration_date, '%Y-%m-%d').date()
                    logger.info(f"Using exact expiration date: {expiration_date}")
                    # Set duration fields to 0 when using exact date
                    warranty_duration_years = 0
                    warranty_duration_months = 0
                    warranty_duration_days = 0
                except ValueError:
                    return jsonify({"error": "Invalid exact expiration date format. Use YYYY-MM-DD"}), 400
            else:
                # Use duration-based calculation (existing logic)
                try:
                    # Handle empty strings explicitly, default to 0
                    years_str = request.form.get('warranty_duration_years', '0')
                    months_str = request.form.get('warranty_duration_months', '0')
                    days_str = request.form.get('warranty_duration_days', '0')
                    
                    warranty_duration_years = int(years_str) if years_str else 0
                    warranty_duration_months = int(months_str) if months_str else 0
                    warranty_duration_days = int(days_str) if days_str else 0

                    if warranty_duration_years < 0 or warranty_duration_months < 0 or warranty_duration_days < 0:
                        return jsonify({"error": "Warranty duration components cannot be negative."}), 400
                    if warranty_duration_months >= 12:
                        return jsonify({"error": "Warranty months must be less than 12."}), 400
                    # Add a reasonable upper limit for days, e.g., 365, though relativedelta handles it.
                    if warranty_duration_days >= 366: # A bit more than a typical month
                        return jsonify({"error": "Warranty days seem too high."}), 400
                    if warranty_duration_years == 0 and warranty_duration_months == 0 and warranty_duration_days == 0:
                        return jsonify({"error": "Warranty duration must be specified for non-lifetime warranties."}), 400
                    if warranty_duration_years > 100: # Keep a reasonable upper limit for years
                         return jsonify({"error": "Warranty years must be 100 or less"}), 400

                except ValueError:
                    return jsonify({"error": "Warranty duration components must be valid numbers."}), 400
        
        # Process the data
        product_name = request.form['product_name']
        purchase_date_str = request.form['purchase_date']
        serial_numbers = request.form.getlist('serial_numbers[]')
        product_url = request.form.get('product_url', '')
        user_id = request.user['id']
        notes = request.form.get('notes', '')
        vendor = request.form.get('vendor', None)
        warranty_type = request.form.get('warranty_type', None)
        
        # Get tag IDs if provided
        tag_ids = []
        if request.form.get('tag_ids'):
            try:
                tag_ids = json.loads(request.form.get('tag_ids'))
                if not isinstance(tag_ids, list):
                    return jsonify({"error": "tag_ids must be a JSON array"}), 400
            except json.JSONDecodeError:
                return jsonify({"error": "tag_ids must be a valid JSON array"}), 400
        
        # Handle purchase price (optional)
        purchase_price = None
        if request.form.get('purchase_price'):
            try:
                purchase_price = float(request.form.get('purchase_price'))
                if purchase_price < 0:
                    return jsonify({"error": "Purchase price cannot be negative"}), 400
            except ValueError:
                return jsonify({"error": "Purchase price must be a valid number"}), 400
        
        try:
            purchase_date = datetime.strptime(purchase_date_str, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400
            
        # Calculate expiration date only if not lifetime
        if not is_lifetime:
            # Check if exact expiration date is provided
            exact_expiration_date = request.form.get('exact_expiration_date')
            
            if exact_expiration_date:
                # Use exact expiration date provided by user
                try:
                    expiration_date = datetime.strptime(exact_expiration_date, '%Y-%m-%d').date()
                    logger.info(f"Using exact expiration date: {expiration_date}")
                except ValueError:
                    return jsonify({"error": "Invalid exact expiration date format. Use YYYY-MM-DD"}), 400
            elif warranty_duration_years > 0 or warranty_duration_months > 0 or warranty_duration_days > 0:
                # Use duration-based calculation
                try:
                    expiration_date = purchase_date + relativedelta(
                        years=warranty_duration_years,
                        months=warranty_duration_months,
                        days=warranty_duration_days
                    )
                    logger.info(f"Calculated expiration date: {expiration_date} from years={warranty_duration_years}, months={warranty_duration_months}, days={warranty_duration_days}")
                except Exception as calc_err:
                    logger.error(f"Error calculating expiration date: {calc_err}")
                    return jsonify({"error": "Failed to calculate expiration date from duration components"}), 500
            else:
                # Neither exact date nor duration provided
                return jsonify({"error": "Either exact expiration date or warranty duration must be specified for non-lifetime warranties."}), 400
        
        # Handle invoice file upload
        db_invoice_path = None
        if 'invoice' in request.files:
            invoice = request.files['invoice']
            if invoice.filename != '':
                if not allowed_file(invoice.filename):
                    return jsonify({"error": "File type not allowed. Use PDF, PNG, JPG, or JPEG"}), 400
                    
                filename = secure_filename(invoice.filename)
                filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
                invoice_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                
                logger.info(f"Attempting to save invoice to: {invoice_path}")
                try:
                    invoice.save(invoice_path)
                    db_invoice_path = os.path.join('uploads', filename)
                    logger.info(f"Successfully saved invoice: {db_invoice_path}")
                except Exception as e:
                    logger.error(f"Error saving invoice {filename} to {invoice_path}: {e}")
                    # Optionally, decide if you want to return an error here or continue
                    return jsonify({"error": f"Failed to save invoice: {str(e)}"}), 500
        
        # Handle manual file upload
        db_manual_path = None
        if 'manual' in request.files:
            manual = request.files['manual']
            if manual.filename != '':
                if not allowed_file(manual.filename):
                    return jsonify({"error": "File type not allowed. Use PDF, PNG, JPG, or JPEG"}), 400
                    
                filename = secure_filename(manual.filename)
                filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_manual_{filename}"
                manual_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                logger.info(f"Attempting to save manual to: {manual_path}")
                try:
                    manual.save(manual_path)
                    db_manual_path = os.path.join('uploads', filename)
                    logger.info(f"Successfully saved manual: {db_manual_path}")
                except Exception as e:
                    logger.error(f"Error saving manual {filename} to {manual_path}: {e}")
                    return jsonify({"error": f"Failed to save manual: {str(e)}"}), 500
        
        # Handle other_document file upload
        db_other_document_path = None
        if 'other_document' in request.files:
            other_document = request.files['other_document']
            if other_document.filename != '':
                if not allowed_file(other_document.filename):
                    return jsonify({"error": "File type not allowed for other document. Use PDF, PNG, JPG, JPEG, ZIP, or RAR"}), 400
                    
                filename = secure_filename(other_document.filename)
                filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_other_{filename}"
                other_document_path_on_disk = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                logger.info(f"Attempting to save other_document to: {other_document_path_on_disk}")
                try:
                    other_document.save(other_document_path_on_disk)
                    db_other_document_path = os.path.join('uploads', filename)
                    logger.info(f"Successfully saved other_document: {db_other_document_path}")
                except Exception as e:
                    logger.error(f"Error saving other_document {filename} to {other_document_path_on_disk}: {e}")
                    return jsonify({"error": f"Failed to save other_document: {str(e)}"}), 500

        # Handle product photo file upload
        db_product_photo_path = None
        if 'product_photo' in request.files:
            product_photo = request.files['product_photo']
            if product_photo.filename != '':
                # Check if it's an image file
                if not (product_photo.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.webp', '.gif'))):
                    return jsonify({"error": "Product photo must be an image file (PNG, JPG, JPEG, WEBP, GIF)"}), 400
                    
                filename = secure_filename(product_photo.filename)
                filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_photo_{filename}"
                product_photo_path_on_disk = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                logger.info(f"Attempting to save product_photo to: {product_photo_path_on_disk}")
                try:
                    product_photo.save(product_photo_path_on_disk)
                    db_product_photo_path = os.path.join('uploads', filename)
                    logger.info(f"Successfully saved product_photo: {db_product_photo_path}")
                except Exception as e:
                    logger.error(f"Error saving product_photo {filename} to {product_photo_path_on_disk}: {e}")
                    return jsonify({"error": f"Failed to save product_photo: {str(e)}"}), 500

        # Save to database
        conn = get_db_connection()
        with conn.cursor() as cur:
            # Insert warranty
            cur.execute('''
                INSERT INTO warranties (
                    product_name, purchase_date, expiration_date, 
                    invoice_path, manual_path, other_document_path, product_url, purchase_price, user_id, is_lifetime, notes, vendor, warranty_type,
                    warranty_duration_years, warranty_duration_months, warranty_duration_days, product_photo_path
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            ''', (
                product_name, purchase_date, expiration_date,
                db_invoice_path, db_manual_path, db_other_document_path, product_url, purchase_price, user_id, is_lifetime, notes, vendor, warranty_type,
                warranty_duration_years, warranty_duration_months, warranty_duration_days, db_product_photo_path
            ))
            warranty_id = cur.fetchone()[0]
            
            # Insert serial numbers
            if serial_numbers:
                for serial_number in serial_numbers:
                    if serial_number.strip():  # Only insert non-empty serial numbers
                        cur.execute('''
                            INSERT INTO serial_numbers (warranty_id, serial_number)
                            VALUES (%s, %s)
                        ''', (warranty_id, serial_number.strip()))
            
            # Insert tags if provided
            if tag_ids:
                for tag_id in tag_ids:
                    # Verify tag exists
                    cur.execute('SELECT id FROM tags WHERE id = %s', (tag_id,))
                    if cur.fetchone():
                        cur.execute('''
                            INSERT INTO warranty_tags (warranty_id, tag_id)
                            VALUES (%s, %s)
                        ''', (warranty_id, tag_id))
                    else:
                        logger.warning(f"Skipping non-existent tag ID: {tag_id}")
            
            conn.commit()
            
        return jsonify({
            'message': 'Warranty added successfully',
            'id': warranty_id
        }), 201
        
    except Exception as e:
        logger.error(f"Error adding warranty: {e}")
        if conn:
            conn.rollback()
        return jsonify({"error": "Failed to add warranty"}), 500
    finally:
        if conn:
            release_db_connection(conn)

@app.route('/api/warranties/<int:warranty_id>', methods=['DELETE'])
@token_required
def delete_warranty(warranty_id):
    conn = None
    try:
        user_id = request.user['id']
        is_admin = request.user['is_admin']
        
        conn = get_db_connection()
        with conn.cursor() as cur:
            # Check if warranty exists and belongs to the user
            if is_admin:
                cur.execute('SELECT id FROM warranties WHERE id = %s', (warranty_id,))
            else:
                cur.execute('SELECT id FROM warranties WHERE id = %s AND user_id = %s', (warranty_id, user_id))
                
            warranty = cur.fetchone()
            
            if not warranty:
                return jsonify({"error": "Warranty not found or you don't have permission to delete it"}), 404
            
            # First get the file paths to delete the files
            cur.execute('SELECT invoice_path, manual_path, other_document_path, product_photo_path FROM warranties WHERE id = %s', (warranty_id,))
            result = cur.fetchone()
            
            invoice_path = result[0]
            manual_path = result[1]
            other_document_path = result[2]
            product_photo_path = result[3]
            
            # Delete the warranty from database
            cur.execute('DELETE FROM warranties WHERE id = %s', (warranty_id,))
            deleted_rows = cur.rowcount
            conn.commit()
            
            # Delete the invoice file if it exists
            if invoice_path:
                full_path = os.path.join('/data', invoice_path)
                if os.path.exists(full_path):
                    os.remove(full_path)
            
            # Delete the manual file if it exists
            if manual_path:
                full_path = os.path.join('/data', manual_path)
                if os.path.exists(full_path):
                    os.remove(full_path)
            
            # Delete the other_document file if it exists
            if other_document_path:
                full_path = os.path.join('/data', other_document_path)
                if os.path.exists(full_path):
                    os.remove(full_path)
            
            # Delete the product photo file if it exists
            if product_photo_path:
                full_path = os.path.join('/data', product_photo_path)
                if os.path.exists(full_path):
                    os.remove(full_path)

            return jsonify({"message": "Warranty deleted successfully"}), 200
            
    except Exception as e:
        logger.error(f"Error deleting warranty: {e}")
        if conn:
            conn.rollback()
        return jsonify({"error": "Failed to delete warranty"}), 500
    finally:
        if conn:
            release_db_connection(conn)

@app.route('/api/warranties/<int:warranty_id>', methods=['PUT'])
@token_required
def update_warranty(warranty_id):
    # --- Log function entry ---
    logger.info(f"Entering update_warranty function for ID: {warranty_id}") 
    conn = None
    try:
        user_id = request.user['id']
        is_admin = request.user['is_admin']
        conn = get_db_connection()
        with conn.cursor() as cur:
            # Check if warranty exists and belongs to the user
            if is_admin:
                cur.execute('SELECT id FROM warranties WHERE id = %s', (warranty_id,))
            else:
                cur.execute('SELECT id FROM warranties WHERE id = %s AND user_id = %s', (warranty_id, user_id))
            warranty = cur.fetchone()
            if not warranty:
                return jsonify({"error": "Warranty not found or you don't have permission to update it"}), 404

            # --- PATCH: Support JSON-only notes update ---
            if request.is_json and 'notes' in request.json and len(request.json) == 1:
                notes = request.json.get('notes', None)
                cur.execute("UPDATE warranties SET notes = %s, updated_at = NOW() WHERE id = %s", (notes, warranty_id))
                conn.commit()
                return jsonify({"message": "Notes updated successfully"}), 200

            # --- Otherwise, continue with the original (form-based) update logic ---
            # Validate input data similar to the add_warranty route
            if not request.form.get('product_name'):
                return jsonify({"error": "Product name is required"}), 400
            if not request.form.get('purchase_date'):
                return jsonify({"error": "Purchase date is required"}), 400
            logger.info(f"Received update request for warranty {warranty_id}")
            logger.info(f"Received update request for warranty {warranty_id}")
            is_lifetime = request.form.get('is_lifetime', 'false').lower() == 'true'
            logger.info(f"Parsed is_lifetime as: {is_lifetime}")
            purchase_date_str = request.form['purchase_date']
            try:
                purchase_date = datetime.strptime(purchase_date_str, '%Y-%m-%d').date() # Use .date()
            except ValueError:
                return jsonify({"error": "Invalid date format for purchase date. Use YYYY-MM-DD"}), 400

            expiration_date = None
            warranty_duration_years = 0
            warranty_duration_months = 0
            warranty_duration_days = 0

            if not is_lifetime:
                # Check if exact expiration date is provided
                exact_expiration_date = request.form.get('exact_expiration_date')
                
                if exact_expiration_date:
                    # Use exact expiration date provided by user
                    try:
                        expiration_date = datetime.strptime(exact_expiration_date, '%Y-%m-%d').date()
                        logger.info(f"Using exact expiration date: {expiration_date}")
                        # Set duration fields to 0 when using exact date
                        warranty_duration_years = 0
                        warranty_duration_months = 0
                        warranty_duration_days = 0
                    except ValueError:
                        return jsonify({"error": "Invalid exact expiration date format. Use YYYY-MM-DD"}), 400
                else:
                    # Use duration-based calculation (existing logic)
                    try:
                        # Handle empty strings explicitly, default to 0
                        years_str = request.form.get('warranty_duration_years', '0')
                        months_str = request.form.get('warranty_duration_months', '0')
                        days_str = request.form.get('warranty_duration_days', '0')
                        
                        warranty_duration_years = int(years_str) if years_str else 0
                        warranty_duration_months = int(months_str) if months_str else 0
                        warranty_duration_days = int(days_str) if days_str else 0

                        if warranty_duration_years < 0 or warranty_duration_months < 0 or warranty_duration_days < 0:
                            return jsonify({"error": "Warranty duration components cannot be negative."}), 400
                        if warranty_duration_months >= 12:
                            return jsonify({"error": "Warranty months must be less than 12."}), 400
                        # Add a reasonable upper limit for days, e.g., 365, though relativedelta handles it.
                        if warranty_duration_days >= 366: # A bit more than a typical month
                            return jsonify({"error": "Warranty days seem too high."}), 400
                        if warranty_duration_years == 0 and warranty_duration_months == 0 and warranty_duration_days == 0:
                            return jsonify({"error": "Warranty duration must be specified for non-lifetime warranties."}), 400
                        if warranty_duration_years > 100: # Keep a reasonable upper limit for years
                             return jsonify({"error": "Warranty years must be 100 or less"}), 400

                    except ValueError:
                        return jsonify({"error": "Warranty duration components must be valid numbers."}), 400
                
                # Calculate expiration date based on duration only if exact date wasn't provided
                if not exact_expiration_date:
                    if warranty_duration_years > 0 or warranty_duration_months > 0 or warranty_duration_days > 0:
                        try:
                            expiration_date = purchase_date + relativedelta(
                                years=warranty_duration_years,
                                months=warranty_duration_months,
                                days=warranty_duration_days
                            )
                            logger.info(f"Calculated expiration date: {expiration_date} from years={warranty_duration_years}, months={warranty_duration_months}, days={warranty_duration_days}")
                        except Exception as calc_err:
                            logger.error(f"Error calculating expiration date: {calc_err}")
                            return jsonify({"error": "Failed to calculate expiration date from duration components"}), 500
                    else:
                        return jsonify({"error": "Either exact expiration date or warranty duration must be specified for non-lifetime warranties."}), 400
            
            logger.info(f"Calculated values: Y={warranty_duration_years}, M={warranty_duration_months}, D={warranty_duration_days}, expiration_date={expiration_date}")
            product_name = request.form['product_name']
            serial_numbers = request.form.getlist('serial_numbers[]') # Ensure correct parsing for lists
            product_url = request.form.get('product_url', '')
            notes = request.form.get('notes', None)
            vendor = request.form.get('vendor', None)
            warranty_type = request.form.get('warranty_type', None)
            tag_ids = []
            if request.form.get('tag_ids'):
                try:
                    tag_ids = json.loads(request.form.get('tag_ids'))
                    if not isinstance(tag_ids, list):
                        return jsonify({"error": "tag_ids must be a JSON array"}), 400
                except json.JSONDecodeError:
                    return jsonify({"error": "tag_ids must be a valid JSON array"}), 400
            purchase_price = None
            if request.form.get('purchase_price'):
                try:
                    purchase_price = float(request.form.get('purchase_price'))
                    if purchase_price < 0:
                        return jsonify({"error": "Purchase price cannot be negative"}), 400
                except ValueError:
                    return jsonify({"error": "Purchase price must be a valid number"}), 400
            db_invoice_path = None
            if 'invoice' in request.files:
                invoice = request.files['invoice']
                if invoice.filename != '':
                    if not allowed_file(invoice.filename):
                        return jsonify({"error": "File type not allowed. Use PDF, PNG, JPG, or JPEG"}), 400
                    cur.execute('SELECT invoice_path FROM warranties WHERE id = %s', (warranty_id,))
                    old_invoice_path = cur.fetchone()[0]
                    if old_invoice_path:
                        full_path = os.path.join('/data', old_invoice_path)
                        if os.path.exists(full_path):
                            try:
                                os.remove(full_path)
                                logger.info(f"Deleted old invoice: {full_path}")
                            except Exception as e:
                                logger.error(f"Error deleting old invoice: {e}")
                    filename = secure_filename(invoice.filename)
                    filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
                    invoice_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    logger.info(f"Attempting to save updated invoice to: {invoice_path}")
                    try:
                        invoice.save(invoice_path)
                        db_invoice_path = os.path.join('uploads', filename)
                        logger.info(f"Successfully saved updated invoice: {db_invoice_path}")
                    except Exception as e:
                        logger.error(f"Error saving updated invoice {filename} to {invoice_path}: {e}")
                        return jsonify({"error": f"Failed to save updated invoice: {str(e)}"}), 500
            elif request.form.get('delete_invoice', 'false').lower() == 'true':
                cur.execute('SELECT invoice_path FROM warranties WHERE id = %s', (warranty_id,))
                old_invoice_path = cur.fetchone()[0]
                if old_invoice_path:
                    full_path = os.path.join('/data', old_invoice_path)
                    if os.path.exists(full_path):
                        try:
                            os.remove(full_path)
                            logger.info(f"Deleted invoice (delete request): {full_path}")
                        except Exception as e:
                            logger.error(f"Error deleting invoice (delete request): {e}")
                db_invoice_path = None  # Set to None to clear in DB
            db_manual_path = None
            if 'manual' in request.files:
                manual = request.files['manual']
                if manual.filename != '':
                    if not allowed_file(manual.filename):
                        return jsonify({"error": "File type not allowed. Use PDF, PNG, JPG, or JPEG"}), 400
                    cur.execute('SELECT manual_path FROM warranties WHERE id = %s', (warranty_id,))
                    old_manual_path = cur.fetchone()[0]
                    if old_manual_path:
                        full_path = os.path.join('/data', old_manual_path)
                        if os.path.exists(full_path):
                            try:
                                os.remove(full_path)
                                logger.info(f"Deleted old manual: {full_path}")
                            except Exception as e:
                                logger.error(f"Error deleting old manual: {e}")
                    filename = secure_filename(manual.filename)
                    filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_manual_{filename}"
                    manual_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    logger.info(f"Attempting to save updated manual to: {manual_path}")
                    try:
                        manual.save(manual_path)
                        db_manual_path = os.path.join('uploads', filename)
                        logger.info(f"Successfully saved updated manual: {db_manual_path}")
                    except Exception as e:
                        logger.error(f"Error saving updated manual {filename} to {manual_path}: {e}")
                        return jsonify({"error": f"Failed to save updated manual: {str(e)}"}), 500
            elif request.form.get('delete_manual', 'false').lower() == 'true':
                cur.execute('SELECT manual_path FROM warranties WHERE id = %s', (warranty_id,))
                old_manual_path = cur.fetchone()[0]
                if old_manual_path:
                    full_path = os.path.join('/data', old_manual_path)
                    if os.path.exists(full_path):
                        try:
                            os.remove(full_path)
                            logger.info(f"Deleted manual (delete request): {full_path}")
                        except Exception as e:
                            logger.error(f"Error deleting manual (delete request): {e}")
                db_manual_path = None  # Set to None to clear in DB
            
            db_other_document_path = None
            if 'other_document' in request.files:
                other_document = request.files['other_document']
                if other_document.filename != '':
                    if not allowed_file(other_document.filename):
                        return jsonify({"error": "File type not allowed for other document. Use PDF, PNG, JPG, JPEG, ZIP, or RAR"}), 400
                    cur.execute('SELECT other_document_path FROM warranties WHERE id = %s', (warranty_id,))
                    old_other_document_path = cur.fetchone()[0]
                    if old_other_document_path:
                        full_path = os.path.join('/data', old_other_document_path)
                        if os.path.exists(full_path):
                            try:
                                os.remove(full_path)
                                logger.info(f"Deleted old other_document: {full_path}")
                            except Exception as e:
                                logger.error(f"Error deleting old other_document: {e}")
                    filename = secure_filename(other_document.filename)
                    filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_other_{filename}"
                    other_document_path_on_disk = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    logger.info(f"Attempting to save updated other_document to: {other_document_path_on_disk}")
                    try:
                        other_document.save(other_document_path_on_disk)
                        db_other_document_path = os.path.join('uploads', filename)
                        logger.info(f"Successfully saved updated other_document: {db_other_document_path}")
                    except Exception as e:
                        logger.error(f"Error saving updated other_document {filename} to {other_document_path_on_disk}: {e}")
                        return jsonify({"error": f"Failed to save updated other_document: {str(e)}"}), 500
            elif request.form.get('delete_other_document', 'false').lower() == 'true':
                cur.execute('SELECT other_document_path FROM warranties WHERE id = %s', (warranty_id,))
                old_other_document_path = cur.fetchone()[0]
                if old_other_document_path:
                    full_path = os.path.join('/data', old_other_document_path)
                    if os.path.exists(full_path):
                        try:
                            os.remove(full_path)
                            logger.info(f"Deleted other_document (delete request): {full_path}")
                        except Exception as e:
                            logger.error(f"Error deleting other_document (delete request): {e}")
                db_other_document_path = None # Set to None to clear in DB

            # Handle product photo file upload
            db_product_photo_path = None
            if 'product_photo' in request.files:
                product_photo = request.files['product_photo']
                if product_photo.filename != '':
                    # Check if it's an image file
                    if not (product_photo.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.webp', '.gif'))):
                        return jsonify({"error": "Product photo must be an image file (PNG, JPG, JPEG, WEBP, GIF)"}), 400
                    
                    # Delete old photo if it exists
                    cur.execute('SELECT product_photo_path FROM warranties WHERE id = %s', (warranty_id,))
                    old_product_photo_path = cur.fetchone()[0]
                    if old_product_photo_path:
                        full_path = os.path.join('/data', old_product_photo_path)
                        if os.path.exists(full_path):
                            try:
                                os.remove(full_path)
                                logger.info(f"Deleted old product_photo: {full_path}")
                            except Exception as e:
                                logger.error(f"Error deleting old product_photo: {e}")
                    
                    filename = secure_filename(product_photo.filename)
                    filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_photo_{filename}"
                    product_photo_path_on_disk = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    logger.info(f"Attempting to save updated product_photo to: {product_photo_path_on_disk}")
                    try:
                        product_photo.save(product_photo_path_on_disk)
                        db_product_photo_path = os.path.join('uploads', filename)
                        logger.info(f"Successfully saved updated product_photo: {db_product_photo_path}")
                    except Exception as e:
                        logger.error(f"Error saving updated product_photo {filename} to {product_photo_path_on_disk}: {e}")
                        return jsonify({"error": f"Failed to save updated product_photo: {str(e)}"}), 500
            elif request.form.get('delete_product_photo', 'false').lower() == 'true':
                cur.execute('SELECT product_photo_path FROM warranties WHERE id = %s', (warranty_id,))
                old_product_photo_path = cur.fetchone()[0]
                if old_product_photo_path:
                    full_path = os.path.join('/data', old_product_photo_path)
                    if os.path.exists(full_path):
                        try:
                            os.remove(full_path)
                            logger.info(f"Deleted product_photo (delete request): {full_path}")
                        except Exception as e:
                            logger.error(f"Error deleting product_photo (delete request): {e}")
                db_product_photo_path = None  # Set to None to clear in DB

            update_params = {
                'product_name': product_name,
                'purchase_date': purchase_date,
                'is_lifetime': is_lifetime,
                'warranty_duration_years': warranty_duration_years,
                'warranty_duration_months': warranty_duration_months,
                'warranty_duration_days': warranty_duration_days,
                'expiration_date': expiration_date, # Will be None if lifetime
                'product_url': product_url,
                'purchase_price': purchase_price,
                'vendor': vendor,
                'warranty_type': warranty_type
            }
            sql_fields = []
            sql_values = []
            for key, value in update_params.items():
                sql_fields.append(f"{key} = %s")
                sql_values.append(value)
            if notes is not None:
                sql_fields.append("notes = %s")
                sql_values.append(notes)
            if db_invoice_path is not None:
                sql_fields.append("invoice_path = %s")
                sql_values.append(db_invoice_path)
            elif 'delete_invoice' in request.form and request.form.get('delete_invoice', 'false').lower() == 'true':
                sql_fields.append("invoice_path = NULL")
            if db_manual_path is not None:
                sql_fields.append("manual_path = %s")
                sql_values.append(db_manual_path)
            elif 'delete_manual' in request.form and request.form.get('delete_manual', 'false').lower() == 'true':
                sql_fields.append("manual_path = NULL")
            if db_other_document_path is not None:
                sql_fields.append("other_document_path = %s")
                sql_values.append(db_other_document_path)
            elif 'delete_other_document' in request.form and request.form.get('delete_other_document', 'false').lower() == 'true':
                sql_fields.append("other_document_path = NULL")
            if db_product_photo_path is not None:
                sql_fields.append("product_photo_path = %s")
                sql_values.append(db_product_photo_path)
            elif 'delete_product_photo' in request.form and request.form.get('delete_product_photo', 'false').lower() == 'true':
                sql_fields.append("product_photo_path = NULL")

            sql_fields.append("updated_at = NOW()") # Use SQL function, no parameter needed
            sql_values.append(warranty_id)
            update_sql = f"UPDATE warranties SET {', '.join(sql_fields)} WHERE id = %s"
            cur.execute(update_sql, sql_values)
            logger.info(f"Updated warranty with SQL: {update_sql}")
            logger.info(f"Parameters: {sql_values}")
            cur.execute('DELETE FROM serial_numbers WHERE warranty_id = %s', (warranty_id,))
            if serial_numbers:
                for serial_number in serial_numbers:
                    if serial_number.strip():  # Only insert non-empty serial numbers
                        cur.execute('''
                            INSERT INTO serial_numbers (warranty_id, serial_number)
                            VALUES (%s, %s)
                        ''', (warranty_id, serial_number.strip()))
            
            # Update tags if provided
            if tag_ids is not None:
                # Remove existing tags
                cur.execute('DELETE FROM warranty_tags WHERE warranty_id = %s', (warranty_id,))
                
                # Add new tags
                for tag_id in tag_ids:
                    # Verify tag exists
                    cur.execute('SELECT id FROM tags WHERE id = %s', (tag_id,))
                    if cur.fetchone():
                        cur.execute('''
                            INSERT INTO warranty_tags (warranty_id, tag_id)
                            VALUES (%s, %s)
                        ''', (warranty_id, tag_id))
                    else:
                        logger.warning(f"Skipping non-existent tag ID: {tag_id}")
            
            conn.commit()
            
            return jsonify({"message": "Warranty updated successfully"}), 200
            
    except Exception as e:
        logger.error(f"Error updating warranty: {e}")
        if conn:
            conn.rollback()
        return jsonify({"error": "Failed to update warranty"}), 500
    finally:
        if conn:
            release_db_connection(conn)

@app.route('/api/statistics', methods=['GET'])
@token_required
def get_statistics():
    user_id = request.user['id']
    conn = None

    try:
        conn = get_db_connection()
        today = date.today()

        # Fetch user preference for expiring soon days
        expiring_soon_days = 30 # Default value
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT expiring_soon_days FROM user_preferences WHERE user_id = %s", (user_id,))
                result = cur.fetchone()
                if result and result[0] is not None:
                    expiring_soon_days = result[0]
                    logger.info(f"Using custom expiring soon days: {expiring_soon_days} for user {user_id}")
                else:
                    logger.info(f"Using default expiring soon days: {expiring_soon_days} for user {user_id}")
        except Exception as pref_err:
             # Log error fetching preference but continue with default
            logger.error(f"Error fetching expiring_soon_days preference for user {user_id}: {pref_err}. Using default 30 days.")

        expiring_soon_date = today + timedelta(days=expiring_soon_days)
        ninety_days_later = today + timedelta(days=90) # Keep timeline fixed or make configurable? For now, keep at 90.

        # Build base query based on role
        from_clause = "FROM warranties w"
        where_clause = ""
        params = []
        active_where = "AND"

        if not request.user.get('is_admin', False):
            where_clause = "WHERE w.user_id = %s"
            params = [user_id]
            active_where = "AND"
        else:
            # Admin should only see their own warranties
            where_clause = "WHERE w.user_id = %s"
            params = [user_id]
            active_where = "AND"
        
        with conn.cursor() as cur:
            # Get total count
            cur.execute(f"SELECT COUNT(*) {from_clause} {where_clause}", params)
            total_count = cur.fetchone()[0]
            logger.info(f"Total warranties: {total_count}")
            
            # Get active count (includes lifetime)
            cur.execute(f"SELECT COUNT(*) {from_clause} {where_clause} {active_where if where_clause else 'WHERE'} (w.is_lifetime = TRUE OR w.expiration_date > %s)", params + [today])
            active_count = cur.fetchone()[0]
            logger.info(f"Active warranties: {active_count}")
            
            # Get expired count (excludes lifetime)
            cur.execute(f"SELECT COUNT(*) {from_clause} {where_clause} {active_where if where_clause else 'WHERE'} w.is_lifetime = FALSE AND w.expiration_date <= %s", params + [today])
            expired_count = cur.fetchone()[0]
            logger.info(f"Expired warranties: {expired_count}")
            
            # Get expiring soon count (excludes lifetime) using user preference
            cur.execute(f"""SELECT COUNT(*) {from_clause} {where_clause} {active_where if where_clause else 'WHERE'}
                          w.is_lifetime = FALSE AND w.expiration_date > %s AND w.expiration_date <= %s""",
                      params + [today, expiring_soon_date])
            expiring_soon_count = cur.fetchone()[0]
            logger.info(f"Expiring soon ({expiring_soon_days} days) warranties: {expiring_soon_count}")
            
            # Get expiration timeline (next 90 days, excluding lifetime)
            cur.execute(f"""
                SELECT 
                    EXTRACT(YEAR FROM expiration_date) as year,
                    EXTRACT(MONTH FROM expiration_date) as month,
                    COUNT(*) as count
                {from_clause} 
                {where_clause} {active_where if where_clause else 'WHERE'} 
                w.is_lifetime = FALSE AND w.expiration_date > %s AND w.expiration_date <= %s
                GROUP BY EXTRACT(YEAR FROM expiration_date), EXTRACT(MONTH FROM expiration_date)
                ORDER BY year, month
            """, params + [today, ninety_days_later])
            
            timeline = []
            for row in cur.fetchall():
                year = int(row[0])
                month = int(row[1])
                count = row[2]
                timeline.append({
                    "year": year,
                    "month": month,
                    "count": count
                })
            
            # Get recent expiring warranties (using user preference +/- 30 days for range, excluding lifetime)
            # We'll keep the window around today somewhat fixed for 'recent', maybe +/- 30 days is still reasonable? Or should this also use expiring_soon_days?
            # Let's adjust the recent window based on the preference for now: N days ago to N days later
            days_ago_for_recent = today - timedelta(days=expiring_soon_days)
            days_later_for_recent = expiring_soon_date # Same as the expiring soon cutoff
            cur.execute(f"""
                SELECT
                    id, product_name, purchase_date, 
                    warranty_duration_years, warranty_duration_months, warranty_duration_days,
                    expiration_date, invoice_path, manual_path, other_document_path, product_url, purchase_price, is_lifetime
                {from_clause}
                {where_clause} {active_where if where_clause else 'WHERE'}
                w.is_lifetime = FALSE AND w.expiration_date >= %s AND w.expiration_date <= %s
                ORDER BY expiration_date
                LIMIT 10
            """, params + [days_ago_for_recent, days_later_for_recent])
            
            columns = [desc[0] for desc in cur.description]
            recent_warranties = []
            
            for row in cur.fetchall():
                warranty = dict(zip(columns, row))
                
                # Convert dates to string format
                if warranty['purchase_date']:
                    warranty['purchase_date'] = warranty['purchase_date'].isoformat()
                if warranty['expiration_date']:
                    warranty['expiration_date'] = warranty['expiration_date'].isoformat()
                
                # Convert Decimal objects to float for JSON serialization
                if warranty.get('purchase_price') and isinstance(warranty['purchase_price'], Decimal):
                    warranty['purchase_price'] = float(warranty['purchase_price'])
                    
                recent_warranties.append(warranty)
            
            # *** ADD CODE TO FETCH ALL WARRANTIES ***
            logger.info(f"Fetching all warranties for user {user_id}...")
            cur.execute(f"""
                SELECT
                    id, product_name, purchase_date, 
                    warranty_duration_years, warranty_duration_months, warranty_duration_days,
                    expiration_date, invoice_path, manual_path, other_document_path, product_url, purchase_price, is_lifetime
                {from_clause}
                {where_clause}
                ORDER BY expiration_date DESC
            """, params)

            all_columns = [desc[0] for desc in cur.description]
            all_warranties_list = []

            for row in cur.fetchall():
                warranty = dict(zip(all_columns, row))
                
                # Convert dates to string format
                if warranty.get('purchase_date') and isinstance(warranty['purchase_date'], date):
                    warranty['purchase_date'] = warranty['purchase_date'].isoformat()
                if warranty.get('expiration_date') and isinstance(warranty['expiration_date'], date):
                    warranty['expiration_date'] = warranty['expiration_date'].isoformat()
                
                # Convert Decimal objects to float for JSON serialization
                if warranty.get('purchase_price') and isinstance(warranty['purchase_price'], Decimal):
                    warranty['purchase_price'] = float(warranty['purchase_price'])
                    
                all_warranties_list.append(warranty)
            logger.info(f"Fetched {len(all_warranties_list)} total warranties.")
            # *** END OF ADDED CODE ***

            statistics = {
                'total': total_count,
                'active': active_count,
                'expired': expired_count,
                'expiring_soon': expiring_soon_count,
                'timeline': timeline,
                'recent_warranties': recent_warranties,
                'all_warranties': all_warranties_list  # <-- Add the new list here
            }
            
            return jsonify(convert_decimals(statistics))
    
    except Exception as e:
        logger.error(f"Error getting warranty statistics: {e}")
        return jsonify({"error": str(e)}), 500
    
    finally:
        if conn:
            release_db_connection(conn)

@app.route('/api/statistics/global', methods=['GET'])
@token_required
def get_global_statistics():
    """Get global warranty statistics for all users (with proper permissions check)"""
    conn = None
    try:
        # Check if global view is enabled for this user
        user_is_admin = request.user.get('is_admin', False)
        
        conn = get_db_connection()
        with conn.cursor() as cur:
            # Get both global view settings
            cur.execute("SELECT key, value FROM site_settings WHERE key IN ('global_view_enabled', 'global_view_admin_only')")
            settings = {row[0]: row[1] for row in cur.fetchall()}
            
            # Check if global view is enabled at all
            global_view_enabled = settings.get('global_view_enabled', 'true').lower() == 'true'
            if not global_view_enabled:
                return jsonify({"error": "Global view is disabled by administrator"}), 403
            
            # Check if global view is restricted to admins only
            admin_only = settings.get('global_view_admin_only', 'false').lower() == 'true'
            if admin_only and not user_is_admin:
                return jsonify({"error": "Global view is restricted to administrators only"}), 403
        
        # Release the connection since we'll get a new one below
        release_db_connection(conn)
        conn = None

        # Get user's expiring soon days preference (for consistency)
        user_id = request.user['id']
        expiring_soon_days = 30  # Default value
        
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT expiring_soon_days FROM user_preferences WHERE user_id = %s", (user_id,))
                result = cur.fetchone()
                if result and result[0] is not None:
                    expiring_soon_days = result[0]
        except Exception as pref_err:
            logger.error(f"Error fetching expiring_soon_days preference for user {user_id}: {pref_err}. Using default 30 days.")

        today = date.today()
        expiring_soon_date = today + timedelta(days=expiring_soon_days)
        ninety_days_later = today + timedelta(days=90)
        
        with conn.cursor() as cur:
            # Global statistics query - all warranties from all users
            
            # Get total count
            cur.execute("SELECT COUNT(*) FROM warranties w")
            total_count = cur.fetchone()[0]
            
            # Get active count (includes lifetime)
            cur.execute("SELECT COUNT(*) FROM warranties w WHERE w.is_lifetime = TRUE OR w.expiration_date > %s", (today,))
            active_count = cur.fetchone()[0]
            
            # Get expired count (excludes lifetime)
            cur.execute("SELECT COUNT(*) FROM warranties w WHERE w.is_lifetime = FALSE AND w.expiration_date <= %s", (today,))
            expired_count = cur.fetchone()[0]
            
            # Get expiring soon count (excludes lifetime)
            cur.execute("""SELECT COUNT(*) FROM warranties w WHERE
                          w.is_lifetime = FALSE AND w.expiration_date > %s AND w.expiration_date <= %s""",
                      (today, expiring_soon_date))
            expiring_soon_count = cur.fetchone()[0]
            
            # Get expiration timeline (next 90 days, excluding lifetime)
            cur.execute("""
                SELECT 
                    EXTRACT(YEAR FROM expiration_date) as year,
                    EXTRACT(MONTH FROM expiration_date) as month,
                    COUNT(*) as count
                FROM warranties w 
                WHERE w.is_lifetime = FALSE AND w.expiration_date > %s AND w.expiration_date <= %s
                GROUP BY EXTRACT(YEAR FROM expiration_date), EXTRACT(MONTH FROM expiration_date)
                ORDER BY year, month
            """, (today, ninety_days_later))
            
            timeline = []
            for row in cur.fetchall():
                year = int(row[0])
                month = int(row[1])
                count = row[2]
                timeline.append({
                    "year": year,
                    "month": month,
                    "count": count
                })
            
            # Get recent expiring warranties with user information
            days_ago_for_recent = today - timedelta(days=expiring_soon_days)
            days_later_for_recent = expiring_soon_date
            cur.execute("""
                SELECT
                    w.id, w.product_name, w.purchase_date, 
                    w.warranty_duration_years, w.warranty_duration_months, w.warranty_duration_days,
                    w.expiration_date, w.invoice_path, w.manual_path, w.other_document_path, 
                    w.product_url, w.purchase_price, w.is_lifetime,
                    u.username, u.email, u.first_name, u.last_name
                FROM warranties w
                JOIN users u ON w.user_id = u.id
                WHERE w.is_lifetime = FALSE AND w.expiration_date >= %s AND w.expiration_date <= %s
                ORDER BY w.expiration_date
                LIMIT 10
            """, (days_ago_for_recent, days_later_for_recent))
            
            columns = [desc[0] for desc in cur.description]
            recent_warranties = []
            
            for row in cur.fetchall():
                warranty = dict(zip(columns, row))
                
                # Convert dates to string format
                if warranty['purchase_date']:
                    warranty['purchase_date'] = warranty['purchase_date'].isoformat()
                if warranty['expiration_date']:
                    warranty['expiration_date'] = warranty['expiration_date'].isoformat()
                
                # Convert Decimal objects to float for JSON serialization
                if warranty.get('purchase_price') and isinstance(warranty['purchase_price'], Decimal):
                    warranty['purchase_price'] = float(warranty['purchase_price'])
                
                # Add user display information
                first_name = warranty.get('first_name', '').strip() if warranty.get('first_name') else ''
                last_name = warranty.get('last_name', '').strip() if warranty.get('last_name') else ''
                username = warranty.get('username', '').strip() if warranty.get('username') else ''
                
                if first_name and last_name:
                    display_name = f"{first_name} {last_name}"
                elif first_name:
                    display_name = first_name
                elif username:
                    display_name = username
                else:
                    display_name = 'Unknown User'
                
                warranty['user_display_name'] = display_name
                    
                recent_warranties.append(warranty)
            
            # Get all warranties with user information
            cur.execute("""
                SELECT
                    w.id, w.product_name, w.purchase_date, 
                    w.warranty_duration_years, w.warranty_duration_months, w.warranty_duration_days,
                    w.expiration_date, w.invoice_path, w.manual_path, w.other_document_path, 
                    w.product_url, w.purchase_price, w.is_lifetime,
                    u.username, u.email, u.first_name, u.last_name
                FROM warranties w
                JOIN users u ON w.user_id = u.id
                ORDER BY w.expiration_date DESC
            """)

            all_columns = [desc[0] for desc in cur.description]
            all_warranties_list = []

            for row in cur.fetchall():
                warranty = dict(zip(all_columns, row))
                
                # Convert dates to string format
                if warranty.get('purchase_date') and isinstance(warranty['purchase_date'], date):
                    warranty['purchase_date'] = warranty['purchase_date'].isoformat()
                if warranty.get('expiration_date') and isinstance(warranty['expiration_date'], date):
                    warranty['expiration_date'] = warranty['expiration_date'].isoformat()
                
                # Convert Decimal objects to float for JSON serialization
                if warranty.get('purchase_price') and isinstance(warranty['purchase_price'], Decimal):
                    warranty['purchase_price'] = float(warranty['purchase_price'])
                
                # Add user display name for better UI
                first_name = warranty.get('first_name', '').strip() if warranty.get('first_name') else ''
                last_name = warranty.get('last_name', '').strip() if warranty.get('last_name') else ''
                username = warranty.get('username', '').strip() if warranty.get('username') else ''
                
                if first_name and last_name:
                    display_name = f"{first_name} {last_name}"
                elif first_name:
                    display_name = first_name
                elif username:
                    display_name = username
                else:
                    display_name = 'Unknown User'
                
                warranty['user_display_name'] = display_name
                    
                all_warranties_list.append(warranty)

            statistics = {
                'total': total_count,
                'active': active_count,
                'expired': expired_count,
                'expiring_soon': expiring_soon_count,
                'timeline': timeline,
                'recent_warranties': recent_warranties,
                'all_warranties': all_warranties_list
            }
            
            return jsonify(convert_decimals(statistics))
    
    except Exception as e:
        logger.error(f"Error getting global warranty statistics: {e}")
        return jsonify({"error": str(e)}), 500
    
    finally:
        if conn:
            release_db_connection(conn)

@app.route('/api/test', methods=['GET'])
def test_endpoint():
    """Simple test endpoint to check if the API is responding."""
    return jsonify({
        "status": "success",
        "message": "API is working",
        "timestamp": datetime.utcnow().isoformat()
    })

# Public endpoint to check if authentication is required
@app.route('/api/auth/status', methods=['GET'])
def auth_status():
    return jsonify({
        "authentication_required": True,
        "message": "Authentication is required for most endpoints"
    })

@app.route('/api/auth/profile', methods=['PUT'])
@token_required
def update_profile():
    user_id = request.user['id']
    
    try:
        # Get request data
        data = request.get_json()
        if not data:
            return jsonify({'message': 'No input data provided'}), 400

        # Extract fields
        first_name = data.get('first_name', '').strip()
        last_name = data.get('last_name', '').strip()
        new_email = data.get('email', '').strip()

        # Validate input
        if not first_name or not last_name:
            return jsonify({'message': 'First name and last name are required'}), 400

        # Get database connection
        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            update_fields = ["first_name = %s", "last_name = %s"]
            update_params = [first_name, last_name]

            # Handle email change
            if new_email:
                if not is_valid_email(new_email):
                    conn.rollback()
                    return jsonify({'message': 'Invalid email format!'}), 400

                # Check if the new email is different from the current one
                cursor.execute("SELECT email FROM users WHERE id = %s", (user_id,))
                current_email_tuple = cur.fetchone()
                if not current_email_tuple:
                    conn.rollback()
                    return jsonify({'message': 'User not found while fetching current email.'}), 404
                current_email = current_email_tuple[0]

                if new_email.lower() != current_email.lower():
                    # Check if the new email is already in use by another user
                    cursor.execute("SELECT id FROM users WHERE LOWER(email) = LOWER(%s) AND id != %s", (new_email, user_id))
                    if cursor.fetchone():
                        conn.rollback()
                        return jsonify({'message': 'This email address is already in use by another account.'}), 409
                    update_fields.append("email = %s")
                    update_params.append(new_email)

            update_query_string = ", ".join(update_fields)
            final_query = f"""
                UPDATE users 
                SET {update_query_string}
                WHERE id = %s 
                RETURNING id, username, email, first_name, last_name, created_at
                """
            cursor.execute(final_query, tuple(update_params + [user_id]))

            # Get updated user data
            user_data = cursor.fetchone()
            if not user_data:
                conn.rollback()
                return jsonify({'message': 'User not found'}), 404

            conn.commit()

            user = {
                'id': user_data[0],
                'username': user_data[1],
                'email': user_data[2],
                'first_name': user_data[3],
                'last_name': user_data[4],
                'created_at': user_data[5].isoformat() if user_data[5] else None
            }
            return jsonify(user), 200

        except Exception as e:
            conn.rollback()
            logger.error(f"Database error in update_profile: {str(e)}")
            return jsonify({'message': 'Database error occurred'}), 500
        finally:
            cursor.close()
            release_db_connection(conn)

    except Exception as e:
        logger.error(f"Error in update_profile: {str(e)}")
        return jsonify({'message': 'An error occurred while updating profile'}), 500

@app.route('/api/auth/account', methods=['DELETE'])
@token_required
def delete_account():
    user_id = request.user['id']
    
    try:
        # Get database connection
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Begin transaction
            cursor.execute("BEGIN")
            
            # Delete user's warranties
            cursor.execute("DELETE FROM warranties WHERE user_id = %s", (user_id,))
            
            # Delete user's reset tokens if any
            cursor.execute("DELETE FROM password_reset_tokens WHERE user_id = %s", (user_id,))
            
            # Delete user's sessions if any
            cursor.execute('DELETE FROM user_sessions WHERE user_id = %s', (user_id,))
            sessions_deleted = cursor.rowcount
            logger.info(f"Deleted {sessions_deleted} sessions belonging to user {user_id}")

            # Delete user's tags
            cursor.execute('DELETE FROM tags WHERE user_id = %s', (user_id,))
            tags_deleted = cur.rowcount
            logger.info(f"Deleted {tags_deleted} tags belonging to user {user_id}")

            # Delete user
            cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
            user_deleted = cur.rowcount
            logger.info(f"Deleted user {user_id}, affected rows: {user_deleted}")
            
            # Commit transaction
            cursor.execute("COMMIT")
            
            return jsonify({'message': 'Account deleted successfully'}), 200
            
        except Exception as e:
            cursor.execute("ROLLBACK")
            logger.error(f"Database error in delete_account: {str(e)}")
            return jsonify({'message': 'Database error occurred'}), 500
        finally:
            cursor.close()
            release_db_connection(conn)
            
    except Exception as e:
        logger.error(f"Error in delete_account: {str(e)}")
        return jsonify({'message': 'An error occurred while deleting account'}), 500

@app.route('/api/auth/preferences', methods=['GET'])
@token_required
def get_preferences():
    user_id = request.user['id']
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            # Check for notification columns
            cursor.execute("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name='user_preferences' 
                AND column_name IN ('notification_channel', 'apprise_notification_time', 'apprise_notification_frequency', 'apprise_timezone')
            """)
            existing_columns = [row[0] for row in cursor.fetchall()]
            
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'user_preferences'
                )
            """)
            table_exists = cursor.fetchone()[0]
            if not table_exists:
                cursor.execute("""
                    CREATE TABLE user_preferences (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                        email_notifications BOOLEAN NOT NULL DEFAULT TRUE,
                        default_view VARCHAR(10) NOT NULL DEFAULT 'grid',
                        theme VARCHAR(10) NOT NULL DEFAULT 'light',
                        expiring_soon_days INTEGER NOT NULL DEFAULT 30,
                        notification_frequency VARCHAR(10) NOT NULL DEFAULT 'daily',
                        notification_time VARCHAR(5) NOT NULL DEFAULT '09:00',
                        timezone VARCHAR(50) NOT NULL DEFAULT 'UTC',
                        currency_symbol VARCHAR(8) DEFAULT '$',
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                        UNIQUE(user_id)
                    )
                """)
                cursor.execute("""
                    CREATE INDEX idx_user_preferences_user_id ON user_preferences(user_id)
                """)
                conn.commit()
                logger.info(f"Created user_preferences table")
            has_currency = has_currency_symbol_column(cursor)

            cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name='user_preferences' AND column_name='date_format'")
            has_date_format_col = cursor.fetchone() is not None

            has_notification_channel = 'notification_channel' in existing_columns
            has_apprise_notification_time = 'apprise_notification_time' in existing_columns
            has_apprise_notification_frequency = 'apprise_notification_frequency' in existing_columns

            # Build select list dynamically
            select_fields_list = ["email_notifications", "default_view", "theme", "expiring_soon_days", "notification_frequency", "notification_time", "timezone"]
            if has_notification_channel:
                select_fields_list.append("notification_channel")
            has_apprise_notification_time = 'apprise_notification_time' in existing_columns
            if has_apprise_notification_time:
                select_fields_list.append("apprise_notification_time")
            if 'apprise_timezone' in existing_columns:
                select_fields_list.append("apprise_timezone")
            has_apprise_notification_frequency = 'apprise_notification_frequency' in existing_columns
            if has_apprise_notification_frequency:
                select_fields_list.append("apprise_notification_frequency")
            if has_currency:
                select_fields_list.append("currency_symbol")
            if has_date_format_col:
                select_fields_list.append("date_format") # Add date_format if column exists
            select_fields = ", ".join(select_fields_list)

            cursor.execute(
                f"""
                SELECT {select_fields}
                FROM user_preferences
                WHERE user_id = %s
                """,
                (user_id,)
            )
            preferences_data = cursor.fetchone()
            
            if not preferences_data:
                # Build insert list dynamically
                insert_cols_list = ["user_id", "email_notifications", "default_view", "theme", "expiring_soon_days", "notification_frequency", "notification_time", "timezone"]
                insert_vals = [user_id, True, 'grid', 'light', 30, 'daily', '09:00', 'UTC']
                if has_notification_channel:
                    insert_cols_list.append("notification_channel")
                    insert_vals.append('email')  # Default to email notifications
                if has_apprise_notification_time:
                    insert_cols_list.append("apprise_notification_time")
                    insert_vals.append('09:00')
                if has_apprise_notification_frequency:
                    insert_cols_list.append("apprise_notification_frequency")
                    insert_vals.append('daily')
                if has_currency:
                    insert_cols_list.append("currency_symbol")
                    insert_vals.append('$')
                if has_date_format_col:
                    insert_cols_list.append("date_format")
                    insert_vals.append('MDY') # Default date format
                
                insert_cols = ", ".join(insert_cols_list)
                insert_vals_placeholders = ", ".join(["%s"] * len(insert_cols_list))
                return_fields = insert_cols # Return the same columns we inserted

                cursor.execute(
                    f"""
                    INSERT INTO user_preferences ({insert_cols})
                    VALUES ({insert_vals_placeholders})
                    RETURNING {return_fields}
                    """,
                    tuple(insert_vals)
                )
                preferences_data = cursor.fetchone()
                conn.commit()
            
            # Map returned data to dictionary using the dynamically determined fields
            returned_columns = [col.strip() for col in select_fields.split(',')]
            if preferences_data:
                pref_map = {col: i for i, col in enumerate(returned_columns)}
                preferences = {
                    'email_notifications': preferences_data[pref_map.get('email_notifications', 0)],
                    'default_view': preferences_data[pref_map.get('default_view', 1)],
                    'theme': preferences_data[pref_map.get('theme', 2)],
                    'expiring_soon_days': preferences_data[pref_map.get('expiring_soon_days', 3)],
                    'notification_frequency': preferences_data[pref_map.get('notification_frequency', 4)],
                    'notification_time': preferences_data[pref_map.get('notification_time', 5)],
                    'timezone': preferences_data[pref_map.get('timezone', 6)],
                    'notification_channel': preferences_data[pref_map['notification_channel']] if 'notification_channel' in pref_map else 'email',
                    'apprise_notification_time': preferences_data[pref_map['apprise_notification_time']] if 'apprise_notification_time' in pref_map else '09:00',
                    'apprise_timezone': preferences_data[pref_map['apprise_timezone']] if 'apprise_timezone' in pref_map else 'UTC',
                    'apprise_notification_frequency': preferences_data[pref_map['apprise_notification_frequency']] if 'apprise_notification_frequency' in pref_map else 'daily',
                    'currency_symbol': preferences_data[pref_map['currency_symbol']] if 'currency_symbol' in pref_map else '$', # Handle currency optionality
                    'date_format': preferences_data[pref_map['date_format']] if 'date_format' in pref_map else 'MDY' # Handle date_format optionality
                }
            else:
                 # Fallback if even insert failed or returned nothing
                 preferences = {
                    'email_notifications': True,
                    'default_view': 'grid',
                    'theme': 'light',
                    'expiring_soon_days': 30,
                    'notification_frequency': 'daily',
                    'notification_time': '09:00',
                    'timezone': 'UTC',
                    'notification_channel': 'email',
                    'apprise_notification_time': '09:00',
                    'apprise_notification_frequency': 'daily',
                    'currency_symbol': '$',
                    'date_format': 'MDY'
                 }

            return jsonify(preferences), 200
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error in get_preferences: {str(e)}")
            default_preferences = {
                'email_notifications': True,
                'default_view': 'grid',
                'theme': 'light',
                'expiring_soon_days': 30,
                'notification_frequency': 'daily',
                'notification_time': '09:00',
                'timezone': 'UTC',
                'notification_channel': 'email',
                'apprise_notification_time': '09:00',
                'apprise_notification_frequency': 'daily',
                'currency_symbol': '$',
                'date_format': 'MDY'
            }
            return jsonify(default_preferences), 200
        finally:
            cursor.close()
            release_db_connection(conn)
    except Exception as e:
        logger.error(f"Error in get_preferences: {str(e)}")
        default_preferences = {
            'email_notifications': True,
            'default_view': 'grid',
            'theme': 'light',
            'expiring_soon_days': 30,
            'notification_frequency': 'daily',
            'notification_time': '09:00',
            'timezone': 'UTC',
            'notification_channel': 'email',
            'apprise_notification_time': '09:00',
            'apprise_notification_frequency': 'daily',
            'currency_symbol': '$',
            'date_format': 'MDY'
        }
        return jsonify(default_preferences), 200

@app.route('/api/auth/preferences', methods=['PUT'])
@token_required
def update_preferences():
    user_id = request.user['id']
    try:
        data = request.get_json()
        if not data:
            return jsonify({'message': 'No input data provided'}), 400
        
        # Debug logging for theme issue
        logger.info(f"Update preferences input data: {data}")
        
        notification_channel = data.get('notification_channel')
        default_view = data.get('default_view')
        theme = data.get('theme')
        expiring_soon_days = data.get('expiring_soon_days')
        notification_frequency = data.get('notification_frequency')
        notification_time = data.get('notification_time')
        apprise_notification_time = data.get('apprise_notification_time')
        apprise_notification_frequency = data.get('apprise_notification_frequency')
        timezone = data.get('timezone')
        apprise_timezone = data.get('apprise_timezone')
        currency_symbol = data.get('currency_symbol')
        date_format = data.get('date_format')
        
        logger.info(f"Update preferences parsed theme: {theme}")

        if notification_channel and notification_channel not in ['none', 'email', 'apprise', 'both']:
            return jsonify({'message': 'Invalid notification channel'}), 400
        if default_view and default_view not in ['grid', 'list', 'table']:
            return jsonify({'message': 'Invalid default view'}), 400
        if theme and theme not in ['light', 'dark']:
            return jsonify({'message': 'Invalid theme'}), 400
        if expiring_soon_days is not None:
            try:
                expiring_soon_days = int(expiring_soon_days)
                if expiring_soon_days < 1 or expiring_soon_days > 365:
                    return jsonify({'message': 'Expiring soon days must be between 1 and 365'}), 400
            except ValueError:
                return jsonify({'message': 'Expiring soon days must be a valid number'}), 400
        if notification_frequency and notification_frequency not in ['daily', 'weekly', 'monthly']:
            return jsonify({'message': 'Invalid notification frequency'}), 400
        if notification_time and not re.match(r'^([01]?[0-9]|2[0-3]):[0-5][0-9]$', notification_time):
            return jsonify({'message': 'Invalid notification time format'}), 400
        if timezone and not is_valid_timezone(timezone):
            return jsonify({'message': 'Invalid timezone'}), 400
        if apprise_timezone and not is_valid_timezone(apprise_timezone):
            return jsonify({'message': 'Invalid Apprise timezone'}), 400
        
        # Add validation for date_format
        valid_date_formats = ['MDY', 'DMY', 'YMD', 'MDY_WORDS', 'DMY_WORDS', 'YMD_WORDS']
        if date_format and date_format not in valid_date_formats:
            return jsonify({'message': 'Invalid date format'}), 400

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            # Check if columns exist first to handle dynamic schema changes
            cursor.execute("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name='user_preferences' 
                AND column_name IN ('date_format', 'notification_channel', 'apprise_notification_time', 'apprise_notification_frequency', 'apprise_timezone')
            """)
            existing_cols = [row[0] for row in cursor.fetchall()]
            has_date_format_col = 'date_format' in existing_cols
            has_notification_channel_col = 'notification_channel' in existing_cols
            has_apprise_notification_time_col = 'apprise_notification_time' in existing_cols
            has_apprise_notification_frequency_col = 'apprise_notification_frequency' in existing_cols
            has_currency = has_currency_symbol_column(cursor)
            
            # Debug logging for Apprise settings
            logger.info(f"Update preferences debug - apprise_notification_time: {apprise_notification_time}")
            logger.info(f"Update preferences debug - has_apprise_notification_time_col: {has_apprise_notification_time_col}")
            logger.info(f"Update preferences debug - existing_cols: {existing_cols}")
            
            cursor.execute(
                "SELECT 1 FROM user_preferences WHERE user_id = %s",
                (user_id,)
            )
            preferences_exist = cursor.fetchone() is not None

            if preferences_exist:
                update_fields = []
                update_values = []
                if notification_channel and has_notification_channel_col:
                    update_fields.append("notification_channel = %s")
                    update_values.append(notification_channel)
                if default_view:
                    update_fields.append("default_view = %s")
                    update_values.append(default_view)
                if theme:
                    update_fields.append("theme = %s")
                    update_values.append(theme)
                if expiring_soon_days is not None:
                    update_fields.append("expiring_soon_days = %s")
                    update_values.append(expiring_soon_days)
                if notification_frequency:
                    update_fields.append("notification_frequency = %s")
                    update_values.append(notification_frequency)
                if notification_time:
                    update_fields.append("notification_time = %s")
                    update_values.append(notification_time)
                if apprise_notification_time is not None and has_apprise_notification_time_col:
                    update_fields.append("apprise_notification_time = %s")
                    update_values.append(apprise_notification_time)
                if apprise_notification_frequency is not None and has_apprise_notification_frequency_col:
                    update_fields.append("apprise_notification_frequency = %s")
                    update_values.append(apprise_notification_frequency)
                if timezone:
                    update_fields.append("timezone = %s")
                    update_values.append(timezone)
                if apprise_timezone and 'apprise_timezone' in existing_cols:
                    update_fields.append("apprise_timezone = %s")
                    update_values.append(apprise_timezone)
                if has_currency and currency_symbol is not None:
                    update_fields.append("currency_symbol = %s")
                    update_values.append(currency_symbol)
                # Add date_format to update only if the column exists
                if has_date_format_col and date_format:
                    update_fields.append("date_format = %s")
                    update_values.append(date_format)
                
                if update_fields:
                    # Build the returning fields string dynamically based on existing columns
                    # IMPORTANT: Always SELECT all fields, don't rely on UPDATE RETURNING subset
                    return_fields_list = ["email_notifications", "default_view", "theme", "expiring_soon_days", "notification_frequency", "notification_time", "timezone"]
                    if has_notification_channel_col:
                        return_fields_list.append("notification_channel")
                    if has_apprise_notification_time_col:
                        return_fields_list.append("apprise_notification_time")
                    if has_apprise_notification_frequency_col:
                        return_fields_list.append("apprise_notification_frequency")
                    if 'apprise_timezone' in existing_cols:
                        return_fields_list.append("apprise_timezone")
                    if has_currency:
                        return_fields_list.append("currency_symbol")
                    if has_date_format_col:
                        return_fields_list.append("date_format")
                    return_fields = ", ".join(return_fields_list)

                    # First do the UPDATE
                    update_query = f"""
                        UPDATE user_preferences 
                        SET {', '.join(update_fields)}
                        WHERE user_id = %s
                    """
                    cursor.execute(update_query, update_values + [user_id])
                    
                    # Then SELECT all fields to get complete data
                    cursor.execute(
                        f"""
                        SELECT {return_fields}
                        FROM user_preferences
                        WHERE user_id = %s
                        """,
                        (user_id,)
                    )
                    preferences_data = cursor.fetchone()
                else:
                    # If no fields to update, select existing data
                    select_fields_list = ["email_notifications", "default_view", "theme", "expiring_soon_days", "notification_frequency", "notification_time", "timezone"]
                    if has_notification_channel_col:
                        select_fields_list.append("notification_channel")
                    if has_apprise_notification_time_col:
                        select_fields_list.append("apprise_notification_time")
                    if has_apprise_notification_frequency_col:
                        select_fields_list.append("apprise_notification_frequency")
                    if 'apprise_timezone' in existing_cols:
                        select_fields_list.append("apprise_timezone")
                    if has_currency:
                        select_fields_list.append("currency_symbol")
                    if has_date_format_col:
                        select_fields_list.append("date_format")
                    select_fields = ", ".join(select_fields_list)
                    
                    cursor.execute(
                        f"""
                        SELECT {select_fields}
                        FROM user_preferences
                        WHERE user_id = %s
                        """,
                        (user_id,)
                    )
                    preferences_data = cursor.fetchone()
            else: # Insert new record
                # Build insert dynamically
                insert_cols_list = ["user_id", "default_view", "theme", "expiring_soon_days", "notification_frequency", "notification_time", "timezone"]
                insert_vals = [
                    user_id,
                    default_view or 'grid',
                    theme or 'light',
                    expiring_soon_days if expiring_soon_days is not None else 30,
                    notification_frequency or 'daily',
                    notification_time or '09:00',
                    timezone or 'UTC'
                ]
                if has_notification_channel_col:
                    insert_cols_list.append("notification_channel")
                    insert_vals.append(notification_channel or 'email')
                if has_apprise_notification_time_col:
                    insert_cols_list.append("apprise_notification_time")
                    insert_vals.append(apprise_notification_time or '09:00')
                if has_apprise_notification_frequency_col:
                    insert_cols_list.append("apprise_notification_frequency")
                    insert_vals.append(apprise_notification_frequency or 'daily')
                if has_currency:
                    insert_cols_list.append("currency_symbol")
                    insert_vals.append(currency_symbol or '$')
                if has_date_format_col:
                    insert_cols_list.append("date_format")
                    insert_vals.append(date_format or 'MDY')

                insert_cols = ", ".join(insert_cols_list)
                insert_vals_placeholders = ", ".join(["%s"] * len(insert_cols_list))
                return_fields = insert_cols # Return the same columns we inserted
                
                cursor.execute(
                    f"""
                    INSERT INTO user_preferences ({insert_cols})
                    VALUES ({insert_vals_placeholders})
                    RETURNING {return_fields}
                    """,
                    tuple(insert_vals)
                )
                preferences_data = cursor.fetchone()
            
            # Map returned data to dictionary using the dynamically determined fields
            returned_columns = [col.strip() for col in return_fields.split(',')]
            if preferences_data:
                pref_map = {col: i for i, col in enumerate(returned_columns)}
                
                # Log debug info for theme issues
                logger.info(f"Update preferences debug - returned_columns: {returned_columns}")
                logger.info(f"Update preferences debug - pref_map: {pref_map}")
                logger.info(f"Update preferences debug - preferences_data: {preferences_data}")
                logger.info(f"Update preferences debug - theme column index: {pref_map.get('theme', 'NOT_FOUND')}")
                
                preferences = {
                    'email_notifications': preferences_data[pref_map['email_notifications']] if 'email_notifications' in pref_map else True,
                    'default_view': preferences_data[pref_map['default_view']] if 'default_view' in pref_map else 'grid',
                    'theme': preferences_data[pref_map['theme']] if 'theme' in pref_map else 'light',
                    'expiring_soon_days': preferences_data[pref_map['expiring_soon_days']] if 'expiring_soon_days' in pref_map else 30,
                    'notification_frequency': preferences_data[pref_map['notification_frequency']] if 'notification_frequency' in pref_map else 'daily',
                    'notification_time': preferences_data[pref_map['notification_time']] if 'notification_time' in pref_map else '09:00',
                    'timezone': preferences_data[pref_map['timezone']] if 'timezone' in pref_map else 'UTC',
                    'notification_channel': preferences_data[pref_map['notification_channel']] if 'notification_channel' in pref_map else 'email',
                    'apprise_notification_time': preferences_data[pref_map['apprise_notification_time']] if 'apprise_notification_time' in pref_map else '09:00',
                    'apprise_notification_frequency': preferences_data[pref_map['apprise_notification_frequency']] if 'apprise_notification_frequency' in pref_map else 'daily',
                    'apprise_timezone': preferences_data[pref_map['apprise_timezone']] if 'apprise_timezone' in pref_map else 'UTC',
                    'currency_symbol': preferences_data[pref_map['currency_symbol']] if 'currency_symbol' in pref_map else '$',
                    'date_format': preferences_data[pref_map['date_format']] if 'date_format' in pref_map else 'MDY'
                }
                
                logger.info(f"Update preferences debug - final theme value: {preferences.get('theme')}")
            else:
                # Fallback if no data returned
                preferences = {}


            conn.commit()
            return jsonify(preferences), 200
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error in update_preferences: {str(e)}")
            fallback_preferences = {
                'email_notifications': True,  # Fixed: Set default value instead of undefined variable
                'default_view': default_view or 'grid',
                'theme': theme or 'light',
                'expiring_soon_days': expiring_soon_days if expiring_soon_days is not None else 30,
                'notification_frequency': notification_frequency or 'daily',
                'notification_time': notification_time or '09:00',
                'timezone': timezone or 'UTC',
                'currency_symbol': currency_symbol or '$',
                'date_format': date_format or 'MDY' # Add to fallback
            }
            return jsonify(fallback_preferences), 200
        finally:
            cursor.close()
            release_db_connection(conn)
    except Exception as e:
        logger.error(f"Error in update_preferences: {str(e)}")
        default_preferences = {
            'email_notifications': True,
            'default_view': 'grid',
            'theme': 'light',
            'expiring_soon_days': 30,
            'notification_frequency': 'daily',
            'notification_time': '09:00',
            'timezone': 'UTC',
            'currency_symbol': '$',
            'date_format': 'MDY'  # Fixed: Added missing date_format to defaults
        }
        return jsonify(default_preferences), 200

# Admin User Management Endpoints

@app.route('/api/admin/users', methods=['GET'])
@admin_required
def get_all_users():
    """Get all users (admin only)"""
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute('''
                SELECT id, username, email, first_name, last_name, is_active, is_admin, created_at, last_login 
                FROM users 
                ORDER BY created_at DESC
            ''')
            users = cur.fetchall()
            columns = [desc[0] for desc in cur.description]
            users_list = []
            
            for row in users:
                user_dict = dict(zip(columns, row))
                # Convert date objects to ISO format strings for JSON serialization
                for key, value in user_dict.items():
                    if isinstance(value, (datetime, date)):
                        user_dict[key] = value.isoformat() if value else None
                
                users_list.append(user_dict)
                
            return jsonify(users_list), 200
    except Exception as e:
        logger.error(f"Error retrieving users: {e}")
        return jsonify({"message": "Failed to retrieve users"}), 500
    finally:
        if conn:
            release_db_connection(conn)

@app.route('/api/admin/users/<int:user_id>', methods=['PUT'])
@admin_required
def update_user(user_id):
    """Update user details (admin only)"""
    conn = None
    try:
        # Prevent modifying self
        if user_id == request.user['id']:
            return jsonify({"message": "Cannot modify your own admin status"}), 403
        
        data = request.get_json()
        
        # Use regular connection since db_user now has superuser privileges
        conn = get_db_connection()
        with conn.cursor() as cur:
            # Check if user exists
            cur.execute('SELECT id FROM users WHERE id = %s', (user_id,))
            user = cur.fetchone()
            
            if not user:
                return jsonify({"message": "User not found"}), 404
            
            # Update fields
            updates = []
            params = []
            
            if 'is_admin' in data:
                updates.append('is_admin = %s')
                params.append(bool(data['is_admin']))
            
            if 'is_active' in data:
                updates.append('is_active = %s')
                params.append(bool(data['is_active']))
            
            if not updates:
                return jsonify({"message": "No fields to update"}), 400
            
            # Build and execute update query
            query = f"UPDATE users SET {', '.join(updates)} WHERE id = %s"
            params.append(user_id)
            
            cur.execute(query, params)
            conn.commit()
            
            return jsonify({"message": "User updated successfully"}), 200
    except Exception as e:
        logger.error(f"Error updating user: {e}")
        if conn:
            conn.rollback()
        return jsonify({"message": f"Failed to update user: {str(e)}"}), 500
    finally:
        if conn:
            release_db_connection(conn)

@app.route('/api/admin/users/<int:user_id>', methods=['DELETE'])
@admin_required
def delete_user(user_id):
    """Delete a user (admin only)"""
    conn = None
    try:
        logger.info(f"Delete user request received for user_id: {user_id}")
        
        # Prevent deleting self
        if user_id == request.user['id']:
            logger.warning(f"User {request.user['username']} attempted to delete their own account")
            return jsonify({"message": "Cannot delete your own account through admin API"}), 403
        
        # Use regular connection since db_user now has superuser privileges
        conn = get_db_connection()
        with conn.cursor() as cur:
            # Check if user exists
            cur.execute('SELECT id, username FROM users WHERE id = %s', (user_id,))
            user = cur.fetchone()
            
            if not user:
                logger.warning(f"User with ID {user_id} not found")
                return jsonify({"message": "User not found"}), 404
            
            logger.info(f"Deleting user {user[1]} (ID: {user[0]})")
            
            # Delete user's warranties first
            cur.execute('DELETE FROM warranties WHERE user_id = %s', (user_id,))
            warranties_deleted = cur.rowcount
            logger.info(f"Deleted {warranties_deleted} warranties belonging to user {user_id}")
            
            # Delete user's password reset tokens if any
            cur.execute('DELETE FROM password_reset_tokens WHERE user_id = %s', (user_id,))
            tokens_deleted = cur.rowcount
            logger.info(f"Deleted {tokens_deleted} password reset tokens belonging to user {user_id}")
            
            # Delete user's sessions if any
            cur.execute('DELETE FROM user_sessions WHERE user_id = %s', (user_id,))
            sessions_deleted = cur.rowcount
            logger.info(f"Deleted {sessions_deleted} sessions belonging to user {user_id}")

            # Delete user's tags
            cur.execute('DELETE FROM tags WHERE user_id = %s', (user_id,))
            tags_deleted = cur.rowcount
            logger.info(f"Deleted {tags_deleted} tags belonging to user {user_id}")

            # Delete user
            cur.execute('DELETE FROM users WHERE id = %s', (user_id,))
            user_deleted = cur.rowcount
            logger.info(f"Deleted user {user_id}, affected rows: {user_deleted}")
            
            conn.commit()
            logger.info(f"User {user_id} deleted successfully")
            
            return jsonify({"message": "User deleted successfully"}), 200
    except Exception as e:
        logger.error(f"Error deleting user: {e}")
        if conn:
            conn.rollback()
        return jsonify({"message": f"Failed to delete user: {str(e)}"}), 500
    finally:
        if conn:
            release_db_connection(conn)

# Site settings
@app.route('/api/admin/settings', methods=['GET'])
@admin_required
def get_site_settings():
    """Get site settings (admin only)"""
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # Check if settings table exists
            cur.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'site_settings'
                )
            """)
            table_exists = cur.fetchone()[0]
            
            # Create settings table if it doesn't exist
            if not table_exists:
                cur.execute("""
                    CREATE TABLE site_settings (
                        key VARCHAR(255) PRIMARY KEY,
                        value TEXT,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                conn.commit()
            
            # Get all settings
            cur.execute('SELECT key, value FROM site_settings')
            raw_settings = {row[0]: row[1] for row in cur.fetchall()}
            
            # Define default values for all settings managed here
            # OIDC Client Secret is write-only from admin UI, not directly exposed via GET
            default_site_settings = {
                'registration_enabled': 'true',
                'email_base_url': os.environ.get('APP_BASE_URL', 'http://localhost:8080'), # Default to APP_BASE_URL
                'global_view_enabled': 'true',  # Global warranty view feature
                'global_view_admin_only': 'false',  # Restrict global view to admins only
                'oidc_enabled': 'false',
                'oidc_provider_name': 'oidc',
                'oidc_client_id': '',
                # 'oidc_client_secret': '', # Not returned
                'oidc_issuer_url': '',
                'oidc_scope': 'openid email profile',
                # Apprise default settings
                'apprise_enabled': 'false',
                'apprise_urls': '',
                'apprise_expiration_days': '7,30',
                'apprise_notification_time': '09:00',
                'apprise_title_prefix': '[Warracker]'
            }

            settings_to_return = {}
            needs_commit = False

            # First, add all existing settings from the database
            for key, value in raw_settings.items():
                # Skip returning the client secret directly
                if key == 'oidc_client_secret':
                    continue
                
                # For boolean-like string settings, ensure they are 'true' or 'false'
                if key in ['registration_enabled', 'oidc_enabled', 'apprise_enabled', 'global_view_enabled', 'global_view_admin_only']:
                    settings_to_return[key] = 'true' if value.lower() == 'true' else 'false'
                else:
                    settings_to_return[key] = value

            # Then, add defaults for any missing settings
            for key, default_value in default_site_settings.items():
                if key not in settings_to_return and key != 'oidc_client_secret':
                    settings_to_return[key] = default_value
                    # Insert default if missing (except for secret)
                    cur.execute(
                        'INSERT INTO site_settings (key, value) VALUES (%s, %s) ON CONFLICT (key) DO NOTHING',
                        (key, default_value)
                    )
                    needs_commit = True
            
            # Indicate if OIDC client secret is set without revealing it
            settings_to_return['oidc_client_secret_set'] = bool(raw_settings.get('oidc_client_secret'))

            if needs_commit:
                conn.commit()
            
            return jsonify(settings_to_return), 200
    except Exception as e:
        logger.error(f"Error retrieving site settings: {e}")
        return jsonify({"message": "Failed to retrieve site settings"}), 500
    finally:
        if conn:
            release_db_connection(conn)

@app.route('/api/admin/settings', methods=['PUT'])
@admin_required
def update_site_settings():
    """Update site settings (admin only)"""
    conn = None
    try:
        data = request.get_json()
        
        conn = get_db_connection()
        with conn.cursor() as cur:
            # Check if settings table exists
            cur.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'site_settings'
                )
            """)
            table_exists = cur.fetchone()[0]
            
            # Create settings table if it doesn't exist
            if not table_exists:
                cur.execute("""
                    CREATE TABLE site_settings (
                        key VARCHAR(255) PRIMARY KEY,
                        value TEXT,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
            
            # Update settings
            updated_keys = []
            requires_restart = False
            for key, value in data.items():
                # Sanitize boolean-like string values
                if key in ['registration_enabled', 'oidc_enabled', 'global_view_enabled', 'global_view_admin_only']:
                    value = 'true' if str(value).lower() == 'true' else 'false'
                
                # Check if it's an OIDC related key that requires restart
                if key.startswith('oidc_'):
                    requires_restart = True
                
                # For oidc_client_secret, only update if a non-empty value is provided
                # An empty string could mean "clear" or "no change" - admin UI should clarify
                # For now, if key is 'oidc_client_secret' and value is empty, we skip update to avoid accidental clearing.
                # The admin UI should send a specific placeholder if they intend to clear it, or not send the key.
                if key == 'oidc_client_secret' and not value: # If an empty secret is passed, don't update
                    logger.info(f"Skipping update for oidc_client_secret as value is empty.")
                    continue


                cur.execute("""
                    INSERT INTO site_settings (key, value, updated_at) 
                    VALUES (%s, %s, CURRENT_TIMESTAMP)
                    ON CONFLICT (key) 
                    DO UPDATE SET value = EXCLUDED.value, updated_at = CURRENT_TIMESTAMP
                """, (key, str(value))) # Ensure value is string
                updated_keys.append(key)
            
            conn.commit()
            
            response_message = "Settings updated successfully."
            oidc_settings_changed = any(k.startswith('oidc_') for k in updated_keys)

            if oidc_settings_changed:
                logger.info("OIDC related settings changed, re-initializing OIDC client...")
                try:
                    with app.app_context(): # Ensure app context for init_oidc_client
                        init_oidc_client(app, get_db_connection, release_db_connection)
                    logger.info("OIDC client re-initialized successfully after settings update.")
                    response_message = "Settings updated successfully. OIDC configuration has been re-applied."
                except Exception as oidc_reinit_err:
                    logger.error(f"Error re-initializing OIDC client after settings update: {oidc_reinit_err}")
                    response_message = "Settings updated, but OIDC re-configuration failed. A manual restart might be needed for OIDC changes to take effect."
            elif requires_restart: # This case might be redundant if all oidc_ keys trigger the above
                response_message += " An application restart is required for some settings to take full effect."
            
            return jsonify({"message": response_message}), 200
    except Exception as e:
        logger.error(f"Error updating site settings: {e}")
        if conn:
            conn.rollback()
        return jsonify({"message": "Failed to update site settings"}), 500
    finally:
        if conn:
            release_db_connection(conn)

# Modify the register endpoint to check if registration is enabled
@app.route('/api/settings/global-view-status', methods=['GET'])
@token_required
def check_global_view_status():
    """Check if global view is enabled for the current user"""
    conn = None
    try:
        user_is_admin = request.user.get('is_admin', False)
        
        conn = get_db_connection()
        with conn.cursor() as cur:
            # Check if settings table exists
            cur.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'site_settings'
                )
            """)
            table_exists = cur.fetchone()[0]
            
            if not table_exists:
                # If table doesn't exist, global view is enabled by default
                return jsonify({"enabled": True}), 200
            
            # Get both global view settings
            cur.execute("SELECT key, value FROM site_settings WHERE key IN ('global_view_enabled', 'global_view_admin_only')")
            settings = {row[0]: row[1] for row in cur.fetchall()}
            
            # Check if global view is enabled at all
            global_view_enabled = settings.get('global_view_enabled', 'true').lower() == 'true'
            if not global_view_enabled:
                return jsonify({"enabled": False}), 200
            
            # Check if global view is restricted to admins only
            admin_only = settings.get('global_view_admin_only', 'false').lower() == 'true'
            if admin_only and not user_is_admin:
                return jsonify({"enabled": False}), 200
            
            # Global view is enabled for this user
            return jsonify({"enabled": True}), 200
            
    except Exception as e:
        logger.error(f"Error checking global view status: {e}")
        # Default to enabled on error for admins, disabled for non-admins
        user_is_admin = request.user.get('is_admin', False)
        return jsonify({"enabled": user_is_admin}), 500
    finally:
        if conn:
            release_db_connection(conn)

@app.route('/api/auth/registration-status', methods=['GET'])
def check_registration_status():
    """Check if registration is enabled"""
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # Check if settings table exists
            cur.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'site_settings'
                )
            """)
            table_exists = cur.fetchone()[0]
            
            if not table_exists:
                # If table doesn't exist, registration is enabled by default
                return jsonify({"enabled": True}), 200
            
            # Get registration_enabled setting
            cur.execute("SELECT value FROM site_settings WHERE key = 'registration_enabled'")
            result = cur.fetchone()
            
            if not result:
                # If setting doesn't exist, registration is enabled by default
                return jsonify({"enabled": True}), 200
            
            registration_enabled = result[0].lower() == 'true'
            
            return jsonify({"enabled": registration_enabled}), 200
    except Exception as e:
        logger.error(f"Error checking registration status: {e}")
        return jsonify({"enabled": True}), 200  # Default to enabled on error
    finally:
        if conn:
            release_db_connection(conn)

# File serving endpoints
@app.route('/api/files/<path:filename>', methods=['GET', 'POST'])
@token_required
def serve_file(filename):
    """Basic secure file serving with authentication."""
    try:
        logger.info(f"File access request for {filename} by user {request.user['id']}")
        
        if not filename.startswith('uploads/'):
            logger.warning(f"Attempted access to non-uploads file: {filename}")
            return jsonify({"message": "Access denied"}), 403
            
        # Remove 'uploads/' prefix for send_from_directory
        file_path = filename[8:] if filename.startswith('uploads/') else filename
        
        return send_from_directory('/data/uploads', file_path)
    except Exception as e:
        logger.error(f"Error serving file {filename}: {e}")
        return jsonify({"message": "Error accessing file"}), 500

@app.route('/api/secure-file/<path:filename>', methods=['GET', 'POST'])
@token_required
def secure_file_access(filename):
    """Enhanced secure file serving with authorization checks and improved reliability."""
    try:
        # ADD EXTRA LOGGING HERE
        logger.info(f"[SECURE_FILE] Raw filename from route: '{filename}' (len: {len(filename)})")
        logger.info(f"[SECURE_FILE] repr(filename): {repr(filename)}")

        # Security check for path traversal
        if '..' in filename or filename.startswith('/'):
            logger.warning(f"[SECURE_FILE] Potential path traversal attempt detected: {filename} by user {request.user['id']}")
            return jsonify({"message": "Invalid file path"}), 400

        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                db_search_path = f"uploads/{filename}"
                logger.info(f"[SECURE_FILE] Searching DB for paths like: '{db_search_path}' (repr: {repr(db_search_path)})")
                query = """
                    SELECT w.id, w.user_id
                    FROM warranties w
                    WHERE w.invoice_path = %s OR w.manual_path = %s OR w.other_document_path = %s OR w.product_photo_path = %s
                """
                cur.execute(query, (db_search_path, db_search_path, db_search_path, db_search_path))
                results = cur.fetchall()
                logger.info(f"[SECURE_FILE] DB query results for '{db_search_path}': {results}")

                user_id = request.user['id']
                is_admin = request.user.get('is_admin', False)
                authorized = is_admin
                logger.info(f"[SECURE_FILE] Initial authorization (is_admin={is_admin}): {authorized}")

                if not authorized and results:
                    for warranty_id_db, warranty_user_id_db in results:
                        logger.info(f"[SECURE_FILE] Checking ownership: warranty_id={warranty_id_db}, owner_id={warranty_user_id_db}, current_user_id={user_id}")
                        if warranty_user_id_db == user_id:
                            authorized = True
                            logger.info(f"[SECURE_FILE] Ownership confirmed for warranty_id={warranty_id_db}")
                            break
                
                if not authorized:
                    logger.warning(f"[SECURE_FILE] Unauthorized file access attempt: '{filename}' (repr: {repr(filename)}) by user {user_id}. DB results count: {len(results) if results else 'None'}")
                    return jsonify({"message": "You are not authorized to access this file"}), 403
                
                logger.info(f"[SECURE_FILE] User {user_id} authorized for file '{filename}'. Attempting to serve from /data/uploads.")
                
                # Construct the full file path
                target_file_path_for_send = os.path.join('/data/uploads', filename)
                logger.info(f"[SECURE_FILE] Path for verification: '{target_file_path_for_send}' (repr: {repr(target_file_path_for_send)})")
                
                # Enhanced file existence and readability checks
                if not os.path.exists(target_file_path_for_send):
                    logger.error(f"[SECURE_FILE] File '{target_file_path_for_send}' does not exist")
                    try:
                        dir_contents = os.listdir('/data/uploads')
                        logger.info(f"[SECURE_FILE] Contents of /data/uploads: {dir_contents}")
                    except Exception as list_err:
                        logger.error(f"[SECURE_FILE] Error listing /data/uploads: {list_err}")
                    return jsonify({"message": "File not found"}), 404
                
                if not os.path.isfile(target_file_path_for_send):
                    logger.error(f"[SECURE_FILE] Path '{target_file_path_for_send}' exists but is not a file")
                    return jsonify({"message": "Invalid file"}), 400
                
                # Check file size and readability
                try:
                    file_size = os.path.getsize(target_file_path_for_send)
                    logger.info(f"[SECURE_FILE] File size: {file_size} bytes")
                    
                    # Verify we can read the file
                    with open(target_file_path_for_send, 'rb') as f:
                        # Try to read first byte to ensure file is readable
                        f.read(1)
                        f.seek(0)  # Reset file pointer
                        
                except (OSError, IOError) as e:
                    logger.error(f"[SECURE_FILE] Cannot read file '{target_file_path_for_send}': {e}")
                    return jsonify({"message": "File read error"}), 500
                
                # Use Flask's send_from_directory with enhanced error handling
                try:
                    # Get MIME type
                    mimetype, _ = mimetypes.guess_type(target_file_path_for_send)
                    if not mimetype:
                        mimetype = 'application/octet-stream'
                    
                    logger.info(f"[SECURE_FILE] Serving file with size {file_size} bytes, mimetype: {mimetype}")
                    
                    # Use streaming for ALL files to prevent Content-Length mismatches
                    logger.info(f"[SECURE_FILE] Using streaming response for file: {filename}")
                    
                    def generate():
                        try:
                            with open(target_file_path_for_send, 'rb') as f:
                                chunk_size = 4096  # 4KB chunks
                                total_sent = 0
                                while True:
                                    chunk = f.read(chunk_size)
                                    if not chunk:
                                        break
                                    total_sent += len(chunk)
                                    logger.debug(f"[SECURE_FILE] Streaming chunk: {len(chunk)} bytes, total sent: {total_sent}/{file_size}")
                                    yield chunk
                                logger.info(f"[SECURE_FILE] Streaming completed: {total_sent}/{file_size} bytes sent")
                        except Exception as e:
                            logger.error(f"[SECURE_FILE] Error during streaming: {e}")
                            raise
                    
                    response = Response(
                        generate(),
                        mimetype=mimetype,
                        headers={
                            'Content-Length': str(file_size),
                            'Content-Disposition': f'inline; filename="{os.path.basename(filename)}"',
                            'Accept-Ranges': 'bytes',
                            'Cache-Control': 'no-cache, no-store, must-revalidate',
                            'Pragma': 'no-cache',
                            'Expires': '0',
                            'X-Content-Type-Options': 'nosniff',
                            'Connection': 'close'
                        }
                    )
                    return response
                except Exception as send_error:
                    logger.error(f"[SECURE_FILE] Error serving file: {send_error}")
                    return jsonify({"message": "Error serving file"}), 500
                    
        finally:
            release_db_connection(conn)
    except Exception as e:
        logger.error(f"[SECURE_FILE] Error in secure file access for '{filename}' (repr: {repr(filename)}): {e}", exc_info=True)
        return jsonify({"message": "Error accessing file"}), 500





def send_password_reset_email(recipient_email, reset_link):
    """Sends the password reset email."""
    logger.info(f"Attempting to send password reset email to {recipient_email}")
    
    subject = "Warracker: Password Reset Request"
    
    # Basic text body
    text_body = f"""Hello,

You requested a password reset for your Warracker account.

Click the link below to set a new password:
{reset_link}

If you did not request this reset, please ignore this email. This link will expire in 24 hours.

Thanks,
The Warracker Team
"""

    # Basic HTML body
    html_body = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Warracker Password Reset</title>
</head>
<body style="font-family: sans-serif; line-height: 1.6;">
  <h2>Warracker Password Reset Request</h2>
  <p>Hello,</p>
  <p>You requested a password reset for your Warracker account.</p>
  <p>Click the button below to set a new password:</p>
  <p style="margin: 25px 0;">
    <a href="{reset_link}" style="background-color: #007bff; color: white; padding: 12px 20px; text-decoration: none; border-radius: 5px; font-weight: bold;">
      Reset Your Password
    </a>
  </p>
  <p>If the button doesn't work, copy and paste this link into your browser:</p>
  <p><a href="{reset_link}">{reset_link}</a></p>
  <p>If you did not request this reset, please ignore this email. This link will expire in 24 hours.</p>
  <p>Thanks,<br>The Warracker Team</p>
</body>
</html>
"""

    # Get SMTP settings from environment variables
    smtp_host = os.environ.get('SMTP_HOST', 'localhost')
    smtp_port = int(os.environ.get('SMTP_PORT', '1025'))
    smtp_username = os.environ.get('SMTP_USERNAME') # No default sender here, should be configured
    smtp_password = os.environ.get('SMTP_PASSWORD')
    # Use SMTP_USERNAME as sender if available, otherwise a default
    sender_email = smtp_username or 'noreply@warracker.local' 

    # Explicit SMTP_USE_TLS from environment, defaulting to true if port is 587
    # and not explicitly set to false.
    smtp_use_tls_env = os.environ.get('SMTP_USE_TLS', 'not_set').lower()

    if not smtp_username:
         logger.warning("SMTP_USERNAME environment variable not set. Using default sender address.")

    # Create a MIMEMultipart object for both text and HTML
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = sender_email
    msg['To'] = recipient_email

    part1 = MIMEText(text_body, 'plain', 'utf-8')
    part2 = MIMEText(html_body, 'html', 'utf-8')

    msg.attach(part1)
    msg.attach(part2)

    # Connect to SMTP server and send
    server = None
    try:
        logger.info(f"Attempting SMTP connection to {smtp_host}:{smtp_port}")
        if smtp_port == 465:
            logger.info("Using SMTP_SSL for port 465.")
            server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=10)
        else:
            logger.info(f"Using SMTP for port {smtp_port}.")
            server = smtplib.SMTP(smtp_host, smtp_port, timeout=10)
            # For port 587, STARTTLS is standard.
            # For other ports, allow SMTP_USE_TLS to explicitly enable/disable it.
            # If SMTP_USE_TLS is 'not_set', default to True for port 587.
            should_use_starttls = False
            if smtp_port == 587:
                should_use_starttls = (smtp_use_tls_env != 'false') # True unless explicitly 'false'
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
        
        # Send email
        logger.info(f"Sending email via {smtp_host}:{smtp_port} from {sender_email} to {recipient_email}")
        server.sendmail(sender_email, recipient_email, msg.as_string())
        logger.info(f"Password reset email successfully sent to {recipient_email}")
        
    except smtplib.SMTPAuthenticationError as e:
        logger.error(f"SMTP Authentication Error sending email to {recipient_email}: {e}")
        # Re-raise a more generic exception or handle appropriately
        raise Exception(f"SMTP Authentication failed for {smtp_username}") from e
    except smtplib.SMTPException as e: # Catch more generic SMTP exceptions
        logger.error(f"SMTP Error sending email to {recipient_email}: {e}")
        logger.error(f"SMTP details used - Host: {smtp_host}, Port: {smtp_port}, Username: {smtp_username}, Sender: {sender_email}")
        raise Exception(f"SMTP error occurred: {str(e)}") from e
    except Exception as e:
        logger.error(f"General error sending email to {recipient_email}: {e}")
        logger.error(f"SMTP details used - Host: {smtp_host}, Port: {smtp_port}, Username: {smtp_username}, Sender: {sender_email}")
        # Raise an exception to be caught by the calling function
        raise Exception("Failed to send password reset email") from e
    finally:
        if server:
            try:
                server.quit()
                logger.info("SMTP connection closed.")
            except Exception as e:
                 logger.error(f"Error quitting SMTP connection: {e}")



# Initialize notification system
# Set up the Apprise handler if available
if APPRISE_AVAILABLE and apprise_handler is not None:
    notifications.set_apprise_handler(apprise_handler)

# Initialize notification scheduler
notifications.init_scheduler(get_db_connection, release_db_connection)

# Hook to ensure scheduler is initialized on request if needed
@app.before_request
def ensure_scheduler_initialized():
    """Ensure scheduler is initialized on the first request if it wasn't at startup"""
    notifications.ensure_scheduler_initialized(get_db_connection, release_db_connection)

# Initialize the database when the application starts
if __name__ == '__main__':
    # Call init_db to ensure tables are created before app starts in standalone mode.
    # In production with Gunicorn/multiple workers, this should ideally be handled by a startup script/migration tool.
    # For simplicity in development or single-worker setups, it's here.
    logger.info("Running in __main__, attempting to initialize database...")
    try:
        init_db()
        logger.info("Database initialized during application startup")
    except Exception as e:
        logger.error(f"Database initialization error during startup: {e}")

@app.route('/api/admin/send-notifications', methods=['POST'])
@admin_required
def trigger_notifications():
    """
    Admin-only endpoint to manually trigger warranty expiration notifications.
    Useful for testing and for sending notifications outside the scheduled time.
    """
    try:
        logger.info(f"Manual notification trigger requested by admin user {request.user['id']}")
        result, status_code = notifications.trigger_notifications_manually(get_db_connection, release_db_connection)
        return jsonify(result), status_code
    except Exception as e:
        error_msg = f"Error triggering notifications: {str(e)}"
        logger.error(error_msg)
        return jsonify({'message': 'Failed to trigger notifications', 'error': error_msg}), 500

@app.route('/api/admin/scheduler-status', methods=['GET'])
@admin_required
def get_scheduler_status():
    """
    Admin-only endpoint to check scheduler status and configuration.
    """
    try:
        status = notifications.get_scheduler_status()
        return jsonify(status), 200
    except Exception as e:
        logger.error(f"Error getting scheduler status: {e}")
        return jsonify({'error': f'Failed to get scheduler status: {str(e)}'}), 500

@app.route('/api/timezones', methods=['GET'])
def get_timezones():
    """Get list of all available timezones"""
    try:
        # Get all timezones from pytz
        all_timezones = pytz.all_timezones
        
        # Group timezones by region
        timezone_groups = {}
        for tz in all_timezones:
            # Split timezone into parts (e.g., 'America/New_York' -> ['America', 'New_York'])
            parts = tz.split('/')
            
            if len(parts) > 1:
                region = parts[0]
                city = '/'.join(parts[1:]).replace('_', ' ')
                
                if region not in timezone_groups:
                    timezone_groups[region] = []
                    
                timezone_groups[region].append({
                    'value': tz,
                    'label': f"{city} ({tz})"
                })
            else:
                # Handle special cases like 'UTC'
                if 'Other' not in timezone_groups:
                    timezone_groups['Other'] = []
                timezone_groups['Other'].append({
                    'value': tz,
                    'label': tz
                })
        
        # Convert to list of groups
        timezone_list = [
            {
                'region': region,
                'timezones': sorted(timezones, key=lambda x: x['label'])
            }
            for region, timezones in sorted(timezone_groups.items())
        ]
        
        return jsonify(timezone_list), 200
    except Exception as e:
        logger.error(f"Error getting timezones: {e}")
        return jsonify({'message': 'Failed to get timezones'}), 500

@app.route('/api/debug/warranty/<int:warranty_id>', methods=['GET'])
@token_required
def debug_warranty(warranty_id):
    conn = None
    try:
        user_id = request.user['id']
        is_admin = request.user['is_admin']
        
        conn = get_db_connection()
        with conn.cursor() as cur:
            # If admin, can see any warranty, otherwise only user's warranties
            if is_admin:
                cur.execute('''
                    SELECT id, product_name, purchase_date, expiration_date, invoice_path, manual_path, other_document_path, product_url, notes,
                           purchase_price, user_id, created_at, updated_at, is_lifetime, vendor, warranty_type,
                           warranty_duration_years, warranty_duration_months, warranty_duration_days, product_photo_path
                    FROM warranties WHERE id = %s
                ''', (warranty_id,))
            else:
                cur.execute('''
                    SELECT id, product_name, purchase_date, expiration_date, invoice_path, manual_path, other_document_path, product_url, notes,
                           purchase_price, user_id, created_at, updated_at, is_lifetime, vendor, warranty_type,
                           warranty_duration_years, warranty_duration_months, warranty_duration_days, product_photo_path
                    FROM warranties WHERE id = %s AND user_id = %s
                ''', (warranty_id, user_id))
                
            warranty = cur.fetchone()
            if not warranty:
                return jsonify({"error": "Warranty not found or you don't have permission to view it"}), 404
                
            columns = [desc[0] for desc in cur.description]
            warranty_dict = dict(zip(columns, warranty))
            
            # Convert date objects to ISO format strings for JSON serialization
            for key, value in warranty_dict.items():
                if isinstance(value, (datetime, date)):
                    warranty_dict[key] = value.isoformat()
                # Convert Decimal objects to float for JSON serialization
                elif isinstance(value, Decimal):
                    warranty_dict[key] = float(value)
            
            # Get serial numbers for this warranty
            cur.execute('SELECT id, serial_number FROM serial_numbers WHERE warranty_id = %s', (warranty_id,))
            serial_numbers = [{
                'id': row[0],
                'serial_number': row[1]
            } for row in cur.fetchall()]
            warranty_dict['serial_numbers'] = serial_numbers

            # Get tags for this warranty (same as /api/warranties)
            cur.execute('''
                SELECT t.id, t.name, t.color
                FROM tags t
                JOIN warranty_tags wt ON t.id = wt.tag_id
                WHERE wt.warranty_id = %s
                ORDER BY t.name
            ''', (warranty_id,))
            tags = [{'id': t[0], 'name': t[1], 'color': t[2]} for t in cur.fetchall()]
            warranty_dict['tags'] = tags
            
            return jsonify({
                'warranty': warranty_dict,
                'columns': columns
            })
    except Exception as e:
        logger.error(f"Error retrieving warranty debug info: {e}")
        return jsonify({"error": f"Failed to retrieve warranty debug info: {str(e)}"}), 500
    finally:
        if conn:
            release_db_connection(conn)

@app.route('/api/debug/file-check', methods=['GET'])
@token_required
def debug_file_check():
    if not request.user.get('is_admin', False):
        return jsonify({"error": "Admin access required"}), 403
        
    filepath = request.args.get('path')
    if not filepath:
        return jsonify({"error": "No file path provided"}), 400
        
    # Check if this is just a filename or a path
    if '/' not in filepath:
        filepath = os.path.join('uploads', filepath)
        
    # Prepend /data if it doesn't start with it
    if not filepath.startswith('/data'):
        full_path = os.path.join('/data', filepath)
    else:
        full_path = filepath
        
    result = {
        'requested_path': filepath,
        'full_path': full_path,
        'exists': os.path.exists(full_path),
        'is_file': os.path.isfile(full_path) if os.path.exists(full_path) else False,
        'size_bytes': os.path.getsize(full_path) if os.path.exists(full_path) and os.path.isfile(full_path) else None,
        'last_modified': None
    }
    
    if result['exists'] and result['is_file']:
        try:
            stat_info = os.stat(full_path)
            result['last_modified'] = datetime.fromtimestamp(stat_info.st_mtime).isoformat()
            result['size_human'] = f"{result['size_bytes'] / 1024:.2f} KB" if result['size_bytes'] else None
        except Exception as e:
            result['error'] = str(e)
    
    return jsonify(result)

@app.route('/api/tags', methods=['GET'])
@token_required
def get_tags():
    """Get tags based on user role."""
    conn = None
    try:
        user_id = request.user['id']
        
        conn = get_db_connection()
        with conn.cursor() as cur:
            # Fetch tags created by the currently logged-in user
            cur.execute('SELECT id, name, color, created_at FROM tags WHERE user_id = %s ORDER BY name', (user_id,))
            
            tags = cur.fetchall()
            
            result = []
            for tag in tags:
                result.append({
                    'id': tag[0],
                    'name': tag[1],
                    'color': tag[2],
                    'created_at': tag[3].isoformat() if tag[3] else None
                    # Removed is_admin_tag comment
                })
            
            return jsonify(result), 200
    except Exception as e:
        logger.error(f"Error fetching tags: {e}")
        return jsonify({"error": "Failed to fetch tags"}), 500
    finally:
        if conn:
            release_db_connection(conn)

@app.route('/api/tags', methods=['POST'])
@token_required
def create_tag():
    """Create a new tag owned by the requesting user."""
    conn = None
    try:
        user_id = request.user['id'] # Get user ID
        data = request.json
        
        if not data or 'name' not in data:
            return jsonify({"error": "Tag name is required"}), 400
        
        name = data['name'].strip()
        color = data.get('color', '#808080')
        
        if not name:
            return jsonify({"error": "Tag name cannot be empty"}), 400
            
        # Validate color format (should be a hex color)
        if not re.match(r'^#[0-9A-Fa-f]{6}$', color):
            return jsonify({"error": "Invalid color format. Use hex format (e.g., #FF5733)"}), 400
        
        conn = get_db_connection()
        with conn.cursor() as cur:
            # Check if tag with this name already exists FOR THIS USER
            cur.execute('SELECT id FROM tags WHERE name = %s AND user_id = %s', (name, user_id)) # Added user_id check
            existing_tag = cur.fetchone()
            
            if existing_tag:
                 # Differentiate error message slightly
                return jsonify({"error": f"A tag with this name already exists for your account"}), 409 # Updated error message
            
            # Create new tag, setting user_id
            cur.execute(
                'INSERT INTO tags (name, color, user_id) VALUES (%s, %s, %s) RETURNING id', # Added user_id
                (name, color, user_id) # Pass user_id here
            )
            tag_id = cur.fetchone()[0]
            conn.commit()
            
            return jsonify({
                "id": tag_id,
                "name": name,
                "color": color,
                "message": "Tag created successfully"
            }), 201
    except Exception as e:
        logger.error(f"Error creating tag: {e}")
        if conn:
            conn.rollback()
        return jsonify({"error": "Failed to create tag"}), 500
    finally:
        if conn:
            release_db_connection(conn)

@app.route('/api/tags/<int:tag_id>', methods=['PUT'])
@token_required
def update_tag(tag_id):
    """Update an existing tag, ensuring user can only update their own type of tag."""
    user_id = request.user['id']
    data = request.get_json()
    new_name = data.get('name')
    new_color = data.get('color')
    
    if not new_name:
        return jsonify({"error": "Tag name cannot be empty"}), 400
        
    # Validate color format (basic check)
    if new_color and not re.match(r'^#[0-9a-fA-F]{6}$', new_color):
        return jsonify({"error": "Invalid color format. Use hex (e.g., #RRGGBB)"}), 400
        
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # Check if tag exists AND belongs to the user
            cur.execute('SELECT id, user_id FROM tags WHERE id = %s', (tag_id,)) # Check user_id
            tag = cur.fetchone()
            if not tag:
                return jsonify({"error": "Tag not found"}), 404
                
            tag_user_id = tag[1]
            if tag_user_id != user_id:
                # Prevent user from updating tag they don't own
                return jsonify({"error": "Permission denied to update this tag"}), 403
                
            # Check if new name conflicts with another tag FOR THIS USER
            cur.execute('SELECT id FROM tags WHERE name = %s AND id != %s AND user_id = %s', 
                        (new_name, tag_id, user_id)) # Added user_id check
            existing = cur.fetchone()
            if existing:
                # tag_type = "admin" if is_admin_updater else "user" # Removed
                return jsonify({"error": f"Another tag with this name already exists for your account"}), 409 # Updated error message
                
            # Update the tag
            cur.execute('UPDATE tags SET name = %s, color = %s, updated_at = NOW() WHERE id = %s RETURNING id, name, color', \
                        (new_name, new_color, tag_id))
            updated_tag = cur.fetchone()
        # conn.commit() and return statement are part of the try block, outside the 'with' block.
        conn.commit()
        return jsonify({"id": updated_tag[0], "name": updated_tag[1], "color": updated_tag[2]}), 200
            
    except Exception as e:
        logger.error(f"Error updating tag {tag_id}: {e}")
        if conn:
            conn.rollback() 
        return jsonify({"error": "Failed to update tag"}), 500
    finally:
        if conn:
            release_db_connection(conn)

@app.route('/api/tags/<int:tag_id>', methods=['DELETE'])
@token_required 
def delete_tag_endpoint(tag_id):
    """Delete a tag owned by the requesting user and its associations."""
    user_id = request.user['id'] # Get user ID
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # Check if tag exists AND belongs to the user
            cur.execute('SELECT id, user_id FROM tags WHERE id = %s', (tag_id,)) # Check user_id
            tag = cur.fetchone()
            if not tag:
                return jsonify({"error": "Tag not found"}), 404
            
            tag_user_id = tag[1]
            # Only allow deletion if the user owns the tag
            if tag_user_id != user_id:
                 # Prevent users from deleting tags they don't own
                return jsonify({"error": "Permission denied to delete this tag"}), 403

            # Delete associations from warranty_tags first
            cur.execute('DELETE FROM warranty_tags WHERE tag_id = %s', (tag_id,))
            
            # Delete the tag itself
            cur.execute('DELETE FROM tags WHERE id = %s', (tag_id,))
            
            conn.commit()
            
            return jsonify({"message": "Tag deleted successfully"}), 200
            
    except Exception as e:
        logger.error(f"Error deleting tag {tag_id}: {e}")
        if conn:
            conn.rollback()
        return jsonify({"error": "Failed to delete tag"}), 500
    finally:
        if conn:
            release_db_connection(conn)

@app.route('/api/warranties/<int:warranty_id>/tags', methods=['GET'])
@token_required
def get_warranty_tags(warranty_id):
    # """Get tags associated with a specific warranty, filtered by user role.""" # Docstring update needed
    """Get tags associated with a specific warranty."""
    conn = None
    try:
        user_id = request.user['id']
        # is_admin = request.user.get('is_admin', False) # Removed
        
        conn = get_db_connection()
        with conn.cursor() as cur:
            # First check if the warranty exists and user has access to it
            # Simplified check: just check if warranty exists and belongs to the user
            cur.execute('SELECT id FROM warranties WHERE id = %s AND user_id = %s', 
                      (warranty_id, user_id))
            
            if cur.fetchone() is None:
                # Add admin check here if admins should be able to see tags for any warranty
                is_admin = request.user.get('is_admin', False)
                if is_admin:
                    cur.execute('SELECT id FROM warranties WHERE id = %s', (warranty_id,))
                    if cur.fetchone() is None:
                        return jsonify({"error": "Warranty not found"}), 404
                else:
                     return jsonify({"error": "Warranty not found or you don't have permission to access it"}), 404
            
            # Get tags for this warranty (show all associated tags)
            cur.execute('''
                SELECT t.id, t.name, t.color, t.created_at
                FROM tags t
                JOIN warranty_tags wt ON t.id = wt.tag_id
                WHERE wt.warranty_id = %s -- Removed user_id/is_admin filter
                ORDER BY t.name
            ''', (warranty_id,))
            
            tags = cur.fetchall()
            
            result = []
            for tag in tags:
                result.append({
                    'id': tag[0],
                    'name': tag[1],
                    'color': tag[2],
                    'created_at': tag[3].isoformat() if tag[3] else None
                })
            
            return jsonify(result), 200
    except Exception as e:
        logger.error(f"Error fetching tags for warranty {warranty_id}: {e}")
        return jsonify({"error": "Failed to fetch tags for this warranty"}), 500
    finally:
        if conn:
            release_db_connection(conn)

@app.route('/api/warranties/<int:warranty_id>/tags', methods=['POST'])
@token_required
def add_tags_to_warranty(warranty_id):
    # """Add tags to a warranty, ensuring tags match user role.""" # Docstring update needed
    """Add tags owned by the user to a warranty they own."""
    conn = None
    try:
        user_id = request.user['id']
        # is_admin = request.user.get('is_admin', False) # Removed
        
        data = request.json
        if not data or 'tag_ids' not in data:
            return jsonify({"error": "tag_ids array is required"}), 400
        
        tag_ids = data['tag_ids']
        if not isinstance(tag_ids, list):
            return jsonify({"error": "tag_ids must be an array of tag IDs"}), 400
        
        conn = get_db_connection()
        with conn.cursor() as cur:
            # First check if the warranty exists and user has access to it (owns it)
            cur.execute('SELECT id FROM warranties WHERE id = %s AND user_id = %s', 
                      (warranty_id, user_id))
            
            if cur.fetchone() is None:
                 # Add admin check here if admins should modify any warranty tags
                is_admin = request.user.get('is_admin', False)
                if is_admin:
                    cur.execute('SELECT id FROM warranties WHERE id = %s', (warranty_id,))
                    if cur.fetchone() is None:
                         return jsonify({"error": "Warranty not found"}), 404
                    # Allow admin to proceed even if they don't own it
                else:
                    return jsonify({"error": "Warranty not found or you don't have permission to modify it"}), 404
            
            # Validate tags before removing/adding
            valid_tag_ids = []
            if tag_ids: # Only validate if there are tags to add
                # Check if all provided tag IDs exist AND belong to the user
                placeholders = ', '.join(['%s'] * len(tag_ids))
                # Ensure the tags being added are owned by the user adding them
                sql = f'SELECT id, user_id FROM tags WHERE id IN ({placeholders}) AND user_id = %s' 
                cur.execute(sql, tag_ids + [user_id]) # Check against current user_id
                found_tags = cur.fetchall()
                
                found_tag_map = {tag[0]: tag[1] for tag in found_tags}
                
                for tag_id in tag_ids:
                    if tag_id not in found_tag_map: # This check also implicitly confirms ownership due to the query change
                        conn.rollback() # Ensure transaction consistency
                        return jsonify({"error": f"Tag with ID {tag_id} not found or not owned by you"}), 404
                    # Removed the old is_admin check
                    # if found_tag_map[tag_id] != is_admin: 
                    #     conn.rollback()
                    #     tag_type_required = "admin" if is_admin else "user"
                    #     return jsonify({"error": f"Tag with ID {tag_id} is not a valid {tag_type_required} tag"}), 403
                    valid_tag_ids.append(tag_id) # Keep track of validated tags
            
            # Remove ALL existing tags before adding new ones for simplicity
            # The old logic only removed tags of the same "type", which is no longer relevant
            cur.execute('DELETE FROM warranty_tags WHERE warranty_id = %s', (warranty_id,))
            
            # Add new (validated) tags
            if valid_tag_ids:
                values_placeholder = ', '.join(['(%s, %s)'] * len(valid_tag_ids))
                sql = f'INSERT INTO warranty_tags (warranty_id, tag_id) VALUES {values_placeholder}'
                params = []
                for tag_id in valid_tag_ids:
                    params.extend([warranty_id, tag_id])
                cur.execute(sql, params)
            
            conn.commit()
            return jsonify({"message": "Tags updated successfully"}), 200
    except Exception as e:
        logger.error(f"Error updating tags for warranty {warranty_id}: {e}")
        if conn:
            conn.rollback()
        return jsonify({"error": "Failed to update tags"}), 500
    finally:
        if conn:
            release_db_connection(conn)

# --- CSV Import Endpoint ---
# Updated CSV Headers for duration components
REQUIRED_CSV_HEADERS = ['ProductName', 'PurchaseDate']
OPTIONAL_CSV_HEADERS = [
    'IsLifetime', 'PurchasePrice', 'SerialNumber', 'ProductURL', 'Tags', 'Vendor', 'WarrantyType',
    'WarrantyDurationYears', 'WarrantyDurationMonths', 'WarrantyDurationDays'
]

@app.route('/api/warranties/import', methods=['POST'])
@token_required
def import_warranties():
    if 'csv_file' not in request.files:
        return jsonify({"error": "No CSV file provided"}), 400

    file = request.files['csv_file']

    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    if not file.filename.lower().endswith('.csv'):
        return jsonify({"error": "Invalid file type. Please upload a .csv file"}), 400

    user_id = request.user['id']
    conn = None
    imported_count = 0
    failed_rows = []
    row_number = 1 # Start from 1 for header

    try:
        # Read the file content
        stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
        csv_reader = csv.DictReader(stream)

        # Validate headers
        headers = csv_reader.fieldnames
        # Check required headers first
        missing_required = [h for h in REQUIRED_CSV_HEADERS if h not in headers]
        if missing_required:
            return jsonify({"error": f"Missing required CSV columns: {', '.join(missing_required)}"}), 400
        
        # Check for unknown headers
        known_headers = set(REQUIRED_CSV_HEADERS + OPTIONAL_CSV_HEADERS)
        unknown_headers = [h for h in headers if h not in known_headers]
        if unknown_headers:
            logger.warning(f"CSV file contains unknown headers which will be ignored: {', '.join(unknown_headers)}")

        conn = get_db_connection()
        conn.autocommit = False # Start transaction

        with conn.cursor() as cur:
            for row in csv_reader:
                row_number += 1 # Increment for each data row (header is row 1)
                errors = []
                processed_row = {}

                try:
                    # --- Data Extraction and Basic Validation ---
                    product_name = row.get('ProductName', '').strip()
                    purchase_date_str = row.get('PurchaseDate', '').strip()
                    is_lifetime_str = row.get('IsLifetime', 'false').strip().lower()
                    
                    # New duration fields
                    warranty_duration_years_str = row.get('WarrantyDurationYears', '0').strip()
                    warranty_duration_months_str = row.get('WarrantyDurationMonths', '0').strip()
                    warranty_duration_days_str = row.get('WarrantyDurationDays', '0').strip()
                    
                    purchase_price_str = row.get('PurchasePrice', '').strip()
                    serial_numbers_str = row.get('SerialNumber', '').strip()
                    product_url = row.get('ProductURL', '').strip()
                    tags_str = row.get('Tags', '').strip() # Get Tags string
                    vendor = row.get('Vendor', '').strip() # Extract Vendor
                    warranty_type = row.get('WarrantyType', '').strip() # Extract Warranty Type

                    if not product_name:
                        errors.append("ProductName is required.")
                    if not purchase_date_str:
                        errors.append("PurchaseDate is required.")

                    # --- Type/Format Validation --- 
                    try:
                        purchase_date = datetime.strptime(purchase_date_str, '%Y-%m-%d').date()
                    except ValueError:
                        errors.append("Invalid PurchaseDate format. Use YYYY-MM-DD.")
                        purchase_date = None # Set to None to prevent further errors

                    is_lifetime = is_lifetime_str == 'true'
                    expiration_date = None
                    warranty_duration_years = 0
                    warranty_duration_months = 0
                    warranty_duration_days = 0

                    if not is_lifetime:
                        try:
                            warranty_duration_years = int(warranty_duration_years_str) if warranty_duration_years_str else 0
                            warranty_duration_months = int(warranty_duration_months_str) if warranty_duration_months_str else 0
                            warranty_duration_days = int(warranty_duration_days_str) if warranty_duration_days_str else 0

                            if warranty_duration_years < 0 or warranty_duration_months < 0 or warranty_duration_days < 0:
                                errors.append("Warranty duration components cannot be negative.")
                            if warranty_duration_months >= 12:
                                errors.append("WarrantyDurationMonths must be less than 12.")
                            if warranty_duration_days >= 366: # Basic check
                                errors.append("WarrantyDurationDays seems too high.")
                            if warranty_duration_years == 0 and warranty_duration_months == 0 and warranty_duration_days == 0:
                                errors.append("Warranty duration (Years, Months, or Days) is required unless IsLifetime is TRUE.")
                            if warranty_duration_years > 100:
                                errors.append("WarrantyDurationYears must be 100 or less.")
                        except ValueError:
                            errors.append("WarrantyDurationYears, WarrantyDurationMonths, WarrantyDurationDays must be valid numbers.")
                    
                    purchase_price = None
                    if purchase_price_str:
                        try:
                            purchase_price = float(purchase_price_str)
                            if purchase_price < 0:
                                errors.append("PurchasePrice cannot be negative.")
                        except ValueError:
                            errors.append("PurchasePrice must be a valid number.")

                    # Calculate expiration date if valid
                    if not errors and not is_lifetime and purchase_date:
                        if warranty_duration_years > 0 or warranty_duration_months > 0 or warranty_duration_days > 0:
                            try:
                                expiration_date = purchase_date + relativedelta(
                                    years=warranty_duration_years,
                                    months=warranty_duration_months,
                                    days=warranty_duration_days
                                )
                                logger.info(f"[Import] Calculated expiration date: {expiration_date} for row {row_number}")
                            except Exception as calc_err:
                                logger.error(f"[Import] Error calculating expiration date for row {row_number}: {calc_err}")
                                errors.append("Failed to calculate expiration date from duration components.")
                                expiration_date = None
                        # No else needed here, error for missing duration already handled

                    # Split serial numbers
                    serial_numbers = [sn.strip() for sn in serial_numbers_str.split(',') if sn.strip()] if serial_numbers_str else []

                    # --- Process Tags --- 
                    tag_ids_to_link = []
                    if tags_str:
                        tag_names = [name.strip() for name in tags_str.split(',') if name.strip()]
                        if tag_names:
                            # Find existing tag IDs (case-insensitive) for THIS USER
                            placeholders = ', '.join(['%s'] * len(tag_names))
                            # Include user_id in the lookup
                            sql = f"SELECT id, LOWER(name) FROM tags WHERE LOWER(name) IN ({placeholders}) AND user_id = %s"
                            cur.execute(sql, [name.lower() for name in tag_names] + [user_id]) # Add user_id
                            existing_tags = {name_lower: tag_id for tag_id, name_lower in cur.fetchall()}
                            
                            processed_tag_ids = []
                            tags_to_create = []
                            
                            for name in tag_names:
                                name_lower = name.lower()
                                if name_lower in existing_tags:
                                    processed_tag_ids.append(existing_tags[name_lower])
                                else:
                                    # Avoid queuing the same new tag multiple times within the same row
                                    if name_lower not in [t['name_lower'] for t in tags_to_create]:
                                        tags_to_create.append({'name': name, 'name_lower': name_lower})
                            
                            # Create tags that don't exist for this user
                            if tags_to_create:
                                default_color = '#808080' # Default color for new tags
                                for tag_data in tags_to_create:
                                    try:
                                        # Insert new tag with default color, preserving original case for name, AND user_id
                                        cur.execute(
                                            "INSERT INTO tags (name, color, user_id) VALUES (%s, %s, %s) RETURNING id",
                                            (tag_data['name'], default_color, user_id) # Add user_id
                                        )
                                        new_tag_id = cur.fetchone()[0]
                                        processed_tag_ids.append(new_tag_id)
                                        logger.info(f"Created new tag '{(tag_data['name'])}' with ID {new_tag_id} for user {user_id} during CSV import.")
                                    except Exception as tag_insert_err:
                                        # If tag creation fails (e.g., unique constraint conflict due to race condition),
                                        # ensure the constraint includes user_id
                                        logger.error(f"Error creating tag '{(tag_data['name'])}' for user {user_id} during import: {tag_insert_err}")
                                        # Attempt to fetch the ID again in case it was created by another process
                                        cur.execute("SELECT id FROM tags WHERE LOWER(name) = %s AND user_id = %s", (tag_data['name_lower'], user_id))
                                        existing_id_result = cur.fetchone()
                                        if existing_id_result:
                                            processed_tag_ids.append(existing_id_result[0])
                                        else:
                                             # Add error to the row if tag creation failed and wasn't found
                                            errors.append(f"Failed to create or find tag: {(tag_data['name'])}")
                                            
                            # Consolidate tag IDs to link
                            if processed_tag_ids:
                                tag_ids_to_link = list(set(processed_tag_ids)) # Ensure unique IDs

                            # Removed the skipped tags warning as we now create them
                            # if skipped_tags:
                            #     errors.append(f"Skipped non-existent tags: {', '.join(skipped_tags)}.")

                    # --- Check for Duplicates --- 
                    if not errors and product_name and purchase_date:
                        cur.execute("""
                            SELECT id FROM warranties 
                            WHERE user_id = %s AND product_name = %s AND purchase_date = %s
                        """, (user_id, product_name, purchase_date))
                        if cur.fetchone(): # Correctly indented
                            errors.append("Duplicate warranty found (same product name and purchase date).")
                    
                    # --- If errors, skip row --- 
                    if errors:
                        failed_rows.append({"row": row_number, "errors": errors})
                        continue

                    # --- Insert into Database --- 
                    cur.execute("""
                        INSERT INTO warranties (
                            product_name, purchase_date, expiration_date, 
                            product_url, purchase_price, user_id, is_lifetime, vendor, warranty_type,
                            warranty_duration_years, warranty_duration_months, warranty_duration_days
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        RETURNING id
                    """, (
                        product_name, purchase_date, expiration_date,
                        product_url, purchase_price, user_id, is_lifetime, vendor, warranty_type,
                        warranty_duration_years, warranty_duration_months, warranty_duration_days
                    ))
                    warranty_id = cur.fetchone()[0]

                    # Insert serial numbers
                    if serial_numbers:
                        for serial_number in serial_numbers:
                            cur.execute("""
                                INSERT INTO serial_numbers (warranty_id, serial_number)
                                VALUES (%s, %s)
                            """, (warranty_id, serial_number))
                    
                    # Link tags
                    if tag_ids_to_link:
                        for tag_id in tag_ids_to_link:
                             cur.execute("""
                                INSERT INTO warranty_tags (warranty_id, tag_id)
                                VALUES (%s, %s)
                                ON CONFLICT (warranty_id, tag_id) DO NOTHING -- Avoid errors if somehow duplicated
                            """, (warranty_id, tag_id))

                    imported_count += 1

                except Exception as e:
                    logger.error(f"Error processing CSV row {row_number}: {e}")
                    failed_rows.append({"row": row_number, "errors": [f"Internal processing error: {str(e)}"]})
                    # Don't rollback yet, just record failure

            # --- Transaction Commit/Rollback --- 
            if failed_rows:
                conn.rollback() # Rollback if any row failed during processing or insertion
                # Reset imported count if we rollback
                final_success_count = 0 
                # Modify errors for rows that might have been initially valid but failed due to rollback
                final_failure_count = row_number - 1 # Total data rows processed
                # Add a general error message
                return jsonify({
                    "error": "Import failed due to errors in one or more rows. No warranties were imported.",
                    "success_count": 0,
                    "failure_count": final_failure_count,
                    "errors": failed_rows 
                }), 400
            else:
                conn.commit() # Commit transaction if all rows were processed successfully
                final_success_count = imported_count
                final_failure_count = len(failed_rows)

        return jsonify({
            "message": "CSV processed.",
            "success_count": final_success_count,
            "failure_count": final_failure_count,
            "errors": failed_rows
        }), 200

    except Exception as e:
        if conn:
            conn.rollback() # Rollback on general error
        logger.error(f"Error importing CSV: {e}")
        return jsonify({"error": f"Failed to import CSV: {str(e)}"}), 500
    finally:
        if conn:
            conn.autocommit = True # Reset autocommit
            release_db_connection(conn)

# --- End CSV Import Endpoint ---

# --- PATCH START: Currency Symbol Support ---
# 1. Add a helper function to check if the currency_symbol column exists in user_preferences

def has_currency_symbol_column(cursor):
    cursor.execute("""
        SELECT column_name FROM information_schema.columns 
        WHERE table_name = 'user_preferences' AND column_name = 'currency_symbol'
    """)
    return cursor.fetchone() is not None

# 2. Update GET /api/auth/preferences
#    - Add currency_symbol to CREATE TABLE, SELECT, INSERT, and response
#    - Default to '$' if not set
#
# 3. Update PUT /api/auth/preferences
#    - Accept currency_symbol from request data and update if provided
#    - Add currency_symbol to CREATE TABLE, SELECT, INSERT, UPDATE, and response
#    - Default to '$' if not set
# --- PATCH END ---

@app.route('/api/auth/password/reset', methods=['POST'])
def reset_password():
    conn = None
    try:
        data = request.get_json()
        
        if not data.get('token') or not data.get('password'):
            return jsonify({'message': 'Token and password are required!'}), 400
        
        token = data['token']
        password = data['password']
        
        # Validate password strength
        if not is_valid_password(password):
            return jsonify({'message': 'Password must be at least 8 characters and include uppercase, lowercase, and numbers!'}), 400
        
        conn = get_db_connection()
        with conn.cursor() as cur:
            # Check if token exists and is valid
            cur.execute('SELECT user_id, expires_at FROM password_reset_tokens WHERE token = %s', (token,))
            token_info = cur.fetchone()
            
            if not token_info or token_info[1] < datetime.utcnow():
                return jsonify({'message': 'Invalid or expired token!'}), 400
            
            user_id = token_info[0]
            
            # Hash the new password
            password_hash = bcrypt.generate_password_hash(password).decode('utf-8')
            
            # Update user's password
            cur.execute('UPDATE users SET password_hash = %s WHERE id = %s', (password_hash, user_id))
            
            # Delete the used token
            cur.execute('DELETE FROM password_reset_tokens WHERE token = %s', (token,))
            
            conn.commit()
            
            return jsonify({'message': 'Password reset successful!'}), 200
    except Exception as e:
        logger.error(f"Password reset error: {e}")
        if conn:
            conn.rollback()
        return jsonify({'message': 'Password reset failed!'}), 500
    finally:
        if conn:
            release_db_connection(conn)

@app.route('/api/auth/password/change', methods=['POST'])
@token_required
def change_password():
    """Allow logged-in users to change their password"""
    conn = None
    try:
        data = request.get_json()
        
        if not data.get('current_password') or not data.get('new_password'):
            return jsonify({'message': 'Current password and new password are required!'}), 400
        
        current_password = data['current_password']
        new_password = data['new_password']
        user_id = request.user['id']  # Get user ID from the token_required decorator
        
        # Validate new password strength
        if not is_valid_password(new_password):
            return jsonify({'message': 'New password must be at least 8 characters and include uppercase, lowercase, and numbers!'}), 400
        
        conn = get_db_connection()
        with conn.cursor() as cur:
            # Get the user's current password hash
            cur.execute('SELECT password_hash FROM users WHERE id = %s', (user_id,))
            user_data = cur.fetchone()
            
            if not user_data:
                return jsonify({'message': 'User not found!'}), 404
            
            current_password_hash = user_data[0]
            
            # Verify the current password
            if not bcrypt.check_password_hash(current_password_hash, current_password):
                return jsonify({'message': 'Incorrect current password!'}), 401
            
            # Hash the new password
            new_password_hash = bcrypt.generate_password_hash(new_password).decode('utf-8')
            
            # Update the password in the database
            cur.execute('UPDATE users SET password_hash = %s WHERE id = %s', (new_password_hash, user_id))
            
            conn.commit()
            
            return jsonify({'message': 'Password changed successfully!'}), 200
            
    except Exception as e:
        logger.error(f"Password change error: {e}")
        if conn:
            conn.rollback()
        return jsonify({'message': 'Failed to change password!'}), 500
    finally:
        if conn:
            release_db_connection(conn)

def send_email_change_verification_email(recipient_email, verification_link_path_with_token):
    """Sends an email with a link to verify the new email address."""
    try:
        smtp_host = os.environ.get('SMTP_HOST', 'localhost')
        smtp_port = int(os.environ.get('SMTP_PORT', 1025))
        smtp_username = os.environ.get('SMTP_USERNAME')
        smtp_password = os.environ.get('SMTP_PASSWORD')
        smtp_use_tls = os.environ.get('SMTP_USE_TLS', 'true').lower() == 'true'
        smtp_use_ssl = os.environ.get('SMTP_USE_SSL', 'false').lower() == 'true'
        sender_email = os.environ.get('SMTP_SENDER_EMAIL', 'noreply@warracker.com')
        app_name = "Warracker" # Or get from config
        
        # Explicit SMTP_USE_TLS from environment, defaulting to true if port is 587
        # and not explicitly set to false.
        smtp_use_tls_env = os.environ.get('SMTP_USE_TLS', 'not_set').lower()
        
        subject = f"Confirm Your New Email Address - {app_name}"
        
        app_base_url = os.environ.get('APP_BASE_URL', request.url_root.rstrip('/'))
        full_verification_link = f"{app_base_url}{verification_link_path_with_token}"

        html_content = None
        email_template_path = os.path.join(os.path.dirname(__file__), 'templates', 'email_change_verification.html')
        if os.path.exists(email_template_path):
            with open(email_template_path, 'r') as f:
                html_content = f.read()
            html_content = html_content.replace("{{verification_link}}", full_verification_link)
            html_content = html_content.replace("{{app_name}}", app_name)
            html_content = html_content.replace("{{expiration_hours}}", str(EMAIL_CHANGE_TOKEN_EXPIRATION_HOURS))
        else:
            logger.warning(f"Email template not found: {email_template_path}. Using basic HTML fallback.")
            html_content = f"""            <html>
                <body>
                    <p>Hello,</p>
                    <p>Please click the link below to confirm your new email address for {app_name}:</p>
                    <p><a href="{full_verification_link}">Confirm Email Change</a></p>
                    <p>If you did not request this change, please ignore this email.</p>
                    <p>This link will expire in {EMAIL_CHANGE_TOKEN_EXPIRATION_HOURS} hours.</p>
                    <p>Thanks,<br>The {app_name} Team</p>
                </body>
            </html>
            """

        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = sender_email
        msg['To'] = recipient_email
        msg.attach(MIMEText(html_content, 'html'))

        logger.info(f"Attempting to send email change verification to {recipient_email} via {smtp_host}:{smtp_port}")

        server = None
        logger.info(f"Attempting SMTP connection to {smtp_host}:{smtp_port}")
        if smtp_port == 465:
            logger.info("Using SMTP_SSL for port 465.")
            server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=10)
        else:
            logger.info(f"Using SMTP for port {smtp_port}.")
            server = smtplib.SMTP(smtp_host, smtp_port, timeout=10)
            # For port 587, STARTTLS is standard.
            # For other ports, allow SMTP_USE_TLS to explicitly enable/disable it.
            # If SMTP_USE_TLS is 'not_set', default to True for port 587.
            should_use_starttls = False
            if smtp_port == 587:
                should_use_starttls = (smtp_use_tls_env != 'false') # True unless explicitly 'false'
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
        
        if smtp_username and smtp_password:
            logger.info(f"Logging in with username: {smtp_username}")
            server.login(smtp_username, smtp_password)
            logger.info("SMTP login successful.")
            
        server.sendmail(sender_email, recipient_email, msg.as_string())
        server.quit()
        logger.info(f"Email change verification sent successfully to {recipient_email}")
        return True
    except smtplib.SMTPAuthenticationError as e:
        logger.error(f"SMTP Authentication Error sending email change verification: {e}")
    except Exception as e:
        logger.error(f"Error sending email change verification: {e}", exc_info=True)
    return False

def generate_secure_token(length=40):
    """Generates a cryptographically secure random string token."""
    return uuid.uuid4().hex + uuid.uuid4().hex[:length-len(uuid.uuid4().hex)]

@app.route('/api/auth/change-email', methods=['POST'])
@token_required
def request_email_change():
    current_user_id = request.user['id'] # Get user ID from decorator
    data = request.get_json()
    new_email = data.get('new_email')
    password = data.get('password')

    if not new_email or not password:
        return jsonify({'message': 'New email and password are required'}), 400

    if not is_valid_email(new_email):
        return jsonify({'message': 'Invalid new email format'}), 400

    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Fetch current user's password hash and current email
        cur.execute("SELECT password_hash, email FROM users WHERE id = %s", (current_user_id,))
        user_data = cur.fetchone()

        if not user_data:
            return jsonify({'message': 'User not found'}), 404 # Should not happen with @token_required

        current_password_hash, current_email = user_data

        if not bcrypt.check_password_hash(current_password_hash, password):
            return jsonify({'message': 'Incorrect password'}), 401
            
        if new_email.lower() == current_email.lower():
            return jsonify({'message': 'New email cannot be the same as the current email'}), 400

        # Check if the new email is already in use by another user
        cur.execute("SELECT id FROM users WHERE email = %s AND id != %s", (new_email.lower(), current_user_id))
        if cur.fetchone():
            return jsonify({'message': 'This email address is already in use by another account.'}), 409
            
        # Check for an existing, non-expired, non-used request for this user and new email
        cur.execute("""
            SELECT id, token_expires_at FROM email_change_requests 
            WHERE user_id = %s AND new_email = %s AND is_used = FALSE AND token_expires_at > NOW()
        """, (current_user_id, new_email.lower()))
        existing_request = cur.fetchone()

        if existing_request:
            # Potentially resend email if requested soon after, or just inform user
            return jsonify({'message': 'An email change request for this address is already pending. Please check your inbox.'}), 409

        # Invalidate any older, unused tokens for this user to prevent multiple active links
        cur.execute("UPDATE email_change_requests SET is_used = TRUE, token_expires_at = NOW() WHERE user_id = %s AND is_used = FALSE", (current_user_id,))


        verification_token = generate_secure_token()
        token_expires_at = datetime.utcnow().replace(tzinfo=pytz.utc) + timedelta(hours=EMAIL_CHANGE_TOKEN_EXPIRATION_HOURS)
        
        # Get app base URL from environment or config
        app_base_url = os.environ.get('APP_BASE_URL', request.url_root.rstrip('/'))
        verification_link = f"{app_base_url}{EMAIL_CHANGE_VERIFICATION_ENDPOINT}?token={verification_token}"

        cur.execute("""
            INSERT INTO email_change_requests (user_id, new_email, verification_token, token_expires_at)
            VALUES (%s, %s, %s, %s)
        """, (current_user_id, new_email.lower(), verification_token, token_expires_at))
        
        conn.commit()

        if send_email_change_verification_email(new_email, verification_link):
            return jsonify({'message': f'Verification email sent to {new_email}. Please check your inbox to confirm.'}), 200
        else:
            # Rollback if email sending failed, to allow user to try again
            # Or, consider if the request should remain, and user can request resend.
            # For now, simple rollback.
            conn.rollback() 
            return jsonify({'message': 'Failed to send verification email. Please try again later.'}), 500

    except psycopg2.Error as e:
        if conn:
            conn.rollback()
        logger.error(f"Database error during email change request: {e}")
        return jsonify({'message': 'Database error processing your request.'}), 500
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Error requesting email change: {e}")
        return jsonify({'message': 'An unexpected error occurred.'}), 500
    finally:
        if conn:
            cur.close()
            release_db_connection(conn)

@app.route('/api/auth/verify-email-change', methods=['POST'])
# This endpoint might not need @token_required if the verification_token itself is the auth mechanism
# However, if a user is already logged in on the browser where they click the link,
# it might be good to associate, but the primary auth is the token from email.
def verify_email_change():
    data = request.get_json()
    verification_token = data.get('token')

    if not verification_token:
        return jsonify({'message': 'Verification token is required'}), 400

    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT id, user_id, new_email, token_expires_at 
            FROM email_change_requests 
            WHERE verification_token = %s AND is_used = FALSE
        """, (verification_token,))
        request_data = cur.fetchone()

        if not request_data:
            return jsonify({'message': 'Invalid or expired verification token.'}), 400

        req_id, user_id, new_email, token_expires_at = request_data
        
        # Ensure token_expires_at is timezone-aware for comparison
        if token_expires_at.tzinfo is None:
            token_expires_at = pytz.utc.localize(token_expires_at)

        if datetime.utcnow().replace(tzinfo=pytz.utc) > token_expires_at:
            # Mark as used/expired anyway
            cur.execute("UPDATE email_change_requests SET is_used = TRUE WHERE id = %s", (req_id,))
            conn.commit()
            return jsonify({'message': 'Verification token has expired.'}), 400

        # Check if the new email has been taken by another user *since the request was made*
        # This is a rare race condition but good to check.
        cur.execute("SELECT id FROM users WHERE email = %s AND id != %s", (new_email, user_id))
        if cur.fetchone():
            cur.execute("UPDATE email_change_requests SET is_used = TRUE WHERE id = %s", (req_id,)) # Invalidate token
            conn.commit()
            return jsonify({'message': 'This email address has recently been claimed by another account. Please try a different email.'}), 409

        # Update user's email
        cur.execute("UPDATE users SET email = %s, updated_at = NOW() WHERE id = %s", (new_email, user_id))
        
        # Mark token as used
        cur.execute("UPDATE email_change_requests SET is_used = TRUE WHERE id = %s", (req_id,))
        
        conn.commit()
        
        # Optionally, log the user out of other sessions for security.
        # This would require a session management mechanism (e.g., storing session IDs or using JWT blacklisting).
        # For now, we will skip this, but it's a good addition for production.

        # Optionally, send a notification to the OLD email address that the email has been changed.
        # old_email_query = "SELECT email FROM users WHERE id = %s" # This would get new email now
        # To get old email, it should have been selected before the update or passed through.
        # For simplicity, this step is omitted but recommended.

        return jsonify({'message': 'Email address updated successfully.'}), 200

    except psycopg2.Error as e:
        if conn:
            conn.rollback()
        logger.error(f"Database error during email verification: {e}")
        return jsonify({'message': 'Database error processing your request.'}), 500
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Error verifying email change: {e}")
        return jsonify({'message': 'An unexpected error occurred.'}), 500
    finally:
        if conn:
            cur.close()
            release_db_connection(conn)

@app.route('/api/settings/oidc-status', methods=['GET'])
def get_oidc_status():
    """Public endpoint to check if OIDC is enabled."""
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT value FROM site_settings WHERE key = 'oidc_enabled'")
            result = cur.fetchone()
            oidc_enabled = False
            if result and result[0].lower() == 'true':
                oidc_enabled = True
            
            # Also check app.config as a fallback, though DB should be primary
            if not result and app.config.get('OIDC_ENABLED'):
                 oidc_enabled = True

            return jsonify({'oidc_enabled': oidc_enabled}), 200
    except Exception as e:
        logger.error(f"Error fetching OIDC status: {e}")
        # Fallback to app.config or default to false if DB error
        return jsonify({'oidc_enabled': app.config.get('OIDC_ENABLED', False)}), 200
    finally:
        if conn:
            release_db_connection(conn)

# =====================
# APPRISE NOTIFICATION ROUTES
# =====================

@app.route('/api/admin/apprise/test', methods=['POST'])
@admin_required
def test_apprise_notification():
    """Send a test Apprise notification"""
    if not APPRISE_AVAILABLE or apprise_handler is None:
        return jsonify({'success': False, 'message': 'Apprise notifications are not available'}), 503
    
    try:
        data = request.get_json()
        test_url = data.get('test_url') if data else None
        
        success = apprise_handler.send_test_notification(test_url)
        
        if success:
            return jsonify({'success': True, 'message': 'Test notification sent successfully'}), 200
        else:
            return jsonify({'success': False, 'message': 'Failed to send test notification'}), 400
            
    except Exception as e:
        logger.error(f"Error sending test Apprise notification: {e}")
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

@app.route('/api/admin/apprise/validate-url', methods=['POST'])
@admin_required
def validate_apprise_url():
    """Validate an Apprise notification URL"""
    if not APPRISE_AVAILABLE or apprise_handler is None:
        return jsonify({'valid': False, 'message': 'Apprise notifications are not available'}), 503
    
    try:
        data = request.get_json()
        url = data.get('url')
        
        if not url:
            return jsonify({'valid': False, 'message': 'URL is required'}), 400
        
        is_valid = apprise_handler.validate_url(url)
        
        return jsonify({
            'valid': is_valid,
            'message': 'URL is valid' if is_valid else 'URL is invalid or unsupported'
        }), 200
        
    except Exception as e:
        logger.error(f"Error validating Apprise URL: {e}")
        return jsonify({'valid': False, 'message': f'Error: {str(e)}'}), 500

@app.route('/api/admin/apprise/supported-services', methods=['GET'])
@admin_required
def get_supported_apprise_services():
    """Get list of supported Apprise services"""
    if not APPRISE_AVAILABLE or apprise_handler is None:
        return jsonify({'services': [], 'message': 'Apprise notifications are not available'}), 503
    
    try:
        services = apprise_handler.get_supported_services()
        return jsonify({'services': services}), 200
        
    except Exception as e:
        logger.error(f"Error getting supported Apprise services: {e}")
        return jsonify({'services': [], 'message': f'Error: {str(e)}'}), 500

@app.route('/api/admin/apprise/send-expiration', methods=['POST'])
@admin_required
def trigger_apprise_expiration_notifications():
    """Manually trigger Apprise expiration notifications"""
    if not APPRISE_AVAILABLE or apprise_handler is None:
        return jsonify({'success': False, 'message': 'Apprise notifications are not available'}), 503
    
    try:
        results = apprise_handler.send_expiration_notifications()
        
        return jsonify({
            'success': True,
            'message': f'Notifications processed: {results["sent"]} sent, {results["errors"]} errors',
            'results': results
        }), 200
        
    except Exception as e:
        logger.error(f"Error triggering Apprise expiration notifications: {e}")
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

@app.route('/api/admin/apprise/reload-config', methods=['POST'])
@admin_required
def reload_apprise_configuration():
    """Reload Apprise configuration from database and environment"""
    if not APPRISE_AVAILABLE or apprise_handler is None:
        return jsonify({'success': False, 'message': 'Apprise notifications are not available'}), 503
    
    try:
        apprise_handler.reload_configuration()
        
        return jsonify({
            'success': True,
            'message': 'Apprise configuration reloaded successfully',
            'enabled': apprise_handler.enabled,
            'urls_configured': len(apprise_handler.notification_urls)
        }), 200
        
    except Exception as e:
        logger.error(f"Error reloading Apprise configuration: {e}")
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

@app.route('/api/admin/apprise/send-custom', methods=['POST'])
@admin_required
def send_custom_apprise_notification():
    """Send a custom Apprise notification"""
    if not APPRISE_AVAILABLE or apprise_handler is None:
        return jsonify({'success': False, 'message': 'Apprise notifications are not available'}), 503
    
    try:
        data = request.get_json()
        title = data.get('title')
        message = data.get('message')
        urls = data.get('urls')  # Optional: specific URLs to send to
        
        if not title or not message:
            return jsonify({'success': False, 'message': 'Title and message are required'}), 400
        
        success = apprise_handler.send_custom_notification(title, message, urls)
        
        if success:
            return jsonify({'success': True, 'message': 'Custom notification sent successfully'}), 200
        else:
            return jsonify({'success': False, 'message': 'Failed to send custom notification'}), 400
            
    except Exception as e:
        logger.error(f"Error sending custom Apprise notification: {e}")
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

@app.route('/api/admin/apprise/status', methods=['GET'])
@admin_required
def get_apprise_status():
    """Get current Apprise configuration status"""
    if not APPRISE_AVAILABLE or apprise_handler is None:
        return jsonify({
            'available': False,
            'enabled': False,
            'message': 'Apprise library is not installed or not available'
        }), 503
    
    try:
        # Get detailed status from the handler
        status = apprise_handler.get_status()
        
        # Add additional fields for backward compatibility
        status.update({
            'expiration_days': apprise_handler.expiration_days,
            'notification_time': apprise_handler.notification_time,
            'title_prefix': apprise_handler.title_prefix,
            'message': 'Apprise is available and configured' if status.get('available') else status.get('error', 'Unknown error')
        })
        
        return jsonify(status), 200
        
    except Exception as e:
        logger.error(f"Error getting Apprise status: {e}")
        return jsonify({
            'available': False,
            'enabled': False,
            'message': f'Error: {str(e)}'
        }), 500

@app.route('/api/admin/warranties', methods=['GET'])
@admin_required
def get_all_warranties():
    """Get all warranties from all users (admin only)"""
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # Get all warranties from all users with user information
            cur.execute('''
                SELECT w.id, w.product_name, w.purchase_date, w.expiration_date, w.invoice_path, w.manual_path, w.other_document_path, 
                       w.product_url, w.notes, w.purchase_price, w.user_id, w.created_at, w.updated_at, w.is_lifetime, 
                       w.vendor, w.warranty_type, w.warranty_duration_years, w.warranty_duration_months, w.warranty_duration_days, w.product_photo_path,
                       u.username, u.email, u.first_name, u.last_name
                FROM warranties w
                JOIN users u ON w.user_id = u.id
                ORDER BY u.username, CASE WHEN w.is_lifetime THEN 1 ELSE 0 END, w.expiration_date NULLS LAST, w.product_name
            ''')
                
            warranties = cur.fetchall()
            columns = [desc[0] for desc in cur.description]
            warranties_list = []
            
            for row in warranties:
                warranty_dict = dict(zip(columns, row))
                # Convert date objects to ISO format strings for JSON serialization
                for key, value in warranty_dict.items():
                    if isinstance(value, (datetime, date)):
                        warranty_dict[key] = value.isoformat()
                    # Convert Decimal objects to float for JSON serialization
                    elif isinstance(value, Decimal):
                        warranty_dict[key] = float(value)
                
                # Get serial numbers for this warranty
                warranty_id = warranty_dict['id']
                cur.execute('SELECT serial_number FROM serial_numbers WHERE warranty_id = %s', (warranty_id,))
                serial_numbers = [row[0] for row in cur.fetchall()]
                warranty_dict['serial_numbers'] = serial_numbers
                
                # Get tags for this warranty
                cur.execute('''
                    SELECT t.id, t.name, t.color
                    FROM tags t
                    JOIN warranty_tags wt ON t.id = wt.tag_id
                    WHERE wt.warranty_id = %s
                    ORDER BY t.name
                ''', (warranty_id,))
                tags = [{'id': t[0], 'name': t[1], 'color': t[2]} for t in cur.fetchall()]
                warranty_dict['tags'] = tags
                
                # Add user display name for better UI
                first_name = warranty_dict.get('first_name', '').strip() if warranty_dict.get('first_name') else ''
                last_name = warranty_dict.get('last_name', '').strip() if warranty_dict.get('last_name') else ''
                username = warranty_dict.get('username', '').strip() if warranty_dict.get('username') else ''
                
                if first_name and last_name:
                    warranty_dict['user_display_name'] = f"{first_name} {last_name}"
                elif first_name:
                    warranty_dict['user_display_name'] = first_name
                elif username:
                    warranty_dict['user_display_name'] = username
                else:
                    warranty_dict['user_display_name'] = 'Unknown User'
                
                warranties_list.append(warranty_dict)
                
            return jsonify(warranties_list)
    except Exception as e:
        logger.error(f"Error retrieving all warranties: {e}")
        return jsonify({"error": "Failed to retrieve all warranties"}), 500
    finally:
        if conn:
            release_db_connection(conn)

@app.route('/api/warranties/global', methods=['GET'])
@token_required
def get_global_warranties():
    """Get all warranties from all users (public view for all authenticated users)"""
    conn = None
    try:
        # Check if global view is enabled for this user
        user_is_admin = request.user.get('is_admin', False)
        
        conn = get_db_connection()
        with conn.cursor() as cur:
            # Get both global view settings
            cur.execute("SELECT key, value FROM site_settings WHERE key IN ('global_view_enabled', 'global_view_admin_only')")
            settings = {row[0]: row[1] for row in cur.fetchall()}
            
            # Check if global view is enabled at all
            global_view_enabled = settings.get('global_view_enabled', 'true').lower() == 'true'
            if not global_view_enabled:
                return jsonify({"error": "Global view is disabled by administrator"}), 403
            
            # Check if global view is restricted to admins only
            admin_only = settings.get('global_view_admin_only', 'false').lower() == 'true'
            if admin_only and not user_is_admin:
                return jsonify({"error": "Global view is restricted to administrators only"}), 403
        
        # Release the connection since we'll get a new one below
        release_db_connection(conn)
        conn = None
        conn = get_db_connection()
        with conn.cursor() as cur:
            # Get all warranties from all users with user information
            cur.execute('''
                SELECT w.id, w.product_name, w.purchase_date, w.expiration_date, w.invoice_path, w.manual_path, w.other_document_path, 
                       w.product_url, w.notes, w.purchase_price, w.user_id, w.created_at, w.updated_at, w.is_lifetime, 
                       w.vendor, w.warranty_type, w.warranty_duration_years, w.warranty_duration_months, w.warranty_duration_days, w.product_photo_path,
                       u.username, u.email, u.first_name, u.last_name
                FROM warranties w
                JOIN users u ON w.user_id = u.id
                ORDER BY u.username, CASE WHEN w.is_lifetime THEN 1 ELSE 0 END, w.expiration_date NULLS LAST, w.product_name
            ''')
                
            warranties = cur.fetchall()
            columns = [desc[0] for desc in cur.description]
            warranties_list = []
            
            for row in warranties:
                warranty_dict = dict(zip(columns, row))
                # Convert date objects to ISO format strings for JSON serialization
                for key, value in warranty_dict.items():
                    if isinstance(value, (datetime, date)):
                        warranty_dict[key] = value.isoformat()
                    # Convert Decimal objects to float for JSON serialization
                    elif isinstance(value, Decimal):
                        warranty_dict[key] = float(value)
                
                # Get serial numbers for this warranty
                warranty_id = warranty_dict['id']
                cur.execute('SELECT serial_number FROM serial_numbers WHERE warranty_id = %s', (warranty_id,))
                serial_numbers = [row[0] for row in cur.fetchall()]
                warranty_dict['serial_numbers'] = serial_numbers
                
                # Get tags for this warranty
                cur.execute('''
                    SELECT t.id, t.name, t.color
                    FROM tags t
                    JOIN warranty_tags wt ON t.id = wt.tag_id
                    WHERE wt.warranty_id = %s
                    ORDER BY t.name
                ''', (warranty_id,))
                tags = [{'id': t[0], 'name': t[1], 'color': t[2]} for t in cur.fetchall()]
                warranty_dict['tags'] = tags
                
                # Add user display name for better UI
                first_name = warranty_dict.get('first_name', '').strip() if warranty_dict.get('first_name') else ''
                last_name = warranty_dict.get('last_name', '').strip() if warranty_dict.get('last_name') else ''
                username = warranty_dict.get('username', '').strip() if warranty_dict.get('username') else ''
                
                if first_name and last_name:
                    warranty_dict['user_display_name'] = f"{first_name} {last_name}"
                elif first_name:
                    warranty_dict['user_display_name'] = first_name
                elif username:
                    warranty_dict['user_display_name'] = username
                else:
                    warranty_dict['user_display_name'] = 'Unknown User'
                
                warranties_list.append(warranty_dict)
                
            return jsonify(warranties_list)
    except Exception as e:
        logger.error(f"Error retrieving global warranties: {e}")
        return jsonify({"error": "Failed to retrieve global warranties"}), 500
    finally:
        if conn:
            release_db_connection(conn)

# Register Blueprints
try:
    # Try Docker environment path first
    from backend.oidc_handler import oidc_bp
except ImportError:
    # Fallback to development path
    from oidc_handler import oidc_bp

app.register_blueprint(oidc_bp, url_prefix='/api')

# Note: Scheduler is already set up earlier in the file with 2-minute intervals
# The main scheduler setup is around line 3642-3655 with precise user-timezone timing
# This duplicate scheduler setup has been removed to prevent conflicts
