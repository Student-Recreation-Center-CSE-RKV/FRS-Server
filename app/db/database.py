import motor.motor_asyncio

MONGODB_URL="mongodb://localhost:27017"
client = motor.motor_asyncio.AsyncIOMotorClient(MONGODB_URL)
db = client.get_database("university")
student_collection = db.get_collection("students")