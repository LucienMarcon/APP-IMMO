import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import google.generativeai as genai
from PIL import Image
import requests
import re

# ==========================================
# CONFIGURATION ET MÉMOIRE
# ==========================================
st.set_page_config(layout="wide", page_title="ImmoInvest Pro", page_icon="🏢")

# Initialisation des variables en mémoire (Session State)
if "ai_budget_m2" not in st.session_state: st.session_state.ai_budget_m2 = 0
if "ai_prix_m2" not in st.session_state: st.session_state.ai_prix_m2 = 0
if "ai_loyer_m2" not in st.session_state: st.session_state.ai_loyer_m2 = 0
if "adresse_valide" not in st.session_state: st.session_state.adresse_valide = None

# CSS pour un look "Lovable App" professionnel
st.markdown("""
    <style>
    .main {background-color: #F8FAFC;}
    .stMetric {background-color: #ffffff; padding: 15px; border-radius: 10px; border: 1px solid #E2E8F0;}
    div.stButton > button:first-child {
        background-color: #0F172A; color: white; border-radius: 8px; width: 100%; border: none; height: 3em;
    }
    div.stButton > button:hover {background-color: #334155; border: none;}
    h1, h2, h3 {color: #1E293B; font-weight: 600;}
    </style>
""", unsafe_allow_html=True)

# ==========================================
# CONNEXION API GEMINI (LOGIQUE HYBRIDE)
# ==========================================
st.sidebar.title("🏢 ImmoInvest Pro")

st.sidebar.subheader("🔑 Paramètres API")
user_key = st.sidebar.text_input(
    "Votre clé API personnelle (optionnel) :", 
    type="password", 
    help="Collez votre clé Google AI Studio ici pour utiliser votre propre quota."
)

if user_key:
    API_KEY = user_key
    st.sidebar.success("Clé personnelle active")
elif "GEMINI_API_KEY" in st.secrets:
    API_KEY = st.secrets["GEMINI_API_KEY"]
    st.sidebar.info("Clé partagée active")
else:
    API_KEY = None
    st.sidebar.error("Aucune clé API configurée")

if API_KEY:
    try:
        genai.configure(api_key=API_KEY)
        model_vision = genai.GenerativeModel('gemini-2.5-flash')
        model_research = genai.GenerativeModel('gemini-2.5-pro')
    except Exception as e:
        st.sidebar.error(f"Erreur config : {e}")

# ==========================================
# FONCTIONS INTELLIGENTES
# ==========================================

def analyser_travaux_photo(image):
    prompt = """
    Agis en tant qu'expert en bâtiment. Analyse cette photo et :
    1. Détaille les travaux de rénovation visibles.
    2. Donne une estimation du coût de rénovation au m².
    FINIS TA RÉPONSE PAR CETTE BALISE : [BUDGET_M2: XXX] (remplace XXX par le chiffre).
    """
    response = model_vision.generate_content([prompt, image])
    return response.text

def analyser_marche_local(ville, cp):
    prompt = f"""
    Analyse le marché immobilier actuel pour {ville} ({cp}).
    1. Donne le prix de vente moyen au m² pour l'ancien.
    2. Donne le loyer moyen mensuel au m² hors charges.
    3. Fais une brève analyse de la tension locative.
    FINIS PAR CES BALISES : [PRIX_M2: XXX] [LOYER_M2: YYY]
    """
    try:
        response = model_research.generate_content(prompt, tools=[{'google_search_retrieval': {}}])
        return response.text
    except Exception:
        try:
            st.warning("⏱️ Mode éco : Analyse basée sur l'historique de l'IA.")
            response = model_vision.generate_content(prompt)
            return response.text
        except:
            return "Service indisponible.\n[PRIX_M2: 2000]\n[LOYER_M2: 12]"

def calculer_mensualite(capital, taux, annees):
    if capital <= 0 or annees <= 0: return 0.0
    tm = (taux / 100) / 12
    n = annees * 12
    if tm == 0: return capital / n
    return capital * (tm * (1 + tm)**n) / ((1 + tm)**n - 1)

# ==========================================
# INTERFACE PRINCIPALE
# ==========================================
mode = st.sidebar.radio("Stratégie d'investissement :", ["Investissement Locatif", "Marchand de Biens"])
st.sidebar.markdown("---")

st.header(f"Projet : {mode}")

# --- ÉTAPE 1 : LOCALISATION ---
st.subheader("📍 Localisation & Marché")
query = st.text_input("Adresse ou Ville :", placeholder="Ex: Châteauroux...")

if query:
    api_url = f"https://api-adresse.data.gouv.fr/search/?q={query}&limit=5"
    res = requests.get(api_url).json()
    if res['features']:
        options = {f["properties"]["label"]: f["properties"] for f in res['features']}
        selection = st.selectbox("Validez l'emplacement :", options.keys())
        st.session_state.adresse_valide = options[selection]
        
        ville = st.session_state.adresse_valide['city']
        cp = st.session_state.adresse_valide['postcode']
        st.success(f"Cible : {ville} ({cp})")
        
        if st.button("📊 Analyser le marché local"):
            with st.spinner("Analyse des data sectorielles..."):
                rapport = analyser_marche_local(ville, cp)
                p_m2 = re.search(r'\[PRIX_M2:\s*(\d+)\]', rapport)
                l_m2 = re.search(r'\[LOYER_M2:\s*(\d+)\]', rapport)
                if p_m2: st.session_state.ai_prix_m2 = int(p_m2.group(1))
                if l_m2: st.session_state.ai_loyer_m2 = int(l_m2.group(1))
                st.markdown("### Rapport IA")
                st.write(re.sub(r'\[.*?\]', '', rapport))
                st.rerun() # On force le rafraîchissement pour mettre à jour les calculs en bas

st.markdown("---")

# --- ÉTAPE 2 : TRAVAUX ---
st.subheader("📸 Expertise Travaux")
up = st.file_uploader("Photo du bien :", type=["jpg","png","jpeg"])

if up:
    img = Image.open(up)
    col_i, col_t = st.columns([1, 2])
    col_i.image(img, use_container_width=True)
    if col_t.button("✨ Estimer le chantier"):
        with st.spinner("Scan visuel..."):
            audit = analyser_travaux_photo(img)
            b_m2 = re.search(r'\[BUDGET_M2:\s*(\d+)\]', audit)
            if b_m2: st.session_state.ai_budget_m2 = int(b_m2.group(1))
            col_t.write(re.sub(r'\[.*?\]', '', audit))
            st.rerun()

st.markdown("---")

# --- ÉTAPE 3 : FINANCES ---
st.subheader("💰 Simulation Financière")
col_a, col_b = st.columns(2)

with col_a:
    surface = st.number_input("Surface (m²)", value=50, key="surf_input")
    prix_bien = st.number_input("Prix net vendeur (€)", value=100000)
    
    if mode == "Investissement Locatif":
        # Logique Loyer
        loyer_ia_total = float(st.session_state.ai_loyer_m2 * surface)
        use_loyer_ia = st.checkbox("Appliquer Loyer IA", value=(loyer_ia_total > 0), key="check_loyer")
        
        default_loyer = loyer_ia_total if use_loyer_ia else 500.0
        loyer_f = st.number_input("Loyer mensuel HC (€)", value=default_loyer, step=10.0)
    else:
        # Logique Revente (Marchand)
        rev_ia_total = float(st.session_state.ai_prix_m2 * surface)
        use_rev_ia = st.checkbox("Appliquer Revente IA", value=(rev_ia_total > 0), key="check_rev")
        
        default_rev = rev_ia_total if use_rev_ia else 150000.0
        rev_f = st.number_input("Prix de revente (€)", value=default_rev, step=1000.0)

with col_b:
    # Logique Travaux
    trav_ia_total = float(st.session_state.ai_budget_m2 * surface)
    use_trav_ia = st.checkbox("Appliquer Travaux IA", value=(trav_ia_total > 0), key="check_trav")
    
    default_trav = trav_ia_total if use_trav_ia else 0.0
    trav_f = st.number_input("Budget Travaux (€)", value=default_trav, step=500.0)
    
    notaire = st.number_input("Notaire (%)", value=8.5 if mode=="Investissement Locatif" else 2.5)
    apport = st.number_input("Apport (€)", value=10000)
    duree = st.number_input("Durée (ans)", value=20)
    taux = st.number_input("Taux (%)", value=3.5)

# Calculs globaux
total_invest = prix_bien + (prix_bien * notaire/100) + trav_f
mensu = calculer_mensualite(max(0, total_invest - apport), taux, duree)

st.markdown("### 📊 Synthèse")
res1, res2, res3 = st.columns(3)

if mode == "Investissement Locatif":
    renta = ((loyer_f * 12) / total_invest) * 100 if total_invest > 0 else 0
    cf = loyer_f - mensu - (loyer_f * 0.2)
    res1.metric("Investissement Total", f"{total_invest:,.0f} €")
    res2.metric("Rentabilité Brute", f"{renta:.2f} %")
    res3.metric("Cash-Flow (est.)", f"{cf:,.0f} €/m")
else:
    marge = rev_f - total_invest
    roi = (marge / total_invest) * 100 if total_invest > 0 else 0
    res1.metric("Prix de Revient", f"{total_invest:,.0f} €")
    res2.metric("Marge Brute", f"{marge:,.0f} €")
    res3.metric("ROI", f"{roi:.1f} %")

# Diagnostic discret
with st.expander("Diagnostic Technique"):
    st.write(f"Mémoire IA - Travaux: {st.session_state.ai_budget_m2}€/m²")
    st.write(f"Mémoire IA - Prix Marché: {st.session_state.ai_prix_m2}€/m²")
    st.write(f"Mémoire IA - Loyer Marché: {st.session_state.ai_loyer_m2}€/m²")
