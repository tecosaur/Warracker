# backend/__init__.py
import os
import logging
import psycopg2.errors
from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix

logger = logging.getLogger(__name__)

def ensure_owner_exists():
    """
    Ensure that an application owner exists. This is a backup mechanism
    in case the migration failed. Runs automatically on app startup.
    """
    from .db_handler import get_db_connection, release_db_connection
    
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

def create_app(config_name=None):
    """Create and configure an instance of the Flask application."""
    # Configure logging FIRST
    logging.basicConfig(level=logging.INFO)
    logger.info("Starting application factory...")
    
    # Determine configuration
    if config_name is None:
        config_name = os.environ.get('FLASK_CONFIG', 'default')
    
    # Create Flask app instance
    app = Flask(__name__)
    
    # Apply ProxyFix middleware for reverse proxy support
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)
    
    # Load configuration
    try:
        from .config import config
        app.config.from_object(config[config_name])
        config[config_name].init_app(app)
        logger.info(f"Configuration '{config_name}' loaded successfully")
    except ImportError:
        try:
            from config import config
            app.config.from_object(config[config_name])
            config[config_name].init_app(app)
            logger.info(f"Configuration '{config_name}' loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            raise
    
    # Initialize extensions
    try:
        from .extensions import initialize_extensions
        initialize_extensions(app)
    except ImportError:
        from extensions import initialize_extensions
        initialize_extensions(app)
    
    # Register Blueprints within app context
    with app.app_context():
        try:
            # Import blueprints
            from .auth_routes import auth_bp
            from .oidc_handler import oidc_bp
            from .warranties_routes import warranties_bp
            from .admin_routes import admin_bp
            from .statistics_routes import statistics_bp
            from .tags_routes import tags_bp
            from .file_routes import file_bp
        except ImportError:
            # Fallback for development
            from auth_routes import auth_bp
            from oidc_handler import oidc_bp
            from warranties_routes import warranties_bp
            from admin_routes import admin_bp
            from statistics_routes import statistics_bp
            from tags_routes import tags_bp
            from file_routes import file_bp
        
        # Register blueprints
        app.register_blueprint(auth_bp, url_prefix='/api/auth')
        app.register_blueprint(oidc_bp, url_prefix='/api')
        app.register_blueprint(warranties_bp, url_prefix='/api')
        app.register_blueprint(admin_bp, url_prefix='/api/admin')
        app.register_blueprint(statistics_bp, url_prefix='/api')
        app.register_blueprint(tags_bp, url_prefix='/api')
        app.register_blueprint(file_bp, url_prefix='/api')
        
        logger.info("All blueprints registered successfully")

        # Apply config
        if app.config['FIXED_CONFIG']:
            try:
                from .db_handler import apply_site_settings_file
                apply_site_settings_file(app.config['FIXED_CONFIG'])
            except ImportError:
                from db_handler import apply_site_settings_file
                apply_site_settings_file(app.config['FIXED_CONFIG'])

        # Initialize OIDC client after extensions and blueprints
        try:
            from .db_handler import get_db_connection, release_db_connection
            from .oidc_handler import init_oidc_client
            init_oidc_client(app, get_db_connection, release_db_connection)
        except ImportError:
            from db_handler import get_db_connection, release_db_connection
            from oidc_handler import init_oidc_client
            init_oidc_client(app, get_db_connection, release_db_connection)
        
        # Ensure an owner exists on startup
        ensure_owner_exists()
        
        # Initialize the notification scheduler with the app context
        try:
            from .notifications import init_scheduler
            from .db_handler import get_db_connection, release_db_connection
            
            init_scheduler(app, get_db_connection, release_db_connection)
            logger.info("✅ Notification scheduler initialized successfully in factory")
        except ImportError:
            try:
                from notifications import init_scheduler
                from db_handler import get_db_connection, release_db_connection
                
                init_scheduler(app, get_db_connection, release_db_connection)
                logger.info("✅ Notification scheduler initialized successfully in factory (dev mode)")
            except Exception as e:
                logger.error(f"❌ Failed to initialize notification scheduler: {e}")
                # Continue without notifications - the app can still function
        except Exception as e:
            logger.error(f"❌ Failed to initialize notification scheduler: {e}")
            # Continue without notifications - the app can still function
        
        logger.info("Application factory completed successfully")
    
    return app
