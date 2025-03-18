from fastapi import FastAPI,HTTPException,Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from routes import auth, admin, student, faculty,user
from routes.model import get_embd,training
from models.AdminModel import LoginCredentials
from db import database
from routes.auth import verify_password,generate_access_token,get_current_user
#from  db  import database

# Use comments_collection in your CRUD operations

app = FastAPI()

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post('/login')
async def login(data: LoginCredentials):
    email = data.email.lower()
    password = data.password
    role = data.role.lower()

    # Mapping roles to respective collections
    role_collection_map = {
        "admin": database.admin,
        "faculty": database.faculty,
        "student": database.student
    }

    if role not in role_collection_map:
        raise HTTPException(status_code=400, detail="Invalid role specified")

    collection = role_collection_map[role]

    # Fetch user from the respective collection
    user = await collection.find_one({"email_address": email})

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Verify password
    if not verify_password(password, user["password"]):
        raise HTTPException(status_code=401, detail="Incorrect password")
    
    token = await generate_access_token(email, role)

    return {"message": "Login successful", "token": token}
    

@app.get("/profile")
async def profile(user: dict = Depends(get_current_user)):
    if user['role'] == 'faculty':
        faculty_data = await database.faculty.find_one({"email_address": user['email']})
        if faculty_data:
            faculty_data.pop("_id", None)
            faculty_data.pop("password", None)
        return faculty_data
    
    elif user['role'] == 'student':
        student_data = await database.students.find_one({"email_address": user['email']})
        if student_data:
            student_data.pop("_id", None)
            student_data.pop("password", None)
        return student_data
    
    return {"error": "Invalid role"}

        

# Include routers from both your code and your friend's code
app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(admin.router, prefix="/admin", tags=["Admin"])
app.include_router(student.router, prefix="/student", tags=["Student"])
app.include_router(faculty.router, prefix="/faculty", tags=["Faculty"])
app.include_router(user.router,prefix='/user',tags=["User"])
app.include_router(get_embd.router,prefix='/predict' , tags=['predict'])
app.include_router(training.router,prefix='/capturing' , tags=['capturing'])


# Mount static files for serving HTML 
app.mount("/static", StaticFiles(directory="templates"), name="static")

@app.get("/", tags=["Root"])
async def root_message():
    return {"message": "Welcome to the API. Use the docs to get started."}

@app.get("/login", response_class=HTMLResponse, tags=["Login"])
async def get_login_page():
    with open("templates/login.html", "r") as file:
        return HTMLResponse(content=file.read())

# Uncomment and implement if needed
# @app.get("/api")
# async def api():
#     temp = collection.find_one({})
#     print(temp)
#     return

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)