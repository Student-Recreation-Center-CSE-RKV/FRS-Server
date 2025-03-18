from fastapi import APIRouter
from networkx import capacity_scaling
from pydantic import BaseModel, Field
import numpy as np
import cv2
import faiss
import os
import tensorflow as tf
from ultralytics import YOLO
from keras_facenet import FaceNet
from db.database import student
from models.StudentModel import CapturedImages
import base64

router = APIRouter()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))   
cropper = YOLO(os.path.join(BASE_DIR, 'locals', 'yolo.pt'))
embedder = FaceNet()
embeddings_list = []
count = 0

# @ExceptionHandler
def crop_faces(img):
    results = cropper.predict(img)
    result = results[0]
    if len(result.boxes) == 0:
        print("No face detected")
        return {'message': 'No face detected', 'status': 0}  
    box = result.boxes
    confidence = box.conf[0]
    if confidence < 0.85:  
        print("Low confidence detection")
        return {'message': 'No face detected', 'status': 1}
    x1, y1, x2, y2 = box.xyxy[0]
    x1, y1, x2, y2 = round(x1.item()), round(y1.item()), round(x2.item()), round(y2.item())
    h, w, ch = img.shape
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(w, x2), min(h, y2)
    face = img[y1:y2, x1:x2]
    if face is not None: 
        face = cv2.cvtColor(face, cv2.COLOR_RGB2BGR)
    return face

# @ExceptionHandler
def get_embeddings(face, embedder):
    face = face.astype('float32')
    face = np.expand_dims(face, axis=0)
    return embedder.embeddings(face)

@router.post("/verify-batch")
async def verify_batch(data: CapturedImages):
    global embeddings_list
    global count
    low_confidence_count = 0
    no_face_count = 0
    id_number = data.id_number
    images_length = len(data.images)
    
    for image in data.images:
        image_data = base64.b64decode(image.split(",")[1])
        np_arr = np.frombuffer(image_data, np.uint8)
        img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        face = crop_faces(img)
        
        if isinstance(face, dict):
            if face['status'] == 0:
                no_face_count += 1
            else:
                low_confidence_count += 1
        else:
            embedding = get_embeddings(face, embedder)
            embeddings_list.append(embedding)
            count += 1
            print(f"embedding {count} taken")
    
    # Ensure MongoDB update is awaited
    print(id_number)
    print(type(embeddings_list))
    print(len(embeddings_list))
    print(type(embeddings_list[0]))
    embeddings_list = [embedding.tolist() for embedding in embeddings_list]
    try:
        result = await student.update_one(
            {"id_number": id_number},
            {"$set": {"embeddings": embeddings_list}}
        )
    except Exception as e:
        print(f"MongoDB Error: {e}")

    embeddings_list.clear()
    
    if result.matched_count:  # Now `matched_count` is accessible
        print("Data uploaded to MongoDB")
        if count == images_length:
            count = 0
            return {'status': 200, 'message': 'Your face embeddings have been successfully updated'}
        else:
            taken_count = count  # Store count before resetting
            count = 0
            return {'status': 207, 'message': f'{taken_count} embeddings updated successfully. Resend {images_length - taken_count} images'}
    else:
        count = 0
        return {'status': 400, 'message': 'Error in updating face embeddings in the database'}
