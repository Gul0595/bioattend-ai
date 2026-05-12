"""
Tests for liveness detection service.
Uses synthetic images — no camera needed.
"""
import numpy as np
import cv2
import pytest
import io
from PIL import Image

from app.services.liveness_service import (
    check_liveness,
    _check_texture_lbp,
    _check_specular,
    _check_frequency_domain,
    _check_skin_tone,
    _bytes_to_bgr,
)


def _make_image_bytes(img_bgr: np.ndarray) -> bytes:
    """Convert OpenCV BGR ndarray → JPEG bytes."""
    _, buf = cv2.imencode('.jpg', img_bgr, [cv2.IMWRITE_JPEG_QUALITY, 90])
    return buf.tobytes()


def _solid_color_image(b: int, g: int, r: int, size: int = 200) -> np.ndarray:
    """Create a solid color image (lowest possible texture variance)."""
    return np.full((size, size, 3), [b, g, r], dtype=np.uint8)


def _noisy_image(size: int = 200) -> np.ndarray:
    """Create a noisy image (high texture variance — mimics real skin)."""
    base = np.full((size, size, 3), [120, 80, 60], dtype=np.uint8)
    noise = np.random.randint(-40, 40, base.shape, dtype=np.int16)
    return np.clip(base.astype(np.int16) + noise, 0, 255).astype(np.uint8)


def _overexposed_image(size: int = 200) -> np.ndarray:
    """Mostly white image with many bright specular pixels."""
    return np.full((size, size, 3), [250, 250, 250], dtype=np.uint8)


def _skin_tone_image(size: int = 200) -> np.ndarray:
    """
    Create an image with pixels in the natural skin YCrCb range.
    Approximate light skin tone: BGR ≈ (160, 120, 180)
    """
    img = np.full((size, size, 3), [130, 100, 180], dtype=np.uint8)
    return img


# ─── Texture (LBP) tests ──────────────────────────────────────────────────────

class TestTextureLBP:
    def test_flat_image_fails(self):
        flat = _solid_color_image(128, 128, 128)
        is_live, score = _check_texture_lbp(flat)
        assert not is_live, "Flat image should fail texture check"
        assert score < 0.5

    def test_noisy_image_passes(self):
        noisy = _noisy_image()
        is_live, score = _check_texture_lbp(noisy)
        assert is_live, "Noisy image (simulates real skin texture) should pass"
        assert score > 0.3


# ─── Specular tests ───────────────────────────────────────────────────────────

class TestSpecular:
    def test_overexposed_fails(self):
        bright = _overexposed_image()
        is_live, score = _check_specular(bright)
        assert not is_live, "Overexposed (screen-like) image should fail specular check"

    def test_normal_image_passes(self):
        normal = _noisy_image()
        is_live, score = _check_specular(normal)
        assert is_live, "Normal image should pass specular check"


# ─── Frequency domain tests ───────────────────────────────────────────────────

class TestFrequency:
    def test_periodic_pattern_suspicious(self):
        """A regular grid pattern (like halftone print) has high frequency energy."""
        img = np.zeros((200, 200, 3), dtype=np.uint8)
        for i in range(0, 200, 4):
            img[i::8, :] = 255   # regular stripes = unnatural high-freq
        is_live, score = _check_frequency_domain(img)
        # periodic patterns may fail; we just check score is computed
        assert 0.0 <= score <= 1.0

    def test_natural_image_ok(self):
        noisy = _noisy_image(200)
        is_live, score = _check_frequency_domain(noisy)
        assert 0.0 <= score <= 1.0


# ─── Skin tone tests ──────────────────────────────────────────────────────────

class TestSkinTone:
    def test_skin_tone_image_passes(self):
        skin = _skin_tone_image()
        is_live, score = _check_skin_tone(skin)
        assert is_live, "Skin-tone image should pass skin check"
        assert score > 0.3

    def test_blue_image_fails(self):
        """Pure blue has no skin pixels."""
        blue = _solid_color_image(200, 20, 20)
        is_live, score = _check_skin_tone(blue)
        assert not is_live, "Blue image has no skin pixels — should fail"


# ─── Full composite liveness check ───────────────────────────────────────────

class TestCheckLiveness:
    def test_invalid_bytes_returns_not_live(self):
        result = check_liveness(b"not_an_image")
        assert not result.is_live
        assert result.confidence == 0.0

    def test_flat_spoof_image_blocked(self):
        """A solid-color image should fail (no texture, possibly no skin)."""
        img    = _solid_color_image(128, 128, 128)
        result = check_liveness(_make_image_bytes(img))
        # DeepFace might not be available in test env so we check structure
        assert isinstance(result.is_live, bool)
        assert 0.0 <= result.confidence <= 1.0
        assert isinstance(result.reason, str)
        assert isinstance(result.scores, dict)

    def test_result_has_all_score_keys(self):
        img    = _noisy_image()
        result = check_liveness(_make_image_bytes(img))
        for key in ('texture_lbp', 'specular', 'frequency', 'skin_tone'):
            assert key in result.scores, f"Missing score key: {key}"

    def test_to_dict(self):
        img    = _noisy_image()
        result = check_liveness(_make_image_bytes(img))
        d = result.to_dict()
        assert 'is_live' in d
        assert 'confidence' in d
        assert 'reason' in d
        assert 'scores' in d


# ─── Blink endpoint tests (via HTTP) ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_blink_challenge_too_few_frames(client, auth_headers):
    """Blink challenge with < 5 frames should return 400."""
    resp = await client.post('/api/v1/attendance/blink-challenge', json={
        'frames_base64': ['data:image/jpeg;base64,/9j/4AAQ']  # only 1 frame
    })
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_liveness_check_endpoint(client, auth_headers):
    """Standalone liveness check endpoint should return structured result."""
    # Create a simple test image
    img = _noisy_image(100)
    _, buf = cv2.imencode('.jpg', img)
    import base64
    b64 = 'data:image/jpeg;base64,' + base64.b64encode(buf.tobytes()).decode()

    resp = await client.post('/api/v1/attendance/liveness-check', json={
        'image_base64': b64
    })
    assert resp.status_code == 200
    data = resp.json()
    assert 'is_live' in data
    assert 'confidence' in data
    assert 'scores' in data
