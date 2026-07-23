import cv2
import numpy as np
from PyQt6.QtGui import QImage, QPixmap


def generate_guidance_map_pixmap(slot_id, polygons, last_poly_status, last_raw_frame=None, last_frame=None):
    """
    Tạo QPixmap sơ đồ bãi đỗ với ô đỗ khuyến nghị (slot_id) được highlight nổi bật.
    """
    if last_raw_frame is not None:
        base_frame = last_raw_frame.copy()
    elif last_frame is not None:
        base_frame = last_frame.copy()
    else:
        base_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        base_frame[:] = (30, 25, 20)

    overlay = base_frame.copy()

    for idx, poly in enumerate(polygons):
        poly_np = np.array(poly, np.int32)
        s_id = idx + 1
        is_occ = last_poly_status[idx] if idx < len(last_poly_status) else False

        pcx = int(sum(p[0] for p in poly) / len(poly))
        pcy = int(sum(p[1] for p in poly) / len(poly))

        if s_id == slot_id:
            # HIGHLIGHT THE RECOMMENDED SLOT!
            # Bright green semi-transparent fill
            cv2.fillPoly(overlay, [poly_np], (16, 185, 129))
            # Thick glowing cyan border
            cv2.polylines(base_frame, [poly_np], True, (255, 255, 0), 4)

            # Big circle marker on slot
            cv2.circle(base_frame, (pcx, pcy), 18, (255, 255, 0), -1)
            cv2.putText(base_frame, str(s_id), (pcx - 8, pcy + 6), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)

            # Tag text banner above slot
            cv2.rectangle(base_frame, (pcx - 70, max(5, pcy - 40)), (pcx + 70, max(30, pcy - 10)), (16, 185, 129), -1)
            cv2.putText(base_frame, "Vao day", (pcx - 60, max(22, pcy - 18)), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2)
        else:
            if is_occ:
                cv2.polylines(base_frame, [poly_np], True, (0, 0, 255), 2)
                cv2.putText(base_frame, str(s_id), (pcx - 8, pcy + 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
            else:
                cv2.polylines(base_frame, [poly_np], True, (0, 255, 0), 2)
                cv2.putText(base_frame, str(s_id), (pcx - 8, pcy + 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

    alpha = 0.45
    cv2.addWeighted(overlay, alpha, base_frame, 1 - alpha, 0, base_frame)

    rgb_frame = cv2.cvtColor(base_frame, cv2.COLOR_BGR2RGB)
    fh, fw, fch = rgb_frame.shape
    qimg = QImage(bytes(rgb_frame.data), fw, fh, fch * fw, QImage.Format.Format_RGB888)
    return QPixmap.fromImage(qimg)
