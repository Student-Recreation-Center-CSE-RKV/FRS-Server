from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib
from typing import Dict
from fastapi import APIRouter, BackgroundTasks,Body, HTTPException
from bson import ObjectId
from pydantic import BaseModel, EmailStr
from .auth import get_password_hash,verify_password,create_reset_token,verify_reset_token
from models.StudentModel import Student,ProfileUpdate,PasswordChange,ForgotPasswordRequest,ResetPasswordRequest
from db.database import student
from fastapi.responses import StreamingResponse
from io import BytesIO  # For handling byte data
from reportlab.pdfgen import canvas  # For PDF generation
import os
from dotenv import load_dotenv
from db import database
from datetime import datetime
router = APIRouter()



attendance_collections = {
        'E1': database.E1,
        'E2': database.E2, 
        'E3': database.E3,
        'E4': database.E4,
    }

timetable_collections = {
        'E1': database.E1_timetable,
        'E2': database.E2_timetable, 
        'E3': database.E3_timetable,
        'E4': database.E4_timetable,
    }



# student dashboard Route
@router.get("/dashboard")
async def get_student_dashboard(id_number: str, date: str):
    details = await student.find_one({'id_number': id_number})
    if not details:
        raise HTTPException(status_code=404, detail="Student not found")
    
    attendance_collection = attendance_collections[details['year']]
    attendance_report = await attendance_collection.find_one({'id_number': id_number})
    if not attendance_report:
        raise HTTPException(status_code=404, detail="Attendance report not found for your Student id")
    date_object = datetime.strptime(date, '%Y-%m-%d')
    current_date = datetime.now()
    current_date = current_date.replace(hour=0, minute=0, second=0, microsecond=0)
    weekday_name = date_object.strftime('%A').lower()
    
    timetable_collection = timetable_collections[details['year']]
    timetable = await timetable_collection.find_one()
    if not timetable:
        raise HTTPException(status_code=404, detail="Timetable not found")
    section = details['section']
    
    if weekday_name not in timetable or section not in timetable[weekday_name]:
        raise HTTPException(status_code=404, detail="Timetable not found")
    
    daily_timetable = timetable[weekday_name][section]
    response = {}

    for subject, periods in daily_timetable.items():
        subject = subject.upper()
        subject_status = [periods]
        subject_data = attendance_report.get('attendance_report', {}).get(subject)
        if subject_data:
            for record in subject_data.get('attendance', []):
                if record['date'] == date:
                    subject_status.append(len(periods))
                    subject_status.append(record['status'])
                    break
            else:
                if date_object < current_date:
                    subject_status.append(len(periods))
                    subject_status.append('Cancelled')
                else:
                    subject_status.append(len(periods))
                    subject_status.append('Upcoming')
        else:
            if date_object < current_date:
                subject_status.append(len(periods))
                subject_status.append('Cancelled')
            else:
                subject_status.append(len(periods))
                subject_status.append('Upcoming')
        response[subject] = subject_status

    return {"Student_id":id_number, "name":details['first_name']+' '+details['last_name'] , "Timetable":response}

# View Profile
@router.get("/students/{id_number}/profile/")
async def view_profile(id_number: str):
    details = await student.find_one({"id_number": id_number})
    if not details:
        raise HTTPException(status_code=404, detail="Student not found")
    details["_id"] = str(details["_id"])  
    return {"Student details":details}

# Change Password
@router.put("/students/{id_number}/change-password/")
async def change_password(id_number: str, data: PasswordChange):
    details = await student.find_one({"id_number": id_number})
    print(details)
    if not details:
        raise HTTPException(status_code=404, detail="Student not found")
    response = verify_password(data.current_password,details['password'])
    print(response)
    if response:
        result = await student.update_one({"id_number": id_number}, {"$set": {"password": get_password_hash(data.new_password)}})
        if result.modified_count > 0:
            return {"message": "Password changed successfully"}
        else:
            raise HTTPException(status_code=400, detail="Failed to update password. Please try again.")
    else:
        raise HTTPException(status_code=400, detail="Incorrect password. Please try again.")

# View Attendance Summary
@router.get("/attendance")
async def view_attendance_summary(id_number: str):
    if id_number:
        student_data=await student.find_one({'id_number':id_number})
        year=student_data.get('year')
        print(year)
        prefix = attendance_collections[year]
        if prefix is not None:
            attendance_report = await prefix.find_one({"id_number": id_number}) 
        else:
            attendance_report = None
        if  attendance_report:
            attendance_summary = calculate_percentage(attendance_report)
            return { "attendance_report": attendance_report["attendance_report"] ,
                "attendance_summary" : attendance_summary
            
            }
        else:
            raise HTTPException(status_code=404, detail="Student details or attendance details are not found")

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


def get_attendance_collection(string: str):
    return attendance_collections[string]

def get_titmtable_collections(string: str):
    return timetable_collections[string]


def send_reset_email(email: str, reset_token: str):
    """Send the password reset email."""
    reset_link = f"http://localhost:8000/reset-password?token={reset_token}"
    subject = "Password Reset Request"
    body = f"Click the link to reset your password: {reset_link}\nThis link will expire in 1 hour."  
 
    BASEDIR = os.path.abspath('') 
    file_path = os.path.join(BASEDIR,'.env')
    load_dotenv(file_path)
    sender_password=os.getenv("sender_password")
    sender_email=os.getenv("sender_email")
    try:
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, email, msg.as_string())
        server.quit()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send email: {str(e)}")

# Routes
@router.post("/forgot-password", response_model=Dict[str, str])
async def forgot_password(request: ForgotPasswordRequest):
    """Handle forgot password request."""
    student_data = student.find_one({"email_address": request.email})
    if not student_data:
        raise HTTPException(status_code=404, detail="Email not registered")

    reset_token = create_reset_token(request.email)
    print(reset_token)
    send_reset_email(request.email, reset_token)
    return {"message": "Password reset email sent"}

@router.post("/reset-password", response_model=Dict[str, str])
async def reset_password(request: ResetPasswordRequest):
    """Reset the password using the provided token."""
    
    email = verify_reset_token(request.token)
    if not email:
        raise HTTPException(status_code=400, detail="Invalid or expired token time limit")

    # Check if new password and confirm password match
    if request.new_password != request.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")

    student_d = await student.find_one({"email_address": email})
    if not student_d:
        raise HTTPException(status_code=404, detail="Student not found")

    # Hash the new password
    hashed_password =get_password_hash(request.new_password)
    # print(hashed_password)
    # # Update the password in MongoDB
    await student.update_one(
        {"email_address":email},
        {"$set": {"password": hashed_password}, "$unset": {"reset_token": ""}},
    )
    return {"message": "Password reset successful"}

def generate_pdf(student_name: str, student_id: str) -> BytesIO:
    """Generate a PDF dynamically for the hall ticket."""
    buffer = BytesIO()
    c = canvas.Canvas(buffer)
    c.drawString(100, 750, f"Hall Ticket for {student_name}")
    c.drawString(100, 730, f"Student ID: {student_id}")
    c.drawString(100, 710, f"Issue Date: {datetime.now().strftime('%Y-%m-%d')}")
    c.save()
    buffer.seek(0)
    return buffer

@router.get("/student/download-hallticket/{student_id}")
async def download_hall_ticket(student_id: str):
    # Check if the student exists and has hall ticket released
    student = student.find_one({"_id": student_id})
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    if not student.get("hallticket_released"):
        raise HTTPException(status_code=403, detail="Hall ticket not released for this student")

    # Generate the hall ticket
    pdf_buffer = generate_pdf(student["name"], str(student["_id"]))
    # pdf_buffer=generate_pdf("Thanisha","R200439")
    # Serve the PDF as a downloadable file
    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=hall_ticket_{student_id}.pdf"}
    )
