import streamlit as st
import pandas as pd
import requests
import time
import re
import json
import io
from datetime import datetime, timedelta
from PIL import Image, ImageDraw, ImageFont

# --- CONFIGURATION FIXE ---
SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/1mmPHzEY9p7ohdzvIYvwQOvqmKNa_8VQdZyl4sj1nksw/export?format=csv&gid=0"
SCRIPT_URL = "https://script.google.com/macros/s/AKfycbxhetuY5QpJEvl-Wv1BMGej5FeW6S3-WDcbS1DwcwUVT-Yt3e8th1XG9pPCcbrwPu5ITw/exec"
ADMIN_PASSWORD = "1234" 

SIMU_CONFIG = {
    "JUPITER": "#1976D2", "MINERVE": "#C2185B", "JUNON": "#757575",
    "BACCHUS": "#388E3C", "MARS": "#D32F2F", "SATURNE": "#E65100",
    "CRONOS": "#A1887F", "NEKKAR": "#C5A000", "PHOBOS": "#DAA520",
    "PERSEE": "#558B2F", "SAGITTAIRE": "#4A148C"
}

# Liste arrêtée à 20:00 pile pour supprimer la ligne 20:30
QUARTS_HEURES = [f"{h:02d}:{m}" for h in range(6, 20) for m in ["00", "30"]] + ["20:00"]

st.set_page_config(page_title="⚓ Planning", layout="wide")

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

# --- INTERFACE ---
df = load_data()
menu = st.sidebar.radio("MENU", ["📅 Planning", "📊 Statistiques", "🔐 Administration"])

st.sidebar.divider()

# --- CALCUL AUTOMATIQUE DATE/SEMAINE ---
maintenant = datetime.now()
annee_actuelle = maintenant.year
semaine_actuelle = maintenant.isocalendar()[1]
jour_actuel_idx = maintenant.weekday() 

annee_sel = st.sidebar.selectbox("Année", [2025, 2026, 2027], index=1)
semaine_sel = st.sidebar.selectbox("Semaine", range(1, 54), index=semaine_actuelle - 1)
simu_sel = st.sidebar.selectbox("Simulateur", list(SIMU_CONFIG.keys()))

st.sidebar.divider()
st.sidebar.subheader("📱 Options d'affichage")
mode_vue = st.sidebar.segmented_control("Format", ["Semaine", "Jour"], default="Jour")

monday = (datetime(annee_sel, 1, 4) - timedelta(days=datetime(annee_sel, 1, 4).weekday())) + timedelta(weeks=semaine_sel-1)
week_days = [monday + timedelta(days=i) for i in range(5)]
jours_fr_liste = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi"]

current_color = SIMU_CONFIG.get(simu_sel, "#000000")
text_on_color = "#000000" if simu_sel in ["PHOBOS", "NEKKAR"] else "#FFFFFF"

# --- CSS COMPLET ---
st.markdown(f"""
    <style>
    .stApp {{ background-color: #FFFFFF !important; }}
    [data-testid="stSidebar"] {{ background-color: #E2E8F0 !important; border-right: 2px solid #000000 !important; }}
    h1 {{ font-size: 1.8rem !important; font-weight: 900 !important; color: #000000 !important; }}
    
    /* Mode Jour : Cadre ajusté pour finir à 20h00 */
    .planning-frame {{
        position: relative; width: 100%; background: #FFFFFF;
        height: 1260px; /* Hauteur exacte pour 6h-20h (14h * 90px) */
        border: 1px solid #000; margin-bottom: 30px;
        overflow: hidden;
    }}
    .hour-row-fixed {{
        position: absolute; left: 0; right: 0; height: 45px;
        display: flex; align-items: center; border-bottom: 1px dashed #CCC; box-sizing: border-box;
    }}
    
    /* Mode Semaine : Grille flexible */
    .slot-container-week {{ position: relative; width: 100%; height: 45px; box-sizing: border-box; }}
    .grid-line-hour {{ border-bottom: 2px solid #333333 !important; height: 45px; box-sizing: border-box; }}
    .grid-line-min {{ border-bottom: 1px dashed #777777 !important; height: 45px; box-sizing: border-box; }}

    .calendar-cell-unique {{ 
        position: absolute; z-index: 100; border: 2px solid #000000; 
        color: {text_on_color} !important; text-align: center; font-weight: 900; 
        display: flex; align-items: center; justify-content: center; 
        box-shadow: 2px 2px 0px rgba(0,0,0,1); box-sizing: border-box;
    }}
    
    .stButton button {{ width: 100% !important; font-weight: bold !important; }}
    </style>
    """, unsafe_allow_html=True)

df_view = df[df['Simu'].str.strip().str.upper() == simu_sel.upper()]

# --- NAVIGATION ---

if menu == "📅 Planning":
    st.markdown(f"<h1>⚓ {simu_sel}</h1>", unsafe_allow_html=True)
    
    if mode_vue == "Jour":
        choix_jour = st.sidebar.selectbox("Choisir le jour", jours_fr_liste, 
                                        index=min(jour_actuel_idx, 4) if annee_sel == annee_actuelle and semaine_sel == semaine_actuelle else 0)
        jour_idx = jours_fr_liste.index(choix_jour)
        d = week_days[jour_idx]
        
        st.markdown(f"<div style='text-align:center; background-color:{current_color}; color:{text_on_color}; padding:8px; font-weight:900; border:2px solid black; box-shadow: 2px 2px 0px black; margin-bottom:10px;'>{choix_jour} {d.strftime('%d/%m')}</div>", unsafe_allow_html=True)
        
        html_jour = '<div class="planning-frame">'
        for i, q in enumerate(QUARTS_HEURES):
            if i >= 29: break # Sécurité pour ne pas dépasser 20h00 (28 créneaux de 30min de 6h à 20h)
            top = i * 45
            style = "border-bottom: 2px solid #333;" if q.endswith(":00") else ""
            html_jour += f'<div class="hour-row-fixed" style="top:{top}px; {style}"><div style="width:60px; text-align:right; padding-right:8px; font-weight:900; border-right:3px solid {current_color}; background:#F0F2F6; height:100%; display:flex; align-items:center; justify-content:flex-end;">{q}</div></div>'
        
        resas = df_view[df_view['Date_DT'].dt.date == d.date()]
        for _, r in resas.iterrows():
            h_deb, h_fin = extraire_heures(r['Horaire'])
            if h_deb is not None:
                top_pos = int((h_deb - 6) * 2 * 45)
                hauteur = int((h_fin - h_deb) * 2 * 45) - 2
                html_jour += f'<div class="calendar-cell-unique" style="top:{top_pos}px; height:{hauteur}px; left:65px; right:5px; background-color:{current_color}; font-size:14px;">{r["Equipage"]}</div>'
        html_jour += '</div>'
        st.markdown(html_jour, unsafe_allow_html=True)

    else:
        # MODE SEMAINE
        cols = st.columns([0.6] + [1]*5)
        for i, d in enumerate(week_days):
            cols[i+1].markdown(f"<div style='text-align:center; background-color:{current_color}; color:{text_on_color}; padding:8px; font-weight:900; border:2px solid black; box-shadow: 2px 2px 0px black;'>{jours_fr_liste[i]}<br>{d.strftime('%d/%m')}</div>", unsafe_allow_html=True)

        for q in QUARTS_HEURES:
            row_cols = st.columns([0.6] + [1]*5)
            is_pile = q.endswith(":00")
            h_act = int(q.split(':')[0]) + int(q.split(':')[1])/60
            border_style = f"border-right:4px solid {current_color};" if is_pile else "border-right:1px solid #CCC;"
            row_cols[0].markdown(f"<div style='height:45px; display:flex; align-items:center; justify-content:flex-end; padding-right:10px; font-weight:900; {border_style}'>{q}</div>", unsafe_allow_html=True)
            
            for i, d in enumerate(week_days):
                with row_cols[i+1]:
                    resas = df_view[df_view['Date_DT'].dt.date == d.date()]
                    html_bloc = ""
                    for _, r in resas.iterrows():
                        h_deb, h_fin = extraire_heures(r['Horaire'])
                        if h_deb == h_act:
                            hauteur_px = int((h_fin - h_deb) * 2 * 45) - 2
                            html_bloc += f'<div class="calendar-cell-unique" style="top:1px; left:2px; right:2px; height:{hauteur_px}px; background-color:{current_color}; font-size:10px;">{r["Equipage"]}</div>'
                    grid_class = 'grid-line-hour' if is_pile else 'grid-line-min'
                    st.markdown(f"<div class='slot-container-week'><div class='{grid_class}'></div>{html_bloc}</div>", unsafe_allow_html=True)

elif menu == "📊 Statistiques":
    st.markdown("<h1>📊 Statistiques</h1>", unsafe_allow_html=True)
    if not df.empty:
        def calcul_duree(horaire_str):
            h_deb, h_fin = extraire_heures(horaire_str)
            return (h_fin - h_deb) if h_deb is not None else 0
        df['Duree_H'] = df['Horaire'].apply(calcul_duree)
        df['Mois'] = df['Date_DT'].dt.strftime('%m - %B')
        df['Annee'] = df['Date_DT'].dt.year

        st.subheader("📁 Volume horaire par équipage (Mensuel)")
        mois_dispo = sorted(df['Mois'].unique())
        mois_sel = st.selectbox("Mois", mois_dispo, index=len(mois_dispo)-1)
        stats_equipage = df[df['Mois'] == mois_sel].groupby('Equipage')['Duree_H'].sum().reset_index()
        st.dataframe(stats_equipage.sort_values(by='Duree_H', ascending=False), use_container_width=True, hide_index=True)

        st.divider()
        st.subheader("🖥️ Utilisation des simulateurs (Annuel)")
        stats_simu = df[df['Annee'] == annee_sel].groupby('Simu')['Duree_H'].sum().sort_values(ascending=False)
        st.bar_chart(stats_simu)
    else:
        st.warning("Aucune donnée.")

elif menu == "🔐 Administration":
    st.markdown("<h1>⚙️ Gestion des Réservations</h1>", unsafe_allow_html=True)
    st.sidebar.subheader("🔒 Accès Restreint")
    pwd = st.sidebar.text_input("Saisir le mot de passe", type="password")
    
    if pwd == ADMIN_PASSWORD:
        tab1, tab2, tab3 = st.tabs(["➕ Ajouter", "📝 Modifier", "🗑️ Supprimer"])
        def format_resa(idx):
            r = df.loc[idx]
            return f"{r['Date']} | {r['Horaire']} | {r['Simu']} | {r['Equipage']}"
        
        with tab1:
            with st.form("a", clear_on_submit=True):
                d = st.date_input("Date", value=datetime.now())
                eq = st.text_input("Equipage")
                hr = st.text_input("Horaire (ex: 08:00 - 10:00)")
                sm = st.selectbox("Simu", list(SIMU_CONFIG.keys()), index=list(SIMU_CONFIG.keys()).index(simu_sel))
                if st.form_submit_button("Ajouter"):
                    if eq and hr:
                        requests.post(SCRIPT_URL, data=json.dumps({"action":"add","date":d.strftime("%d/%m/%Y"),"equipage":eq.upper(),"horaire":hr,"simu":sm}))
                        st.success("✅ Ajouté !"), time.sleep(1), st.rerun()
        with tab2:
            if not df.empty:
                idx = st.selectbox("Sélectionner la ligne", df.index, format_func=format_resa)
                with st.form("e"):
                    ed, ee, eh = st.date_input("Date", value=df.loc[idx,'Date_DT']), st.text_input("Equipage", df.loc[idx,'Equipage']), st.text_input("Horaire", df.loc[idx,'Horaire'])
                    s_list = list(SIMU_CONFIG.keys())
                    current_s = str(df.loc[idx,'Simu']).strip().upper()
                    es = st.selectbox("Simu", s_list, index=s_list.index(current_s) if current_s in s_list else 0)
                    if st.form_submit_button("Mettre à jour"):
                        requests.post(SCRIPT_URL, data=json.dumps({"action":"update","row":int(idx)+2,"date":ed.strftime("%d/%m/%Y"),"equipage":ee.upper(),"horaire":eh,"simu":es}))
                        st.success("📝 Modifié !"), time.sleep(1), st.rerun()
        with tab3:
            if not df.empty:
                t = st.selectbox("Ligne à supprimer", df.index, format_func=format_resa)
                if st.button("❌ Supprimer définitivement", disabled=not st.checkbox("Confirmer la suppression")):
                    requests.post(SCRIPT_URL, data=json.dumps({"action":"delete","row":int(t)+2}))
                    st.success("🗑️ Supprimé !"), time.sleep(1), st.rerun()
    else:
        st.error("🔑 Entrez le mot de passe dans la barre latérale.")
