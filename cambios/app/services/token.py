import jwt
from datetime import datetime, timedelta, UTC
import os

JWT_ALGORITHM = os.getenv('JWT_ALGORITHM')
SECRET_KEY = os.getenv('SECRET_KEY')
DEVELOPMENT_MODE = os.getenv('DEVELOPMENT_MODE') == 'True'
def validate_jwt(token):
        
    if DEVELOPMENT_MODE and token == 'simulated_token':
        return {
            '_id': 'simulated_user_id',
            'email': 'simulated_user_email@example.com'
        }
    try:
        decoded = jwt.decode(token, SECRET_KEY, JWT_ALGORITHM)
        return decoded
    except: # Token has expired or is invalid
        return None