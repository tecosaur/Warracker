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
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # Create warranties table if it doesn't exist
            cur.execute('''
                CREATE TABLE IF NOT EXISTS warranties (
                    id SERIAL PRIMARY KEY,
                    product_name TEXT NOT NULL,
                    purchase_date DATE NOT NULL,
                    warranty_years INTEGER NOT NULL,
                    expiration_date DATE,
                    invoice_path TEXT,
                    manual_path TEXT,
                    product_url TEXT,
                    purchase_price DECIMAL(10, 2),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Add user_id column if it doesn't exist - use DO block to avoid errors
            cur.execute('''
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name='warranties' AND column_name='user_id'
                ) THEN
                    ALTER TABLE warranties ADD COLUMN user_id INTEGER;
                END IF;
            END $$;
            ''')
            
            # Add indexes for faster queries
            cur.execute('CREATE INDEX IF NOT EXISTS idx_expiration_date ON warranties(expiration_date)')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_product_name ON warranties(product_name)')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_user_id ON warranties(user_id)')
            
            # Create serial numbers table
            cur.execute('''
                CREATE TABLE IF NOT EXISTS serial_numbers (
                    id SERIAL PRIMARY KEY,
                    warranty_id INTEGER NOT NULL,
                    serial_number VARCHAR(255) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (warranty_id) REFERENCES warranties(id) ON DELETE CASCADE
                )
            ''')
            
            # Add indexes for serial numbers
            cur.execute('CREATE INDEX IF NOT EXISTS idx_warranty_id ON serial_numbers(warranty_id)')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_serial_number ON serial_numbers(serial_number)')
            
            # Create users table
            cur.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR(255) NOT NULL UNIQUE,
                    email VARCHAR(255) NOT NULL UNIQUE,
                    password_hash VARCHAR(255) NOT NULL,
                    first_name VARCHAR(255),
                    last_name VARCHAR(255),
                    is_active BOOLEAN DEFAULT TRUE,
                    is_admin BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP
                )
            ''')
            
            # Add indexes for users
            cur.execute('CREATE INDEX IF NOT EXISTS idx_username ON users(username)')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_email ON users(email)')
            
            # Create password reset tokens table
            cur.execute('''
                CREATE TABLE IF NOT EXISTS password_reset_tokens (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    token VARCHAR(255) NOT NULL,
                    expires_at TIMESTAMP NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            ''')
            
            # Add indexes for password reset tokens
            cur.execute('CREATE INDEX IF NOT EXISTS idx_token ON password_reset_tokens(token)')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_user_id_token ON password_reset_tokens(user_id)')
            
            # Create user sessions table
            cur.execute('''
                CREATE TABLE IF NOT EXISTS user_sessions (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    session_token VARCHAR(255) NOT NULL,
                    expires_at TIMESTAMP NOT NULL,
                    ip_address VARCHAR(45),
                    user_agent TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            ''')
            
            # Add indexes for user sessions
            cur.execute('CREATE INDEX IF NOT EXISTS idx_session_token ON user_sessions(session_token)')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_user_id_session ON user_sessions(user_id)')
            
        conn.commit()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization error: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
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
                # Make filename unique by adding timestamp
                filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
                invoice_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                
                # Ensure directory exists
                os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
                
                invoice.save(invoice_path)
                db_invoice_path = os.path.join('uploads', filename)
        
        # Handle manual file upload
        db_manual_path = None
        if 'manual' in request.files:
            manual = request.files['manual']
            if manual.filename != '':
                if not allowed_file(manual.filename):
                    return jsonify({"error": "File type not allowed. Use PDF, PNG, JPG, or JPEG"}), 400
                    
                filename = secure_filename(manual.filename)
                # Make filename unique by adding timestamp
                filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_manual_{filename}"
                manual_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                
                # Ensure directory exists
                os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
                
                manual.save(manual_path)
                db_manual_path = os.path.join('uploads', filename)
        
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
                        
                    filename = secure_filename(invoice.filename)
                    filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
                    invoice_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    
                    invoice.save(invoice_path)
                    db_invoice_path = os.path.join('uploads', filename)
                    
                    # Remove old invoice file if exists and different from new one
                    cur.execute('SELECT invoice_path FROM warranties WHERE id = %s', (warranty_id,))
                    old_invoice_path = cur.fetchone()[0]
                    if old_invoice_path and old_invoice_path != db_invoice_path:
                        old_full_path = os.path.join('/data', old_invoice_path)
                        if os.path.exists(old_full_path):
                            os.remove(old_full_path)
            
            # Handle manual file upload if new file is provided
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
                    
                    # Remove old manual file if exists and different from new one
                    cur.execute('SELECT manual_path FROM warranties WHERE id = %s', (warranty_id,))
                    old_manual_path = cur.fetchone()[0]
                    if old_manual_path and old_manual_path != db_manual_path:
                        old_full_path = os.path.join('/data', old_manual_path)
                        if os.path.exists(old_full_path):
                            os.remove(old_full_path)
            
            # Update the warranty in database
            cur.execute('''
                UPDATE warranties
                SET product_name = %s, purchase_date = %s, warranty_years = %s, 
                    expiration_date = %s, invoice_path = %s, manual_path = %s, product_url = %s, purchase_price = %s
                WHERE id = %s
            ''', (product_name, purchase_date, warranty_years, expiration_date, 
                  db_invoice_path, db_manual_path, product_url, purchase_price, warranty_id))
            
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
                SELECT email_notifications, default_view, theme, expiring_soon_days
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
                    INSERT INTO user_preferences (user_id, email_notifications, default_view, theme, expiring_soon_days)
                    VALUES (%s, TRUE, 'grid', 'light', 30)
                    RETURNING email_notifications, default_view, theme, expiring_soon_days
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
                'expiring_soon_days': preferences_data[3]
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
                'expiring_soon_days': 30
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
            'expiring_soon_days': 30
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
                
                if update_fields:
                    update_query = f"""
                        UPDATE user_preferences 
                        SET {', '.join(update_fields)}, updated_at = NOW() 
                        WHERE user_id = %s
                        RETURNING email_notifications, default_view, theme, expiring_soon_days
                    """
                    
                    cursor.execute(update_query, update_values + [user_id])
                    preferences_data = cursor.fetchone()
                else:
                    # No fields to update
                    cursor.execute(
                        """
                        SELECT email_notifications, default_view, theme, expiring_soon_days
                        FROM user_preferences
                        WHERE user_id = %s
                        """,
                        (user_id,)
                    )
                    preferences_data = cursor.fetchone()
            else:
                # Create new preferences
                cursor.execute(
                    """
                    INSERT INTO user_preferences (
                        user_id, 
                        email_notifications, 
                        default_view, 
                        theme,
                        expiring_soon_days
                    )
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING email_notifications, default_view, theme, expiring_soon_days
                    """,
                    (
                        user_id,
                        email_notifications if email_notifications is not None else True,
                        default_view or 'grid',
                        theme or 'light',
                        expiring_soon_days if expiring_soon_days is not None else 30
                    )
                )
                preferences_data = cursor.fetchone()
            
            # Format preferences data
            preferences = {
                'email_notifications': preferences_data[0],
                'default_view': preferences_data[1],
                'theme': preferences_data[2],
                'expiring_soon_days': preferences_data[3]
            }
            
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
                'expiring_soon_days': expiring_soon_days if expiring_soon_days is not None else 30
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
            'expiring_soon_days': 30
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

# Initialize the database when the application starts
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