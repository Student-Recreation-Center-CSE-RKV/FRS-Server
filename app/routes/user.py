from fastapi import APIRouter,HTTPException
from . import auth
from db .database import user
from typing import List
from models.UserModel import Role, User


router=APIRouter()

@router.post("/add_user")
async def add_user(user_name: str, password: str, roles: List[Role]):
    existing_user = await user.find_one({"user_name": user_name})
    if existing_user:
        raise HTTPException(status_code=400, detail="User already exists.")
    
    # Insert new user into the collection
    
    new_user = {
        "user_name": user_name,
        "password": password,
        "roles": roles
    }
    new_user["password"]=auth.get_password_hash(new_user['password'])
    result = user.insert_one(new_user)
    print(new_user)
    return {"message": "User added successfully!"}

@router.get("/users")
async def get_users():
    """Retrieve all users"""
    users = await user.find().to_list(100)
    return [
        {
            "user_name": user["user_name"],
            "password": user["password"],
            "roles": user["roles"]
        }
        for user in users
    ]

@router.put("/update_user/{user_name}")
async def update_user(user: User,user_name:str):
    existing_user = await user.find_one({"user_name": user_name})
    if existing_user:
        raise HTTPException(status_code=400, detail="User already exists.")
    
    updated_user = {
        "user_name": user.user_name,
        "password": user.password,
        "roles": user.roles
    }
    updated_user["password"]=auth.get_password_hash(updated_user['password'])
    result = user.update_one({"user_name": user_name}, {"$set": updated_user})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found.")
    return {"message": "User updated successfully!"}

@router.delete("/delete_user/{user_name}")
async def delete_user(user_name: str):
    user_data= await user.find_one({"user_name": user_name})
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found.")

    # Delete the user
    result = await user_data.delete_one({"user_name": user_name})
    if result.deleted_count == 1:
        return {"message": f"User '{user_name}' deleted successfully!"}
    else:
        raise HTTPException(status_code=500, detail="Failed to delete user. Please try again.")
