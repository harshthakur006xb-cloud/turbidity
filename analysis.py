import cv2
import numpy as np

def analyze_image_array(image: np.ndarray) -> dict | None:
    """
    Performs shape-agnostic laser turbidity image analysis on an OpenCV BGR image array.
    Returns metric dictionary or None if no valid red spot contour is found.
    """
    if image is None or image.size == 0:
        return None

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

    # 1. Red spot detection in HSV
    lower_red1 = np.array([0, 80, 30])
    upper_red1 = np.array([10, 255, 255])
    lower_red2 = np.array([170, 80, 30])
    upper_red2 = np.array([180, 255, 255])

    red_mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
    red_mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
    color_mask = cv2.bitwise_or(red_mask1, red_mask2)

    # 2. Preprocessing: Median blur + Otsu thresholding
    gray_blur = cv2.medianBlur(gray, 5)
    _, thresh = cv2.threshold(gray_blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    final_mask = cv2.bitwise_and(thresh, color_mask)

    # 3. Noise cleanup: MORPH_OPEN (3x3, 1 iter) then MORPH_CLOSE (3x3, 2 iter)
    kernel = np.ones((3, 3), np.uint8)
    final_mask = cv2.morphologyEx(final_mask, cv2.MORPH_OPEN, kernel, iterations=1)
    final_mask = cv2.morphologyEx(final_mask, cv2.MORPH_CLOSE, kernel, iterations=2)

    # 4. Contour extraction (CHAIN_APPROX_NONE keeps all boundary points)
    contours, _ = cv2.findContours(final_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    if not contours:
        return None

    # Select topmost contour by minimum bounding box y-coordinate
    top_contour, min_y = None, float("inf")
    for c in contours:
        x, y, w, h = cv2.boundingRect(c)
        if y < min_y:
            min_y, top_contour = y, c
    cnt = top_contour

    area = cv2.contourArea(cnt)
    perimeter = cv2.arcLength(cnt, True)
    if area < 20:
        return None

    # 5. Shape-agnostic metrics
    M = cv2.moments(cnt)
    if M["m00"] == 0:
        return None
    cx, cy = float(M["m10"] / M["m00"]), float(M["m01"] / M["m00"])
    
    pts = cnt.reshape(-1, 2).astype(np.float64)
    radii = np.sqrt((pts[:, 0] - cx) ** 2 + (pts[:, 1] - cy) ** 2)
    mean_radius = float(radii.mean())
    radius_std = float(radii.std())
    irregularity = float(radius_std / mean_radius) if mean_radius > 0 else 0.0
    circularity = float(4 * np.pi * area / (perimeter ** 2)) if perimeter > 0 else 0.0
    equivalent_diameter = float(2 * np.sqrt(area / np.pi))

    # 6. Shape fit (for visual comparison)
    annotated = image.copy()
    mask = np.zeros(gray.shape, dtype=np.uint8)

    if len(cnt) >= 5:
        ellipse = cv2.fitEllipse(cnt)
        (ex, ey), (d1, d2), angle = ellipse
        major, minor = max(d1, d2), min(d1, d2)
        shape = "Ellipse"
        cv2.drawContours(mask, [cnt], -1, 255, -1)
        cv2.ellipse(annotated, ellipse, (0, 255, 0), 2)  # Green fitted ellipse
    else:
        (ex, ey), radius = cv2.minEnclosingCircle(cnt)
        major = minor = 2 * radius
        shape = "Circle"
        cv2.drawContours(mask, [cnt], -1, 255, -1)
        cv2.circle(annotated, (int(ex), int(ey)), int(radius), (255, 0, 0), 2)  # Blue fitted circle

    # True irregular contour outline in yellow
    cv2.drawContours(annotated, [cnt], -1, (0, 255, 255), 2)
    # Centroid in red
    cv2.circle(annotated, (int(cx), int(cy)), 4, (0, 0, 255), -1)

    # 7. Intensity calculated from true contour mask
    red_channel = image[:, :, 2]
    mask_pixels = red_channel[mask == 255]
    if len(mask_pixels) > 0:
        intensity = float(np.mean(mask_pixels))
    else:
        intensity = 0.0
    log_intensity = float(np.log(intensity + 1))

    return {
        "shape": shape,
        "major": float(major),
        "minor": float(minor),
        "equivalent_diameter": float(equivalent_diameter),
        "mean_radius": float(mean_radius),
        "radius_std": float(radius_std),
        "irregularity": float(irregularity),
        "circularity": float(circularity),
        "area": float(area),
        "perimeter": float(perimeter),
        "centroid": [cx, cy],
        "intensity": float(intensity),
        "log_intensity": float(log_intensity),
        "annotated_image": annotated,
    }
