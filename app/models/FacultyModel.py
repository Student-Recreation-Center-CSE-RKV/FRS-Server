from typing import List, Optional
from pydantic import BaseModel
from enum import Enum
from models.StudentModel import Branch  # Ensure Branch is defined correctly

class Faculty(BaseModel):
    first_name: str
    last_name: str
    middle_name: Optional[str] = None
    email_address: str
    phone_number: str
    department: Branch  # Ensure Branch is a valid Pydantic model or Enum
    designation: str
    qualification: str
    subjects: List[str]

class FacultyCollection(BaseModel):
    faculties: List[Faculty]  # List of Faculty objects