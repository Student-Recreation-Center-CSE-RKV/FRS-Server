from motor.motor_asyncio import AsyncIOMotorClient
# from pymongo.mongo_client import MongoClient
# from pymongo.server_api import ServerApi
import os
from dotenv import load_dotenv



BASEDIR = r'/home/rguktrkvalley/Downloads/app'
load_dotenv(os.path.join(BASEDIR, '.env'))


uri = os.getenv("mongoDB_url")
client = AsyncIOMotorClient(uri)
db = client.get_database("University")
collection = db.get_collection("Student")

print(collection)

try:
    client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(e)


#db = client.get_database("Sample_mflix")
#collection = db.get_collection("comments")





# client = motor.motor_asyncio.AsyncIOMotorClient(MONGODB_URL)
 















# import motor.motor_asyncio
# import os
# from dotenv import load_dotenv
# load_dotenv()


# MONGODB_URL = os.getenv("mongoDB_url")


