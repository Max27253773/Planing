import streamlit as st
import pandas as pd
import requests
import time
import re
import json
from datetime import datetime, timedelta

# --- CONFIGURATION ---
SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/1mmPHzEY9p7ohdzvIYvwQOvqmKNa_8VQdZyl4sj1nksw/export?format=csv&gid=0"
# URL mise à jour avec la tienne
SCRIPT_URL = "https://script.google.com/macros/s/AKfycbxhetuY5QpJEvl-Wv1BMGej5FeW6S3-WDcbS1DwcwUVT-Yt3e8th1XG9pPCcbrwPu5ITw/exec"
ADMIN_PASSWORD = "1234" 

SIMU_CONFIG = {
    "Passerelle 1": "#B3E5FC", 
    "Machine": "#C8E6C9",      
    "Radar": "#FFF9C4",        
    "Manœuvre": "#F8BBD0"      
}

QUARTS_HEURES = [f"{h:02d}:{m}" for h in range(6, 21) for m in ["00", "15", "30", "45"]]

st.set_page_config(page_title="⚓ Planning Naval", layout="wide")

# --- STYLE CSS ---
st.markdown("""
    <style>
    .slot-container { display: flex !important; flex-direction: row !important; gap: 2px !important; width: 100% !important; height: 100%; }
    .calendar-cell { 
        flex: 1 !important; padding: 2px !important; border-radius: 2px !important; 
        font-size: 11px !important; border: 1px solid rgba(0,0,0,0.1) !important; 
        color: #000 !important; text-align: center !important; font-weight: bold; 
        min-height: 25px; display: flex; align-items: center; justify-content: center;
    }
    .time-col { font-size: 12px; font-weight: bold; color: #003366; text-align: right; padding-right: 10px; border-right: 2px solid #003366; }
    .grid-line-hour { border-bottom: 2px solid #ccc; height: 28px; }
    .grid-line-min { border-bottom: 1px dashed #eee; height: 28px; }
    .day-header { text-align: center; background-color: #003366; color: white; padding: 8px; border-radius: 4px; font-weight: bold; margin-bottom: 5px; }
    </style>
    """, unsafe_allow_html=True)

# --- FONCTION DE PARSING ---
def est_dans_quart_heure(horaire_str, quart_str):
    try:
        nums = re.findall(r'(\d+)', str(horaire_str))
        if len(nums) >= 4:
            debut, fin = int(nums[0]) + int(nums[1])/60, int(nums[2]) + int(nums[3])/60
        elif len(nums) == 2:
            debut, fin = float(nums[0]), float(nums[1])
        else: return False
        h_q, m_q = map(int, quart_str.split(':'))
        return debut <= (h_q + m_q/60) < fin
    except: return False

@st.cache_data(ttl=2)
def load_data():
    try:
        url = f"{SHEET_CSV_URL}&v={time.time()}"
        data = pd.read_csv(url)
        data['Date_DT'] = pd.to_datetime(data['Date'], dayfirst=True, errors='coerce')
        return data.dropna(subset=['Date_DT', 'Horaire'])
    except: return pd.DataFrame()

df = load_data()

# --- NAVIGATION ---
menu = st.sidebar.radio("MENU", ["📅 Planning Hebdo", "📊 Statistiques", "🔐 Administration"])

# --- 1. PLANNING ---
if menu == "📅 Planning Hebdo":
    st.title("⚓ Planning des Simulateurs")
    c1, c2, _ = st.columns([1, 1, 4])
    with c1: annee_sel = st.selectbox("Année", [2025, 2026, 2027], index=1)
    with c2: semaine_sel = st.selectbox("Semaine", range(1, 54), index=datetime.now().isocalendar()[1]-1)

    jan4 = datetime(annee_sel, 1, 4)
    monday = (jan4 - timedelta(days=jan4.weekday())) + timedelta(weeks=semaine_sel-1)
    week_days = [monday + timedelta(days=i) for i in range(5)]

    cols = st.columns([0.6] + [1]*5)
    for i, d in enumerate(week_days):
        cols[i+1].markdown(f"<div class='day-header'>{d.strftime('%A')}<br>{d.strftime('%d/%m')}</div>", unsafe_allow_html=True)

    for q in QUARTS_HEURES:
        row_cols = st.columns([0.6] + [1]*5)
        is_pile = q.endswith(":00")
        row_cols[0].markdown(f"<div class='time-col'>{q if is_pile else ''}</div>", unsafe_allow_html=True)
        for i, d in enumerate(week_days):
            with row_cols[i+1]:
                resas = df[(df['Date_DT'].dt.date == d.date()) & (df['Horaire'].apply(lambda x: est_dans_quart_heure(x, q)))]
                if not resas.empty:
                    html = '<div class="slot-container">'
                    for _, r in resas.iterrows():
                        color = SIMU_CONFIG.get(str(r['Simu']).strip(), "#EEEEEE")
                        nums = re.findall(r'(\d+)', str(r['Horaire']))
                        h_start = f"{int(nums[0]):02d}:{int(nums[1] if len(nums)>1 else 0):02d}"
                        label = f"{r['Equipage']}" if h_start == q else ""
                        html += f'<div class="calendar-cell" style="background-color: {color};" title="{r["Simu"]}">{label}</div>'
                    st.markdown(html + '</div>', unsafe_allow_html=True)
                else:
                    st.markdown(f"<div class='{'grid-line-hour' if is_pile else 'grid-line-min'}'></div>", unsafe_allow_html=True)

# --- 2. STATISTIQUES ---
elif menu == "📊 Statistiques":
    st.title("📊 Statistiques d'Utilisation")
    if not df.empty:
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Répartition par Simulateur")
            st.bar_chart(df['Simu'].value_counts())
        with col2:
            st.subheader("Top 10 Équipages")
            st.bar_chart(df['Equipage'].value_counts().head(10))
        st.divider()
        st.subheader("📋 Liste des réservations")
        st.dataframe(df.drop(columns=['Date_DT']), use_container_width=True)

# --- 3. ADMINISTRATION ---
elif menu == "🔐 Administration":
    st.title("⚙️ Administration")
    pwd = st.sidebar.text_input("Mot de passe", type="password")
    
    if pwd == ADMIN_PASSWORD:
        tab1, tab2, tab3 = st.tabs(["➕ Ajouter", "📝 Modifier", "🗑️ Supprimer"])
        
        with tab1:
            with st.form("form_add", clear_on_submit=True):
                d = st.date_input("Date")
                eq = st.text_input("Équipage")
                hr = st.text_input("Horaire (08h00 - 12h00)")
                sm = st.selectbox("Simu", list(SIMU_CONFIG.keys()))
                if st.form_submit_button("Ajouter"):
                    requests.post(SCRIPT_URL, data=json.dumps({"action": "add", "date": d.strftime("%d/%m/%Y"), "equipage": eq, "horaire": hr, "simu": sm}))
                    st.success("Ajouté !"); time.sleep(1); st.rerun()

        with tab2:
            if not df.empty:
                idx_mod = st.selectbox("Sélectionner pour modifier", df.index, format_func=lambda x: f"{df.loc[x, 'Date']} - {df.loc[x, 'Equipage']}")
                val_simu = str(df.loc[idx_mod, 'Simu']).strip()
                list_simus = list(SIMU_CONFIG.keys())
                default_idx = list_simus.index(val_simu) if val_simu in list_simus else 0

                with st.form("form_edit"):
                    ed = st.date_input("Date", df.loc[idx_mod, 'Date_DT'])
                    ee = st.text_input("Équipage", df.loc[idx_mod, 'Equipage'])
                    eh = st.text_input("Horaire", df.loc[idx_mod, 'Horaire'])
                    es = st.selectbox("Simu", list_simus, index=default_idx)
                    if st.form_submit_button("Mettre à jour"):
                        # row = index + 2 (header + base 0)
                        requests.post(SCRIPT_URL, data=json.dumps({"action": "update", "row": int(idx_mod)+2, "date": ed.strftime("%d/%m/%Y"), "equipage": ee, "horaire": eh, "simu": es}))
                        st.success("Mis à jour !"); time.sleep(1); st.rerun()

        with tab3:
            if not df.empty:
                target = st.selectbox("Ligne à supprimer", df.index, format_func=lambda x: f"{df.loc[x, 'Date']} - {df.loc[x, 'Equipage']}")
                
                # Double vérification simplifiée
                if st.button("❌ Supprimer la sélection"):
                    st.session_state['confirm_del'] = True
                
                if st.session_state.get('confirm_del'):
                    st.warning(f"Confirmer la suppression de : {df.loc[target, 'Equipage']} ?")
                    if st.button("✅ CONFIRMER DÉFINITIVEMENT"):
                        requests.post(SCRIPT_URL, data=json.dumps({"action": "delete", "row": int(target)+2}))
                        st.session_state['confirm_del'] = False
                        st.success("Supprimé !")
                        time.sleep(1)
                        st.rerun()
    else:
        st.error("Entrez le mot de passe 1234 pour continuer.")
