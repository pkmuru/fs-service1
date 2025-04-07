from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import EmailStr
from typing import Dict, List, Optional, Any
import os
import logging
import time
from datetime import datetime

# Import from our modules
from models import ServiceResponse
from graph_api import get_access_token, get_booking_businesses, get_staff_members_for_business, get_services_for_business

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="Microsoft Booking API Service")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Simple in-memory cache implementation
class InMemoryCache:
    def __init__(self):
        self.cache = {}
        self.default_expiry = 3600  # 1 hour in seconds
    
    def get(self, key: str) -> Optional[Any]:
        """Get data from cache if it exists and hasn't expired"""
        if key not in self.cache:
            return None
        
        item = self.cache[key]
        if item["expires_at"] < time.time():
            # Item has expired, remove it
            del self.cache[key]
            return None
        
        return item["data"]
    
    def set(self, key: str, data: Any, expire_seconds: int = None) -> None:
        """Set data in cache with expiration"""
        if expire_seconds is None:
            expire_seconds = self.default_expiry
        
        self.cache[key] = {
            "data": data,
            "expires_at": time.time() + expire_seconds
        }
    
    def clear_expired(self) -> None:
        """Clear expired items from cache"""
        now = time.time()
        expired_keys = [k for k, v in self.cache.items() if v["expires_at"] < now]
        for key in expired_keys:
            del self.cache[key]

# Initialize cache
cache = InMemoryCache()

# Cache helpers
def get_cache_key(prefix: str, identifier: str) -> str:
    """Generate a cache key"""
    return f"{prefix}:{identifier}"

def get_from_cache(key: str) -> Optional[Any]:
    """Get data from cache"""
    return cache.get(key)

def set_in_cache(key: str, data: Any, expire_seconds: int = None) -> None:
    """Set data in cache with expiration"""
    cache.set(key, data, expire_seconds)

# API endpoints
@app.get("/")
async def root():
    return {"message": "Microsoft Booking API Service"}

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    # Clear expired cache items on health check
    cache.clear_expired()
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "cache_size": len(cache.cache)
    }

@app.get("/api/booking/businesses")
async def get_businesses(token: str = Depends(get_access_token)):
    """Get all booking businesses"""
    cache_key = get_cache_key("businesses", "all")
    cached_data = get_from_cache(cache_key)
    
    if cached_data:
        logger.info("Returning businesses from cache")
        return cached_data
    
    data = await get_booking_businesses(token)
    set_in_cache(cache_key, data)
    return data

@app.get("/api/booking/staff")
async def get_staff_members(business_id: Optional[str] = None, token: str = Depends(get_access_token)):
    """Get all staff members, optionally filtered by business ID"""
    cache_key = get_cache_key("staff", business_id or "all")
    cached_data = get_from_cache(cache_key)
    
    if cached_data:
        logger.info("Returning staff members from cache")
        return cached_data
    
    # If no business ID provided, get all businesses first
    if not business_id:
        businesses_response = await get_businesses(token)
        businesses = businesses_response.get("value", [])
        
        all_staff = []
        for business in businesses:
            business_id = business["id"]
            try:
                staff_data = await get_staff_members_for_business(business_id, token)
                # Add business ID to each staff member for reference
                for staff in staff_data.get("value", []):
                    staff["businessId"] = business_id
                all_staff.extend(staff_data.get("value", []))
            except HTTPException as e:
                logger.warning(f"Failed to fetch staff for business {business_id}: {e.detail}")
        
        result = {"value": all_staff}
        set_in_cache(cache_key, result)
        return result
    
    # If business ID is provided, get staff for that business
    data = await get_staff_members_for_business(business_id, token)
    set_in_cache(cache_key, data)
    return data

@app.get("/api/booking/services")
async def get_services(business_id: Optional[str] = None, token: str = Depends(get_access_token)):
    """Get all services, optionally filtered by business ID"""
    cache_key = get_cache_key("services", business_id or "all")
    cached_data = get_from_cache(cache_key)
    
    if cached_data:
        logger.info("Returning services from cache")
        return cached_data
    
    # If no business ID provided, get all businesses first
    if not business_id:
        businesses_response = await get_businesses(token)
        businesses = businesses_response.get("value", [])
        
        all_services = []
        for business in businesses:
            business_id = business["id"]
            try:
                services_data = await get_services_for_business(business_id, token)
                # Add business ID to each service for reference
                for service in services_data.get("value", []):
                    service["businessId"] = business_id
                all_services.extend(services_data.get("value", []))
            except HTTPException as e:
                logger.warning(f"Failed to fetch services for business {business_id}: {e.detail}")
        
        result = {"value": all_services}
        set_in_cache(cache_key, result)
        return result
    
    # If business ID is provided, get services for that business
    data = await get_services_for_business(business_id, token)
    set_in_cache(cache_key, data)
    return data

@app.get("/api/staff/{email}/services", response_model=ServiceResponse)
async def get_staff_services_by_email(email: EmailStr, token: str = Depends(get_access_token)):
    """
    Get services for a staff member by email, grouped by business
    """
    cache_key = get_cache_key("staff_services", email)
    cached_data = get_from_cache(cache_key)
    
    if cached_data:
        logger.info(f"Returning staff services from cache for {email}")
        return cached_data
    
    # Get all staff members
    staff_response = await get_staff_members(token=token)
    staff_members = staff_response.get("value", [])
    
    # Find the staff member by email
    staff_member = None
    for staff in staff_members:
        if staff.get("emailAddress", "").lower() == email.lower():
            staff_member = staff
            break
    
    if not staff_member:
        raise HTTPException(status_code=404, detail=f"Staff member with email {email} not found")
    
    staff_id = staff_member["id"]
    
    # Get all services
    services_response = await get_services(token=token)
    all_services = services_response.get("value", [])
    
    # Filter services for this staff member
    staff_services = []
    for service in all_services:
        staff_member_ids = service.get("staffMemberIds", [])
        if staff_id in staff_member_ids:
            staff_services.append(service)
    
    # Get all businesses
    businesses_response = await get_businesses(token=token)
    businesses = {b["id"]: b for b in businesses_response.get("value", [])}
    
    # Group services by business
    services_by_business = {}
    for service in staff_services:
        business_id = service.get("businessId")
        if business_id not in services_by_business:
            services_by_business[business_id] = []
        services_by_business[business_id].append(service)
    
    # Format the response
    services_grouped = []
    for business_id, services in services_by_business.items():
        business = businesses.get(business_id, {"displayName": "Unknown Business"})
        services_grouped.append({
            "businessId": business_id,
            "businessName": business.get("displayName"),
            "services": services
        })
    
    result = {
        "staffMember": staff_member,
        "servicesByBusiness": services_grouped
    }
    
    # Cache the result
    set_in_cache(cache_key, result, 1800)  # Cache for 30 minutes
    
    return result

# Run the application with uvicorn
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=int(os.getenv("PORT", "8000")), reload=True)

