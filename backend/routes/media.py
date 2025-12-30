from fastapi import APIRouter
from fastapi.staticfiles import StaticFiles

router = APIRouter()

# Just a router wrapper if we need dynamic serving, 
# but StaticFiles mounting in server.py is usually better.
# We'll use this file to explicitly ensure the static mount exists in server.py

def setup_media_routes(app):
    # Mount the generated images directory
    # The frontend expects /generated_images/{filename}
    # So we mount frontend/generated_images to /generated_images
    app.mount("/generated_images", StaticFiles(directory="frontend/generated_images"), name="generated_images")
