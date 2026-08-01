import numpy as np
import cv2
from analysis import analyze_image_array
from calibration import fit_all_models
from sample_generator import generate_laser_spot_sample

def test_generate_sample_and_analyze():
    sample_img = generate_laser_spot_sample(target_ntu=10.0)
    assert sample_img is not None, "Sample image is None"
    assert sample_img.shape == (500, 500, 3), f"Unexpected shape {sample_img.shape}"

    res = analyze_image_array(sample_img)
    assert res is not None, "Analysis returned None"
    assert "shape" in res
    assert res["shape"] in ["Ellipse", "Circle"]
    assert res["equivalent_diameter"] > 0
    assert res["circularity"] > 0
    assert res["irregularity"] >= 0
    assert res["intensity"] > 0
    assert res["log_intensity"] > 0
    assert res["annotated_image"] is not None
    print(f"Analysis result shape={res['shape']}, diameter={res['equivalent_diameter']:.2f}, intensity={res['intensity']:.2f}, irregularity={res['irregularity']:.4f}")

def test_calibration_fit():
    models, summary = fit_all_models()
    assert "intensity" in models
    assert "diameter" in models
    assert "major_2a" in models
    assert "minor_2b" in models
    assert summary["intensity"]["r2"] >= 0
    assert summary["diameter"]["r2"] >= 0
    print("Calibration fit results:", {k: v['r2'] for k, v in summary.items()})

if __name__ == "__main__":
    test_generate_sample_and_analyze()
    test_calibration_fit()
    print("ALL BACKEND TESTS PASSED SUCCESSFULLY!")
