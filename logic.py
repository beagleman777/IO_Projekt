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
    if img is None: 
        return None
    detector = cv2.QRCodeDetector()
    data, _, _ = detector.detectAndDecode(img)
    return data


def check_qr_validity(scanned_qr_id):
    user_data = database.get_user_by_qr(scanned_qr_id)
    if not user_data:
        return False, "Nieznany kod QR. Spróbuj ponownie.", None
    _, user_name, is_active = user_data
    if not is_active:
        return False, "Dostęp zablokowany przez administratora.", user_name
    return True, "Kod poprawny.", user_name


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


def verify_biometric_only(scanned_qr_id, current_face_image_file):
    current_face_image_file.seek(0)
    image_bytes = current_face_image_file.read()
    current_face_image_file.seek(0)
    user_data = database.get_user_by_qr(scanned_qr_id)
    if not user_data:
        return False, "Błąd sesji. Zeskanuj QR ponownie.", None
        
    saved_encoding_blob, user_name, _ = user_data
    if not BIOMETRICS_AVAILABLE:
        database.log_access_attempt(scanned_qr_id, "SUCCESS_DEV")
        return True, f"Weryfikacja pozytywna (DEV)", user_name

    try:
        try:
            current_face_image_file.seek(0)
            current_image = face_recognition.load_image_file(current_face_image_file)
        except:
            return False, "Błąd pliku obrazu.", user_name

        current_encodings = face_recognition.face_encodings(current_image)
        
        if not current_encodings:
            database.log_access_attempt(scanned_qr_id, "NO_FACE_DETECTED", image_bytes)
            return False, "Nie wykryto twarzy. Stań prosto.", user_name
            
        saved_encoding = np.frombuffer(saved_encoding_blob, dtype=np.float64)
        match = face_recognition.compare_faces([saved_encoding], current_encodings[0], tolerance=0.5)
        
        if match[0]:
            database.log_access_attempt(scanned_qr_id, "SUCCESS")
            return True, f"Dostęp przyznany!", user_name
        else:
            database.log_access_attempt(scanned_qr_id, "FACE_MISMATCH", image_bytes)
            return False, "Twarz niezgodna z kodem QR!", user_name
            
    except Exception as e:
        return False, f"Błąd systemu: {str(e)}", user_name
    