import uuid
from passlib.context import CryptContext
from service.db import db

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_user_by_username(username: str):
    return db.users.find_one({"username": username})

def create_user(username: str, password: str, role: str):
    hashed_password = pwd_context.hash(password)
    user = {
        "uuid": str(uuid.uuid4()),
        "username": username,
        "hashed_password": hashed_password,
        "role": role
    }
    db.users.insert_one(user)
    return user
