from pydantic import BaseModel, EmailStr
from typing import List, Optional

class StaffMember(BaseModel):
    id: str
    displayName: str
    emailAddress: EmailStr
    role: str
    useBusinessHours: bool
    businessId: Optional[str] = None
    
class BookingBusiness(BaseModel):
    id: str
    displayName: str
    businessType: str
    phone: str
    email: EmailStr
    webSiteUrl: Optional[str] = None
    
class BookingService(BaseModel):
    id: str
    displayName: str
    description: Optional[str] = None
    defaultDuration: int
    businessId: str
    staffMemberIds: Optional[List[str]] = None
    
class ServicesByBusiness(BaseModel):
    businessId: str
    businessName: str
    services: List[BookingService]
    
class ServiceResponse(BaseModel):
    staffMember: StaffMember
    servicesByBusiness: List[ServicesByBusiness]

