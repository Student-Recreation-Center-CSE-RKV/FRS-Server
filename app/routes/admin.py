from math import e
from pickle import EXT2
from re import sub
from typing import Literal, Union
from venv import create
from fastapi import APIRouter, Body, Depends, HTTPException
from bson import ObjectId
from numpy import number
from models.FacultyModel import Attendance, Faculty
from models.StudentModel import Student
from pydantic import BaseModel
from db import database
from db.database import admin, faculty, student  # Assuming these collections exist
from routes import auth  # For password hashing and verification
from fastapi.responses import StreamingResponse
import json
from openpyxl import Workbook
from openpyxl.styles import Alignment,Font,Border,Side
from openpyxl.utils import get_column_letter
from io import BytesIO
import os

attendance_collections = {
        'E1': database.E1,
        'E2': database.E2, 
        'E3': database.E3,
        'E4': database.E4,
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
