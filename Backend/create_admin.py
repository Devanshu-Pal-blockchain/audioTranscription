#!/usr/bin/env python3
"""
Script to create the first admin user for the system
Run this once to create the initial admin account
"""

import asyncio
import sys
import os

# Add the Backend directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models.user import User
from service.user_service import UserService

async def create_admin():
    """Create the initial admin user"""
    
    print("Creating initial admin user...")
    
    # Create admin user
    admin_user = User(
        employee_name="System Administrator",
        employee_email="admin@commetrix.com",
        employee_password="admin123",  # Change this in production!
        employee_role="admin",
        employee_responsibilities="System administration and company management",
        employee_designation="System Admin"
    )
    
    try:
        created_admin = await UserService.create_user(admin_user)
        
        if created_admin:
            print("✅ Admin user created successfully!")
            print(f"   Email: {created_admin.employee_email}")
            print(f"   Password: admin123")
            print(f"   Role: {created_admin.employee_role}")
            print(f"   ID: {created_admin.employee_id}")
            print("\n⚠️  IMPORTANT: Change the admin password after first login!")
        else:
            print("❌ Failed to create admin user (email might already exist)")
            
    except Exception as e:
        print(f"❌ Error creating admin user: {e}")

if __name__ == "__main__":
    asyncio.run(create_admin())
