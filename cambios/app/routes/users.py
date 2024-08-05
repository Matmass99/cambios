from flask import Blueprint, request, jsonify
from app.db_connection import mongo
@users.route('/', methods=['GET'])
def get_users():
    try:
        users = mongo.db.users.find({})
        user_list = []
        for user in users:
            user_list.append({
                "_id": str(user['_id']),
                "username": user.get('username', 'Unknown'),
                "profile_picture": user.get('picture', '')
            })
        return jsonify(user_list), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500