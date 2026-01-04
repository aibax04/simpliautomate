import requests
from backend.config import Config

class LinkedInAgent:
    """
    Handles LinkedIn OAuth2 and UGC Post API with Image Support.
    """
    def __init__(self, access_token=None, person_urn=None):
        # Force reload from .env in project root
        from dotenv import load_dotenv
        import os
        from pathlib import Path
        
        # Calculate project root
        env_path = Path(os.getcwd()) / '.env'
        load_dotenv(dotenv_path=env_path, override=True)
        
        self.access_token = access_token or os.getenv("LINKEDIN_ACCESS_TOKEN")
        self.person_urn = person_urn or os.getenv("LINKEDIN_USER_URN")
        self.base_url = "https://api.linkedin.com/v2"
        
        # DEBUG: Print status (masked)
        token_status = "FOUND" if self.access_token else "MISSING"
        urn_status = "FOUND" if self.person_urn else "MISSING"
        print(f"[DEBUG] LinkedIn Agent Init - Token: {token_status}, URN: {urn_status}")

    def post_to_linkedin(self, text, image_path=None):
        # Auto-fetch URN if we have a token but no URN
        if self.access_token and not self.person_urn:
            self.person_urn = self._fetch_user_urn()
            
        if not self.access_token or not self.person_urn:
            print("❌ Error: Missing LinkedIn credentials.")
            return {
                "error": "LinkedIn credentials (TOKEN/URN) are missing. Cannot post."
            }

        try:
            asset = None
            if image_path:
                # 1. Register Upload
                asset = self._upload_image(image_path)
            
            # 2. Create Share
            return self._create_share(text, asset)
            
        except Exception as e:
            print(f"LinkedIn Posting Error: {e}")
            return {"error": str(e)}

    def _fetch_user_urn(self):
        """
        Fetches the authenticated user's ID to construct the URN.
        Supports 'id' from /me (r_liteprofile) and 'sub' from /userinfo (openid).
        """
        headers = {"Authorization": f"Bearer {self.access_token}"}
        
        # 1. Try Legacy /me (r_liteprofile)
        try:
            print("[DEBUG] Attempting to fetch URN via /me (r_liteprofile)...")
            resp = requests.get(f"{self.base_url}/me", headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                if 'id' in data:
                    print(f"[SUCCESS] Fetched User ID from /me: {data['id']}")
                    return data['id']
        except Exception as e:
            print(f"[DEBUG] /me request failed: {e}")

        # 2. Try OpenID /userinfo (openid)
        try:
            print("[DEBUG] Attempting to fetch URN via /userinfo (openid)...")
            resp = requests.get(f"{self.base_url}/userinfo", headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                if 'sub' in data:
                    print(f"[SUCCESS] Fetched User ID from /userinfo: {data['sub']}")
                    return data['sub']
        except Exception as e:
            print(f"[DEBUG] /userinfo request failed: {e}")

        print("❌ Failed to fetch User URN from both /me and /userinfo.")
        return None

    def _upload_image(self, image_path):
        """
        Uploads image to LinkedIn in 2 steps: Register -> Upload
        """
        import os
        
        # 0. Resolve path using absolute project root logic
        # This file is in backend/agents/linkedin_agent.py
        current_dir = os.path.dirname(os.path.abspath(__file__)) # agents/
        project_root = os.path.dirname(os.path.dirname(current_dir)) # simplii/
        
        if image_path.startswith("/generated_images/"):
            clean_path = image_path.replace("/generated_images/", "")
            real_path = os.path.join(project_root, "frontend", "generated_images", clean_path)
        else:
            real_path = image_path
            
        if not os.path.exists(real_path):
            print(f"[ERROR] LinkedIn Post: Image not found at {real_path}")
            return None

        # 1. Register
        register_url = f"{self.base_url}/assets?action=registerUpload"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        register_body = {
            "registerUploadRequest": {
                "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
                "owner": f"urn:li:person:{self.person_urn}",
                "serviceRelationships": [
                    {
                        "relationshipType": "OWNER",
                        "identifier": "urn:li:userGeneratedContent"
                    }
                ]
            }
        }
        
        reg_resp = requests.post(register_url, headers=headers, json=register_body)
        reg_resp.raise_for_status()
        reg_data = reg_resp.json()
        
        upload_url = reg_data['value']['uploadMechanism']['com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest']['uploadUrl']
        asset = reg_data['value']['asset']
        
        # 2. Upload Binary
        with open(real_path, 'rb') as img_file:
            # Note: Many pre-signed URLs (like LinkedIn's) fail if you include the Authorization header twice.
            # We only use 'Content-Type' for the binary upload.
            headers_put = {"Content-Type": "application/octet-stream"}
            up_resp = requests.put(upload_url, headers=headers_put, data=img_file)
            up_resp.raise_for_status()
            
        print(f"Image uploaded successfully: {asset}")
        return asset

    def _create_share(self, text, asset=None):
        url = f"{self.base_url}/ugcPosts"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "X-Restli-Protocol-Version": "2.0.0",
            "Content-Type": "application/json",
        }
        
        share_content = {
            "shareCommentary": {
                "text": text
            },
            "shareMediaCategory": "NONE"
        }
        
        if asset:
            share_content["shareMediaCategory"] = "IMAGE"
            share_content["media"] = [
                {
                    "status": "READY",
                    "description": {
                        "text": "Generated Infographic"
                    },
                    "media": asset,
                    "title": {
                        "text": "Simplii Insight"
                    }
                }
            ]

        post_data = {
            "author": f"urn:li:person:{self.person_urn}",
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": share_content
            },
            "visibility": {
                "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
            }
        }

        response = requests.post(url, headers=headers, json=post_data)
        if response.status_code == 201:
            print(f"Successfully posted to LinkedIn: {response.json().get('id')}")
            return {"status": "success", "message": "Published successfully!", "post_id": response.json().get('id')}
        else:
            print(f"Failed to post: {response.text}")
            return {"error": response.text}
