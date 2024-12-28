from typing import Literal, Union
from fastapi import APIRouter, Body, Depends, HTTPException
from bson import ObjectId
from models.FacultyModel import Faculty
from models.StudentModel import Student
from pydantic import BaseModel
from db.database import admin, faculty, student  # Assuming these collections exist
from routes import auth  # For password hashing and verification

router = APIRouter()

@router.post("/admin/login")
async def admin_login(email_address: str, password: str):
    faculty_member = await faculty.find_one({"email_address": email_address})
    if faculty_member and auth.verify_password(password, faculty_member['password']):
        if faculty_member.get('is_admin'):
            return {"message": "Login successful", "admin": faculty_member}
        else:
            raise HTTPException(status_code=403, detail="User  is not an admin")
    raise HTTPException(status_code=401, detail="Invalid username or password")

# Create User (Faculty or Student)
@router.post("/create-student", response_model=Student)
async def create_student(student_data: Student = Depends(Student)):
    # Check if the student already exists (optional)
    existing_student = await student.find_one({"id_number": student_data.id_number})
    if existing_student:
        raise HTTPException(status_code=400, detail="Student with this ID already exists.")
    # Insert the new student into the database
    student_data = student_data.model_dump()
    hash_pass = auth.get_password_hash(student_data['password'])
    student_data['password'] = hash_pass
    # print(data)
    res = await student.insert_one(student_data)
    if res.inserted_id and res.acknowledged:
        return {'message':True}
    else:
        return {'message':False}
   
@router.post("/create-faculty", response_model=Faculty)
async def create_faculty(faculty_data: Faculty = Depends(Faculty)):
    # Check if the faculty already exists (optional)
    existing_faculty = await faculty.find_one({"email_address": faculty_data.email_address})
    if existing_faculty:
        raise HTTPException(status_code=400, detail="Faculty member with this email already exists.")
    # Insert the new faculty member into the database
    faculty_data = faculty_data.model_dump()
    hash_pass = auth.get_password_hash(faculty_data['password'])
    faculty_data['password'] = hash_pass
    result = await faculty.insert_one(faculty_data)
    # Retrieve the newly created faculty document
    created_faculty = await faculty.find_one({"_id": result._id})
    return {"message": "Faculty member created successfully", "faculty": created_faculty}

# # View Admin Dashboard
# @router.get("/admin/dashboard")
# async def get_admin_dashboard(username: str):
#     details = await admin.find_one({'username': username})
#     if details:
#         # Add more statistics here, like counts of faculty and students
#         faculty_count = await faculty.count_documents({})
#         student_count = await student.count_documents({})
#         return {
#             "admin_details": details,
#             "faculty_count": faculty_count,
#             "student_count": student_count
#         }
#     raise HTTPException(status_code=404, detail="Admin not found")
# # Manage Attendance
# @router.post('/manage-attendance')
# async def manage_attendance(student_id: str, attendance: bool):
#     # Here you would implement the logic to mark attendance
#     # This can be a separate collection or within the student document
#     res = await student.update_one({'id_number': student_id}, {'$set': {'attendance': attendance}})
#     if res.modified_count > 0:
#         return {'message': "Attendance updated successfully"}
#     raise HTTPException(status_code=404, detail="Student not found or attendance not updated")

# Get All Users (Faculty and Students)
def convert_objectid_to_str(documents):
    if isinstance(documents, list):
        for document in documents:
            for key, value in document.items():
                if isinstance(value, ObjectId):
                    document[key] = str(value)
    elif isinstance(documents, dict):
        for key, value in documents.items():
            if isinstance(value, ObjectId):
                documents[key] = str(value)
    return documents

@router.get('/users')
async def get_all_users(user_type: str):
    if user_type == "faculty":
        faculty_list = await faculty.find().to_list(None)  # Get all faculty
        faculty_list = convert_objectid_to_str(faculty_list)  # Convert ObjectId to string
        return {'faculty': faculty_list}
    elif user_type == "student":
        student_list = await student.find().to_list(None)  # Get all students
        student_list = convert_objectid_to_str(student_list)  # Convert ObjectId to string
        return {'students': student_list}
    raise HTTPException(status_code=400, detail="Invalid user type")


# Delete User (Faculty or Student)
@router.delete('/delete-user')
async def delete_user(user_type: str, identifier: str):
    if user_type == "faculty":
        res = await faculty.delete_one(
            {'email_address': identifier})  # Assuming email_address is used to identify faculty
        if res.deleted_count > 0:
            return {'message': "Faculty deleted successfully"}
    elif user_type == "student":
        res = await student.delete_one({'id_number': identifier})  # Assuming id_number is used to identify students
        if res.deleted_count > 0:
            return {'message': "Student deleted successfully"}
    raise HTTPException(status_code=404, detail="User  not found or invalid user type")

@router.put('/update-faculty')
async def update_faculty(email: str,faculty_data: Faculty = Depends(Faculty)):
    existing_faculty = await faculty.find_one({'email_address': email})
    if not existing_faculty:
        raise HTTPException(status_code=404, detail="Faculty not found")

    faculty_data = faculty_data.model_dump()
    hash_pass = auth.get_password_hash(faculty_data['password'])
    faculty_data['password'] = hash_pass    
    res = await faculty.update_one(
            {'email_address': email},
            {'$set': faculty_data}
        )
    return {"message": "Faculty updated successfully"} if res.modified_count else {"message": "No changes made"}
 
 
@router.put('/update-student')
async def update_student(student_id: str,student_data: Student = Depends(Student)):   
    # Update logic for student
    existing_student = await student.find_one({'id_number': student_id})
    if not existing_student:
        raise HTTPException(status_code=404, detail="Student not found")
    student_data = student_data.model_dump()
    hash_pass = auth.get_password_hash(student_data['password'])
    student_data['password'] = hash_pass
    res = await student.update_one(
            {'id_number': student_id},
            {'$set': student_data}
        )
    return {"message": "Student updated successfully"} if res.modified_count else {"message": "No changes made"}

@router.get('/Scheduled_classes')
async def manage_attendance(date: str, year:str):
    
    return {}