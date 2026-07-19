"""
Backward compatibility module for alpr_utils.
Re-exports preprocess_license_plate from the logic layer (logic.alpr_utils).
"""
from logic.alpr_utils import (
    extract_value,
    maximize_contrast,
    preprocess_image,
    detect_and_align_plate,
    preprocess_license_plate
)

__all__ = [
    "extract_value",
    "maximize_contrast",
    "preprocess_image",
    "detect_and_align_plate",
    "preprocess_license_plate"
]
