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
        df_sorted = df.sort_values(by='Date_DT', ascending=False)
        for _, row in df_sorted.iterrows():
            d_fmt = row['Date_DT'].strftime('%d/%m/%Y') if pd.notnull(row['Date_DT']) else str(row['Date'])
            st.info(f"**{d_fmt}** | {row['Equipage']} | {row['Horaire']} | {row['Simu']}")

# --- 2. RÉSUMÉ D'ACTIVITÉ (SANS CSS FORCÉ) ---
elif menu == "📊 Résumé d'Activité":
    st.header("📊 Synthèse de l'entraînement naval")
    if df.empty: st.info("Données insuffisantes.")
    else:
        annees = sorted(df[df['Annee'] > 0]['Annee'].unique(), reverse=True)
        sel_annee = st.selectbox("Sélectionner l'année", annees)
        df_an = df[df['Annee'] == sel_annee]

        # On utilise des boîtes de couleur natives pour les chiffres
        st.subheader(f"Chiffres clés - {sel_annee}")
        c1, c2, c3 = st.columns(3)
        with c1: st.success(f"**Volume total** \n### {round(df_an['Heures'].sum(), 1)} h")
        with c2: st.info(f"**Équipages** \n### {df_an['Equipage'].nunique()}")
        with c3: st.warning(f"**Séances** \n### {len(df_an)}")

        st.divider()
        st.subheader("Répartition par équipage (Heures)")
        stats_crew = df_an.groupby('Equipage')['Heures'].sum().reset_index()
        st.bar_chart(data=stats_crew.sort_values(by='Heures', ascending=False), x='Equipage', y='Heures')

        st.divider()
        st.subheader("Détail cumulé")
        summary_table = df_an.groupby('Equipage').agg({
            'Heures': 'sum',
            'Date': 'count'
        }).rename(columns={'Heures': 'Total Heures', 'Date': 'Nombre de Séances'})
        st.table(summary_table.sort_values(by='Total Heures', ascending=False))

# --- 3. ADMINISTRATION ---
elif menu == "🔐 Admin":
    pwd = st.sidebar.text_input("Code", type="password")
    if pwd == "1234":
        t1, t2, t3 = st.tabs(["Ajouter", "Modifier", "Supprimer"])
        with t1:
            with st.form("add"):
                d, e, h = st.date_input("Date"), st.text_input("Equipage"), st.text_input("Horaire")
                s = st.selectbox("Simu", ["Simu A", "Simu B", "Simu C"])
                if st.form_submit_button("Valider"):
                    requests.post(SCRIPT_URL, data=json.dumps({"action":"add","date":str(d),"equipage":e,"horaire":h,"simu":s}))
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
                        st.rerun()
        with t3:
            if not df.empty:
                df['label_del'] = df['Date'].astype(str) + " - " + df['Equipage']
                sel_d = st.selectbox("Supprimer", df['label_del'].tolist())
                idx_d = df[df['label_del'] == sel_d].index[0]
                if st.checkbox("Confirmer"):
                    if st.button("Supprimer"):
                        requests.post(SCRIPT_URL, data=json.dumps({"action":"delete","row_index":int(idx_d)}))
                        st.cache_data.clear()
                        st.rerun()
    else:
        st.info("Entrez le code admin.")
