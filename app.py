import streamlit as st
import pandas as pd
import requests
import time
import re
import json
from datetime import datetime, timedelta

# --- CONFIGURATION (VERROUILLÉE) ---
SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/1mmPHzEY9p7ohdzvIYvwQOvqmKNa_8VQdZyl4sj1nksw/export?format=csv&gid=0"
SCRIPT_URL = "https://script.google.com/macros/s/AKfycbxhetuY5QpJEvl-Wv1BMGej5FeW6S3-WDcbS1DwcwUVT-Yt3e8th1XG9pPCcbrwPu5ITw/exec"
ADMIN_PASSWORD = "1234" 

SIMU_CONFIG = {
    "JUPITER": "#B3E5FC", "MINERVE": "#C8E6C9", "JUNON": "#FFF9C4",        
    "BACCHUS": "#F8BBD0", "MARS": "#E1BEE7", "SATURNE": "#FFCCBC",
    "CRONOS": "#D1C4E9", "NEKKAR": "#CFD8DC", "PHOBOS": "#F0F4C3",
    "PERSEE": "#B2DFDB", "SAGITTAIRE": "#FFE0B2"
}

# Précision à 30 minutes
QUARTS_HEURES = [f"{h:02d}:{m}" for h in range(6, 21) for m in ["00", "30"]]

st.set_page_config(page_title="⚓ Planning Naval", layout="wide")

# --- STYLE CSS (Optimisé pour la différenciation Heure/Demi-heure) ---
st.markdown("""
    <style>
    .slot-container { display: flex !important; flex-direction: row !important; gap: 2px !important; width: 100% !important; height: 100%; }
    .calendar-cell { 
        flex: 1 !important; padding: 4px !important; border-radius: 3px !important; 
        font-size: 12px !important; border: 1px solid rgba(0,0,0,0.1) !important; 
        color: #000 !important; text-align: center !important; font-weight: bold; 
        min-height: 40px; display: flex; align-items: center; justify-content: center;
    }
    /* Style différencié pour la colonne de temps */
    .time-col-full { font-size: 14px; font-weight: 800; color: #003366; text-align: right; padding-right: 15px; border-right: 4px solid #003366; background-color: #f0f2f6; }
    .time-col-half { font-size: 12px; font-weight: 400; color: #666; text-align: right; padding-right: 15px; border-right: 4px solid #99abc0; }
    
    /* Style différencié pour les lignes de grille */
    .grid-line-hour { border-bottom: 2px solid #b0bec5; height: 45px; background-color: rgba(0, 51, 102, 0.02); }
    .grid-line-min { border-bottom: 1px dashed #cfd8dc; height: 45px; }
    
    .day-header { text-align: center; background-color: #003366; color: white; padding: 10px; border-radius: 4px; font-weight: bold; margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- LOGIQUE INTERNE ---
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

    monday = (datetime(annee_sel, 1, 4) - timedelta(days=datetime(annee_sel, 1, 4).weekday())) + timedelta(weeks=semaine_sel-1)
    week_days = [monday + timedelta(days=i) for i in range(5)]

    cols = st.columns([0.6] + [1]*5)
    for i, d in enumerate(week_days):
        cols[i+1].markdown(f"<div class='day-header'>{d.strftime('%A')}<br>{d.strftime('%d/%m')}</div>", unsafe_allow_html=True)

    for q in QUARTS_HEURES:
        row_cols = st.columns([0.6] + [1]*5)
        is_pile = q.endswith(":00")
        
        # Application du style différencié sur la colonne heure
        time_class = "time-col-full" if is_pile else "time-col-half"
        row_cols[0].markdown(f"<div class='{time_class}'>{q}</div>", unsafe_allow_html=True)
        
        for i, d in enumerate(week_days):
            with row_cols[i+1]:
                resas = df[(df['Date_DT'].dt.date == d.date()) & (df['Horaire'].apply(lambda x: est_dans_quart_heure(x, q)))]
                if not resas.empty:
                    html = '<div class="slot-container">'
                    for _, r in resas.iterrows():
                        color = SIMU_CONFIG.get(str(r['Simu']).strip(), "#EEEEEE")
                        label = f"{r['Equipage']}"
                        html += f'<div class="calendar-cell" style="background-color: {color};" title="{r["Simu"]}">{label}</div>'
                    st.markdown(html + '</div>', unsafe_allow_html=True)
                else:
                    # Application du style différencié sur la ligne vide
                    grid_class = "grid-line-hour" if is_pile else "grid-line-min"
                    st.markdown(f"<div class='{grid_class}'></div>", unsafe_allow_html=True)

# --- 2. STATISTIQUES (VERROUILLÉES) ---
elif menu == "📊 Statistiques":
    st.title("📊 Statistiques d'Utilisation")
    if not df.empty:
        col1, col2 = st.columns(2)
        with col1: st.bar_chart(df['Simu'].value_counts())
        with col2: st.bar_chart(df['Equipage'].value_counts().head(10))
        st.divider()
        st.dataframe(df.drop(columns=['Date_DT']), use_container_width=True)

# --- 3. ADMINISTRATION (VERROUILLÉE) ---
elif menu == "🔐 Administration":
    st.title("⚙️ Administration")
    pwd = st.sidebar.text_input("Mot de passe", type="password")
    if pwd == ADMIN_PASSWORD:
        tab1, tab2, tab3 = st.tabs(["➕ Ajouter", "📝 Modifier", "🗑️ Supprimer"])
        def format_resa(idx):
            r = df.loc[idx]
            return f"{r['Date']} | {r['Horaire']} | {r['Simu']} | {r['Equipage']}"
        with tab1:
            with st.form("form_add", clear_on_submit=True):
                d, eq, hr = st.date_input("Date"), st.text_input("Équipage"), st.text_input("Horaire")
                sm = st.selectbox("Simu", list(SIMU_CONFIG.keys()))
                if st.form_submit_button("Ajouter"):
                    requests.post(SCRIPT_URL, data=json.dumps({"action":"add","date":d.strftime("%d/%m/%Y"),"equipage":eq,"horaire":hr,"simu":sm}))
                    st.success("Ajouté !"); time.sleep(1); st.rerun()
        with tab2:
            if not df.empty:
                idx = st.selectbox("Sélectionner", df.index, format_func=format_resa)
                with st.form("form_edit"):
                    ed, ee, eh = st.date_input("Date", df.loc[idx,'Date_DT']), st.text_input("Équipage", df.loc[idx,'Equipage']), st.text_input("Horaire", df.loc[idx,'Horaire'])
                    es = st.selectbox("Simu", list(SIMU_CONFIG.keys()), index=list(SIMU_CONFIG.keys()).index(str(df.loc[idx,'Simu']).strip()) if str(df.loc[idx,'Simu']).strip() in SIMU_CONFIG else 0)
                    if st.form_submit_button("Mettre à jour"):
                        requests.post(SCRIPT_URL, data=json.dumps({"action":"update","row":int(idx)+2,"date":ed.strftime("%d/%m/%Y"),"equipage":ee,"horaire":eh,"simu":es}))
                        st.success("Mis à jour !"); time.sleep(1); st.rerun()
        with tab3:
            if not df.empty:
                target = st.selectbox("Supprimer", df.index, format_func=format_resa)
                if st.button("❌ Supprimer la sélection"): st.session_state['confirm_del'] = True
                if st.session_state.get('confirm_del'):
                    st.warning(f"Confirmer suppression ?")
                    if st.button("✅ CONFIRMER"):
                        requests.post(SCRIPT_URL, data=json.dumps({"action":"delete","row":int(target)+2}))
                        st.session_state['confirm_del'] = False
                        st.success("Supprimé !"); time.sleep(1); st.rerun()
    else: st.error("Accès restreint.")
