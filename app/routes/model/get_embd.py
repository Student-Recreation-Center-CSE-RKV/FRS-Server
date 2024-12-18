from fastapi import APIRouter
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Optional
from pydantic import BaseModel, Field
import base64
import numpy as np
import cv2
from ultralytics import YOLO
from keras_facenet import FaceNet
from .exception_handler import ExceptionHandler
import os
import pandas as pd
from pymongo import MongoClient
from bson.json_util import dumps
import json
from models.StudentModel import CapturedImages 
from db.database import student

router = APIRouter()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))   
cropper = YOLO(os.path.join(BASE_DIR, 'locals', 'yolo.pt'))
embedder = FaceNet()
embeddings_list = []
count = 0


 
@ExceptionHandler
def crop_faces(img):
    def return_crop_face(img, cropper):
        results = cropper.predict(img)
        result = results[0]
        if len(result.boxes) == 0:
            print("No face detected")
            return {'message':'No face detected' , 'status':0}  
        box = result.boxes
        confidence = box.conf[0]
        if confidence < 0.85:  
            print("Low confidence detection")
            return {'message':'No face detected' , 'status':1}
        x1, y1, x2, y2 = box.xyxy[0]
        x1, y1, x2, y2 = round(x1.item()), round(y1.item()), round(x2.item()), round(y2.item())
        h, w, ch = img.shape
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w, x2), min(h, y2)
        face = img[y1:y2, x1:x2]
        if face is not None: 
            face = cv2.cvtColor(face, cv2.COLOR_RGB2BGR)
        else:
            pass

        return face

@ExceptionHandler
def get_embeddings(face , embedder):
    face = face.astype('float32')
    face = np.expand_dims(face,axis=0)
    return embedder.embeddings(face)



@router.post("/verify-batch")
async def verify_batch(data: CapturedImages):
    global embeddings_list
    global count
    low_confidence_count = 0
    no_face_count = 0

    images_length = len(data.images)
    for image in data.images:
        image_data = base64.b64decode(image.split(",")[1])
        np_arr = np.frombuffer(image_data, np.uint8)
        img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        face = crop_faces(img)
        if isinstance(face,dict):
            if face.status == 0:
                no_face_count = no_face_count + 1
            else:
                low_confidence_count = low_confidence_count + 1
        else:
            embedding = get_embeddings(face, embedder)
            embeddings_list.append(embedding)
            count = count + 1
            print(f"embedding {count} taken")
    embeddings = [embed.tolist() for embed in embeddings_list]
    document = {
        "name" : data.form_data['formData']['name'],
        "id" : data.form_data['formData']['studentId'],
        "batch" : data.form_data['formData']['batch'],
        "branch" : data.form_data['formData']['branch'],
        "section" : data.form_data['formData']['section'],
        "embeddings" : embeddings
    }
    filter_query = {"id": data.form_data['formData']['studentId']}
    result = student.replace_one(filter_query,document,upsert=True)
    embeddings_list.clear()
    if result.matched_count:
        print("Data uploaded to mongodb")
        if(count == images_length):
            count=0
            return {'status':200,'message':'your face embeddings are taken sucessfully taken'}
        else:
            count=0
            return {'status':207 ,'message':f'{count} only sucessfully taken. Resend {images_length - count} images'}
    else:
        count=0
        return {'status':400 , 'message':'Error in inserting the data into the database'}
