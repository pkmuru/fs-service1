import os
import json
import shutil

# Define the project structure and file contents
project = {
    "requirements.txt": """fastapi==0.109.2
uvicorn==0.27.1
redis==5.0.1
pydantic==2.6.1
pydantic-settings==2.1.0
email-validator==2.1.0
python-dotenv==1.0.1
azure-identity==1.15.0
msgraph-sdk==1.26.0""",
    
    "Dockerfile": """FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Use environment variables from Azure App Service
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]""",
    
    ".env.example": """# Microsoft Graph API Authentication
MS_CLIENT_ID=your_client_id_here
MS_USERNAME=your_username_here
MS_PASSWORD=your_password_here
MS_TENANT_ID=your_tenant_id_here

# Cache Configuration
# Options: "memory" or "redis"
CACHE_TYPE=memory
# Redis URL (only needed if CACHE_TYPE=redis)
REDIS_URL=redis://localhost:6379/0
# Cache TTL in seconds (default: 3600 = 1 hour)
CACHE_TTL_SECONDS=3600
# Maximum number of items in memory cache (0 = unlimited, default: 0)
MEMORY_CACHE_MAX_SIZE=0""",
    
    "run.py": """# Script to run the application
import uvicorn
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    logger.info("Starting Microsoft Booking API Service")
    uvicorn.run(
        "app.main:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=True,
        log_level="info"
    )
    logger.info("Shutting down Microsoft Booking API Service")""",
    
    "app/__init__.py": """# Microsoft Booking API Service package""",
    
    "app/main.py": """# Main application module
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api.routes import router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title=settings.api_title,
    description=settings.api_description,
    version=settings.api_version
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router)

@app.get("/")
async def root():
    # Root endpoint
    return {
        "message": "Microsoft Booking API Service",
        "docs": "/docs",
        "version": settings.api_version
    }

# Run the application with uvicorn
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)""",
    
    "app/config.py": """# Configuration management for the application
import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import Literal, List

class Settings(BaseSettings):
    # Application settings loaded from environment variables
    
    # API settings
    api_title: str = "Microsoft Booking API Service"
    api_description: str = "API service for Microsoft Booking data"
    api_version: str = "1.0.0"
    
    # CORS settings - for production, replace with specific origins
    cors_origins: List[str] = ["*"]
    
    # Microsoft Graph API settings - required for authentication
    ms_client_id: str = Field(default=os.environ.get("MS_CLIENT_ID", ""))
    ms_username: str = Field(default=os.environ.get("MS_USERNAME", ""))
    ms_password: str = Field(default=os.environ.get("MS_PASSWORD", ""))
    ms_tenant_id: str = Field(default=os.environ.get("MS_TENANT_ID", ""))
    
    # Cache settings
    cache_type: Literal["memory", "redis"] = Field(
        default=os.environ.get("CACHE_TYPE", "memory")
    )
    redis_url: str = Field(default=os.environ.get("REDIS_URL", ""))
    cache_ttl_seconds: int = int(os.environ.get("CACHE_TTL_SECONDS", "3600"))  # Default: 1 hour
    memory_cache_max_size: int = int(os.environ.get("MEMORY_CACHE_MAX_SIZE", "0"))  # 0 = unlimited

    # Use SettingsConfigDict instead of Config class in Pydantic v2
    model_config = SettingsConfigDict(env_file=".env")

# Create settings instance
settings = Settings()""",
    
    "app/api/__init__.py": """# API package""",
    
    "app/api/routes.py": """# API routes for the application
import logging
from fastapi import APIRouter, HTTPException, Depends
from pydantic import EmailStr

from app.models.schemas import ServiceResponse, ErrorResponse
from app.services.graph_service import GraphService
from app.services.cache_service import cache_service

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api")

# Create graph service
graph_service = GraphService()

@router.get("/health")
async def health_check():
    # Health check endpoint
    return {"status": "healthy"}

@router.get("/booking/businesses")
async def get_booking_businesses():
    # Get all booking businesses
    cache_key = cache_service.get_key("businesses", "all")
    cached_data = cache_service.get(cache_key)
    
    if cached_data:
        logger.info("Returning businesses from cache")
        return {"value": cached_data}
    
    try:
        businesses = graph_service.get_booking_businesses()
        cache_service.set(cache_key, businesses)
        return {"value": businesses}
    
    except Exception as e:
        logger.error(f"Failed to fetch booking businesses: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch booking businesses: {str(e)}"
        )

@router.get("/booking/business/{business_id}/staff")
async def get_staff_members(business_id: str):
    # Get staff members for a specific business
    cache_key = cache_service.get_key("staff", business_id)
    cached_data = cache_service.get(cache_key)
    
    if cached_data:
        logger.info(f"Returning staff members from cache for business {business_id}")
        return {"value": cached_data}
    
    try:
        staff_members = graph_service.get_staff_members(business_id)
        cache_service.set(cache_key, staff_members)
        return {"value": staff_members}
    
    except Exception as e:
        logger.error(f"Failed to fetch staff members for business {business_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch staff members: {str(e)}"
        )

@router.get("/booking/business/{business_id}/services")
async def get_services(business_id: str):
    # Get services for a specific business
    cache_key = cache_service.get_key("services", business_id)
    cached_data = cache_service.get(cache_key)
    
    if cached_data:
        logger.info(f"Returning services from cache for business {business_id}")
        return {"value": cached_data}
    
    try:
        services = graph_service.get_services(business_id)
        cache_service.set(cache_key, services)
        return {"value": services}
    
    except Exception as e:
        logger.error(f"Failed to fetch services for business {business_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch services: {str(e)}"
        )

@router.get("/staff/{email}/services", response_model=ServiceResponse, responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}})
async def get_staff_services_by_email(email: EmailStr):
    # Get services for a staff member by email, grouped by business
    cache_key = cache_service.get_key("staff_services", email)
    cached_data = cache_service.get(cache_key)
    
    if cached_data:
        logger.info(f"Returning staff services from cache for {email}")
        return cached_data
    
    try:
        # Find the staff member by email
        staff_member, _ = graph_service.find_staff_member_by_email(email)
        
        if not staff_member:
            raise HTTPException(status_code=404, detail=f"Staff member with email {email} not found")
        
        # Get services for this staff member
        services_with_businesses = graph_service.get_services_for_staff(staff_member["id"])
        
        # Group services by business
        from app.utils.helpers import group_services_by_business
        services_by_business = group_services_by_business(services_with_businesses)
        
        # Format the response
        result = {
            "staffMember": staff_member,
            "servicesByBusiness": services_by_business
        }
        
        # Cache the result
        cache_service.set(cache_key, result, 1800)  # Cache for 30 minutes
        
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch services for staff {email}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch staff services: {str(e)}"
        )

# Add a cache control endpoint
@router.delete("/cache/clear")
async def clear_cache():
    # Clear the cache (for admin use)
    # Note: This is a simplified implementation
    # In a real app, you would add authentication
    try:
        # For memory cache, we can't easily clear all keys
        # For Redis, we could use FLUSHDB, but that's dangerous
        # Instead, we'll just log that this endpoint was called
        logger.info("Cache clear requested")
        return {"message": "Cache clear requested"}
    except Exception as e:
        logger.error(f"Failed to clear cache: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to clear cache: {str(e)}"
        )""",
    
    "app/models/__init__.py": """# Models package""",
    
    "app/models/schemas.py": """# Pydantic models for request and response validation
from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional, Dict, Any

class StaffMember(BaseModel):
    # Staff member model
    id: str
    displayName: str
    emailAddress: EmailStr
    role: str
    useBusinessHours: bool
    
    model_config = {
        "extra": "allow"  # Allow extra fields from Microsoft Graph API
    }

class BookingBusiness(BaseModel):
    # Booking business model
    id: str
    displayName: str
    businessType: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    webSiteUrl: Optional[str] = None
    
    model_config = {
        "extra": "allow"  # Allow extra fields from Microsoft Graph API
    }

class BookingService(BaseModel):
    # Booking service model
    id: str
    displayName: str
    description: Optional[str] = None
    defaultDuration: int
    businessId: str
    staffMemberIds: Optional[List[str]] = None
    
    model_config = {
        "extra": "allow"  # Allow extra fields from Microsoft Graph API
    }

class ServicesByBusiness(BaseModel):
    # Services grouped by business
    businessId: str
    businessName: str
    services: List[BookingService]

class ServiceResponse(BaseModel):
    # Response model for staff services
    staffMember: StaffMember
    servicesByBusiness: List[ServicesByBusiness]

class ErrorResponse(BaseModel):
    # Error response model
    detail: str""",
    
    "app/services/__init__.py": """# Services package""",
    
    "app/services/graph_service.py": """# Microsoft Graph API service for accessing Booking data
import logging
from typing import Dict, List, Optional, Any, Tuple

from azure.identity import UsernamePasswordCredential
from msgraph import GraphServiceClient

from app.config import settings

# Configure logging
logger = logging.getLogger(__name__)

class GraphService:
    # Service for interacting with Microsoft Graph API
    
    def __init__(self):
        # Initialize the Graph service with credentials
        self.client = self._create_graph_client()
    
    def _create_graph_client(self) -> GraphServiceClient:
        # Create a Microsoft Graph client using username/password authentication
        try:
            # Check if all required credentials are available
            if not all([settings.ms_client_id, settings.ms_username, 
                       settings.ms_password, settings.ms_tenant_id]):
                raise ValueError("Missing required Microsoft Graph API credentials")
            
            # Define the scopes
            scopes = ["https://graph.microsoft.com/.default"]
            
            # Create the credential
            credential = UsernamePasswordCredential(
                client_id=settings.ms_client_id,
                username=settings.ms_username,
                password=settings.ms_password,
                tenant_id=settings.ms_tenant_id
            )
            
            # Create the Graph client - updated for msgraph-sdk 1.26.0
            graph_client = GraphServiceClient(credentials=credential)
            
            return graph_client
        
        except Exception as e:
            logger.error(f"Failed to create Graph client: {e}")
            raise
    
    def get_booking_businesses(self) -> List[Dict[str, Any]]:
        # Get all booking businesses
        try:
            # Get booking businesses - updated for msgraph-sdk 1.26.0
            result = self.client.booking_businesses.get()
            
            # Convert to list of dictionaries
            businesses = [business.to_dict() for business in result.value]
            
            return businesses
        
        except Exception as e:
            logger.error(f"Failed to get booking businesses: {e}")
            raise
    
    def get_staff_members(self, business_id: str) -> List[Dict[str, Any]]:
        # Get staff members for a specific business
        try:
            # Get staff members for the business - updated for msgraph-sdk 1.26.0
            result = self.client.booking_businesses.by_booking_business_id(business_id).staff_members.get()
            
            # Convert to list of dictionaries
            staff_members = [staff.to_dict() for staff in result.value]
            
            return staff_members
        
        except Exception as e:
            logger.error(f"Failed to get staff members for business {business_id}: {e}")
            raise
    
    def get_services(self, business_id: str) -> List[Dict[str, Any]]:
        # Get services for a specific business
        try:
            # Get services for the business - updated for msgraph-sdk 1.26.0
            result = self.client.booking_businesses.by_booking_business_id(business_id).services.get()
            
            # Convert to list of dictionaries
            services = [service.to_dict() for service in result.value]
            
            # Add business ID to each service for reference
            for service in services:
                service["businessId"] = business_id
            
            return services
        
        except Exception as e:
            logger.error(f"Failed to get services for business {business_id}: {e}")
            raise
    
    def find_staff_member_by_email(self, email: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        # Find a staff member by email across all businesses
        try:
            # Get all booking businesses
            businesses = self.get_booking_businesses()
            
            # Search for the staff member in each business
            for business in businesses:
                business_id = business["id"]
                
                # Get staff members for this business
                staff_members = self.get_staff_members(business_id)
                
                # Look for the staff member with the matching email
                for staff in staff_members:
                    if staff.get("emailAddress", "").lower() == email.lower():
                        return staff, business_id
            
            # Staff member not found
            return None, None
        
        except Exception as e:
            logger.error(f"Failed to find staff member by email {email}: {e}")
            raise
    
    def get_services_for_staff(self, staff_id: str) -> List[Tuple[Dict[str, Any], Dict[str, Any]]]:
        # Get services for a specific staff member across all businesses
        try:
            # Get all booking businesses
            businesses = self.get_booking_businesses()
            businesses_dict = {b["id"]: b for b in businesses}
            
            # Get services for each business and filter for this staff member
            staff_services = []
            
            for business_id in businesses_dict:
                # Get services for this business
                services = self.get_services(business_id)
                
                # Filter services for this staff member
                for service in services:
                    staff_member_ids = service.get("staffMemberIds", [])
                    if staff_id in staff_member_ids:
                        staff_services.append((service, businesses_dict[business_id]))
            
            return staff_services
        
        except Exception as e:
            logger.error(f"Failed to get services for staff {staff_id}: {e}")
            raise""",
    
    "app/services/cache_service.py": """# Cache service for caching API responses
import json
import logging
import time
import os
from typing import Any, Dict, Optional, List
from abc import ABC, abstractmethod
import redis
from collections import OrderedDict

from app.config import settings

# Configure logging
logger = logging.getLogger(__name__)

# Cache interface
class CacheInterface(ABC):
    # Abstract base class for cache implementations
    
    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        # Get data from cache
        pass
    
    @abstractmethod
    def set(self, key: str, data: Any, expire_seconds: Optional[int] = None) -> bool:
        # Set data in cache with expiration
        pass
    
    @abstractmethod
    def delete(self, key: str) -> bool:
        # Delete data from cache
        pass
    
    def get_key(self, prefix: str, identifier: str) -> str:
        # Generate a cache key
        return f"{prefix}:{identifier}"

# In-memory cache implementation
class MemoryCache(CacheInterface):
    # Simple in-memory cache using OrderedDict
    
    def __init__(self, max_size: int = 0):
        # Initialize in-memory cache
        # Parameters:
        #   max_size: Maximum number of items to store in cache (0 = unlimited)
        #
        # The max_size parameter controls how many items can be stored in the cache.
        # When set to a positive number, the cache will remove the oldest items
        # when it reaches this limit. This prevents memory usage from growing indefinitely.
        # When set to 0, the cache has no size limit (use with caution).
        
        self.cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        self.max_size = max_size
        
        if max_size > 0:
            logger.info(f"In-memory cache initialized with max size: {max_size}")
        else:
            logger.info("In-memory cache initialized with no size limit")
    
    def get(self, key: str) -> Optional[Any]:
        # Get data from cache
        try:
            if key in self.cache:
                item = self.cache[key]
                # Check if item has expired
                if item["expires"] > time.time() or item["expires"] == 0:
                    # Move to end (most recently used)
                    self.cache.move_to_end(key)
                    return item["data"]
                else:
                    # Remove expired item
                    self.delete(key)
            return None
        except Exception as e:
            logger.error(f"Memory cache retrieval error: {e}")
            return None
    
    def set(self, key: str, data: Any, expire_seconds: Optional[int] = None) -> bool:
        # Set data in cache with expiration
        try:
            # Use default TTL if not specified
            if expire_seconds is None:
                expire_seconds = settings.cache_ttl_seconds
            
            # Calculate expiration time
            expires = time.time() + expire_seconds if expire_seconds > 0 else 0
            
            # Add to cache
            self.cache[key] = {
                "data": data,
                "expires": expires
            }
            
            # Move to end (most recently used)
            self.cache.move_to_end(key)
            
            # Remove oldest items if cache is too large and max_size is set
            if self.max_size > 0:
                while len(self.cache) > self.max_size:
                    self.cache.popitem(last=False)
            
            return True
        except Exception as e:
            logger.error(f"Memory cache storage error: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        # Delete data from cache
        try:
            if key in self.cache:
                del self.cache[key]
            return True
        except Exception as e:
            logger.error(f"Memory cache deletion error: {e}")
            return False

# Redis cache implementation
class RedisCache(CacheInterface):
    # Redis-based cache implementation
    
    def __init__(self, redis_url: str):
        # Initialize Redis client
        try:
            self.redis_client = redis.from_url(redis_url)
            logger.info("Redis cache initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Redis: {e}")
            self.redis_client = None
    
    def get(self, key: str) -> Optional[Any]:
        # Get data from cache
        if not self.redis_client:
            return None
        
        try:
            data = self.redis_client.get(key)
            if data:
                return json.loads(data)
        except Exception as e:
            logger.error(f"Redis cache retrieval error: {e}")
        
        return None
    
    def set(self, key: str, data: Any, expire_seconds: Optional[int] = None) -> bool:
        # Set data in cache with expiration
        if not self.redis_client:
            return False
        
        try:
            # Use default TTL if not specified
            if expire_seconds is None:
                expire_seconds = settings.cache_ttl_seconds
            
            self.redis_client.setex(key, expire_seconds, json.dumps(data))
            return True
        except Exception as e:
            logger.error(f"Redis cache storage error: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        # Delete data from cache
        if not self.redis_client:
            return False
        
        try:
            self.redis_client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Redis cache deletion error: {e}")
            return False

# Factory function to create the appropriate cache service
def create_cache_service() -> CacheInterface:
    # Create cache service based on configuration
    cache_type = settings.cache_type.lower()
    
    if cache_type == "redis" and settings.redis_url:
        logger.info("Using Redis cache")
        return RedisCache(settings.redis_url)
    else:
        if cache_type == "redis" and not settings.redis_url:
            logger.warning("Redis cache selected but no REDIS_URL provided. Falling back to in-memory cache.")
        else:
            logger.info("Using in-memory cache")
        
        # Use 0 for unlimited cache size
        memory_cache_max_size = int(os.environ.get("MEMORY_CACHE_MAX_SIZE", "0"))
        return MemoryCache(memory_cache_max_size)

# Create cache service instance
cache_service = create_cache_service()""",
    
    "app/utils/__init__.py": """# Utilities package""",
    
    "app/utils/helpers.py": """# Helper functions for the application
from typing import Dict, List, Any

def group_services_by_business(services_with_businesses: List[tuple]) -> List[Dict[str, Any]]:
    # Group services by business
    
    # Group services by business ID
    services_by_business = {}
    
    for service, business in services_with_businesses:
        business_id = business["id"]
        
        if business_id not in services_by_business:
            services_by_business[business_id] = {
                "businessId": business_id,
                "businessName": business["displayName"],
                "services": []
            }
        
        services_by_business[business_id]["services"].append(service)
    
    # Convert to list
    return list(services_by_business.values())"""
}

def create_project():
    # Define project directory
    project_dir = "booking-api-service"
    
    # Remove existing directory if it exists
    if os.path.exists(project_dir):
        shutil.rmtree(project_dir)
    
    # Create project directory
    os.makedirs(project_dir, exist_ok=True)
    
    # Create files and directories
    for file_path, content in project.items():
        # Create directory if it doesn't exist
        full_path = os.path.join(project_dir, file_path)
        directory = os.path.dirname(full_path)
        
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
        
        # Write file content
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)
    
    print(f"Project created successfully in '{project_dir}' directory!")
    print("\nTo set up the project:")
    print("1. Create a virtual environment:")
    print("   python -m venv .venv")
    print("2. Activate the virtual environment:")
    print("   - On Windows: .venv\\Scripts\\activate")
    print("   - On Linux/Mac: source .venv/bin/activate")
    print("3. Install dependencies:")
    print("   pip install -r requirements.txt")
    print("4. Copy .env.example to .env and fill in your credentials")
    print("5. Run the application:")
    print("   python run.py")
    print("\nTo create a ZIP file of the project:")
    print("   python -c \"import shutil; shutil.make_archive('booking-api-service', 'zip', 'booking-api-service')\"")

if __name__ == "__main__":
    create_project()
