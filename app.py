import streamlit as st
import pandas as pd
import requests

# --- CONFIGURATION ---
SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/1mmPHzEY9p7ohdzvIYvwQOvqmKNa_8VQdZyl4sj1nksw/export?format=csv&gid=0"
SCRIPT_URL = "https://script.google.com/macros/s/AKfycbxhetuY5QpJEvl-Wv1BMGej5FeW6S3-WDcbS1DwcwUVT-Yt3e8th1XG9pPCcbrwPu5ITw/exec"

st.set_page_config(page_title="Planning Simu", layout="wide")
st.title("✈️ Planning Équipages")

# Lecture des données
@st.cache_data(ttl=10)
def load_data():
    try:
        data = pd.read_csv(SHEET_CSV_URL)
        data['Date'] = pd.to_datetime(data['Date'], errors='coerce')
        return data
    except:
        return pd.DataFrame(columns=["Date", "Equipage", "Horaire", "Simu"])

df = load_data()

# Barre latérale pour la navigation
menu = st.sidebar.selectbox("Menu", ["Consulter le Planning", "Administration 🔐"])

if menu == "Consulter le Planning":
    st.subheader("Programme de la semaine")
    if df.empty:
        st.info("Aucune séance de prévue.")
    else:
        df_view = df.sort_values(by="Date", ascending=True)
        for _, row in df_view.iterrows():
            d_str = row['Date'].strftime('%d/%m/%Y') if pd.notnull(row['Date']) else "Date ?"
            with st.expander(f"📅 {d_str} — {row['Equipage']}"):
                st.write(f"**⏰ Horaire :** {row['Horaire']}")
                st.write(f"**🖥️ Simulateur :** {row['Simu']}")

elif menu == "Administration 🔐":
    pwd = st.sidebar.text_input("Code Admin", type="password")
    if pwd == "1234":
        st.subheader("🛠️ Ajouter une séance")
        
        with st.form("mon_formulaire", clear_on_submit=True):
            d = st.date_input("Date de la séance")
            e = st.text_input("Noms de l'équipage")
            h = st.text_input("Créneau horaire (ex: 08:30 - 12:30)")
            s = st.selectbox("Choisir le Simulateur", ["SIM 1", "SIM 2", "SIM 3"])
            
            bouton_valider = st.form_submit_button("Enregistrer le planning")
            
            if bouton_valider:
                if e and h:
                    payload = {
                        "action": "add",
                        "date": str(d),
                        "equipage": e,
                        "horaire": h,
                        "simu": s
                    }
                    try:
                        r = requests.post(SCRIPT_URL, json=payload)
                        st.success("✅ Séance enregistrée ! Elle apparaîtra dans quelques secondes.")
                        st.cache_data.clear() 
                    except:
                        st.error("Erreur de connexion au serveur Google.")
                else:
                    st.warning("Veuillez remplir les noms et l'horaire.")
    else:
        st.info("Veuillez saisir le code dans la barre latérale.")
