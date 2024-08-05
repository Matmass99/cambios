import os
from bson import ObjectId
from flask import Blueprint, request, jsonify, g
from webargs import fields
from webargs.flaskparser import use_args
from app.db_connection import mongo
from app.services.google_auth import validate_credentials
from app.services.token import validate_jwt

epics = Blueprint('epics', __name__)

# Validación para la creación de epics
epic_args = {
    'title': fields.Str(required=True),
    'description': fields.Str(required=True),
    'sprints': fields.Str(required=True),
    'priority': fields.Str(required=True),
}

# Validación para la actualización de epics
update_epic_args = {
    'description': fields.Str(required=False),
    'sprints': fields.Str(required=False),
    'priority': fields.Str(required=False),
}

def get_current_user(request):
    if os.getenv('DEVELOPMENT_MODE', 'False') == 'True':
        #En modo de desarrollo, usa un usuario simulado
        return {'sub': 'simulated_user_id','username': 'Usuario de prueba' ,'email': 'test@example.com','picture': 'default.png'}
    
    token = request.headers.get('Authorization', None)
    if token is None:
        print("No token provided")
        return None

    # Remove the "Bearer " prefix
    token = token.replace('Bearer ', '')
    print(f"Token: {token}")
    
    # Validate the JWT token
    decoded = validate_jwt(token)
    if decoded is None:
        print("Invalid token")
        return None

    # Validate Google token
    user_token = decoded.get('google_token')
    if user_token is None:
        print("No Google token in JWT")
        return None

    user_info = validate_credentials(user_token)
    if user_info is None:
        print("Invalid Google token")
        return None
    return user_info

def convert_objectid_to_str(document):
    """Convierte todos los ObjectId en un documento a strings."""
    if isinstance(document, dict):
        return {i: (str(j) if isinstance(j, ObjectId) else convert_objectid_to_str(j)) for i, j in document.items()}
    elif isinstance(document, list):
        return [convert_objectid_to_str(item) for item in document]
    return document

@epics.route('/', methods=['POST'])
def create_epic():
    current_user = get_current_user(request)
    if current_user is None:
        return jsonify({"message": "Unauthorized"}), 401

    try:
        args = request.get_json()
        
        # Normalizar el título
        normalized_title = args['title'].strip().lower()
        
        # Comprobar si ya existe una épica con el mismo título normalizado
        existing_epic = mongo.db.epics.find_one({"title_normalized": normalized_title, "creator._id": current_user['sub']})
        if existing_epic:
            return jsonify({"error": "Epic with this title already exists."}), 400

        creator_data = {
            "_id": current_user['sub'],  
            "username": current_user.get('username', 'Unknown'),  
            "profile_picture": current_user.get('picture', '') 
        }
        
        epic_data = {**args, 'creator': creator_data}  

        result = mongo.db.epics.insert_one(epic_data)
        created_epic = mongo.db.epics.find_one({"_id": result.inserted_id})
        created_epic["_id"] = str(created_epic["_id"])  
        return jsonify(created_epic), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@epics.route('/<string:title>', methods=['PUT'])
def update_epic(title):
    current_user = get_current_user(request)
    if current_user is None:
        return jsonify({"message": "Unauthorized"}), 401

    try:
        args = request.get_json()
        
        epic = mongo.db.epics.find_one({"title": title})
        if epic is None:
            return jsonify({"message": "Epic not found."}), 404

        creator_id = epic.get('creator', {}).get('_id', None)
        if creator_id != current_user['sub']:
            return jsonify({"message": "Unauthorized to update this epic."}), 403

        update_fields = {key: value for key, value in args.items() if value is not None}

        if update_fields:
            result = mongo.db.epics.update_one({"title": title}, {"$set": update_fields})
            if result.matched_count == 0:
                return jsonify({"message": "Epic update failed."}), 500

        updated_epic = mongo.db.epics.find_one({"title": title})
        if updated_epic:
            updated_epic["_id"] = str(updated_epic["_id"])
            return jsonify(updated_epic), 200
        else:
            return jsonify({"message": "Epic update failed."}), 500

    except Exception as e:
        print(f"Exception: {e}") 
        return jsonify({"error": str(e)}), 500

@epics.route('/', methods=['GET'])
def get_all_epics():
    try:
        epics_list = mongo.db.epics.find()  
        epics_data = [convert_objectid_to_str(epic) for epic in epics_list]
        return jsonify(epics_data), 200
    except Exception as e:
        print(f"Exception: {e}")  
        return jsonify({"error": str(e)}), 500