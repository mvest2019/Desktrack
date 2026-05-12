# mongo.py — MongoDB connection
from pymongo import MongoClient, DESCENDING
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).parent / ".env")

# Matches your .env variable names: MONGODB_URL and MONGODB_DB_NAME
MONGO_URL = os.getenv("MONGODB_URL")
MONGO_DB  = os.getenv("MONGODB_DB_NAME", "ai_assistant")

if not MONGO_URL:
    raise ValueError("MONGODB_URL is not set in your .env file")

mongo_client = MongoClient(MONGO_URL)
mongo_db = mongo_client[MONGO_DB]
raw_samples_collection = mongo_db["raw_samples"]

# Create indexes for fast lookups
# One document per user — user_id is unique
def create_indexes():
    try:
        raw_samples_collection.create_index([("user_id", DESCENDING)], unique=True)
        print("MongoDB indexes created")
    except Exception as e:
        print(f"MongoDB index warning: {e}")

create_indexes()

def get_raw_samples():
    return raw_samples_collection
