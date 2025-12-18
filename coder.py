import streamlit as st
import sqlite3
import face_recognition
import numpy as np
import qrcode
from io import BytesIO

conn = sqlite3.connect('access_system.db')
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS users 
             (id INTEGER PRIMARY KEY, name TEXT, face_encoding BLOB, qr_code_id TEXT)''')
conn.commit()

st.title("📝 Rejestracja Użytkownika")

name = st.text_input("Imię i Nazwisko")
user_id = st.text_input("Unikalne ID (np. PESEL lub Numer pracownika)")

uploaded_image = st.camera_input("Zrób zdjęcie profilowe")

if uploaded_image and name and user_id:
    if st.button("Zarejestruj i generuj QR"):
        image = face_recognition.load_image_file(uploaded_image)
        encodings = face_recognition.face_encodings(image)

        if len(encodings) > 0:
            face_encoding = encodings[0].tobytes()  # Zamiana na format binarny do bazy
            c.execute("INSERT INTO users (name, face_encoding, qr_code_id) VALUES (?, ?, ?)",
                      (name, face_encoding, user_id))
            conn.commit()
            qr = qrcode.make(user_id)
            buf = BytesIO()
            qr.save(buf)
            st.image(buf, caption="Twój kod QR (Zapisz go!)")
            st.success(f"Użytkownik {name} zarejestrowany!")
        else:
            st.error("Nie wykryto twarzy na zdjęciu. Spróbuj ponownie.")