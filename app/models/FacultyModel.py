from datetime import date
from typing import Dict, List, Optional
import dateutil
from pydantic import BaseModel, RootModel
from enum import Enum
from models.StudentModel import Branch , Year , Section  # Ensure Branch is defined correctly

class Section(BaseModel):
    subject_name: str
    year: str
    sections: List[str]


class Faculty(BaseModel):
    first_name: str
    last_name: str
    middle_name: Optional[str] = None
    password : str
    email_address: str
    phone_number: str
    department: Branch  # Ensure Branch is a valid Pydantic model or Enum
    designation: str
    qualification: str
    subjects: List[Section]
    is_admin: bool = False

class FacultyCollection(BaseModel):
    faculties: List[Faculty]  # List of Faculty objects
    
class AttendanceRequest(BaseModel):
    student_id : Optional[str] = None
    branch : Optional[str] = None
    batch : Optional[str] = None
    section : Optional[List[str]] = None

class StudentAttendance(BaseModel):
    id: str
    name: str
    classes_attended: int
    
class Attendance(BaseModel):
    student_id: str
    subject : str
    attended: bool
    
# class SubjectAttendance(BaseModel):
#     date: date
#     status: str = "absent"  # Default to "absent"

class AttendanceUpdate(BaseModel):
    ids: List[str]  # List of student IDs
    subject: str  # Subject name
    faculty_name: str  # Faculty name for the subject
    year: str
    branch: str
    section: str
    number_of_periods:int 


class AttendanceRecord(BaseModel):
    faculty_name: str  
    date: date
    status: str = "absent"  # Default to absent / can be present or absent"

class StudentAttendance(BaseModel):
    id_number: str
    attendance: Dict[str, List[AttendanceRecord]]  


class AttendanceRecord(BaseModel):
    date: str
    status: str
    number_of_periods: int

class SubjectAttendance(BaseModel):
    faculty_name: str
    attendance: List[AttendanceRecord]


class AttendanceData(BaseModel):
    id_number: str
    attendance_report: Dict[str, SubjectAttendance]
