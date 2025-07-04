import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI")
MONGODB_DBNAME = os.getenv("MONGODB_DBNAME", "audioTranscription")

if not MONGODB_URI:
    raise RuntimeError("MONGODB_URI is not set in the environment variables. Please set it in your .env file.")

client = MongoClient(MONGODB_URI)
db = client[MONGODB_DBNAME]
