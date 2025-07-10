"""
VTO Database Migration Script
Handles the migration from EOS-centric to comprehensive VTO system
"""

import asyncio
from typing import Dict, List, Optional
from uuid import UUID, uuid4
from datetime import datetime
from service.db import get_database
from models.meeting import Meeting
from models.issue import Issue
from models.solution import Solution
from models.milestone import Milestone
from models.time_slot import TimeSlot
from models.rock import Rock
from models.user import User
from models.quarter import Quarter

class VTOMigration:
    def __init__(self):
        self.db = None
        self.migration_log = []
    
    async def initialize(self):
        """Initialize database connection"""
        self.db = await get_database()
        self.log("Database connection initialized")
    
    def log(self, message: str):
        """Log migration steps"""
        timestamp = datetime.now().isoformat()
        log_entry = f"[{timestamp}] {message}"
        self.migration_log.append(log_entry)
        print(log_entry)
    
    async def create_collections(self):
        """Create new collections for VTO system"""
        collections_to_create = [
            "meetings",
            "issues", 
            "solutions",
            "milestones",
            "time_slots",
            "todos",  # New parallel entity to rocks
            "meeting_sessions",  # For session management
            "audio_chunks",  # For pause/resume chunks
            "analytics_cache",
            "rag_embeddings",
            "vto_settings"
        ]
        
        existing_collections = await self.db.list_collection_names()
        
        for collection_name in collections_to_create:
            if collection_name not in existing_collections:
                await self.db.create_collection(collection_name)
                self.log(f"Created collection: {collection_name}")
            else:
                self.log(f"Collection already exists: {collection_name}")
    
    async def create_indexes(self):
        """Create indexes for optimal query performance"""
        indexes_config = {
            "meetings": [
                ("meeting_type", 1),
                ("quarter_id", 1),
                ("date", -1),
                ("attendees", 1),
                ("created_by", 1),
                ("created_at", -1)
            ],
            "issues": [
                ("status", 1),  # Simplified to open/resolved only
                ("mentioned_by", 1),
                ("meeting_id", 1),
                ("created_at", -1),
                ("resolved_at", 1)
            ],
            "solutions": [
                ("status", 1),
                ("issue_id", 1),
                ("assigned_to", 1),
                ("created_by", 1),
                ("meeting_id", 1),
                ("created_at", -1),
                ("implementation_date", 1)
            ],
            "milestones": [
                ("status", 1),
                ("parent_rock_id", 1),  # Only rocks have milestones
                ("due_date", 1),
                ("created_at", -1)
            ],
            "todos": [  # New collection for parallel 1-14 day tasks
                ("status", 1),
                ("owner_id", 1),
                ("parent_rock_id", 1),  # Optional parent rock reference
                ("deadline", 1),
                ("meeting_id", 1),
                ("created_at", -1)
            ],
            "meeting_sessions": [  # Session management
                ("meeting_id", 1),
                ("session_number", 1),
                ("status", 1),
                ("created_at", -1)
            ],
            "audio_chunks": [  # Audio chunk management
                ("session_id", 1),
                ("chunk_number", 1),
                ("created_at", -1)
            ],
            "time_slots": [
                ("meeting_id", 1),
                ("speaker_id", 1),
                ("start_time", 1),
                ("end_time", 1),
                ("topics", 1)
            ],
            "rocks": [
                ("rock_type", 1),
                ("quarter_id", 1),
                ("assigned_to_id", 1),
                ("status", 1),
                ("percentage_completion", 1),
                ("created_at", -1)
            ],
            "users": [
                ("employee_id", 1),
                ("employee_role", 1),
                ("email", 1)
            ],
            "quarters": [
                ("start_date", 1),
                ("end_date", 1),
                ("is_current", 1)
            ]
        }
        
        for collection_name, indexes in indexes_config.items():
            collection = self.db[collection_name]
            for index_spec in indexes:
                try:
                    await collection.create_index([index_spec])
                    self.log(f"Created index on {collection_name}.{index_spec[0]}")
                except Exception as e:
                    self.log(f"Index creation failed for {collection_name}.{index_spec[0]}: {str(e)}")
    
    async def migrate_existing_rocks(self):
        """Enhance existing rocks with VTO fields"""
        rocks_collection = self.db["rocks"]
        
        # Find rocks missing VTO fields
        rocks_to_update = await rocks_collection.find({
            "$or": [
                {"rock_type": {"$exists": False}},
                {"measurable_success": {"$exists": False}},
                {"smart_objective": {"$exists": True}}  # Remove smart_objective
            ]
        }).to_list(length=None)
        
        updated_count = 0
        for rock in rocks_to_update:
            update_fields = {}
            unset_fields = {}
            
            # Set default rock_type if missing
            if "rock_type" not in rock:
                update_fields["rock_type"] = "company"  # Default to company rock
            
            # Set default measurable_success if missing
            if "measurable_success" not in rock:
                # Use smart_objective if it exists, otherwise create default
                if "smart_objective" in rock:
                    update_fields["measurable_success"] = rock["smart_objective"]
                else:
                    update_fields["measurable_success"] = f"Complete {rock.get('rock_name', 'rock')} successfully"
            
            # Remove smart_objective field (rocks are inherently SMART)
            if "smart_objective" in rock:
                unset_fields["smart_objective"] = ""
            
            # Remove percentage_completion if stored (should be calculated)
            if "percentage_completion" in rock:
                unset_fields["percentage_completion"] = ""
            
            # Add other VTO fields with defaults
            if "owner" not in rock:
                update_fields["owner"] = rock.get("assigned_to_name", "")
            
            if "milestones" not in rock:
                update_fields["milestones"] = []
            
            # Update the rock
            update_doc = {}
            if update_fields:
                update_doc["$set"] = update_fields
            if unset_fields:
                update_doc["$unset"] = unset_fields
            
            if update_doc:
                await rocks_collection.update_one(
                    {"_id": rock["_id"]},
                    {"$set": update_fields}
                )
                updated_count += 1
        
        self.log(f"Updated {updated_count} rocks with VTO fields")
    
    async def migrate_existing_users(self):
        """Enhance existing users with VTO fields"""
        users_collection = self.db["users"]
        
        # Find users missing VTO fields
        users_to_update = await users_collection.find({
            "$or": [
                {"annual_rocks": {"$exists": False}},
                {"company_rocks": {"$exists": False}},
                {"individual_rocks": {"$exists": False}},
                {"employee_role": "admin"}  # Convert admin to facilitator
            ]
        }).to_list(length=None)
        
        updated_count = 0
        for user in users_to_update:
            update_fields = {}
            
            # Convert admin role to facilitator
            if user.get("employee_role") == "admin":
                update_fields["employee_role"] = "facilitator"
            
            # Add VTO rock tracking fields
            if "annual_rocks" not in user:
                update_fields["annual_rocks"] = []
            
            if "company_rocks" not in user:
                update_fields["company_rocks"] = []
            
            if "individual_rocks" not in user:
                update_fields["individual_rocks"] = []
            
            # Add VTO permissions based on role
            role = user.get("employee_role", "employee")
            if role == "admin":  # Convert to facilitator
                role = "facilitator"
                
            if "vto_permissions" not in user:
                update_fields["vto_permissions"] = {
                    "can_create_meetings": role == "facilitator",
                    "can_manage_rocks": role == "facilitator",
                    "can_view_analytics": True,
                    "can_access_all_quarters": role == "facilitator"
                }
            
            if update_fields:
                await users_collection.update_one(
                    {"_id": user["_id"]},
                    {"$set": update_fields}
                )
                updated_count += 1
        
        self.log(f"Updated {updated_count} users with VTO fields")
    
    async def create_sample_data(self):
        """Create sample VTO data for demonstration"""
        # Create sample meeting types configuration
        vto_settings = {
            "_id": "meeting_types_config",
            "meeting_types": {
                "yearly": {
                    "name": "Yearly Planning",
                    "description": "Annual vision and planning sessions",
                    "typical_duration": 480,  # 8 hours
                    "required_participants": ["leadership"],
                    "agenda_template": [
                        "Review previous year",
                        "Set annual vision",
                        "Define annual rocks",
                        "Quarterly planning"
                    ]
                },
                "quarterly": {
                    "name": "Quarterly Planning",
                    "description": "Quarterly rock setting and review",
                    "typical_duration": 240,  # 4 hours
                    "required_participants": ["team_leads"],
                    "agenda_template": [
                        "Previous quarter review",
                        "Rock completion analysis",
                        "New quarter rock setting",
                        "Issue identification"
                    ]
                },
                "weekly": {
                    "name": "Weekly L10",
                    "description": "Weekly Level 10 meetings",
                    "typical_duration": 90,  # 90 minutes
                    "required_participants": ["team"],
                    "agenda_template": [
                        "Scorecard review",
                        "Rock updates", 
                        "Issues list",
                        "IDS session",
                        "Action items"
                    ]
                }
            },
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        await self.db["vto_settings"].replace_one(
            {"_id": "meeting_types_config"},
            vto_settings,
            upsert=True
        )
        
        self.log("Created VTO settings and meeting type configurations")
    
    async def setup_rag_collections(self):
        """Setup collections for enhanced RAG functionality"""
        # Create embeddings collection with proper schema
        rag_embeddings_schema = {
            "_id": "schema_definition",
            "fields": {
                "content_id": "UUID",
                "content_type": "string",  # meeting, rock, issue, solution, milestone
                "content_text": "string",
                "embedding_vector": "array",
                "metadata": "object",
                "indexed_at": "datetime",
                "user_access": "array"  # List of user IDs who can access this content
            },
            "indexes": [
                {"content_id": 1},
                {"content_type": 1},
                {"indexed_at": -1},
                {"user_access": 1}
            ]
        }
        
        await self.db["rag_embeddings"].replace_one(
            {"_id": "schema_definition"},
            rag_embeddings_schema,
            upsert=True
        )
        
        self.log("Setup RAG embeddings collection schema")
    
    async def validate_migration(self):
        """Validate the migration was successful"""
        validation_results = {}
        
        # Check all collections exist
        collections = await self.db.list_collection_names()
        required_collections = ["meetings", "issues", "solutions", "milestones", "time_slots"]
        
        validation_results["collections"] = {
            "required": required_collections,
            "existing": [c for c in required_collections if c in collections],
            "missing": [c for c in required_collections if c not in collections]
        }
        
        # Check indexes
        validation_results["indexes"] = {}
        for collection_name in required_collections:
            if collection_name in collections:
                indexes = await self.db[collection_name].list_indexes().to_list(length=None)
                validation_results["indexes"][collection_name] = len(indexes)
        
        # Check data migration
        validation_results["data_migration"] = {
            "rocks_with_vto_fields": await self.db["rocks"].count_documents({"rock_type": {"$exists": True}}),
            "users_with_vto_fields": await self.db["users"].count_documents({"annual_rocks": {"$exists": True}})
        }
        
        self.log(f"Migration validation results: {validation_results}")
        return validation_results
    
    async def run_full_migration(self):
        """Run the complete VTO migration"""
        self.log("Starting VTO system migration...")
        
        try:
            await self.initialize()
            await self.create_collections()
            await self.create_indexes()
            await self.migrate_existing_rocks()
            await self.migrate_existing_users()
            await self.create_sample_data()
            await self.setup_rag_collections()
            
            validation_results = await self.validate_migration()
            
            self.log("VTO migration completed successfully!")
            return {
                "success": True,
                "migration_log": self.migration_log,
                "validation_results": validation_results
            }
            
        except Exception as e:
            self.log(f"Migration failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "migration_log": self.migration_log
            }

async def run_migration():
    """Entry point for running the VTO migration"""
    migration = VTOMigration()
    return await migration.run_full_migration()

if __name__ == "__main__":
    # Run migration when script is executed directly
    result = asyncio.run(run_migration())
    print("\n" + "="*50)
    print("MIGRATION SUMMARY")
    print("="*50)
    print(f"Success: {result['success']}")
    if not result['success']:
        print(f"Error: {result['error']}")
    print(f"Total steps: {len(result['migration_log'])}")
    print("="*50)
