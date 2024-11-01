from fastapi import APIRouter

router = APIRouter()

@router.get("/dashboard")
async def get_faculty_dashboard():
    return {"message": "Faculty Dashboard"}
