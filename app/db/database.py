from motor.motor_asyncio import AsyncIOMotorClient
# from pymongo.mongo_client import MongoClient
# from pymongo.server_api import ServerApi
import os
from dotenv import load_dotenv



BASEDIR = r'/home/rguktrkvalley/Desktop/FinalFRS/FRS-Server/app/.env'
load_dotenv(BASEDIR)

uri = os.getenv("mongoDB_url")
client = AsyncIOMotorClient(uri)


try:
    client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(e)


db = client["University"]
student = db["Student"]
faculty = db['Faculty']
admin = db['Admin']
user=db["User"]


# client = motor.motor_asyncio.AsyncIOMotorClient(MONGODB_URL)
 















# import motor.motor_asyncio
# import os
# from dotenv import load_dotenv
# load_dotenv()


# MONGODB_URL = os.getenv("mongoDB_url")


