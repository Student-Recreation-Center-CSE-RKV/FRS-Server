from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from routes.v1 import auth, admin, student, faculty
from routes.index import router as main_router
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

# Include routers from both your code and your friend's code
app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(admin.router, prefix="/admin", tags=["Admin"])
app.include_router(student.router, prefix="/student", tags=["Student"])
app.include_router(faculty.router, prefix="/faculty", tags=["Faculty"])
app.include_router(main_router, prefix="/api", tags=["API"])

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