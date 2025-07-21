from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime
from fastapi import HTTPException
from models.company import Company
from .db import db

class CompanyService:
    collection = db.companies

    @staticmethod
    async def create_company(company: Company) -> Optional[Company]:
        """Create a new company"""
        try:
            # Check if company name already exists
            existing = await CompanyService.collection.find_one({"company_name": company.company_name})
            if existing:
                return None  # Company name already exists
            
            # Convert company to dict
            company_dict = company.model_dump()
            
            # Convert UUIDs to strings for MongoDB
            company_dict["company_id"] = str(company_dict["company_id"])
            
            # Set timestamps
            company_dict["created_at"] = datetime.utcnow()
            company_dict["updated_at"] = datetime.utcnow()
            
            # Insert into database
            result = await CompanyService.collection.insert_one(company_dict)
            if not result.inserted_id:
                raise HTTPException(status_code=500, detail="Failed to create company")
            
            # Convert the MongoDB document back to a Company model
            company_dict["_id"] = result.inserted_id
            return Company.model_validate(company_dict)
            
        except Exception as e:
            print(f"Error creating company: {e}")
            return None
    
    @staticmethod
    async def get_company(company_id: UUID) -> Optional[Company]:
        """Get a company by ID"""
        try:
            company_dict = await CompanyService.collection.find_one({"company_id": str(company_id)})
            if not company_dict:
                return None
            
            # Convert string UUID back to UUID object
            company_dict["company_id"] = UUID(company_dict["company_id"])
            return Company.model_validate(company_dict)
            
        except Exception as e:
            print(f"Error getting company: {e}")
            return None
    
    @staticmethod
    async def get_companies() -> List[Company]:
        """Get all companies"""
        try:
            companies = []
            async for company_dict in CompanyService.collection.find():
                # Convert string UUID back to UUID object
                company_dict["company_id"] = UUID(company_dict["company_id"])
                companies.append(Company.model_validate(company_dict))
            return companies
            
        except Exception as e:
            print(f"Error getting companies: {e}")
            return []
    
    @staticmethod
    async def update_company(company_id: UUID, company_update: Company) -> Optional[Company]:
        """Update a company"""
        try:
            # Prepare update data
            update_data = company_update.model_dump(exclude={"company_id", "created_at"})
            update_data["updated_at"] = datetime.utcnow()
            
            # Update in database
            result = await CompanyService.collection.find_one_and_update(
                {"company_id": str(company_id)},
                {"$set": update_data},
                return_document=True
            )
            
            if result:
                # Convert string UUID back to UUID object
                result["company_id"] = UUID(result["company_id"])
                return Company.model_validate(result)
            
            return None
            
        except Exception as e:
            print(f"Error updating company: {e}")
            return None
    
    @staticmethod
    async def delete_company(company_id: UUID) -> bool:
        """Delete a company"""
        try:
            result = await CompanyService.collection.delete_one({"company_id": str(company_id)})
            return result.deleted_count > 0
            
        except Exception as e:
            print(f"Error deleting company: {e}")
            return False
    
    @staticmethod
    async def get_company_by_name(company_name: str) -> Optional[Company]:
        """Get a company by name"""
        try:
            company_dict = await CompanyService.collection.find_one({"company_name": company_name})
            if not company_dict:
                return None
            
            # Convert string UUID back to UUID object
            company_dict["company_id"] = UUID(company_dict["company_id"])
            return Company.model_validate(company_dict)
            
        except Exception as e:
            print(f"Error getting company by name: {e}")
            return None
