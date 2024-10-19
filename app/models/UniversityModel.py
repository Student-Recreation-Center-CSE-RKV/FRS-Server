from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Optional
from motor.motor_asyncio import AsyncIOMotorClient
from models.FacultyModel import Faculty
from models.StudentModel import Student
class Branch(BaseModel):
  name:List[str]
  faculty:List[Faculty]
  student:List[Student]
  location:str
class UniversityModel(BaseModel):
  name: str
  location: str
  established_year: int
  branches:List[Branch]
  
class UniversityCollection(BaseModel):
  universities:List[UniversityModel]
