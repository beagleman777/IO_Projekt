import streamlit as st
import logic

st.header("Punkt Kontrolny")
if 'auth_step' not in st.session_state:
    st.session_state.auth_step = 1
if 'scanned_user' not in st.session_state:
    st.session_state.scanned_user = None
if 'scanned_qr_code' not in st.session_state:
    st.session_state.scanned_qr_code = None
if st.session_state.auth_step == 2:
    if st.button("Anuluj / Inna osoba"):
        st.session_state.auth_step = 1
        st.session_state.scanned_user = None
        st.session_state.scanned_qr_code = None
        st.rerun()
if st.session_state.auth_step == 1:
    st.info("KROK 1/2: Zeskanuj QR przepustki")
    qr_cam = st.camera_input("Kamera QR", key="qr_cam_step1")
    if qr_cam:
        qr_code_text = logic.decode_qr_from_image(qr_cam)
        if qr_code_text:
            is_valid, msg, user_name = logic.check_qr_validity(qr_code_text)
            if is_valid:
                st.session_state.scanned_qr_code = qr_code_text
                st.session_state.scanned_user = user_name
                st.session_state.auth_step = 2
                st.rerun()
            else:
                st.error(msg)
        else:
            st.warning("Nie wykryto kodu QR.")
elif st.session_state.auth_step == 2:
    st.success(f"Przepustka: **{st.session_state.scanned_user}**")
    st.warning("KROK 2/2: Spójrz w kamerę, aby potwierdzić tożsamość.")
    face_cam = st.camera_input("Kamera Biometryczna", key="face_cam_step2")
    if face_cam:
        qr_code = st.session_state.scanned_qr_code
        success, msg, _ = logic.verify_biometric_only(qr_code, face_cam)
        if success:
            st.balloons()
            st.success(f"{msg}")
            st.image(face_cam, width=200, caption="Zdjęcie wejściowe")
            if st.button("Następna osoba"):
                st.session_state.auth_step = 1
                st.session_state.scanned_user = None
                st.rerun()
        else:
            st.error(f"ODMOWA: {msg}")