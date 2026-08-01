import numpy as np
from scipy.optimize import curve_fit

# Default seed datasets (NTU, pixel_metric)
DEFAULT_CALIBRATION = {
    "intensity": [
        [0.0, 220.0],
        [10.0, 180.0],
        [20.0, 140.0],
        [30.0, 100.0],
        [40.0, 70.0],
    ],
    "diameter": [
        [0.0, 120.0],
        [10.0, 180.0],
        [20.0, 260.0],
        [30.0, 340.0],
        [40.0, 420.0],
    ],
    "major_2a": [
        [0.0, 150.0],
        [10.0, 220.0],
        [20.0, 300.0],
        [30.0, 390.0],
        [40.0, 470.0],
    ],
    "minor_2b": [
        [0.0, 90.0],
        [10.0, 150.0],
        [20.0, 210.0],
        [30.0, 290.0],
        [40.0, 360.0],
    ],
}

# Active calibration state
calibration_data = {
    "intensity": list(DEFAULT_CALIBRATION["intensity"]),
    "diameter": list(DEFAULT_CALIBRATION["diameter"]),
    "major_2a": list(DEFAULT_CALIBRATION["major_2a"]),
    "minor_2b": list(DEFAULT_CALIBRATION["minor_2b"]),
}


def exp_model(T, a, b):
    return a * np.exp(b * T)


def fit_intensity_model(data_list):
    data = np.array(data_list, dtype=float)
    if len(data) < 2:
        def fallback_func(I):
            return 0.0
        return fallback_func, {"a": 1.0, "b": -0.01}, 0.0

    try:
        # Initial guess: a ~ I[0], b ~ -0.02
        p0 = [max(data[0, 1], 1.0), -0.02]
        popt, _ = curve_fit(exp_model, data[:, 0], data[:, 1], p0=p0, maxfev=5000)
        a, b = float(popt[0]), float(popt[1])

        pred = exp_model(data[:, 0], a, b)
        ss_res = np.sum((data[:, 1] - pred) ** 2)
        ss_tot = np.sum((data[:, 1] - data[:, 1].mean()) ** 2)
        r2 = float(1 - ss_res / ss_tot) if ss_tot > 0 else 1.0

        def intensity_to_turbidity(I):
            if a <= 0 or b == 0:
                return 0.0
            ratio = max(float(I) / a, 1e-6)
            val = float(np.log(ratio) / b)
            return max(0.0, round(val, 2))

        return intensity_to_turbidity, {"a": a, "b": b}, round(r2, 4)
    except Exception as e:
        # Fallback linear fit if exponential fit fails to converge
        coeffs = np.polyfit(data[:, 1], data[:, 0], 1)
        r2 = 0.5
        def fallback_intensity(I):
            return max(0.0, round(float(np.polyval(coeffs, I)), 2))
        return fallback_intensity, {"a": float(coeffs[0]), "b": float(coeffs[1])}, r2


def fit_geometry_model(data_list):
    data = np.array(data_list, dtype=float)
    if len(data) < 2:
        def fallback_func(v):
            return 0.0
        return fallback_func, [0.0, 0.0, 0.0], 0.0

    degree = min(2, len(data) - 1)
    coeffs = np.polyfit(data[:, 1], data[:, 0], degree)
    pred = np.polyval(coeffs, data[:, 1])
    ss_res = np.sum((data[:, 0] - pred) ** 2)
    ss_tot = np.sum((data[:, 0] - data[:, 0].mean()) ** 2)
    r2 = float(1 - ss_res / ss_tot) if ss_tot > 0 else 1.0

    coeffs_list = [float(c) for c in coeffs]

    def value_to_turbidity(v):
        val = float(np.polyval(coeffs, v))
        return max(0.0, round(val, 2))

    return value_to_turbidity, coeffs_list, round(r2, 4)


def fit_all_models():
    """Fits all 4 models on current calibration datasets and returns models and summary metadata."""
    intensity_to_turbidity, params_I, r2_I = fit_intensity_model(calibration_data["intensity"])
    diameter_to_turbidity, coeffs_D, r2_D = fit_geometry_model(calibration_data["diameter"])
    a_to_turbidity, coeffs_A, r2_A = fit_geometry_model(calibration_data["major_2a"])
    b_to_turbidity, coeffs_B, r2_B = fit_geometry_model(calibration_data["minor_2b"])

    models = {
        "intensity": intensity_to_turbidity,
        "diameter": diameter_to_turbidity,
        "major_2a": a_to_turbidity,
        "minor_2b": b_to_turbidity,
    }

    summary = {
        "intensity": {
            "model_type": "Exponential (I = a * e^(b*T))",
            "params": params_I,
            "equation": f"I = {params_I['a']:.2f} * e^({params_I['b']:.4f} * T)",
            "r2": r2_I,
        },
        "diameter": {
            "model_type": "Polynomial (Quadratic)",
            "coefficients": coeffs_D,
            "equation": f"T = {coeffs_D[0]:.6f}*D² + {coeffs_D[1]:.4f}*D + {coeffs_D[2]:.2f}" if len(coeffs_D) == 3 else f"T = {coeffs_D[0]:.4f}*D + {coeffs_D[1]:.2f}",
            "r2": r2_D,
        },
        "major_2a": {
            "model_type": "Polynomial (Quadratic)",
            "coefficients": coeffs_A,
            "equation": f"T = {coeffs_A[0]:.6f}*2a² + {coeffs_A[1]:.4f}*2a + {coeffs_A[2]:.2f}" if len(coeffs_A) == 3 else f"T = {coeffs_A[0]:.4f}*2a + {coeffs_A[1]:.2f}",
            "r2": r2_A,
        },
        "minor_2b": {
            "model_type": "Polynomial (Quadratic)",
            "coefficients": coeffs_B,
            "equation": f"T = {coeffs_B[0]:.6f}*2b² + {coeffs_B[1]:.4f}*2b + {coeffs_B[2]:.2f}" if len(coeffs_B) == 3 else f"T = {coeffs_B[0]:.4f}*2b + {coeffs_B[1]:.2f}",
            "r2": r2_B,
        },
    }

    return models, summary
