import easyocr
import cv2
import numpy as np

# 全域初始化，確保只載入一次模型
print("正在載入 OCR 模型...")
reader = easyocr.Reader(['ch_tra', 'en'], gpu=True)

def preprocess_image(image_bytes):
    """共用的影像前處理 (轉灰階 + CLAHE)"""
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    return clahe.apply(gray)