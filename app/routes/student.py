from fastapi import APIRouter,Body, HTTPException
from bson import ObjectId
from .auth import get_password_hash
from models.StudentModel import Student,ProfileUpdate,PasswordChange,AttendanceRecord
from db.database import student
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

    return response


        

# View Profile
@router.get("/students/{id_number}/profile/")
async def view_profile(id_number: str):
    details = await student.find_one({"id_number": id_number})
    if not details:
        raise HTTPException(status_code=404, detail="Student not found")
    details["_id"] = str(details["_id"])  # Convert ObjectId to string
    return {"Student details":details}

# Change Password
@router.put("/students/{id_number}/change-password/")
async def change_password(id_number: str, data: PasswordChange):
    details = await student.find_one({"id_number": id_number})
    current_password = get_password_hash(details["password"])
    if not details:
        raise HTTPException(status_code=404, detail="Student not found")
    if current_password != data.current_password: 
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    result = await student.update_one({"id_number": id_number}, {"$set": {"password": get_password_hash(data.new_password)}})
    if result.modified_count > 0:
        return {"message": "Password changed successfully"}
    else:
        raise HTTPException(status_code=400, detail="Failed to update password. Please try again.")


# View Attendance Summary
@router.get("/attendance")
async def view_attendance_summary(id_number: str , year : str):
    if id_number:
        prefix = get_attendance_collection(year)
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



