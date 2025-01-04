from datetime import date, datetime
from pydantic import BaseModel
from models.StudentModel import AttendanceRecord
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Dict, List, Optional
from models.FacultyModel import AttendanceUpdate,AttendanceData, AttendanceData2
from db import database


router = APIRouter()

attendance_collections = {
        'E1': database.E1,
        'E2': database.E2, 
        'E3': database.E3,
        'E4': database.E4,
    }
timetable_collections={
    'E1':database.E1_timetable,
    'E2':database.E2_timetable,
    'E3':database.E3_timetable,
    'E4':database.E4_timetable,
}
today_date = str(date.today()) 
student_data=database.student
faculty_collection=database.faculty
@router.get("/faculty/dashboard/")
async def faculty_dashboard(email_address: str, date: str):
    """
    Displays all the classes available for a faculty on a specific date.
    If the attendance for a class is not recorded (e.g., future dates), it shows 'N/A' for attendance.
    """
    try:
        # Convert the date string into a datetime object
        date_obj = datetime.strptime(date, "%Y-%m-%d")
        # Get the day of the week (e.g., Monday, Tuesday)
        day = date_obj.strftime("%A").lower()

        # Check if the date is in the future
        current_date = datetime.now()
        is_future_date = date_obj > current_date
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")

    # Step 1: Fetch faculty details using email address
    faculty = await faculty_collection.find_one({"email_address": email_address})
    if not faculty:
        raise HTTPException(status_code=404, detail="Faculty not found")

    subjects = faculty.get("subjects", [])  # List of subjects with year and sections
    if not subjects:
        return {"message": "No subjects assigned to this faculty."}

    # Step 2: Fetch timetable for the selected day for all assigned years/sections
    day_wise_schedule = []
    for subject in subjects:
        subject_name = subject["subject_name"]
        year = subject["year"]
        sections = subject["sections"]

         # Dynamically select the timetable collection for the given year
        timetable_collection = timetable_collections[year]
        # if not timetable_collection:
        #     raise HTTPException(status_code=404, detail=f"No timetable collection for year: {year}")

        # Fetch the timetable for the specific year
        timetable = await timetable_collection.find_one({})
        if not timetable:
            raise HTTPException(status_code=404, detail=f"Timetable not found for year: {year}")

        # Check if the day exists in the document
        if day not in timetable:
            raise HTTPException(status_code=404, detail=f"No timetable found for day: {day}")

        # Extract the day's schedule
        day_schedule = timetable[day]  
            # Filter the timetable to include only the relevant subject and sections
        for section in sections:
            section_schedule = day_schedule.get(section, {})
            for subject_key, periods in section_schedule.items():
                if subject_key == subject_name:
                    # for period in periods:
                        day_wise_schedule.append({
                            "year": year,
                            "section": section,
                            "subject": subject_name,
                            "periods": periods,
                            
                        })
    if not day_wise_schedule:
        return {"message": f"No classes scheduled for {day.capitalize()} for this faculty."}

    # Step 3: Fetch attendance for completed classes or set to 'N/A' for future dates
    attendance_details = []
    for schedule in day_wise_schedule:
        year = schedule["year"]
        section = schedule["section"]
        subject_name = schedule["subject"]
        periods = schedule["periods"]

        # Dynamically select the attendance collection for the given year
        attendance_collection = attendance_collections.get(year)
        # if not attendance_collection:
        #     raise HTTPException(status_code=404, detail=f"No attendance collection for year: {year}")

        if is_future_date:
            # For future dates, attendance is 'N/A'
            attendance_details.append({
                "year": year,
                "section": section,
                "subject": subject_name,
                "periods": periods,
                "no of classes":"N/A",
                "present_ids": "N/A",
                "absent_ids": "N/A"
            })
            continue

        # Fetch students for the section
        students_to_check = await student_data.find(
            {"year": year, "section": section}
        ).to_list(length=None)

        if not students_to_check:
            attendance_details.append({
                "year": year,
                "section": section,
                "subject": subject_name,
                "periods": periods,
                "no of classes":"N/A",
                "present_ids": "N/A",
                "absent_ids": "N/A"
            })
            continue

        # Initialize attendance lists for the subject
        present_ids = []
        absent_ids = []
        no_of_classes=0
        for student in students_to_check:
            student_id = student["id_number"]

            # Fetch the student's attendance record
            attendance_record = await attendance_collection.find_one({"id_number": student_id})
            if not attendance_record:
                continue

            # Get the attendance report
            attendance_report = attendance_record.get("attendance_report", {})
            subject_attendance = attendance_report.get(subject_name, {})

            if not subject_attendance:
                continue

            # Check attendance for the specific date
            attendance_records = subject_attendance.get("attendance", [])
            for record in attendance_records:
                if record["date"] == date:
                    if record["status"] == "present":
                        present_ids.append(student_id)
                    elif record["status"] == "absent":
                        absent_ids.append(student_id)
                    no_of_classes=record["number_of_periods"]
                    break  # Avoid processing the same record again
           
        # Append attendance details for the section and subject
        attendance_details.append({
            "year": year,
            "section": section,
            "subject": subject_name,
            "periods": periods,
            "no of classes":no_of_classes if no_of_classes>0 else "N/A",
            "present_ids": present_ids if present_ids else "N/A",
            "absent_ids": absent_ids if absent_ids else "N/A"
        })

    # Final validation to ensure consistent results
    if not attendance_details:
        return {"message": f"No attendance records found for the date {date}."}

    # Combine timetable and attendance details
    result = {
        "date": date,
        "day": day.capitalize(),
        "faculty_email": email_address,
        "schedule": day_wise_schedule,
        "attendance": attendance_details,
    }
    return result

@router.post("/mark_attendance/")
async def update_attendance(attendance_data: AttendanceUpdate):
    ids = attendance_data.ids
    subject = attendance_data.subject
    faculty_name = attendance_data.faculty_name
    year = attendance_data.year
    branch = attendance_data.branch 
    section = attendance_data.section
    number_of_periods = attendance_data.number_of_periods

    collection = attendance_collections[year]

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
        
        attendance_field = f"attendance_report.{subject}.attendance"
        # Add or update attendance entry for present students
        
        await collection.update_one(
            {"id_number": student_id},
            {
                "$set": {f"attendance_report.{subject}.faculty_name": faculty_name},
                "$push": {attendance_field: {
                    "date": today_date,
                    "status": "present",
                    "number_of_periods": number_of_periods
                }}
            },
            upsert=True
        )
    # Mark absent for students not in the list of IDs
    for student in relevant_students:
        if student["id_number"] not in ids:
            # attendance_field = f"attendance.{subject}"
            # # subject_summary_field = f"subject_summary.{subject}"
            existing_entry = await collection.find_one({
                "id_number": student["id_number"],
                f"{attendance_field}.date": today_date
            })

            # Check if attendance for this date already exists
            if existing_entry:
                # Update status to absent if entry exists
                await collection.update_one(
                    {"id_number": student["id_number"], f"{attendance_field}.date": today_date},
                    {"$set": {f"{attendance_field}.$.status": "absent"}}
                )
            else:
                # Add new attendance entry with absent status
                await collection.update_one(
                    {"id_number": student["id_number"]},
                    {
                        "$set": {f"attendance_report.{subject}.faculty_name": faculty_name},
                        "$push": {attendance_field: {
                            "date": today_date,
                            "status": "absent",
                            "number_of_periods": number_of_periods
                        }}
                    },
                    upsert=True
                )
    for student in relevant_students:
        id_number = student["id_number"]
        attendance_record = await collection.find_one({"id_number": id_number})

        if not attendance_record:
            continue

        attendance_report = attendance_record.get("attendance_report", {})
        per_subject_attendance = {}
        subject_attendance_percentages = []

        for subject, subject_data in attendance_report.items():
            attendance_entries = subject_data.get("attendance", [])
            total_classes = len(attendance_entries)
            present_classes = sum(1 for record in attendance_entries if record["status"] == "present")
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
    collection = attendance_collections.get(year)

    # if not collection:
    #     raise HTTPException(status_code=404, detail="No attendance records found for the student's year.")
    
    # Retrieve the student's attendance data
    attendance_record = await collection.find_one({"id_number": id_number})
    if not attendance_record :
        return {
            "id_number": id_number,
            "message": "No attendance records found for this student.",
            "per_subject_attendance": {},
            "overall_attendance": 0.0
        }
    attendance_report = attendance_record.get("attendance_report", {})
    per_subject_attendance = {}
    subject_attendance_percentages = []

    for subject, subject_data in attendance_report.items():
        attendance_entries = subject_data.get("attendance", [])
        total_classes = len(attendance_entries)
        present_classes = sum(1 for record in attendance_entries if record["status"] == "present")
        attendance_percentage = (present_classes / total_classes) * 100 if total_classes > 0 else 0
        per_subject_attendance[subject] = attendance_percentage
        subject_attendance_percentages.append(attendance_percentage)

    # Calculate overall attendance as the average of subject attendance percentages
    overall_attendance = (
        sum(subject_attendance_percentages) / len(subject_attendance_percentages)
        if subject_attendance_percentages else 0
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
@router.post("/manage-attendance", response_model=dict)
async def manage_attendance(data : AttendanceData2):
    id_number = data.id_number
    year = data.year
    attendance_report = data.attendance_report
    prefix = attendance_collections[year]
    previous_data = await prefix.find_one({'id_number':id_number})
    if previous_data is None:
        raise HTTPException(status_code=404, detail="Student data not found")
    for subject, subject_data in attendance_report.items():
        existing_attendance = {
            entry["date"]: entry
            for entry in previous_data["attendance_report"][subject]["attendance"]
        }
        print(existing_attendance)
        for updated_entry in subject_data.attendance:
            existing_attendance[updated_entry.date] = updated_entry.dict()
        previous_data["attendance_report"][subject]["attendance"] = list(
            existing_attendance.values()
        )
    await database.E1.update_one(
        {"id_number": id_number},
        {"$set": {"attendance_report": previous_data["attendance_report"]}},
    )

    return {"status code": 200, "message": "Attendance updated successfully" }



# Route to get attendance details for a specific student and for all students.
@router.get("/attendance/",response_model=dict)
async def get_attendance(
    student_id: Optional[str] = Query(None),
    branch: Optional[str] = Query(None),
    year: str = Query(None),
    sections: Optional[List[str]] = Query(None)
    ):
    if student_id and year:
        student_details = await database.student.find_one({"id_number": student_id})
        prefix = attendance_collections[year]
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
    elif year is not None and branch is not None and sections is not None:
        students = await database.student.find({"branch": branch.lower(), "year":year,"section": {"$in": sections}}).to_list(None)
        if students:
            result = []
            for student in students:
                student_id = student["id_number"]
                prefix = attendance_collections[year]
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
    
    total_percentage = 0
    for subject, data in attendance_report['attendance_report'].items():
        num_classes = 0
        num_present = 0
        for entry in data['attendance']: 
            num_classes += entry['number_of_periods']
            if entry['status'] == 'present':
                num_present+=entry['number_of_periods']
        
        percentage = (num_present / num_classes) * 100 if num_classes > 0 else 0
        total_percentage += percentage
        result[subject] = {
            'faculty_name': data['faculty_name'],
            'num_classes': num_classes,
            'num_present': num_present,
            'percentage': percentage
        }


    total_percentage = total_percentage / len(attendance_report['attendance_report']) if len(attendance_report['attendance_report']) > 0 else 0
    
    result['total_percentage'] = {
        'total_percentage': total_percentage
    }

    return result





