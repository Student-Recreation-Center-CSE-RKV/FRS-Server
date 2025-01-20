from datetime import date
from typing import Dict, List, Optional
import dateutil
from pydantic import BaseModel, RootModel
from enum import Enum

class SubjectModel(BaseModel):
    subject_name: str  # Subject name (e.g., Mathematics, Physics)
    faculty_id: Optional[str]  # Faculty ID (optional in case not assigned yet)


class SectionModel(BaseModel):
    section_name: str  # Section name (e.g., A, B, C, D)
    cr_id: Optional[str]  # Class Representative ID
    students: List[str]  # List of student IDs in the class
    subjects: List[SubjectModel]  # List of subjects taught in the class

# class YearModel(BaseModel):
#     year: str  # Year (e.g., E1, E2, E3, E4)
#     sections: List[SectionModel]  # List of sections in the year

