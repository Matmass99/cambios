from flask import Blueprint, request, jsonify
from webargs import fields
from webargs.flaskparser import use_args
from bson import ObjectId
from app.db_connection import mongo

tasks = Blueprint('tasks', __name__)

# Validación para la creación de tareas
task_args = {
    'title': fields.Str(required=True),
    'description': fields.Str(required=True),
    'status': fields.Str(required=True),  
    'app': fields.Str(required=True),
}

# Validación para la actualización del status de una tarea
task_status_args = {
    'status': fields.Str(required=True),
}

def convert_objectid_to_str(document):
    """Convierte todos los ObjectId en un documento a strings."""
    if isinstance(document, dict):
        return {i: (str(j) if isinstance(j, ObjectId) else convert_objectid_to_str(j)) for i, j in document.items()}
    elif isinstance(document, list):
        return [convert_objectid_to_str(item) for item in document]
    return document

@tasks.route('/', methods=['POST'])
@use_args(task_args, location='json')
def create_task(args):
    
    try:
        # Normalizar el título
        normalized_title = args['title'].strip().lower()

        # Comprobar si ya existe una tarea con el mismo título normalizado
        existing_task = mongo.db.tasks.find_one({"title_normalized": normalized_title})
        if existing_task:
            return jsonify({"error": "A task with the same title already exists."}), 400
        
        # Insertar la nueva tarea
        result = mongo.db.tasks.insert_one(args)
        created_task = mongo.db.tasks.find_one({"_id": result.inserted_id})
        created_task["_id"] = str(created_task["_id"])  
        return jsonify(created_task), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@tasks.route('/<string:title>', methods=['PUT'])
@use_args(task_status_args, location='json')
def update_task_status(args, title):
    try:
        # Buscar la tarea por el título
        task = mongo.db.tasks.find_one({"title": title})
        if not task:
            return jsonify({"error": "Task not found"}), 404
        
        # Actualizar el estado de la tarea
        result = mongo.db.tasks.update_one({"title": title}, {"$set": {"status": args['status']}})
        if result.modified_count == 0:
            return jsonify({"error": "Failed to update task status"}), 500
        
        # Obtener la tarea actualizada
        updated_task = mongo.db.tasks.find_one({"title": title})
        updated_task["_id"] = str(updated_task["_id"]) 
        return jsonify(updated_task), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@tasks.route('/', methods=['GET'])
def get_all_tasks():
    try:
        tasks_list = mongo.db.tasks.find()  
        tasks_data = [convert_objectid_to_str(task) for task in tasks_list]
        return jsonify(tasks_data), 200
    except Exception as e:
        print(f"Exception: {e}")  
        return jsonify({"error": str(e)}), 500