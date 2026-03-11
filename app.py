import streamlit as st
import pandas as pd
import requests
import time
import json
import re

# --- CONFIGURATION ---
SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/1mmPHzEY9p7ohdzvIYvwQOvqmKNa_8VQdZyl4sj1nksw/export?format=csv&gid=0"
SCRIPT_URL = "https://script.google.com/macros/s/AKfycbxhetuY5QpJEvl-Wv1BMGej5FeW6S3-WDcbS1DwcwUVT-Yt3e8th1XG9pPCcbrwPu5ITw/exec"

st.set_page_config(page_title="Planning Simu Pro", layout="wide")
st.title("✈️ Suivi des Heures Simulateur")

def extraire_heures(horaire_str):
    """Calcule la durée à partir d'une chaîne type '08h-12h' ou '4h'"""
    try:
        nombres = re.findall(r'\d+', str(horaire_str))
        if len(nombres) >= 2: # Format "08-12" ou "08h12h"
            duree = int(nombres[1]) - int(nombres[0])
            return abs(duree)
        elif len(nombres) == 1: # Format "4" ou "4h"
            return int(nombres[0])
        return 4 # Valeur par défaut
    except:
        return 4

@st.cache_data(ttl=2)
def load_data():
    try:
        url_force = f"{SHEET_CSV_URL}&v={time.time()}"
        data = pd.read_csv(url_force)
        data['Date_DT'] = pd.to_datetime(data['Date'], errors='coerce')
        data['Annee'] = data['Date_DT'].dt.year.fillna(0).astype(int)
        data['Heures'] = data['Horaire'].apply(extraire_heures)
        return data
    except:
        return pd.DataFrame(columns=["Date", "Equipage", "Horaire", "Simu", "Annee", "Heures"])

df = load_data()

menu = st.sidebar.selectbox("Menu", ["Consulter le Planning", "Statistiques Heures 📊", "Administration 🔐"])

# --- VUE CONSULTATION ---
if menu == "Consulter le Planning":
    st.subheader("🗓️ Séances programmées")
    if df.empty:
        st.info("Le planning est vide.")
    else:
        df_sorted = df.sort_values(by='Date_DT', ascending=True)
        for _, row in df_sorted.iterrows():
            d_fmt = row['Date_DT'].strftime('%d/%m/%Y') if pd.notnull(row['Date_DT']) else str(row['Date'])
            with st.expander(f"📅 {d_fmt} — {row['Equipage']}"):
                st.write(f"**⏰ Horaire :** {row['Horaire']} ({row['Heures']}h)")
                st.write(f"**🖥️ Simu :** {row['Simu']}")

# --- VUE STATISTIQUES ---
elif menu == "Statistiques Heures 📊":
    st.subheader("📈 Bilan des heures par équipage")
    if df.empty:
        st.info("Aucune donnée disponible.")
    else:
        annees_dispo = sorted(df[df['Annee'] > 0]['Annee'].unique(), reverse=True)
        annee_sel = st.selectbox("Filtrer par année", ["Toutes"] + list(annees_dispo))
        
        df_stats = df.copy()
        if annee_sel != "Toutes":
            df_stats = df_stats[df_stats['Annee'] == annee_sel]

        c1, c2 = st.columns(2)
        c1.metric("Total Heures", f"{df_stats['Heures'].sum()} h")
        c2.metric("Équipages actifs", df_stats['Equipage'].nunique())

        st.write(f"### Récapitulatif Heures / Année")
        df_valid = df[df['Annee'] > 0]
        if not df_valid.empty:
            pivot_h = df_valid.pivot_table(index='Equipage', columns='Annee', values='Heures', aggfunc='sum', fill_value=0)
            pivot_h['Total Cumulé'] = pivot_h.sum(axis=1)
            st.dataframe(pivot_h.sort_values(by='Total Cumulé', ascending=False))

# --- VUE ADMINISTRATION (RÉTABLIE) ---
elif menu == "Administration 🔐":
    pwd = st.sidebar.text_input("Code Admin", type="password")
    if pwd == "1234":
        tab1, tab2, tab3 = st.tabs(["➕ Ajouter", "📝 Modifier", "🗑️ Supprimer"])

        with tab1:
            with st.form("add_form", clear_on_submit=True):
                d = st.date_input("Date")
                e = st.text_input("Equipage")
                h = st.text_input("Horaire (ex: 08-12)")
                s = st.selectbox("Simu", ["SIM 1", "SIM 2", "SIM 3"])
                if st.form_submit_button("Valider l'ajout"):
                    payload = {"action": "add", "date": str(d), "equipage": e, "horaire": h, "simu": s}
                    requests.post(SCRIPT_URL, data=json.dumps(payload))
                    st.success("✅ Ajouté !")
                    st.cache_data.clear()

        with tab2:
            if not df.empty:
                df['label_edit'] = df['Date'].astype(str) + " | " + df['Equipage'].astype(str) + " (" + df['Horaire'].astype(str) + ")"
                choix = st.selectbox("Sélectionner la séance", options=df['label_edit'].tolist())
                idx = df[df['label_edit'] == choix].index[0]
                row_sel = df.loc[idx]
                with st.form("edit_form"):
                    new_d = st.date_input("Date", value=pd.to_datetime(row_sel['Date']))
                    new_e = st.text_input("Equipage", value=row_sel['Equipage'])
                    new_h = st.text_input("Horaire", value=row_sel['Horaire'])
                    new_s = st.selectbox("Simu", ["SIM 1", "SIM 2", "SIM 3"], index=["SIM 1", "SIM 2", "SIM 3"].index(row_sel['Simu']) if row_sel['Simu'] in ["SIM 1", "SIM 2", "SIM 3"] else 0)
                    if st.form_submit_button("Enregistrer"):
                        payload = {"action": "edit", "row_index": int(idx), "new_date": str(new_d), "new_equipage": new_e, "new_horaire": new_h, "new_simu": new_s}
                        requests.post(SCRIPT_URL, data=json.dumps(payload))
                        st.success("📝 Modifié !")
                        st.cache_data.clear()

        with tab3:
            if not df.empty:
                df['label_del'] = df['Date'].astype(str) + " | " + df['Equipage'].astype(str) + " (" + df['Horaire'].astype(str) + ")"
                choix_del = st.selectbox("Séance à supprimer", options=df['label_del'].tolist())
                idx_del = df[df['label_del'] == choix_del].index[0]
                st.warning("⚠️ Attention : suppression définitive.")
                confirm = st.checkbox("Je confirme la suppression")
                if st.button("🗑️ Supprimer"):
                    if confirm:
                        payload = {"action": "delete", "row_index": int(idx_del)}
                        requests.post(SCRIPT_URL, data=json.dumps(payload))
                        st.success("Supprimé !")
                        st.cache_data.clear()
                        time.sleep(1)
                        st.rerun()
    else:
        st.info("Entrez le code admin.")
