from fastapi import APIRouter
from fastapi.staticfiles import StaticFiles

router = APIRouter()

# Just a router wrapper if we need dynamic serving, 
# but StaticFiles mounting in server.py is usually better.
# We'll use this file to explicitly ensure the static mount exists in server.py

import os

def setup_media_routes(app):
    # Ensure directory exists
    static_dir = os.path.join(os.getcwd(), "frontend", "generated_images")
    os.makedirs(static_dir, exist_ok=True)
    
    print(f"[INFO] Mounting /generated_images to {static_dir}")
    app.mount("/generated_images", StaticFiles(directory=static_dir), name="generated_images")
