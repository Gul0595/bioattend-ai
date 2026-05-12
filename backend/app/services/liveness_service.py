"""
BioAttend Ultimate — Liveness Detection Service
================================================
Anti-spoofing layer that sits BEFORE face matching.
Prevents attendance fraud via printed photos, phone screens, or video replay.

Techniques used (layered defense):
1. DeepFace built-in anti_spoofing flag  (primary — deep CNN model)
2. Texture analysis — LBP (Local Binary Pattern) variance
   Real skin has high micro-texture variance; printed paper/screens are flat.
3. Specular reflection check
   Screens and glossy prints produce bright specular hotspots.
4. Frequency domain analysis (FFT)
   Printed/screen images have unnatural high-frequency patterns (moiré, pixels).
5. Color space analysis (YCrCb skin tone naturalness)
   Real skin has a narrow natural distribution in Cr/Cb channels.

Any single layer alone can be fooled. Together they are very hard to beat.
"""
from __future__ import annotations

import io
import logging
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)


# ─── Result dataclass ─────────────────────────────────────────────────────────

@dataclass
class LivenessResult:
    is_live: bool
    confidence: float          # 0.0 = definitely spoof, 1.0 = definitely real
    reason: str                # Human-readable explanation
    scores: dict               # Per-check breakdown for debugging

    def to_dict(self) -> dict:
        return {
            "is_live": self.is_live,
            "confidence": self.confidence,
            "reason": self.reason,
            "scores": self.scores,
        }


# ─── Thresholds (tunable via env in production) ───────────────────────────────

LBP_VARIANCE_THRESHOLD      = 80.0    # Below this → too flat → spoof
SPECULAR_PIXEL_MAX_FRACTION = 0.08    # Above this → too many bright spots → screen
FFT_HIGH_FREQ_RATIO_MAX     = 0.45    # Above this → unnatural pattern → print/screen
SKIN_PIXEL_MIN_FRACTION     = 0.15    # Below this → no natural skin tone detected
OVERALL_LIVENESS_THRESHOLD  = 0.55    # Final weighted score to pass


# ─── Helper: image bytes → OpenCV BGR ndarray ─────────────────────────────────

def _bytes_to_bgr(image_bytes: bytes) -> np.ndarray:
    arr = np.frombuffer(image_bytes, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Could not decode image")
    return img


def _to_temp_file(image_bytes: bytes) -> str:
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    tmp = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
    img.save(tmp, format="JPEG", quality=95)
    tmp.flush()
    tmp.close()
    return tmp.name


# ─── Check 1: DeepFace Anti-Spoofing (CNN-based) ─────────────────────────────

def _check_deepface_antispoof(image_bytes: bytes) -> tuple[bool, float]:
    """
    Uses DeepFace's built-in anti-spoofing model (Silent-Face).
    Returns (is_real, confidence).
    """
    tmp = _to_temp_file(image_bytes)
    try:
        from deepface import DeepFace
        results = DeepFace.extract_faces(
            img_path=tmp,
            detector_backend="retinaface",
            anti_spoofing=True,
            enforce_detection=False,
        )
        if not results:
            return False, 0.0

        face = results[0]
        # DeepFace returns is_real and antispoof_score per detected face
        is_real = face.get("is_real", False)
        score = float(face.get("antispoof_score", 0.0))
        return is_real, score

    except Exception as exc:
        logger.warning("DeepFace anti-spoof check failed: %s", exc)
        # If model not available, return neutral (don't block)
        return True, 0.5
    finally:
        Path(tmp).unlink(missing_ok=True)


# ─── Check 2: LBP Texture Variance ───────────────────────────────────────────

def _check_texture_lbp(img_bgr: np.ndarray) -> tuple[bool, float]:
    """
    Local Binary Pattern variance.
    Real faces have high micro-texture variance.
    Flat photos/screens score very low.
    """
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)

    # Resize for consistency
    h, w = gray.shape
    if w > 300:
        scale = 300 / w
        gray = cv2.resize(gray, (300, int(h * scale)))

    # Compute LBP-like texture using Laplacian variance (fast approximation)
    laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()

    # Also compute local standard deviation in blocks
    block_size = 16
    stds = []
    for y in range(0, gray.shape[0] - block_size, block_size):
        for x in range(0, gray.shape[1] - block_size, block_size):
            block = gray[y:y+block_size, x:x+block_size]
            stds.append(float(np.std(block)))

    mean_local_std = np.mean(stds) if stds else 0.0
    combined_score = (laplacian_var * 0.6 + mean_local_std * 0.4)

    # Normalize to 0–1 (real faces typically score 80–500+)
    normalized = min(1.0, combined_score / 200.0)
    is_live = combined_score >= LBP_VARIANCE_THRESHOLD

    return is_live, round(normalized, 3)


# ─── Check 3: Specular Reflection ────────────────────────────────────────────

def _check_specular(img_bgr: np.ndarray) -> tuple[bool, float]:
    """
    Screens and glossy prints produce unnatural specular highlights.
    Count pixels above brightness threshold.
    Real faces in normal lighting have few such pixels.
    """
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    _, bright_mask = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY)
    bright_fraction = float(np.sum(bright_mask > 0)) / (gray.shape[0] * gray.shape[1])

    # Also check for uniform glare patch (screens show rectangular bright regions)
    # using connected components
    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(bright_mask, connectivity=8)
    large_bright_patches = sum(
        1 for i in range(1, num_labels)
        if stats[i, cv2.CC_STAT_AREA] > (gray.shape[0] * gray.shape[1] * 0.02)
    )

    is_suspicious = (bright_fraction > SPECULAR_PIXEL_MAX_FRACTION) or (large_bright_patches > 2)
    score = 1.0 - min(1.0, bright_fraction / SPECULAR_PIXEL_MAX_FRACTION * 0.7
                      + large_bright_patches * 0.1)

    return (not is_suspicious), round(max(0.0, score), 3)


# ─── Check 4: Frequency Domain (FFT) ─────────────────────────────────────────

def _check_frequency_domain(img_bgr: np.ndarray) -> tuple[bool, float]:
    """
    Printed photos and screens introduce regular patterns (halftone dots, pixels)
    that show as peaks in the frequency domain.
    Real faces have a more natural frequency spectrum.
    """
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY).astype(np.float32)
    if gray.shape[1] > 256:
        gray = cv2.resize(gray, (256, 256))

    fft = np.fft.fft2(gray)
    fft_shift = np.fft.fftshift(fft)
    magnitude = np.log(np.abs(fft_shift) + 1)

    h, w = magnitude.shape
    cy, cx = h // 2, w // 2
    radius = min(h, w) // 4

    # Create masks for low vs high frequency regions
    Y, X = np.ogrid[:h, :w]
    dist_from_center = np.sqrt((X - cx)**2 + (Y - cy)**2)

    low_freq_energy  = float(magnitude[dist_from_center <= radius].mean())
    high_freq_energy = float(magnitude[dist_from_center >  radius].mean())

    ratio = high_freq_energy / (low_freq_energy + 1e-6)
    is_natural = ratio < FFT_HIGH_FREQ_RATIO_MAX
    score = 1.0 - min(1.0, ratio / FFT_HIGH_FREQ_RATIO_MAX)

    return is_natural, round(score, 3)


# ─── Check 5: Skin Color Distribution (YCrCb) ────────────────────────────────

def _check_skin_tone(img_bgr: np.ndarray) -> tuple[bool, float]:
    """
    Natural skin tones cluster in a specific region of YCrCb space.
    Printed images may shift color distribution outside this range.
    Very low natural skin pixel count → suspicious.
    """
    # Resize for speed
    img = cv2.resize(img_bgr, (200, 200))
    ycrcb = cv2.cvtColor(img, cv2.COLOR_BGR2YCrCb)

    # Standard skin range in YCrCb
    lower = np.array([0,   133, 77],  dtype=np.uint8)
    upper = np.array([255, 173, 127], dtype=np.uint8)
    skin_mask = cv2.inRange(ycrcb, lower, upper)

    skin_fraction = float(np.sum(skin_mask > 0)) / (200 * 200)
    is_natural = skin_fraction >= SKIN_PIXEL_MIN_FRACTION
    score = min(1.0, skin_fraction / 0.35)  # 35% skin → max score

    return is_natural, round(score, 3)


# ─── Main Liveness Check (composite) ─────────────────────────────────────────

def check_liveness(image_bytes: bytes) -> LivenessResult:
    """
    Run all liveness checks and return a composite LivenessResult.

    Weights:
      - DeepFace anti-spoof (CNN): 40%
      - Texture (LBP):             25%
      - Specular reflection:        15%
      - Frequency domain:           10%
      - Skin tone:                  10%
    """
    try:
        img_bgr = _bytes_to_bgr(image_bytes)
    except Exception as exc:
        return LivenessResult(
            is_live=False,
            confidence=0.0,
            reason="Could not decode image",
            scores={},
        )

    scores = {}
    checks = {}

    # ── Run each check ────────────────────────────────────────────────────────
    try:
        ds_live, ds_score = _check_deepface_antispoof(image_bytes)
        scores["deepface_antispoof"] = ds_score
        checks["deepface_antispoof"] = ds_live
    except Exception as e:
        logger.warning("DeepFace check error: %s", e)
        scores["deepface_antispoof"] = 0.5
        checks["deepface_antispoof"] = True  # neutral fallback

    try:
        tex_live, tex_score = _check_texture_lbp(img_bgr)
        scores["texture_lbp"] = tex_score
        checks["texture_lbp"] = tex_live
    except Exception as e:
        logger.warning("Texture check error: %s", e)
        scores["texture_lbp"] = 0.5
        checks["texture_lbp"] = True

    try:
        spec_live, spec_score = _check_specular(img_bgr)
        scores["specular"] = spec_score
        checks["specular"] = spec_live
    except Exception as e:
        logger.warning("Specular check error: %s", e)
        scores["specular"] = 0.5
        checks["specular"] = True

    try:
        fft_live, fft_score = _check_frequency_domain(img_bgr)
        scores["frequency"] = fft_score
        checks["frequency"] = fft_live
    except Exception as e:
        logger.warning("FFT check error: %s", e)
        scores["frequency"] = 0.5
        checks["frequency"] = True

    try:
        skin_live, skin_score = _check_skin_tone(img_bgr)
        scores["skin_tone"] = skin_score
        checks["skin_tone"] = skin_live
    except Exception as e:
        logger.warning("Skin tone check error: %s", e)
        scores["skin_tone"] = 0.5
        checks["skin_tone"] = True

    # ── Weighted composite score ───────────────────────────────────────────────
    weights = {
        "deepface_antispoof": 0.40,
        "texture_lbp":        0.25,
        "specular":           0.15,
        "frequency":          0.10,
        "skin_tone":          0.10,
    }

    weighted_score = sum(scores.get(k, 0.5) * w for k, w in weights.items())
    weighted_score = round(weighted_score, 3)

    # Hard-fail: if DeepFace explicitly says spoof, override regardless
    deepface_hard_fail = not checks.get("deepface_antispoof", True) and scores.get("deepface_antispoof", 1.0) < 0.3

    # Hard-fail: if ≥3 checks fail
    failed_checks = [k for k, v in checks.items() if not v]
    majority_fail = len(failed_checks) >= 3

    is_live = (weighted_score >= OVERALL_LIVENESS_THRESHOLD
               and not deepface_hard_fail
               and not majority_fail)

    if deepface_hard_fail:
        reason = "Anti-spoofing model detected a fake face (photo/screen replay attempt)"
    elif majority_fail:
        reason = f"Multiple liveness checks failed: {', '.join(failed_checks)}"
    elif not is_live:
        reason = f"Liveness score {weighted_score:.2f} below threshold {OVERALL_LIVENESS_THRESHOLD}"
    else:
        reason = "Liveness verified — real person detected"

    return LivenessResult(
        is_live=is_live,
        confidence=weighted_score,
        reason=reason,
        scores=scores,
    )


# ─── Blink detection (for challenge-response liveness) ───────────────────────

def detect_blink_from_frames(frames_bytes: list[bytes]) -> bool:
    """
    Given a short sequence of frames (e.g. 10–20 captured over ~1s),
    detect whether the person blinked.
    Uses Eye Aspect Ratio (EAR) via facial landmarks.

    Returns True if a blink was detected (strong liveness indicator).
    """
    try:
        import mediapipe as mp

        mp_face_mesh = mp.solutions.face_mesh
        # MediaPipe eye landmark indices
        LEFT_EYE  = [33, 160, 158, 133, 153, 144]
        RIGHT_EYE = [362, 385, 387, 263, 373, 380]

        def _ear(landmarks, eye_indices, img_w, img_h):
            pts = [(landmarks[i].x * img_w, landmarks[i].y * img_h) for i in eye_indices]
            # Vertical distances
            v1 = np.linalg.norm(np.array(pts[1]) - np.array(pts[5]))
            v2 = np.linalg.norm(np.array(pts[2]) - np.array(pts[4]))
            # Horizontal distance
            h  = np.linalg.norm(np.array(pts[0]) - np.array(pts[3]))
            return (v1 + v2) / (2.0 * h + 1e-6)

        EAR_THRESHOLD = 0.21
        ears = []

        with mp_face_mesh.FaceMesh(static_image_mode=True, max_num_faces=1,
                                    refine_landmarks=True) as mesh:
            for fb in frames_bytes:
                img = Image.open(io.BytesIO(fb)).convert("RGB")
                arr = np.array(img)
                result = mesh.process(arr)
                if result.multi_face_landmarks:
                    lms = result.multi_face_landmarks[0].landmark
                    h, w = arr.shape[:2]
                    left_ear  = _ear(lms, LEFT_EYE,  w, h)
                    right_ear = _ear(lms, RIGHT_EYE, w, h)
                    ears.append((left_ear + right_ear) / 2.0)

        if len(ears) < 3:
            return False

        # Blink = EAR dips below threshold between two normal-EAR frames
        blinked = False
        for i in range(1, len(ears) - 1):
            if ears[i] < EAR_THRESHOLD and ears[i-1] >= EAR_THRESHOLD:
                blinked = True
                break

        return blinked

    except ImportError:
        logger.warning("mediapipe not installed — blink detection skipped")
        return True   # Don't block if library unavailable
    except Exception as exc:
        logger.warning("Blink detection error: %s", exc)
        return True
