"""Enhanced PDF to Excel conversion service using Adobe API"""

import time
import tempfile
import os
from typing import Optional, Dict, Any
from fastapi import HTTPException
import requests
import pandas as pd
from app.core.config import settings
from app.core.logging import LoggerMixin
from app.core.exceptions import ExternalServiceError, FileProcessingError


class PDFExcelService(LoggerMixin):
    """Enhanced service for converting PDF files to Excel using Adobe PDF Services API"""

    BASE_URL = "https://pdf-services-ue1.adobe.io"
    TOKEN_ENDPOINT = f"{BASE_URL}/token"
    ASSETS_ENDPOINT = f"{BASE_URL}/assets"
    EXPORT_ENDPOINT = f"{BASE_URL}/operation/exportpdf"

    def __init__(self):
        self.client_id = settings.ADOBE_CLIENT_ID
        self.client_secret = settings.ADOBE_CLIENT_SECRET
        
        if not self.client_id or not self.client_secret:
            raise ValueError("Adobe API credentials must be configured")

    def generate_token(self) -> str:
        """Generate access token for Adobe PDF Services API"""
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        payload = {
            'client_id': self.client_id,
            'client_secret': self.client_secret
        }

        try:
            self.log_operation("generate_token_request")
            
            response = requests.post(self.TOKEN_ENDPOINT, data=payload, headers=headers)
            response.raise_for_status()

            token_data = response.json()
            access_token = token_data.get('access_token')

            if not access_token:
                raise ExternalServiceError("No access token in Adobe API response")

            self.log_operation("generate_token_success")
            return access_token

        except requests.RequestException as e:
            self.log_error(e, "generate_token")
            raise ExternalServiceError(f"Failed to generate Adobe API token: {str(e)}")

    def create_asset_from_bytes(self, file_content: bytes, access_token: str) -> Dict[str, Any]:
        """Create an asset and upload PDF content from bytes"""
        headers = {
            "X-API-Key": self.client_id,
            "Authorization": f'Bearer {access_token}',
            "Content-Type": "application/json"
        }
        payload = {"mediaType": "application/pdf"}

        try:
            self.log_operation("create_asset_request", content_size=len(file_content))
            
            # Create asset
            response = requests.post(self.ASSETS_ENDPOINT, headers=headers, json=payload)
            response.raise_for_status()
            asset_info = response.json()

            upload_uri = asset_info["uploadUri"]
            asset_id = asset_info["assetID"]
            
            self.log_operation("asset_created", asset_id=asset_id)

            # Upload file content
            put_response = requests.put(
                upload_uri,
                headers={"Content-Type": "application/pdf"},
                data=file_content
            )
            put_response.raise_for_status()

            self.log_operation("file_uploaded", asset_id=asset_id)
            return asset_info

        except requests.RequestException as e:
            self.log_error(e, "create_asset")
            raise ExternalServiceError(f"Failed to create Adobe asset: {str(e)}")

    def export_to_excel(self, asset_info: Dict[str, Any], access_token: str) -> bytes:
        """Export PDF asset to Excel format and return content"""
        headers = {
            "X-API-Key": self.client_id,
            "Authorization": f'Bearer {access_token}',
            "Content-Type": "application/json"
        }

        payload = {
            "assetID": asset_info["assetID"],
            "targetFormat": "xlsx",
            "ocrLang": "en-US"
        }

        try:
            self.log_operation("export_request", asset_id=asset_info["assetID"])
            
            # Submit export job
            response = requests.post(self.EXPORT_ENDPOINT, headers=headers, json=payload)
            response.raise_for_status()

            poll_url = response.headers.get("Location")
            if not poll_url:
                raise ExternalServiceError("No polling URL returned from Adobe export request")

            job_id = poll_url.rstrip("/").split("/")[-2]
            self.log_operation("export_job_submitted", job_id=job_id)

            # Poll for completion and download
            download_url = self._poll_job_status(poll_url, headers)
            excel_content = self._download_excel_content(download_url)
            
            self.log_operation("export_completed", job_id=job_id, content_size=len(excel_content))
            return excel_content

        except requests.RequestException as e:
            self.log_error(e, "export_to_excel")
            raise ExternalServiceError(f"Adobe export failed: {str(e)}")

    def _poll_job_status(
        self, 
        poll_url: str, 
        headers: Dict[str, str], 
        poll_interval: int = 10, 
        max_attempts: int = 30
    ) -> str:
        """Poll job status until completion with exponential backoff"""
        attempts = 0
        current_interval = poll_interval

        while attempts < max_attempts:
            try:
                self.log_operation("polling_status", attempt=attempts + 1)
                
                status_response = requests.get(poll_url, headers=headers)
                status_response.raise_for_status()

                status_data = status_response.json()
                status = status_data.get("status")

                if status == "done":
                    download_uri = status_data['asset']['downloadUri']
                    if not download_uri:
                        raise ExternalServiceError("No download URI in completed job response")

                    self.log_operation("job_completed", attempts=attempts + 1)
                    return download_uri

                elif status == "failed":
                    error_msg = status_response.text
                    self.log_error(Exception(error_msg), "job_failed")
                    raise ExternalServiceError(f"Adobe export job failed: {error_msg}")

                attempts += 1
                time.sleep(current_interval)
                
                # Exponential backoff with jitter
                current_interval = min(current_interval * 1.5, 60)

            except requests.RequestException as e:
                self.log_error(e, "poll_job_status", attempt=attempts + 1)
                raise ExternalServiceError(f"Status polling failed: {str(e)}")

        raise ExternalServiceError("Adobe export job timed out")

    def _download_excel_content(self, download_url: str) -> bytes:
        """Download Excel content from Adobe"""
        try:
            self.log_operation("download_excel_request")
            
            response = requests.get(download_url, stream=True)
            response.raise_for_status()
            
            content = response.content
            self.log_operation("download_excel_success", size=len(content))
            
            return content
            
        except requests.RequestException as e:
            self.log_error(e, "download_excel_content")
            raise ExternalServiceError(f"Failed to download Excel content: {str(e)}")

    async def convert_pdf_to_excel(self, pdf_content: bytes) -> pd.DataFrame:
        """Convert PDF content to Excel and return as pandas DataFrame"""
        try:
            self.log_operation("pdf_conversion_start", pdf_size=len(pdf_content))
            
            # Generate token
            access_token = self.generate_token()
            
            # Create asset and upload
            asset_info = self.create_asset_from_bytes(pdf_content, access_token)
            
            # Export to Excel
            excel_content = self.export_to_excel(asset_info, access_token)
            
            # Convert to DataFrame
            with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as temp_file:
                temp_file.write(excel_content)
                temp_file.flush()
                
                try:
                    # Read Excel file into DataFrame
                    df = pd.read_excel(temp_file.name, sheet_name=None)
                    
                    # If multiple sheets, combine them
                    if isinstance(df, dict):
                        # Take the first sheet or combine all sheets
                        if len(df) == 1:
                            df = list(df.values())[0]
                        else:
                            # Combine all sheets
                            combined_df = pd.DataFrame()
                            for sheet_name, sheet_df in df.items():
                                sheet_df['sheet_name'] = sheet_name
                                combined_df = pd.concat([combined_df, sheet_df], ignore_index=True)
                            df = combined_df
                    
                    self.log_operation(
                        "pdf_conversion_success", 
                        rows=len(df), 
                        columns=len(df.columns)
                    )
                    
                    return df
                    
                finally:
                    # Clean up temp file
                    os.unlink(temp_file.name)
                    
        except Exception as e:
            self.log_error(e, "convert_pdf_to_excel")
            raise FileProcessingError(f"PDF to Excel conversion failed: {str(e)}")

    def extract_metadata(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Extract metadata from converted Excel data"""
        try:
            metadata = {
                "total_rows": len(df),
                "total_columns": len(df.columns),
                "column_names": df.columns.tolist(),
                "data_types": df.dtypes.to_dict(),
                "null_counts": df.isnull().sum().to_dict(),
                "sample_data": df.head(5).to_dict('records') if len(df) > 0 else []
            }
            
            self.log_operation("metadata_extracted", rows=metadata["total_rows"])
            return metadata
            
        except Exception as e:
            self.log_error(e, "extract_metadata")
            return {}


# Create service instance
pdf_service = PDFExcelService()