import time
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from datetime import datetime, timedelta
from jose import ExpiredSignatureError, JWTError, jwt
from passlib.context import CryptContext
from db.database import admin,student
import os
from typing import Optional
from dotenv import load_dotenv


"""from models import user as models
from utils import security
from crud import user as crud

from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

import os
"""

BASEDIR = os.path.abspath('') 
file_path = os.path.join(BASEDIR,'.env')
load_dotenv(file_path)

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES"))
RESET_TOKEN_EXPIRATION = int(os.getenv("RESET_TOKEN_EXPIRATION"))

# MongoDB connection

#MONGO_URI = os.getenv("MONGO_URI")

#client = AsyncIOMotorClient(database.uri)

db = admin
# Secret key and algorithm for JWT

#SECRET_KEY = os.getenv("SECRET_KEY")

router = APIRouter()

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class User(BaseModel):
    username: Optional[str] = None
    email: Optional[str] = None
    disabled: Optional[bool] = None

class UserInDB(User):
    hashed_password: str

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def get_user(db, username: str):
    if username in db:
        user_data = db[username]
        return UserInDB(**user_data)

def authenticate_user(db, username: str, password: str):
    user = get_user(db, username)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    # to_encode.update({"exp": expire.isoformat()})
    expire = int(time.time()) + 3600 # One hour time limit
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    print(to_encode)
    return encoded_jwt



async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        print(token)
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        print(payload)
        email = payload.get("sub")
        role = payload.get("role")
        if not email or not role:
            raise HTTPException(status_code=401, detail="Invalid token payload")


        if role != "student":
            return {"email": email, "role": role}

        # Fetch student ID
        student_data = await student.find_one({"email_address":email})
        student_id=student_data["id_number"]
        if not student_id:
            raise HTTPException(status_code=404, detail="Student not found")
        return {"email": email, "role": role}

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.JWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")



async def get_current_active_user(current_user: UserInDB = Depends(get_current_user)):
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

async def generate_access_token(username:str,role:str):
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": username,"role":role}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/users/me/", response_model=User)
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    return current_user

@router.get("/users/me/items")
async def read_own_items(current_user: User = Depends(get_current_active_user)):
    return [{"item_id": "Item1", "owner": current_user.username}]


def create_reset_token(email: str):
    """Create a JWT reset token."""
    expiration = datetime.utcnow() + timedelta(minutes=RESET_TOKEN_EXPIRATION)
    payload = {"email": email, "exp": expiration}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def verify_reset_token(token: str):
    """Verify a JWT reset token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        print(payload.get("email"))
        return payload.get("email")
    except jwt.JWTError:
        return None
    
    
