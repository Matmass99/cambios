import os
from flask import Blueprint, request, Flask, jsonify

from app.services.mongoHelper import MongoHelper

def convert_objectid_to_str(document):
    """Convierte todos los ObjectId en un documento a strings."""
    if isinstance(document, dict):
        return {i: (str(j) if isinstance(j, ObjectId) else convert_objectid_to_str(j)) for i, j in document.items()}
    elif isinstance(document, list):
        return [convert_objectid_to_str(item) for item in document]
    return document

@teams.route('/', methods=['GET'])
def get_all_teams():
    try:
        mongo_helper = MongoHelper() 
        teams_list = mongo_helper.astra.db.teams.find()  
        teams_data = [convert_objectid_to_str(team) for team in teams_list]
        return jsonify(teams_data), 200
    except Exception as e:
        print(f"Exception: {e}")  
        return jsonify({"error": str(e)}), 500