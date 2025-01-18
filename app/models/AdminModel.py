from typing import Dict, List, Optional
from pydantic import BaseModel






class DaySchedule(BaseModel):
    A: Optional[Dict[str, list[str]]]
    B: Optional[Dict[str, list[str]]]
    C: Optional[Dict[str, list[str]]]
    D: Optional[Dict[str, list[str]]]
    E: Optional[Dict[str, list[str]]]

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