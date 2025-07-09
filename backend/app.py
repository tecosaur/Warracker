from flask import Flask, request, jsonify, send_from_directory, session, redirect, url_for, Response
from werkzeug.middleware.proxy_fix import ProxyFix
try:
    # Try relative import for Docker environment
    from backend.extensions import oauth
    from backend.db_handler import init_db_pool, get_db_connection, release_db_connection
    # Import the NEW auth_utils instead of having helpers in app.py
    from backend.auth_utils import generate_token, decode_token, token_required, admin_required, is_valid_email, is_valid_password
    # Import Paperless-ngx handler
    from backend.paperless_handler import get_paperless_handler
except ImportError:
    # Fallback to direct import for development
    from extensions import oauth
    from db_handler import init_db_pool, get_db_connection, release_db_connection
    from auth_utils import generate_token, decode_token, token_required, admin_required, is_valid_email, is_valid_password
    # Import Paperless-ngx handler
    from paperless_handler import get_paperless_handler
import psycopg2 # Added import
import psycopg2.errors
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
import requests

# Configure logging FIRST - before any other initialization
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import localization
try:
    from backend.localization import init_babel, get_current_language, set_language, _, _n, _l
except ImportError:
    from localization import init_babel, get_current_language, set_language, _, _n, _l

app = Flask(__name__)

# Configure Flask to trust forwarded headers from reverse proxy (Nginx)
# This middleware makes the app aware of being behind a proxy
# It reads X-Forwarded-Proto (for https) and other headers
app.wsgi_app = ProxyFix(
    app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1
)

# Initialize localization
try:
    babel = init_babel(app)
    logger.info("Localization initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize localization: {e}")
    babel = None

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

# Logger already configured at top of file

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

# Initialize database connection pool via db_handler
try:
    init_db_pool()
    logger.info("Database connection pool initialized successfully.")
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

# Database environment variables for admin connections only
DB_HOST = os.environ.get('DB_HOST', 'warrackerdb')
DB_NAME = os.environ.get('DB_NAME', 'warranty_db')
DB_ADMIN_USER = os.environ.get('DB_ADMIN_USER', 'warracker_admin')
DB_ADMIN_PASSWORD = os.environ.get('DB_ADMIN_PASSWORD', 'change_this_password_in_production')

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

# Initialize OIDC client after DB handler is ready
with app.app_context():
    init_oidc_client(app, get_db_connection, release_db_connection)

def init_db():
    """Initialize the database with required tables"""
    # Database table creation is now handled by migration files in backend/migrations/
    # This function is kept for compatibility but does not perform any operations
    try:
        conn = get_db_connection()
        if conn:
            conn.commit()
        
        # Ensure owner role is properly set (backup to migration)
        ensure_owner_exists()
        
        logger.info("Database initialization completed - using migration system")
    except Exception as e:
        logger.error(f"Database initialization error: {str(e)}")
    finally:
        if conn:
            release_db_connection(conn)

def ensure_owner_exists():
    """
    Ensure that an application owner exists. This is a backup mechanism
    in case the migration failed. Runs automatically on app startup.
    """
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # First check if the is_owner column exists (handles migration timing issue)
            try:
                cur.execute("""
                    SELECT column_name FROM information_schema.columns 
                    WHERE table_name = 'users' AND column_name = 'is_owner'
                """)
                column_exists = cur.fetchone() is not None
                
                if not column_exists:
                    logger.info("is_owner column not yet created, skipping owner check (migrations may still be running)")
                    return
                
                # Check if any owner exists
                cur.execute("SELECT COUNT(*) FROM users WHERE is_owner = TRUE")
                owner_count = cur.fetchone()[0]
            except psycopg2.errors.UndefinedColumn:
                logger.info("is_owner column not yet created, skipping owner check (migrations may still be running)")
                return
            
            if owner_count == 0:
                logger.info("No application owner found, attempting to promote first user...")
                
                # Find the first user using multiple strategies
                first_user_id = None
                
                # Strategy 1: First user by created_at
                try:
                    cur.execute("""
                        SELECT id FROM users 
                        WHERE created_at IS NOT NULL 
                        ORDER BY created_at ASC, id ASC 
                        LIMIT 1
                    """)
                    result = cur.fetchone()
                    if result:
                        first_user_id = result[0]
                except Exception as e:
                    logger.warning(f"Strategy 1 (created_at) failed: {e}")
                
                # Strategy 2: First user by ID if Strategy 1 failed
                if first_user_id is None:
                    try:
                        cur.execute("SELECT id FROM users ORDER BY id ASC LIMIT 1")
                        result = cur.fetchone()
                        if result:
                            first_user_id = result[0]
                    except Exception as e:
                        logger.warning(f"Strategy 2 (lowest ID) failed: {e}")
                
                # Strategy 3: First admin user if other strategies failed
                if first_user_id is None:
                    try:
                        cur.execute("SELECT id FROM users WHERE is_admin = TRUE ORDER BY id ASC LIMIT 1")
                        result = cur.fetchone()
                        if result:
                            first_user_id = result[0]
                    except Exception as e:
                        logger.warning(f"Strategy 3 (first admin) failed: {e}")
                
                # Promote the user to owner if found
                if first_user_id is not None:
                    try:
                        cur.execute("UPDATE users SET is_owner = TRUE WHERE id = %s", (first_user_id,))
                        conn.commit()
                        logger.info(f"✅ Automatically promoted user ID {first_user_id} to application owner")
                        
                        # Log user info for confirmation
                        cur.execute("SELECT username, email FROM users WHERE id = %s", (first_user_id,))
                        user_info = cur.fetchone()
                        if user_info:
                            logger.info(f"Owner is now: {user_info[0]} ({user_info[1]})")
                    except Exception as e:
                        logger.error(f"Failed to promote user {first_user_id} to owner: {e}")
                        conn.rollback()
                else:
                    logger.warning("No users found in system. First registered user will become owner.")
            else:
                # Log current owner for confirmation
                cur.execute("SELECT id, username, email FROM users WHERE is_owner = TRUE")
                owners = cur.fetchall()
                logger.info(f"Application owner(s) confirmed: {[f'{o[1]} (ID:{o[0]})' for o in owners]}")
                
    except Exception as e:
        logger.error(f"Error in ensure_owner_exists: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            release_db_connection(conn)


# Helper functions


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



# Authentication helper functions moved to auth_utils.py

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

# OIDC functionality is handled by the oidc_bp Blueprint in backend/oidc_handler.py

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
                       warranty_duration_years, warranty_duration_months, warranty_duration_days, product_photo_path, currency,
                       paperless_invoice_id, paperless_manual_id, paperless_photo_id, paperless_other_id
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
        
        # Handle currency (optional, defaults to USD)
        currency = request.form.get('currency', 'USD')
        # Validate currency code
        valid_currencies = [
            'USD', 'EUR', 'GBP', 'JPY', 'CNY', 'INR', 'KRW', 'CHF', 'CAD', 'AUD',
            'SEK', 'NOK', 'DKK', 'PLN', 'CZK', 'HUF', 'BGN', 'RON', 'HRK', 'RUB',
            'BRL', 'MXN', 'ARS', 'CLP', 'COP', 'PEN', 'VES', 'ZAR', 'EGP', 'NGN',
            'KES', 'GHS', 'MAD', 'TND', 'AED', 'SAR', 'QAR', 'KWD', 'BHD', 'OMR',
            'JOD', 'LBP', 'ILS', 'TRY', 'IRR', 'PKR', 'BDT', 'LKR', 'NPR', 'BTN',
            'MMK', 'THB', 'VND', 'LAK', 'KHR', 'MYR', 'SGD', 'IDR', 'PHP', 'TWD',
            'HKD', 'MOP', 'KPW', 'MNT', 'KZT', 'UZS', 'TJS', 'KGS', 'TMT', 'AFN',
            'AMD', 'AZN', 'GEL', 'MDL', 'UAH', 'BYN', 'RSD', 'MKD', 'ALL', 'BAM',
            'ISK', 'FJD', 'PGK', 'SBD', 'TOP', 'VUV', 'WST', 'XPF', 'NZD'
        ]
        if currency not in valid_currencies:
            return jsonify({"error": f"Invalid currency code: {currency}"}), 400
        
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
        
        # Handle Paperless-ngx document IDs if provided (check before file uploads)
        paperless_invoice_id = request.form.get('paperless_invoice_id')
        paperless_manual_id = request.form.get('paperless_manual_id')
        paperless_photo_id = request.form.get('paperless_photo_id')
        paperless_other_id = request.form.get('paperless_other_id')
        
        # Convert empty strings to None for database insertion
        paperless_invoice_id = int(paperless_invoice_id) if paperless_invoice_id and paperless_invoice_id.strip() else None
        paperless_manual_id = int(paperless_manual_id) if paperless_manual_id and paperless_manual_id.strip() else None
        paperless_photo_id = int(paperless_photo_id) if paperless_photo_id and paperless_photo_id.strip() else None
        paperless_other_id = int(paperless_other_id) if paperless_other_id and paperless_other_id.strip() else None

        # Handle invoice file upload (only if not stored in Paperless-ngx)
        db_invoice_path = None
        if not paperless_invoice_id and 'invoice' in request.files:
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
        elif paperless_invoice_id:
            logger.info(f"Invoice stored in Paperless-ngx with ID: {paperless_invoice_id}")
        
        # Handle manual file upload (only if not stored in Paperless-ngx)
        db_manual_path = None
        if not paperless_manual_id and 'manual' in request.files:
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
        elif paperless_manual_id:
            logger.info(f"Manual stored in Paperless-ngx with ID: {paperless_manual_id}")
        
        # Handle other_document file upload (only if not stored in Paperless-ngx)
        db_other_document_path = None
        if not paperless_other_id and 'other_document' in request.files:
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
        elif paperless_other_id:
            logger.info(f"Other document stored in Paperless-ngx with ID: {paperless_other_id}")

        # Handle product photo file upload (only if not stored in Paperless-ngx)
        db_product_photo_path = None
        if not paperless_photo_id and 'product_photo' in request.files:
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
        elif paperless_photo_id:
            logger.info(f"Product photo stored in Paperless-ngx with ID: {paperless_photo_id}")



        # Save to database
        conn = get_db_connection()
        with conn.cursor() as cur:
            # Insert warranty
            cur.execute('''
                INSERT INTO warranties (
                    product_name, purchase_date, expiration_date, 
                    invoice_path, manual_path, other_document_path, product_url, purchase_price, user_id, is_lifetime, notes, vendor, warranty_type,
                    warranty_duration_years, warranty_duration_months, warranty_duration_days, product_photo_path, currency,
                    paperless_invoice_id, paperless_manual_id, paperless_photo_id, paperless_other_id
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            ''', (
                product_name, purchase_date, expiration_date,
                db_invoice_path, db_manual_path, db_other_document_path, product_url, purchase_price, user_id, is_lifetime, notes, vendor, warranty_type,
                warranty_duration_years, warranty_duration_months, warranty_duration_days, db_product_photo_path, currency,
                paperless_invoice_id, paperless_manual_id, paperless_photo_id, paperless_other_id
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
            
            # Handle currency (optional, defaults to USD)
            currency = request.form.get('currency', 'USD')
            # Validate currency code
            valid_currencies = [
                'USD', 'EUR', 'GBP', 'JPY', 'CNY', 'INR', 'KRW', 'CHF', 'CAD', 'AUD',
                'SEK', 'NOK', 'DKK', 'PLN', 'CZK', 'HUF', 'BGN', 'RON', 'HRK', 'RUB',
                'BRL', 'MXN', 'ARS', 'CLP', 'COP', 'PEN', 'VES', 'ZAR', 'EGP', 'NGN',
                'KES', 'GHS', 'MAD', 'TND', 'AED', 'SAR', 'QAR', 'KWD', 'BHD', 'OMR',
                'JOD', 'LBP', 'ILS', 'TRY', 'IRR', 'PKR', 'BDT', 'LKR', 'NPR', 'BTN',
                'MMK', 'THB', 'VND', 'LAK', 'KHR', 'MYR', 'SGD', 'IDR', 'PHP', 'TWD',
                'HKD', 'MOP', 'KPW', 'MNT', 'KZT', 'UZS', 'TJS', 'KGS', 'TMT', 'AFN',
                'AMD', 'AZN', 'GEL', 'MDL', 'UAH', 'BYN', 'RSD', 'MKD', 'ALL', 'BAM',
                'ISK', 'FJD', 'PGK', 'SBD', 'TOP', 'VUV', 'WST', 'XPF', 'NZD'
            ]
            if currency not in valid_currencies:
                return jsonify({"error": f"Invalid currency code: {currency}"}), 400

            # Handle Paperless-ngx document IDs
            paperless_invoice_id = request.form.get('paperless_invoice_id')
            paperless_manual_id = request.form.get('paperless_manual_id')
            paperless_photo_id = request.form.get('paperless_photo_id')
            paperless_other_id = request.form.get('paperless_other_id')

            logger.info(f"[UPDATE] Received Paperless IDs: invoice={paperless_invoice_id}, manual={paperless_manual_id}, photo={paperless_photo_id}, other={paperless_other_id}")

            # Convert to integers if provided, otherwise None
            paperless_invoice_id = int(paperless_invoice_id) if paperless_invoice_id and paperless_invoice_id.strip() else None
            paperless_manual_id = int(paperless_manual_id) if paperless_manual_id and paperless_manual_id.strip() else None
            paperless_photo_id = int(paperless_photo_id) if paperless_photo_id and paperless_photo_id.strip() else None
            paperless_other_id = int(paperless_other_id) if paperless_other_id and paperless_other_id.strip() else None

            logger.info(f"[UPDATE] Converted Paperless IDs: invoice={paperless_invoice_id}, manual={paperless_manual_id}, photo={paperless_photo_id}, other={paperless_other_id}")
            db_invoice_path = None
            if not paperless_invoice_id and 'invoice' in request.files:
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
            elif paperless_invoice_id:
                logger.info(f"Invoice updated to Paperless-ngx with ID: {paperless_invoice_id}")
                # Clear local path when storing in Paperless-ngx
                cur.execute('SELECT invoice_path FROM warranties WHERE id = %s', (warranty_id,))
                old_invoice_path = cur.fetchone()[0]
                if old_invoice_path:
                    full_path = os.path.join('/data', old_invoice_path)
                    if os.path.exists(full_path):
                        try:
                            os.remove(full_path)
                            logger.info(f"Deleted old local invoice (moving to Paperless): {full_path}")
                        except Exception as e:
                            logger.error(f"Error deleting old local invoice: {e}")
                db_invoice_path = None  # Clear local path
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
            if not paperless_manual_id and 'manual' in request.files:
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
            elif paperless_manual_id:
                logger.info(f"Manual updated to Paperless-ngx with ID: {paperless_manual_id}")
                # Clear local path when storing in Paperless-ngx
                cur.execute('SELECT manual_path FROM warranties WHERE id = %s', (warranty_id,))
                old_manual_path = cur.fetchone()[0]
                if old_manual_path:
                    full_path = os.path.join('/data', old_manual_path)
                    if os.path.exists(full_path):
                        try:
                            os.remove(full_path)
                            logger.info(f"Deleted old local manual (moving to Paperless): {full_path}")
                        except Exception as e:
                            logger.error(f"Error deleting old local manual: {e}")
                db_manual_path = None  # Clear local path
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
            if not paperless_other_id and 'other_document' in request.files:
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
            elif paperless_other_id:
                logger.info(f"Other document updated to Paperless-ngx with ID: {paperless_other_id}")
                # Clear local path when storing in Paperless-ngx
                cur.execute('SELECT other_document_path FROM warranties WHERE id = %s', (warranty_id,))
                old_other_document_path = cur.fetchone()[0]
                if old_other_document_path:
                    full_path = os.path.join('/data', old_other_document_path)
                    if os.path.exists(full_path):
                        try:
                            os.remove(full_path)
                            logger.info(f"Deleted old local other_document (moving to Paperless): {full_path}")
                        except Exception as e:
                            logger.error(f"Error deleting old local other_document: {e}")
                db_other_document_path = None  # Clear local path
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

            # Handle product photo file upload (only if not stored in Paperless-ngx)
            db_product_photo_path = None
            if not paperless_photo_id and 'product_photo' in request.files:
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
            elif paperless_photo_id:
                logger.info(f"Product photo updated to Paperless-ngx with ID: {paperless_photo_id}")
                # Clear local path when storing in Paperless-ngx
                cur.execute('SELECT product_photo_path FROM warranties WHERE id = %s', (warranty_id,))
                old_product_photo_path = cur.fetchone()[0]
                if old_product_photo_path:
                    full_path = os.path.join('/data', old_product_photo_path)
                    if os.path.exists(full_path):
                        try:
                            os.remove(full_path)
                            logger.info(f"Deleted old local product_photo (moving to Paperless): {full_path}")
                        except Exception as e:
                            logger.error(f"Error deleting old local product_photo: {e}")
                db_product_photo_path = None  # Clear local path
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
                'warranty_type': warranty_type,
                'currency': currency
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
                sql_fields.append("paperless_invoice_id = NULL")  # Also clear Paperless ID
            if db_manual_path is not None:
                sql_fields.append("manual_path = %s")
                sql_values.append(db_manual_path)
            elif 'delete_manual' in request.form and request.form.get('delete_manual', 'false').lower() == 'true':
                sql_fields.append("manual_path = NULL")
                sql_fields.append("paperless_manual_id = NULL")  # Also clear Paperless ID
            if db_other_document_path is not None:
                sql_fields.append("other_document_path = %s")
                sql_values.append(db_other_document_path)
            elif 'delete_other_document' in request.form and request.form.get('delete_other_document', 'false').lower() == 'true':
                sql_fields.append("other_document_path = NULL")
                sql_fields.append("paperless_other_id = NULL")  # Also clear Paperless ID
            if db_product_photo_path is not None:
                sql_fields.append("product_photo_path = %s")
                sql_values.append(db_product_photo_path)
            elif 'delete_product_photo' in request.form and request.form.get('delete_product_photo', 'false').lower() == 'true':
                sql_fields.append("product_photo_path = NULL")
                sql_fields.append("paperless_photo_id = NULL")  # Also clear Paperless ID

            # Handle Paperless-ngx document IDs
            if paperless_invoice_id is not None:
                sql_fields.append("paperless_invoice_id = %s")
                sql_values.append(paperless_invoice_id)
            if paperless_manual_id is not None:
                sql_fields.append("paperless_manual_id = %s")
                sql_values.append(paperless_manual_id)
            if paperless_photo_id is not None:
                sql_fields.append("paperless_photo_id = %s")
                sql_values.append(paperless_photo_id)
            if paperless_other_id is not None:
                sql_fields.append("paperless_other_id = %s")
                sql_values.append(paperless_other_id)

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

# Admin User Management Endpoints

@app.route('/api/admin/users', methods=['GET'])
@admin_required
def get_all_users():
    """Get all users (admin only)"""
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # Try to get users with is_owner column, fall back to without it if column doesn't exist
            try:
                cur.execute('''
                    SELECT id, username, email, first_name, last_name, is_active, is_admin, is_owner, created_at, last_login 
                    FROM users 
                    ORDER BY created_at DESC
                ''')
                users = cur.fetchall()
                has_owner_column = True
            except Exception as e:
                # If the query fails (likely because is_owner column doesn't exist), rollback and try again
                logger.warning(f"Failed to query with is_owner column in get_all_users, falling back: {e}")
                conn.rollback()  # Rollback the failed transaction
                cur.execute('''
                    SELECT id, username, email, first_name, last_name, is_active, is_admin, created_at, last_login 
                    FROM users 
                    ORDER BY created_at DESC
                ''')
                users = cur.fetchall()
                has_owner_column = False
                
            columns = [desc[0] for desc in cur.description]
            users_list = []
            
            for row in users:
                user_dict = dict(zip(columns, row))
                
                # Add is_owner field if it wasn't included in the query
                if not has_owner_column:
                    user_dict['is_owner'] = False
                
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
            # Check if user exists and if they are the owner
            try:
                cur.execute('SELECT id, is_owner FROM users WHERE id = %s', (user_id,))
                user = cur.fetchone()
                is_owner = user[1] if user and len(user) > 1 else False
            except Exception as e:
                # If the query fails (likely because is_owner column doesn't exist), rollback and try again
                logger.warning(f"Failed to query with is_owner column in update_user, falling back: {e}")
                conn.rollback()  # Rollback the failed transaction
                cur.execute('SELECT id FROM users WHERE id = %s', (user_id,))
                user = cur.fetchone()
                is_owner = False
            
            if not user:
                return jsonify({"message": "User not found"}), 404
            
            # Check if the user being updated is the owner
            if is_owner:
                # If the user is the owner, prevent demotion or deactivation
                if 'is_admin' in data and data['is_admin'] is False:
                    return jsonify({"message": "The application owner cannot be demoted from admin status."}), 403
                if 'is_active' in data and data['is_active'] is False:
                    return jsonify({"message": "The application owner's account cannot be deactivated."}), 403
            
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
            # Check if user exists and if they are the owner
            try:
                cur.execute('SELECT id, username, is_owner FROM users WHERE id = %s', (user_id,))
                user = cur.fetchone()
                is_owner = user[2] if user and len(user) > 2 else False
            except Exception as e:
                # If the query fails (likely because is_owner column doesn't exist), rollback and try again
                logger.warning(f"Failed to query with is_owner column in delete_user, falling back: {e}")
                conn.rollback()  # Rollback the failed transaction
                cur.execute('SELECT id, username FROM users WHERE id = %s', (user_id,))
                user = cur.fetchone()
                is_owner = False
            
            if not user:
                logger.warning(f"User with ID {user_id} not found")
                return jsonify({"message": "User not found"}), 404
            
            # Check if the user to be deleted is the owner
            if is_owner:
                logger.warning(f"Admin {request.user['id']} attempted to delete the application owner (user_id: {user_id})")
                return jsonify({"message": "The application owner cannot be deleted."}), 403
            
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

@app.route('/api/admin/transfer-ownership', methods=['POST'])
@admin_required
def transfer_ownership():
    """Transfer application ownership to another admin user (owner only)"""
    # 1. Security Check: Only the current owner can initiate a transfer.
    # If is_owner column doesn't exist yet, this feature is not available
    if not request.user.get('is_owner'):
        return jsonify({"message": "Ownership transfer feature is not available. Please run the database migration first."}), 403

    data = request.get_json()
    new_owner_id = data.get('new_owner_id')
    current_owner_id = request.user['id']

    if not new_owner_id:
        return jsonify({"message": "New owner ID is required."}), 400

    if int(new_owner_id) == current_owner_id:
        return jsonify({"message": "Cannot transfer ownership to yourself."}), 400

    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # 2. Validate the new owner
            cur.execute("SELECT id, is_admin, is_active FROM users WHERE id = %s", (new_owner_id,))
            new_owner = cur.fetchone()

            if not new_owner:
                return jsonify({"message": "The selected user does not exist."}), 404
            
            if not new_owner[1]: # is_admin is false
                 return jsonify({"message": "Ownership can only be transferred to another admin user."}), 400

            if not new_owner[2]: # is_active is false
                return jsonify({"message": "Cannot transfer ownership to an inactive user."}), 400

            # 3. Perform the transfer within a database transaction
            # This ensures both updates succeed or both fail.
            logger.info(f"Ownership transfer initiated by user {current_owner_id} to user {new_owner_id}.")
            
            # Demote current owner to a regular admin
            try:
                cur.execute("UPDATE users SET is_owner = FALSE WHERE id = %s", (current_owner_id,))
                
                # Promote the new user to be the owner (and ensure they remain admin)
                cur.execute("UPDATE users SET is_owner = TRUE, is_admin = TRUE WHERE id = %s", (new_owner_id,))
            except Exception as e:
                logger.error(f"Error updating ownership in database: {e}")
                return jsonify({"message": "Ownership transfer feature is not available. Please run the database migration first."}), 500
            
            conn.commit()
            
            logger.info(f"Ownership successfully transferred from {current_owner_id} to {new_owner_id}.")
            return jsonify({"message": "Ownership transferred successfully."}), 200

    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Error during ownership transfer: {e}")
        return jsonify({"message": "An error occurred during ownership transfer. The operation has been rolled back."}), 500
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
                'oidc_only_mode': 'false',  # Force OIDC-only login (hide traditional login form)
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
                'apprise_title_prefix': '[Warracker]',
                # Paperless-ngx integration settings
                'paperless_enabled': 'false',
                'paperless_url': '',
                # 'paperless_api_token': '', # Not returned directly
            }

            settings_to_return = {}
            needs_commit = False

            # First, add all existing settings from the database
            for key, value in raw_settings.items():
                # Skip returning sensitive secrets directly
                if key in ['oidc_client_secret', 'paperless_api_token']:
                    continue
                
                # For boolean-like string settings, ensure they are 'true' or 'false'
                if key in ['registration_enabled', 'oidc_enabled', 'oidc_only_mode', 'apprise_enabled', 'global_view_enabled', 'global_view_admin_only', 'paperless_enabled']:
                    settings_to_return[key] = 'true' if value.lower() == 'true' else 'false'
                else:
                    settings_to_return[key] = value

            # Then, add defaults for any missing settings
            for key, default_value in default_site_settings.items():
                if key not in settings_to_return and key not in ['oidc_client_secret', 'paperless_api_token']:
                    settings_to_return[key] = default_value
                    # Insert default if missing (except for secrets)
                    cur.execute(
                        'INSERT INTO site_settings (key, value) VALUES (%s, %s) ON CONFLICT (key) DO NOTHING',
                        (key, default_value)
                    )
                    needs_commit = True
            
            # Indicate if secrets are set without revealing them
            settings_to_return['oidc_client_secret_set'] = bool(raw_settings.get('oidc_client_secret'))
            settings_to_return['paperless_api_token_set'] = bool(raw_settings.get('paperless_api_token'))

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
                if key in ['registration_enabled', 'oidc_enabled', 'oidc_only_mode', 'global_view_enabled', 'global_view_admin_only', 'paperless_enabled']:
                    value = 'true' if str(value).lower() == 'true' else 'false'
                
                # Check if it's an OIDC related key that requires restart
                if key.startswith('oidc_'):
                    requires_restart = True
                
                # For sensitive secrets, only update if a non-empty value is provided
                # An empty string could mean "clear" or "no change" - admin UI should clarify
                # For now, if key is a secret and value is empty, we skip update to avoid accidental clearing.
                # The admin UI should send a specific placeholder if they intend to clear it, or not send the key.
                if key in ['oidc_client_secret', 'paperless_api_token'] and not value: # If an empty secret is passed, don't update
                    logger.info(f"Skipping update for {key} as value is empty.")
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
    """Enhanced secure file serving with authorization checks and Paperless-ngx integration."""
    conn = None
    try:
        # Check if this is a Paperless-ngx document ID request (paperless-{id})
        if filename.startswith('paperless-'):
            try:
                paperless_id = int(filename.replace('paperless-', ''))
                return serve_paperless_document(paperless_id)
            except ValueError:
                logger.warning(f"[SECURE_FILE] Invalid Paperless-ngx document ID format: {filename}")
                return jsonify({"message": "Invalid Paperless document ID"}), 400
        
        # Original local file serving logic
        logger.info(f"[SECURE_FILE] Raw filename from route: '{filename}' (len: {len(filename)})")
        logger.info(f"[SECURE_FILE] repr(filename): {repr(filename)}")

        # Security check for path traversal
        if '..' in filename or filename.startswith('/'):
            logger.warning(f"[SECURE_FILE] Potential path traversal attempt detected: {filename} by user {request.user['id']}")
            return jsonify({"message": "Invalid file path"}), 400

        conn = get_db_connection()
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

            # Check for ownership authorization
            if not authorized and results:
                for warranty_id_db, warranty_user_id_db in results:
                    logger.info(f"[SECURE_FILE] Checking ownership: warranty_id={warranty_id_db}, owner_id={warranty_user_id_db}, current_user_id={user_id}")
                    if warranty_user_id_db == user_id:
                        authorized = True
                        logger.info(f"[SECURE_FILE] Ownership confirmed for warranty_id={warranty_id_db}")
                        break

            # Check for global view authorization for product photos
            if not authorized and results:
                # Check if this file is a product photo by looking at which column matched
                cur.execute("""
                    SELECT w.id, w.user_id
                    FROM warranties w
                    WHERE w.product_photo_path = %s
                """, (db_search_path,))
                photo_results = cur.fetchall()
                
                if photo_results:
                    logger.info(f"[SECURE_FILE] File is a product photo, checking global view permissions")
                    
                    # Get global view settings
                    cur.execute("SELECT key, value FROM site_settings WHERE key IN ('global_view_enabled', 'global_view_admin_only')")
                    settings = {row[0]: row[1] for row in cur.fetchall()}
                    
                    # Check if global view is enabled at all
                    global_view_enabled = settings.get('global_view_enabled', 'true').lower() == 'true'
                    logger.info(f"[SECURE_FILE] Global view enabled: {global_view_enabled}")
                    
                    if global_view_enabled:
                        # Check if global view is restricted to admins only
                        admin_only = settings.get('global_view_admin_only', 'false').lower() == 'true'
                        logger.info(f"[SECURE_FILE] Global view admin only: {admin_only}")
                        
                        if not admin_only or is_admin:
                            authorized = True
                            logger.info(f"[SECURE_FILE] Global view photo access authorized for user {user_id}")
                        else:
                            logger.info(f"[SECURE_FILE] Global view restricted to admins only, user {user_id} is not admin")
            
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
                
    except Exception as e:
        logger.error(f"[SECURE_FILE] Error in secure file access for '{filename}' (repr: {repr(filename)}): {e}", exc_info=True)
        return jsonify({"message": "Error accessing file"}), 500
    finally:
        if conn:
            release_db_connection(conn)


@app.route('/api/paperless-file/<int:paperless_id>', methods=['GET'])
@token_required
def serve_paperless_document(paperless_id: int):
    """Serve a document from Paperless-ngx"""
    conn = None
    try:
        user_id = request.user['id']
        is_admin = request.user.get('is_admin', False)
        
        # Get database connection
        conn = get_db_connection()
        
        # Find warranty that has this Paperless document ID
        with conn.cursor() as cur:
            cur.execute("""
                SELECT w.id, w.user_id
                FROM warranties w
                WHERE w.paperless_invoice_id = %s OR w.paperless_manual_id = %s 
                   OR w.paperless_photo_id = %s OR w.paperless_other_id = %s
            """, (paperless_id, paperless_id, paperless_id, paperless_id))
            
            results = cur.fetchall()
            
            if not results:
                logger.warning(f"[PAPERLESS_FILE] No warranty found with Paperless document ID {paperless_id}")
                return jsonify({"message": "Document not found"}), 404
            
            # Check authorization
            authorized = is_admin
            if not authorized:
                for warranty_id_db, warranty_user_id_db in results:
                    if warranty_user_id_db == user_id:
                        authorized = True
                        break
            
            # Check global view for photos
            if not authorized:
                cur.execute("""
                    SELECT w.id, w.user_id
                    FROM warranties w
                    WHERE w.paperless_photo_id = %s
                """, (paperless_id,))
                photo_results = cur.fetchall()
                
                if photo_results:
                    # Get global view settings
                    cur.execute("SELECT key, value FROM site_settings WHERE key IN ('global_view_enabled', 'global_view_admin_only')")
                    settings = {row[0]: row[1] for row in cur.fetchall()}
                    
                    global_view_enabled = settings.get('global_view_enabled', 'true').lower() == 'true'
                    admin_only = settings.get('global_view_admin_only', 'false').lower() == 'true'
                    
                    if global_view_enabled and (not admin_only or is_admin):
                        authorized = True
            
            if not authorized:
                logger.warning(f"[PAPERLESS_FILE] Unauthorized access to Paperless document {paperless_id} by user {user_id}")
                return jsonify({"message": "You are not authorized to access this document"}), 403
        
        # Get Paperless handler and retrieve document
        paperless_handler = get_paperless_handler(conn)
        if not paperless_handler:
            return jsonify({"message": "Paperless-ngx integration not available"}), 503
        
        # Get document from Paperless-ngx
        success, content, message, content_type = paperless_handler.get_document_preview(paperless_id)
        
        if not success:
            logger.error(f"[PAPERLESS_FILE] Failed to retrieve document {paperless_id}: {message}")
            return jsonify({"message": message}), 404
        
        # Stream the document content
        def generate():
            chunk_size = 4096
            total_sent = 0
            remaining = len(content)
            
            while remaining > 0:
                chunk_size_actual = min(chunk_size, remaining)
                chunk = content[total_sent:total_sent + chunk_size_actual]
                total_sent += chunk_size_actual
                remaining -= chunk_size_actual
                yield chunk
        
        # Return streaming response
        response = Response(
            generate(),
            mimetype=content_type or 'application/octet-stream',
            headers={
                'Content-Length': str(len(content)),
                'Content-Disposition': f'inline; filename="paperless_document_{paperless_id}"',
                'Cache-Control': 'no-cache, no-store, must-revalidate',
                'Pragma': 'no-cache',
                'Expires': '0',
                'X-Content-Type-Options': 'nosniff'
            }
        )
        
        logger.info(f"[PAPERLESS_FILE] Successfully served Paperless document {paperless_id} to user {user_id}")
        return response
        
    except Exception as e:
        logger.error(f"[PAPERLESS_FILE] Error serving Paperless document {paperless_id}: {e}")
        return jsonify({"message": "Error retrieving document"}), 500
    finally:
        if conn:
            release_db_connection(conn)





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

# Always ensure owner exists regardless of how the app is started (dev vs production)
try:
    logger.info("Ensuring application owner exists on startup...")
    ensure_owner_exists()
except Exception as e:
    logger.error(f"Error ensuring owner exists during startup: {e}")

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

@app.route('/api/currencies', methods=['GET'])
def get_currencies():
    """Get list of available currencies with their symbols"""
    try:
        currencies = [
            {'code': 'USD', 'name': 'US Dollar', 'symbol': '$'},
            {'code': 'EUR', 'name': 'Euro', 'symbol': '€'},
            {'code': 'GBP', 'name': 'British Pound', 'symbol': '£'},
            {'code': 'JPY', 'name': 'Japanese Yen', 'symbol': '¥'},
            {'code': 'CNY', 'name': 'Chinese Yuan', 'symbol': '¥'},
            {'code': 'INR', 'name': 'Indian Rupee', 'symbol': '₹'},
            {'code': 'KRW', 'name': 'South Korean Won', 'symbol': '₩'},
            {'code': 'CHF', 'name': 'Swiss Franc', 'symbol': 'CHF'},
            {'code': 'CAD', 'name': 'Canadian Dollar', 'symbol': 'C$'},
            {'code': 'AUD', 'name': 'Australian Dollar', 'symbol': 'A$'},
            {'code': 'SEK', 'name': 'Swedish Krona', 'symbol': 'kr'},
            {'code': 'NOK', 'name': 'Norwegian Krone', 'symbol': 'kr'},
            {'code': 'DKK', 'name': 'Danish Krone', 'symbol': 'kr'},
            {'code': 'PLN', 'name': 'Polish Złoty', 'symbol': 'zł'},
            {'code': 'CZK', 'name': 'Czech Koruna', 'symbol': 'Kč'},
            {'code': 'HUF', 'name': 'Hungarian Forint', 'symbol': 'Ft'},
            {'code': 'BGN', 'name': 'Bulgarian Lev', 'symbol': 'лв'},
            {'code': 'RON', 'name': 'Romanian Leu', 'symbol': 'lei'},
            {'code': 'HRK', 'name': 'Croatian Kuna', 'symbol': 'kn'},
            {'code': 'RUB', 'name': 'Russian Ruble', 'symbol': '₽'},
            {'code': 'BRL', 'name': 'Brazilian Real', 'symbol': 'R$'},
            {'code': 'MXN', 'name': 'Mexican Peso', 'symbol': '$'},
            {'code': 'ARS', 'name': 'Argentine Peso', 'symbol': '$'},
            {'code': 'CLP', 'name': 'Chilean Peso', 'symbol': '$'},
            {'code': 'COP', 'name': 'Colombian Peso', 'symbol': '$'},
            {'code': 'PEN', 'name': 'Peruvian Sol', 'symbol': 'S/'},
            {'code': 'VES', 'name': 'Venezuelan Bolívar', 'symbol': 'Bs'},
            {'code': 'ZAR', 'name': 'South African Rand', 'symbol': 'R'},
            {'code': 'EGP', 'name': 'Egyptian Pound', 'symbol': '£'},
            {'code': 'NGN', 'name': 'Nigerian Naira', 'symbol': '₦'},
            {'code': 'KES', 'name': 'Kenyan Shilling', 'symbol': 'KSh'},
            {'code': 'GHS', 'name': 'Ghanaian Cedi', 'symbol': '₵'},
            {'code': 'MAD', 'name': 'Moroccan Dirham', 'symbol': 'DH'},
            {'code': 'TND', 'name': 'Tunisian Dinar', 'symbol': 'DT'},
            {'code': 'AED', 'name': 'UAE Dirham', 'symbol': 'AED'},
            {'code': 'SAR', 'name': 'Saudi Riyal', 'symbol': 'SR'},
            {'code': 'QAR', 'name': 'Qatari Riyal', 'symbol': 'QR'},
            {'code': 'KWD', 'name': 'Kuwaiti Dinar', 'symbol': 'KD'},
            {'code': 'BHD', 'name': 'Bahraini Dinar', 'symbol': 'BD'},
            {'code': 'OMR', 'name': 'Omani Rial', 'symbol': 'OR'},
            {'code': 'JOD', 'name': 'Jordanian Dinar', 'symbol': 'JD'},
            {'code': 'LBP', 'name': 'Lebanese Pound', 'symbol': 'LL'},
            {'code': 'ILS', 'name': 'Israeli Shekel', 'symbol': '₪'},
            {'code': 'TRY', 'name': 'Turkish Lira', 'symbol': '₺'},
            {'code': 'IRR', 'name': 'Iranian Rial', 'symbol': '﷼'},
            {'code': 'PKR', 'name': 'Pakistani Rupee', 'symbol': '₨'},
            {'code': 'BDT', 'name': 'Bangladeshi Taka', 'symbol': '৳'},
            {'code': 'LKR', 'name': 'Sri Lankan Rupee', 'symbol': 'Rs'},
            {'code': 'NPR', 'name': 'Nepalese Rupee', 'symbol': 'Rs'},
            {'code': 'BTN', 'name': 'Bhutanese Ngultrum', 'symbol': 'Nu'},
            {'code': 'MMK', 'name': 'Myanmar Kyat', 'symbol': 'K'},
            {'code': 'THB', 'name': 'Thai Baht', 'symbol': '฿'},
            {'code': 'VND', 'name': 'Vietnamese Dong', 'symbol': '₫'},
            {'code': 'LAK', 'name': 'Lao Kip', 'symbol': '₭'},
            {'code': 'KHR', 'name': 'Cambodian Riel', 'symbol': '៛'},
            {'code': 'MYR', 'name': 'Malaysian Ringgit', 'symbol': 'RM'},
            {'code': 'SGD', 'name': 'Singapore Dollar', 'symbol': 'S$'},
            {'code': 'IDR', 'name': 'Indonesian Rupiah', 'symbol': 'Rp'},
            {'code': 'PHP', 'name': 'Philippine Peso', 'symbol': '₱'},
            {'code': 'TWD', 'name': 'Taiwan Dollar', 'symbol': 'NT$'},
            {'code': 'HKD', 'name': 'Hong Kong Dollar', 'symbol': 'HK$'},
            {'code': 'MOP', 'name': 'Macanese Pataca', 'symbol': 'MOP'},
            {'code': 'KPW', 'name': 'North Korean Won', 'symbol': '₩'},
            {'code': 'MNT', 'name': 'Mongolian Tugrik', 'symbol': '₮'},
            {'code': 'KZT', 'name': 'Kazakhstani Tenge', 'symbol': '₸'},
            {'code': 'UZS', 'name': 'Uzbekistani Som', 'symbol': 'soʻm'},
            {'code': 'TJS', 'name': 'Tajikistani Somoni', 'symbol': 'SM'},
            {'code': 'KGS', 'name': 'Kyrgyzstani Som', 'symbol': 'с'},
            {'code': 'TMT', 'name': 'Turkmenistani Manat', 'symbol': 'T'},
            {'code': 'AFN', 'name': 'Afghan Afghani', 'symbol': '؋'},
            {'code': 'AMD', 'name': 'Armenian Dram', 'symbol': '֏'},
            {'code': 'AZN', 'name': 'Azerbaijani Manat', 'symbol': '₼'},
            {'code': 'GEL', 'name': 'Georgian Lari', 'symbol': '₾'},
            {'code': 'MDL', 'name': 'Moldovan Leu', 'symbol': 'L'},
            {'code': 'UAH', 'name': 'Ukrainian Hryvnia', 'symbol': '₴'},
            {'code': 'BYN', 'name': 'Belarusian Ruble', 'symbol': 'Br'},
            {'code': 'RSD', 'name': 'Serbian Dinar', 'symbol': 'дин'},
            {'code': 'MKD', 'name': 'Macedonian Denar', 'symbol': 'ден'},
            {'code': 'ALL', 'name': 'Albanian Lek', 'symbol': 'L'},
            {'code': 'BAM', 'name': 'Bosnia-Herzegovina Mark', 'symbol': 'KM'},
            {'code': 'ISK', 'name': 'Icelandic Króna', 'symbol': 'kr'},
            {'code': 'FJD', 'name': 'Fijian Dollar', 'symbol': 'FJ$'},
            {'code': 'PGK', 'name': 'Papua New Guinea Kina', 'symbol': 'K'},
            {'code': 'SBD', 'name': 'Solomon Islands Dollar', 'symbol': 'SI$'},
            {'code': 'TOP', 'name': 'Tongan Paʻanga', 'symbol': 'T$'},
            {'code': 'VUV', 'name': 'Vanuatu Vatu', 'symbol': 'VT'},
            {'code': 'WST', 'name': 'Samoan Tala', 'symbol': 'WS$'},
            {'code': 'XPF', 'name': 'CFP Franc', 'symbol': '₣'},
            {'code': 'NZD', 'name': 'New Zealand Dollar', 'symbol': 'NZ$'}
        ]
        
        return jsonify(currencies)
        
    except Exception as e:
        logger.error(f"Error getting currencies: {e}")
        return jsonify([{'code': 'USD', 'name': 'US Dollar', 'symbol': '$'}]), 500

@app.route('/api/debug/export', methods=['GET'])
@token_required
def debug_export():
    """Debug endpoint to help troubleshoot export issues"""
    conn = None
    try:
        user_id = request.user['id']
        is_admin = request.user.get('is_admin', False)
        
        conn = get_db_connection()
        with conn.cursor() as cur:
            # Get basic warranty count
            cur.execute('SELECT COUNT(*) FROM warranties WHERE user_id = %s', (user_id,))
            personal_count = cur.fetchone()[0]
            
            # Get all warranty IDs for this user
            cur.execute('SELECT id, product_name, is_lifetime, expiration_date FROM warranties WHERE user_id = %s ORDER BY id', (user_id,))
            personal_warranties = cur.fetchall()
            
            # Get global count if admin
            global_count = 0
            global_warranties = []
            if is_admin:
                cur.execute('SELECT COUNT(*) FROM warranties')
                global_count = cur.fetchone()[0]
                
                cur.execute('SELECT id, product_name, is_lifetime, expiration_date, user_id FROM warranties ORDER BY id')
                global_warranties = cur.fetchall()
            
            # Get tag associations
            cur.execute('''
                SELECT w.id, t.id as tag_id, t.name as tag_name
                FROM warranties w
                LEFT JOIN warranty_tags wt ON w.id = wt.warranty_id
                LEFT JOIN tags t ON wt.tag_id = t.id
                WHERE w.user_id = %s
                ORDER BY w.id, t.name
            ''', (user_id,))
            tag_associations = cur.fetchall()
            
            # Get serial number associations
            cur.execute('''
                SELECT w.id, sn.serial_number
                FROM warranties w
                LEFT JOIN serial_numbers sn ON w.id = sn.warranty_id
                WHERE w.user_id = %s
                ORDER BY w.id
            ''', (user_id,))
            serial_associations = cur.fetchall()
            
            return jsonify({
                'user_id': user_id,
                'is_admin': is_admin,
                'personal_warranty_count': personal_count,
                'global_warranty_count': global_count,
                'personal_warranties': [
                    {
                        'id': w[0],
                        'product_name': w[1],
                        'is_lifetime': w[2],
                        'expiration_date': w[3].isoformat() if w[3] else None
                    } for w in personal_warranties
                ],
                'global_warranties': [
                    {
                        'id': w[0],
                        'product_name': w[1],
                        'is_lifetime': w[2],
                        'expiration_date': w[3].isoformat() if w[3] else None,
                        'user_id': w[4]
                    } for w in global_warranties
                ] if is_admin else [],
                'tag_associations': [
                    {
                        'warranty_id': t[0],
                        'tag_id': t[1],
                        'tag_name': t[2]
                    } for t in tag_associations if t[1] is not None
                ],
                'serial_associations': [
                    {
                        'warranty_id': s[0],
                        'serial_number': s[1]
                    } for s in serial_associations if s[1] is not None
                ]
            })
            
    except Exception as e:
        logger.error(f"Error in debug export endpoint: {e}")
        return jsonify({"error": f"Debug failed: {str(e)}"}), 500
    finally:
        if conn:
            release_db_connection(conn)

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

                    # --- Get user's preferred currency code ---
                    user_currency_code = 'USD'  # Default fallback
                    try:
                        # Get user's preferred currency symbol from their preferences
                        cur.execute("""
                            SELECT currency_symbol FROM user_preferences 
                            WHERE user_id = %s
                        """, (user_id,))
                        currency_result = cur.fetchone()
                        
                        if currency_result and currency_result[0]:
                            user_symbol = currency_result[0]
                            # Map common currency symbols to currency codes (same as frontend logic)
                            symbol_to_currency_map = {
                                '$': 'USD', '€': 'EUR', '£': 'GBP', '¥': 'JPY', '₹': 'INR', '₩': 'KRW',
                                'CHF': 'CHF', 'C$': 'CAD', 'A$': 'AUD', 'kr': 'SEK', 'zł': 'PLN', 
                                'Kč': 'CZK', 'Ft': 'HUF', '₽': 'RUB', 'R$': 'BRL', '₦': 'NGN',
                                '₪': 'ILS', '₺': 'TRY', '₨': 'PKR', '৳': 'BDT', '฿': 'THB',
                                '₫': 'VND', 'RM': 'MYR', 'S$': 'SGD', 'Rp': 'IDR', '₱': 'PHP',
                                'NT$': 'TWD', 'HK$': 'HKD', '₮': 'MNT', '₸': 'KZT', '₼': 'AZN',
                                '₾': 'GEL', '₴': 'UAH', 'NZ$': 'NZD'
                            }
                            
                            if user_symbol in symbol_to_currency_map:
                                user_currency_code = symbol_to_currency_map[user_symbol]
                                logger.info(f"[Import] Using user's preferred currency: {user_symbol} -> {user_currency_code} for user {user_id}")
                            else:
                                logger.info(f"[Import] Unknown currency symbol '{user_symbol}' for user {user_id}, defaulting to USD")
                        else:
                            logger.info(f"[Import] No currency preference found for user {user_id}, defaulting to USD")
                    except Exception as currency_err:
                        logger.error(f"[Import] Error getting user currency preference: {currency_err}, defaulting to USD")

                    # --- Insert into Database --- 
                    cur.execute("""
                        INSERT INTO warranties (
                            product_name, purchase_date, expiration_date, 
                            product_url, purchase_price, user_id, is_lifetime, vendor, warranty_type,
                            warranty_duration_years, warranty_duration_months, warranty_duration_days, currency
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        RETURNING id
                    """, (
                        product_name, purchase_date, expiration_date,
                        product_url, purchase_price, user_id, is_lifetime, vendor, warranty_type,
                        warranty_duration_years, warranty_duration_months, warranty_duration_days, user_currency_code
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

@app.route('/api/settings/oidc-status', methods=['GET'])
def get_oidc_status():
    """Public endpoint to check if OIDC is enabled and if OIDC-only mode is active."""
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # Get both OIDC enabled and OIDC-only mode settings
            cur.execute("SELECT key, value FROM site_settings WHERE key IN ('oidc_enabled', 'oidc_only_mode')")
            settings = {row[0]: row[1] for row in cur.fetchall()}
            
            oidc_enabled = False
            if settings.get('oidc_enabled') and settings['oidc_enabled'].lower() == 'true':
                oidc_enabled = True
            
            # Also check app.config as a fallback, though DB should be primary
            if not settings.get('oidc_enabled') and app.config.get('OIDC_ENABLED'):
                 oidc_enabled = True
            
            oidc_only_mode = False
            if settings.get('oidc_only_mode') and settings['oidc_only_mode'].lower() == 'true':
                oidc_only_mode = True

            return jsonify({
                'oidc_enabled': oidc_enabled,
                'oidc_only_mode': oidc_only_mode
            }), 200
    except Exception as e:
        logger.error(f"Error fetching OIDC status: {e}")
        # Fallback to app.config or default to false if DB error
        return jsonify({
            'oidc_enabled': app.config.get('OIDC_ENABLED', False),
            'oidc_only_mode': False
        }), 200
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
    """Manually trigger Apprise expiration notifications with warranty scope filtering"""
    if not APPRISE_AVAILABLE or apprise_handler is None:
        return jsonify({'success': False, 'message': 'Apprise notifications are not available'}), 503
    
    try:
        # Get warranty scope setting to determine which warranties to include
        conn = None
        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                cur.execute("SELECT value FROM site_settings WHERE key = 'apprise_warranty_scope'")
                result = cur.fetchone()
                warranty_scope = result[0] if result else 'all'
        except Exception as e:
            logger.error(f"Error fetching warranty scope setting: {e}")
            warranty_scope = 'all'  # Default fallback
        finally:
            if conn:
                release_db_connection(conn)
        
        # Get eligible user IDs based on warranty scope
        eligible_user_ids = None  # None means all users
        
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
                eligible_user_ids = [admin_user_id]
                logger.info(f"Warranty scope 'admin': Limiting notifications to admin user ID {admin_user_id}")
            else:
                logger.warning("Warranty scope 'admin' requested but no admin user found, including all users")
        
        logger.info(f"Triggering Apprise notifications with warranty scope: '{warranty_scope}', eligible users: {eligible_user_ids}")
        
        # Send notifications with user filtering
        results = apprise_handler.send_expiration_notifications(eligible_user_ids=eligible_user_ids)
        
        return jsonify({
            'success': True,
            'message': f'Notifications processed: {results["sent"]} sent, {results["errors"]} errors',
            'results': results,
            'warranty_scope': warranty_scope
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
                       w.vendor, w.warranty_type, w.warranty_duration_years, w.warranty_duration_months, w.warranty_duration_days, w.product_photo_path, w.currency,
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
                       w.vendor, w.warranty_type, w.warranty_duration_years, w.warranty_duration_months, w.warranty_duration_days, w.product_photo_path, w.currency,
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
    from backend.auth_routes import auth_bp
except ImportError:
    # Fallback to development path
    from oidc_handler import oidc_bp
    from auth_routes import auth_bp

app.register_blueprint(oidc_bp, url_prefix='/api')
app.register_blueprint(auth_bp, url_prefix='/api/auth')

# Note: Scheduler is already set up earlier in the file with 2-minute intervals
# The main scheduler setup is around line 3642-3655 with precise user-timezone timing
# This duplicate scheduler setup has been removed to prevent conflicts

@app.route('/api/admin/fix-owner-role', methods=['POST'])
@admin_required  
def fix_owner_role():
    """Temporary endpoint to manually fix owner role - can be removed after fix"""
    try:
        ensure_owner_exists()
        return jsonify({'success': True, 'message': 'Owner role fix attempted. Check logs for results.'}), 200
    except Exception as e:
        logger.error(f"Error in fix_owner_role endpoint: {e}")
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

# ============================
# Paperless-ngx Integration Routes
# ============================

@app.route('/api/paperless/upload', methods=['POST'])
@token_required
def paperless_upload():
    """
    Proxy endpoint to upload files to Paperless-ngx
    """
    conn = None
    try:
        logger.info("Paperless upload endpoint called")
        
        # Get Paperless handler
        conn = get_db_connection()
        logger.info("Database connection acquired")
        
        paperless_handler = get_paperless_handler(conn)
        logger.info(f"Paperless handler: {paperless_handler is not None}")
        
        if not paperless_handler:
            logger.warning("Paperless handler is None - integration not configured")
            return jsonify({"error": "Paperless-ngx integration is not enabled or configured"}), 400
        
        # Validate file upload
        logger.info(f"Request files keys: {list(request.files.keys())}")
        if 'file' not in request.files:
            logger.warning("No 'file' key in request.files")
            return jsonify({"error": "No file provided"}), 400
        
        uploaded_file = request.files['file']
        logger.info(f"Uploaded file: filename='{uploaded_file.filename}', content_type='{uploaded_file.content_type}'")
        
        if uploaded_file.filename == '':
            logger.warning("Empty filename")
            return jsonify({"error": "No file selected"}), 400
        
        # Validate file type
        if not allowed_file(uploaded_file.filename):
            logger.warning(f"File type not allowed: {uploaded_file.filename}")
            return jsonify({"error": "File type not allowed"}), 400
        
        # Get additional metadata
        title = request.form.get('title', uploaded_file.filename)
        document_type = request.form.get('document_type', 'warranty_document')
        logger.info(f"Upload metadata: title='{title}', document_type='{document_type}'")
        
        # Add Warracker-specific tags
        tags = ['warracker', document_type]
        if request.form.get('warranty_id'):
            tags.append(f"warranty_{request.form.get('warranty_id')}")
        logger.info(f"Upload tags: {tags}")
        
        # Read file content
        try:
            file_content = uploaded_file.read()
            logger.info(f"File content read successfully: {len(file_content)} bytes")
        except Exception as file_read_error:
            logger.error(f"Error reading file content: {file_read_error}")
            return jsonify({"error": f"Error reading file: {str(file_read_error)}"}), 400
        
        # Upload to Paperless-ngx
        logger.info("Starting upload to Paperless-ngx")
        try:
            success, document_id, message = paperless_handler.upload_document(
                file_content=file_content,
                filename=uploaded_file.filename,
                title=title,
                tags=tags,
                correspondent="Warracker"
            )
            logger.info(f"Upload result: success={success}, document_id={document_id}, message='{message}'")
        except Exception as upload_error:
            logger.error(f"Error during paperless upload: {upload_error}")
            return jsonify({"error": f"Upload to Paperless-ngx failed: {str(upload_error)}"}), 500
        
        if success:
            logger.info("Upload successful")
            return jsonify({
                "success": True,
                "document_id": document_id,
                "message": message
            }), 200
        else:
            logger.warning(f"Upload failed: {message}")
            return jsonify({
                "success": False,
                "error": message
            }), 500
        
    except Exception as e:
        logger.error(f"Error in Paperless upload proxy: {e}", exc_info=True)
        return jsonify({"error": f"Upload failed: {str(e)}"}), 500
    finally:
        if conn:
            release_db_connection(conn)

@app.route('/api/paperless/test', methods=['POST'])
@admin_required
def test_paperless_connection():
    """
    Test connection to Paperless-ngx instance
    """
    conn = None
    try:
        conn = get_db_connection()
        paperless_handler = get_paperless_handler(conn)
        
        if not paperless_handler:
            return jsonify({"error": "Paperless-ngx integration is not enabled or configured"}), 400
        
        success, message = paperless_handler.test_connection()
        
        if success:
            return jsonify({
                "success": True,
                "message": message
            }), 200
        else:
            return jsonify({
                "success": False,
                "error": message
            }), 400
        
    except Exception as e:
        logger.error(f"Error testing Paperless connection: {e}")
        return jsonify({"error": "Connection test failed"}), 500
    finally:
        if conn:
            release_db_connection(conn)

@app.route('/api/paperless/search', methods=['GET'])
@token_required
def paperless_search():
    """
    Search documents in Paperless-ngx
    """
    conn = None
    try:
        conn = get_db_connection()
        paperless_handler = get_paperless_handler(conn)
        
        if not paperless_handler:
            return jsonify({'success': False, 'message': 'Paperless-ngx not configured'}), 400
        
        # Get query parameters
        ordering = request.args.get('ordering', '-created')
        created_gte = request.args.get('created__gte')
        search_query = request.args.get('query', '')
        
        # Get pagination parameters (support both old and new formats)
        limit = request.args.get('limit', request.args.get('page_size', '25'))
        offset = request.args.get('offset', '0')
        page = request.args.get('page', '1')
        
        # Calculate page from offset if needed
        try:
            limit_int = int(limit)
            offset_int = int(offset)
            if offset_int > 0:
                page = str((offset_int // limit_int) + 1)
        except (ValueError, ZeroDivisionError):
            page = '1'
            limit = '25'
        
        # Build search URL using paperless handler's configuration
        search_url = f"{paperless_handler.base_url.rstrip('/')}/api/documents/"
        params = {
            'ordering': ordering,
            'page_size': limit,
            'page': page
        }
        
        if created_gte:
            # Convert ISO format to Paperless-ngx expected format
            # Remove 'Z' and use format that Paperless-ngx accepts
            try:
                from datetime import datetime, timezone
                # Parse the ISO format and convert to YYYY-MM-DD format
                dt = datetime.fromisoformat(created_gte.replace('Z', '+00:00'))
                # Use date only format for better compatibility
                params['created__gte'] = dt.strftime('%Y-%m-%d')
                logger.info(f"Converted date filter from {created_gte} to {params['created__gte']}")
            except Exception as date_error:
                logger.warning(f"Could not parse date {created_gte}: {date_error}")
                # Fallback: use today's date
                from datetime import datetime
                params['created__gte'] = datetime.now().strftime('%Y-%m-%d')
        if search_query:
            params['query'] = search_query
            
        # Add document type filter
        document_type = request.args.get('document_type', '')
        if document_type:
            params['document_type'] = document_type
            
        # Add tag filter
        tags_filter = request.args.get('tags__id__in', '')
        if tags_filter:
            params['tags__id__in'] = tags_filter
            
        logger.info(f"Searching Paperless documents with params: {params}")
        
        # Make request to Paperless-ngx using the session from paperless handler
        response = paperless_handler.session.get(
            search_url,
            params=params,
            timeout=30
        )
        
        response.raise_for_status()
        search_result = response.json()
        
        logger.info(f"Paperless search returned {len(search_result.get('results', []))} documents")
        
        return jsonify(search_result)
        
    except Exception as e:
        logger.error(f"Error searching Paperless documents: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        if conn:
            release_db_connection(conn)

@app.route('/api/paperless/tags', methods=['GET'])
@token_required
def paperless_tags():
    """
    Get tags from Paperless-ngx
    """
    conn = None
    try:
        conn = get_db_connection()
        paperless_handler = get_paperless_handler(conn)
        
        if not paperless_handler:
            return jsonify({'success': False, 'message': 'Paperless-ngx integration not available'}), 400
        
        # Make request to Paperless-ngx tags endpoint
        response = paperless_handler.session.get(
            f"{paperless_handler.paperless_url}/api/tags/",
            timeout=30
        )
        
        response.raise_for_status()
        tags_result = response.json()
        
        logger.info(f"Paperless tags returned {len(tags_result.get('results', []))} tags")
        
        return jsonify(tags_result)
        
    except Exception as e:
        logger.error(f"Error fetching Paperless tags: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        if conn:
            release_db_connection(conn)

@app.route('/api/paperless/debug', methods=['GET'])
@token_required
def paperless_debug():
    """
    Debug endpoint to test Paperless-ngx configuration
    """
    conn = None
    try:
        conn = get_db_connection()
        
        # Check database settings
        with conn.cursor() as cur:
            cur.execute("""
                SELECT key, value FROM site_settings 
                WHERE key IN ('paperless_enabled', 'paperless_url', 'paperless_api_token')
            """)
            settings = {row[0]: row[1] for row in cur.fetchall()}
        
        debug_info = {
            "paperless_enabled": settings.get('paperless_enabled', 'false'),
            "paperless_url": settings.get('paperless_url', ''),
            "paperless_api_token_set": bool(settings.get('paperless_api_token', '').strip()),
            "paperless_handler_available": False,
            "test_connection_result": None
        }
        
        # Try to get paperless handler
        try:
            paperless_handler = get_paperless_handler(conn)
            debug_info["paperless_handler_available"] = paperless_handler is not None
            
            if paperless_handler:
                # Test connection
                try:
                    success, message = paperless_handler.test_connection()
                    debug_info["test_connection_result"] = {
                        "success": success,
                        "message": message
                    }
                except Exception as test_error:
                    debug_info["test_connection_result"] = {
                        "success": False,
                        "error": str(test_error)
                    }
        except Exception as handler_error:
            debug_info["paperless_handler_error"] = str(handler_error)
        
        return jsonify(debug_info), 200
        
    except Exception as e:
        logger.error(f"Error in Paperless debug: {e}")
        return jsonify({"error": f"Debug failed: {str(e)}"}), 500
    finally:
        if conn:
            release_db_connection(conn)

@app.route('/api/paperless/test-upload', methods=['POST'])
@token_required
def test_file_upload():
    """
    Test file upload mechanism without Paperless-ngx
    """
    try:
        logger.info("Test upload endpoint called")
        logger.info(f"Request files keys: {list(request.files.keys())}")
        logger.info(f"Request form keys: {list(request.form.keys())}")
        
        if 'file' not in request.files:
            return jsonify({"error": "No file provided"}), 400
        
        uploaded_file = request.files['file']
        logger.info(f"File: {uploaded_file.filename}, size: {uploaded_file.content_length}, type: {uploaded_file.content_type}")
        
        # Read file content to test
        file_content = uploaded_file.read()
        logger.info(f"Successfully read {len(file_content)} bytes")
        
        return jsonify({
            "success": True,
            "message": "File upload test successful",
            "file_info": {
                "filename": uploaded_file.filename,
                "size": len(file_content),
                "content_type": uploaded_file.content_type
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Test upload error: {e}", exc_info=True)
        return jsonify({"error": f"Test upload failed: {str(e)}"}), 500

@app.route('/api/paperless/debug-document/<int:document_id>', methods=['GET'])
@token_required
def paperless_debug_document(document_id: int):
    """
    Debug endpoint to check status of a specific Paperless-ngx document
    """
    conn = None
    try:
        conn = get_db_connection()
        paperless_handler = get_paperless_handler(conn)
        
        if not paperless_handler:
            return jsonify({"error": "Paperless-ngx integration not available"}), 400
        
        # Get debug information about the document
        debug_info = paperless_handler.debug_document_status(document_id)
        
        # Also check if this document ID exists in our database
        with conn.cursor() as cur:
            cur.execute("""
                SELECT w.id, w.product_name, w.user_id,
                       CASE 
                           WHEN w.paperless_invoice_id = %s THEN 'invoice'
                           WHEN w.paperless_manual_id = %s THEN 'manual'
                           WHEN w.paperless_photo_id = %s THEN 'photo'
                           WHEN w.paperless_other_id = %s THEN 'other'
                           ELSE 'unknown'
                       END as document_type
                FROM warranties w
                WHERE w.paperless_invoice_id = %s OR w.paperless_manual_id = %s 
                   OR w.paperless_photo_id = %s OR w.paperless_other_id = %s
            """, (document_id, document_id, document_id, document_id, 
                  document_id, document_id, document_id, document_id))
            
            db_results = cur.fetchall()
            debug_info['database_references'] = [
                {
                    'warranty_id': row[0],
                    'product_name': row[1],
                    'user_id': row[2],
                    'document_type': row[3]
                }
                for row in db_results
            ]
        
        return jsonify(debug_info), 200
        
    except Exception as e:
        logger.error(f"Error in Paperless document debug: {e}")
        return jsonify({"error": f"Debug failed: {str(e)}"}), 500
    finally:
        if conn:
            release_db_connection(conn)

@app.route('/api/paperless/cleanup-invalid', methods=['POST'])
@token_required
def cleanup_invalid_paperless_documents():
    """
    Clean up invalid Paperless-ngx document references from the database
    """
    conn = None
    try:
        user_id = request.user['id']
        is_admin = request.user.get('is_admin', False)
        
        conn = get_db_connection()
        paperless_handler = get_paperless_handler(conn)
        
        if not paperless_handler:
            return jsonify({"error": "Paperless-ngx integration not available"}), 400
        
        cleanup_results = {
            'checked': 0,
            'invalid_found': 0,
            'cleaned_up': 0,
            'errors': []
        }
        
        with conn.cursor() as cur:
            # Get all Paperless document IDs for this user (or all if admin)
            if is_admin:
                cur.execute("""
                    SELECT id, product_name, paperless_invoice_id, paperless_manual_id, 
                           paperless_photo_id, paperless_other_id
                    FROM warranties 
                    WHERE paperless_invoice_id IS NOT NULL 
                       OR paperless_manual_id IS NOT NULL 
                       OR paperless_photo_id IS NOT NULL 
                       OR paperless_other_id IS NOT NULL
                """)
            else:
                cur.execute("""
                    SELECT id, product_name, paperless_invoice_id, paperless_manual_id, 
                           paperless_photo_id, paperless_other_id
                    FROM warranties 
                    WHERE user_id = %s 
                      AND (paperless_invoice_id IS NOT NULL 
                           OR paperless_manual_id IS NOT NULL 
                           OR paperless_photo_id IS NOT NULL 
                           OR paperless_other_id IS NOT NULL)
                """, (user_id,))
            
            warranties = cur.fetchall()
            
            for warranty in warranties:
                warranty_id, product_name, invoice_id, manual_id, photo_id, other_id = warranty
                
                # Check each document ID
                document_fields = [
                    ('paperless_invoice_id', invoice_id),
                    ('paperless_manual_id', manual_id),
                    ('paperless_photo_id', photo_id),
                    ('paperless_other_id', other_id)
                ]
                
                for field_name, doc_id in document_fields:
                    if doc_id is not None:
                        cleanup_results['checked'] += 1
                        
                        try:
                            if not paperless_handler.document_exists(doc_id):
                                cleanup_results['invalid_found'] += 1
                                logger.info(f"Found invalid Paperless document ID {doc_id} in warranty {warranty_id} ({product_name})")
                                
                                # Clear the invalid reference
                                cur.execute(f"""
                                    UPDATE warranties 
                                    SET {field_name} = NULL 
                                    WHERE id = %s
                                """, (warranty_id,))
                                
                                cleanup_results['cleaned_up'] += 1
                                logger.info(f"Cleaned up invalid {field_name} reference for warranty {warranty_id}")
                                
                        except Exception as e:
                            error_msg = f"Error checking document {doc_id}: {str(e)}"
                            cleanup_results['errors'].append(error_msg)
                            logger.error(error_msg)
            
            conn.commit()
        
        return jsonify({
            "success": True,
            "message": f"Cleanup complete. Checked {cleanup_results['checked']} documents, found {cleanup_results['invalid_found']} invalid, cleaned up {cleanup_results['cleaned_up']}.",
            "details": cleanup_results
        }), 200
        
    except Exception as e:
        logger.error(f"Error in Paperless cleanup: {e}")
        return jsonify({"error": f"Cleanup failed: {str(e)}"}), 500
    finally:
        if conn:
            release_db_connection(conn)

@app.route('/api/paperless-search-and-link', methods=['POST'])
@token_required
def paperless_search_and_link():
    """Search for a Paperless document by title and link it to a warranty."""

    conn = None  # Single connection for the full request lifecycle
    try:
        logger.info("paperless_search_and_link called by user: %s", request.user)

        data = request.get_json() or {}
        warranty_id = data.get("warranty_id")
        document_type = data.get("document_type")  # 'invoice', 'manual', 'photo', 'other'
        search_title = data.get("search_title")

        logger.info("Search request: warranty_id=%s, document_type=%s, search_title=%s", warranty_id, document_type, search_title)

        if not all([warranty_id, document_type, search_title]):
            return jsonify({"success": False, "message": "Missing required parameters"}), 400

        # Validate document_type
        valid_types = {
            "invoice": "paperless_invoice_id",
            "manual": "paperless_manual_id",
            "photo": "paperless_photo_id",
            "other": "paperless_other_id",
        }

        if document_type not in valid_types:
            return jsonify({"success": False, "message": "Invalid document type"}), 400

        # Get DB connection once and reuse it throughout
        conn = get_db_connection()

        # Obtain Paperless handler (uses same connection to fetch settings)
        paperless_handler = get_paperless_handler(conn)
        if not paperless_handler:
            return jsonify({"success": False, "message": "Paperless-ngx not configured"}), 400

        # Search for the document in Paperless-ngx
        success, document_id, message = paperless_handler.find_document_by_title(search_title)
        logger.info("Paperless search result: success=%s, document_id=%s, message=%s", success, document_id, message)

        if not success or not document_id:
            return jsonify({"success": False, "message": f"Document not found: {message}"}), 404

        # Update warranty with the found document ID
        db_field = valid_types[document_type]

        with conn.cursor() as cursor:
            logger.info(
                "Updating warranty %s field %s with document ID %s for user %s",
                warranty_id,
                db_field,
                document_id,
                request.user["id"],
            )

            cursor.execute(
                f"""
                UPDATE warranties
                SET {db_field} = %s
                WHERE id = %s AND user_id = %s
                """,
                (document_id, warranty_id, request.user["id"]),
            )

            if cursor.rowcount == 0:
                logger.warning("No warranty found with ID %s for user %s", warranty_id, request.user["id"])
                conn.rollback()
                return jsonify({"success": False, "message": "Warranty not found or access denied"}), 404

        conn.commit()

        logger.info("Successfully linked document %s to warranty %s", document_id, warranty_id)

        return jsonify({"success": True, "message": "Document linked successfully", "document_id": document_id})

    except Exception as e:
        logger.error("Error in paperless_search_and_link: %s", e, exc_info=True)
        return jsonify({"success": False, "message": "Internal server error"}), 500
    finally:
        if conn:
            release_db_connection(conn)

@app.route('/api/test-auth', methods=['POST'])
@token_required
def test_auth():
    """Simple test endpoint to verify authentication is working"""
    try:
        logger.info(f"test_auth called by user: {request.user}")
        return jsonify({
            'success': True,
            'user': request.user,
            'message': 'Authentication working'
        })
    except Exception as e:
        logger.error(f"Error in test_auth: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/paperless/url', methods=['GET'])
@token_required
def get_paperless_url():
    """Get the Paperless-ngx base URL for opening documents directly"""
    conn = None
    try:
        conn = get_db_connection()
        paperless_handler = get_paperless_handler(conn)
        
        if not paperless_handler:
            return jsonify({'success': False, 'message': 'Paperless-ngx not configured'}), 400
        
        return jsonify({
            'success': True,
            'url': paperless_handler.base_url
        })
        
    except Exception as e:
        logger.error(f"Error getting Paperless URL: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        if conn:
            release_db_connection(conn)

@app.route('/api/user/language-preference', methods=['PUT'])
@token_required
def save_language_preference():
    """Save user's language preference"""
    conn = None
    try:
        data = request.get_json()
        if not data or 'preferred_language' not in data:
            return jsonify({'error': 'Invalid request'}), 400
        
        language = data['preferred_language']
        
        # Validate language code
        valid_languages = ['en', 'fr', 'es', 'de', 'it', 'cs', 'nl', 'hi', 'fa', 'ar']
        if language not in valid_languages:
            return jsonify({'error': 'Invalid language code'}), 400
        
        # Get current user ID from token
        token_header = request.headers.get('Authorization', '').replace('Bearer ', '')
        try:
            payload = decode_token(token_header)
            user_id = payload['user_id']
        except Exception as e:
            return jsonify({'error': 'Invalid token'}), 401
        
        # Update user's language preference
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE users 
                SET preferred_language = %s 
                WHERE id = %s
            """, (language, user_id))
            conn.commit()
        
        logger.info(f"User {user_id} language preference updated to {language}")
        return jsonify({'message': 'Language preference saved successfully'})
        
    except Exception as e:
        logger.error(f"Error saving language preference: {e}")
        return jsonify({'error': 'Failed to save language preference'}), 500
    finally:
        if conn:
            release_db_connection(conn)

@app.route('/api/locales', methods=['GET'])
def get_supported_locales():
    """Get list of supported locales"""
    locales = {
        'en': 'English',
        'fr': 'Français', 
        'es': 'Español',
        'de': 'Deutsch',
        'it': 'Italiano'
    }
    
    return jsonify({
        'supported_languages': ['en', 'fr', 'es', 'de', 'it'],
        'locales': locales,
        'default': 'en'
    })
