import face_recognition
import numpy as np
import cv2
from io import BytesIO
import qrcode
import database


database.init_db()

def process_registration(name, user_id, image_file):
    """Przetwarza rejestrację: enkoduje twarz i zapisuje w bazie."""
    try:
        image = face_recognition.load_image_file(image_file)
        encodings = face_recognition.face_encodings(image)
        if not encodings:
            return False, "Nie wykryto twarzy."
            
        face_encoding = encodings[0].tobytes()
        success = database.add_user(name, user_id, face_encoding)
        if success:
            return True, "Zarejestrowano pomyślnie."
        else:
            return False, "Błąd bazy danych."
    except Exception as e:
        return False, f"Błąd przetwarzania: {str(e)}"


def generate_qr(user_id):
    """Generuje obraz QR code."""
    qr = qrcode.make(user_id)
    buf = BytesIO()
    qr.save(buf)
    return buf


def verify_access(scanned_qr_id, current_face_image_file):
    current_face_image_file.seek(0)
    image_bytes = current_face_image_file.read()
    current_face_image_file.seek(0)
    user_data = database.get_user_by_qr(scanned_qr_id)
    if not user_data:
        database.log_access_attempt(scanned_qr_id, "USER_NOT_FOUND", image_bytes)
        return False, "Nieznany identyfikator QR.", None

    saved_encoding_blob, user_name, is_active = user_data
    if not is_active:
        database.log_access_attempt(scanned_qr_id, "ACCESS_REVOKED", image_bytes)
        return False, "Pracownik ma zablokowany dostęp!", user_name

    try:
        current_image = face_recognition.load_image_file(current_face_image_file)
        current_encodings = face_recognition.face_encodings(current_image)
    except Exception:
        database.log_access_attempt(scanned_qr_id, "CAMERA_ERROR", image_bytes)
        return False, "Błąd przetwarzania obrazu.", user_name

    if len(current_encodings) == 0:
        database.log_access_attempt(scanned_qr_id, "NO_FACE_DETECTED", image_bytes)
        return False, "Nie wykryto twarzy.", user_name

    saved_encoding = np.frombuffer(saved_encoding_blob, dtype=np.float64)
    match = face_recognition.compare_faces([saved_encoding], current_encodings[0])
    
    if match[0]:
        database.log_access_attempt(scanned_qr_id, "SUCCESS")
        return True, f"Witaj, {user_name}!", user_name
    else:
        database.log_access_attempt(scanned_qr_id, "FACE_MISMATCH", image_bytes)
        return False, "Niezgodność biometryczna!", user_name


def decode_qr_from_image(image_file):
    """Wyciąga dane z obrazka QR."""
    file_bytes = np.asarray(bytearray(image_file.read()), dtype=np.uint8)
    img = cv2.imdecode(file_bytes, 1)
    detector = cv2.QRCodeDetector()
    data, _, _ = detector.detectAndDecode(img)
    # Reset pointera pliku, bo Streamlit może chcieć go użyć ponownie (lub nie)
    image_file.seek(0) 
    return data
