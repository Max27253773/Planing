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

H_DEBUT = 6
H_FIN = 20
HAUTEUR_HEURE = 60 

st.set_page_config(page_title="Planning Naval Précis", layout="wide", page_icon="⚓")

# --- STYLE CSS ---
st.markdown(f"""
    <style>
    .planning-container {{
        position: relative;
        height: {(H_FIN - H_DEBUT) * HAUTEUR_HEURE}px;
        border-left: 1px solid #ddd;
        background-image: linear-gradient(#eee 1px, transparent 1px);
        background-size: 100% {HAUTEUR_HEURE}px;
        background-color: #ffffff;
    }}
    .time-label {{
        height: {HAUTEUR_HEURE}px;
        display: flex;
        align-items: flex-start;
        justify-content: flex-end;
        padding-right: 10px;
        font-weight: bold;
        color: #003366;
        font-size: 13px;
        transform: translateY(-8px);
    }}
    .resa-block {{
        position: absolute;
        left: 5%;
        width: 90%;
        border-radius: 4px;
        border: 1px solid rgba(0,0,0,0.15);
        padding: 5px;
        font-size: 11px;
        font-weight: bold;
        color: #000;
        z-index: 10;
        overflow: hidden;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.1);
    }}
    .day-header {{
        text-align: center;
        background-color: #003366;
        color: white;
        padding: 10px;
        border-radius: 5px;
        margin-bottom: 5px;
    }}
    </style>
    """, unsafe_allow_html=True)

# --- FONCTION DE PARSING ULTRA-FLEXIBLE ---
def parse_horaire_precis(h_str):
    """Transforme '08h30 - 12h00' en [8.5, 12.0]"""
    try:
        # Trouve tous les nombres (heures et minutes)
        # Supporte : 08h30, 08:30, 8h, 8:30
        nums = re.findall(r'(\d+)', str(h_str))
        if len(nums) >= 4: # Format HH MM - HH MM
            start = int(nums[0]) + int(nums[1])/60
            end = int(nums[2]) + int(nums[3])/60
            return [start, end]
        elif len(nums) == 2: # Format HH - HH (ex: 08h - 12h)
            return [float(nums[0]), float(nums[1])]
        elif len(nums) == 3: # Cas mixte (ex: 08h30 - 12h)
            # On vérifie où se trouve le 'h' ou ':' pour deviner
            start = int(nums[0]) + (int(nums[1])/60 if 'h'+nums[1] in h_str or ':'+nums[1] in h_str else 0)
            end = int(nums[-1])
            return [start, end]
        return None
    except:
        return None

@st.cache_data(ttl=2)
def load_data():
    try:
        url_force = f"{SHEET_CSV_URL}&v={time.time()}"
        data = pd.read_csv(url_force)
        data['Date_DT'] = pd.to_datetime(data['Date'], errors='coerce')
        return data.dropna(subset=['Date_DT', 'Horaire'])
    except:
        return pd.DataFrame(columns=["Date", "Equipage", "Horaire", "Simu", "Date_DT"])

df = load_data()

# --- INTERFACE ---
st.title("⚓ Planning Naval Haute Précision")

# Navigation par semaine
c1, c2, _ = st.columns([1.5, 1.5, 4])
with c1: annee_sel = st.selectbox("Année", [2025, 2026, 2027], index=1)
with c2: 
    curr_w = datetime.now().isocalendar()[1]
    semaine_sel = st.selectbox("Semaine", range(1, 54), index=curr_w-1)

# Calcul des jours (Lundi-Vendredi)
jan4 = datetime(annee_sel, 1, 4)
monday = (jan4 - timedelta(days=jan4.weekday())) + timedelta(weeks=semaine_sel-1)
week_days = [monday + timedelta(days=i) for i in range(5)]

# En-têtes
cols = st.columns([0.6] + [1]*5)
for i, d in enumerate(week_days):
    cols[i+1].markdown(f"<div class='day-header'>{d.strftime('%A')}<br>{d.strftime('%d/%m')}</div>", unsafe_allow_html=True)

# Grille principale
main_grid = st.columns([0.6] + [1]*5)

# Colonne des heures
with main_grid[0]:
    for h in range(H_DEBUT, H_FIN + 1):
        st.markdown(f"<div class='time-label'>{h:02d}:00</div>", unsafe_allow_html=True)

# Colonnes des jours
for i, d in enumerate(week_days):
    with main_grid[i+1]:
        # Conteneur relatif pour les blocs
        st.markdown("<div class='planning-container'>", unsafe_allow_html=True)
        
        # Filtrage des réservations du jour
        day_resas = df[df['Date_DT'].dt.date == d.date()]
        
        for _, r in day_resas.iterrows():
            heures = parse_horaire_precis(r['Horaire'])
            if heures:
                h_start, h_end = heures[0], heures[1]
                
                # On ne dessine que si c'est dans notre plage horaire (06h-20h)
                if h_end > H_DEBUT and h_start < H_FIN:
                    # Calcul des pixels
                    top = max(0, (h_start - H_DEBUT) * HAUTEUR_HEURE)
                    height = (h_end - h_start) * HAUTEUR_HEURE
                    
                    # Ajustement si ça dépasse en bas
                    if top + height > (H_FIN - H_DEBUT) * HAUTEUR_HEURE:
                        height = ((H_FIN - H_DEBUT) * HAUTEUR_HEURE) - top
                        
                    color = SIMU_CONFIG.get(r['Simu'], "#EEEEEE")
                    
                    st.markdown(f"""
                        <div class="resa-block" style="top: {top}px; height: {height}px; background-color: {color};">
                            {r['Equipage']}<br>
                            <span style="font-size:9px; font-weight:normal;">{r['Simu']}</span><br>
                            <span style="font-size:8px; font-weight:normal;">{r['Horaire']}</span>
                        </div>
                    """, unsafe_allow_html=True)
        
        st.markdown("</div>", unsafe_allow_html=True)
