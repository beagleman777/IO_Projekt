import streamlit as st
import sqlite3
import face_recognition
import numpy as np
import cv2
from datetime import datetime

st.title("🔐 Punkt Weryfikacji")


def log_event(user_id, status):
    conn = sqlite3.connect('access_system.db')
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS logs (user_id TEXT, timestamp TEXT, status TEXT)")
    c.execute("INSERT INTO logs VALUES (?, ?, ?)",
              (user_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), status))
    conn.commit()


st.header("Krok 1: Zeskanuj kod QR")
qr_image = st.camera_input("Pokaż kod QR do kamery", key="qr_scanner")

scanned_id = None
if qr_image:
    file_bytes = np.asarray(bytearray(qr_image.read()), dtype=np.uint8)
    img = cv2.imdecode(file_bytes, 1)
    detector = cv2.QRCodeDetector()
    data, _, _ = detector.detectAndDecode(img)
    if data:
        scanned_id = data
        st.info(f"Wykryto ID: {scanned_id}")
    else:
        st.warning("Nie wykryto kodu QR na zdjęciu.")

if scanned_id:
    st.header("Krok 2: Weryfikacja twarzy")
    face_image = st.camera_input("Zrób zdjęcie twarzy", key="face_scanner")

    if face_image:
        # Pobranie wzorca z bazy
        conn = sqlite3.connect('access_system.db')
        c = conn.cursor()
        c.execute("SELECT face_encoding, name FROM users WHERE qr_code_id = ?", (scanned_id,))
        result = c.fetchone()

        if result:
            saved_encoding = np.frombuffer(result[0], dtype=np.float64)
            current_image = face_recognition.load_image_file(face_image)
            current_encodings = face_recognition.face_encodings(current_image)

            if len(current_encodings) > 0:
                match = face_recognition.compare_faces([saved_encoding], current_encodings[0])

                if match[0]:
                    st.success(f"Dostęp przyznany! Witaj {result[1]}")
                    log_event(scanned_id, "SUCCESS")
                else:
                    st.error("Twarz nie zgadza się z kodem QR!")
                    log_event(scanned_id, "FAILED_FACE_MISMATCH")
            else:
                st.warning("Nie wykryto twarzy.")
        else:
            st.error("Nie znaleziono użytkownika o takim ID w bazie.")
            log_event(scanned_id, "USER_NOT_FOUND")