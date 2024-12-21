from datetime import datetime
from models.StudentModel import AttendanceRecord
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from models.FacultyModel import StudentAttendance, AttendanceRequest, Attendance
from db import database

router = APIRouter()


collections = {
        'R19': database.R19,
        'R20': database.R20, 
        'R21': database.R21,
        'R22': database.R22,
    }



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


# Route to get attendance details for a specific student.

@router.get("/attendance/",response_model=dict)
async def get_attendance(
    student_id: Optional[str] = Query(None),
    branch: Optional[str] = Query(None),
    batch: Optional[str] = Query(None),
    sections: Optional[List[str]] = Query(None)
    ):
    
    if student_id:
        student_details = await database.student.find_one({"id_number": student_id})
        prefix = get_batch(student_id)
        if prefix is not None:
            attendance_report = await prefix.find_one({"id_number": student_id})
        else:
            attendance_report = None
        if student_details and attendance_report:
            attendance_summary = calculate_percentage(attendance_report)
            return { "student_details" : {"student_id": student_id,
                "first_name": student_details["first_name"],
                "last_name" : student_details["last_name"],
                "year" : student_details["year"],
                "branch" : student_details["branch"],
                "section":student_details["section"],
                "phone_number" : student_details["phone_number"]} , "attendance_report": attendance_report["attendance_report"] ,
                "attendance_summary" : attendance_summary
            
            }
        else:
            raise HTTPException(status_code=404, detail="Student details or attendance details are not found")
    elif batch is not None and branch is not None and sections is not None:
        students = await database.student.find({"branch": branch, "section": {"$in": sections}}).to_list(None)
        if students:
            result = []
            for student in students:
                student_id = student["id_number"]
                prefix = get_batch(batch)
                attendance_data = await prefix.find_one({"id_number": student_id})
                if attendance_data is not None:
                    attendance_summary = calculate_percentage(attendance_data)
                    result.append({
                        "student_id": student_id,
                        "first_name": student["first_name"],
                        "last_name": student["last_name"],
                        "Section" : student["section"],
                        "attendance_summary": attendance_summary
                    })
                else:
                    result.append({
                        "student_id": student_id,
                        "first_name": student["first_name"],
                        "last_name": student["last_name"],
                        "Section" : student["section"],
                        "attendance_summary": None
                    })
            result.sort(key=lambda x: (x["Section"], x["student_id"]))
            return {"students": result}
        else:
            raise HTTPException(status_code=404, detail="No students found for the given criteria")
    else:
        raise HTTPException(status_code=400, detail="Invalid query parameters")
    


# function to calculate the percentage of the attendance
def calculate_percentage(attendance_report):
    result = {}
    total_classes = 0
    total_present = 0

    for subject, data in attendance_report['attendance_report'].items():
        num_classes = len(data['attendance'])
        
        num_present = 0
        for entry in data['attendance']: 
            if entry['status'] == 'present':
                num_present+=1
        
        percentage = (num_present / num_classes) * 100 if num_classes > 0 else 0

        result[subject] = {
            'subject_name': data['subject_name'],
            'faculty_name': data['faculty_name'],
            'num_classes': num_classes,
            'num_present': num_present,
            'percentage': percentage
        }

        total_classes += num_classes
        total_present += num_present

    total_percentage = (total_present / total_classes) * 100 if total_classes > 0 else 0
    
    result['total'] = {
        'total_classes': total_classes,
        'total_present': total_present,
        'total_percentage': total_percentage
    }

    return result


def get_batch(string: str):
    return collections[string[:3]]



