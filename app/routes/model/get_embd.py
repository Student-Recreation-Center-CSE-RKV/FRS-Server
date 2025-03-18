import numpy as np
import cv2
import tensorflow as tf
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, APIRouter, HTTPException
from pydantic import BaseModel
import asyncio
from typing import List,Dict,Any
from bson import ObjectId
from ultralytics import YOLO
import faiss
import pymongo
from pymongo import MongoClient
from db import database
from ultralytics import YOLO
from keras_facenet import FaceNet
import base64

# Initialize FastAPI app
router = APIRouter()

# Database connection
students_collection = database.student  # Replace with your collection name

# WebSocket model
class FrameData(BaseModel):
    frame: str
    faculty_id: str
    year: str
    branch: str
    section: str

class StudentRequest(BaseModel):
    year: str
    branch: str
    section: str

# Load YOLOv8 face detector
print("Loading YOLO model...")
yolo_model = YOLO("C:\\Users\\Kalki\\Documents\\code\\FRS\\frs_backend\\FRS-Server\\app\\routes\\model\\locals\\yolo.pt")
print("YOLO model loaded.")

# Load FaceNet model
print("Loading FaceNet model...")
facenet_model = FaceNet()
print("FaceNet model loaded.")

# FAISS Index for face recognition
embedding_dim = 512  # Adjust based on FaceNet output
index = faiss.IndexFlatL2(embedding_dim)

# Store student data
stored_embeddings = []
stored_ids = []

# Function to detect faces using YOLOv8
def detect_faces_yolov8(image: np.ndarray):
    print("Running YOLO face detection...")

    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    results = yolo_model(image_rgb)  # Returns a list of Results objects

    if not results:
        print("No detection results from YOLO.")
        return []

    results = results[0]  # Extract the first `Results` object

    if not hasattr(results, "boxes"):
        print("YOLO results object has no 'boxes' attribute!")
        return []

    boxes = []
    for box in results.boxes.xywh:  # Use `.boxes.xywh` instead of `results.xywh`
        x_center, y_center, w, h = map(int, box[:4])  # Convert to integers
        boxes.append([x_center - w // 2, y_center - h // 2, w, h])  # Convert to (x1, y1, w, h)

    print(f"Detected {len(boxes)} faces.")
    return boxes

# Function to extract embeddings using FaceNet
def get_face_embedding(image: np.ndarray) -> np.ndarray:
    print("Extracting face embedding...")
    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    image = cv2.resize(image, (160, 160))
    image = np.expand_dims(image, axis=0)
    embedding = facenet_model.embeddings(image)
    print(f"Embedding shape: {embedding.shape}")
    return embedding.flatten()

# Fetch students from database and ensure consistent embedding format
async def get_students_by_year_and_section(year: str, branch: str, section: str):
    print(f"Fetching students from DB: Year={year}, Branch={branch}, Section={section}")
    
    students_cursor = students_collection.find(
        {"year": year, "branch": branch, "section": section},
        {"_id": 0, "id_number": 1, "embeddings": 1}
    )
    students_list = await students_cursor.to_list(length=None)
    
    # Filter out students who have no embeddings or empty embeddings
    valid_students = [
        student for student in students_list 
        if isinstance(student.get("embeddings"), list) and len(student["embeddings"]) > 0
    ]

    print(f"Total students found: {len(students_list)}, Valid students with embeddings: {len(valid_students)}")

    # Convert embeddings to NumPy array
    for student in valid_students:
        print("Valid student:", student["id_number"])
        student["embeddings"] = np.array(student["embeddings"], dtype=np.float32)

    return valid_students

# Save multiple embeddings per student into FAISS index
def save_student_embeddings(students):
    global stored_embeddings, stored_ids
    print("Saving student embeddings to FAISS...")

    embeddings_list = []
    ids_list = []

    for student in students:
        embeddings = student["embeddings"]  # List of 30 embeddings
        student_id = student["id_number"]
        print(f"Length of embeddings for {student_id}: {len(embeddings)}")
        print(type(embeddings))
        print("Length of embeddings[0]:", embeddings[0].shape)
        print(type(embeddings[0]))
        print(embeddings[0])
        if isinstance(embeddings, list):  # Convert list of lists into NumPy array
            embeddings = np.array(embeddings, dtype=np.float32)

        for embedding in embeddings:
            embeddings_list.append(embedding.flatten())
            ids_list.append(student_id)

    if len(embeddings_list) > 0:
        embeddings_np = np.array(embeddings_list, dtype=np.float32)  # Ensure it's a proper 2D NumPy array
        print(f"Adding {embeddings_np.shape[0]} embeddings of shape {embeddings_np.shape[1]} to FAISS index...")
        index.add(embeddings_np)  # FAISS requires a 2D NumPy array
        stored_embeddings.extend(embeddings_list)
        stored_ids.extend(ids_list)
        print("FAISS indexing complete.")


# WebSocket endpoint for handling real-time attendance
@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("WebSocket connection established.")

    try:
        while True:
            data = await websocket.receive_text()
            print("Received WebSocket data.")

            frame_data = FrameData.parse_raw(data)

            print(f"Processing frame from Faculty={frame_data.faculty_id}, Year={frame_data.year}, Branch={frame_data.branch}, Section={frame_data.section}")

            # Fetch students and store embeddings if not already indexed
            students = await get_students_by_year_and_section(frame_data.year, frame_data.branch, frame_data.section)
            if not stored_embeddings:
                save_student_embeddings(students)

            # Decode the base64-encoded frame
            frame_bytes = base64.b64decode(frame_data.frame.split(",")[1])
            nparr = np.frombuffer(frame_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            # Detect faces using YOLO
            faces = detect_faces_yolov8(img)

            recognized_students = []
            for (x, y, w, h) in faces:
                face_image = img[y:y + h, x:x + w]
                query_embedding = get_face_embedding(face_image)

                # Search across all embeddings
                D, I = index.search(np.array([query_embedding], dtype=np.float32), k=5)
                
                matched_students = []
                for idx in I[0]:  # Check multiple embeddings per student
                    if idx < len(stored_ids):
                        student_id = stored_ids[idx]
                        matched_students.append(student_id)

                # If a match is found, retrieve student details
                for student_id in set(matched_students):
                    student = await students_collection.find_one({"id_number": student_id})
                    if student:
                        recognized_students.append({
                            "x": x,
                            "y": y,
                            "w": w,
                            "h": h,
                            "id_number": student["id_number"],
                            "name": f"{student.get('first_name', 'Unknown')} {student.get('last_name', '')}".strip(),
                        })

            print(f"Recognized {len(recognized_students)} students.")
            print(recognized_students)
            await websocket.send_json({"students": recognized_students})

    except WebSocketDisconnect:
        print("Client disconnected")
        await websocket.close()


@router.post("/allstudents")
async def get_students(request: StudentRequest) -> Dict[str, List[Dict[str, Any]]]:
    """
    Fetch students based on year, branch, and section from request body.
    Excludes MongoDB's `_id` field for cleaner JSON output.
    """

    query = {"year": request.year, "branch": request.branch, "section": request.section}

    # Fetch only required fields
    students_cursor = students_collection.find(
        query, {"_id": 0, "id_number": 1, "first_name": 1, "last_name": 1, "year": 1, "branch": 1, "section": 1}
    )

    students = [
        {
            "id_number": student["id_number"],
            "name": f"{student.get('first_name', '')} {student.get('last_name', '')}".strip(),
            "year": student["year"],
            "branch": student["branch"],
            "section": student["section"]
        }
        async for student in students_cursor
    ]

    if not students:
        raise HTTPException(status_code=404, detail="No students found for the given criteria")

    return {"students": students}
