"""
Base service with shared database connection
"""

from .db import db

class BaseService:
    """Base service class with database connection"""
    db = db
    rocks = db.rocks
    tasks = db.tasks
    users = db.users
    quarters = db.quarters 