import time

from fastapi import HTTPException
import logging
import os
import requests
from typing import Optional
from dotenv import load_dotenv

logger = logging.getLogger(__name__)
load_dotenv(".env")


class PDFExcelService:
    """Service for converting PDF files to Excel using Adobe PDF Services API"""

    BASE_URL = "https://pdf-services-ue1.adobe.io"
    TOKEN_ENDPOINT = f"{BASE_URL}/token"
    ASSETS_ENDPOINT = f"{BASE_URL}/assets"
    EXPORT_ENDPOINT = f"{BASE_URL}/operation/exportpdf"

    def __init__(self, file_path: str):
        """
        Initialize the PDF to Excel service

        Args:
            file_path: Path to the PDF file to convert
            client_id: Adobe API client ID (defaults to environment variable)
            client_secret: Adobe API client secret (defaults to environment variable)
        """
        self.file_path = file_path
        self.client_id = os.getenv("CLIENT_ID")
        self.client_secret = os.getenv("CLIENT_SECRET")

        if not self.client_id or not self.client_secret:
            raise ValueError("CLIENT_ID and CLIENT_SECRET must be provided or set as environment variables")

        # if not os.path.exists(self.file_path):
        #     raise FileNotFoundError(f"PDF file not found: {self.file_path}")

    def generate_token(self) -> str:
        """Generate access token for Adobe PDF Services API"""
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        payload = {
            'client_id': self.client_id,
            'client_secret': self.client_secret
        }

        try:
            response = requests.post(self.TOKEN_ENDPOINT, data=payload, headers=headers)
            response.raise_for_status()

            token_data = response.json()
            access_token = token_data.get('access_token')

            if not access_token:
                raise HTTPException(status_code=500, detail="No access token in response")

            logger.info("Successfully generated access token")
            return access_token

        except requests.RequestException as e:
            logger.error(f"Failed to generate token: {e}")
            raise HTTPException(status_code=500, detail=f"Error generating token: {str(e)}")

    def create_asset(self, access_token: str) -> dict:
        """
        Create an asset and upload the PDF file

        Args:
            access_token: Valid access token for API authentication

        Returns:
            dict: Asset information including assetID
        """
        headers = {
            "X-API-Key": self.client_id,
            "Authorization": f'Bearer {access_token}',
            "Content-Type": "application/json"
        }
        payload = {"mediaType": "application/pdf"}

        try:
            # Create asset
            response = requests.post(self.ASSETS_ENDPOINT, headers=headers, json=payload)
            response.raise_for_status()
            asset_info = response.json()

            upload_uri = asset_info["uploadUri"]
            logger.info(f"Created asset with ID: {asset_info['assetID']}")


            with open(self.file_path, "rb") as file:
                put_response = requests.put(
                    upload_uri,
                    headers={"Content-Type": "application/pdf"},
                    data=file
                )
                put_response.raise_for_status()

            print("PDF file uploaded successfully")
            return asset_info

        except requests.RequestException as e:
            logger.error(f"Failed to create asset or upload file: {e}")
            raise HTTPException(status_code=500, detail=f"Asset creation failed: {str(e)}")
        except IOError as e:
            logger.error(f"Failed to read PDF file: {e}")
            raise HTTPException(status_code=500, detail=f"File read error: {str(e)}")

    def export_to_excel(self, asset_info: dict, access_token: str) -> str:
        """
        Export PDF asset to Excel format

        Args:
            asset_info: Asset information from create_asset
            access_token: Valid access token for API authentication

        Returns:
            str: Download URI for the converted Excel file
        """
        headers = {
            "X-API-Key": self.client_id,
            "Authorization": f'Bearer {access_token}',
            "Content-Type": "application/json"
        }

        payload = {
            "assetID": asset_info,
            "targetFormat": "xlsx",
            "ocrLang": "en-US"
        }

        try:
            # Submit export job
            response = requests.post(self.EXPORT_ENDPOINT, headers=headers, json=payload)
            response.raise_for_status()

            poll_url = response.headers.get("Location")
            if not poll_url:
                raise HTTPException(status_code=500, detail="No polling URL returned from export request")

            job_id = poll_url.rstrip("/").split("/")[-2]
            logger.info(f"Export job submitted with ID: {job_id}")

            return self._poll_job_status(poll_url, headers)

            # response = requests.get(download_url, stream=True)
            # response.raise_for_status()
            #
            # return response

        except requests.RequestException as e:
            logger.error(f"Export request failed: {e}")
            raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")

    def _poll_job_status(self, poll_url: str, headers: dict, poll_interval: int = 10, max_attempts: int = 5) -> str:
        """
        Poll job status until completion

        Args:
            poll_url: URL to poll for job status
            headers: Request headers
            poll_interval: Seconds between polls
            max_attempts: Maximum polling attempts

        Returns:
            str: Download URI for the converted file
        """
        attempts = 0

        while attempts < max_attempts:
            try:
                status_response = requests.get(poll_url, headers=headers)
                status_response.raise_for_status()

                status_data = status_response.json()
                status = status_data.get("status")

                logger.info(f"Job status: {status} (attempt {attempts + 1})")

                if status == "done":
                    download_uri = status_data['asset']['downloadUri']
                    if not download_uri:
                        raise HTTPException(status_code=500, detail="No download URI in completed job response")

                    logger.info("Export completed successfully")
                    return download_uri

                elif status == "failed":
                    error_msg = status_response.text
                    logger.error(f"Export job failed: {error_msg}")
                    raise HTTPException(status_code=500, detail=f"Export failed: {error_msg}")

                attempts += 1
                time.sleep(poll_interval)

            except requests.RequestException as e:
                logger.error(f"Failed to poll job status: {e}")
                raise HTTPException(status_code=500, detail=f"Status polling failed: {str(e)}")

        raise HTTPException(status_code=408, detail="Export job timed out")