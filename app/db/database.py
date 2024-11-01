from motor.motor_asyncio import AsyncIOMotorClient
# from pymongo.mongo_client import MongoClient
# from pymongo.server_api import ServerApi
import os
from dotenv import load_dotenv



BASEDIR = r'C:\\Users\\sathe\\OneDrive\\Documents\\FRS-Server\\app\\.env'


uri = os.getenv("mongoDB_url")
client = AsyncIOMotorClient(uri)

try:
    client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(e)


db = client.get_database("University")
student = db.get_collection("Student")
faculty = db.get_collection('Faculty')
admin = db.get_collection('Admin')





# client = motor.motor_asyncio.AsyncIOMotorClient(MONGODB_URL)
# db = client.get_database("university")
# student_collection = db.get_collection("students")

















# import motor.motor_asyncio
# import os
# from dotenv import load_dotenv
# load_dotenv()


# MONGODB_URL = os.getenv("mongoDB_url")


