import os
import httpx
import logging
from typing import Optional, Dict

logger = logging.getLogger(__name__)

async def verify_google_token(id_token: str) -> Optional[Dict]:
    """
    Verifies a Google ID token.
    Requires GOOGLE_CLIENT_ID env var.
    """
    client_id = os.environ.get("GOOGLE_CLIENT_ID")
    if not client_id:
        logger.error("GOOGLE_CLIENT_ID not set")
        return None
        
    try:
        # We use httpx to call Google's tokeninfo endpoint
        # For production, using 'google-auth' library is recommended
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"https://oauth2.googleapis.com/tokeninfo?id_token={id_token}")
            if resp.status_code != 200:
                logger.warning(f"Google token verification failed: {resp.text}")
                return None
            
            data = resp.json()
            if data.get("aud") != client_id:
                logger.warning("Google token audience mismatch")
                return None
                
            return {
                "email": data.get("email"),
                "sub": data.get("sub"),
                "name": data.get("name"),
                "picture": data.get("picture")
            }
    except Exception as e:
        logger.error(f"Error verifying Google token: {e}")
        return None

async def verify_facebook_token(access_token: str) -> Optional[Dict]:
    """
    Verifies a Facebook Access Token.
    Requires FACEBOOK_APP_ID and FACEBOOK_APP_SECRET.
    """
    app_id = os.environ.get("FACEBOOK_APP_ID")
    app_secret = os.environ.get("FACEBOOK_APP_SECRET")
    
    if not app_id or not app_secret:
        logger.error("FACEBOOK_APP_ID or FACEBOOK_APP_SECRET not set")
        return None
        
    try:
        async with httpx.AsyncClient() as client:
            # 1. Get Inspect Token (to verify audience)
            inspect_url = f"https://graph.facebook.com/debug_token?input_token={access_token}&access_token={app_id}|{app_secret}"
            resp = await client.get(inspect_url)
            if resp.status_code != 200:
                return None
            
            debug_data = resp.json().get("data", {})
            if not debug_data.get("is_valid") or str(debug_data.get("app_id")) != str(app_id):
                return None
            
            # 2. Get User Info
            me_url = f"https://graph.facebook.com/me?fields=id,name,email,picture.type(large)&access_token={access_token}"
            resp = await client.get(me_url)
            if resp.status_code != 200:
                return None
                
            data = resp.json()
            return {
                "email": data.get("email"),
                "sub": data.get("id"),
                "name": data.get("name"),
                "picture": data.get("picture", {}).get("data", {}).get("url")
            }
    except Exception as e:
        logger.error(f"Error verifying Facebook token: {e}")
        return None

async def verify_apple_token(identity_token: str) -> Optional[Dict]:
    """
    Placeholder for Apple token verification. 
    Apple requires JWT verification with public keys from Apple.
    """
    logger.warning("Apple login verification is not fully implemented (requires complex JWT verification)")
    return None
