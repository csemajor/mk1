from fastapi import APIRouter

router = APIRouter()

@router.get("/")
async def root():
    return {"message": "Eventra API is running"}

@router.get("/test")
async def test_endpoint():
    return {"status": "success"}
