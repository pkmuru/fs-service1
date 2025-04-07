import os
import logging
import httpx
from fastapi import HTTPException
from functools import lru_cache
from typing import Dict, List, Optional, Any

# Configure logging
logger = logging.getLogger(__name__)

# Configuration
class GraphSettings:
    MS_GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"
    MS_USERNAME = os.getenv("MS_USERNAME")
    MS_PASSWORD = os.getenv("MS_PASSWORD")
    MS_TENANT_ID = os.getenv("MS_TENANT_ID", "common")

settings = GraphSettings()

# Authentication helper
@lru_cache(maxsize=1)
async def get_access_token():
    """
    Get Microsoft Graph API access token using username and password
    This approach is suitable for testing but not recommended for production
    """
    if not settings.MS_USERNAME or not settings.MS_PASSWORD:
        raise HTTPException(
            status_code=500,
            detail="Authentication not configured. Set MS_USERNAME and MS_PASSWORD environment variables."
        )
    
    # Using the Resource Owner Password Credentials flow
    # This is not recommended for production applications
    token_url = f"https://login.microsoftonline.com/{settings.MS_TENANT_ID}/oauth2/v2.0/token"
    
    # Prepare the request body
    data = {
        "grant_type": "password",
        "client_id": "1950a258-227b-4e31-a9cf-717495945fc2",  # Microsoft's Resource Explorer App ID
        "scope": "https://graph.microsoft.com/.default",
        "username": settings.MS_USERNAME,
        "password": settings.MS_PASSWORD
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(token_url, data=data)
            response.raise_for_status()
            token_data = response.json()
            return token_data["access_token"]
    except httpx.HTTPStatusError as e:
        logger.error(f"Failed to get access token: {e.response.text}")
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"Authentication failed: {e.response.text}"
        )
    except Exception as e:
        logger.error(f"Authentication error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Authentication error: {str(e)}"
        )

# Graph API requests
async def get_booking_businesses(token: str) -> Dict[str, Any]:
    """Get all booking businesses from Microsoft Graph API"""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{settings.MS_GRAPH_BASE_URL}/bookingBusinesses",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        if response.status_code != 200:
            logger.error(f"Failed to fetch businesses: {response.text}")
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Failed to fetch booking businesses: {response.text}"
            )
        
        return response.json()

async def get_staff_members_for_business(business_id: str, token: str) -> Dict[str, Any]:
    """Get staff members for a specific business"""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{settings.MS_GRAPH_BASE_URL}/bookingBusinesses/{business_id}/staffMembers",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        if response.status_code != 200:
            logger.error(f"Failed to fetch staff: {response.text}")
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Failed to fetch staff members: {response.text}"
            )
        
        return response.json()

async def get_services_for_business(business_id: str, token: str) -> Dict[str, Any]:
    """Get services for a specific business"""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{settings.MS_GRAPH_BASE_URL}/bookingBusinesses/{business_id}/services",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        if response.status_code != 200:
            logger.error(f"Failed to fetch services: {response.text}")
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Failed to fetch services: {response.text}"
            )
        
        return response.json()

