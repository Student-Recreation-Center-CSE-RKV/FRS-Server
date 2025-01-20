from datetime import datetime
from email import message
from math import e
from pickle import EXT2
from re import sub
from typing import Dict, List, Literal, Union
from venv import create
from fastapi import APIRouter, Body, Depends, HTTPException, Query
from bson import ObjectId
from models.AdminModel import ExamTimetable,UpdateCRRequest,YearAssignment
from numpy import number
from models.FacultyModel import Attendance, Faculty
from models.StudentModel import Student
from pydantic import BaseModel
from db import database
from db.database import db,admin, faculty, student,db2,db3 ,db4,db5 # Assuming these collections exist
from routes import auth  # For password hashing and verification
from fastapi.responses import StreamingResponse
import json
from openpyxl import Workbook
from openpyxl.styles import Alignment,Font,Border,Side
from openpyxl.utils import get_column_letter
from io import BytesIO
import os
from models.AdminModel import TimeTableRequest

attendance_collections = {
        'E1': database.E1,
        'E2': database.E2, 
        'E3': database.E3,
        'E4': database.E4
    }

exam_timetable_collections = {
    'E1': database.E1_exam_timetable,
    'E2': database.E2_exam_timetable,
    'E3': database.E3_exam_timetable,
    'E4': database.E4_exam_timetable,
        }
student_collections = {
    'E1': database.E1_student,
    'E2': database.E2_student,
    'E3': database.E3_student,
    'E4': database.E4_student,
            }

timetable_collections ={
    "E1":database.E1_timetable,
    "E2":database.E2_timetable,
    "E3":database.E3_timetable,
    "E4":database.E4_timetable
}
router = APIRouter()



@router.put("/update-student-year-sem/")
async def update_student_year_sem(student_id: str, year: str, semester: int):
    """
    Updates the year and semester for a specific student.
    Args:
        student_id: The ID of the student to update.
        year: The updated year (e.g., "E1", "E2", "E3", "E4").
        semester: The updated semester (e.g., 1 or 2).
    """
    # Validate inputs
    if year not in ["E1", "E2", "E3", "E4"]:
        raise HTTPException(status_code=400, detail="Invalid year. Must be one of ['E1', 'E2', 'E3', 'E4'].")
    if semester not in [1, 2]:
        raise HTTPException(status_code=400, detail="Invalid semester. Must be 1 or 2.")

    # Find the student by ID
    student_data = await student.find_one({"id_number": student_id})
    if not student_data:
        raise HTTPException(status_code=404, detail=f"Student with ID {student_id} not found.")

    # Check if the student is already in the final semester
    if student_data["year"] == "E4" and student_data["semester"] == 2:
        raise HTTPException(
            status_code=400,
            detail="The student is already in the final semester and cannot be updated further."
        )

    # Update the student's year and semester in the database
    result = await student.update_one(
        {"id_number": student_id},
        {"$set": {"year": year, "semester": semester}}
    )

    if result.modified_count == 0:
        raise HTTPException(status_code=500, detail="Failed to update the student's year and semester.")

    return {
        "message": f"Student year and semester updated successfully for ID {student_id}.",
        "updated_year": year,
        "updated_semester": semester
    }


@router.put("/update-cr-id/")
async def update_cr_id(request: UpdateCRRequest):
    """
    Update the CR ID for a specific section and year in the student database.
    """
    year = request.year
    section_name = request.section_name
    cr_id = request.cr_id

    # Find the section based on year and section_name
    year_data=db4[year]
    # print(year_data)
    section = await year_data.find_one({"section_name": section_name})
    # print(section)
    if not section:
        raise HTTPException(status_code=404, detail=f"Section {section_name} in year {year} not found.")

    # Check if the student belongs to the section
    if cr_id not in section.get("students", []):
        raise HTTPException(
            status_code=403, 
            detail=f"Student {cr_id} does not belong to section {section_name} in year {year}."
        )

    # Update the CR ID
    update_result = await db4[year].update_one(
        {"_id": section["_id"]}, {"$set": {"cr_id": cr_id}}
    )

    if update_result.modified_count == 0:
        raise HTTPException(status_code=500, detail="Failed to update CR ID.")
    
    return {"message": f"CR ID for section {section_name} in year {year} updated successfully."}


async def get_subjects_for_section(
    year: str, section_name: str, db4
) -> List[str]:
    """
    Fetch the list of subjects available for a specific section in a given year.

    Args:
    - year: Year of the section (e.g., "e1", "e2").
    - section_name: Name of the section (e.g., "A", "B").
    - db: The database instance.

    Returns:
    - A list of subject names for the given section.
    """
    # Access the collection for the specified year
    year_collection = db4[year]

    # Find the section based on the section name
    section_data = await year_collection.find_one({"section_name": section_name})

    if not section_data:
        raise HTTPException(
            status_code=404, detail=f"Section {section_name} in year {year} not found."
        )

    # Extract the subject names from the section data
    subjects = [subject["subject_name"] for subject in section_data.get("subjects", [])]

    if not subjects:
        raise HTTPException(
            status_code=404,
            detail=f"No subjects found for section {section_name} in year {year}.",
        )
    return subjects


# Route to store or update the exam timetable
@router.put("/update-exam-timetable/")
async def update_exam_timetable(data: ExamTimetable):
    """
    Stores or updates the exam timetable for a specific year and semester.
    """
    year_collection = db5[data.year]  # Access the collection for the specified year

    # Fetch the subjects for the specified section
    try:
        section_subjects = await get_subjects_for_section(data.year, 'A', db4)
    except HTTPException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)

    # Gather all subjects listed in sem_exam
    timetable_subjects = set(data.sem_exam.keys())

    # Validate the subjects
    invalid_subjects = timetable_subjects - set(section_subjects)
    if invalid_subjects:
        raise HTTPException(
            status_code=400,
            detail=f"The following subjects in the timetable are invalid for year {data.year}: {', '.join(invalid_subjects)}"
        )

    # Check if a timetable for the given semester already exists
    existing_timetable = await year_collection.find_one({"semester": data.semester})

    if existing_timetable:
        # Update the existing timetable
        result = await year_collection.update_one(
            {"_id": existing_timetable["_id"]},
            {"$set": {
                "mid_exams": data.mid_exams,
                "sem_exam": data.sem_exam
            }}
        )
        if result.modified_count:
            return {"message": f"Timetable for semester {data.semester} in {data.year} updated successfully."}
        else:
            raise HTTPException(status_code=500, detail="Failed to update the timetable.")
    else:
        # Insert a new timetable
        result = await year_collection.insert_one({
            "semester": data.semester,
            "mid_exams": data.mid_exams,
            "sem_exam": data.sem_exam
        })
        if result.inserted_id:
            return {"message": f"Timetable for semester {data.semester} in {data.year} added successfully."}
        else:
            raise HTTPException(status_code=500, detail="Failed to add the timetable.")




@router.post("/update-timetable-for-faculty/")
async def update_timetable_for_faculty(assignments: YearAssignment):
    """
    Incrementally update the timetable and faculty data for the given year.
    Dynamically add new subjects if they do not exist in the timetable.
    """
    year = assignments.year
    timetable_collection = db3[year]  # Access the year-specific timetable collection
    faculty_collection = db["Faculty"]  # Faculty collection

    # Fetch available subjects for the year
    year_data = db4[year]
    available_subjects = set()

    async for semester_data in year_data.find():
        available_subjects.update(
            subject["subject_name"] for subject in semester_data.get("subjects", [])
        )

    if not available_subjects:
        raise HTTPException(
            status_code=404,
            detail=f"No subjects found for year {year} in the database."
        )

    # Fetch the existing timetable document or initialize a new one
    existing_timetable_doc = await timetable_collection.find_one({"type": "assignments"})
    timetable_doc = existing_timetable_doc or {"type": "assignments", "subjects": {}}

    for subject_assignment in assignments.assignments:
        subname = subject_assignment.subname

        # Check if the subject is valid for the year
        if subname not in available_subjects:
            # If subname is new, dynamically add it to the timetable doc
            timetable_doc["subjects"].setdefault(subname, [])

        # Prepare the new data for this subject
        new_faculty_data = [
            {"faculty_name": fa.faculty_name, "sec": fa.sec}
            for fa in subject_assignment.data
        ]

        # Merge or update the timetable subject data
        existing_subject_data = timetable_doc["subjects"].get(subname, [])

        updated_subject_data = []
        for new_faculty in new_faculty_data:
            existing_match = next(
                (ef for ef in existing_subject_data if ef["faculty_name"] == new_faculty["faculty_name"]),
                None
            )
            if existing_match:
                # Merge sections if there are overlaps
                existing_match["sec"] = list(set(existing_match["sec"]) | set(new_faculty["sec"]))
                updated_subject_data.append(existing_match)
            else:
                # Add new assignment if not present
                updated_subject_data.append(new_faculty)

        # Update timetable with the merged data
        timetable_doc["subjects"][subname] = updated_subject_data

        # Update each faculty's subject list
        for fa in subject_assignment.data:
            faculty_name_split = fa.faculty_name.split()
            faculty = await faculty_collection.find_one({
                "first_name": faculty_name_split[0],
                "last_name": faculty_name_split[-1],
            })

            if not faculty:
                raise HTTPException(
                    status_code=404,
                    detail=f"Faculty {fa.faculty_name} not found."
                )

            # Merge or update the faculty's subject list
            existing_subjects = faculty.get("subjects", [])
            existing_assignment = next(
                (subj for subj in existing_subjects if subj["subject_name"] == subname), None
            )

            if existing_assignment:
                # Merge sections if they overlap
                existing_assignment["sections"] = list(set(existing_assignment["sections"]) | set(fa.sec))
            else:
                # Add new assignment if not present
                existing_subjects.append({
                    "subject_name": subname,
                    "year": year,
                    "sections": fa.sec
                })

            # Update the faculty's subject list in the database
            await faculty_collection.update_one(
                {"_id": faculty["_id"]},
                {"$set": {"subjects": existing_subjects}}
            )

    # Store the updated timetable document in the database
    if existing_timetable_doc:
        # Update only if the document has changed
        await timetable_collection.update_one(
            {"_id": existing_timetable_doc["_id"]},
            {"$set": {"subjects": timetable_doc["subjects"]}}
        )
    else:
        # Insert a new document
        await timetable_collection.insert_one(timetable_doc)

    return {"message": "Timetable and faculty assignments updated successfully."}


# Helper function to calculate percentage
def calculate_percentage(part: int, whole: int) -> float:
    if whole == 0:
        return 0.0
    return round((part / whole) * 100, 2)
@router.get("/admin/dashboard")
async def admin_dashboard(date: str = Query(...)):
    """
    Admin dashboard to view timetable and attendance for all years and sections.
    The `date` parameter is in YYYY-MM-DD format.
    """
    # Validate date
    try:
        query_date_obj = datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")

    day_of_week = query_date_obj.strftime("%A").lower()
    today_date_obj = datetime.now()

    overall_response = {
        "date": date,
        "years": []
    }

    # Iterate through all years (e.g., E1, E2, E3, E4)
    for year in ["E1", "E2", "E3", "E4"]:
        # Fetch timetable for the year
        timetable_collection = db3[year]
        timetable_data = await timetable_collection.find_one({})
        if not timetable_data or day_of_week not in timetable_data:
            raise HTTPException(status_code=404, detail=f"Timetable not found for {year} on {day_of_week}.")

        day_timetable = timetable_data[day_of_week]

        year_data = {
            "year": year,
            "sections": [],
            "year_total_classes": 0,
            "year_overall_present_percentage": "N/A" if query_date_obj > today_date_obj else 0.0
        }

        total_classes_for_year = 0
        total_present_percentage_for_year = 0.0
        total_sections = 0

        # Iterate through sections (e.g., A, B, C, etc.)
        for section, subjects in day_timetable.items():
            section_data = {
                "section": section,
                "classes_scheduled_today": [],
                "attendance_report": [],
                "total_classes": 0,
                "overall_present_percentage": "N/A" if query_date_obj > today_date_obj else 0.0
            }

            total_classes_for_section = 0
            total_present_percentage_for_section = 0.0
            total_subjects = 0

            # Process each subject
            for subject, periods in subjects.items():
                num_classes = len(periods)
                total_classes_for_section += num_classes

                # Fetch attendance data for the subject
                attendance_collection = db2[year]
                attendance_records = attendance_collection.find({
                    f"attendance_report.{subject}": {"$exists": True},
                })
                attendance_records_list = await attendance_records.to_list(length=None)

                faculty_name = None
                total_students = 0
                total_present_students = 0

                for record in attendance_records_list:
                    subject_attendance = record["attendance_report"].get(subject, {})

                    # Extract faculty name
                    if not faculty_name:
                        faculty_name = subject_attendance.get("faculty_name", "Unknown")

                    attendance_report = subject_attendance.get("attendance", [])
                    for attendance in attendance_report:
                        if attendance["date"] == date:
                            total_students += 1
                            if attendance["status"].lower() == "present":
                                total_present_students += 1

                # Calculate attendance percentage for the subject
                if total_students > 0:
                    present_percentage = round((total_present_students / total_students) * 100, 2)
                else:
                    present_percentage = 0.0

                section_data["classes_scheduled_today"].append({
                    "subject": subject,
                    "faculty_name": faculty_name,
                    "number_of_periods": num_classes
                })

                if query_date_obj > today_date_obj:
                    section_data["attendance_report"].append({
                        "subject": subject,
                        "faculty_name": faculty_name,
                        "present_percentage": "N/A"
                    })
                else:
                    section_data["attendance_report"].append({
                        "subject": subject,
                        "faculty_name": faculty_name,
                        "present_percentage": present_percentage
                    })

                    total_present_percentage_for_section += present_percentage
                    total_subjects += 1

            # Calculate overall attendance percentage for the section
            if total_subjects > 0 and query_date_obj <= today_date_obj:
                section_data["overall_present_percentage"] = round(
                    total_present_percentage_for_section / total_subjects, 2
                )

            section_data["total_classes"] = total_classes_for_section
            year_data["sections"].append(section_data)

            total_classes_for_year += total_classes_for_section
            total_present_percentage_for_year += total_present_percentage_for_section
            total_sections += total_subjects

        # Calculate overall attendance percentage for the year
        if total_sections > 0 and query_date_obj <= today_date_obj:
            year_data["year_overall_present_percentage"] = round(
                total_present_percentage_for_year / total_sections, 2
            )

        year_data["year_total_classes"] = total_classes_for_year
        overall_response["years"].append(year_data)

    return overall_response



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
    existing_student = await student.find_one({"id_number": student_data.student_id})
    if existing_student:
        raise HTTPException(status_code=400, detail="Student with this ID already exists.")
    # Insert the new student into the database
    student_data = student_data.model_dump()
    hash_pass = auth.get_password_hash(student_data['password'])
    student_data['password'] = hash_pass
    # print(data)
    res = await student.insert_one(student_data)
    if res.inserted_id and res.acknowledged:
        return {'message':'True'}
    else:
        return {'message':'False'}
   
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
    if result.inserted_id and result.acknowledged:
        return {'message':'True'}
    else:
        return {'message':'False'}
   
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

@router.get('/download-attendance')
async def get_attendance_summary():
    workbook = Workbook()
    E1 = workbook.active
    await create_sub_sheet(E1,"E1")
    E2 = workbook.create_sheet(title="E2")
    await create_sub_sheet(E2,"E2")
    E3 = workbook.create_sheet(title="E3")
    await create_sub_sheet(E3,"E3")
    E4 = workbook.create_sheet(title="E4")
    await create_sub_sheet(E4,"E4")
    

    excel_stream = BytesIO()
    workbook.save(excel_stream)
    excel_stream.seek(0)
    response = StreamingResponse(
        excel_stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response.headers["Content-Disposition"] = "attachment; filename=preview_data.xlsx"

    return response


async def create_sub_sheet(sheet,year):
    sno = 1
    sheet.title = f"{year}"
    sheet.merge_cells("A1:D1") 
    sheet["A1"] = "Student Details"
    sheet["A1"].font = Font(name="Times New Roman", size=17, bold=True)
    sheet["A1"].alignment = Alignment(horizontal="center", vertical="center")
    # List of column groups to merge
    column_groups = [
        ('E', 'N'),
        ('O', 'X'),
        ('Y', 'AH'),
        ('AI', 'AR'),
        ('AS', 'BB'),
        ('BC', 'BL'),
        ('BM', 'BV'),
        ('BW', 'CF'),
        ('CG', 'CP'),
        ('CQ', 'DA'),
        ('DB', 'DJ'),
        ('DK', 'DS')
    ]
    year_details = student_collections[year]
    prefix_exams = exam_timetable_collections[year]
    exams = await prefix_exams.find_one({})
    subjects_data = await year_details.find_one({})
    if exams is None or subjects_data is None:
        raise HTTPException(status_code=400, detail="Invalid year")
    subjects = [subject['subject_name'] for subject in subjects_data['subjects']]
    for subject , (start_col, end_col) in zip(subjects,column_groups):
        sheet.merge_cells(f"{start_col}1:{end_col}1")
        sheet[f"{start_col}1"] = f'Subject Name : {subject}'
        sheet[f"{start_col}1"].alignment = Alignment(horizontal="center", vertical="center")
        sheet[f"{start_col}1"].font = Font(name="Times New Roman", size=17, bold=True)
    thin_border = Border(
        left=Side(style="thin"),
        right=Side(style="thin"),
        top=Side(style="thin"),
        bottom=Side(style="thin")
    )
    
    headers = ["S No", "ID Number", "Student Name", "Section Name"]

    for col_idx, header in enumerate(headers, start=1):
        sheet.merge_cells(start_row=2, start_column=col_idx, end_row=3, end_column=col_idx)
        cell = sheet.cell(row=2, column=col_idx)
        cell.value = header
        cell.font = Font(name="Times New Roman", size=12, bold=True)
        cell.alignment = Alignment(horizontal="center", vertical="center",wrap_text=True)
    
    sections = [
        {"name": f"MID-1 upto({exams['mid_exams']['MID-1']})", "subheaders": ["Number of classes Taken", "Number of classes Attended", "MID-1 Percentage"]},
        {"name": f"MID-2 upto({exams['mid_exams']['MID-1']})", "subheaders": ["Number of classes Taken", "Number of classes Attended", "MID-2 Percentage"]},
        {"name": f"MID-3 upto({exams['mid_exams']['MID-1']})", "subheaders": ["Number of classes Taken", "Number of classes Attended", "MID-3 Percentage"]},
    ]


    start_column = "E"
    for i in range(len(subjects)):  
        create_section(sheet, start_column, "Faculty Name", [])
        start_column = chr(ord(start_column) + 1)  

        for section in sections:
            create_section(sheet, start_column, section["name"], section["subheaders"])
            start_column = chr(ord(start_column) + len(section["subheaders"]))
    next_column = get_column_letter(sheet.max_column+1)
    sheet.merge_cells(f"{next_column}1:{next_column}3")
    sheet[f"{next_column}1"] = "Consolidated Percentage"
    sheet[f"{next_column}1"].font = Font(name="Times New Roman", size=17, bold=True)
    sheet[f"{next_column}1"].alignment = Alignment(horizontal="center", vertical="center",wrap_text=True)
    
    documents = await year_details.find({}).to_list(length=None)
    for document in documents:
        section = document['section_name']
        students = document['students']
        for student_id in students:
            student_details = await database.student.find_one({"id_number": student_id})
            attendance = await attendance_collections[year].find_one({"id_number": student_id})
            if attendance is None:
                continue
            if not student_details:
                continue
            student_name = student_details['first_name'] + " " + student_details['last_name']
            row = [sno, student_id, student_name, section]
            for subject in subjects:
                consolidated_attendance = 0
                row.append(attendance['attendance_report'][subject]['faculty_name'])
                mid_1_attendance = get_attendance_report(attendance, exams['mid_exams']['MID-1'],subject)
                mid_2_attendance = get_attendance_report(attendance, exams['mid_exams']['MID-2'],subject)
                mid_3_attendance = get_attendance_report(attendance, exams['mid_exams']['MID-3'],subject)
                print(mid_1_attendance,mid_2_attendance,mid_3_attendance)   
                if mid_1_attendance[0] > 0:
                    row.extend(mid_1_attendance)
                else:
                    row.extend(['', '', '']) 
                if mid_2_attendance[0] > 0:
                    row.extend(mid_2_attendance)
                else:
                    row.extend(['', '', ''])  
                if mid_3_attendance[0] > 0:
                    row.extend(mid_3_attendance)
                else:
                    row.extend(['', '', ''])
            # print(row)
            row.append(student_details['overall_attendance'])
            sheet.append(row)
            sno += 1
                
            
            # row = [sno, student_id, student_name, section]

    sheet.row_dimensions[1].height = 45
    sheet.row_dimensions[2].height = 31.5
    for row in sheet.iter_rows(min_row=1, max_row=sheet.max_row, min_col=1, max_col=sheet.max_column):
        for cell in row:
            cell.border = thin_border

    
def get_attendance_report(attendance, exam_date, subject):
    attendance_report = attendance['attendance_report'][subject]['attendance']
    number_of_classes = 0
    number_of_attended = 0
    for report in attendance_report:
        if report['date'] >= exam_date:
            number_of_classes += report['number_of_periods']
            if report['status'] == 'present':
                number_of_attended += report['number_of_periods']
    
    if number_of_classes == 0:
        return [number_of_classes, number_of_attended, 0]
    else:
        return [number_of_classes, number_of_attended, (number_of_attended / number_of_classes) * 100]
    
    
    
    
    
def create_section(sheet, col_start, section_name, subheaders):
    header_font = Font(name="Times New Roman", size=12, bold=True)
    center_align = Alignment(horizontal="center", vertical="center",wrap_text=True)
    
    col_start_index = ord(col_start) - ord('A') + 1  
    if not subheaders:
        col_end_index = col_start_index
        col_start_letter = get_column_letter(col_start_index)
        col_end_letter = get_column_letter(col_end_index)
        sheet.merge_cells(f"{col_start_letter}2:{col_end_letter}3")
        sheet[f"{col_start_letter}2"] = section_name
        sheet[f"{col_start_letter}2"].font = header_font
        sheet[f"{col_start_letter}2"].alignment = center_align
    else:
        col_end_index = col_start_index + len(subheaders) - 1
        col_start_letter = get_column_letter(col_start_index)
        col_end_letter = get_column_letter(col_end_index) 
        sheet.merge_cells(f"{col_start_letter}2:{col_end_letter}2")
        sheet[f"{col_start_letter}2"] = section_name
        sheet[f"{col_start_letter}2"].font = header_font
        sheet[f"{col_start_letter}2"].alignment = center_align
    
    
    for i, subheader in enumerate(subheaders):
        col_index = col_start_index + i
        col_letter = get_column_letter(col_index)
        sheet[f"{col_letter}3"] = subheader
        sheet[f"{col_letter}3"].font = header_font
        sheet[f"{col_letter}3"].alignment = center_align


@router.delete('/delete-attendance')
async def delete_attendance():
    years = ['E1','E2','E3','E4']
    await database.student.update_many({}, {'$set': { 'overall_attendance': 0}})
    data = dict()
    try:
        for year in years:
            attendance_collection = attendance_collections[year]
            result = attendance_collection.delete_many({})
            data[year] = result.delete_count
        return {"message":"Attendance deleted sucessfully","data":data}
    except Exception as e:
        raise HTTPException(status_code = 500,detail=f"error while deleting the attendance collection : {str(e)}")
    
    
@router.post("/timetable")
async def modify_timetable(request: TimeTableRequest):
    year  = request.year
    prefix = timetable_collections[year]
    result = prefix.delete_many({})
    inserted_result = await prefix.insert_one(request.timetable.dict())
    if inserted_result.inserted_id:
        return {"TimeTable" : request.timetable,"message":"Time table Sucessfully inserted","status_code":200}
    else:
        raise HTTPException(status_code=500,message="Internal server error")

