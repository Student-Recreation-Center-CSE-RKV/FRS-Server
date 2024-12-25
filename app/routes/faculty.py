from datetime import date
from pydantic import BaseModel
from models.StudentModel import AttendanceRecord
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Dict, List, Optional
from models.FacultyModel import AttendanceUpdate,AttendanceRecord,StudentAttendance, Attendance
from db import database

router = APIRouter()

collections = {
        'E1': database.E1,
        'E2': database.E2, 
        'E3': database.E3,
        'E4': database.E4,
    }
today_date = str(date.today()) 

student_data=database.student
@router.post("/mark_attendance/")
async def update_attendance(attendance_data: AttendanceUpdate):
    ids = attendance_data.ids
    subject = attendance_data.subject
    faculty_name = attendance_data.faculty_name
    year = attendance_data.year
    branch = attendance_data.branch
    section = attendance_data.section

    collection = collections[year]

    relevant_students = await student_data.find(
        {"year": year, "branch": branch, "section": section}
    ).to_list(length=None)
    
    if not relevant_students:
        raise HTTPException(status_code=404, detail="No students found for the given criteria.")
    
    # Create a dictionary for quick lookups by id_number
    relevant_students_dict = {student["id_number"]: student for student in relevant_students}

    # Process each student ID in the provided list
    for student_id in ids:
        student = relevant_students_dict.get(student_id)
        if not student:
            raise HTTPException(status_code=404, detail=f"Student ID {student_id} not found")
        
        attendance_field = f"attendance.{subject}"
                
        # Check if an attendance entry for today already exists
        existing_entry = await collection.find_one({
            "id_number": student_id,
            f"{attendance_field}.date": today_date,
            f"{attendance_field}.faculty_name": faculty_name
         })
        
        if existing_entry:
            # Update the existing entry's status to "present"
            await collection.update_one(
                {"id_number": student_id, f"{attendance_field}.date": today_date},
                {"$set": {f"{attendance_field}.$.status": "present"}}
            )
        else:
            # Add a new attendance entry
            await collection.update_one(
                {"id_number": student_id},
                {"$push": {attendance_field: {"faculty_name": faculty_name, "date": today_date, "status": "present"}}},
                upsert=True
            ) 
        
    # Mark absent for students not in the list of IDs
    for student in relevant_students:
        if student["id_number"] not in ids:
            attendance_field = f"attendance.{subject}"
            # subject_summary_field = f"subject_summary.{subject}"

            # Check if attendance for this date already exists
            existing_entry =await  collection.find_one({
                "id_number": student["id_number"],
                f"{attendance_field}.date": today_date,
                f"{attendance_field}.faculty_name": faculty_name
            })

            if existing_entry:
            #     # Update status to absent if entry exists
                await collection.update_one(
                    {"id_number": student["id_number"], f"{attendance_field}.date":today_date},
                    {"$set": {f"{attendance_field}.$.status": "absent"}}
                )
            else:
                # Add new attendance entry with absent status
                await collection.update_one(
                    {"id_number": student["id_number"]},
                    {"$push": {attendance_field: {"faculty_name": faculty_name, "date": today_date, "status": "absent"}}},
                    upsert=True
                )     
    for student in relevant_students:
        id_number = student["id_number"]
        attendance_record = await collection.find_one({"id_number": id_number})

        if not attendance_record:
            continue

        attendance = attendance_record.get("attendance", {})
        per_subject_attendance = {}
        subject_attendance_percentages = []

        for subject, records in attendance.items():
            total_classes = len(records)
            present_classes = sum(1 for record in records if record["status"] == "present")
            attendance_percentage = (present_classes / total_classes) * 100 if total_classes > 0 else 0
            per_subject_attendance[subject] = attendance_percentage
            subject_attendance_percentages.append(attendance_percentage)

        # Calculate overall attendance as the average of subject attendance percentages
        overall_attendance = (
            sum(subject_attendance_percentages) / len(subject_attendance_percentages)
            if subject_attendance_percentages else 0
        )

        # Update the student's attendance summary
        await student_data.update_one(
            {"id_number": id_number},
            {"$set": {"overall_attendance": overall_attendance}},
            upsert=True
        )
 

    return {
        "message": "Attendance updated successfully",
        "updated_ids": ids,
        "absent_marked_ids": [
            student["id_number"] for student in relevant_students if student["id_number"] not in ids
        ]
    }

@router.get("/attendance/student/{id_number}")
async def calculate_student_attendance(id_number: str):
    # Find the student in the database
    student_record = await student_data.find_one({"id_number": id_number})
    if not student_record:
        raise HTTPException(status_code=404, detail=f"Student ID {id_number} not found.")
    
    year = student_record["year"]
    collection = collections.get(year)
    
    # if not collection:
    #     raise HTTPException(status_code=404, detail="No attendance records found for the student's year.")
    
    # Retrieve the student's attendance data
    attendance_record = await collection.find_one({"id_number": id_number})
    if not attendance_record or "attendance" not in attendance_record:
        return {
            "id_number": id_number,
            "message": "No attendance records found for this student.",
            "per_subject_attendance": {},
            "overall_attendance": 0.0
        }
    
    # Attendance processing
    attendance = attendance_record.get("attendance", {})
    per_subject_attendance = {}
    subject_attendance_percentages = []

    for subject, records in attendance.items():
        # Ensure records are valid as per the AttendanceRecord model
        valid_records = [
            record for record in records 
            if "status" in record and record["status"] in {"present", "absent"}
        ]
        
        present_count = sum(1 for record in valid_records if record["status"] == "present")
        total_count = len(valid_records)
        
        subject_percentage = ((present_count / total_count )* 100) if total_count > 0 else 0.0
        per_subject_attendance[subject] = {
            "present": present_count,
            "total": total_count,
            "percentage": subject_percentage
        }
        
        # Store the percentage for averaging later
        subject_attendance_percentages.append(subject_percentage)

    # Calculate overall subjects attendance as the average of subject percentages
    overall_attendance = (
        sum(subject_attendance_percentages) / len(subject_attendance_percentages)
        if subject_attendance_percentages else 0.0
    )
    if "overall_attendance" in student_record:
        # Update existing overall attendance
        await student_data.update_one(
            {"id_number": id_number},
            {"$set": {"overall_attendance": overall_attendance}}
        )
    else:
        # Insert new overall attendance field
        await student_data.update_one(
            {"id_number": id_number},
            {"$set": {"overall_attendance": overall_attendance}},
            upsert=True
        )

    return {
        "id_number": id_number,
        "per_subject_attendance": per_subject_attendance,
        "overall_attendance": overall_attendance
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



