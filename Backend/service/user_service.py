from typing import List, Optional, Dict
from uuid import UUID
from fastapi import HTTPException
from models.user import User
from .db import db
from passlib.hash import bcrypt
from datetime import datetime

class UserService:
    collection = db.users

    @staticmethod
    async def create_user(user: User) -> User:
        """Create a new user with hashed password"""
        # Convert user to dict
        user_dict = user.model_dump()
        
        # Hash the password
        user_dict["employee_password"] = bcrypt.hash(user.employee_password)
        
        # Set timestamps
        user_dict["created_at"] = datetime.utcnow()
        user_dict["updated_at"] = datetime.utcnow()
        
        # Convert UUIDs to strings for MongoDB
        user_dict["employee_id"] = str(user_dict["employee_id"])
        # Handle optional assigned_rocks
        if user_dict.get("assigned_rocks") is not None:
            user_dict["assigned_rocks"] = [str(rock) for rock in user_dict["assigned_rocks"]]
        else:
            user_dict["assigned_rocks"] = []
        
        # Insert into database
        result = await UserService.collection.insert_one(user_dict)
        if not result.inserted_id:
            raise HTTPException(status_code=500, detail="Failed to create user")
            
        # Convert the MongoDB document back to a User model
        user_dict["_id"] = result.inserted_id
        return User.model_validate(user_dict)

    @staticmethod
    async def get_user(user_id: UUID) -> Optional[User]:
        """Get a user by ID"""
        user_dict = await UserService.collection.find_one({"employee_id": str(user_id)})
        if not user_dict:
            return None
        # Convert string IDs to UUIDs
        user_dict["employee_id"] = UUID(user_dict["employee_id"])
        user_dict["assigned_rocks"] = [UUID(rock_id) for rock_id in user_dict.get("assigned_rocks", [])]
        return User.model_validate(user_dict)

    @staticmethod
    async def get_user_by_email(email: str) -> Optional[User]:
        """Get a user by email"""
        user_dict = await UserService.collection.find_one({"employee_email": email})
        if user_dict:
            # Convert string UUIDs back to UUID objects
            user_dict["employee_id"] = UUID(user_dict["employee_id"])
            user_dict["assigned_rocks"] = [UUID(rock) for rock in user_dict["assigned_rocks"]]
            return User.model_validate(user_dict)
        return None

    @staticmethod
    async def get_users(role: Optional[str] = None) -> List[User]:
        """Get all users, optionally filtered by role"""
        query = {"employee_role": role} if role else {}
        users = []
        async for user_dict in UserService.collection.find(query):
            users.append(User(**user_dict))
        return users

    @staticmethod
    async def update_user(user_id: UUID, user_update: User) -> Optional[User]:
        """Update a user"""
        update_data = user_update.model_dump(exclude={"id", "created_at", "employee_password"})
        update_data["updated_at"] = datetime.utcnow()
        await UserService.collection.update_one(
            {"employee_id": str(user_id)},
            {"$set": update_data}
        )
        return await UserService.get_user(user_id)

    @staticmethod
    async def update_name(user_id: UUID, name: str) -> Optional[User]:
        """Update a user's name"""
        result = await UserService.collection.find_one_and_update(
            {"employee_id": str(user_id)},
            {
                "$set": {
                    "employee_name": name,
                    "updated_at": datetime.utcnow()
                }
            },
            return_document=True
        )
        return User(**result) if result else None

    @staticmethod
    async def update_email(user_id: UUID, email: str) -> Optional[User]:
        """Update a user's email"""
        # Check if email is already taken
        existing = await UserService.get_user_by_email(email)
        if existing and str(existing.employee_id) != str(user_id):
            raise HTTPException(
                status_code=400,
                detail="Email is already in use"
            )

        result = await UserService.collection.find_one_and_update(
            {"employee_id": str(user_id)},
            {
                "$set": {
                    "employee_email": email,
                    "updated_at": datetime.utcnow()
                }
            },
            return_document=True
        )
        return User(**result) if result else None

    @staticmethod
    async def update_password(user_id: UUID, new_password: str) -> Optional[User]:
        """Update a user's password"""
        hashed_password = bcrypt.hash(new_password)
        result = await UserService.collection.find_one_and_update(
            {"employee_id": str(user_id)},
            {
                "$set": {
                    "employee_password": hashed_password,
                    "updated_at": datetime.utcnow()
                }
            },
            return_document=True
        )
        return User(**result) if result else None

    @staticmethod
    async def update_role(user_id: UUID, role: str) -> Optional[User]:
        """Update a user's role"""
        result = await UserService.collection.find_one_and_update(
            {"employee_id": str(user_id)},
            {
                "$set": {
                    "employee_role": role,
                    "updated_at": datetime.utcnow()
                }
            },
            return_document=True
        )
        return User(**result) if result else None

    @staticmethod
    async def delete_user(user_id: UUID) -> bool:
        """Delete a user"""
        result = await UserService.collection.delete_one({"employee_id": str(user_id)})
        return result.deleted_count > 0

    @staticmethod
    async def verify_password(user: User, password: str) -> bool:
        """Verify a user's password"""
        user_dict = await UserService.collection.find_one({"employee_id": str(user.employee_id)})
        if not user_dict:
            return False
        return bcrypt.verify(password, user_dict["employee_password"])

    @staticmethod
    async def assign_rock(user_id: UUID, rock_id: UUID) -> Optional[User]:
        """Assign a rock to a user"""
        result = await UserService.collection.find_one_and_update(
            {"employee_id": str(user_id)},
            {
                "$addToSet": {"assigned_rocks": str(rock_id)},
                "$set": {"updated_at": datetime.utcnow()}
            },
            return_document=True
        )
        return User(**result) if result else None

    @staticmethod
    async def unassign_rock(user_id: UUID, rock_id: UUID) -> Optional[User]:
        """Remove a rock assignment from a user"""
        result = await UserService.collection.find_one_and_update(
            {"employee_id": str(user_id)},
            {
                "$pull": {"assigned_rocks": str(rock_id)},
                "$set": {"updated_at": datetime.utcnow()}
            },
            return_document=True
        )
        return User(**result) if result else None

    @staticmethod
    async def get_users_by_rock(rock_id: UUID) -> List[User]:
        """Get all users assigned to a specific rock"""
        users = []
        async for user_dict in UserService.collection.find(
            {"assigned_rocks": str(rock_id)}
        ):
            users.append(User(**user_dict))
        return users

    @staticmethod
    async def get_user_profile(user_id: UUID) -> Optional[Dict]:
        """Get a user's profile information (excluding sensitive data)"""
        user = await UserService.get_user(user_id)
        if not user:
            return None
        
        return {
            "employee_id": str(user.employee_id),
            "employee_name": user.employee_name,
            "employee_email": user.employee_email,
            "employee_role": user.employee_role,
            "assigned_rocks": [str(rock_id) for rock_id in user.assigned_rocks]
        } 