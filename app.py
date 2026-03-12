import streamlit as st
import pandas as pd
import requests
import time
import re
import json
import io
from datetime import datetime, timedelta
from PIL import Image, ImageDraw, ImageFont

# --- CONFIGURATION ---
st.set_page_config(page_title="⚓ Planning", layout="wide")

# --- BANDEAU D'ALERTE FORCE (VISIBLE EN MODE SOMBRE) ---
st.markdown("""
    <div style="
        background-color: #FFFFFF; 
        color: #FF0000; 
        padding: 15px; 
        border: 4px solid #FF0000; 
        border-radius: 10px; 
        text-align: center; 
        font-weight: bold; 
        font-size: 1.2rem; 
        margin-bottom: 20px;
        box-shadow: 0px 4px 10px rgba(0,0,0,0.5);
    ">
        ⚠️ ATTENTION : PASSEZ VOTRE TÉLÉPHONE EN "MODE CLAIR"<br>
        <span style="color: #000000; font-size: 0.9rem;">
            Le mode sombre rend certains textes et plannings invisibles.
        </span>
    </div>
    """, unsafe_allow_html=True)

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

def verifier_conflit(df, date_test, horaire_test, simu_test, exclude_idx=None):
    """Vérifie si un créneau chevauche une réservation existante"""
    h_deb_new, h_fin_new = extraire_heures(horaire_test)
    if h_deb_new is None: return False, "Format d'heure invalide."
    
    date_test_dt = pd.to_datetime(date_test)
    # Filtrer par même jour et même simulateur
    match_df = df[(df['Date_DT'].dt.date == date_test_dt.date()) & 
                  (df['Simu'].str.strip().str.upper() == simu_test.upper())]
    
    for idx, row in match_df.iterrows():
        if exclude_idx is not None and idx == exclude_idx:
            continue
        h_deb_ex, h_fin_ex = extraire_heures(row['Horaire'])
        if h_deb_ex is not None:
            if max(h_deb_new, h_deb_ex) < min(h_fin_new, h_fin_ex):
                return True, f"Conflit avec {row['Equipage']} ({row['Horaire']})"
    return False, ""

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
menu = st.sidebar.radio("MENU", ["📅 Planning", "🖥️ Supervision", "🔍 Trouver ses créneaux", "📊 Statistiques", "🔐 Administration"])

# --- CONNEXION ADMIN GLOBALE ---
st.sidebar.title("🔐 Accès ADMIN")
admin_key = st.sidebar.text_input("Mot de passe", type="password", key="global_pwd")
is_admin = (admin_key == ADMIN_PASSWORD)

if is_admin:
    st.sidebar.success("Mode Administrateur Actif")
    
st.sidebar.divider()

# --- CALCUL AUTOMATIQUE DATE/SEMAINE ---
maintenant = datetime.now()
annee_actuelle = maintenant.year
semaine_actuelle = maintenant.isocalendar()[1]
jour_actuel_idx = maintenant.weekday() 

annee_sel = st.sidebar.selectbox("Année", [2025, 2026, 2027], index=1)
semaine_sel = st.sidebar.selectbox("Semaine", range(1, 54), index=semaine_actuelle - 1)
jours_fr_liste = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi"]
choix_j_global = st.sidebar.selectbox("Jour", jours_fr_liste, index=min(maintenant.weekday(), 4) if annee_sel == maintenant.year else 0)
simu_sel = st.sidebar.selectbox("Simulateur", list(SIMU_CONFIG.keys()))

st.sidebar.divider()
st.sidebar.subheader("📱 Options d'affichage")
mode_vue = st.sidebar.segmented_control("Format", ["Semaine", "Jour"], default="Jour")

# --- COPYRIGHT ET SIGNATURE ---
st.sidebar.divider()
st.sidebar.markdown(
    """
    <div style='text-align: center; color: #666666; font-size: 0.8rem; padding: 10px;'>
        © 2026 <b>Maxime JAMAIN</b><br>
        Tous droits réservés<br>
        <span style='font-size: 0.7rem;'>Version Bêta - Planning </span>
    </div>
    """, 
    unsafe_allow_html=True
)

monday = (datetime(annee_sel, 1, 4) - timedelta(days=datetime(annee_sel, 1, 4).weekday())) + timedelta(weeks=semaine_sel-1)
week_days = [monday + timedelta(days=i) for i in range(5)]

d = week_days[jours_fr_liste.index(choix_j_global)]

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
        # On utilise choix_j_global qui vient de la sidebar
        d = week_days[jours_fr_liste.index(choix_j_global)]
        
        st.markdown(f"<div style='text-align:center; background-color:{current_color}; color:{text_on_color}; padding:8px; font-weight:900; border:2px solid black; box-shadow: 2px 2px 0px black; margin-bottom:10px;'>{choix_j_global} {d.strftime('%d/%m')}</div>", unsafe_allow_html=True)
        
        # --- DESSIN DU PLANNING ---
        html_jour = '<div class="planning-frame">'
        for i, q in enumerate(QUARTS_HEURES):
            if i >= 29: break
            top = i * 45
            style = "border-bottom: 2px solid #333;" if q.endswith(":00") else ""
            html_jour += f'<div class="hour-row-fixed" style="top:{top}px; {style}"><div style="width:60px; text-align:right; padding-right:8px; font-weight:900; border-right:3px solid {current_color}; background:#F0F2F6; height:100%; display:flex; align-items:center; justify-content:flex-end; color:black;">{q}</div></div>'
        
        resas = df_view[df_view['Date_DT'].dt.date == d.date()]
        for _, r in resas.iterrows():
            h_deb, h_f = extraire_heures(r['Horaire'])
            if h_deb is not None:
                top_p = int((h_deb - 6) * 90)
                haut = int((h_f - h_deb) * 90) - 2
                html_jour += f'<div class="calendar-cell-unique" style="top:{top_p}px; height:{haut}px; left:65px; right:5px; background-color:{current_color}; font-size:14px;">{r["Equipage"]}</div>'
        st.markdown(html_jour + '</div>', unsafe_allow_html=True)

        # --- QUICK BOOKING CONDITIONNEL ---
        if is_admin:
            with st.expander("⚡ RÉSERVATION RAPIDE", expanded=False):
                with st.form("quick_booking"):
                    c1, c2 = st.columns(2)
                    q_eq = c1.text_input("Équipage", placeholder="Nom")
                    q_hr = c2.text_input("Horaire", placeholder="08h00 - 10h00")
                    if st.form_submit_button("Vérifier et valider la réservation"):
                        if q_eq and q_hr:
                            # On utilise la fonction conflit que tu as déjà
                            conf, msg = verifier_conflit(df, d, q_hr, simu_sel)
                            if conf:
                                st.error(msg)
                            else:
                                requests.post(SCRIPT_URL, data=json.dumps({
                                    "action":"add",
                                    "date":d.strftime("%d/%m/%Y"),
                                    "equipage":q_eq.upper(),
                                    "horaire":q_hr,
                                    "simu":simu_sel
                                }))
                                st.success("Ajouté !"), time.sleep(1), st.rerun()

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

elif menu == "🖥️ Supervision":
    st.markdown("<h1>🖥️ Vue d'ensemble des Simulateurs</h1>", unsafe_allow_html=True)
    
    # On utilise choix_j_global (sidebar) et d (calculé plus haut)
    st.info(f"Visualisation de tous les simulateurs pour le **{choix_j_global} {d.strftime('%d/%m/%Y')}**")

    # On utilise d pour le filtrage
    df_jour = df[df['Date_DT'].dt.date == d.date()]

    # Création de la grille de données (Heures en lignes, Simus en colonnes)
    # On crée une liste d'heures (toutes les 30 min)
    heures_sup = [f"{h:02d}:{m}" for h in range(6, 20) for m in ["00", "30"]]
    
    # On prépare le tableau HTML
    html_sup = """
    <div style="overflow-x: auto;">
        <table style="width: 100%; border-collapse: collapse; font-family: sans-serif; font-size: 0.8rem;">
            <thead>
                <tr style="background-color: #f0f2f6;">
                    <th style="border: 1px solid #ddd; padding: 8px; position: sticky; left: 0; background: #f0f2f6; z-index: 10; color: black;">Heure</th>
    """
    
    # Ajout des colonnes pour chaque simulateur
    for s in SIMU_CONFIG.keys():
        color = SIMU_CONFIG[s]
        html_sup += f'<th style="border: 1px solid #ddd; padding: 8px; background-color: {color}; color: white; text-align: center; min-width: 80px;">{s}</th>'
    
    html_sup += "</tr></thead><tbody>"

    # Remplissage des lignes
    for h_str in heures_sup:
        h_val = int(h_str.split(':')[0]) + int(h_str.split(':')[1])/60
        html_sup += f'<tr><td style="border: 1px solid #ddd; padding: 4px; font-weight: bold; position: sticky; left: 0; background: white; z-index: 5; color: black;">{h_str}</td>'
        
        for s in SIMU_CONFIG.keys():
            # Vérifier si une réservation existe pour ce simu à cette heure
            occupe = False
            nom_eq = ""
            
            # On cherche les résas de ce simulateur
            resas_simu = df_jour[df_jour['Simu'].str.strip().str.upper() == s.upper()]
            for _, r in resas_simu.iterrows():
                h_deb, h_fin = extraire_heures(r['Horaire'])
                if h_deb is not None and h_deb <= h_val < h_fin:
                    occupe = True
                    nom_eq = r['Equipage']
                    break
            
            if occupe:
                color = SIMU_CONFIG[s]
                html_sup += f'<td style="border: 1px solid #ddd; padding: 2px; background-color: {color}44; color: black; text-align: center; font-size: 0.6rem; font-weight: bold;">{nom_eq}</td>'
            else:
                html_sup += '<td style="border: 1px solid #ddd; padding: 2px; background-color: white;"></td>'
        
        html_sup += "</tr>"
    
    html_sup += "</tbody></table></div>"
    
    st.markdown(html_sup, unsafe_allow_html=True)
    
    # Petite légende
    st.caption("💡 Astuce : Sur mobile, faites glisser le tableau vers la droite pour voir tous les simulateurs.")

elif menu == "🔍 Trouver ses créneaux":
    st.markdown("<h1>🔍 Rechercher par Équipage</h1>", unsafe_allow_html=True)
    
    # Zone de recherche
    nom_cherche = st.text_input("Entrez le nom de l'équipage (ex: ECOLE)", "").upper()
    
    if nom_cherche:
        # Filtrage sur le nom, l'année et la semaine sélectionnée en sidebar
        mask = (
            (df['Equipage'].str.contains(nom_cherche, na=False, case=False)) &
            (df['Date_DT'].dt.isocalendar().week == semaine_sel) &
            (df['Date_DT'].dt.year == annee_sel)
        )
        resultats = df[mask].sort_values(by=['Date_DT', 'Horaire'])

        if not resultats.empty:
            st.success(f"Nombre de créneau(x) trouvé(s) : {len(resultats)}")
            
            # Affichage sous forme de "Cartes" pour mobile
            for idx, r in resultats.iterrows():
                with st.container():
                    col_sim, col_info = st.columns([0.2, 0.8])
                    color = SIMU_CONFIG.get(r['Simu'].strip().upper(), "#333")
                    
                    # Petit carré de couleur du simulateur
                    col_sim.markdown(f"""
                        <div style="background-color:{color}; height:60px; border-radius:10px; 
                        border:2px solid black; display:flex; align-items:center; justify-content:center;">
                        </div>
                        """, unsafe_allow_html=True)
                    
                    # Détails de la réservation
                    col_info.markdown(f"""
                        **{r['Date']}** — <span style="color:{color}; font-weight:bold;">{r['Simu']}</span><br>
                        ⌚ **{r['Horaire']}**
                        """, unsafe_allow_html=True)
                    st.divider()
        else:
            st.warning(f"Aucune réservation trouvée pour '{nom_cherche}' en semaine {semaine_sel}.")
    else:
        st.info("Saisissez un nom pour voir votre planning de la semaine.")

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
    
    # Plus besoin de 'pwd = st.sidebar.text_input...' ici !
    # On utilise directement la variable 'is_admin' définie plus haut
    
    if is_admin:
        tab1, tab2, tab3 = st.tabs(["➕ Ajouter", "📝 Modifier", "🗑️ Supprimer"])
        
        # Le reste de ton code d'administration (df_filtre_admin, etc.) continue ici...
        df_filtre_admin = df[
            (df['Date_DT'].dt.isocalendar().week == semaine_sel) & 
            (df['Date_DT'].dt.year == annee_sel)
        ].sort_values(by=['Date_DT', 'Horaire'])

        with tab1:
            with st.form("ajouter_form", clear_on_submit=True):
                d_add = st.date_input("Date", value=datetime.now())
                eq_add = st.text_input("Equipage", placeholder="Nom")
                hr_add = st.text_input("Horaire", placeholder="08h00 - 10h00")
                sm_add = st.selectbox("Simu", list(SIMU_CONFIG.keys()), index=list(SIMU_CONFIG.keys()).index(simu_sel))
                if st.form_submit_button("Vérifier et Ajouter"):
                    if eq_add and hr_add:
                        conflit, msg = verifier_conflit(df, d_add, hr_add, sm_add)
                        if conflit:
                            st.error(f"❌ IMPOSSIBLE : {msg}")
                        else:
                            requests.post(SCRIPT_URL, data=json.dumps({"action":"add","date":d_add.strftime("%d/%m/%Y"),"equipage":eq_add.upper(),"horaire":hr_add,"simu":sm_add}))
                            st.success("✅ Réservation validée !"), time.sleep(1), st.rerun()
                    else:
                        st.warning("Veuillez remplir tous les champs.")

        with tab2:
            if not df_filtre_admin.empty:
                idx_mod = st.selectbox("Sélectionner le créneau", df_filtre_admin.index, format_func=lambda i: f"{df.loc[i,'Date']} | {df.loc[i,'Equipage']} ({df.loc[i,'Horaire']})")
                with st.form("modifier_form"):
                    ed = st.date_input("Date", value=df.loc[idx_mod,'Date_DT'])
                    ee = st.text_input("Equipage", df.loc[idx_mod,'Equipage'])
                    eh = st.text_input("Horaire", df.loc[idx_mod,'Horaire'])
                    es = st.selectbox("Simu", list(SIMU_CONFIG.keys()), index=list(SIMU_CONFIG.keys()).index(str(df.loc[idx_mod,'Simu']).strip().upper()))
                    if st.form_submit_button("Vérifier et Enregistrer"):
                        conflit, msg = verifier_conflit(df, ed, eh, es, exclude_idx=idx_mod)
                        if conflit:
                            st.error(f"❌ MODIFICATION IMPOSSIBLE : {msg}")
                        else:
                            requests.post(SCRIPT_URL, data=json.dumps({"action":"update","row":int(idx_mod)+2,"date":ed.strftime("%d/%m/%Y"),"equipage":ee.upper(),"horaire":eh,"simu":es}))
                            st.success("📝 Modification enregistrée !"), time.sleep(1), st.rerun()
            else:
                st.warning("Aucun créneau à modifier cette semaine.")

        with tab3:
            if not df_filtre_admin.empty:
                t_del = st.selectbox("Créneau à supprimer", df_filtre_admin.index, format_func=lambda i: f"{df.loc[i,'Date']} | {df.loc[i,'Equipage']} ({df.loc[i,'Horaire']}) {df.loc[i,'Simu']}")
                if st.button("❌ Supprimer définitivement", disabled=not st.checkbox("Confirmer")):
                    requests.post(SCRIPT_URL, data=json.dumps({"action":"delete","row":int(t_del)+2}))
                    st.success("🗑️ Supprimé !"), time.sleep(1), st.rerun()
    else:
        # Message si l'utilisateur n'est pas admin
        st.error("🔒 Accès réservé. Veuillez saisir le mot de passe dans la barre latérale pour accéder à la gestion.")
        st.info("L'administration permet d'ajouter, modifier ou supprimer des créneaux de manière avancée.")
