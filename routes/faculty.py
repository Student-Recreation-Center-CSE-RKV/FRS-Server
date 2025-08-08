from datetime import date, datetime
from pydantic import BaseModel
from models.StudentModel import AttendanceRecord
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Dict, List, Optional
from models.FacultyModel import AttendanceUpdate,AttendanceData, AttendanceData2,ConsolidatedAttendanceModel
from db import database
from . import auth

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
@router.get("/dashboard")
async def faculty_dashboard(date: str, user: dict = Depends(auth.get_current_user)):    
    """
    Optimized version: 
    - Fetches student and attendance records in bulk.
    - Reduces MongoDB queries for better performance.
    """
    email_address = user["email"]

    try:
        date_obj = datetime.strptime(date, "%Y-%m-%d")
        day = date_obj.strftime("%A").lower()
        is_future_date = date_obj > datetime.now()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")

    # 🔹 Fetch faculty details
    faculty = await faculty_collection.find_one({"email_address": email_address})
    if not faculty:
        raise HTTPException(status_code=404, detail="Faculty not found")

    years = ["E3"]
    subjects = []

    # 🔹 Fetch all subjects assigned to the faculty
    for year in years:
        assignments = await timetable_collections[year].find_one({"type": "assignments"})
        if assignments:
            for subject, data in assignments["subjects"].items():
                for record in data:
                    if record.get("faculty_username") == email_address:
                        subjects.append({"subject_name": subject, "year": year, "sections": record["sec"]})

    if not subjects:
        return {"message": "No subjects assigned to this faculty."}

    # 🔹 Fetch timetable data in one query per year
    day_wise_schedule = []
    for subject in subjects:
        year, subject_name, sections = subject["year"], subject["subject_name"], subject["sections"]
        timetable = await timetable_collections[year].find_one({}, {"_id": 0})

        if not timetable or day not in timetable:
            continue  # Skip if no timetable for this year or day

        for section in sections:
            section_schedule = timetable[day].get(section, {})
            if subject_name in section_schedule:
                day_wise_schedule.append({
                    "year": year, "section": section, "subject": subject_name, "periods": section_schedule[subject_name]
                })

    if not day_wise_schedule:
        return {"message": f"No classes scheduled for {day.capitalize()} for this faculty."}

    # 🔹 Fetch student data in one query
    student_query = {"year": {"$in": years}, "section": {"$in": [s["sections"] for s in subjects]}}
    students = await student_data.find(student_query, {"_id": 0, "id_number": 1, "year": 1, "section": 1}).to_list(length=None)

    # 🔹 Organize students by year-section
    student_dict = {}
    for student in students:
        key = (student["year"], student["section"])
        if key not in student_dict:
            student_dict[key] = []
        student_dict[key].append(student["id_number"])

    # 🔹 Fetch attendance records in one query
    attendance_query = {"id_number": {"$in": [s["id_number"] for s in students]}}
    attendance_records = await attendance_collections["E3"].find(attendance_query).to_list(length=None)

    # 🔹 Convert attendance records to a dictionary for quick lookup
    attendance_data = {record["id_number"]: record.get("attendance_report", {}) for record in attendance_records}

    # 🔹 Prepare final attendance details
    attendance_details = []
    for schedule in day_wise_schedule:
        year, section, subject_name, periods = schedule.values()
        student_ids = student_dict.get((year, section), [])

        if is_future_date:
            attendance_details.append({
                "year": year, "section": section, "subject": subject_name, "periods": periods,
                "no of classes": "N/A", "present_ids": "N/A", "absent_ids": "N/A"
            })
            continue

        present_ids, absent_ids = [], []
        no_of_classes = 0

        for student_id in student_ids:
            subject_attendance = attendance_data.get(student_id, {}).get(subject_name, {})
            if not subject_attendance:
                continue

            for record in subject_attendance.get("attendance", []):
                if record["date"] == date:
                    if record["status"] == "present":
                        present_ids.append(student_id)
                    elif record["status"] == "absent":
                        absent_ids.append(student_id)
                    no_of_classes = record["number_of_periods"]
                    break

        attendance_details.append({
            "year": year, "section": section, "subject": subject_name, "periods": periods,
            "no of classes": no_of_classes if no_of_classes > 0 else "N/A",
            "present_ids": present_ids or "N/A", "absent_ids": absent_ids or "N/A"
        })

    return {
        "date": date, "day": day.capitalize(),
        "faculty_email": email_address,
        "schedule": day_wise_schedule, "attendance": attendance_details
    }



@router.post("/mark-attendance")
async def update_attendance(attendance_data: AttendanceUpdate):
    print("📌 Received attendance update request")
    
    ids = attendance_data.ids
    subject = attendance_data.subject
    faculty_name = attendance_data.faculty_name
    year = attendance_data.year
    branch = attendance_data.branch
    section = attendance_data.section
    number_of_periods = attendance_data.number_of_periods

    today_date = datetime.today().strftime('%Y-%m-%d')  # Ensure today_date is defined
    print(f"📆 Today's date: {today_date}")

    collection = attendance_collections[year]

    # Fetch relevant students
    relevant_students = await student_data.find(
        {"year": year, "branch": branch, "section": section}
    ).to_list(length=None)

    if not relevant_students:
        print("⚠️ No students found for the given criteria.")
        raise HTTPException(status_code=404, detail="No students found for the given criteria.")
    
    print(f"👨‍🎓 Found {len(relevant_students)} students in section {section}")

    # Create a dictionary for quick lookup
    relevant_students_dict = {student["id_number"]: student for student in relevant_students}

    # Process each student ID in the provided list (Marking Present)
    for student_id in ids:
        student = relevant_students_dict.get(student_id)
        if not student:
            print(f"⚠️ Student ID {student_id} not found in database")
            raise HTTPException(status_code=404, detail=f"Student ID {student_id} not found")

        attendance_field = f"attendance_report.{subject}.attendance"

        print(f"✅ Marking Present: {student_id}")

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

    # Mark Absent for Students NOT in the List
    for student in relevant_students:
        if student["id_number"] not in ids:
            student_id = student["id_number"]
            print(f"🚨 Marking Absent: {student_id}")

            existing_entry = await collection.find_one({
                "id_number": student_id,
                f"{attendance_field}.date": today_date
            })

            if existing_entry:
                print(f"🔄 Updating existing attendance record to 'absent' for {student_id}")
                await collection.update_one(
                    {"id_number": student_id, f"{attendance_field}.date": today_date},
                    {"$set": {f"{attendance_field}.$.status": "absent"}}
                )
            else:
                print(f"🆕 Creating new attendance entry for {student_id}")
                await collection.update_one(
                    {"id_number": student_id},
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

    # Calculate Attendance Percentage
    for student in relevant_students:
        id_number = student["id_number"]
        attendance_record = await collection.find_one({"id_number": id_number})

        if not attendance_record:
            print(f"⚠️ No attendance record found for {id_number}, skipping calculation")
            continue

        print(f"📊 Calculating attendance for {id_number}")

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

        overall_attendance = (
            sum(subject_attendance_percentages) / len(subject_attendance_percentages)
            if subject_attendance_percentages else 0
        )

        print(f"📈 Updating overall attendance for {id_number}: {overall_attendance:.2f}%")

        await student_data.update_one(
            {"id_number": id_number},
            {"$set": {"overall_attendance": overall_attendance}},
            upsert=True
        )

    print("✅ Attendance update completed successfully!")

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
    attendance_data = await prefix.find_one({"id_number": id_number})
    total_percentage = calculate_percentage(attendance_data)['total_percentage']
    await database.student.update_one({"id_number": id_number,'$set':{"overall_attendance":total_percentage}})
    return {"status code": 200, "message": "Attendance updated successfully", "total_percentage": total_percentage}



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



@router.post('/consolidated-attendance')
async def consolidated_attendance(data: ConsolidatedAttendanceModel):
    id_number = data.id_number
    prefix = attendance_collections[data.year]
    percentage = 0
    attendance = await prefix.find_one({"id_number": id_number})
    if not attendance:
        return {"status": "Failed", "message": "No student record found."}

    for subject_name, attendance_data in data.subject_attendance.items():
        if subject_name not in attendance.get("attendance_report", {}):
            return {"status": "Failed", "message": f"Subject '{subject_name}' not found for student {id_number}."}

        number_of_periods = sum(entry.number_of_periods for entry in attendance_data.consolidated_attendance)
        number_of_classes = len(attendance["attendance_report"][subject_name]["attendance"])
        if number_of_classes == 0:
            return {"status": "Failed", "message": f"No attendance records found for subject '{subject_name}'."}
        
        percentage += (number_of_periods / number_of_classes) * 100

        await prefix.update_one(
            {"id_number": id_number, f"attendance_report.{subject_name}.consolidated_attendance": {"$exists": False}},
            {"$set": {f"attendance_report.{subject_name}.consolidated_attendance": []}}
        )

        update_query = {
            "$push": {
                f"attendance_report.{subject_name}.consolidated_attendance": {
                    "$each": [entry.dict() for entry in attendance_data.consolidated_attendance]
                }
            }
        }

        result = await prefix.update_one(
            {"id_number": id_number, f"attendance_report.{subject_name}": {"$exists": True}},
            update_query
        )

        if result.modified_count == 0:
            return {"status": "Failed", "message": f"Failed to update consolidated attendance for '{subject_name}'."}

    await database.student.update_one(
        {"id_number": id_number},
        {"$set": {'consolidated_percentage': percentage}}
    )

    return {"status": "Success", "message": "Consolidated attendance added successfully for all subjects."}
