from fastapi import APIRouter

router = APIRouter()

@router.get("/dashboard")
async def get_student_dashboard():
    return {"message": "Student Dashboard"}
