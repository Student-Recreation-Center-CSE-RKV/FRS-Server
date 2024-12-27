from motor.motor_asyncio import AsyncIOMotorClient
# from pymongo.mongo_client import MongoClient
# from pymongo.server_api import ServerApi
import os
from dotenv import load_dotenv



BASEDIR = r'/home/rguktrkvalley/FRS-Server/app/.env'
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

db2 = client['Attendance']
E1 = db2['E1']
E2 = db2['E2']
E3 = db2['E3']
E4 = db2['E4']

db3=client["TimeTable"]
E1T = db3['E1']
E2T = db3['E2']
E3T = db3['E3']
E4T = db3['E4']

# client = motor.motor_asyncio.AsyncIOMotorClient(MONGODB_URL)
 















# import motor.motor_asyncio
# import os
# from dotenv import load_dotenv
# load_dotenv()


# MONGODB_URL = os.getenv("mongoDB_url")


