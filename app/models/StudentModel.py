from typing import Optional, List
from pydantic import BaseModel, Field
from enum import Enum
from bson import ObjectId

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

class Student(BaseModel):
    id: Optional[ObjectId] = Field(alias="_id", default=None)
    first_name: str
    last_name: str
    middle_name: Optional[str] = None
    id_number: str
    year: Year
    branch: Branch
    section: Section
    email_address: str
    phone_number: str

    class Config:
        arbitrary_types_allowed = True  # Allow ObjectId

class StudentCollection(BaseModel):
    students: List[Student]