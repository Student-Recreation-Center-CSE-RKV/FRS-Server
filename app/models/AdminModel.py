from typing import Dict, List
from pydantic import BaseModel


class ExamTimetable(BaseModel):
    year: str  # e.g., "e1", "e2", "e3", "e4"
    semester: str  # e.g., "1" or "2"
    mid_exams: Dict[str, str]  # e.g., {"MID-1": "2024-08-07", "MID-2": "2024-09-26"}
    sem_exam: Dict[str, str]  # e.g., {"BEE": "2024-11-17", "PSPC": "2024-11-19"}


class UpdateCRRequest(BaseModel):
    year: str
    section_name: str
    cr_id: str
    

class FacultyAssignment(BaseModel):
    faculty_name: str
    sec: List[str]

class SubjectAssignment(BaseModel):
    subname: str
    data: List[FacultyAssignment]

class YearAssignment(BaseModel):
    year: str
    assignments: List[SubjectAssignment]
