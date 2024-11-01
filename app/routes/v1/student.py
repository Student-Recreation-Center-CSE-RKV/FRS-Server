from fastapi import APIRouter,Body
from pydantic import BaseModel
from .auth import create_access_token
from models.StudentModel import Student
from crud.student import student_insert , student_delete , get_details
from db.database import student
router = APIRouter()

@router.get("/dashboard")
async def get_student_dashboard(id_number : str = Body(...,embed=True)):
    details = await get_details(id_number)
    return details



@router.post('/create-student')
async def create_student(data:Student):
    res = await student_insert(data.model_dump())
    print('hello')
    return {'message':res}


@router.post('/delete_student')
async def delete_student(id_number:str= Body(..., embed=True)):
    res = await student_delete(id_number)
    return {'messaage':res}

@router.post('/update_student')
async def update_student():
    pass

