from fastapi import APIRouter,Body
from bson import ObjectId
from . import auth
from models.StudentModel import Student
from db.database import student
router = APIRouter()

@router.get("/dashboard")
async def get_student_dashboard(id_number : str = Body(...,embed=True)):
    details = await student.find_one({'id_number':id_number})
    if details:
        if isinstance(details,dict):
            for key,value in details.items():
                if isinstance(value,ObjectId):
                    details[key] = str(value)
    return details


@router.post('/create-student')
async def create_student(data:Student):
    data = data.model_dump()
    hash_pass = auth.get_password_hash(data['password'])
    data['password'] = hash_pass
    res = await student.insert_one(data)
    if res.inserted_id and res.acknowledged:
        return {'messaage':True}
    else:
        return {'messaage':False}

@router.post('/delete-student')
async def delete_student(id_number:str= Body(..., embed=True)):
    res = await student.delete_one({'id_number':id_number})
    if res.acknowledged:
        return {'messaage':True}
    else:
        return {'messaage':False}

@router.post('/update-student')
async def update_student():
    pass

