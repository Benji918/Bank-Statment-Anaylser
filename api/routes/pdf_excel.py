import io

import requests
from fastapi import HTTPException, status, UploadFile, File
from fastapi.responses import StreamingResponse
from fastapi.routing import APIRouter
from api.services.pdf_excel import PDFExcelService
import logging
import tempfile


logger = logging.getLogger(__name__)

pdf_router = APIRouter(
    prefix="/api/pdf-excel",
    tags=["PDF to Excel"],
)


@pdf_router.post("/convert")
async def convert_pdf_to_excel(file: UploadFile = File(...)):
    try:
        if file.content_type != "application/pdf":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid file type. Please upload a PDF file.")

        with tempfile.NamedTemporaryFile(suffix='.pdf') as tmp:
            with open(tmp.name, 'wb') as f:
                f.write(file.file.read())

            pdf_service = PDFExcelService(tmp.name)
            access_token = pdf_service.generate_token()
            asset_info = pdf_service.create_asset(access_token)
            download_url = pdf_service.export_to_excel(asset_info["assetID"], access_token)

            response = requests.get(download_url)
            response.raise_for_status()

            return StreamingResponse(
                io.BytesIO(response.content),
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={"Content-Disposition": f"attachment; filename={file.filename}.xlsx"}
            )

    except Exception as e:
        logger.error(f"Error converting PDF to Excel: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
