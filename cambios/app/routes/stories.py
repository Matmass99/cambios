import os
from flask import Blueprint, request, jsonify
from app.db_connection import mongo
from app.services.google_auth import validate_credentials
stories = Blueprint('stories', __name__)

# Validación para la creación de stories
story_args = {
    'title': fields.Str(required=True),
    'description': fields.Str(required=True),
    'acceptance_criteria': fields.Str(required=True),
    'assigned_to': fields.List(fields.Str(), required=True),
    'epic': fields.Str(required=True),
    'sprint': fields.Int(required=True),
    'story_points': fields.Int(required=True),
    'tags': fields.List(fields.Str(), required=True),
    'priority': fields.Str(required=True),
    'estimation_method': fields.Str(required=True),
    'type': fields.Str(required=True),
    'tasks': fields.List(fields.Str(), required=True), 
    'story_id': fields.Str(required=True),
    'estimation': fields.Str(required=True),
    'team': fields.Str(required=True)
}

# Validación para la actualización de stories
update_story_args = {
    'title': fields.Str(required=False),
    'description': fields.Str(required=False),
    'acceptance_criteria': fields.Str(required=False),
    'assigned_to': fields.List(fields.Str(), required=False),
    'epic': fields.Str(required=False),
    'sprint': fields.Int(required=False),
    'story_points': fields.Int(required=False),
    'tags': fields.List(fields.Str(), required=False),
    'priority': fields.Str(required=False),
    'estimation_method': fields.Str(required=False),
    'type': fields.Str(required=False),
    'tasks': fields.List(fields.Str(), required=False), 
    'estimation': fields.Str(required=False),
    'team': fields.Str(required=False)
}

def get_current_user(request):
    if os.getenv('DEVELOPMENT_MODE', 'False') == 'True':
        # En modo de desarrollo, usa un usuario simulado
        return {'sub': 'simulated_user_id', 'username': 'Usuario de prueba', 'email': 'test@example.com', 'picture': 'default.png'}
    
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
@stories.route('/', methods=['POST'])
def create_story():
    current_user = get_current_user(request)
    if current_user is None:
        return jsonify({"message": "Unauthorized"}), 401

    try:
        args = request.get_json()
        print("Received data:", args)
        
        # Normalizar el título
        normalized_title = args['title'].strip().lower()
        
        # Comprobar si ya existe una historia con el mismo título normalizado
        existing_story = mongo.db.stories.find_one({"title_normalized": normalized_title, "creator._id": current_user['sub']})
        if existing_story:
            return jsonify({"error": "Story with this title already exists."}), 400

        # Manejar la lista de usuarios asignados
        assigned_to_user_ids = args.get('assigned_to', [])
        print("Assigned to IDs:", assigned_to_user_ids)
        assigned_to_users = []
        for user_id in assigned_to_user_ids:
            user = mongo.db.users.find_one({"_id": ObjectId(user_id)})
            if user:
                assigned_to_users.append({
                    "_id": str(user['_id']),
                    "username": user.get('username', 'Unknown'),
                    "profile_picture": user.get('picture', '')
                })
            else:
                return jsonify({"message": f"Assigned user with ID {user_id} not found."}), 404

        creator_data = {
            "_id": current_user['sub'],
            "username": current_user.get('username', 'Unknown'),
            "profile_picture": current_user.get('picture', '')
        }

        if not assigned_to_users:
            assigned_to_users = [creator_data]

        # Obtener los datos completos de las tareas 
        tasks = []
        for task_id in args.get('tasks', []):
            print("Task ID:", task_id)
            task = mongo.db.tasks.find_one({"_id": ObjectId(task_id)})
            if task:
                tasks.append({
                    "title": task.get("title"),
                    "description": task.get("description"),
                    "app": task.get("app"),
                    "status": task.get("status")
                })
            else:
                return jsonify({"message": f"Task with ID {task_id} not found."}), 404

        # Obtener los datos de las epics
        epic_id = args.get('epic')
        epic_data = mongo.db.epics.find_one({"_id": ObjectId(epic_id)})
        if epic_data:
            epic_info = {
                "_id": str(epic_data["_id"]),
                "title": epic_data.get("title")
            }
        else:
            return jsonify({"message": f"Epic with ID {epic_id} not found."}), 404

        # Obtener los datos del equipo
        team_id = args.get('team')
        print("Received team data:", team_id)  
        if team_id and ObjectId.is_valid(team_id):
            team_data = mongo.db.teams.find_one({"_id": ObjectId(team_id)})
            if team_data:
                team_info = {
                    "_id": str(team_data["_id"]),
                    "name": team_data.get("name") 
                }
            else:
                return jsonify({"message": f"Team with ID {team_id} not found."}), 404
        else:
            team_info = None
        
        story_data = {
            **args,
            'creator': creator_data,
            'assigned_to': assigned_to_users,
            'tasks': tasks,
            'epic': epic_info,
            'team': team_info
        }

        result = mongo.db.stories.insert_one(story_data)
        created_story = mongo.db.stories.find_one({"_id": result.inserted_id})
        created_story["_id"] = str(created_story["_id"])
        return jsonify(created_story), 201
    except Exception as e:
        print("Error:", e) 
        return jsonify({"error": str(e)}), 500

@stories.route('/', methods=['GET'])
def get_stories():
    try:
        stories_cursor = mongo.db.stories.find()  
        stories_list = [convert_objectid_to_str(story) for story in stories_cursor]
        return jsonify(stories_list), 200
    except Exception as e:
        print(f"Exception: {e}")  
        return jsonify({"error": str(e)}), 500

@stories.route('/<string:story_id>', methods=['PUT'])
def update_story(story_id):
    current_user = get_current_user(request)
    if current_user is None:
        return jsonify({"message": "Unauthorized"}), 401

    try:
        args = request.get_json()
        print("Received data:", args)

        # Encuentra la historia actual usando el story_id
        story = mongo.db.stories.find_one({"_id": ObjectId(story_id)})
        if story is None:
            return jsonify({"message": "Story not found."}), 404

        creator_id = story.get('creator', {}).get('_id', None)
        if creator_id != current_user['sub']:
            return jsonify({"message": "Unauthorized to update this story."}), 403

        # Manejar la lista de usuarios asignados
        assigned_to_user_ids = args.get('assigned_to', [])
        print("Assigned to IDs:", assigned_to_user_ids)
        assigned_to_users = []
        for user_id in assigned_to_user_ids:
            user = mongo.db.users.find_one({"_id": ObjectId(user_id)})
            if user:
                assigned_to_users.append({
                    "_id": str(user['_id']),
                    "username": user.get('username', 'Unknown'),
                    "profile_picture": user.get('picture', '')
                })
            else:
                return jsonify({"message": f"Assigned user with ID {user_id} not found."}), 404

        if not assigned_to_users:
            # Si no hay usuarios asignados, asignar al creador
            assigned_to_users = [{
                "_id": current_user['sub'],
                "username": current_user.get('username', 'Unknown'),
                "profile_picture": current_user.get('picture', '')
            }]

        # Obtener los datos completos de las tareas
        tasks = []
        for task_id in args.get('tasks', []):
            print("Task ID:", task_id)
            task = mongo.db.tasks.find_one({"_id": ObjectId(task_id)})
            if task:
                tasks.append({
                    "title": task.get("title"),
                    "description": task.get("description"),
                    "app": task.get("app"),
                    "status": task.get("status")
                })
            else:
                return jsonify({"message": f"Task with ID {task_id} not found."}), 404

        # Obtener los datos del epic
        epic_id = args.get('epic')
        epic_data = mongo.db.epics.find_one({"_id": ObjectId(epic_id)})
        if epic_data:
            epic_info = {
                "_id": str(epic_data["_id"]),
                "title": epic_data.get("title")
            }
        else:
            return jsonify({"message": f"Epic with ID {epic_id} not found."}), 404
        
        # Obtener los datos del equipo
        team_id = args.get('team')
        print("Received team data:", team_id)  
        if team_id and ObjectId.is_valid(team_id):
            team_data = mongo.db.teams.find_one({"_id": ObjectId(team_id)})
            if team_data:
                team_info = {
                    "_id": str(team_data["_id"]),
                    "name": team_data.get("name")  
                }
            else:
                return jsonify({"message": f"Team with ID {team_id} not found."}), 404
        else:
            team_info = None
        
        # Filtra los campos que se deben actualizar
        update_fields = {
            **args,
            'assigned_to': assigned_to_users,
            'tasks': tasks,
            'epic': epic_info,
            'team': team_info
        }

        # Solo actualiza los campos sin cambiar el título
        result = mongo.db.stories.update_one({"_id": ObjectId(story_id)}, {"$set": update_fields})
        if result.matched_count == 0:
            return jsonify({"message": "Story update failed."}), 500

        # Recupera la historia actualizada
        updated_story = mongo.db.stories.find_one({"_id": ObjectId(story_id)})
        if updated_story:
            updated_story["_id"] = str(updated_story["_id"])
            return jsonify(updated_story), 200
        else:
            return jsonify({"message": "Story update failed."}), 500

    except Exception as e:
        print(f"Exception: {e}")
        return jsonify({"error": str(e)}), 500