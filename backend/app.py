from flask import Flask
from routes import register_routes
from db import init_db

app = Flask(__name__)

init_db()

register_routes(app)

if __name__ == "__main__":
    app.run(debug=True)     # used for local dev 