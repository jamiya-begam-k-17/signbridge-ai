"""
backend/main.py
---------------
FastAPI app for SignBridge.

Run from inside backend/:
    uvicorn main:app --reload --host 0.0.0.0 --port 8000
"""

from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware

import numpy as np
import cv2

from utils.predict_sign import predict_sign, reset_session

app = FastAPI(title="SignBridge API")

# Allow React dev server (port 5173) and any other origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def home():
    return {"message": "SignBridge GRU API is running"}


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "SignBridge API",
        "model_loaded": True,
        "model_type": "GRU + Temporal Attention",
        "num_classes": 10,
    }


@app.post("/reset")
def reset():
    """
    Clears the 40-frame sliding window.
    Called by the frontend whenever the user clicks 'Start Detection'.
    """
    reset_session()
    return {"status": "ok"}


@app.post("/predict")
async def predict(file: UploadFile = File(...)):
    """
    Accepts a single JPEG frame, feeds it into the sliding window,
    returns a prediction once the window is full.

    Response:
        { "prediction": "hello", "confidence": 0.94, "buffered": 40 }
        { "prediction": "",      "confidence": 0.0,  "buffered": 23 }  <- warming up
    """
    try:
        contents = await file.read()
        npimg    = np.frombuffer(contents, np.uint8)
        frame    = cv2.imdecode(npimg, cv2.IMREAD_COLOR)

        if frame is None:
            return {"error": "Could not decode image"}

        return predict_sign(frame)

    except Exception as e:
        return {"error": str(e)}









# ---------------------------------------------------------------





# from fastapi import FastAPI, UploadFile, File
# from fastapi.middleware.cors import CORSMiddleware

# import numpy as np
# import cv2

# from utils.predict_sign import predict_sign


# # =====================================
# # APP SETUP
# # =====================================
# app = FastAPI(title="SignBridge API")

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )


# # =====================================
# # ROOT
# # =====================================
# @app.get("/")
# def home():
#     return {"message": "SignBridge API running"}


# # =====================================
# # HEALTH CHECK ⭐
# # =====================================
# @app.get("/health")
# def health_check():
#     """
#     Used by frontend/devops to check
#     if backend + model are ready.
#     """
#     try:
#         # simple test call (no image)
#         status = "healthy"

#         return {
#             "status": status,
#             "service": "SignBridge API",
#             "model_loaded": True
#         }

#     except Exception as e:
#         return {
#             "status": "unhealthy",
#             "error": str(e)
#         }


# # =====================================
# # PREDICTION ENDPOINT
# # =====================================
# @app.post("/predict")
# async def predict(file: UploadFile = File(...)):
#     try:
#         contents = await file.read()

#         npimg = np.frombuffer(contents, np.uint8)
#         frame = cv2.imdecode(npimg, cv2.IMREAD_COLOR)

#         if frame is None:
#             return {"error": "Invalid image"}

#         prediction = predict_sign(frame)

#         return {"prediction": prediction}

#     except Exception as e:
#         return {"error": str(e)}