import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from bson.codec_options import CodecOptions
from uuid import UUID

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
MONGODB_DBNAME = os.getenv("MONGODB_DBNAME", "audioTranscription")

if not MONGODB_URI:
    raise RuntimeError("MONGODB_URI is not set in the environment variables. Please set it in your .env file.")

# Configure client with UUID support
client = AsyncIOMotorClient(MONGODB_URI, uuidRepresentation="standard")
db = client[MONGODB_DBNAME]
