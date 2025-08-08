from typing import Dict, Literal, Optional, List
from pydantic import BaseModel, Field, EmailStr, field_validator
from enum import Enum
from bson import ObjectId
from datetime import datetime

# Enum definitions remain the same
class Gender(str, Enum):
    male = "male"
    female = "female"

class Branch(str, Enum):
    cse = "cse"
    ece = "ece"
    eee = "eee"
    mech = "mech"
    civil = "civil"
    mme = "mme"
    chemical = "chemical"

class Year(str, Enum):
    E1 = "E1"
    E2 = "E2"
    E3 = "E3"
    E4 = "E4"

class Section(str, Enum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"
    E = "E"
    
class SubjectSummary(BaseModel):
    faculty_name: str  # Name of the faculty member for the subject
    present_days: int = 0
    absent_days: int = 0


class Student(BaseModel):
    # Treat `id` as a string and ensure proper conversion from ObjectId
    # id: Optional[str] = Field(alias="_id", default=None)
    id_number: str
    first_name: str
    last_name: str
    middle_name: Optional[str] = None
    year: Year
    branch: Branch
    section: Section
    email_address: EmailStr
    phone_number: Optional[str] = None
    password:str
    gender: Gender
    overall_attendance: Optional[int] = Field(default=0, exclude=True)
    semester:str
    # subject_summary: Dict[str, SubjectSummary] = Field(default_factory=dict)  # Subject-wise attendance summary
    
    # Convert ObjectId to string if present 
    # @field_validator("id", mode="before")
    # def convert_objectid(cls, value):
    #     return str(value) if isinstance(value, ObjectId) else value

    # class Config:
    #     # Enable alias usage for Pydantic models
    #     allow_population_by_field_name = True

class StudentCollection(BaseModel):
    students: List[Student]
    
    
class ProfileUpdate(BaseModel):
    phone_number: Optional[str]
    email_address: Optional[EmailStr]

class PasswordChange(BaseModel):
    current_password: str
    new_password: str

class AttendanceRecord(BaseModel):
    course_id: str
    timestamp: datetime
    status: List[Literal["present", "absent"]]  # e.g., "present" or "absent
    
    
# class ImageBatch(BaseModel):
#     images: list[str]
    
class StudentDetails(BaseModel):
    batch: str
    branch: str
    name: str
    section: str
    studentId: str 
# class CapturedImages(BaseModel):
#     form_data: StudentDetails 
#     images: List[str]

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str
    confirm_password :str

class CapturedImages(BaseModel):
    id_number : str
    images : List[str]

class studentDetails(BaseModel):
    id_number: str

