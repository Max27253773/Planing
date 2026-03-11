import streamlit as st
import pandas as pd
import requests
import time
import json
import re
from datetime import datetime, timedelta

# --- CONFIGURATION ---
SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/1mmPHzEY9p7ohdzvIYvwQOvqmKNa_8VQdZyl4sj1nksw/export?format=csv&gid=0"
SCRIPT_URL = "https://script.google.com/macros/s/AKfycbxhetuY5QpJEvl-Wv1BMGej5FeW6S3-WDcbS1DwcwUVT-Yt3e8th1XG9pPCcbrwPu5ITw/exec"

SIMU_CONFIG = {
    "Passerelle 1": "#B3E5FC", 
    "Machine": "#C8E6C9",      
    "Radar": "#FFF9C4",        
    "Manœuvre": "#F8BBD0"      
}

# Génération des tranches de 30 min de 06:00 à 20:00
HEURES_GRILLE = []
for h in range(6, 20):
    HEURES_GRILLE.append(f"{h:02d}:00")
    HEURES_GRILLE.append(f"{h:02d}:30")
HEURES_GRILLE.append("20:00")

st.set_page_config(page_title="Planning Naval Précis", layout="wide", page_icon="⚓")

# --- STYLE CSS (GRILLE TYPE AGENDA) ---
st.markdown("""
    <style>
    .slot-container {
        display: flex !important;
        flex-direction: row !important;
        gap: 2px !important;
        width: 100% !important;
        height: 100%;
    }
    .calendar-cell {
        flex: 1 !important;
        padding: 2px 4px !important;
        border-radius: 3px !important;
        font-size: 10px !important;
        border: 1px solid rgba(0,0,0,0.05) !important;
        color: #000 !important;
        text-align: center !important;
        font-weight: bold;
        overflow: hidden;
    }
    .time-col {
        font-size: 12px;
        font-weight: bold;
        color: #555;
        text-align: right;
        padding-right: 10px;
        border-right: 1px solid #ddd;
    }
    .grid-row {
        border-bottom: 1px solid #f0f0f0;
        height: 35px; /* Hauteur fixe pour aligner les heures */
    }
    .grid-row-hour {
        border-bottom: 2px solid #e0e0e0;
    }laus
    .day-header {
        text-align: center;
        background-color: #003366;
        color: white;
        padding: 10px;
        border-radius: 5px;
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)

# --- LOGIQUE ---
def get_monday_from_week(year, week):
    jan4 = datetime(year, 1, 4)
    start_monday = jan4 - timedelta(days=jan4.weekday())
    return start_monday + timedelta(weeks=week-1)

def est_dans_creneau(horaire_str, heure_ligne):
    """Vérifie si une réservation couvre la tranche de 30min de la ligne"""
    try:
        # Nettoyage et extraction (ex: "08h30 - 12h00")
        times = re.findall(r'(\d+)h(\d+)?|(\d+):(\d+)?', str(horaire_str))
        parts = []
        for t in times:
            h = int(t[0] or t[2])
            m = int(t[1] or t[3] or 0)
            parts.append(h + m/60)
        
        if len(parts) >= 2:
            debut_resa, fin_resa = parts[0], parts[1]
            h_ligne = int(heure_ligne.split(':')[0]) + (int(heure_ligne.split(':')[1])/60)
            # La réservation couvre cette ligne si l'heure de la ligne est entre le début et la fin
            return debut_resa <= h_ligne < fin_resa
        return False
    except: return False

@st.cache_data(ttl=2)
def load_data():
    try:
        url_force = f"{SHEET_CSV_URL}&v={time.time()}"
        data = pd.read_csv(url_force)
        data['Date_DT'] = pd.to_datetime(data['Date'], errors='coerce')
        return data.dropna(subset=['Date_DT'])
    except:
        return pd.DataFrame(columns=["Date", "Equipage", "Horaire", "Simu", "Date_DT"])

df = load_data()

# --- INTERFACE ---
st.title("⚓ Planning de Navigation Précis")

c1, c2, _ = st.columns([1, 1, 4])
with c1: annee_sel = st.selectbox("Année", [2025, 2026, 2027], index=1)
with c2: 
    curr_w = datetime.now().isocalendar()[1]
    semaine_sel = st.selectbox("Semaine", range(1, 53), index=curr_w-1)

monday = get_monday_from_week(annee_sel, semaine_sel)
week_days = [monday + timedelta(days=i) for i in range(5)]
day_names = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi"]

# En-têtes
cols = st.columns([0.6] + [1]*5)
cols[0].write("")
for i, d in enumerate(week_days):
    cols[i+1].markdown(f"<div class='day-header'>{day_names[i]}<br>{d.strftime('%d/%m')}</div>", unsafe_allow_html=True)

# Grille temporelle
for h_str in HEURES_GRILLE[:-1]: # On ne fait pas de ligne pour 20:00 (c'est la fin)
    is_full_hour = h_str.endswith(":00")
    row_class = "grid-row-hour" if is_full_hour else "grid-row"
    
    row_cols = st.columns([0.6] + [1]*5)
    
    # Heure à gauche (on affiche l'heure seulement sur les piles, ou partout)
    row_cols[0].markdown(f"<div class='time-col'>{h_str if is_full_hour else '<span style=opacity:0.3>'+h_str+'</span>'}</div>", unsafe_allow_html=True)
    
    for i, d in enumerate(week_days):
        with row_cols[i+1]:
            mask = (df['Date_DT'].dt.date == d.date())
            resas_du_jour = df[mask]
            
            # On cherche les résas qui occupent cette demi-heure précise
            resas_actives = resas_du_jour[resas_du_jour['Horaire'].apply(lambda x: est_dans_creneau(x, h_str))]
            
            if not resas_actives.empty:
                html = f'<div class="slot-container">'
                for _, r in resas_actives.iterrows():
                    color = SIMU_CONFIG.get(r['Simu'], "#EEEEEE")
                    # On n'affiche le texte que sur la première ligne du créneau pour ne pas surcharger
                    match = re.search(r'(\d+)[h:]?(\d+)?', str(r['Horaire']))
                    label = f"<b>{r['Equipage']}</b>" if match and f"{int(match.group(1)):02d}:{int(match.group(2) or 0):02d}" == h_str else ""
                    
                    html += f'<div class="calendar-cell" style="background-color: {color};">{label}</div>'
                html += '</div>'
                st.markdown(html, unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="{row_class}" style="height:35px;"></div>', unsafe_allow_html=True)
