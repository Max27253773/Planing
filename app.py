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

# --- STYLE PERSONNALISÉ ---
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

st.title("✈️ Dashboard Simulateur")

# --- LOGIQUE DE CALCUL ---
def extraire_heures_precises(horaire_str):
    try:
        blocs = re.findall(r'(\d+)[h:]?(\d+)?', str(horaire_str))
        if len(blocs) >= 2:
            h1, m1 = int(blocs[0][0]), int(blocs[0][1]) if blocs[0][1] else 0
            h2, m2 = int(blocs[1][0]), int(blocs[1][1]) if blocs[1][1] else 0
            debut = (h1 * 60) + m1
            fin = (h2 * 60) + m2
            return round(abs(fin - debut) / 60, 2)
        nombres = re.findall(r'\d+', str(horaire_str))
        return float(nombres[0]) if len(nombres) == 1 else 4.0
    except: return 4.0

# --- CHARGEMENT ---
@st.cache_data(ttl=2)
def load_data():
    try:
        url_force = f"{SHEET_CSV_URL}&v={time.time()}"
        data = pd.read_csv(url_force)
        data['Date_DT'] = pd.to_datetime(data['Date'], errors='coerce')
        data['Annee'] = data['Date_DT'].dt.year.fillna(0).astype(int)
        data['Mois'] = data['Date_DT'].dt.strftime('%m - %b')
        data['Heures'] = data['Horaire'].apply(extraire_heures_precises)
        return data
    except: return pd.DataFrame(columns=["Date", "Equipage", "Horaire", "Simu", "Annee", "Heures"])

df = load_data()

menu = st.sidebar.selectbox("Navigation", ["📅 Planning", "📊 Statistiques Visuelles", "🔐 Admin"])

# --- 1. PLANNING VISUEL ---
if menu == "📅 Planning":
    st.subheader("Séances à venir")
    if df.empty: st.info("Aucun vol prévu.")
    else:
        df_sorted = df.sort_values(by='Date_DT', ascending=True)
        for _, row in df_sorted.iterrows():
            d_fmt = row['Date_DT'].strftime('%d %B %Y') if pd.notnull(row['Date_DT']) else str(row['Date'])
            with st.container():
                col_a, col_b, col_c = st.columns([1, 2, 1])
                col_a.write(f"**{d_fmt}**")
                col_b.info(f"👨‍✈️ {row['Equipage']} | ⏰ {row['Horaire']}")
                col_c.success(f"🖥️ {row['Simu']}")
                st.divider()

# --- 2. STATISTIQUES VISUELLES ---
elif menu == "📊 Statistiques Visuelles":
    if df.empty: st.info("Pas de données.")
    else:
        # Filtre Année simple
        annees = sorted(df[df['Annee'] > 0]['Annee'].unique(), reverse=True)
        sel_annee = st.selectbox("Sélectionner l'année", annees)
        df_an = df[df['Annee'] == sel_annee]

        # --- KEY METRICS ---
        st.write(f"### 🎯 Bilan {sel_annee}")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Heures", f"{round(df_an['Heures'].sum(), 1)}h")
        m2.metric("Moyenne / Vol", f"{round(df_an['Heures'].mean(), 1)}h")
        m3.metric("Équipages", df_an['Equipage'].nunique())
        m4.metric("Séances", len(df_an))

        st.divider()

        # --- GRAPHIQUES ---
        col_left, col_right = st.columns(2)
        
        with col_left:
            st.write("#### 🥧 Répartition par Équipage")
            # Graphique Donut (Heures cumulées)
            pie_data = df_an.groupby('Equipage')['Heures'].sum()
            st.bar_chart(pie_data) # Streamlit native bar chart est très propre
            
        with col_right:
            st.write("#### 📅 Activité Mensuelle")
            # Graphique de l'évolution par mois
            monthly_data = df_an.groupby('Mois')['Heures'].sum()
            st.line_chart(monthly_data)

        st.write("#### 🏆 Classement des Équipages (Heures)")
        # Un classement horizontal visuel
        st.dataframe(
            df_an.groupby('Equipage')['Heures'].sum().sort_values(ascending=False),
            use_container_width=True
        )

# --- 3. ADMINISTRATION ---
elif menu == "🔐 Admin":
    pwd = st.sidebar.text_input("Code", type="password")
    if pwd == "1234":
        t1, t2, t3 = st.tabs(["Ajouter", "Modifier", "Supprimer"])
        with t1:
            with st.form("add"):
                d, e, h = st.date_input("Date"), st.text_input("Equipage"), st.text_input("Horaire (ex: 13h30-17h)")
                s = st.selectbox("Simu", ["SIM 1", "SIM 2", "SIM 3"])
                if st.form_submit_button("Valider"):
                    requests.post(SCRIPT_URL, data=json.dumps({"action":"add","date":str(d),"equipage":e,"horaire":h,"simu":s}))
                    st.success("Ajouté !")
                    st.cache_data.clear()
        
        with t2:
            if not df.empty:
                df['label'] = df['Date'].astype(str) + " | " + df['Equipage']
                sel = st.selectbox("Séance", df['label'].tolist())
                idx = df[df['label'] == sel].index[0]
                row = df.loc[idx]
                with st.form("edit"):
                    nd, ne, nh = st.date_input("Date", pd.to_datetime(row['Date'])), st.text_input("Equipage", row['Equipage']), st.text_input("Horaire", row['Horaire'])
                    ns = st.selectbox("Simu", ["SIM 1", "SIM 2", "SIM 3"], index=["SIM 1", "SIM 2", "SIM 3"].index(row['Simu']))
                    if st.form_submit_button("Modifier"):
                        requests.post(SCRIPT_URL, data=json.dumps({"action":"edit","row_index":int(idx),"new_date":str(nd),"new_equipage":ne,"new_horaire":nh,"new_simu":ns}))
                        st.cache_data.clear()
        
        with t3:
            if not df.empty:
                df['label_del'] = df['Date'].astype(str) + " | " + df['Equipage']
                sel_d = st.selectbox("Supprimer", df['label_del'].tolist())
                idx_d = df[df['label_del'] == sel_d].index[0]
                if st.checkbox("Confirmer la suppression"):
                    if st.button("🗑️ Supprimer"):
                        requests.post(SCRIPT_URL, data=json.dumps({"action":"delete","row_index":int(idx_d)}))
                        st.cache_data.clear()
                        st.rerun()
