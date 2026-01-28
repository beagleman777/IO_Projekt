import streamlit as st
import logic
import pandas as pd
import database
from io import BytesIO

st.set_page_config(page_title="SecureGate 3000", layout="wide")
st.title("System Kontroli Dostępu")

ADMIN_PASSWORD = "admin"

tab1, tab2, tab3, tab4 = st.tabs(["Weryfikacja", "Rejestracja", "Logi i Incydenty", "Zarządzanie Uprawnieniami"])

with tab1:
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


with tab2:
    st.header("Panel HR - Nowy Pracownik")
    password = st.text_input("Podaj hasło administratora", type="password", key="reg_pass")
    if password == ADMIN_PASSWORD:
        reg_name = st.text_input("Imię i Nazwisko")
        reg_id = st.text_input("ID Pracownika")
        reg_photo = st.camera_input("Zdjęcie do bazy", key="reg_cam")
        if st.button("Zarejestruj pracownika"):
            if reg_name and reg_id and reg_photo:
                success, msg = logic.process_registration(reg_name, reg_id, reg_photo)
                if success:
                    st.success(msg)
                    qr_img = logic.generate_qr(reg_id)
                    st.image(qr_img, caption="Wygenerowana przepustka")
                else:
                    st.error(msg)
            else:
                st.warning("Wypełnij wszystkie pola.")
    elif password:
        st.error("Błędne hasło.")


with tab3:
    st.header("Dziennik Zdarzeń")
    if st.button("Odśwież logi"):
        logs = database.get_all_logs()
        df_data = []
        incidents = []
        
        for log in logs:
            df_data.append([log[1], log[2], log[3]])
            if log[4] is not None:
                incidents.append(log)

        st.subheader("Pełna historia wejść")
        df = pd.DataFrame(df_data, columns=["User ID", "Czas", "Status"])
        
        def highlight_status(val):
            color = 'red' if 'MISMATCH' in val or 'NOT_FOUND' in val or 'REVOKED' in val else 'green'
            return f'color: {color}'

        st.dataframe(df.style.map(highlight_status, subset=['Status']), use_container_width=True)
        if incidents:
            st.divider()
            st.subheader("Wykryte Incydenty (Dowody Zdjęciowe)")
            st.warning(f"Liczba wykrytych prób nieautoryzowanego dostępu: {len(incidents)}")
            for inc in incidents:
                with st.expander(f"{inc[2]} - Próba wejścia na ID: {inc[1]} ({inc[3]})"):
                    col_a, col_b = st.columns([1, 2])
                    with col_a:
                        if inc[4]:
                            st.image(BytesIO(inc[4]), caption="Zdjęcie z kamery w momencie odrzucenia")
                    with col_b:
                        st.write(f"**Data:** {inc[2]}")
                        st.write(f"**Status błędu:** {inc[3]}")
                        st.error("Dostęp zablokowany przez system.")


with tab4:
    st.header("Zarządzanie Pracownikami")
    password_mgmt = st.text_input("Podaj hasło administratora", type="password", key="mgmt_pass")
    if password_mgmt == ADMIN_PASSWORD:
        users = database.get_all_users()
        if users:
            df_users = pd.DataFrame(users, columns=["ID Bazy", "Nazwisko", "ID Przepustki", "Aktywny"])
            df_users["Aktywny"] = df_users["Aktywny"].apply(lambda x: True if x == 1 else False)
            st.info("Zaznacz lub odznacz 'Aktywny', aby zmienić uprawnienia.")
            edited_df = st.data_editor(
                df_users,
                column_config={
                    "Aktywny": st.column_config.CheckboxColumn(
                        "Dostęp do fabryki",
                        help="Odznacz, aby zablokować pracownika bez usuwania go z bazy",
                        default=True,
                    )
                },
                disabled=["ID Bazy", "Nazwisko", "ID Przepustki"],
                hide_index=True,
            )
            if st.button("Zapisz zmiany uprawnień"):
                for index, row in edited_df.iterrows():
                    qr_id = row["ID Przepustki"]
                    new_status = 1 if row["Aktywny"] else 0
                    database.update_user_status(qr_id, new_status)
                st.success("Uprawnienia zostały zaktualizowane!")
                st.rerun()
        else:
            st.warning("Brak zarejestrowanych pracowników.")
    elif password_mgmt:
        st.error("Błędne hasło.")
    