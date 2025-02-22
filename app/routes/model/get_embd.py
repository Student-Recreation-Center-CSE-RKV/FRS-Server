import numpy as np
import cv2
import torch
import tensorflow as tf
from fastapi import FastAPI, WebSocket, WebSocketDisconnect,APIRouter
from pydantic import BaseModel
import asyncio
from typing import List
from bson import ObjectId
from ultralytics import YOLO
import faiss
import pymongo
from pymongo import MongoClient
from db import database
from ultralytics import YOLO
# Initialize FastAPI app
router = APIRouter()

# Database connection
students_collection = database.student # Replace with your collection name

# Load YOLOv8 face detector
yolo_model = YOLO(r"C:\Users\sathe\OneDrive\Documents\FRS-Server\app\routes\model\locals\yolo.pt")  # Replace with the path to your YOLOv8 model

# Load FaceNet model (adjust the path to your model)
# facenet_model = tf.saved_model.load('path_to_facenet_model')  # Change path as needed

# Indexing and searching face embeddings using FAISS
index = faiss.IndexFlatL2(128)  # Using FAISS for fast similarity search
stored_embeddings = []
stored_ids = []

# Function to detect faces using YOLOv8
def detect_faces_yolov8(image: np.ndarray):
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    results = yolo_model(image_rgb)
    boxes = []
    for result in results.xywh[0]:
        x_center, y_center, w, h, confidence, class_id = result
        if class_id == 0 and confidence > 0.5:
            x1 = int(x_center - w / 2)
            y1 = int(y_center - h / 2)
            boxes.append([x1, y1, int(w), int(h)])
    return boxes

# Function to extract embeddings using FaceNet
def get_face_embedding(image: np.ndarray) -> np.ndarray:
    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    image = cv2.resize(image, (160, 160))
    image = np.expand_dims(image, axis=0)
    embedding = facenet_model(image)
    return embedding.numpy().flatten()

# Fetch students from the database based on year and section
def get_students_by_year_and_section(year: str, branch:str, section: str):
    return list(students_collection.find({"year": year, "branch":branch, "section": section}))

# Function to save student embeddings into the FAISS index
def save_student_embeddings(students):
    for student in students:
        embedding = student['embedding']
        student_id = student['id_number']
        stored_embeddings.append(embedding)
        stored_ids.append(student_id)
    index.add(np.array(stored_embeddings))  # Add embeddings to FAISS index

# WebSocket model
class FrameData(BaseModel):
    frame: str
    faculty_id: str
    year: str
    Branch: str
    section: str

# WebSocket endpoint for handling real-time attendance
@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            frame_data = FrameData.parse_raw(data)
            frame = frame_data.frame
            faculty_id = frame_data.faculty_id
            year = frame_data.year
            branch = frame_data.branch
            section = frame_data.section

            # Fetch students based on the year and section from MongoDB
            students = get_students_by_year_and_section(year, branch, section)

            # Save embeddings to FAISS if it's the first time
            if not stored_embeddings:
                save_student_embeddings(students)

            # Decode frame from base64 and process it
            nparr = np.frombuffer(frame.encode(), np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            # Detect faces in the image using YOLOv8
            faces = detect_faces_yolov8(img)

            # List to store recognized students
            recognized_students = []

            for (x, y, w, h) in faces:
                face_image = img[y:y + h, x:x + w]
                query_embedding = get_face_embedding(face_image)

                # Search the FAISS index for similar embeddings
                D, I = index.search(np.array([query_embedding]), k=5)
                matched_ids = [stored_ids[i] for i in I[0]]

                # If match is found, consider the student recognized
                for student_id in matched_ids:
                    student = students_collection.find_one({"id_number": student_id})
                    if student:
                        recognized_students.append({
                            "id_number": student['id_number'],
                            "name": f"{student['first_name']} {student['last_name']}",
                            "year": student['year'],
                            "branch":student['branch'],
                            "section": student['section']
                        })

            # Send recognized students to the frontend
            await websocket.send_text(
                {"students": recognized_students}
            )

    except WebSocketDisconnect:
        print("Client disconnected")
        await websocket.close()

# Run FastAPI with Uvicorn
# Command to run: uvicorn script_name:app --reload
