from fastapi import APIRouter,Body, HTTPException
from bson import ObjectId
from . import auth
from models.StudentModel import Student,ProfileUpdate,PasswordChange,AttendanceRecord
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

# View Profile
@router.get("/students/{id_number}/profile/")
async def view_profile(id_number: str):
    details = await student.find_one({"id_number": id_number})
    if not details:
        raise HTTPException(status_code=404, detail="Student not found")
    details["_id"] = str(details["_id"])  # Convert ObjectId to string
    return details

# Change Password
@router.put("/students/{id_number}/change-password/")
async def change_password(id_number: str, data: PasswordChange):
    details = await student.find_one({"id_number": id_number})
    if not details:
        raise HTTPException(status_code=404, detail="Student not found")
    if details["password"] != data.current_password:  # Replace with secure hash comparison
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    await student.update_one({"id_number": id_number}, {"$set": {"password": data.new_password}})
    return {"message": "Password changed successfully"}

# View Attendance Records
@router.get("/students/{id_number}/view_attendance/")
async def view_attendance(id_number: str):
    details = await student.find_one({"id_number": id_number}, {"attendance_records": 1})
    if not details or "attendance_records" not in details:
        return []
    return details["attendance_records"]

# View Attendance Summary
@router.get("/students/{id_number}/attendance/summary/")
async def view_attendance_summary(id_number: str):
    details = await student.find_one({"id_number": id_number}, {"attendance_records": 1})
    if not details or "attendance_records" not in details:
        return {"percentage": 0, "total_sessions": 0, "attended_sessions": 0}
    records = details["attendance_records"]
    total_sessions = len(records)
    attended_sessions = sum(1 for r in records if r["status"] == "present")
    percentage = (attended_sessions / total_sessions) * 100 if total_sessions > 0 else 0
    return {
        "percentage": percentage,
        "total_sessions": total_sessions,
        "attended_sessions": attended_sessions
    }

