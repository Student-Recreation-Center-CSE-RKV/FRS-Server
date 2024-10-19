from fastapi import FastAPI
from models.UserModel import User
app=FastAPI()
@app.get("/")
async def root():
  return{"message":"Hello "}