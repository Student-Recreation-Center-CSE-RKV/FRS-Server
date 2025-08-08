from typing import Dict, List, Optional
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
    faculty_username: str
    sec: List[str]

class SubjectAssignment(BaseModel):
    subname: str
    data: List[FacultyAssignment]

class YearAssignment(BaseModel):
    year: str
    assignments: List[SubjectAssignment]






class DaySchedule(BaseModel):
    A: Optional[Dict[str, List[str]]]
    B: Optional[Dict[str, List[str]]]
    C: Optional[Dict[str, List[str]]]
    D: Optional[Dict[str, List[str]]]
    E: Optional[Dict[str, List[str]]]

class WeeklySchedule(BaseModel):
    monday: Optional[DaySchedule]
    tuesday: Optional[DaySchedule]
    wednesday: Optional[DaySchedule]
    thursday: Optional[DaySchedule]
    friday: Optional[DaySchedule]
    saturday: Optional[DaySchedule]
    
    
class TimeTableRequest(BaseModel):
    year:str
    timetable : WeeklySchedule



class LoginCredentials(BaseModel):
    email:str
    password:str
    role:str
    
class TodayClassesRequest(BaseModel):
    today_date : str
    year:str
    
class ClassAttendanceRequest(BaseModel):
    year:str
    date:str
    section:str
    subject:str