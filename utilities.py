from PIL import Image, ImageOps
from datetime import datetime
import base64
from io import BytesIO


def format_team_name(name):
    return name.lower().replace(" ", "_")


def load_and_resize_logo(team_name, box_size=(150, 150)):
    logo_path = f"team_logos/{format_team_name(team_name)}_logo.png"
    logo = Image.open(logo_path).convert("RGBA")  # Convert to RGBA to handle transparency

    # Crop transparent padding around the image
    bbox = logo.getbbox()
    if bbox:
        logo = logo.crop(bbox)

    logo.thumbnail(box_size, Image.ANTIALIAS)
    
    # Convert image to Base64
    buffered = BytesIO()
    logo.save(buffered, format="PNG")
    encoded_logo = base64.b64encode(buffered.getvalue()).decode('utf-8')
    
    return encoded_logo