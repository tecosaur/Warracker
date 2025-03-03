from flask import Flask, request, jsonify, send_from_directory
import psycopg2
from psycopg2 import pool
import os
from datetime import datetime, timedelta, date
from werkzeug.utils import secure_filename
from flask_cors import CORS
import logging

app = Flask(__name__)
CORS(app)  # Enable CORS

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

UPLOAD_FOLDER = '/data/uploads'
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max upload

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

# PostgreSQL connection pool
DB_HOST = os.environ.get('DB_HOST', 'warrackerdb')
DB_NAME = os.environ.get('DB_NAME', 'warranty_db')
DB_USER = os.environ.get('DB_USER', 'warranty_user')
DB_PASSWORD = os.environ.get('DB_PASSWORD', 'warranty_password')

# Create a connection pool
connection_pool = pool.SimpleConnectionPool(
    1, 10,  # min, max connections
    host=DB_HOST,
    database=DB_NAME,
    user=DB_USER,
    password=DB_PASSWORD
)

def get_db_connection():
    try:
        return connection_pool.getconn()
    except Exception as e:
        logger.error(f"Database connection error: {e}")
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
            # Add indexes to frequently queried fields
            cur.execute('''
                CREATE TABLE IF NOT EXISTS warranties (
                    id SERIAL PRIMARY KEY,
                    product_name TEXT NOT NULL,
                    purchase_date DATE NOT NULL,
                    warranty_years INTEGER NOT NULL,
                    expiration_date DATE,
                    invoice_path TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Add indexes for faster queries
            cur.execute('CREATE INDEX IF NOT EXISTS idx_expiration_date ON warranties(expiration_date)')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_product_name ON warranties(product_name)')
            
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

@app.route('/api/warranties', methods=['GET'])
def get_warranties():
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute('SELECT * FROM warranties ORDER BY expiration_date')
            warranties = cur.fetchall()
            columns = [desc[0] for desc in cur.description]
            warranties_list = []
            
            for row in warranties:
                warranty_dict = dict(zip(columns, row))
                # Convert date objects to ISO format strings for JSON serialization
                for key, value in warranty_dict.items():
                    if isinstance(value, (datetime, date)):
                        warranty_dict[key] = value.isoformat()
                warranties_list.append(warranty_dict)
                
            return jsonify(warranties_list)
    except Exception as e:
        logger.error(f"Error retrieving warranties: {e}")
        return jsonify({"error": "Failed to retrieve warranties"}), 500
    finally:
        if conn:
            release_db_connection(conn)

@app.route('/api/warranties', methods=['POST'])
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
        
        try:
            purchase_date = datetime.strptime(purchase_date_str, '%Y-%m-%d')
        except ValueError:
            return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400
            
        expiration_date = purchase_date + timedelta(days=warranty_years * 365)
        
        # Handle file upload
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
        
        # Save to database
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute('''
                INSERT INTO warranties (product_name, purchase_date, warranty_years, expiration_date, invoice_path)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
            ''', (product_name, purchase_date, warranty_years, expiration_date, db_invoice_path))
            warranty_id = cur.fetchone()[0]
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
def delete_warranty(warranty_id):
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # First get the invoice path to delete the file
            cur.execute('SELECT invoice_path FROM warranties WHERE id = %s', (warranty_id,))
            result = cur.fetchone()
            
            if not result:
                return jsonify({"error": "Warranty not found"}), 404
                
            invoice_path = result[0]
            
            # Delete the warranty from database
            cur.execute('DELETE FROM warranties WHERE id = %s', (warranty_id,))
            deleted_rows = cur.rowcount
            conn.commit()
            
            # Delete the invoice file if it exists
            if invoice_path:
                full_path = os.path.join('/data', invoice_path)
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
def update_warranty(warranty_id):
    conn = None
    try:
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
        
        try:
            purchase_date = datetime.strptime(purchase_date_str, '%Y-%m-%d')
        except ValueError:
            return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400
            
        expiration_date = purchase_date + timedelta(days=warranty_years * 365)
        
        conn = get_db_connection()
        with conn.cursor() as cur:
            # Check if warranty exists
            cur.execute('SELECT invoice_path FROM warranties WHERE id = %s', (warranty_id,))
            result = cur.fetchone()
            
            if not result:
                return jsonify({"error": "Warranty not found"}), 404
                
            old_invoice_path = result[0]
            
            # Handle file upload if new file is provided
            db_invoice_path = old_invoice_path
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
                    if old_invoice_path and old_invoice_path != db_invoice_path:
                        old_full_path = os.path.join('/data', old_invoice_path)
                        if os.path.exists(old_full_path):
                            os.remove(old_full_path)
            
            # Update the warranty in database
            cur.execute('''
                UPDATE warranties
                SET product_name = %s, purchase_date = %s, warranty_years = %s, 
                    expiration_date = %s, invoice_path = %s
                WHERE id = %s
            ''', (product_name, purchase_date, warranty_years, expiration_date, 
                  db_invoice_path, warranty_id))
            
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

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    try:
        # Make sure this is pointing to the correct absolute path
        return send_from_directory('/data/uploads', filename)
    except Exception as e:
        logger.error(f"Error serving file {filename}: {e}")
        return jsonify({"error": "File not found"}), 404

@app.errorhandler(413)
def request_entity_too_large(error):
    return jsonify({"error": "File too large. Maximum size is 16MB"}), 413

if __name__ == '__main__':
    try:
        init_db()
        app.run(debug=os.environ.get('FLASK_DEBUG', '0') == '1', host='0.0.0.0')
    except Exception as e:
        logger.critical(f"Failed to start application: {e}")