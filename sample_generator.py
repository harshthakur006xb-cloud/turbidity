import cv2
import numpy as np
import base64

def generate_laser_spot_sample(target_ntu: float = 10.0, width: int = 500, height: int = 500) -> np.ndarray:
    """
    Generates a realistic synthetic laser diffraction spot image corresponding to a target NTU level.
    Lower NTU -> smaller, brighter, smoother red spot.
    Higher NTU -> larger, scattered, distorted red spot with irregular edges.
    """
    img = np.zeros((height, width, 3), dtype=np.uint8)
    
    # Ambient background noise (dark laboratory setting with slight camera sensor noise)
    noise = np.random.normal(15, 5, (height, width, 3)).astype(np.float32)
    img = np.clip(img.astype(np.float32) + noise, 0, 255).astype(np.uint8)
    
    # Center coordinates
    cx, cy = width // 2, height // 3 + 20  # Positioned upper-middle as per real laser setups
    
    # Calculate spot metrics based on target NTU
    # Equivalent diameter ranges roughly from 120 (0 NTU) to 380 (35 NTU)
    base_radius = 60 + target_ntu * 4.5
    
    # Create irregular boundary distortion using sine waves and noise
    angles = np.linspace(0, 2 * np.pi, 200, endpoint=False)
    distortion_amplitude = 5 + target_ntu * 0.4
    r_profile = base_radius + distortion_amplitude * np.sin(4 * angles) + distortion_amplitude * 0.5 * np.cos(7 * angles) + np.random.normal(0, 3, 200)
    r_profile = np.clip(r_profile, 10, min(width, height) / 2 - 10)
    
    contour_pts = []
    for a, r in zip(angles, r_profile):
        x = cx + r * np.cos(a)
        y = cy + r * np.sin(a)
        contour_pts.append([int(x), int(y)])
    contour_pts = np.array(contour_pts, dtype=np.int32)
    
    # Draw laser diffraction spot on canvas
    spot_mask = np.zeros((height, width), dtype=np.uint8)
    cv2.fillPoly(spot_mask, [contour_pts], 255)
    
    # Intensity profile (Gaussian falloff from center)
    y_grid, x_grid = np.ogrid[:height, :width]
    dist_sq = (x_grid - cx) ** 2 + (y_grid - cy) ** 2
    
    # Intensity decreases with higher NTU due to scattering loss
    peak_intensity = max(80, 240 - target_ntu * 3.5)
    sigma = base_radius * 0.7
    intensity_map = peak_intensity * np.exp(-dist_sq / (2 * sigma ** 2))
    
    # Laser speckle pattern simulation
    speckle = np.random.uniform(0.7, 1.3, (height, width))
    intensity_map = intensity_map * speckle
    
    # Apply to Red channel (in BGR, Red is channel index 2)
    red_layer = np.zeros((height, width), dtype=np.float32)
    red_layer[spot_mask == 255] = intensity_map[spot_mask == 255]
    
    # Slight green/blue leakage in core high-intensity zone
    core_mask = red_layer > 180
    green_layer = np.zeros((height, width), dtype=np.float32)
    green_layer[core_mask] = (red_layer[core_mask] - 180) * 0.4
    
    img[:, :, 2] = np.clip(img[:, :, 2].astype(np.float32) + red_layer, 0, 255).astype(np.uint8)
    img[:, :, 1] = np.clip(img[:, :, 1].astype(np.float32) + green_layer, 0, 255).astype(np.uint8)
    
    # Apply light median blur to make it realistic camera photo
    img = cv2.medianBlur(img, 3)
    return img

def get_preset_samples():
    """Returns base64 encoded test images for quick frontend testing."""
    presets = [
        {"name": "0.5 NTU (Ultra-Pure)", "ntu": 0.5, "description": "Small, concentrated red spot with crisp perimeter."},
        {"name": "3.5 NTU (Drinking Water)", "ntu": 3.5, "description": "Slightly expanded spot with minor diffraction fringe."},
        {"name": "12.0 NTU (Turbid Water)", "ntu": 12.0, "description": "Wider diffraction pattern with noticeable edge irregularity."},
        {"name": "28.0 NTU (Highly Turbid)", "ntu": 28.0, "description": "Large scattered laser halo with lower core intensity."},
    ]
    
    results = []
    for p in presets:
        img = generate_laser_spot_sample(target_ntu=p["ntu"])
        _, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 85])
        b64 = base64.b64encode(buf).decode("utf-8")
        results.append({
            **p,
            "image_b64": f"data:image/jpeg;base64,{b64}"
        })
    return results
