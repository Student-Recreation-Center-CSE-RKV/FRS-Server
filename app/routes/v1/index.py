from fastapi import APIRouter
from app.db.database import collection
router = APIRouter()



@router.get("/")
async def get_name():
    temp = collection.find_one({})
    print(temp)
    return {'name':'FRS+Server'}