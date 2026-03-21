"""
/api/login – Driver authentication (PDF: Face Detection + Recognition).
Login: face image → match (2D and/or 3D) → driver_id, driver_name, age.
Register: live photo (base64) + name, age → MediaPipe landmarks → 3D embedding → face_embedding_3d.
"""

import base64
import io
from typing import Optional

import cv2
import numpy as np
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from PIL import Image

from src.schemas.payloads import LoginResponse, RegisterLiveBody, RegisterResponse
from src.driver_identity import match_embedding_to_driver
from src.face_embedding_3d import build_3d_embedding
from database import driver_repository
from training.scripts.face_detection.face_detection import FaceDetector
from training.scripts.face_recongnition.face_recognition import ArcFaceModel
from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/login", tags=["login"])

try:
    _arcface_model: ArcFaceModel | None = ArcFaceModel()
    logger.info("ArcFace model ready for login route")
except Exception as e:
    logger.warning("ArcFace model not available for login: %s", e)
    _arcface_model = None

_face_detector: FaceDetector | None = FaceDetector()


def _get_face_model() -> ArcFaceModel | None:
    return _arcface_model


def _decode_image(raw: bytes) -> Optional[np.ndarray]:
    """Decode image bytes to BGR frame. Tries OpenCV first, then Pillow for broader format support."""
    if not raw or len(raw) == 0:
        return None
    nparr = np.frombuffer(raw, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is not None:
        return img
    try:
        pil_img = Image.open(io.BytesIO(raw))
        if pil_img.mode != "RGB":
            pil_img = pil_img.convert("RGB")
        img = np.array(pil_img)
        return cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    except Exception:
        return None


def _get_landmarks_from_image(img: np.ndarray):
    """Run MediaPipe Face Landmarker on full image; return (landmarks, img_w, img_h) or (None, None, None)."""
    if _face_detector is None:
        return None, None, None
    return _face_detector.get_landmarks(img)


def _extract_face_from_bytes(raw: bytes):
    """Decode image bytes and return largest face crop in BGR."""
    nparr = np.frombuffer(raw, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        return None

    model = _get_face_model()
    if model is None:
        return None

    try:
        detections = model.detector.detect_faces(img)
    except Exception:
        return None
    if not detections:
        return None

    faces = list(detections.values())
    largest = max(
        faces,
        key=lambda d: (d["facial_area"][2] - d["facial_area"][0])
        * (d["facial_area"][3] - d["facial_area"][1]),
    )
    x1, y1, x2, y2 = largest["facial_area"]
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(img.shape[1], x2), min(img.shape[0], y2)
    face = img[y1:y2, x1:x2]
    if face.shape[0] < 50 or face.shape[1] < 50:
        return None
    return face


@router.post("/", response_model=LoginResponse)
async def login(
    driver_id: Optional[str] = Form(None),
    image: UploadFile = File(...),
):
    """
    Login with face image. If driver_id provided, verify against that driver; else match against DB.
    Uses 3D embedding (MediaPipe) when available and 2D (ArcFace) for legacy drivers.
    """
    raw = await image.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Empty image")

    logger.info("Login attempt (driver_id=%s, image_size=%d bytes)", driver_id, len(raw))
    img = _decode_image(raw)
    if img is None:
        logger.warning("Login failed: could not decode image")
        raise HTTPException(status_code=400, detail="Could not decode image")

    emb_3d = None
    landmarks, _, _ = _get_landmarks_from_image(img)
    if landmarks is not None:
        emb_3d = build_3d_embedding(landmarks)

    emb_2d = None
    model = _get_face_model()
    if model is not None:
        face = _extract_face_from_bytes(raw)
        if face is not None:
            emb_2d = model.get_embedding(face)

    if emb_3d is None and emb_2d is None:
        raise HTTPException(status_code=400, detail="No valid face detected in image")

    driver, score = match_embedding_to_driver(
        embedding_2d=emb_2d,
        embedding_3d=emb_3d,
        driver_id=driver_id,
    )
    if not driver:
        logger.info("Login failed: face not recognised (score=%.3f)", score)
        raise HTTPException(status_code=401, detail="Face not recognized or invalid driver_id")

    logger.info("Login success: driver=%s score=%.3f", driver["driver_id"], score)
    driver_repository.update_last_seen(driver["driver_id"])
    return LoginResponse(
        driver_id=driver["driver_id"],
        driver_name=driver.get("name", ""),
        age=driver.get("age"),
        message="Login successful",
    )


def _normalize_image_base64(value: str) -> str:
    """Strip optional data URL prefix; remove newlines only (preserve space for +-fix later)."""
    s = (value or "").strip()
    if s.startswith("data:") and "," in s:
        s = s.split(",", 1)[1]
    # Remove newlines/tabs so line-wrapped base64 works; do not remove spaces (may be corrupted +)
    s = s.replace("\n", "").replace("\r", "").replace("\t", "")
    return s


@router.post("/register", response_model=RegisterResponse)
async def register(body: RegisterLiveBody):
    """
    First-time registration: live photo only (no file upload).
    Uses MediaPipe Face Landmarker to get 3D landmarks and stores face_embedding_3d.
    """
    image_b64 = _normalize_image_base64(body.image_base64)
    if not image_b64:
        raise HTTPException(
            status_code=400,
            detail="Missing image_base64. Send raw base64 or data URL (data:image/...;base64,...).",
        )
    try:
        raw = base64.b64decode(image_b64, validate=True)
    except Exception:
        # If sent as form data, + may have been converted to space; try fixing
        try:
            raw = base64.b64decode(image_b64.replace(" ", "+"), validate=True)
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid image_base64: ensure raw base64 or data URL. ({e!r})",
            )

    if not raw or len(raw) == 0:
        raise HTTPException(status_code=400, detail="Empty image")

    img = _decode_image(raw)
    if img is None:
        raise HTTPException(
            status_code=400,
            detail="Could not decode image. Ensure image_base64 is valid base64-encoded JPEG or PNG (e.g. from canvas.toDataURL('image/jpeg') or file read).",
        )

    landmarks, _, _ = _get_landmarks_from_image(img)
    if landmarks is None:
        raise HTTPException(
            status_code=400,
            detail="No valid face detected. Use a live photo from the camera.",
        )

    emb_3d = build_3d_embedding(landmarks)
    if emb_3d is None:
        raise HTTPException(
            status_code=400,
            detail="Could not build face embedding. Ensure a clear face is visible.",
        )

    logger.info("Registering driver: name=%s age=%s", body.name, body.age)
    driver = driver_repository.create_driver(
        driver_id=None,
        name=body.name,
        age=body.age,
        face_embedding=None,
        face_embedding_3d=emb_3d.astype(float).tolist(),
        face_image_path=None,
    )
    logger.info("Registration success: driver_id=%s", driver["driver_id"])
    return RegisterResponse(
        driver_id=driver["driver_id"],
        driver_name=body.name,
        age=body.age,
        message="Registration successful",
    )
