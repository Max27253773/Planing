import streamlit as st
import pandas as pd
import requests
import time
import re
import json
from datetime import datetime, timedelta

# --- CONFIGURATION ---
SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/1mmPHzEY9p7ohdzvIYvwQOvqmKNa_8VQdZyl4sj1nksw/export?format=csv&gid=0"
SCRIPT_URL = "https://script.google.com/macros/s/AKfycbxhetuY5QpJEvl-Wv1BMGej5FeW6S3-WDcbS1DwcwUVT-Yt3e8th1XG9pPCcbrwPu5ITw/exec"
ADMIN_PASSWORD = "1234" 

SIMU_CONFIG = {
    "JUPITER": "#B3E5FC", "MINERVE": "#C8E6C9", "JUNON": "#FFF9C4",        
    "BACCHUS": "#F8BBD0", "MARS": "#E1BEE7", "SATURNE": "#FFCCBC",
    "CRONOS": "#D1C4E9", "NEKKAR": "#CFD8DC", "PHOBOS": "#F0F4C3",
    "PERSEE": "#B2DFDB", "SAGITTAIRE": "#FFE0B2"
}

QUARTS_HEURES = [f"{h:02d}:{m}" for h in range(6, 21) for m in ["00", "30"]]

st.set_page_config(page_title="⚓ Planning Naval", layout="wide")

# --- CSS RADICAL (Tableau Propre) ---
st.markdown("""
    <style>
    .planning-table { width: 100%; border-collapse: collapse; font-family: sans-serif; table-layout: fixed; }
    .planning-table th { background-color: #003366; color: white; padding: 10px; border: 1px solid #ddd; }
    .planning-table td { height: 40px; border-left: 1px solid #ddd; border-right: 1px solid #ddd; vertical-align: middle; padding: 0 5px; position: relative; }
    
    /* Lignes : Pleine pour :00, Pointillée pour :30 */
    .row-00 { border-bottom: 2px solid #333 !important; }
    .row-30 { border-bottom: 1px dashed #bbb !important; }
    
    /* Colonne Heure */
    .col-time { width: 80px; text-align: right; padding-right: 15px !important; border: none !important; }
    .txt-00 { font-weight: 900; font-size: 15px; color: #003366; }
    .txt-30 { font-style: italic; font-size: 13px; color: #666; }
    
    /* Conteneur de réservation */
    .res-flex { display: flex; gap: 4px; height: 32px; align-items: center; justify-content: center; }
    .res-item { flex: 1; height: 100%; display: flex; align-items: center; justify-content: center; 
                font-size: 11px; font-weight: bold; border-radius: 4px; border: 1px solid rgba(0,0,0,0.1); color: black !important; }
    </style>
    """, unsafe_allow_html=True)

# --- LOGIQUE ---
@st.cache_data(ttl=2)
def load_data():
    try:
        url = f"{SHEET_CSV_URL}&v={time.time()}"
        data = pd.read_csv(url)
        data['Date_DT'] = pd.to_datetime(data['Date'], dayfirst=True, errors='coerce')
        return data.dropna(subset=['Date_DT', 'Horaire'])
    except: return pd.DataFrame()

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

df = load_data()

# --- INTERFACE ---
menu = st.sidebar.radio("MENU", ["📅 Planning Hebdomadaire", "🔐 Administration"])

if menu == "📅 Planning Hebdomadaire":
    st.title("⚓ Planning des Simulateurs")
    
    c1, c2, _ = st.columns([1, 1, 4])
    with c1: annee_sel = st.selectbox("Année", [2025, 2026, 2027], index=1)
    with c2: semaine_sel = st.selectbox("Semaine", range(1, 54), index=datetime.now().isocalendar()[1]-1)

    monday = (datetime(annee_sel, 1, 4) - timedelta(days=datetime(annee_sel, 1, 4).weekday())) + timedelta(weeks=semaine_sel-1)
    week_days = [monday + timedelta(days=i) for i in range(5)]
    jours_fr = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi"]

    # Construction du tableau HTML
    html = '<table class="planning-table"><thead><tr><th style="width:80px">Heure</th>'
    for i, d in enumerate(week_days):
        html += f'<th>{jours_fr[i]}<br>{d.strftime("%d/%m")}</th>'
    html += '</tr></thead><tbody>'

    for q in QUARTS_HEURES:
        is_pile = q.endswith(":00")
        row_class = "row-00" if is_pile else "row-30"
        txt_class = "txt-00" if is_pile else "txt-30"
        
        html += f'<tr><td class="col-time {row_class} {txt_class}">{q}</td>'
        
        for d in week_days:
            resas = df[(df['Date_DT'].dt.date == d.date()) & (df['Horaire'].apply(lambda x: est_dans_quart_heure(x, q)))]
            html += f'<td class="{row_class}">'
            
            if not resas.empty:
                html += '<div class="res-flex">'
                for _, r in resas.iterrows():
                    color = SIMU_CONFIG.get(str(r['Simu']).strip().upper(), "#EEEEEE")
                    html += f'<div class="res-item" style="background-color:{color}" title="{r["Simu"]}">{r["Equipage"]}</div>'
                html += '</div>'
            
            html += '</td>'
        html += '</tr>'
    
    html += '</tbody></table>'
    st.markdown(html, unsafe_allow_html=True)

# --- ADMIN ---
elif menu == "🔐 Administration":
    st.title("⚙️ Administration")
    pwd = st.sidebar.text_input("Mot de passe", type="password")
    if pwd == ADMIN_PASSWORD:
        with st.form("add"):
            d = st.date_input("Date", format="DD/MM/YYYY")
            eq = st.text_input("Équipage")
            hr = st.text_input("Horaire (ex: 10:00 - 12:00)")
            sm = st.selectbox("Simulateur", list(SIMU_CONFIG.keys()))
            if st.form_submit_button("Ajouter"):
                requests.post(SCRIPT_URL, data=json.dumps({"action":"add","date":d.strftime("%d/%m/%Y"),"equipage":eq,"horaire":hr,"simu":sm}))
                st.success("Ajouté !"); time.sleep(1); st.rerun()
