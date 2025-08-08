from passlib.context import CryptContext
from datetime import datetime, timedelta
from jose import jwt, JWTError
"""from typing import Optional
from motor import motor_asyncio
from dotenv import load_dotenv
import os
from pymongo import MongoClient
from bson import ObjectId
"""
SECRET_KEY = "db9c2516a45ba1440ab9bc243c1b0c0648348f60a2c83150ba79207801447a38"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
RESET_TOKEN_EXPIRATION = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: timedelta or None= None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


def create_reset_token(email: str):
    """Create a JWT reset token."""
    expiration = datetime.utcnow() + timedelta(minutes=RESET_TOKEN_EXPIRATION)
    payload = {"email": email, "exp": expiration}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def verify_reset_token(token: str):
    """Verify a JWT reset token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("email")
    except jwt.JWTError:
        return None