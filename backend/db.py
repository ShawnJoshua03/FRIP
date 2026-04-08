from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()

client = None
db = None

def init_db():
    global client, db
    client = MongoClient(os.getenv("MONGO_URI"))
    db = client.get_database()