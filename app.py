import streamlit as st
import pandas as pd
import requests
import time
import re
import json
from datetime import datetime, timedelta
import streamlit.components.v1 as components

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

# Plage horaire : de 06:00 à 20:00
QUARTS_HEURES = [f"{h:02d}:{m}" for h in range(6, 21) for m in ["00", "30"]]

st.set_page_config(page_title="⚓ Planning Naval", layout="wide")

# --- FONCTION DE CAPTURE (JS) - CADRAGE CORRIGÉ ---
def bouton_capture(nom_fichier):
    # Composant HTML/JS pour capturer UNIQUEMENT le calendrier
    components.html(f"""
        <script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script>
        <script>
        function doCapture() {{
            // MODIFICATION ICI : On cible l'élément spécifique 'stBlock' qui contient le calendrier
            // window.parent.document nous permet de sortir de l'iframe du composant
            const doc = window.parent.document;
            
            // On cherche le conteneur du titre '⚓ Planning : ...' et on remonte d'un niveau
            const titleEl = Array.from(doc.querySelectorAll('h1')).find(el => el.textContent.includes('⚓ Planning :'));
            
            if (titleEl) {{
                // Le parent direct du titre contient généralement tout le planning
                const calendarBlock = titleEl.closest('[data-testid="stBlock"]');
                
                html2canvas(calendarBlock, {{
                    backgroundColor: "#FFFFFF",
                    scale: 2, // Haute définition
                    useCORS: true,
                    // Petits ajustements pour s'assurer que tout rentre
                    logging: false,
                    onclone: function(clonedDoc) {{
                        // Optionnel : masquer des éléments indésirables dans le clone avant capture
                    }}
                }}).then(canvas => {{
                    const link = document.createElement('a');
                    link.download = '{nom_fichier}.png';
                    link.href = canvas.toDataURL("image/png");
                    link.click();
                }});
            }} else {{
                console.error("Impossible de trouver le conteneur du calendrier.");
            }}
        }}
        </script>
        <button onclick="doCapture()" style="
            background-color: #003366; 
            color: white; 
            border: none; 
            padding: 12px; 
            border-radius: 8px; 
            cursor: pointer;
            font-weight: bold;
            width: 100%;
            font-family: sans-serif;
            font-size: 14px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
            📸 Télécharger l'IMAGE du calendrier
        </button>
    """, height=70)

# --- STYLE CSS ---
st.markdown("""
    <style>
    .slot-wrapper { position: relative; width: 100%; height: 45px; }
    .calendar-cell-unique { 
        position: absolute; top: 2px; left: 2px; right: 2px;
        z-index: 100; padding: 4px; border-radius: 4px; 
        font-size: 13px; border: 1px solid rgba(0,0,0,0.2); 
        color: #000 !important; text-align: center; font-weight: bold;
        display: flex; align-items: center; justify-content: center;
        overflow: hidden; box-shadow: 2px 2px 5px rgba(0,0,0,0.1);
        pointer-events: none; /* Évite de bloquer les clics si besoin */
    }
    .time-col-full { font-size: 14px; font-weight: 900; color: #003366; text-align: right; padding-right: 15px; border-right: 4px solid #003366; }
    .time-col-half { font-size: 13px; font-style: italic; font-weight: 400; color: #555; text-align: right; padding-right: 15px; border-right: 4px solid #99abc0; }
    .grid-line-hour { border-bottom: 2px solid #888; height: 45px; background-color: rgba(0,0,0,0.02); }
    .grid-line-min { border-bottom: 1px dashed #ccc; height: 45px; }
    .day-header { text-align: center; background-color: #003366; color: white; padding: 10px; border-radius: 4px; font-weight: bold; margin-bottom: 10px; }
    
    /* Pour s'assurer que html2canvas capture bien tout, on donne un fond blanc explicite */
    [data-testid="stBlock"] { background-color: white; }
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

df = load_data()

# --- SIDEBAR ---
menu = st.sidebar.radio("MENU", ["📅 Planning Hebdomadaire", "📊 Statistiques", "🔐 Administration"])

st.sidebar.divider()
st.sidebar.subheader("Sélection")
annee_sel = st.sidebar.selectbox("Année", [2025, 2026, 2027], index=1)
semaine_sel = st.sidebar.selectbox("Semaine", range(1, 54), index=datetime.now().isocalendar()[1]-1)
simu_sel = st.sidebar.selectbox("Simulateur", list(SIMU_CONFIG.keys()))

st.sidebar.divider()
st.sidebar.write("💾 **Exporter**")
# Nom de fichier dynamique
filename = f"Planning_{simu_sel}_S{semaine_sel}_{annee_sel}"
bouton_capture(filename)

# --- AFFICHAGE ---
monday = (datetime(annee_sel, 1, 4) - timedelta(days=datetime(annee_sel, 1, 4).weekday())) + timedelta(weeks=semaine_sel-1)
week_days = [monday + timedelta(days=i) for i in range(5)]

if menu == "📅 Planning Hebdomadaire":
    # ATTENTION : Le titre h1 est crucial pour le sélecteur JS
    st.title(f"⚓ Planning : {simu_sel}")
    
    # Conteneur principal pour le planning (stBlock)
    cols = st.columns([0.6] + [1]*5)
    jours_fr = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi"]
    for i, d in enumerate(week_days):
        cols[i+1].markdown(f"<div class='day-header'>{jours_fr[i]}<br>{d.strftime('%d/%m')}</div>", unsafe_allow_html=True)

    df_view = df[df['Simu'].str.strip().str.upper() == simu_sel.upper()]
    color_active = SIMU_CONFIG.get(simu_sel, "#EEEEEE")

    for q in QUARTS_HEURES:
        if q == "20:30": continue
        row_cols = st.columns([0.6] + [1]*5)
        is_pile = q.endswith(":00")
        h_actuelle = int(q.split(':')[0]) + int(q.split(':')[1])/60
        
        t_class = "time-col-full" if is_pile else "time-col-half"
        row_cols[0].markdown(f"<div class='{t_class}'>{q}</div>", unsafe_allow_html=True)
        
        for i, d in enumerate(week_days):
            with row_cols[i+1]:
                resas = df_view[df_view['Date_DT'].dt.date == d.date()]
                html_bloc = ""
                for _, r in resas.iterrows():
                    h_deb, h_fin = extraire_heures(r['Horaire'])
                    if h_deb == h_actuelle:
                        hauteur_px = int((h_fin - h_deb) * 2 * 45) - 4 
                        html_bloc += f'<div class="calendar-cell-unique" style="background-color:{color_active}; height:{hauteur_px}px;">{r["Equipage"]}</div>'
                
                grid_class = "grid-line-hour" if is_pile else "grid-line-min"
                st.markdown(f"<div class='slot-wrapper'><div class='{grid_class}'></div>{html_bloc}</div>", unsafe_allow_html=True)

elif menu == "📊 Statistiques":
    st.title("📊 Statistiques")
    if not df.empty:
        st.bar_chart(df['Simu'].value_counts())
        st.dataframe(df.drop(columns=['Date_DT']), use_container_width=True)

elif menu == "🔐 Administration":
    st.title("⚙️ Gestion")
    pwd = st.sidebar.text_input("Mot de passe", type="password")
    if pwd == ADMIN_PASSWORD:
        tab1, tab2, tab3 = st.tabs(["➕ Ajouter", "📝 Modifier", "🗑️ Supprimer"])
        def format_resa(idx):
            r = df.loc[idx]
            return f"{r['Date']} | {r['Horaire']} | {r['Simu']} | {r['Equipage']}"
        with tab1:
            with st.form("add_form", clear_on_submit=True):
                d = st.date_input("Date", format="DD/MM/YYYY")
                eq = st.text_input("Équipage")
                hr = st.text_input("Horaire (ex: 08:30 - 12:00)")
                sm = st.selectbox("Simulateur", list(SIMU_CONFIG.keys()))
                if st.form_submit_button("VALIDER"):
                    requests.post(SCRIPT_URL, data=json.dumps({"action":"add","date":d.strftime("%d/%m/%Y"),"equipage":eq,"horaire":hr,"simu":sm}))
                    st.success("Ajouté !"); time.sleep(1); st.rerun()
        with tab2:
            if not df.empty:
                idx = st.selectbox("Modifier", df.index, format_func=format_resa)
                with st.form("edit_form"):
                    ed = st.date_input("Date", value=df.loc[idx,'Date_DT'], format="DD/MM/YYYY")
                    ee = st.text_input("Équipage", df.loc[idx,'Equipage'])
                    eh = st.text_input("Horaire", df.loc[idx,'Horaire'])
                    es = st.selectbox("Simulateur", list(SIMU_CONFIG.keys()), index=list(SIMU_CONFIG.keys()).index(str(df.loc[idx,'Simu']).strip()) if str(df.loc[idx,'Simu']).strip() in SIMU_CONFIG else 0)
                    if st.form_submit_button("SAUVEGARDER"):
                        requests.post(SCRIPT_URL, data=json.dumps({"action":"update","row":int(idx)+2,"date":ed.strftime("%d/%m/%Y"),"equipage":ee,"horaire":eh,"simu":es}))
                        st.success("Mis à jour !"); time.sleep(1); st.rerun()
        with tab3:
            if not df.empty:
                target = st.selectbox("Supprimer", df.index, format_func=format_resa)
                confirm = st.checkbox("Confirmer la suppression")
                if st.button("❌ Supprimer définitivement", disabled=not confirm):
                    requests.post(SCRIPT_URL, data=json.dumps({"action":"delete","row":int(target)+2}))
                    st.success("Supprimé !"); time.sleep(1); st.rerun()
    else: st.info("Mot de passe requis.")
