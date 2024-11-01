from routes.v1 import auth
from db.database import student
from bson import ObjectId


async def student_insert(data):
    hash_pass = auth.get_password_hash(data['password'])
    data['password'] = hash_pass
    res = await student.insert_one(data)
    if res.inserted_id and res.acknowledged:
        return True
    else:
        return False
    

async def student_delete(id_number):
    res = await student.delete_one({'id_number':id_number})
    if res.acknowledged:
        return True
    else:
        return False

async def get_details(id_number):
    details = await student.find_one({'id_number':id_number})
    if details:
        if isinstance(details,dict):
            for key,value in details.items():
                if isinstance(value,ObjectId):
                    details[key] = str(value)
    return details


async def update_details(detail):
    pass