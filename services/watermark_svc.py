from WatermarkingModule.engine import Watermarker
import numpy as np
import cv2
import base64
import os

wm = Watermarker(alpha=0.2)

def apply_watermark(file_bytes: bytes, username: str) -> str:
    nparr = np.frombuffer(file_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    temp_in  = f"in_{username}.png"
    temp_out = f"out_{username}.png"
    cv2.imwrite(temp_in, img)

    success = wm.encode(temp_in, username, temp_out)
    if not success:
        raise Exception("Erreur lors du tatouage DCT")

    with open(temp_out, "rb") as f:
        b64_result = base64.b64encode(f.read()).decode('utf-8')

    if os.path.exists(temp_in):  os.remove(temp_in)
    if os.path.exists(temp_out): os.remove(temp_out)

    return b64_result

def extract_watermark(original_bytes: bytes, watermarked_bytes: bytes) -> str:
    temp_orig = "orig_decode.png"
    temp_wm   = "wm_decode.png"

    nparr_o = np.frombuffer(original_bytes, np.uint8)
    nparr_w = np.frombuffer(watermarked_bytes, np.uint8)

    cv2.imwrite(temp_orig, cv2.imdecode(nparr_o, cv2.IMREAD_COLOR))
    cv2.imwrite(temp_wm,   cv2.imdecode(nparr_w, cv2.IMREAD_COLOR))

    result = wm.decode(temp_orig, temp_wm)

    if os.path.exists(temp_orig): os.remove(temp_orig)
    if os.path.exists(temp_wm):   os.remove(temp_wm)

    return result