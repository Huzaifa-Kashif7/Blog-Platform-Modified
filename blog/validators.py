"""
Image upload validators for the Blog Platform.
Validates file extension, file size, and image integrity.
"""
import os
from django.core.exceptions import ValidationError
from PIL import Image


MAX_SIZE_MB = 5
ALLOWED_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.webp']


def validate_image_upload(file):
    """
    Validates an uploaded image file for:
    - Allowed file extension (.jpg, .jpeg, .png, .webp)
    - Maximum file size (5 MB)
    - Valid image integrity (PIL verify)
    """
    # 1. Check file extension
    ext = os.path.splitext(file.name)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValidationError(
            f"Unsupported file type: '{ext}'. "
            f"Allowed types are: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    # 2. Check file size
    if file.size > MAX_SIZE_MB * 1024 * 1024:
        size_mb = file.size / (1024 * 1024)
        raise ValidationError(
            f"File too large ({size_mb:.1f} MB). Maximum allowed size is {MAX_SIZE_MB} MB."
        )

    # 3. Verify it is a real image (PIL integrity check)
    try:
        img = Image.open(file)
        img.verify()
    except Exception:
        raise ValidationError(
            "The uploaded file is not a valid image or is corrupted."
        )
    finally:
        # Reset file pointer after PIL reads it, so Django can save it normally
        file.seek(0)
