from flask import request, jsonify
from db import db

def register_routes(app):

    @app.route("/users", methods=["POST"])
    def create_user():
        data = request.json
        db.users.insert_one(data)
        return jsonify({"message": "User created"})

    @app.route("/users", methods=["GET"])
    def get_users():
        users = list(db.users.find({}, {"_id": 0}))
        return jsonify(users)