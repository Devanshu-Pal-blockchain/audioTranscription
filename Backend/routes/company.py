from typing import List, Dict, Any, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Form
from pydantic import BaseModel
from models.company import Company
from models.user import User
from service.company_service import CompanyService
from service.user_service import UserService
from service.auth_service import get_current_user

router = APIRouter()

# Request models for creating company with facilitator
class CreateCompanyRequest(BaseModel):
    company_name: str
    facilitator_name: str
    facilitator_email: str
    facilitator_password: str
    facilitator_responsibilities: Optional[str] = None
    facilitator_code: Optional[str] = None
    facilitator_designation: Optional[str] = None

class CreateCompanyResponse(BaseModel):
    company: Dict[str, Any]
    facilitator: Dict[str, Any]
    message: str

# Admin-only dependency
def admin_required(current_user: User = Depends(get_current_user)):
    """Require admin role"""
    if current_user.employee_role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user

# Admin or facilitator access
def admin_or_facilitator_required(current_user: User = Depends(get_current_user)):
    """Require admin or facilitator role"""
    if current_user.employee_role not in ["admin", "facilitator"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin or Facilitator access required"
        )
    return current_user

@router.post("/companies", response_model=CreateCompanyResponse)
async def create_company_with_facilitator(
    request: CreateCompanyRequest,
    current_user: User = Depends(admin_required)
) -> CreateCompanyResponse:
    """Create a new company and its facilitator (Admin only)"""
    try:
        # Step 1: Create the company
        new_company = Company(company_name=request.company_name)
        created_company = await CompanyService.create_company(new_company)
        
        if not created_company:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Company name already exists or creation failed"
            )
        
        # Step 2: Create facilitator for this company
        facilitator_user = User(
            employee_name=request.facilitator_name,
            employee_email=request.facilitator_email,
            employee_password=request.facilitator_password,
            employee_role="facilitator",
            company_id=created_company.company_id,
            employee_responsibilities=request.facilitator_responsibilities,
            employee_code=request.facilitator_code,
            employee_designation=request.facilitator_designation
        )
        
        created_facilitator = await UserService.create_user(facilitator_user)
        
        if not created_facilitator:
            # Rollback: delete the company if facilitator creation fails
            await CompanyService.delete_company(created_company.company_id)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create facilitator. Company creation rolled back."
            )
        
        return CreateCompanyResponse(
            company=created_company.model_dump(),
            facilitator=created_facilitator.model_dump(),
            message=f"Company '{created_company.company_name}' and facilitator '{created_facilitator.employee_name}' created successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )

@router.get("/companies", response_model=List[Company])
async def list_companies(
    current_user: User = Depends(admin_required)
) -> List[Company]:
    """List all companies (Admin only)"""
    return await CompanyService.get_companies()

@router.get("/companies/{company_id}", response_model=Company)
async def get_company(
    company_id: UUID,
    current_user: User = Depends(get_current_user)
) -> Company:
    """Get a company by ID"""
    # Admin can view all companies, others can only view their own company
    if (current_user.employee_role not in ["admin", "facilitator"] and 
        current_user.company_id != company_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Can only view your own company"
        )
    
    company = await CompanyService.get_company(company_id)
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found"
        )
    return company

@router.put("/companies/{company_id}", response_model=Company)
async def update_company(
    company_id: UUID,
    company_update: Company,
    current_user: User = Depends(admin_required)
) -> Company:
    """Update a company (Admin only)"""
    updated_company = await CompanyService.update_company(company_id, company_update)
    if not updated_company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found"
        )
    return updated_company

@router.delete("/companies/{company_id}")
async def delete_company(
    company_id: UUID,
    current_user: User = Depends(admin_required)
) -> dict:
    """Delete a company (Admin only)"""
    success = await CompanyService.delete_company(company_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found"
        )
    return {"message": "Company deleted successfully"}

@router.get("/companies/{company_id}/facilitator", response_model=User)
async def get_company_facilitator(
    company_id: UUID,
    current_user: User = Depends(get_current_user)
) -> User:
    """Get the facilitator for a company"""
    # Admin can view all, others can only view their own company's facilitator
    if (current_user.employee_role not in ["admin", "facilitator"] and 
        current_user.company_id != company_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Can only view your own company's facilitator"
        )
    
    # Get company to verify it exists
    company = await CompanyService.get_company(company_id)
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found"
        )
    
    # Get facilitator for this company
    users = await UserService.get_users("facilitator")
    facilitator = None
    for user in users:
        if user.company_id == company_id:
            facilitator = user
            break
    
    if not facilitator:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No facilitator found for this company"
        )
    
    return facilitator

@router.get("/companies/{company_id}/employees", response_model=List[User])
async def get_company_employees(
    company_id: UUID,
    current_user: User = Depends(get_current_user)
) -> List[User]:
    """Get all employees for a company"""
    # Admin can view all, facilitators or employees of this company can view
    if (current_user.employee_role not in ["admin", "facilitator"] and 
        current_user.company_id != company_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Can only view your own company's employees"
        )
    
    # Get company to verify it exists
    company = await CompanyService.get_company(company_id)
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found"
        )
    
    # Get all employees for this company
    all_users = await UserService.get_users()
    company_employees = [user for user in all_users if user.company_id == company_id]
    
    return company_employees
