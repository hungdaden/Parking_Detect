import cv2
import numpy as np
import math

def extract_value(img_original):
    """
    Extract the brightness/value channel from HSV space.
    This works better than cv2.cvtColor(..., cv2.COLOR_BGR2GRAY) for license plate contrast.
    """
    img_hsv = cv2.cvtColor(img_original, cv2.COLOR_BGR2HSV)
    _, _, img_v = cv2.split(img_hsv)
    return img_v

def maximize_contrast(img_gray):
    """
    Enhances contrast using Top Hat and Black Hat morphological operations.
    """
    structuring_element = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    
    img_top_hat = cv2.morphologyEx(img_gray, cv2.MORPH_TOPHAT, structuring_element, iterations=10)
    img_black_hat = cv2.morphologyEx(img_gray, cv2.MORPH_BLACKHAT, structuring_element, iterations=10)
    
    img_grayscale_plus_top_hat = cv2.add(img_gray, img_top_hat)
    img_grayscale_plus_top_hat_minus_black_hat = cv2.subtract(img_grayscale_plus_top_hat, img_black_hat)
    
    return img_grayscale_plus_top_hat_minus_black_hat

def preprocess_image(img_original):
    """
    Preprocess image to binary representation to find contours.
    """
    img_gray = extract_value(img_original)
    img_contrast = maximize_contrast(img_gray)
    img_blurred = cv2.GaussianBlur(img_contrast, (5, 5), 0)
    
    img_thresh = cv2.adaptiveThreshold(
        img_blurred, 255.0, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV, 19, 9
    )
    return img_gray, img_thresh

def detect_and_align_plate(crop_img):
    """
    Detects the license plate contour inside crop_img, aligns it (rotates to straight),
    and crops it out. If detection fails, returns the original crop_img.
    """
    try:
        h, w = crop_img.shape[:2]
        img_gray, img_thresh = preprocess_image(crop_img)
        
        canny_image = cv2.Canny(img_thresh, 250, 255)
        kernel = np.ones((3, 3), np.uint8)
        dilated_image = cv2.dilate(canny_image, kernel, iterations=1)
        
        contours, _ = cv2.findContours(dilated_image, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        contours = sorted(contours, key=cv2.contourArea, reverse=True)[:10]
        
        plate_contour = None
        for c in contours:
            peri = cv2.arcLength(c, True)
            approx = cv2.approxPolyDP(c, 0.06 * peri, True)
            if len(approx) == 4:
                _, _, cw, ch = cv2.boundingRect(approx)
                if cw > 40 and ch > 12:
                    aspect_ratio = cw / float(ch)
                    if 1.0 <= aspect_ratio <= 6.0:
                        plate_contour = approx
                        break
        
        if plate_contour is not None:
            points = plate_contour.reshape(4, 2)
            sorted_by_y = sorted(points, key=lambda x: x[1], reverse=True)
            bottom_points = sorted_by_y[:2]
            bottom_points = sorted(bottom_points, key=lambda x: x[0])
            p1, p2 = bottom_points[0], bottom_points[1]
            
            dy = int(p2[1] - p1[1])
            dx = int(p2[0] - p1[0])
            
            angle = math.atan2(dy, dx) * (180.0 / math.pi)
            
            if abs(angle) < 45:
                mask = np.zeros(img_gray.shape, np.uint8)
                cv2.drawContours(mask, [plate_contour], 0, 255, -1)
                
                y_indices, x_indices = np.where(mask == 255)
                if len(y_indices) > 0 and len(x_indices) > 0:
                    ymin, ymax = np.min(y_indices), np.max(y_indices)
                    xmin, xmax = np.min(x_indices), np.max(x_indices)
                    
                    padding = 4
                    ymin = max(0, ymin - padding)
                    ymax = min(h - 1, ymax + padding)
                    xmin = max(0, xmin - padding)
                    xmax = min(w - 1, xmax + padding)
                    
                    roi = crop_img[ymin:ymax, xmin:xmax]
                    roi_h, roi_w = roi.shape[:2]
                    center = (roi_w / 2.0, roi_h / 2.0)
                    
                    rotation_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
                    rotated_roi = cv2.warpAffine(roi, rotation_matrix, (roi_w, roi_h), flags=cv2.INTER_CUBIC)
                    return rotated_roi
                    
    except Exception as e:
        print("Error during plate alignment:", e)
        
    return crop_img

def preprocess_license_plate(crop_img):
    """
    Pipeline:
    1. Plate boundary localization & rotation alignment.
    2. Convert to grayscale.
    3. Resize up if small to help EasyOCR detect characters.
    4. CLAHE local contrast enhancement.
    5. Bilateral filter to reduce noise while preserving edges.
    """
    aligned = detect_and_align_plate(crop_img)
    
    if len(aligned.shape) == 3:
        gray = cv2.cvtColor(aligned, cv2.COLOR_BGR2GRAY)
    else:
        gray = aligned.copy()
        
    gh, gw = gray.shape[:2]
    target_w = 400
    if gw > 0 and gw < target_w:
        scale = target_w / float(gw)
        gray = cv2.resize(gray, (0, 0), fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
        
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    
    denoised = cv2.bilateralFilter(enhanced, 7, 50, 50)
    
    return denoised
