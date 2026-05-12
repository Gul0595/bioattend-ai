import io
from typing import Optional

import face_recognition
import numpy as np
from PIL import Image


def extract_embedding(image_bytes: bytes) -> Optional[list[float]]:
    """
    Extract 128D face embedding using face_recognition
    """

    image = face_recognition.load_image_file(io.BytesIO(image_bytes))

    face_locations = face_recognition.face_locations(image)

    if len(face_locations) == 0:
        return None

    encodings = face_recognition.face_encodings(image, face_locations)

    if len(encodings) == 0:
        return None

    return encodings[0].tolist()


def verify_face(
    image_bytes: bytes,
    stored_embedding: list[float],
) -> tuple[bool, float]:
    """
    Compare uploaded face with stored embedding
    """

    query_embedding = extract_embedding(image_bytes)

    if query_embedding is None:
        return False, 0.0

    distance = np.linalg.norm(
        np.array(query_embedding) - np.array(stored_embedding)
    )

    matched = distance < 0.5

    confidence = round(1 - distance, 4)

    return matched, confidence


def match_face(
    image_bytes: bytes,
    gallery: list[dict],
) -> tuple[Optional[object], float]:
    """
    Match face against employee gallery
    """

    probe_embedding = extract_embedding(image_bytes)

    if probe_embedding is None:
        return None, 0.0

    best_match = None
    best_distance = float("inf")

    for employee in gallery:

        stored_embedding = employee.get("embedding")

        if not stored_embedding:
            continue

        distance = np.linalg.norm(
            np.array(probe_embedding) - np.array(stored_embedding)
        )

        if distance < best_distance:
            best_distance = distance
            best_match = employee["employee_id"]

    confidence = round(1 - best_distance, 4)

    if best_distance < 0.5:
        return best_match, confidence

    return None, confidence


def detect_face(image_bytes: bytes) -> bool:
    """
    Detect whether image contains a face
    """

    image = face_recognition.load_image_file(io.BytesIO(image_bytes))

    face_locations = face_recognition.face_locations(image)

    return len(face_locations) > 0