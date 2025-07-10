#!/usr/bin/env python3
"""
VTO System Quick Start Script
Automates the setup and initialization of the VTO system
"""

import asyncio
import sys
import subprocess
import os
from pathlib import Path

def print_banner():
    print("="*60)
    print("  VTO MEETING TRANSCRIPTION SYSTEM - QUICK START")
    print("="*60)
    print()

def check_prerequisites():
    """Check if required services are available"""
    print("🔍 Checking prerequisites...")
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ required")
        return False
    print("✓ Python version OK")
    
    # Check if MongoDB is accessible (basic check)
    try:
        import pymongo
        client = pymongo.MongoClient("mongodb://localhost:27017/", serverSelectionTimeoutMS=2000)
        client.server_info()
        print("✓ MongoDB connection OK")
    except Exception:
        print("⚠️  MongoDB not accessible - ensure it's running on localhost:27017")
    
    # Check if Qdrant is accessible (basic check)
    try:
        import requests
        response = requests.get("http://localhost:6333/health", timeout=2)
        if response.status_code == 200:
            print("✓ Qdrant connection OK")
        else:
            print("⚠️  Qdrant not accessible - ensure it's running on localhost:6333")
    except Exception:
        print("⚠️  Qdrant not accessible - ensure it's running on localhost:6333")
    
    return True

def install_dependencies():
    """Install Python dependencies"""
    print("\n📦 Installing dependencies...")
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], 
                      check=True, capture_output=True)
        print("✓ Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        return False

def setup_environment():
    """Setup environment file if it doesn't exist"""
    print("\n⚙️  Setting up environment...")
    
    env_path = Path(".env")
    if not env_path.exists():
        env_content = """# VTO System Environment Configuration
MONGODB_URL=mongodb://localhost:27017/vto_db
QDRANT_URL=http://localhost:6333
SECRET_KEY=your-super-secret-key-change-this-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Optional: Redis for caching
REDIS_URL=redis://localhost:6379/0

# Optional: Logging level
LOG_LEVEL=INFO

# Optional: CORS settings
CORS_ORIGINS=["http://localhost:3000","http://localhost:5173"]
"""
        env_path.write_text(env_content)
        print("✓ Created .env file with default configuration")
        print("⚠️  Please update SECRET_KEY in .env file for production use")
    else:
        print("✓ Environment file already exists")

async def run_migration():
    """Run database migration"""
    print("\n🔄 Running database migration...")
    try:
        from vto_migration import VTOMigration
        migration = VTOMigration()
        result = await migration.run_full_migration()
        
        if result["success"]:
            print("✓ Database migration completed successfully")
            return True
        else:
            print(f"❌ Migration failed: {result.get('error', 'Unknown error')}")
            return False
    except Exception as e:
        print(f"❌ Migration failed: {str(e)}")
        return False

def create_admin_user():
    """Instructions for creating admin user"""
    print("\n👤 Admin User Setup:")
    print("1. Start the server (see instructions below)")
    print("2. Use the following endpoint to create an admin user:")
    print("   POST /auth/register-admin")
    print("   Body: {")
    print('     "employee_id": "admin-001",')
    print('     "name": "Admin User",')
    print('     "email": "admin@yourdomain.com",')
    print('     "password": "your-secure-password",')
    print('     "employee_role": "admin"')
    print("   }")

def start_server():
    """Start the FastAPI server"""
    print("\n🚀 Starting VTO API server...")
    print("Server will be available at: http://localhost:8000")
    print("API Documentation: http://localhost:8000/docs")
    print("Press Ctrl+C to stop the server")
    print()
    
    try:
        subprocess.run([
            sys.executable, "-m", "uvicorn", 
            "main:app", 
            "--reload", 
            "--host", "0.0.0.0", 
            "--port", "8000"
        ])
    except KeyboardInterrupt:
        print("\n👋 Server stopped")

def run_tests():
    """Run the test suite"""
    print("\n🧪 Running test suite...")
    try:
        subprocess.run([sys.executable, "test_vto_api.py"], check=True)
        print("✓ All tests passed")
    except subprocess.CalledProcessError:
        print("❌ Some tests failed - check output above")

def show_menu():
    """Show the main menu"""
    print("\nWhat would you like to do?")
    print("1. 🏃 Quick start (setup + migration + start server)")
    print("2. 📦 Install dependencies only")
    print("3. 🔄 Run migration only")
    print("4. 🚀 Start server only")
    print("5. 🧪 Run tests")
    print("6. 📊 Generate test data")
    print("7. ❓ Show help")
    print("8. 🚪 Exit")
    print()

def show_help():
    """Show help information"""
    print("""
VTO System Quick Start Help

Prerequisites:
- Python 3.8+
- MongoDB running on localhost:27017
- Qdrant running on localhost:6333 (optional but recommended)

Quick Start Steps:
1. Ensure MongoDB and Qdrant are running
2. Run this script and choose option 1 (Quick start)
3. Create an admin user via API
4. Start using the system!

Configuration:
- Edit .env file for custom settings
- Update CORS settings for frontend integration
- Change SECRET_KEY for production deployment

API Endpoints:
- Documentation: http://localhost:8000/docs
- Health check: http://localhost:8000/admin/system/health
- Migration status: http://localhost:8000/admin/migration/validate-vto

For more information, see README_VTO.md
""")

async def quick_start():
    """Run the complete quick start process"""
    print_banner()
    
    if not check_prerequisites():
        print("❌ Prerequisites check failed. Please address the issues above.")
        return
    
    if not install_dependencies():
        print("❌ Dependency installation failed.")
        return
    
    setup_environment()
    
    migration_success = await run_migration()
    if not migration_success:
        print("⚠️  Migration failed, but you can continue and try manual migration later.")
    
    create_admin_user()
    
    print("\n" + "="*60)
    print("✅ VTO SYSTEM SETUP COMPLETE!")
    print("="*60)
    print("Next steps:")
    print("1. Create an admin user (see instructions above)")
    print("2. Access the API documentation at http://localhost:8000/docs")
    print("3. Start building your VTO workflow!")
    print()
    
    input("Press Enter to start the server...")
    start_server()

async def main():
    """Main entry point"""
    if len(sys.argv) > 1:
        command = sys.argv[1]
        if command == "quick-start":
            await quick_start()
        elif command == "migration":
            await run_migration()
        elif command == "test":
            run_tests()
        elif command == "server":
            start_server()
        else:
            print(f"Unknown command: {command}")
            show_help()
        return
    
    # Interactive mode
    while True:
        show_menu()
        choice = input("Enter your choice (1-8): ").strip()
        
        if choice == "1":
            await quick_start()
            break
        elif choice == "2":
            install_dependencies()
        elif choice == "3":
            await run_migration()
        elif choice == "4":
            start_server()
            break
        elif choice == "5":
            run_tests()
        elif choice == "6":
            print("Generating test data...")
            subprocess.run([sys.executable, "test_vto_api.py", "generate-data"])
        elif choice == "7":
            show_help()
        elif choice == "8":
            print("👋 Goodbye!")
            break
        else:
            print("❌ Invalid choice. Please enter 1-8.")

if __name__ == "__main__":
    # Change to the script's directory
    os.chdir(Path(__file__).parent)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)
