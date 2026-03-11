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

st.set_page_config(page_title="⚓ Planning Naval", layout="wide")

# --- STYLE CSS (VISUEL) ---
st.markdown("""
    <style>
    .stApp { background-color: #F4F7F9; }
    .day-header { 
        text-align: center; background-color: #003366; color: white; 
        padding: 12px; border-radius: 8px 8px 0 0; font-weight: bold; font-size: 15px;
    }
    .slot-wrapper { position: relative; width: 100%; height: 46px; }
    .calendar-cell-unique { 
        position: absolute; top: 2px; left: 3px; right: 3px; z-index: 100; padding: 6px; 
        border-radius: 6px; font-size: 13px; border: 1px solid rgba(0,0,0,0.15); 
        color: #1A1A1A !important; text-align: center; font-weight: 700;
        display: flex; align-items: center; justify-content: center; overflow: hidden; 
        box-shadow: 1px 2px 4px rgba(0,0,0,0.08);
    }
    .time-col-full { font-size: 15px; font-weight: 900; color: #003366; text-align: right; padding-right: 15px; border-right: 4px solid #003366; height: 46px; display: flex; align-items: center; justify-content: flex-end; }
    .time-col-half { font-size: 12px; font-style: italic; font-weight: 400; color: #78909C; text-align: right; padding-right: 15px; border-right: 4px solid #CFD8DC; height: 46px; display: flex; align-items: center; justify-content: flex-end; }
    .grid-line-hour { border-bottom: 2px solid #B0BEC5; height: 46px; background-color: white; }
    .grid-line-min { border-bottom: 1px dashed #ECEFF1; height: 46px; background-color: white; }
    
    /* Mise en avant du bouton de téléchargement dans la sidebar */
    div.stDownloadButton > button {
        background-color: #003366 !important;
        color: white !important;
        border: 2px solid #001f3f !important;
        padding: 0.6rem 1rem !important;
        border-radius: 8px !important;
        width: 100%;
        font-weight: bold !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1) !important;
    }
    div.stDownloadButton > button:hover {
        background-color: #00509d !important;
        transform: translateY(-2px);
        box-shadow: 0 6px 8px rgba(0,0,0,0.15) !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- LOGIQUE ---
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

# --- GÉNÉRATEUR D'IMAGE ---
def generer_image_planning(df_view, week_days, simu_name):
    W, H = 1000, 1100
    img = Image.new('RGB', (W, H), color='#FFFFFF')
    draw = ImageDraw.Draw(img)
    navy, bg_simu = (0, 51, 102), SIMU_CONFIG.get(simu_name.upper(), "#B3E5FC")
    draw.rectangle([0, 0, W, 70], fill=navy)
    draw.text((W//2 - 90, 20), f"PLANNING : {simu_name}", fill='white')
    col_w, row_h = (W - 120) // 5, (H - 120) // len(QUARTS_HEURES)
    jours = ["Lun", "Mar", "Mer", "Jeu", "Ven"]
    for i, d in enumerate(week_days):
        x = 120 + i * col_w
        draw.rectangle([x, 70, x + col_w, 110], fill=(230, 230, 230), outline='gray')
        draw.text((x + 15, 85), f"{jours[i]} {d.strftime('%d/%m')}", fill='black')
    for j, q in enumerate(QUARTS_HEURES):
        y = 110 + j * row_h
        draw.text((20, y + 5), q, fill=navy)
        draw.line([120, y, W, y], fill=(220, 220, 220))
        h_act = int(q.split(':')[0]) + int(q.split(':')[1])/60
        for i, d in enumerate(week_days):
            resas = df_view[df_view['Date_DT'].dt.date == d.date()]
            for _, r in resas.iterrows():
                h_deb, h_fin = extraire_heures(r['Horaire'])
                if h_deb == h_act:
                    x_pos = 120 + i * col_w
                    y_fin = y + int((h_fin - h_deb) * 2 * row_h)
                    draw.rectangle([x_pos+3, y+3, x_pos+col_w-3, y_fin-3], fill=bg_simu, outline='black')
                    draw.text((x_pos+10, y+10), str(r['Equipage'])[:15], fill='black')
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='PNG')
    return img_byte_arr.getvalue()

# --- INTERFACE SIDEBAR ---
df = load_data()
# Changement : "Planning" au lieu de "Planning Hebdomadaire"
menu = st.sidebar.radio("MENU", ["📅 Planning", "📊 Statistiques", "🔐 Administration"])

st.sidebar.divider()
st.sidebar.subheader("Réglages")
annee_sel = st.sidebar.selectbox("Année", [2025, 2026, 2027], index=1)
semaine_sel = st.sidebar.selectbox("Semaine", range(1, 54), index=datetime.now().isocalendar()[1]-1)
simu_sel = st.sidebar.selectbox("Simulateur", list(SIMU_CONFIG.keys()))

monday = (datetime(annee_sel, 1, 4) - timedelta(days=datetime(annee_sel, 1, 4).weekday())) + timedelta(weeks=semaine_sel-1)
week_days = [monday + timedelta(days=i) for i in range(5)]
df_view = df[df['Simu'].str.strip().str.upper() == simu_sel.upper()]

# Bouton de téléchargement mis en avant dans la sidebar
st.sidebar.divider()
st.sidebar.write("💾 **Action Rapide**")
img_bin = generer_image_planning(df_view, week_days, simu_sel)
st.sidebar.download_button(
    label="📸 Télécharger le planning",
    data=img_bin,
    file_name=f"Planning_{simu_sel}_S{semaine_sel}.png",
    mime="image/png"
)

# --- CORPS DE PAGE ---
if menu == "📅 Planning":
    st.markdown(f"<h1 style='text-align: center; color: #003366;'>⚓ {simu_sel}</h1>", unsafe_allow_html=True)
    st.markdown(f"<p style='text-align: center; color: #607D8B;'>Semaine {semaine_sel} - {annee_sel}</p>", unsafe_allow_html=True)
    
    cols = st.columns([0.6] + [1]*5)
    jours_fr = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi"]
    for i, d in enumerate(week_days):
        cols[i+1].markdown(f"<div class='day-header'>{jours_fr[i]}<br><span style='font-size: 11px; font-weight: normal;'>{d.strftime('%d/%m')}</span></div>", unsafe_allow_html=True)
    
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
                        hauteur_px = int((h_fin - h_deb) * 2 * 46) - 4 
                        html_bloc += f'<div class="calendar-cell-unique" style="background-color:{color_active}; height:{hauteur_px}px;">{r["Equipage"]}</div>'
                st.markdown(f"<div class='slot-wrapper'><div class='{'grid-line-hour' if is_pile else 'grid-line-min'}'></div>{html_bloc}</div>", unsafe_allow_html=True)

elif menu == "📊 Statistiques":
    st.title("📊 Statistiques")
    if not df.empty:
        st.bar_chart(df['Simu'].value_counts())
        st.dataframe(df.drop(columns=['Date_DT']), use_container_width=True)

elif menu == "🔐 Administration":
    st.title("⚙️ Gestion des Réservations")
    pwd = st.sidebar.text_input("Mot de passe", type="password")
    if pwd == ADMIN_PASSWORD:
        tab1, tab2, tab3 = st.tabs(["➕ Ajouter", "📝 Modifier", "🗑️ Supprimer"])
        with tab1:
            with st.form("a", clear_on_submit=True):
                d = st.date_input("Date")
                eq = st.text_input("Équipage")
                hr = st.text_input("Horaire (ex: 08:30 - 12:00)")
                sm = st.selectbox("Simulateur", list(SIMU_CONFIG.keys()))
                if st.form_submit_button("VALIDER"):
                    requests.post(SCRIPT_URL, data=json.dumps({"action":"add","date":d.strftime("%d/%m/%Y"),"equipage":eq,"horaire":hr,"simu":sm}))
                    st.rerun()
        with tab2:
            if not df.empty:
                idx = st.selectbox("Sélectionner la ligne", df.index, format_func=lambda x: f"{df.loc[x,'Date']} - {df.loc[x,'Equipage']}")
                with st.form("e"):
                    ed = st.date_input("Date", value=df.loc[idx,'Date_DT'])
                    ee = st.text_input("Équipage", df.loc[idx,'Equipage'])
                    eh = st.text_input("Horaire", df.loc[idx,'Horaire'])
                    es = st.selectbox("Simu", list(SIMU_CONFIG.keys()), index=list(SIMU_CONFIG.keys()).index(str(df.loc[idx,'Simu']).strip()) if str(df.loc[idx,'Simu']).strip() in SIMU_CONFIG else 0)
                    if st.form_submit_button("MODIFIER"):
                        requests.post(SCRIPT_URL, data=json.dumps({"action":"update","row":int(idx)+2,"date":ed.strftime("%d/%m/%Y"),"equipage":ee,"horaire":eh,"simu":es}))
                        st.rerun()
        with tab3:
            if not df.empty:
                t = st.selectbox("Ligne à supprimer", df.index, format_func=lambda x: f"{df.loc[x,'Date']} - {df.loc[x,'Equipage']}")
                if st.button("❌ Supprimer définitivement"):
                    requests.post(SCRIPT_URL, data=json.dumps({"action":"delete","row":int(t)+2}))
                    st.rerun()
    else: st.info("Veuillez entrer le mot de passe dans la barre latérale.")
