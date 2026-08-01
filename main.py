import base64
import os
import cv2
import numpy as np
from fastapi import FastAPI, File, UploadFile, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Dict, List, Optional

from analysis import analyze_image_array
from calibration import (
    calibration_data,
    fit_all_models,
    fit_intensity_model,
    fit_geometry_model,
)
from storage import get_history, add_history_entry, clear_history
from sample_generator import get_preset_samples

app = FastAPI(
    title="AquaSpot Laser Turbidity Analyzer API",
    description="Backend service running OpenCV image analysis and SciPy curve fitting calibrations.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def calculate_water_quality(ntu: float) -> dict:
    """Classifies water turbidity per WHO / BIS standard safety guidelines."""
    if ntu <= 1.0:
        return {
            "status": "Excellent",
            "category": "Ultra-Pure / Safe",
            "badge_color": "emerald",
            "who_standard": "0 – 1 NTU: Excellent drinking water standard (Ultra-filtered).",
            "recommendation": "Optimal quality. Safe for direct consumption.",
        }
    elif ntu <= 5.0:
        return {
            "status": "Good",
            "category": "Acceptable Drinking Water",
            "badge_color": "cyan",
            "who_standard": "1 – 5 NTU: Acceptable drinking water quality threshold.",
            "recommendation": "Safe for drinking. Standard municipal quality.",
        }
    elif ntu <= 10.0:
        return {
            "status": "Fair",
            "category": "Slightly Turbid",
            "badge_color": "amber",
            "who_standard": "5 – 10 NTU: Noticeable haze; filtration recommended.",
            "recommendation": "Requires particle filtration before domestic use.",
        }
    else:
        return {
            "status": "Poor",
            "category": "Highly Turbid",
            "badge_color": "rose",
            "who_standard": "10+ NTU: Exceeds WHO safety threshold.",
            "recommendation": "Unsafe for direct consumption without treatment.",
        }


@app.get("/api/health")
def read_health():
    return {
        "status": "online",
        "app": "AquaSpot Laser Turbidity Analyzer",
        "version": "1.0.0",
    }


@app.post("/analyze")
@app.post("/api/analyze")
async def analyze(file: UploadFile = File(...)):
    """
    Upload an image file (multipart/form-data), perform OpenCV analysis pipeline,
    and compute water turbidity across all 4 calibrated models.
    """
    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    np_arr = np.frombuffer(contents, np.uint8)
    image = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

    if image is None:
        return {
            "error": "Failed to decode image file. Please upload a valid PNG or JPG image."
        }

    # Run OpenCV analysis pipeline
    result = analyze_image_array(image)
    if result is None:
        return {
            "error": "No upper red spot detected. Check laser alignment, surface distance, or reduce ambient light."
        }

    # Fit calibration models
    models, summary = fit_all_models()

    turbidity_I = models["intensity"](result["intensity"])
    turbidity_D = models["diameter"](result["equivalent_diameter"])
    turbidity_A = models["major_2a"](result["major"])
    turbidity_B = models["minor_2b"](result["minor"])

    # Find highest R^2 model
    r2_scores = {
        "diameter": summary["diameter"]["r2"],
        "intensity": summary["intensity"]["r2"],
        "major_2a": summary["major_2a"]["r2"],
        "minor_2b": summary["minor_2b"]["r2"],
    }

    best_method = max(r2_scores, key=r2_scores.get)

    method_values = {
        "diameter": turbidity_D,
        "intensity": turbidity_I,
        "major_2a": turbidity_A,
        "minor_2b": turbidity_B,
    }

    primary_ntu = method_values[best_method]
    water_quality = calculate_water_quality(primary_ntu)

    # Base64 encode original and annotated images
    _, buffer_ann = cv2.imencode(".png", result["annotated_image"])
    annotated_b64 = base64.b64encode(buffer_ann).decode("utf-8")

    _, buffer_orig = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, 85])
    original_b64 = base64.b64encode(buffer_orig).decode("utf-8")

    response_payload = {
        "filename": file.filename,
        "shape": result["shape"],
        "major_axis": round(result["major"], 2),
        "minor_axis": round(result["minor"], 2),
        "equivalent_diameter": round(result["equivalent_diameter"], 2),
        "mean_radius": round(result["mean_radius"], 2),
        "radius_std": round(result["radius_std"], 2),
        "irregularity": round(result["irregularity"], 4),
        "circularity": round(result["circularity"], 4),
        "area": round(result["area"], 1),
        "perimeter": round(result["perimeter"], 1),
        "centroid": [round(c, 1) for c in result["centroid"]],
        "intensity": round(result["intensity"], 2),
        "log_intensity": round(result["log_intensity"], 4),
        "turbidity_from_intensity": {
            "value": turbidity_I,
            "r2": summary["intensity"]["r2"],
            "name": "Exponential Intensity",
        },
        "turbidity_from_diameter": {
            "value": turbidity_D,
            "r2": summary["diameter"]["r2"],
            "name": "Equivalent Diameter",
        },
        "turbidity_from_2a": {
            "value": turbidity_A,
            "r2": summary["major_2a"]["r2"],
            "name": "Major Axis (2a)",
        },
        "turbidity_from_2b": {
            "value": turbidity_B,
            "r2": summary["minor_2b"]["r2"],
            "name": "Minor Axis (2b)",
        },
        "best_method": best_method,
        "primary_ntu": primary_ntu,
        "water_quality": water_quality,
        "annotated_image_base64": annotated_b64,
        "original_image_base64": original_b64,
    }

    # Store entry in history
    add_history_entry({
        "filename": file.filename or "sample_image.png",
        "shape": response_payload["shape"],
        "equivalent_diameter": response_payload["equivalent_diameter"],
        "irregularity": response_payload["irregularity"],
        "intensity": response_payload["intensity"],
        "primary_ntu": primary_ntu,
        "water_quality_status": water_quality["status"],
        "best_method": best_method,
        "turbidity_from_intensity": turbidity_I,
        "turbidity_from_diameter": turbidity_D,
        "turbidity_from_2a": turbidity_A,
        "turbidity_from_2b": turbidity_B,
        "thumbnail": annotated_b64,
    })

    return response_payload


@app.get("/calibration")
@app.get("/api/calibration")
def get_calibration():
    """Returns current calibration datasets and fitted model formulas."""
    models, summary = fit_all_models()
    return {
        "datasets": calibration_data,
        "models_summary": summary,
    }


class CalibrationUpdatePayload(BaseModel):
    intensity: Optional[List[List[float]]] = None
    diameter: Optional[List[List[float]]] = None
    major_2a: Optional[List[List[float]]] = None
    minor_2b: Optional[List[List[float]]] = None


@app.put("/calibration")
@app.put("/api/calibration")
def update_calibration(payload: CalibrationUpdatePayload):
    """Updates calibration datasets."""
    if payload.intensity is not None:
        calibration_data["intensity"] = payload.intensity
    if payload.diameter is not None:
        calibration_data["diameter"] = payload.diameter
    if payload.major_2a is not None:
        calibration_data["major_2a"] = payload.major_2a
    if payload.minor_2b is not None:
        calibration_data["minor_2b"] = payload.minor_2b

    models, summary = fit_all_models()
    return {
        "message": "Calibration datasets updated successfully.",
        "datasets": calibration_data,
        "models_summary": summary,
    }


@app.post("/calibration/fit")
@app.post("/api/calibration/fit")
def refit_calibration():
    """Re-runs SciPy curve_fit and NumPy polyfit on current calibration datasets."""
    models, summary = fit_all_models()
    return {
        "message": "Calibration models successfully re-fitted.",
        "models_summary": summary,
    }


@app.get("/history")
@app.get("/api/history")
def fetch_history():
    """Returns past analysis history records."""
    return get_history()


@app.delete("/history")
@app.delete("/api/history")
def clear_history_data():
    """Clears history records."""
    clear_history()
    return {"message": "History cleared successfully."}


@app.get("/samples")
@app.get("/api/samples")
def get_samples():
    """Returns preset test images for quick frontend evaluation."""
    return get_preset_samples()


# Mount Static Frontend Build (if available)
dist_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "dist")
if os.path.exists(dist_path):
    app.mount("/", StaticFiles(directory=dist_path, html=True), name="static")
