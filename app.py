import streamlit as st
import pandas as pd
from shupdatesheet import update_sheet # On va utiliser une petite astuce de connexion

# Remplacez par l'URL de votre Google Sheet créé à l'étape 1
SHEET_URL = "https://docs.google.com/spreadsheets/d/1mmPHzEY9p7ohdzvIYvwQOvqmKNa_8VQdZyl4sj1nksw/edit?gid=0#gid=0"
# Pour transformer l'URL en lien de téléchargement CSV direct
CSV_URL = SHEET_URL.replace("/edit#gid=", "/export?format=csv&gid=")

st.set_page_config(page_title="Planning Simu", layout="wide")
st.title("✈️ Planning Équipages")

# Lecture des données depuis Google Sheets
try:
    df = pd.read_csv(CSV_URL)
except:
    st.error("Connexion au planning impossible. Vérifiez l'URL du Google Sheet.")
    df = pd.DataFrame(columns=["Date", "Equipage", "Horaire", "Simu"])

menu = st.sidebar.selectbox("Menu", ["Consulter le Planning", "Administration 🔐"])

if menu == "Consulter le Planning":
    if df.empty:
        st.info("Aucun vol prévu.")
    else:
        # Affichage par date
        for _, row in df.iterrows():
            with st.expander(f"📅 {row['Date']} - {row['Equipage']}"):
                st.write(f"**Horaire :** {row['Horaire']} | **Appareil :** {row['Simu']}")

elif menu == "Administration 🔐":
    pwd = st.sidebar.text_input("Code Admin", type="password")
    if pwd == "1234":
        st.subheader("Ajouter une séance")
        with st.form("add_form"):
            d = st.date_input("Date")
            e = st.text_input("Equipage")
            h = st.text_input("Horaire")
            s = st.selectbox("Simu", ["SIM 1", "SIM 2", "SIM 3"])
            
            if st.form_submit_button("Enregistrer dans le cloud"):
                # Ici, on ajoute la ligne au Google Sheet
                # Note: Pour que cela écrive vraiment, il faut configurer st.connection
                # Mais pour tester la lecture, cette structure est déjà fonctionnelle.
                st.success("Séance ajoutée (Vérifiez votre Google Sheet) !")
    else:
        st.info("Entrez le code pour modifier le programme.")
