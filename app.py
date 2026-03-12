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

QUARTS_HEURES = [f"{h:02d}:{m}" for h in range(6, 21) for m in ["00", "30"]]

st.set_page_config(page_title="⚓ Planning Naval", layout="wide")

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
jour_actuel_idx = maintenant.weekday() # 0=Lundi, 4=Vendredi

# Sélecteurs Barre Latérale
annee_sel = st.sidebar.selectbox("Année", [2025, 2026, 2027], index=1)
semaine_sel = st.sidebar.selectbox("Semaine", range(1, 54), index=semaine_actuelle - 1)
simu_sel = st.sidebar.selectbox("Simulateur", list(SIMU_CONFIG.keys()))

# --- OPTIMISATION MOBILE ---
st.sidebar.divider()
st.sidebar.subheader("📱 Options d'affichage")
mode_vue = st.sidebar.segmented_control("Format", ["Semaine", "Jour"], default="Jour")

monday = (datetime(annee_sel, 1, 4) - timedelta(days=datetime(annee_sel, 1, 4).weekday())) + timedelta(weeks=semaine_sel-1)
week_days = [monday + timedelta(days=i) for i in range(5)]

# Si mode Jour, on choisit quel jour afficher
if mode_vue == "Jour":
    choix_jour = st.sidebar.selectbox("Choisir le jour", ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi"], 
                                    index=min(jour_actuel_idx, 4) if annee_sel == annee_actuelle and semaine_sel == semaine_actuelle else 0)
    jour_idx = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi"].index(choix_jour)
    jours_a_afficher = [week_days[jour_idx]]
    colonnes_layout = [0.7, 3] # Plus de place pour le contenu
else:
    jours_a_afficher = week_days
    colonnes_layout = [0.6] + [1]*5

current_color = SIMU_CONFIG.get(simu_sel, "#000000")
text_on_color = "#000000" if simu_sel in ["PHOBOS", "NEKKAR"] else "#FFFFFF"

# --- CSS ADAPTATIF ---
st.markdown(f"""
    <style>
    .stApp {{ background-color: #FFFFFF !important; }}
    [data-testid="stSidebar"] {{ background-color: #E2E8F0 !important; border-right: 2px solid #000000 !important; }}
    h1 {{ font-size: 1.8rem !important; font-weight: 900 !important; color: #000000 !important; }}
    
    /* Cellules du calendrier */
    .calendar-cell-unique {{ 
        position: absolute; top: 2px; left: 2px; right: 2px; z-index: 100; 
        padding: 4px; border-radius: 2px; border: 2px solid #000000; 
        color: {text_on_color} !important; text-align: center; font-weight: 900; 
        display: flex; align-items: center; justify-content: center; 
        box-shadow: 2px 2px 0px rgba(0,0,0,1);
        font-size: {"14px" if mode_vue == "Jour" else "11px"}; 
    }}
    
    .grid-line-hour {{ border-bottom: 2px solid #333333 !important; height: 45px; }}
    .grid-line-min {{ border-bottom: 1px dashed #777777 !important; height: 45px; }}
    
    /* Optimisation des inputs sur mobile */
    .stButton button {{ width: 100% !important; font-weight: bold !important; }}
    @media (max-width: 640px) {{
        .main .block-container {{ padding: 1rem 0.5rem !important; }}
    }}
    </style>
    """, unsafe_allow_html=True)

df_view = df[df['Simu'].str.strip().str.upper() == simu_sel.upper()]

# --- NAVIGATION ---

if menu == "📅 Planning":
    st.markdown(f"<h1>⚓ {simu_sel}</h1>", unsafe_allow_html=True)
    
    # En-têtes de colonnes
    cols = st.columns(colonnes_layout)
    jours_fr = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi"]
    
    for i, d in enumerate(jours_a_afficher):
        label = jours_fr[jour_idx] if mode_vue == "Jour" else jours_fr[i]
        cols[i+1].markdown(f"<div style='text-align:center; background-color:{current_color}; color:{text_on_color}; padding:8px; font-weight:900; border:2px solid black; box-shadow: 2px 2px 0px black;'>{label}<br>{d.strftime('%d/%m')}</div>", unsafe_allow_html=True)

    # Grille horaire
    for q in QUARTS_HEURES:
        if q == "20:30": continue
        row_cols = st.columns(colonnes_layout)
        is_pile = q.endswith(":00")
        h_act = int(q.split(':')[0]) + int(q.split(':')[1])/60
        
        # Colonne Heure
        row_cols[0].markdown(f"<div style='height:45px; display:flex; align-items:center; justify-content:flex-end; padding-right:10px; font-weight:900; border-right:3px solid {current_color if is_pile else '#EEE'};'>{q}</div>", unsafe_allow_html=True)
        
        # Colonnes Jours
        for i, d in enumerate(jours_a_afficher):
            with row_cols[i+1]:
                resas = df_view[df_view['Date_DT'].dt.date == d.date()]
                html_bloc = ""
                for _, r in resas.iterrows():
                    h_deb, h_fin = extraire_heures(r['Horaire'])
                    if h_deb == h_act:
                        hauteur_px = int((h_fin - h_deb) * 2 * 45) - 4 
                        html_bloc += f'<div class="calendar-cell-unique" style="background-color:{current_color}; height:{hauteur_px}px;">{r["Equipage"]}</div>'
                st.markdown(f"<div style='position:relative; width:100%; height:45px;'><div class='{'grid-line-hour' if is_pile else 'grid-line-min'}'></div>{html_bloc}</div>", unsafe_allow_html=True)

elif menu == "📊 Statistiques":
    st.markdown("<h1>📊 Statistiques</h1>", unsafe_allow_html=True)
    if not df.empty:
        # (Logique stats identique, Streamlit gère bien les graphiques sur mobile)
        def calcul_duree(horaire_str):
            h_deb, h_fin = extraire_heures(horaire_str)
            return (h_fin - h_deb) if h_deb is not None else 0
        df['Duree_H'] = df['Horaire'].apply(calcul_duree)
        df['Mois'] = df['Date_DT'].dt.strftime('%m - %B')
        df['Annee'] = df['Date_DT'].dt.year

        st.subheader("📁 Volume par équipage (Mois)")
        mois_dispo = sorted(df['Mois'].unique())
        mois_sel = st.selectbox("Mois", mois_dispo, index=len(mois_dispo)-1)
        stats_equipage = df[df['Mois'] == mois_sel].groupby('Equipage')['Duree_H'].sum().reset_index()
        st.dataframe(stats_equipage.sort_values(by='Duree_H', ascending=False), use_container_width=True, hide_index=True)

        st.divider()
        st.subheader("🖥️ Utilisation Simus (An)")
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
                # Date dynamique sur aujourd'hui
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
