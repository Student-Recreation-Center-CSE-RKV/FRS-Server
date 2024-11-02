from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from models.FacultyModel import StudentAttendance, AttendanceRequest, Attendance
from db import database

router = APIRouter()

students_data = [
    {"id": "S001", "name": "Alice Johnson", "attendance": {"Math": 28, "Physics": 25}},
    {"id": "S002", "name": "Bob Smith", "attendance": {"Math": 25, "Chemistry": 20}},
    {"id": "S003", "name": "Charlie Brown", "attendance": {"Math": 29, "Biology": 24}},
    {"id": "S004", "name": "David Wilson", "attendance": {"Physics": 30, "Math": 28}},
    {"id": "S005", "name": "Eva Green", "attendance": {"Chemistry": 20, "Physics": 18}},
    {"id": "S006", "name": "Frank Black", "attendance": {"Biology": 22, "Physics": 26}},
]

# Route to grant access to students
@router.post("/students/access", response_model=str)
async def grant_access(student_id: str):
    student = next((s for s in students_data if s["id"] == student_id), None)
    if student:
        return f"Access granted to student {student['name']}"
    raise HTTPException(status_code=404, detail="Student not found")

# Route to mark attendance for a student
@router.post("/attendance/mark", response_model=str)
async def mark_attendance(attendance: Attendance):
    student = next((s for s in students_data if s["id"] == attendance.student_id), None)
    if student:
        student["attendance"][attendance.subject] += 1  # Assuming subject is passed in Attendance
        return f"Attendance updated for student {student['name']}"
    raise HTTPException(status_code=404, detail="Student not found")

# Route to get attendance for a specific student
@router.get("/attendance/{student_id}", response_model=dict)
async def get_attendance(student_id: str):
    student = next((s for s in students_data if s["id"] == student_id), None)
    if student:
        return {
            "student_id": student_id,
            "name": student["name"],
            "attendance": student["attendance"],
        }
    raise HTTPException(status_code=404, detail="Student not found")

# # Route to get all students' attendance
# @router.get("/attendance", response_model=List[dict])
# async def get_all_attendance():
#     return [
#         {
#             "student_id": student["id"],
#             "name": student["name"],
#             "attendance": student["attendance"],
#         }
#         for student in students_data
#     ]

# Function to filter students by name
def filter_students_by_name(query: str):
    return [student for student in students_data if query.lower() in student["name"].lower()]

@router.get("/attendance/")
async def get_attendance_data(
    year: str, branch: str, section: str, subject: str, search_query: Optional[str] = Query(None)
) -> List[StudentAttendance]:
    """
    Retrieves attendance data for a specified year, branch, section, and subject.
    Optionally filters students by name if search_query is provided.
    """
    filtered_students = filter_students_by_name(search_query) if search_query else students_data
    return [StudentAttendance(**student) for student in filtered_students]

@router.get("/total-classes")
async def get_total_classes(year: str, branch: str, section: str, subject: str) -> int:
    """
    Returns the total number of classes held for the specified course.
    """
    total_classes = 30  # Replace with actual calculation
    return total_classes
from fastapi import APIRouter

router = APIRouter()

@router.get("/dashboard")
async def get_faculty_dashboard():
    return {"message": "Faculty Dashboard"}
