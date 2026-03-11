import streamlit as st
import pandas as pd
import requests
import time
import re
import json
import io
from datetime import datetime, timedelta
from PIL import Image, ImageDraw, ImageFont

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

QUARTS_HEURES = [f"{h:02d}:{m}" for h in range(6, 21) for m in ["00", "30"]]

# Configuration de la page avec un layout large
st.set_page_config(page_title="⚓ Planning Naval", layout="wide")

# --- STYLE CSS (RETOUR À LA STABILITÉ) ---
st.markdown("""
    <style>
    /* Fond gris de l'application sans casser le moteur Streamlit */
    .stApp {
        background-color: #F4F7F9;
    }
    
    /* On garde les styles du planning */
    .slot-wrapper { position: relative; width: 100%; height: 45px; }
    .calendar-cell-unique { 
        position: absolute; top: 2px; left: 2px; right: 2px;
        z-index: 100; padding: 4px; border-radius: 4px; 
        font-size: 13px; border: 1px solid rgba(0,0,0,0.2); 
        color: #000 !important; text-align: center; font-weight: bold;
        display: flex; align-items: center; justify-content: center;
        overflow: hidden; box-shadow: 2px 2px 5px rgba(0,0,0,0.1);
    }
    .time-col-full { font-size: 14px; font-weight: 900; color: #003366; text-align: right; padding-right: 15px; border-right: 4px solid #003366; height: 45px; display: flex; align-items: center; justify-content: flex-end; }
    .time-col-half { font-size: 13px; font-style: italic; font-weight: 400; color: #555; text-align: right; padding-right: 15px; border-right: 4px solid #99abc0; height: 45px; display: flex; align-items: center; justify-content: flex-end; }
    .grid-line-hour { border-bottom: 2px solid #888; height: 45px; }
    .grid-line-min { border-bottom: 1px dashed #ccc; height: 45px; }
    .day-header { text-align: center; background-color: #003366; color: white; padding: 10px; border-radius: 4px; font-weight: bold; margin-bottom: 10px; }
    
    /* Bouton Télécharger Planning */
    div.stDownloadButton > button {
        background-color: #003366 !important;
        color: white !important;
        width: 100%;
        border-radius: 8px;
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)

# --- LOGIQUE DONNÉES ---
def extraire_heures(horaire_str):
    try:
        nums = re.findall(r'(\d+)', str(horaire_str))
        if len(nums) >= 4:
            h_deb = int(nums[0]) + int(nums[1])/60
            h_fin = int(nums[2]) + int(nums[3])/60
            return h_deb, h_fin
    except: pass
    return None, None

@st.cache_data(ttl=2)
def load_data():
    try:
        url = f"{SHEET_CSV_URL}&v={time.time()}"
        data = pd.read_csv(url)
        data['Date_DT'] = pd.to_datetime(data['Date'], dayfirst=True, errors='coerce')
        return data.dropna(subset=['Date_DT', 'Horaire'])
    except: return pd.DataFrame()

def generer_image_planning(df_view, week_days, simu_name):
    W, H = 1000, 1200
    img = Image.new('RGB', (W, H), color='white')
    draw = ImageDraw.Draw(img)
    navy, gray = (0, 51, 102), (200, 200, 200)
    bg_simu = SIMU_CONFIG.get(simu_name.upper(), "#B3E5FC")
    
    draw.rectangle([0, 0, W, 80], fill=navy)
    draw.text((W//2 - 100, 25), f"PLANNING : {simu_name}", fill='white')

    col_w, row_h = (W - 100) // 5, (H - 120) // len(QUARTS_HEURES)
    jours_fr = ["Lun", "Mar", "Mer", "Jeu", "Ven"]
    
    for i, d in enumerate(week_days):
        x = 100 + i * col_w
        draw.rectangle([x, 80, x + col_w, 120], outline='black', fill=(240, 240, 240))
        draw.text((x + 10, 90), f"{jours_fr[i]} {d.strftime('%d/%m')}", fill='black')

    for j, q in enumerate(QUARTS_HEURES):
        y = 120 + j * row_h
        draw.text((10, y + 5), q, fill=navy)
        draw.line([100, y, W, y], fill=gray)
        h_act = int(q.split(':')[0]) + int(q.split(':')[1])/60
        for i, d in enumerate(week_days):
            resas = df_view[df_view['Date_DT'].dt.date == d.date()]
            for _, r in resas.iterrows():
                h_deb, h_fin = extraire_heures(r['Horaire'])
                if h_deb == h_act:
                    x_pos = 100 + i * col_w
                    y_fin = y + int((h_fin - h_deb) * 2 * row_h)
                    draw.rectangle([x_pos+2, y+2, x_pos+col_w-2, y_fin-2], fill=bg_simu, outline='black')
                    draw.text((x_pos+5, y+10), str(r['Equipage'])[:15], fill='black')

    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='PNG')
    return img_byte_arr.getvalue()

# --- INTERFACE ---
df = load_data()
menu = st.sidebar.radio("MENU", ["📅 Planning", "📊 Statistiques", "🔐 Administration"])

st.sidebar.divider()
annee_sel = st.sidebar.selectbox("Année", [2025, 2026, 2027], index=1)
semaine_sel = st.sidebar.selectbox("Semaine", range(1, 54), index=datetime.now().isocalendar()[1]-1)
simu_sel = st.sidebar.selectbox("Simulateur", list(SIMU_CONFIG.keys()))

monday = (datetime(annee_sel, 1, 4) - timedelta(days=datetime(annee_sel, 1, 4).weekday())) + timedelta(weeks=semaine_sel-1)
week_days = [monday + timedelta(days=i) for i in range(5)]
df_view = df[df['Simu'].str.strip().str.upper() == simu_sel.upper()]

st.sidebar.divider()
img_bin = generer_image_planning(df_view, week_days, simu_sel)
st.sidebar.download_button(
    label="📸 Télécharger Planning",
    data=img_bin,
    file_name=f"Planning_{simu_sel}_S{semaine_sel}.png",
    mime="image/png"
)

if menu == "📅 Planning":
    st.title(f"⚓ Planning : {simu_sel}")
    cols = st.columns([0.6] + [1]*5)
    jours_fr = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi"]
    for i, d in enumerate(week_days):
        cols[i+1].markdown(f"<div class='day-header'>{jours_fr[i]}<br>{d.strftime('%d/%m')}</div>", unsafe_allow_html=True)

    color_active = SIMU_CONFIG.get(simu_sel, "#EEEEEE")
    for q in QUARTS_HEURES:
        if q == "20:30": continue
        row_cols = st.columns([0.6] + [1]*5)
        is_pile = q.endswith(":00")
        h_act = int(q.split(':')[0]) + int(q.split(':')[1])/60
        t_class = "time-col-full" if is_pile else "time-col-half"
        row_cols[0].markdown(f"<div class='{t_class}'>{q}</div>", unsafe_allow_html=True)
        
        for i, d in enumerate(week_days):
            with row_cols[i+1]:
                resas = df_view[df_view['Date_DT'].dt.date == d.date()]
                html_bloc = ""
                for _, r in resas.iterrows():
                    h_deb, h_fin = extraire_heures(r['Horaire'])
                    if h_deb == h_act:
                        hauteur_px = int((h_fin - h_deb) * 2 * 45) - 4 
                        html_bloc += f'<div class="calendar-cell-unique" style="background-color:{color_active}; height:{hauteur_px}px;">{r["Equipage"]}</div>'
                st.markdown(f"<div class='slot-wrapper'><div class='{'grid-line-hour' if is_pile else 'grid-line-min'}'></div>{html_bloc}</div>", unsafe_allow_html=True)

elif menu == "📊 Statistiques":
    st.title("📊 Statistiques")
    if not df.empty:
        st.bar_chart(df['Simu'].value_counts())

elif menu == "🔐 Administration":
    st.title("⚙️ Gestion")
    pwd = st.sidebar.text_input("Mot de passe", type="password")
    if pwd == ADMIN_PASSWORD:
        tab1, tab2, tab3 = st.tabs(["➕ Ajouter", "📝 Modifier", "🗑️ Supprimer"])
        def format_resa(idx):
            r = df.loc[idx]
            return f"{r['Date']} | {r['Horaire']} | {r['Simu']} | {r['Equipage']}"
            
        with tab1:
            with st.form("a", clear_on_submit=True):
                d = st.date_input("Date")
                eq = st.text_input("Equipage")
                hr = st.text_input("Horaire")
                sm = st.selectbox("Simu", list(SIMU_CONFIG.keys()))
                if st.form_submit_button("Ajouter"):
                    requests.post(SCRIPT_URL, data=json.dumps({"action":"add","date":d.strftime("%d/%m/%Y"),"equipage":eq,"horaire":hr,"simu":sm}))
                    st.rerun()
        with tab2:
            if not df.empty:
                idx = st.selectbox("Editer", df.index, format_func=format_resa)
                with st.form("e"):
                    ed = st.date_input("Date", value=df.loc[idx,'Date_DT'])
                    ee = st.text_input("Equipage", df.loc[idx,'Equipage'])
                    eh = st.text_input("Horaire", df.loc[idx,'Horaire'])
                    current_simu = str(df.loc[idx,'Simu']).strip().upper()
                    simu_list = list(SIMU_CONFIG.keys())
                    default_idx = simu_list.index(current_simu) if current_simu in simu_list else 0
                    es = st.selectbox("Simu", simu_list, index=default_idx)
                    if st.form_submit_button("Modifier"):
                        requests.post(SCRIPT_URL, data=json.dumps({"action":"update","row":int(idx)+2,"date":ed.strftime("%d/%m/%Y"),"equipage":ee,"horaire":eh,"simu":es}))
                        st.rerun()
        with tab3:
            if not df.empty:
                t = st.selectbox("Supprimer", df.index, format_func=format_resa)
                if st.button("❌ Confirmer la suppression"):
                    requests.post(SCRIPT_URL, data=json.dumps({"action":"delete","row":int(t)+2}))
                    st.rerun()
