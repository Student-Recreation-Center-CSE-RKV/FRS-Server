from datetime import datetime
from models.StudentModel import AttendanceRecord
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from models.FacultyModel import StudentAttendance, AttendanceRequest, Attendance
from db import database

router = APIRouter()

# Route to grant access to students
@router.post("/students/access", response_model=str)
async def grant_access(student_id: str):
    students_data = await database.student.find().to_list(100)
    student = next((s for s in students_data if str(s["id_number"]) == str(student_id)), None)
    # print(student)
    if student:
        return f"Access granted to student {student['first_name']}"
    raise HTTPException(status_code=404, detail="Student not found")
   
@router.post("/attendance/update", response_model=str)
async def update_attendance(student_id: str, attendance_count: int):
    students_data = await database.student.find().to_list(100)
    success = await database.student.update_one(
            {"id_number": student_id},  # Match by the student's ID
            {"$set": {"attendance": attendance_count}}  # Set attendance to 0
        )
    if not success:
        raise HTTPException(status_code=404, detail="Student not found.")
    return f"Attendance updated for student with ID {student_id}."

     
#To initialise all students attendance initially to 0
@router.post("/attendance/initialize", response_model=str)
async def initialize_attendance():
    students_data = await database.student.find().to_list(100)
    if not students_data:
        raise HTTPException(status_code=404, detail="No students found in the database.")
    for student in students_data:
        student_id = student.get("id_number")
        # Update the attendance field directly, setting it to 0 if it's not present or if it exists
        await database.student.update_one(
            {"id_number": student_id},  # Match by the student's ID
            {"$set": {"attendance": 0}}  # Set attendance to 0
        )
    return "Overall attendance initialized successfully for all students."

#  Route to get all students' attendance
@router.get("/attendance", response_model=List[dict])
async def get_all_attendance():
    students_data = await database.student.find().to_list(100)
    return [
    {
        "id": student.get("id_number"),
        "name": student.get("first_name"),
        "attendance": student.get("attendance", None),
    }
     for student in students_data
    ]

# Route to mark attendance of a  student accc to course ID
@router.post("/students/{id_number}/log_attendance/")
async def log_attendance(id_number: str, attendance: AttendanceRecord):
    record = attendance.dict()
    result = await database.student.update_one(
        {"id_number": id_number},
        {"$push": {"attendance_records": record}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Student not found")
    return {"message": "Attendance logged successfully", "record": record}


# Route to mark attendance for a single student with a timestamp
@router.post("/attendance/mark", response_model=str)
async def mark_attendance(attendance: Attendance=Depends(Attendance)):
    student = await database.student.find_one({"id_number": attendance.student_id})
    if student:
        # Get the current timestamp
        timestamp = datetime.utcnow().isoformat()

        # Increment attendance and add the timestamp
        new_attendance = student.get("attendance", 0) + 1
        timestamps = student.get("attendance_timestamps", [])
        timestamps.append(timestamp)

        # Update the student document
        await database.student.update_one(
            {"id_number": attendance.student_id},
            {"$set": {"attendance": new_attendance, "attendance_timestamps": timestamps}}
        )

        return f"Attendance updated for student {student['first_name']} at {timestamp}"
    raise HTTPException(status_code=404, detail="Student not found")


# Route to mark attendance for multiple students with timestamps
@router.post("/faculty/mark-attendance", response_model=str)
async def mark_attendance_bulk(year: str, branch: str, section: str, subject: str, student_ids: List[str]):
    course_filter = {"year": year, "branch": branch, "section": section, "subject": subject}
    timestamp = datetime.utcnow().isoformat()

    for student_id in student_ids:
        student = await database.student.find_one({"id_number": student_id, **course_filter})
        if student:
            new_attendance = student.get("attendance", 0) + 1
            timestamps = student.get("attendance_timestamps", [])
            timestamps.append(timestamp)

            await database.student.update_one(
                {"id_number": student_id, **course_filter},
                {"$set": {"attendance": new_attendance, "attendance_timestamps": timestamps}}
            )

    return f"Attendance marked for {len(student_ids)} students in {subject} at {timestamp}"


# Route to get attendance for a specific student, including timestamps
@router.get("/attendance/{student_id}", response_model=dict)
async def get_attendance(student_id: str):
    student = await database.student.find_one({"id_number": student_id})
    if student:
        return {
            "student_id": student_id,
            "name": student["first_name"],
            "attendance": student.get("attendance", 0),
            "timestamps": student.get("attendance_timestamps", []),
        }
    raise HTTPException(status_code=404, detail="Student not found")


# Route to get attendance for all students, including timestamps
@router.get("/attendance", response_model=List[dict])
async def get_all_attendance():
    students_data = await database.student.find().to_list(100)
    return [
        {
            "student_id": student["id_number"],
            "name": student["first_name"],
            "attendance": student.get("attendance", 0),
            "timestamps": student.get("attendance_timestamps", []),
        }
        for student in students_data
    ]
