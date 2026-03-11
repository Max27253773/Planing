import streamlit as st
import pandas as pd
import json
import os

# --- GESTION DE LA SAUVEGARDE ---
DATA_FILE = "data_planning.json"

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {"planning": [], "simus": ["SIM 1", "SIM 2"]}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

data = load_data()

# --- INTERFACE ---
st.title("✈️ Planning Simulateur Pro")

menu = st.sidebar.selectbox("Menu", ["Consulter le Planning", "Administration 🔐"])

if menu == "Consulter le Planning":
    st.subheader("Programme de la semaine")
    if not data["planning"]:
        st.info("Aucune séance de prévue pour le moment.")
    else:
        df = pd.DataFrame(data["planning"])
        # Tri par date
        df["Date"] = pd.to_datetime(df["Date"])
        df = df.sort_values("Date")
        
        for _, row in df.iterrows():
            with st.expander(f"📅 {row['Date'].strftime('%d/%m')} - {row['Equipage']}"):
                st.write(f"**Appareil :** {row['Simu']}")
                st.write(f"**Horaire :** {row['Horaire']}")

elif menu == "Administration 🔐":
    password = st.sidebar.text_input("Code Admin", type="password")
    if password == "1234": # Changez ce code !
        
        st.subheader("⚙️ Gestion des Simulateurs")
        new_sim = st.text_input("Ajouter un nouveau simulateur (ex: SIM A320)")
        if st.button("Ajouter Simu"):
            data["simus"].append(new_sim)
            save_data(data)
            st.rerun()

        st.markdown("---")
        st.subheader("📅 Ajouter une séance")
        with st.form("ajout_seance"):
            date_s = st.date_input("Date")
            eq_s = st.text_input("Noms de l'équipage")
            h_s = st.text_input("Créneau (ex: 08h00 - 12h00)")
            sim_s = st.selectbox("Choisir le simulateur", data["simus"])
            
            if st.form_submit_button("Valider l'ajout"):
                data["planning"].append({
                    "Date": str(date_s),
                    "Equipage": eq_s,
                    "Horaire": h_s,
                    "Simu": sim_s
                })
                save_data(data)
                st.success("Planning mis à jour !")
                st.rerun()
                
        st.markdown("---")
        if st.button("🗑️ Vider tout le planning"):
            data["planning"] = []
            save_data(data)
            st.rerun()
    else:
        st.warning("Veuillez entrer le code administrateur dans la barre latérale.")
