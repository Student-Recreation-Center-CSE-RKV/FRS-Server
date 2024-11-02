from fastapi import APIRouter, Body, HTTPException
from bson import ObjectId
from models.FacultyModel import Faculty
from models.StudentModel import Student
from db.database import admin, faculty, student  # Assuming these collections exist
from routes import auth  # For password hashing and verification

router = APIRouter()

@router.post("/admin/login")
async def admin_login(username: str, password: str):
    faculty_member = await faculty.find_one({"email_address": username})
    if faculty_member and auth.verify_password(password, faculty_member['password']):
        if faculty_member.get('is_admin'):
            return {"message": "Login successful", "admin": faculty_member}
        else:
            raise HTTPException(status_code=403, detail="User  is not an admin")
    raise HTTPException(status_code=401, detail="Invalid username or password")

# Create User (Faculty or Student)
@router.post("/create-student", response_model=Student)
async def create_student(student_data: Student):
    # Check if the student already exists (optional)
    existing_student = await student.find_one({"id_number": student_data.id_number})
    if existing_student:
        raise HTTPException(status_code=400, detail="Student with this ID already exists.")
    # Insert the new student into the database
    result = await student.insert_one(student_data.dict())
    # Retrieve the newly created student document
    created_student = await student.find_one({"_id": result.inserted_id})
    return {"message": "Student created successfully", "student": created_student}
@router.post("/create-faculty", response_model=Faculty)
async def create_faculty(faculty_data: Faculty):
    # Check if the faculty already exists (optional)
    existing_faculty = await faculty.find_one({"email_address": faculty_data.email_address})
    if existing_faculty:
        raise HTTPException(status_code=400, detail="Faculty member with this email already exists.")
    # Insert the new faculty member into the database
    result = await faculty.insert_one(faculty_data.dict())
    # Retrieve the newly created faculty document
    created_faculty = await faculty.find_one({"_id": result.inserted_id})
    return {"message": "Faculty member created successfully", "faculty": created_faculty}

# View Admin Dashboard
@router.get("/admin/dashboard")
async def get_admin_dashboard(username: str):
    details = await admin.find_one({'username': username})
    if details:
        # Add more statistics here, like counts of faculty and students
        faculty_count = await faculty.count_documents({})
        student_count = await student.count_documents({})
        return {
            "admin_details": details,
            "faculty_count": faculty_count,
            "student_count": student_count
        }
    raise HTTPException(status_code=404, detail="Admin not found")

# Manage Attendance
@router.post('/manage-attendance')
async def manage_attendance(student_id: str, attendance: bool):
    # Here you would implement the logic to mark attendance
    # This can be a separate collection or within the student document
    res = await student.update_one({'id_number': student_id}, {'$set': {'attendance': attendance}})
    if res.modified_count > 0:
        return {'message': "Attendance updated successfully"}
    raise HTTPException(status_code=404, detail="Student not found or attendance not updated")

# Get All Users (Faculty and Students)
@router.get('/users')
async def get_all_users(user_type: str):
    if user_type == "faculty":
        faculty_list = await faculty.find().to_list(None)  # Get all faculty
        return {'faculty': faculty_list}
    elif user_type == "student":
        student_list = await student.find().to_list(None)  # Get all students
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

@router.put('/update-user')
async def update_user(user_type: str, identifier: str, data: dict = Body(...)):  # Use `data: dict = Body(...)`
    if user_type == "faculty":
        # Validate that the faculty exists
        existing_faculty = await faculty.find_one({'email_address': identifier})
        if not existing_faculty:
            raise HTTPException(status_code=404, detail="Faculty not found")
        # Update the faculty record
        faculty_data = Faculty(**data)  # Create a Faculty instance
        res = await faculty.update_one({'email_address': identifier}, {'$set': faculty_data.dict()})
        if res.modified_count > 0:
            return {'message': "Faculty updated successfully"}
        else:
            return {'message': "No changes made to the faculty record"}
    elif user_type == "student":
        # Validate that the student exists
        existing_student = await student.find_one({'id_number': identifier})
        if not existing_student:
            raise HTTPException(status_code=404, detail="Student not found")
        # Update the student record
        student_data = Student(**data)  # Create a Student instance
        res = await student.update_one({'id_number': identifier}, {'$set': student_data.dict()})
        if res.modified_count > 0:
            return {'message': "Student updated successfully"}
        else:
            return {'message': "No changes made to the student record"}
    raise HTTPException(status_code=400, detail="Invalid user type")