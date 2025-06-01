# backend/auth_utils.py
import jwt
from datetime import datetime, timedelta
from flask import current_app # To access app.config

def generate_token(user_id):
    """Generate a JWT token for the user"""
    payload = {
        'exp': datetime.utcnow() + current_app.config['JWT_EXPIRATION_DELTA'],
        'iat': datetime.utcnow(),
        'sub': user_id
    }
    return jwt.encode(payload, current_app.config['SECRET_KEY'], algorithm='HS256')

# Note: You can later move decode_token, token_required, admin_required here too.
# For token_required and admin_required, you'll also need:
# from functools import wraps
# from flask import request, jsonify
# And you'd need to import get_db_connection, release_db_connection from your db_handler. 