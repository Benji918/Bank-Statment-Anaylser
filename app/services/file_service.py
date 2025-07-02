"""File service for handling file uploads and storage"""

import os
import hashlib
from typing import Optional, Tuple
from fastapi import UploadFile
import cloudinary
import cloudinary.uploader
from app.core.config import settings
from app.core.logging import LoggerMixin
from app.core.exceptions import FileProcessingError, ValidationError


class FileService(LoggerMixin):
    """Service for file upload and management"""
    
    def __init__(self):
        # Configure Cloudinary
        cloudinary.config(
            cloud_name=settings.CLOUDINARY_CLOUD_NAME,
            api_key=settings.CLOUDINARY_API_KEY,
            api_secret=settings.CLOUDINARY_API_SECRET
        )
    
    def validate_file(self, file: UploadFile) -> None:
        """Validate uploaded file"""
        try:
            # Check file size
            if file.size > settings.MAX_FILE_SIZE:
                raise ValidationError(
                    f"File size {file.size} exceeds maximum allowed size {settings.MAX_FILE_SIZE}"
                )
            
            # Check file type
            if file.content_type not in settings.ALLOWED_FILE_TYPES:
                raise ValidationError(
                    f"File type {file.content_type} not allowed. Allowed types: {settings.ALLOWED_FILE_TYPES}"
                )
            
            # Check file extension
            if not file.filename.lower().endswith('.pdf'):
                raise ValidationError("Only PDF files are allowed")
            
            self.log_operation(
                "validate_file", 
                filename=file.filename, 
                size=file.size, 
                content_type=file.content_type
            )
            
        except ValidationError:
            raise
        except Exception as e:
            self.log_error(e, "validate_file", filename=file.filename)
            raise FileProcessingError("File validation failed")
    
    def generate_unique_filename(self, original_filename: str, user_id: int) -> str:
        """Generate unique filename for storage"""
        try:
            # Create hash from user_id and original filename
            hash_input = f"{user_id}_{original_filename}_{os.urandom(8).hex()}"
            file_hash = hashlib.md5(hash_input.encode()).hexdigest()
            
            # Get file extension
            _, ext = os.path.splitext(original_filename)
            
            # Create unique filename
            unique_filename = f"statements/{user_id}/{file_hash}{ext}"
            
            self.log_operation(
                "generate_unique_filename",
                original=original_filename,
                unique=unique_filename,
                user_id=user_id
            )
            
            return unique_filename
            
        except Exception as e:
            self.log_error(e, "generate_unique_filename", filename=original_filename)
            raise FileProcessingError("Failed to generate unique filename")
    
    async def upload_to_cloudinary(
        self, 
        file: UploadFile, 
        user_id: int
    ) -> Tuple[str, str]:
        """Upload file to Cloudinary and return public_id and URL"""
        try:
            # Generate unique filename
            unique_filename = self.generate_unique_filename(file.filename, user_id)
            
            # Read file content
            file_content = await file.read()
            
            # Upload to Cloudinary
            upload_result = cloudinary.uploader.upload(
                file_content,
                public_id=unique_filename,
                resource_type="raw",  # For non-image files
                folder=f"intellibank/statements/{user_id}",
                use_filename=True,
                unique_filename=False
            )
            
            public_id = upload_result["public_id"]
            secure_url = upload_result["secure_url"]
            
            self.log_operation(
                "upload_to_cloudinary",
                filename=file.filename,
                public_id=public_id,
                user_id=user_id
            )
            
            return public_id, secure_url
            
        except Exception as e:
            self.log_error(e, "upload_to_cloudinary", filename=file.filename)
            raise FileProcessingError("Failed to upload file to cloud storage")
    
    def delete_from_cloudinary(self, public_id: str) -> bool:
        """Delete file from Cloudinary"""
        try:
            result = cloudinary.uploader.destroy(
                public_id,
                resource_type="raw"
            )
            
            success = result.get("result") == "ok"
            
            self.log_operation(
                "delete_from_cloudinary",
                public_id=public_id,
                success=success
            )
            
            return success
            
        except Exception as e:
            self.log_error(e, "delete_from_cloudinary", public_id=public_id)
            return False
    
    async def download_from_cloudinary(self, public_id: str) -> bytes:
        """Download file content from Cloudinary"""
        try:
            import httpx
            
            # Get the file URL
            url = cloudinary.utils.cloudinary_url(
                public_id,
                resource_type="raw"
            )[0]
            
            # Download file content
            async with httpx.AsyncClient() as client:
                response = await client.get(url)
                response.raise_for_status()
                
                self.log_operation(
                    "download_from_cloudinary",
                    public_id=public_id,
                    size=len(response.content)
                )
                
                return response.content
                
        except Exception as e:
            self.log_error(e, "download_from_cloudinary", public_id=public_id)
            raise FileProcessingError("Failed to download file from cloud storage")


# Create service instance
file_service = FileService()