from fastapi import APIRouter
from db.database import student 
router = APIRouter()



@router.get("/")
async def get_name():
    temp = await student.find_one({})
    return {'data':temp}

