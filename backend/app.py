from flask import Flask, request, jsonify, send_from_directory, session, redirect, url_for
import psycopg2
from psycopg2 import pool
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
from apscheduler.schedulers.background import BackgroundScheduler
import atexit
from pytz import timezone as pytz_timezone
import pytz
import threading
import json

app = Flask(__name__)
CORS(app, supports_credentials=True)  # Enable CORS with credentials
bcrypt = Bcrypt(app)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set a secret key for session and JWT
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev_secret_key_change_in_production')
app.config['JWT_EXPIRATION_DELTA'] = timedelta(days=7)  # Token expiration time

UPLOAD_FOLDER = '/data/uploads'
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}
MAX_CONTENT_LENGTH = 32 * 1024 * 1024  # 32MB max upload

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

# PostgreSQL connection pool
DB_HOST = os.environ.get('DB_HOST', 'warrackerdb')
DB_NAME = os.environ.get('DB_NAME', 'warranty_db')
DB_USER = os.environ.get('DB_USER', 'warranty_user')
DB_PASSWORD = os.environ.get('DB_PASSWORD', 'warranty_password')
DB_ADMIN_USER = os.environ.get('DB_ADMIN_USER', 'warracker_admin')
DB_ADMIN_PASSWORD = os.environ.get('DB_ADMIN_PASSWORD', 'change_this_password_in_production')

# Add connection retry logic
def create_db_pool(max_retries=5, retry_delay=5):
    attempt = 0
    last_exception = None
    
    while attempt < max_retries:
        try:
            logger.info(f"Attempting to connect to database (attempt {attempt+1}/{max_retries})")
            connection_pool = pool.SimpleConnectionPool(
                1, 10,  # min, max connections
                host=DB_HOST,
                database=DB_NAME,
                user=DB_USER,
                password=DB_PASSWORD
            )
            logger.info("Database connection successful")
            return connection_pool
        except Exception as e:
            last_exception = e
            logger.error(f"Database connection error: {e}")
            logger.info(f"Retrying in {retry_delay} seconds...")
            time.sleep(retry_delay)
            attempt += 1
    
    # If we got here, all connection attempts failed
    logger.error(f"Failed to connect to database after {max_retries} attempts")
    raise last_exception

# Create a connection pool with retry logic
try:
    connection_pool = create_db_pool()
except Exception as e:
    logger.error(f"Fatal database connection error: {e}")
    # Allow the app to start even if DB connection fails
    # This lets us serve static files while DB is unavailable
    connection_pool = None

def get_db_connection():
    try:
        if connection_pool is None:
            raise Exception("Database connection pool not initialized")
        return connection_pool.getconn()
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        raise

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

def release_db_connection(conn):
    connection_pool.putconn(conn)

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
        #         file_type VARCHAR(50),
        #         file_size INTEGER,
        #         created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        #     )
        # """)
        
        # Create sequence if it doesn't exist - Handled by migrations
        # cur.execute("""
        #     DO $$
        #     BEGIN
        #         IF NOT EXISTS (SELECT 1 FROM pg_sequences WHERE sequencename = 'warranty_documents_id_seq') THEN
        #             CREATE SEQUENCE warranty_documents_id_seq;
        #         END IF;
        #     END $$;
        # """)
        
        # Alter table to use the sequence - Handled by migrations
        # cur.execute("""
        #     ALTER TABLE warranty_documents
        #     ALTER COLUMN id SET DEFAULT nextval('warranty_documents_id_seq');
        # """)
        
        # We might still need to commit if other operations were performed before the commented blocks
        conn.commit()
        cur.close()
        conn.close()
        logger.info("Database initialized successfully")
        
    except Exception as e:
        logger.error(f"Database initialization error: {str(e)}")
        raise

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
                'INSERT INTO user_sessions (user_id, session_token, expires_at, ip_address, user_agent) VALUES (%s, %s, %s, %s, %s)',
                (user_id, session_token, expires_at, ip_address, user_agent)
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
            # Check if user exists
            cur.execute('SELECT id, username, email, password_hash, is_active FROM users WHERE username = %s OR email = %s', (username, username))
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
                'INSERT INTO user_sessions (user_id, session_token, expires_at, ip_address, user_agent) VALUES (%s, %s, %s, %s, %s)',
                (user_id, session_token, expires_at, ip_address, user_agent)
            )
            
            conn.commit()
            
            return jsonify({
                'message': 'Login successful!',
                'token': token,
                'user': {
                    'id': user_id,
                    'username': user[1],
                    'email': user[2]
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
    try:
        user = request.user
        return jsonify({
            'id': user['id'],
            'username': user['username'],
            'email': user['email'],
            'is_admin': user['is_admin']
        }), 200
    except Exception as e:
        logger.error(f"Get user error: {e}")
        return jsonify({'message': 'Failed to retrieve user information!'}), 500

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
            
            # In a real application, you would send an email with the reset link
            # For now, we'll just return the token in the response (for testing purposes)
            reset_link = f"/reset-password?token={reset_token}"
            
            logger.info(f"Password reset requested for user {user_id}. Reset link: {reset_link}")
            
            return jsonify({
                'message': 'If your email is registered, you will receive a password reset link.',
                'reset_link': reset_link  # Remove this in production
            }), 200
    except Exception as e:
        logger.error(f"Password reset request error: {e}")
        if conn:
            conn.rollback()
        return jsonify({'message': 'Password reset request failed!'}), 500
    finally:
        if conn:
            release_db_connection(conn)

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
    conn = None
    try:
        data = request.get_json()
        
        if not data.get('current_password') or not data.get('new_password'):
            return jsonify({'message': 'Current password and new password are required!'}), 400
        
        current_password = data['current_password']
        new_password = data['new_password']
        
        # Validate password strength
        if not is_valid_password(new_password):
            return jsonify({'message': 'Password must be at least 8 characters and include uppercase, lowercase, and numbers!'}), 400
        
        user_id = request.user['id']
        
        conn = get_db_connection()
        with conn.cursor() as cur:
            # Check current password
            cur.execute('SELECT password_hash FROM users WHERE id = %s', (user_id,))
            user = cur.fetchone()
            
            if not user or not bcrypt.check_password_hash(user[0], current_password):
                return jsonify({'message': 'Current password is incorrect!'}), 401
            
            # Hash the new password
            password_hash = bcrypt.generate_password_hash(new_password).decode('utf-8')
            
            # Update user's password
            cur.execute('UPDATE users SET password_hash = %s WHERE id = %s', (password_hash, user_id))
            
            conn.commit()
            
            return jsonify({'message': 'Password changed successfully!'}), 200
    except Exception as e:
        logger.error(f"Password change error: {e}")
        if conn:
            conn.rollback()
        return jsonify({'message': 'Password change failed!'}), 500
    finally:
        if conn:
            release_db_connection(conn)

# Update existing endpoints to use authentication

@app.route('/api/warranties', methods=['GET'])
@token_required
def get_warranties():
    conn = None
    try:
        conn = get_db_connection()
        user_id = request.user['id']
        is_admin = request.user['is_admin']
        
        with conn.cursor() as cur:
            # If admin, can see all warranties, otherwise only user's warranties
            if is_admin:
                cur.execute('SELECT * FROM warranties ORDER BY expiration_date')
            else:
                cur.execute('SELECT * FROM warranties WHERE user_id = %s ORDER BY expiration_date', (user_id,))
                
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
            
        try:
            warranty_years = int(request.form.get('warranty_years', '0'))
            if warranty_years <= 0 or warranty_years > 100:  # Set reasonable limits
                return jsonify({"error": "Warranty years must be between 1 and 100"}), 400
        except ValueError:
            return jsonify({"error": "Warranty years must be a valid number"}), 400
            
        # Process the data
        product_name = request.form['product_name']
        purchase_date_str = request.form['purchase_date']
        serial_numbers = request.form.getlist('serial_numbers')
        product_url = request.form.get('product_url', '')
        user_id = request.user['id']
        
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
            purchase_date = datetime.strptime(purchase_date_str, '%Y-%m-%d')
        except ValueError:
            return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400
            
        expiration_date = purchase_date + timedelta(days=warranty_years * 365)
        
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
                
                invoice.save(invoice_path)
                db_invoice_path = os.path.join('uploads', filename)
                logger.info(f"New invoice uploaded: {db_invoice_path}")
        
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
                
                manual.save(manual_path)
                db_manual_path = os.path.join('uploads', filename)
                logger.info(f"New manual uploaded: {db_manual_path}")
        
        # Save to database
        conn = get_db_connection()
        with conn.cursor() as cur:
            # Insert warranty
            cur.execute('''
                INSERT INTO warranties (product_name, purchase_date, warranty_years, expiration_date, invoice_path, manual_path, product_url, purchase_price, user_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            ''', (product_name, purchase_date, warranty_years, expiration_date, db_invoice_path, db_manual_path, product_url, purchase_price, user_id))
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
            
            # First get the invoice path to delete the file
            cur.execute('SELECT invoice_path, manual_path FROM warranties WHERE id = %s', (warranty_id,))
            result = cur.fetchone()
            
            invoice_path = result[0]
            manual_path = result[1]
            
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
            
            # Validate input data similar to the add_warranty route
            if not request.form.get('product_name'):
                return jsonify({"error": "Product name is required"}), 400
                
            if not request.form.get('purchase_date'):
                return jsonify({"error": "Purchase date is required"}), 400
                
            try:
                warranty_years = int(request.form.get('warranty_years', '0'))
                if warranty_years <= 0 or warranty_years > 100:
                    return jsonify({"error": "Warranty years must be between 1 and 100"}), 400
            except ValueError:
                return jsonify({"error": "Warranty years must be a valid number"}), 400
                
            # Process the data
            product_name = request.form['product_name']
            purchase_date_str = request.form['purchase_date']
            serial_numbers = request.form.getlist('serial_numbers')
            product_url = request.form.get('product_url', '')
            
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
                purchase_date = datetime.strptime(purchase_date_str, '%Y-%m-%d')
            except ValueError:
                return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400
                
            expiration_date = purchase_date + timedelta(days=warranty_years * 365)
            
            # Handle invoice file upload if new file is provided
            db_invoice_path = None
            if 'invoice' in request.files:
                invoice = request.files['invoice']
                if invoice.filename != '':
                    if not allowed_file(invoice.filename):
                        return jsonify({"error": "File type not allowed. Use PDF, PNG, JPG, or JPEG"}), 400
                        
                    # First check if there's an existing invoice to delete
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
                    
                    # Save new invoice
                    filename = secure_filename(invoice.filename)
                    filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
                    invoice_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    
                    invoice.save(invoice_path)
                    db_invoice_path = os.path.join('uploads', filename)
                    logger.info(f"New invoice uploaded: {db_invoice_path}")
            
            # Handle manual file upload if new file is provided
            db_manual_path = None
            if 'manual' in request.files:
                manual = request.files['manual']
                if manual.filename != '':
                    if not allowed_file(manual.filename):
                        return jsonify({"error": "File type not allowed. Use PDF, PNG, JPG, or JPEG"}), 400
                        
                    # First check if there's an existing manual to delete
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
                    
                    # Save new manual
                    filename = secure_filename(manual.filename)
                    filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_manual_{filename}"
                    manual_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    
                    manual.save(manual_path)
                    db_manual_path = os.path.join('uploads', filename)
                    logger.info(f"New manual uploaded: {db_manual_path}")
                
            # Update the warranty in database - IMPORTANT: The database set operation needs to be updated
            # Create a list of parameters for the UPDATE query
            update_params = {
                'product_name': product_name,
                'purchase_date': purchase_date,
                'warranty_years': warranty_years,
                'expiration_date': expiration_date,
                'product_url': product_url,
                'purchase_price': purchase_price
            }
            
            # Build dynamic SQL query based on which files have been uploaded or preserved
            sql_fields = []
            sql_values = []
            
            for key, value in update_params.items():
                sql_fields.append(f"{key} = %s")
                sql_values.append(value)
            
            # Only include invoice_path in the update if it's not None
            if db_invoice_path is not None:
                sql_fields.append("invoice_path = %s")
                sql_values.append(db_invoice_path)
                
            # Only include manual_path in the update if it's not None
            if db_manual_path is not None:
                sql_fields.append("manual_path = %s")
                sql_values.append(db_manual_path)
                
            # Add the warranty_id at the end
            sql_values.append(warranty_id)
            
            # Execute the dynamic SQL update
            update_sql = f"UPDATE warranties SET {', '.join(sql_fields)} WHERE id = %s"
            cur.execute(update_sql, sql_values)
            logger.info(f"Updated warranty with SQL: {update_sql}")
            logger.info(f"Parameters: {sql_values}")
            
            # Update serial numbers
            # First, delete existing serial numbers for this warranty
            cur.execute('DELETE FROM serial_numbers WHERE warranty_id = %s', (warranty_id,))
            
            # Then insert the new serial numbers
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
        
        # Get the user's expiring_soon_days preference
        expiring_soon_days = 30  # Default value
        
        try:
            # Check if user_preferences table exists before trying to query it
            with conn.cursor() as check_cur:
                check_cur.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = 'user_preferences'
                    )
                """)
                
                table_exists = check_cur.fetchone()[0]
                
                if table_exists:
                    with conn.cursor() as pref_cur:
                        pref_cur.execute(
                            """
                            SELECT expiring_soon_days FROM user_preferences 
                            WHERE user_id = %s
                            """, 
                            (user_id,)
                        )
                        
                        preference = pref_cur.fetchone()
                        if preference:
                            expiring_soon_days = preference[0]
        except Exception as e:
            logger.error(f"Error getting user preferences: {e}")
            # Continue with default value
        
        # Current date
        today = date.today()
        thirty_days_later = today + timedelta(days=expiring_soon_days)
        ninety_days_later = today + timedelta(days=90)
        
        # Build the SQL query based on user role
        from_clause = "FROM warranties"
        where_clause = ""
        active_where = "AND"
        params = []
        
        # For non-admin users, filter by user_id
        if not request.user.get('is_admin', False):
            # For non-admin users, add join to warranty_users table
            from_clause = "FROM warranties w JOIN warranty_users wu ON w.id = wu.warranty_id"
            where_clause = "WHERE wu.user_id = %s"
            params = [user_id]
        
        with conn.cursor() as cur:
            # Get total count
            cur.execute(f"SELECT COUNT(*) {from_clause} {where_clause}", params)
            total_count = cur.fetchone()[0]
            logger.info(f"Total warranties: {total_count}")
            
            # Get active count
            cur.execute(f"SELECT COUNT(*) {from_clause} {where_clause} {active_where if where_clause else 'WHERE'} expiration_date > %s", params + [today])
            active_count = cur.fetchone()[0]
            logger.info(f"Active warranties: {active_count}")
            
            # Get expired count
            cur.execute(f"SELECT COUNT(*) {from_clause} {where_clause} {active_where if where_clause else 'WHERE'} expiration_date <= %s", params + [today])
            expired_count = cur.fetchone()[0]
            logger.info(f"Expired warranties: {expired_count}")
            
            # Get expiring soon count (using user preference)
            cur.execute(f"SELECT COUNT(*) {from_clause} {where_clause} {active_where if where_clause else 'WHERE'} expiration_date > %s AND expiration_date <= %s", 
                      params + [today, thirty_days_later])
            expiring_soon_count = cur.fetchone()[0]
            logger.info(f"Expiring soon warranties: {expiring_soon_count}")
            
            # Get expiration timeline (next 90 days, grouped by month)
            cur.execute(f"""
                SELECT 
                    EXTRACT(YEAR FROM expiration_date) as year,
                    EXTRACT(MONTH FROM expiration_date) as month,
                    COUNT(*) as count
                {from_clause} 
                {where_clause} {active_where if where_clause else 'WHERE'} expiration_date > %s AND expiration_date <= %s
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
            
            # Get recent expiring warranties (30 days before and after today)
            thirty_days_ago = today - timedelta(days=30)
            cur.execute(f"""
                SELECT 
                    id, product_name, purchase_date, warranty_years, 
                    expiration_date, invoice_path, manual_path, product_url, purchase_price
                {from_clause} 
                {where_clause} {active_where if where_clause else 'WHERE'} expiration_date >= %s AND expiration_date <= %s
                ORDER BY expiration_date
                LIMIT 10
            """, params + [thirty_days_ago, thirty_days_later])
            
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
            
            statistics = {
                'total': total_count,
                'active': active_count,
                'expired': expired_count,
                'expiring_soon': expiring_soon_count,
                'timeline': timeline,
                'recent_warranties': recent_warranties
            }
            
            return jsonify(statistics)
    
    except Exception as e:
        logger.error(f"Error getting warranty statistics: {e}")
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
        
        # Validate input
        if not first_name or not last_name:
            return jsonify({'message': 'First name and last name are required'}), 400
            
        # Get database connection
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Update user profile
            cursor.execute(
                """
                UPDATE users 
                SET first_name = %s, last_name = %s, updated_at = NOW() 
                WHERE id = %s 
                RETURNING id, username, email, first_name, last_name, created_at, updated_at
                """,
                (first_name, last_name, user_id)
            )
            
            # Get updated user data
            user_data = cursor.fetchone()
            
            if not user_data:
                return jsonify({'message': 'User not found'}), 404
                
            # Commit changes
            conn.commit()
            
            # Format user data
            user = {
                'id': user_data[0],
                'username': user_data[1],
                'email': user_data[2],
                'first_name': user_data[3],
                'last_name': user_data[4],
                'created_at': user_data[5].isoformat() if user_data[5] else None,
                'updated_at': user_data[6].isoformat() if user_data[6] else None
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
            
            # Delete user
            cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
            
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
        # Get database connection
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Check if user_preferences table exists
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'user_preferences'
                )
            """)
            
            table_exists = cursor.fetchone()[0]
            
            if not table_exists:
                # Create the user_preferences table
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
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                        UNIQUE(user_id)
                    )
                """)
                
                # Add index for faster lookups
                cursor.execute("""
                    CREATE INDEX idx_user_preferences_user_id ON user_preferences(user_id)
                """)
                
                conn.commit()
                logger.info(f"Created user_preferences table")
            
            # Get user preferences
            cursor.execute(
                """
                SELECT email_notifications, default_view, theme, expiring_soon_days, notification_frequency, notification_time, timezone
                FROM user_preferences
                WHERE user_id = %s
                """,
                (user_id,)
            )
            
            preferences_data = cursor.fetchone()
            
            if not preferences_data:
                # Create default preferences if not exists
                cursor.execute(
                    """
                    INSERT INTO user_preferences (user_id, email_notifications, default_view, theme, expiring_soon_days, notification_frequency, notification_time, timezone)
                    VALUES (%s, TRUE, 'grid', 'light', 30, 'daily', '09:00', 'UTC')
                    RETURNING email_notifications, default_view, theme, expiring_soon_days, notification_frequency, notification_time, timezone
                    """,
                    (user_id,)
                )
                
                preferences_data = cursor.fetchone()
                conn.commit()
            
            # Format preferences data
            preferences = {
                'email_notifications': preferences_data[0],
                'default_view': preferences_data[1],
                'theme': preferences_data[2],
                'expiring_soon_days': preferences_data[3],
                'notification_frequency': preferences_data[4],
                'notification_time': preferences_data[5],
                'timezone': preferences_data[6]
            }
            
            return jsonify(preferences), 200
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error in get_preferences: {str(e)}")
            
            # Return default preferences as fallback
            default_preferences = {
                'email_notifications': True,
                'default_view': 'grid',
                'theme': 'light',
                'expiring_soon_days': 30,
                'notification_frequency': 'daily',
                'notification_time': '09:00',
                'timezone': 'UTC'
            }
            
            return jsonify(default_preferences), 200
        finally:
            cursor.close()
            release_db_connection(conn)
            
    except Exception as e:
        logger.error(f"Error in get_preferences: {str(e)}")
        
        # Return default preferences as fallback
        default_preferences = {
            'email_notifications': True,
            'default_view': 'grid',
            'theme': 'light',
            'expiring_soon_days': 30,
            'notification_frequency': 'daily',
            'notification_time': '09:00',
            'timezone': 'UTC'
        }
        
        return jsonify(default_preferences), 200

@app.route('/api/auth/preferences', methods=['PUT'])
@token_required
def update_preferences():
    user_id = request.user['id']
    
    try:
        # Get request data
        data = request.get_json()
        
        if not data:
            return jsonify({'message': 'No input data provided'}), 400
        
        # Extract fields
        email_notifications = data.get('email_notifications')
        default_view = data.get('default_view')
        theme = data.get('theme')
        expiring_soon_days = data.get('expiring_soon_days')
        notification_frequency = data.get('notification_frequency')
        notification_time = data.get('notification_time')
        timezone = data.get('timezone')
        
        # Validate input
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

        # Get database connection
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Check if timezone column exists in user_preferences
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'user_preferences' AND column_name = 'timezone'
            """)
            
            has_timezone_column = cursor.fetchone() is not None
            
            # Check if user_preferences table exists
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'user_preferences'
                )
            """)
            
            table_exists = cursor.fetchone()[0]
            
            if not table_exists:
                # Create the user_preferences table
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
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                        UNIQUE(user_id)
                    )
                """)
                
                # Add index for faster lookups
                cursor.execute("""
                    CREATE INDEX idx_user_preferences_user_id ON user_preferences(user_id)
                """)
                
                # Set preferences_exist to false to create new preferences
                preferences_exist = False
                conn.commit()
                logger.info(f"Created user_preferences table")
            else:
                # Check if preferences exist
                cursor.execute(
                    "SELECT 1 FROM user_preferences WHERE user_id = %s",
                    (user_id,)
                )
                
                preferences_exist = cursor.fetchone() is not None
            
            if preferences_exist:
                # Update existing preferences
                update_fields = []
                update_values = []
                
                if email_notifications is not None:
                    update_fields.append("email_notifications = %s")
                    update_values.append(email_notifications)
                    
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
                
                if timezone and has_timezone_column:
                    update_fields.append("timezone = %s")
                    update_values.append(timezone)
                
                if update_fields:
                    # Construct return fields based on whether timezone column exists
                    return_fields = "email_notifications, default_view, theme, expiring_soon_days, notification_frequency, notification_time"
                    if has_timezone_column:
                        return_fields += ", timezone"
                    
                    update_query = f"""
                        UPDATE user_preferences 
                        SET {', '.join(update_fields)}, updated_at = NOW() 
                        WHERE user_id = %s
                        RETURNING {return_fields}
                    """
                    
                    cursor.execute(update_query, update_values + [user_id])
                    preferences_data = cursor.fetchone()
                else:
                    # No fields to update
                    # Construct select fields based on whether timezone column exists
                    select_fields = "email_notifications, default_view, theme, expiring_soon_days, notification_frequency, notification_time"
                    if has_timezone_column:
                        select_fields += ", timezone"
                    
                    cursor.execute(
                        f"""
                        SELECT {select_fields}
                        FROM user_preferences
                        WHERE user_id = %s
                        """,
                        (user_id,)
                    )
                    preferences_data = cursor.fetchone()
            else:
                # Create new preferences
                # Check for timezone column to adjust INSERT statement
                if has_timezone_column:
                    cursor.execute(
                        """
                        INSERT INTO user_preferences (
                            user_id, 
                            email_notifications, 
                            default_view, 
                            theme,
                            expiring_soon_days,
                            notification_frequency,
                            notification_time,
                            timezone
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        RETURNING email_notifications, default_view, theme, expiring_soon_days, notification_frequency, notification_time, timezone
                        """,
                        (
                            user_id,
                            email_notifications if email_notifications is not None else True,
                            default_view or 'grid',
                            theme or 'light',
                            expiring_soon_days if expiring_soon_days is not None else 30,
                            notification_frequency or 'daily',
                            notification_time or '09:00',
                            timezone or 'UTC'
                        )
                    )
                else:
                    cursor.execute(
                        """
                        INSERT INTO user_preferences (
                            user_id, 
                            email_notifications, 
                            default_view, 
                            theme,
                            expiring_soon_days,
                            notification_frequency,
                            notification_time
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        RETURNING email_notifications, default_view, theme, expiring_soon_days, notification_frequency, notification_time
                        """,
                        (
                            user_id,
                            email_notifications if email_notifications is not None else True,
                            default_view or 'grid',
                            theme or 'light',
                            expiring_soon_days if expiring_soon_days is not None else 30,
                            notification_frequency or 'daily',
                            notification_time or '09:00'
                        )
                    )
                preferences_data = cursor.fetchone()
            
            # Format preferences data
            preferences = {
                'email_notifications': preferences_data[0],
                'default_view': preferences_data[1],
                'theme': preferences_data[2],
                'expiring_soon_days': preferences_data[3],
                'notification_frequency': preferences_data[4],
                'notification_time': preferences_data[5]
            }
            
            # Add timezone if column exists
            if has_timezone_column and len(preferences_data) > 6:
                preferences['timezone'] = preferences_data[6]
            else:
                preferences['timezone'] = timezone or 'UTC'
            
            conn.commit()
            
            return jsonify(preferences), 200
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error in update_preferences: {str(e)}")
            
            # Return original data as fallback
            fallback_preferences = {
                'email_notifications': email_notifications if email_notifications is not None else True,
                'default_view': default_view or 'grid',
                'theme': theme or 'light',
                'expiring_soon_days': expiring_soon_days if expiring_soon_days is not None else 30,
                'notification_frequency': notification_frequency or 'daily',
                'notification_time': notification_time or '09:00',
                'timezone': timezone or 'UTC'
            }
            
            return jsonify(fallback_preferences), 200
        finally:
            cursor.close()
            release_db_connection(conn)
            
    except Exception as e:
        logger.error(f"Error in update_preferences: {str(e)}")
        
        # Return default preferences as fallback
        default_preferences = {
            'email_notifications': True,
            'default_view': 'grid',
            'theme': 'light',
            'expiring_soon_days': 30,
            'notification_frequency': 'daily',
            'notification_time': '09:00',
            'timezone': 'UTC'
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
        
        # Use regular connection since warranty_user now has superuser privileges
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
        
        # Use regular connection since warranty_user now has superuser privileges
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
            settings = {row[0]: row[1] for row in cur.fetchall()}
            
            # Set default values if not present
            if 'registration_enabled' not in settings:
                settings['registration_enabled'] = 'true'
                cur.execute(
                    'INSERT INTO site_settings (key, value) VALUES (%s, %s)',
                    ('registration_enabled', 'true')
                )
                conn.commit()
            
            return jsonify(settings), 200
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
            for key, value in data.items():
                # Convert boolean to string
                if isinstance(value, bool):
                    value = str(value).lower()
                
                cur.execute("""
                    INSERT INTO site_settings (key, value, updated_at) 
                    VALUES (%s, %s, CURRENT_TIMESTAMP)
                    ON CONFLICT (key) 
                    DO UPDATE SET value = %s, updated_at = CURRENT_TIMESTAMP
                """, (key, value, value))
            
            conn.commit()
            
            return jsonify({"message": "Settings updated successfully"}), 200
    except Exception as e:
        logger.error(f"Error updating site settings: {e}")
        if conn:
            conn.rollback()
        return jsonify({"message": "Failed to update site settings"}), 500
    finally:
        if conn:
            release_db_connection(conn)

# Modify the register endpoint to check if registration is enabled
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
    """Enhanced secure file serving with authorization checks."""
    try:
        logger.info(f"Secure file access request for {filename} by user {request.user['id']}")
        
        # Security check for path traversal
        if '..' in filename or filename.startswith('/'):
            logger.warning(f"Potential path traversal attempt detected: {filename} by user {request.user['id']}")
            return jsonify({"message": "Invalid file path"}), 400
        
        # Check if user is authorized to access this file
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                # Find warranties that reference this file
                query = """
                    SELECT w.id, w.user_id 
                    FROM warranties w 
                    WHERE w.invoice_path = %s OR w.manual_path = %s
                """
                cur.execute(query, (f"uploads/{filename}", f"uploads/{filename}"))
                results = cur.fetchall()
                
                # Check if user owns any of these warranties or is admin
                user_id = request.user['id']
                is_admin = request.user.get('is_admin', False)
                
                authorized = is_admin  # Admins can access all files
                
                if not authorized and results:
                    for warranty_id, warranty_user_id in results:
                        if warranty_user_id == user_id:
                            authorized = True
                            break
                
                if not authorized:
                    logger.warning(f"Unauthorized file access attempt: {filename} by user {user_id}")
                    return jsonify({"message": "You are not authorized to access this file"}), 403
                
                # Serve the file securely
                return send_from_directory('/data/uploads', filename)
        finally:
            release_db_connection(conn)
    except Exception as e:
        logger.error(f"Error in secure file access for {filename}: {e}")
        return jsonify({"message": "Error accessing file"}), 500

def get_expiring_warranties():
    """
    Query the database to find warranties that are expiring soon based on user preferences.
    Returns a list of dictionaries containing the necessary information for email notifications.
    """
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # Get today's date
            today = date.today()

            cur.execute("""
                SELECT
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
                    w.expiration_date > %s
                    AND w.expiration_date <= %s + (COALESCE(up.expiring_soon_days, 30) || ' days')::interval
                    AND u.is_active = TRUE
                    AND COALESCE(up.email_notifications, TRUE) = TRUE;
            """, (today, today))

            expiring_warranties = []
            for row in cur.fetchall():
                email, first_name, product_name, expiration_date, expiring_soon_days = row
                expiration_date_str = expiration_date.strftime('%Y-%m-%d')
                expiring_warranties.append({
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

def format_expiration_email(user, warranties):
    """
    Format an email notification for expiring warranties.
    Returns a MIMEMultipart email object with both text and HTML versions.
    """
    subject = "Warracker: Upcoming Warranty Expirations"
    
    # Create both plain text and HTML versions of the email body
    text_body = f"Hello {user['first_name']},\n\n"
    text_body += "The following warranties are expiring soon:\n\n"
    
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
        text_body += f"- {warranty['product_name']} (expires on {warranty['expiration_date']})\n"
        html_body += f"""\
            <tr>
              <td style="padding: 8px;">{warranty['product_name']}</td>
              <td style="padding: 8px;">{warranty['expiration_date']}</td>
            </tr>
        """

    text_body += "\nLog in to Warracker to view details:\n"
    text_body += "http://localhost:8080\n\n"
    text_body += "Manage your notification settings:\n"
    text_body += "http://localhost:8080/settings.html\n"

    html_body += f"""\
          </tbody>
        </table>
        <p>Log in to <a href="http://localhost:8080">Warracker</a> to view details.</p>
        <p>Manage your notification settings <a href="http://localhost:8080/settings.html">here</a>.</p>
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

# Create a lock for the notification function
notification_lock = threading.Lock()
# Track when notifications were last sent to each user
last_notification_sent = {}

def send_expiration_notifications(manual_trigger=False):
    """
    Main function to send warranty expiration notifications.
    Retrieves expiring warranties, groups them by user, and sends emails.
    
    Args:
        manual_trigger (bool): Whether this function was triggered manually (vs scheduled)
                               If True, it ignores notification frequency/time preferences
    """
    # Use a lock to prevent concurrent executions
    if not notification_lock.acquire(blocking=False):
        logger.info("Notification job already running, skipping this execution")
        return
        
    try:
        logger.info("Starting expiration notification process")
        
        # If not manually triggered, check if notifications should be sent today based on preferences
        if not manual_trigger:
            conn = None
            try:
                conn = get_db_connection()
                with conn.cursor() as cur:
                    # Get today's date and current time in UTC
                    utc_now = datetime.utcnow()
                    
                    # Get user IDs that should receive notifications today
                    eligible_users_query = """
                        SELECT 
                            u.id, 
                            u.email, 
                            u.first_name, 
                            up.notification_time,
                            up.timezone,
                            up.notification_frequency
                        FROM users u
                        JOIN user_preferences up ON u.id = up.user_id
                        WHERE u.is_active = TRUE 
                        AND up.email_notifications = TRUE
                    """
                    cur.execute(eligible_users_query)
                    eligible_users = cur.fetchall()
                    
                    if not eligible_users:
                        logger.info("No users are eligible for notifications")
                        return
                    
                    # Check if we should send notifications based on time and timezone
                    users_for_current_time = []
                    for user in eligible_users:
                        user_id, email, first_name, notification_time, timezone, frequency = user
                        
                        try:
                            # Convert UTC time to user's timezone
                            user_tz = pytz_timezone(timezone or 'UTC')
                            user_local_time = utc_now.replace(tzinfo=pytz.UTC).astimezone(user_tz)
                            
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
                                
                                # Calculate exact time difference (can be negative if current time is before notification time)
                                time_diff = current_minutes - user_minutes
                                
                                # For notifications, we want to send:
                                # 1. If current time is 0-2 minutes after scheduled time (11:27 → send between 11:27-11:29)
                                # 2. Or, if the next scheduler run would miss the time (scheduler runs every 5 min)
                                #    For example, if it's 11:24 and notification is set for 11:27, next run is 11:29 so we should send now
                                send_window = time_diff >= 0 and time_diff <= 2  # 0-2 minutes after scheduled time
                                next_miss_window = time_diff < 0 and time_diff >= -3  # 1-3 minutes before scheduled time
                                
                                logger.info(f"Time check for {email}: scheduled={time_hour}:{time_minute:02d}, " +
                                            f"current={current_hour}:{current_minute:02d}, diff={time_diff} min, " +
                                            f"send_window={send_window}, next_miss_window={next_miss_window}")
                                
                                if send_window or next_miss_window:
                                    # Check if we've already sent a notification to this user recently
                                    now_timestamp = int(utc_now.timestamp())
                                    if email in last_notification_sent:
                                        last_sent = last_notification_sent[email]
                                        # Only send if it's been more than 10 minutes since the last notification
                                        # (longer than the 5-minute scheduler interval)
                                        if now_timestamp - last_sent > 600:
                                            users_for_current_time.append(user_id)
                                            logger.info(f"User {email} eligible for notification at their local time {notification_time} ({timezone})")
                                        else:
                                            logger.info(f"Skipping notification for {email} - already sent within the last 10 minutes (last sent: {datetime.fromtimestamp(last_sent).strftime('%Y-%m-%d %H:%M:%S')})")
                                    else:
                                        users_for_current_time.append(user_id)
                                        logger.info(f"User {email} eligible for notification at their local time {notification_time} ({timezone})")
                        
                        except Exception as e:
                            logger.error(f"Error processing timezone for user {email}: {e}")
                            continue
                    
                    if not users_for_current_time:
                        logger.info("No users are scheduled for notifications at their local time")
                        return
                    
                    logger.info(f"Found {len(users_for_current_time)} users eligible for notifications now")
            except Exception as e:
                logger.error(f"Error determining notification eligibility: {e}")
                return
            finally:
                if conn:
                    release_db_connection(conn)
        
        expiring_warranties = get_expiring_warranties()
        if not expiring_warranties:
            logger.info("No expiring warranties found.")
            return

        # Group warranties by user
        users_warranties = {}
        for warranty in expiring_warranties:
            email = warranty['email']
            if email not in users_warranties:
                users_warranties[email] = {
                    'first_name': warranty['first_name'],
                    'warranties': []
                }
            users_warranties[email]['warranties'].append(warranty)
        
        # Get SMTP settings from environment variables with fallbacks
        smtp_host = os.environ.get('SMTP_HOST', 'localhost')
        smtp_port = int(os.environ.get('SMTP_PORT', '1025'))
        smtp_username = os.environ.get('SMTP_USERNAME', 'notifications@warracker.com')
        smtp_password = os.environ.get('SMTP_PASSWORD', '')
        
        # Connect to SMTP server
        try:
            # Use SMTP_SSL for port 465, regular SMTP for other ports
            if smtp_port == 465:
                import smtplib
                logger.info(f"Using SMTP_SSL connection for port 465")
                server = smtplib.SMTP_SSL(smtp_host, smtp_port)
            else:
                server = smtplib.SMTP(smtp_host, smtp_port)
                # Start TLS for security if not local debug server and not using SSL
                if smtp_host != 'localhost':
                    server.starttls()
            
            # Login if credentials are provided
            if smtp_username and smtp_password:
                logger.info(f"Logging in with username: {smtp_username}")
                server.login(smtp_username, smtp_password)

            # Send emails to each user
            utc_now = datetime.utcnow()
            timestamp = int(utc_now.timestamp())
            
            emails_sent = 0
            for email, user_data in users_warranties.items():
                # For manual triggers, check if we've sent recently
                if manual_trigger and email in last_notification_sent:
                    last_sent = last_notification_sent[email]
                    # Only allow manual trigger to bypass the time limit if it's been more than 2 minutes
                    # This prevents accidental double-clicks by admins
                    if timestamp - last_sent < 120:
                        logger.info(f"Manual trigger: Skipping notification for {email} - already sent within the last 2 minutes")
                        continue
                
                msg = format_expiration_email(
                    {'first_name': user_data['first_name'], 'email': email},
                    user_data['warranties']
                )
                try:
                    server.sendmail(smtp_username, email, msg.as_string())
                    # Record timestamp when we sent the notification
                    last_notification_sent[email] = timestamp
                    emails_sent += 1
                    logger.info(f"Expiration notification email sent to {email} for {len(user_data['warranties'])} warranties at {datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')}")
                except Exception as e:
                    logger.error(f"Error sending email to {email}: {e}")
            
            logger.info(f"Email notification process completed. Sent {emails_sent} emails out of {len(users_warranties)} eligible users.")
            # Close the server connection
            server.quit()
            
        except Exception as e:
            logger.error(f"Error connecting to SMTP server: {e}")
            logger.error(f"SMTP details - Host: {smtp_host}, Port: {smtp_port}, Username: {smtp_username}")

    except Exception as e:
        logger.error(f"Error in send_expiration_notifications: {e}")
    finally:
        notification_lock.release()

# Initialize scheduler
scheduler = BackgroundScheduler(
    job_defaults={
        'coalesce': True,       # Combine multiple executions into one
        'max_instances': 1,     # Only allow one instance of the job to run at a time
        'misfire_grace_time': 300 # Allow 5 minutes for a misfired job (increased from 60 seconds)
    }
)

# Helper to check if this is the main process that should run the scheduler
def should_run_scheduler():
    # For gunicorn
    if os.environ.get('GUNICORN_WORKER_PROCESS_NAME') == 'worker-0' or \
       (os.environ.get('GUNICORN_WORKER_CLASS') and int(os.environ.get('GUNICORN_WORKER_ID', '0')) == 0):
        logger.info("Starting scheduler in Gunicorn worker 0")
        return True
    # For development server
    elif __name__ == '__main__':
        logger.info("Starting scheduler in development server")
        return True
    # Default case - don't start scheduler
    return False

# Only start the scheduler in the main process, not in workers
if should_run_scheduler():
    # Check for scheduled notifications every 2 minutes for more precise timing
    scheduler.add_job(func=send_expiration_notifications, trigger="interval", minutes=2, id='notification_job')
    scheduler.start()
    logger.info("Email notification scheduler started - checking every 2 minutes")
    
    # Add a shutdown hook
    atexit.register(lambda: scheduler.shutdown())

# Initialize the database when the application starts
if __name__ != '__main__':  # Only for production
    try:
        init_db()
        logger.info("Database initialized during application startup")
    except Exception as e:
        logger.error(f"Database initialization error during startup: {e}")

if __name__ == '__main__':
    try:
        app.run(debug=os.environ.get('FLASK_DEBUG', '0') == '1', host='0.0.0.0')
    except Exception as e:
        logger.error(f"Application startup error: {e}")

# Move this code before the if __name__ == '__main__' block
@app.route('/api/admin/send-notifications', methods=['POST'])
@admin_required
def trigger_notifications():
    """
    Admin-only endpoint to manually trigger warranty expiration notifications.
    Useful for testing and for sending notifications outside the scheduled time.
    """
    try:
        logger.info(f"Manual notification trigger requested by admin user {request.user['id']}")
        send_expiration_notifications(manual_trigger=True)
        return jsonify({'message': 'Notifications triggered successfully'}), 200
    except Exception as e:
        error_msg = f"Error triggering notifications: {str(e)}"
        logger.error(error_msg)
        return jsonify({'message': 'Failed to trigger notifications', 'error': error_msg}), 500

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
                cur.execute('SELECT * FROM warranties WHERE id = %s', (warranty_id,))
            else:
                cur.execute('SELECT * FROM warranties WHERE id = %s AND user_id = %s', 
                          (warranty_id, user_id))
                
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
    """Get all tags"""
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute('SELECT id, name, color, created_at FROM tags ORDER BY name')
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
        logger.error(f"Error fetching tags: {e}")
        return jsonify({"error": "Failed to fetch tags"}), 500
    finally:
        if conn:
            release_db_connection(conn)

@app.route('/api/tags', methods=['POST'])
@token_required
def create_tag():
    """Create a new tag"""
    conn = None
    try:
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
            # Check if tag with this name already exists
            cur.execute('SELECT id FROM tags WHERE name = %s', (name,))
            existing_tag = cur.fetchone()
            
            if existing_tag:
                return jsonify({"error": "A tag with this name already exists"}), 409
            
            # Create new tag
            cur.execute(
                'INSERT INTO tags (name, color) VALUES (%s, %s) RETURNING id',
                (name, color)
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
    """Update an existing tag"""
    conn = None
    try:
        data = request.json
        
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        name = data.get('name')
        color = data.get('color')
        
        if not name and not color:
            return jsonify({"error": "At least one field (name or color) is required"}), 400
        
        # Validate color format if provided
        if color and not re.match(r'^#[0-9A-Fa-f]{6}$', color):
            return jsonify({"error": "Invalid color format. Use hex format (e.g., #FF5733)"}), 400
        
        conn = get_db_connection()
        with conn.cursor() as cur:
            # Check if tag exists
            cur.execute('SELECT id FROM tags WHERE id = %s', (tag_id,))
            if cur.fetchone() is None:
                return jsonify({"error": "Tag not found"}), 404
            
            # Check if new name already exists (if name is being updated)
            if name:
                cur.execute('SELECT id FROM tags WHERE name = %s AND id != %s', (name, tag_id))
                if cur.fetchone():
                    return jsonify({"error": "A tag with this name already exists"}), 409
            
            # Build update query
            update_fields = []
            values = []
            
            if name:
                update_fields.append("name = %s")
                values.append(name)
            
            if color:
                update_fields.append("color = %s")
                values.append(color)
            
            values.append(tag_id)
            
            # Update tag
            query = f"UPDATE tags SET {', '.join(update_fields)} WHERE id = %s"
            cur.execute(query, values)
            conn.commit()
            
            return jsonify({"message": "Tag updated successfully"}), 200
    except Exception as e:
        logger.error(f"Error updating tag {tag_id}: {e}")
        if conn:
            conn.rollback()
        return jsonify({"error": "Failed to update tag"}), 500
    finally:
        if conn:
            release_db_connection(conn)

@app.route('/api/warranties/<int:warranty_id>/tags', methods=['GET'])
@token_required
def get_warranty_tags(warranty_id):
    """Get all tags for a specific warranty"""
    conn = None
    try:
        user_id = request.user['id']
        is_admin = request.user['is_admin']
        
        conn = get_db_connection()
        with conn.cursor() as cur:
            # First check if the warranty exists and user has access to it
            if is_admin:
                cur.execute('SELECT id FROM warranties WHERE id = %s', (warranty_id,))
            else:
                cur.execute('SELECT id FROM warranties WHERE id = %s AND user_id = %s', 
                          (warranty_id, user_id))
            
            if cur.fetchone() is None:
                return jsonify({"error": "Warranty not found or you don't have permission to access it"}), 404
            
            # Get tags for this warranty
            cur.execute('''
                SELECT t.id, t.name, t.color, t.created_at
                FROM tags t
                JOIN warranty_tags wt ON t.id = wt.tag_id
                WHERE wt.warranty_id = %s
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
    """Add tags to a warranty"""
    conn = None
    try:
        user_id = request.user['id']
        is_admin = request.user['is_admin']
        
        data = request.json
        if not data or 'tag_ids' not in data:
            return jsonify({"error": "tag_ids array is required"}), 400
        
        tag_ids = data['tag_ids']
        if not isinstance(tag_ids, list):
            return jsonify({"error": "tag_ids must be an array of tag IDs"}), 400
        
        conn = get_db_connection()
        with conn.cursor() as cur:
            # First check if the warranty exists and user has access to it
            if is_admin:
                cur.execute('SELECT id FROM warranties WHERE id = %s', (warranty_id,))
            else:
                cur.execute('SELECT id FROM warranties WHERE id = %s AND user_id = %s', 
                          (warranty_id, user_id))
            
            if cur.fetchone() is None:
                return jsonify({"error": "Warranty not found or you don't have permission to modify it"}), 404
            
            # Remove existing tags
            cur.execute('DELETE FROM warranty_tags WHERE warranty_id = %s', (warranty_id,))
            
            # Add new tags
            for tag_id in tag_ids:
                # Verify tag exists
                cur.execute('SELECT id FROM tags WHERE id = %s', (tag_id,))
                if cur.fetchone() is None:
                    conn.rollback()
                    return jsonify({"error": f"Tag with ID {tag_id} not found"}), 404
                
                # Add tag to warranty
                cur.execute(
                    'INSERT INTO warranty_tags (warranty_id, tag_id) VALUES (%s, %s)',
                    (warranty_id, tag_id)
                )
            
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
