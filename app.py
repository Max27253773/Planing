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
        if len(nombres) == 2: # Format "08-12"
            duree = int(nombres[1]) - int(nombres[0])
            return abs(duree)
        elif len(nombres) == 1: # Format "4h"
            return int(nombres[0])
        return 4 # Valeur par défaut si format inconnu
    except:
        return 4

@st.cache_data(ttl=2)
def load_data():
    try:
        url_force = f"{SHEET_CSV_URL}&v={time.time()}"
        data = pd.read_csv(url_force)
        data['Date_DT'] = pd.to_datetime(data['Date'], errors='coerce')
        data['Annee'] = data['Date_DT'].dt.year.fillna(0).astype(int)
        # Calcul de la colonne Heures
        data['Heures'] = data['Horaire'].apply(extraire_heures)
        return data
    except:
        return pd.DataFrame(columns=["Date", "Equipage", "Horaire", "Simu", "Annee", "Heures"])

df = load_data()

menu = st.sidebar.selectbox("Menu", ["Consulter le Planning", "Statistiques Heures 📊", "Administration 🔐"])

if menu == "Consulter le Planning":
    st.subheader("🗓️ Séances programmées")
    df_sorted = df.sort_values(by='Date_DT', ascending=True)
    for _, row in df_sorted.iterrows():
        d_fmt = row['Date_DT'].strftime('%d/%m/%Y') if pd.notnull(row['Date_DT']) else str(row['Date'])
        with st.expander(f"📅 {d_fmt} — {row['Equipage']}"):
            st.write(f"**⏰ Horaire :** {row['Horaire']} ({row['Heures']}h)")
            st.write(f"**🖥️ Simu :** {row['Simu']}")

elif menu == "Statistiques Heures 📊":
    st.subheader("📈 Bilan des heures de vol simu")
    
    if df.empty:
        st.info("Aucune donnée.")
    else:
        # Filtre par année en haut
        annees_dispo = sorted(df[df['Annee'] > 0]['Annee'].unique(), reverse=True)
        annee_sel = st.selectbox("Filtrer par année", ["Toutes"] + list(annees_dispo))
        
        df_stats = df.copy()
        if annee_sel != "Toutes":
            df_stats = df_stats[df_stats['Annee'] == annee_sel]

        # Métriques
        c1, c2 = st.columns(2)
        c1.metric("Total Heures", f"{df_stats['Heures'].sum()} h")
        c2.metric("Moyenne / Équipage", f"{round(df_stats.groupby('Equipage')['Heures'].sum().mean(), 1)} h")

        st.divider()

        # Graphique des heures par équipage
        st.write(f"### Heures effectuées par équipage ({annee_sel})")
        chart_data = df_stats.groupby('Equipage')['Heures'].sum().sort_values(ascending=False)
        st.bar_chart(chart_data)

        # Tableau croisé : Lignes = Équipages | Colonnes = Années
        st.write("### Récapitulatif Annuel Détaillé (Heures)")
        df_valid = df[df['Annee'] > 0]
        if not df_valid.empty:
            pivot_h = df_valid.pivot_table(
                index='Equipage', 
                columns='Annee', 
                values='Heures', 
                aggfunc='sum', 
                fill_value=0
            )
            # Ajout d'une colonne Total
            pivot_h['Total Cumulé'] = pivot_h.sum(axis=1)
            st.dataframe(pivot_h.style.highlight_max(axis=0, color='#2E7D32'))
        
elif menu == "Administration 🔐":
    # (Le code d'administration reste le même que le précédent)
    pwd = st.sidebar.text_input("Code Admin", type="password")
    if pwd == "1234":
        tab1, tab2, tab3 = st.tabs(["➕ Ajouter", "📝 Modifier", "🗑️ Supprimer"])
        # ... (insérer ici vos blocs tab1, tab2, tab3 du code précédent)
