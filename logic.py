import numpy as np
import cv2
from io import BytesIO
import qrcode
import database
import streamlit as st

try:
    import face_recognition
    BIOMETRICS_AVAILABLE = True
except ImportError:
    BIOMETRICS_AVAILABLE = False
    print("WARNING: Running in DEV mode (No biometrics).")


def _load_image(image_file):
    try:
        image_file.seek(0)
        img = face_recognition.load_image_file(image_file)
        if len(img.shape) == 3 and img.shape[2] == 4:
            img = img[:, :, :3]
        return img
    except Exception:
        return None


def _get_bytes(image_file):
    image_file.seek(0)
    data = image_file.read()
    image_file.seek(0)
    return data


def generate_qr(user_id):
    qr = qrcode.make(user_id)
    buf = BytesIO()
    qr.save(buf)
    return buf


def decode_qr_from_image(image_file):
    file_bytes = np.asarray(bytearray(image_file.read()), dtype=np.uint8)
    img = cv2.imdecode(file_bytes, 1)
    image_file.seek(0)
    if img is None: return None
    detector = cv2.QRCodeDetector()
    data, _, _ = detector.detectAndDecode(img)
    return data


def process_registration(name, user_id, image_file):
    try:
        if not BIOMETRICS_AVAILABLE:
            return database.add_user(name, user_id, np.zeros(128).tobytes()), "DEV: Zarejestrowano (bez biometrii)."

        image = _load_image(image_file)
        if image is None: 
            return False, "Błąd pliku."

        encodings = face_recognition.face_encodings(image)
        if not encodings: 
            return False, "Nie wykryto twarzy."
        
        if database.add_user(name, user_id, encodings[0].tobytes()):
            return True, "Zarejestrowano pomyślnie."
        return False, "ID zajęte."
    except Exception as e:
        return False, str(e)


def verify_access(scanned_qr_id, current_face_image_file):
    img_bytes = _get_bytes(current_face_image_file)
    user_data = database.get_user_by_qr(scanned_qr_id)
    if not user_data:
        database.log_access_attempt(scanned_qr_id, "USER_NOT_FOUND", img_bytes)
        return False, "Nieznany QR.", None
    
    blob, name, active = user_data
    if not active:
        database.log_access_attempt(scanned_qr_id, "ACCESS_REVOKED", img_bytes)
        return False, "Zablokowany.", name
    
    if not BIOMETRICS_AVAILABLE:
        database.log_access_attempt(scanned_qr_id, "DEV_SKIP")
        return True, f"Witaj {name} (DEV)", name

    try:
        curr_img = _load_image(current_face_image_file)
        curr_enc = face_recognition.face_encodings(curr_img)
        if not curr_enc:
            database.log_access_attempt(scanned_qr_id, "NO_FACE", img_bytes)
            return False, "Brak twarzy.", name
        
        saved_enc = np.frombuffer(blob, dtype=np.float64)
        match = face_recognition.compare_faces([saved_enc], curr_enc[0], tolerance=0.5)
        if match[0]:
            database.log_access_attempt(scanned_qr_id, "SUCCESS")
            return True, f"Witaj, {name}!", name
        else:
            database.log_access_attempt(scanned_qr_id, "MISMATCH", img_bytes)
            return False, "Twarz niezgodna!", name
    except Exception as e:
        return False, f"Err: {str(e)}", name
    