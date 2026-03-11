import streamlit as st
import pandas as pd
import requests
import time
import json
import re

# --- CONFIGURATION ---
SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/1mmPHzEY9p7ohdzvIYvwQOvqmKNa_8VQdZyl4sj1nksw/export?format=csv&gid=0"
SCRIPT_URL = "https://script.google.com/macros/s/AKfycbxhetuY5QpJEvl-Wv1BMGej5FeW6S3-WDcbS1DwcwUVT-Yt3e8th1XG9pPCcbrwPu5ITw/exec"

st.set_page_config(page_title="Suivi Simulateur Naval", layout="wide", page_icon="⚓")

# --- STYLE ÉPURÉ ---
st.markdown("""
    <style>
    [data-testid="stMetricValue"] { font-size: 30px; color: #003366; }
    .stMetric { background-color: #f8f9fa; padding: 20px; border-radius: 10px; border: 1px solid #dee2e6; }
    </style>
    """, unsafe_allow_html=True)

# --- CALCUL DES DURÉES ---
def extraire_heures_precises(horaire_str):
    try:
        blocs = re.findall(r'(\d+)[h:]?(\d+)?', str(horaire_str))
        if len(blocs) >= 2:
            h1, m1 = int(blocs[0][0]), int(blocs[0][1]) if blocs[0][1] else 0
            h2, m2 = int(blocs[1][0]), int(blocs[1][1]) if blocs[1][1] else 0
            debut, fin = (h1 * 60) + m1, (h2 * 60) + m2
            return round(abs(fin - debut) / 60, 2)
        nombres = re.findall(r'\d+', str(horaire_str))
        return float(nombres[0]) if len(nombres) == 1 else 4.0
    except: return 4.0

@st.cache_data(ttl=2)
def load_data():
    try:
        url_force = f"{SHEET_CSV_URL}&v={time.time()}"
        data = pd.read_csv(url_force)
        data['Date_DT'] = pd.to_datetime(data['Date'], errors='coerce')
        data['Annee'] = data['Date_DT'].dt.year.fillna(0).astype(int)
        data['Heures'] = data['Horaire'].apply(extraire_heures_precises)
        return data
    except: return pd.DataFrame(columns=["Date", "Equipage", "Horaire", "Simu", "Annee", "Heures"])

df = load_data()

menu = st.sidebar.selectbox("Navigation ⚓", ["📅 Planning", "📊 Résumé d'Activité", "🔐 Admin"])

# --- 1. PLANNING ---
if menu == "📅 Planning":
    st.header("🗓️ Planning des entraînements")
    if df.empty: st.info("Aucune séance enregistrée.")
    else:
        df_sorted = df.sort_values(by='Date_DT', ascending=False) # Plus récent en premier
        for _, row in df_sorted.iterrows():
            d_fmt = row['Date_DT'].strftime('%d/%m/%Y') if pd.notnull(row['Date_DT']) else str(row['Date'])
            st.write(f"**{d_fmt}** | {row['Equipage']} | {row['Horaire']} | {row['Simu']}")
            st.divider()

# --- 2. RÉSUMÉ CLAIR (STATISTIQUES) ---
elif menu == "📊 Résumé d'Activité":
    st.header("📊 Synthèse de l'entraînement naval")
    if df.empty: st.info("Données insuffisantes.")
    else:
        annees = sorted(df[df['Annee'] > 0]['Annee'].unique(), reverse=True)
        sel_annee = st.selectbox("Sélectionner l'année de référence", annees)
        df_an = df[df['Annee'] == sel_annee]

        # --- CHIFFRES CLÉS ---
        st.subheader(f"Indicateurs globaux - Année {sel_annee}")
        c1, c2, c3 = st.columns(3)
        c1.metric("Volume total", f"{round(df_an['Heures'].sum(), 1)} h")
        c2.metric("Nombre d'équipages", df_an['Equipage'].nunique())
        c3.metric("Séances effectuées", len(df_an))

        st.divider()

        # --- RÉPARTITION ÉQUIPAGES ---
        st.subheader("Répartition du temps d'entraînement par équipage")
        # On groupe par équipage et on fait la somme des heures
        stats_crew = df_an.groupby('Equipage')['Heures'].sum().reset_index()
        stats_crew = stats_crew.sort_values(by='Heures', ascending=False)
        
        # Graphique à barres horizontal (très lisible pour les noms d'équipages)
        st.bar_chart(data=stats_crew, x='Equipage', y='Heures', color='#003366')

        st.divider()

        # --- TABLEAU DE SYNTHÈSE ---
        st.subheader("Détail cumulé par équipage")
        # Tableau simple et propre sans fioritures
        summary_table = df_an.groupby('Equipage').agg({
            'Heures': 'sum',
            'Date': 'count'
        }).rename(columns={'Heures': 'Total Heures', 'Date': 'Nombre de Séances'})
        
        st.dataframe(summary_table.sort_values(by='Total Heures', ascending=False), use_container_width=True)

# --- 3. ADMINISTRATION ---
elif menu == "🔐 Admin":
    pwd = st.sidebar.text_input("Code", type="password")
    if pwd == "1234":
        t1, t2, t3 = st.tabs(["Ajouter", "Modifier", "Supprimer"])
        with t1:
            with st.form("add"):
                d, e, h = st.date_input("Date"), st.text_input("Equipage"), st.text_input("Horaire (ex: 08h30-12h00)")
                s = st.selectbox("Simu", ["Simu A", "Simu B", "Simu C"])
                if st.form_submit_button("Valider"):
                    requests.post(SCRIPT_URL, data=json.dumps({"action":"add","date":str(d),"equipage":e,"horaire":h,"simu":s}))
                    st.success("Enregistré")
                    st.cache_data.clear()
        
        with t2:
            if not df.empty:
                df['label'] = df['Date'].astype(str) + " - " + df['Equipage']
                sel = st.selectbox("Choisir", df['label'].tolist())
                idx = df[df['label'] == sel].index[0]
                row = df.loc[idx]
                with st.form("edit"):
                    nd, ne, nh = st.date_input("Date", pd.to_datetime(row['Date'])), st.text_input("Equipage", row['Equipage']), st.text_input("Horaire", row['Horaire'])
                    ns = st.selectbox("Simu", ["Simu A", "Simu B", "Simu C"])
                    if st.form_submit_button("Modifier"):
                        requests.post(SCRIPT_URL, data=json.dumps({"action":"edit","row_index":int(idx),"new_date":str(nd),"new_equipage":ne,"new_horaire":nh,"new_simu":ns}))
                        st.cache_data.clear()
        
        with t3:
            if not df.empty:
                df['label_del'] = df['Date'].astype(str) + " - " + df['Equipage']
                sel_d = st.selectbox("Supprimer", df['label_del'].tolist())
                idx_d = df[df['label_del'] == sel_d].index[0]
                if st.checkbox("Confirmer la suppression"):
                    if st.button("Supprimer définitivement"):
                        requests.post(SCRIPT_URL, data=json.dumps({"action":"delete","row_index":int(idx_d)}))
                        st.cache_data.clear()
                        st.rerun()
