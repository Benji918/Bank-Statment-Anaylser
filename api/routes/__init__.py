from fastapi import APIRouter
from api.routes.pdf_excel import pdf_router

router = APIRouter()
router.include_router(pdf_router)