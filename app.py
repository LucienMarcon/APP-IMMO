import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import google.generativeai as genai
from PIL import Image
import requests
import re

# ==========================================
# 1. CONFIGURATION ET MÉMOIRE (SESSION STATE)
# ==========================================
st.set_page_config(layout="wide", page_title="ImmoInvest Pro", page_icon="🏢")

# Initialisation de la mémoire pour éviter les pertes au rafraîchissement
if "ai_budget_m2" not in st.session_state: st.session_state.ai_budget_m2 = 0
if "ai_prix_m2" not in st.session_state: st.session_state.ai_prix_m2 = 0
if "ai_loyer_m2" not in st.session_state: st.session_state.ai_loyer_m2 = 0
if "rapport_marche" not in st.session_state: st.session_state.rapport_marche = ""
if "rapport_travaux" not in st.session_state: st.session_state.rapport_travaux = ""
if "is_pro_active" not in st.session_state: st.session_state.is_pro_active = False

# CSS Personnalisé pour un look "Lovable"
st.markdown("""
    <style>
    .main {background-color: #F8FAFC;}
    .stMetric {background-color: #ffffff; padding: 15px; border-radius: 10px; border: 1px solid #E2E8F0; box-shadow: 0 1px 3px rgba(0,0,0,0.1);}
    div.stButton > button:first-child {
        background-color: #0F172A; color: white; border-radius: 8px; width: 100%; height: 3.5em; font-weight: 600;
    }
    div.stButton > button:hover {background-color: #334155; border: none;}
    .stExpander {background-color: white; border-radius: 10px;}
    h1, h2, h3 {color: #1E293B; font-weight: 700;}
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. GESTION DES CLÉS API ET QUOTAS
# ==========================================
st.sidebar.title("🏢 ImmoInvest Pro")
user_key = st.sidebar.text_input("Votre clé API personnelle (Optionnel) :", type="password")

# Choix de la clé : Utilisateur > Secrets Streamlit
API_KEY = user_key if user_key else st.secrets.get("GEMINI_API_KEY")

if API_KEY:
    genai.configure(api_key=API_KEY)
    # Détection automatique du mode PRO ou ÉCO
    try:
        tmp_model = genai.GenerativeModel('gemini-2.5-pro')
        # Test de connexion minimal
        tmp_model.generate_content("test", generation_config={"max_output_tokens": 1})
        st.session_state.is_pro_active = True
        st.sidebar.success("✅ Mode PRO actif (Recherche Web)")
    except Exception:
        st.session_state.is_pro_active = False
        st.sidebar.warning("⚠️ Mode ÉCO (Quota Pro saturé)")
    
    model_vision = genai.GenerativeModel('gemini-2.5-flash')
    model_pro = genai.GenerativeModel('gemini-2.5-pro')
else:
    st.sidebar.error("❌ Aucune clé API détectée")

# ==========================================
# 3. FONCTIONS UTILES (LOGIQUE & IA)
# ==========================================

def extraire_nombre(texte, balise):
    """Extrait proprement un nombre entre balises [BALISE: 123]"""
    pattern = rf"\[{balise}:\s*(\d+)\]"
    match = re.search(pattern, texte)
    return int(match.group(1)) if match else 0

def analyser_travaux_photo(image):
    prompt = """Tu es maître d'œuvre. Analyse l'état et les matériaux sur cette photo.
    Détaille les rénovations à prévoir et donne une estimation au m².
    FINIS PAR CETTE BALISE : [BUDGET_M2: XXX]"""
    response = model_vision.generate_content([prompt, image])
    return response.text

def analyser_marche_local(ville, cp):
    prompt = f"""Analyse précise du marché immobilier à {ville} ({cp}). 
    Donne le prix m² moyen de vente et le loyer m² moyen HC.
    FINIS PAR CES BALISES : [PRIX_M2: XXX] [LOYER_M2: YYY]"""
    
    try:
        if st.session_state.is_pro_active:
            # Recherche Web si le quota Pro le permet
            response = model_pro.generate_content(prompt, tools=[{'google_search_retrieval': {}}])
        else:
            response = model_vision.generate_content(prompt)
        return response.text
    except:
        return "Erreur de quota. Données indicatives : [PRIX_M2: 2500] [LOYER_M2: 12]"

def calculer_mensualite(capital, taux, annees):
    if capital <= 0 or annees <= 0: return 0.0
    tm = (taux / 100) / 12
    n = annees * 12
    if tm == 0: return capital / n
    return capital * (tm * (1 + tm)**n) / ((1 + tm)**n - 1)

# ==========================================
# 4. INTERFACE : LOCALISATION & IA
# ==========================================
mode = st.sidebar.radio("Stratégie d'investissement :", ["Investissement Locatif", "Marchand de Biens"])

st.header("📍 Localisation & Analyse de Marché")

# Autocomplétion d'adresse en direct
addr_query = st.text_input("Commencez à taper une adresse ou une ville...", placeholder="Ex: 15 rue de Rivoli, Paris")

if len(addr_query) > 3:
    url_ban = f"https://api-adresse.data.gouv.fr/search/?q={addr_query}&limit=5"
    data_ban = requests.get(url_ban).json()
    if data_ban['features']:
        adresses_dict = {f["properties"]["label"]: f["properties"] for f in data_ban['features']}
        choix = st.selectbox("Sélectionnez l'adresse exacte :", adresses_dict.keys())
        
        info = adresses_dict[choix]
        ville, cp = info['city'], info['postcode']
        st.success(f"📍 Bien localisé : {ville} ({cp})")
        
        if st.button("📊 Lancer l'analyse du marché local"):
            with st.spinner(f"L'IA étudie les données immobilières de {ville}..."):
                st.session_state.rapport_marche = analyser_marche_local(ville, cp)
                st.session_state.ai_prix_m2 = extraire_nombre(st.session_state.rapport_marche, "PRIX_M2")
                st.session_state.ai_loyer_m2 = extraire_nombre(st.session_state.rapport_marche, "LOYER_M2")
                st.rerun()

if st.session_state.rapport_marche:
    with st.expander("📄 Voir l'analyse détaillée du quartier", expanded=True):
        st.write(re.sub(r'\[.*?\]', '', st.session_state.rapport_marche))

st.markdown("---")

# ==========================================
# 5. INTERFACE : AUDIT PHOTO
# ==========================================
st.header("📸 Expertise Travaux par Vision")
photo = st.file_uploader("Importez une photo de l'annonce :", type=["jpg", "jpeg", "png"])

if photo:
    img = Image.open(photo)
    col_img, col_btn = st.columns([1, 2])
    col_img.image(img, use_container_width=True)
    
    if col_btn.button("✨ Estimer le montant des travaux"):
        with st.spinner("Analyse visuelle des finitions..."):
            st.session_state.rapport_travaux = analyser_travaux_photo(img)
            st.session_state.ai_budget_m2 = extraire_nombre(st.session_state.rapport_travaux, "BUDGET_M2")
            st.rerun()

if st.session_state.rapport_travaux:
    with st.expander("🔨 Détails des travaux estimés", expanded=True):
        st.info(re.sub(r'\[.*?\]', '', st.session_state.rapport_travaux))

st.markdown("---")

# ==========================================
# 6. CALCULATEUR FINANCIER COMPLET
# ==========================================
st.header(f"💰 Simulation Financière : {mode}")

c1, c2 = st.columns(2)

with c1:
    st.subheader("Acquisition")
    surface = st.number_input("Surface du bien (m²)", value=50, step=1)
    prix_achat = st.number_input("Prix d'achat net vendeur (€)", value=100000, step=1000)
    
    if mode == "Investissement Locatif":
        # Logique Loyer IA
        loyer_ia_tot = float(st.session_state.ai_loyer_m2 * surface)
        use_loyer_ia = st.checkbox(f"Appliquer Loyer IA ({loyer_ia_tot}€)", value=(loyer_ia_tot > 0))
        loyer_final = st.number_input("Loyer mensuel HC (€)", value=loyer_ia_tot if use_loyer_ia else 500.0)
    else:
        # Logique Revente IA
        revente_ia_tot = float(st.session_state.ai_prix_m2 * surface)
        use_revente_ia = st.checkbox(f"Appliquer Revente IA ({revente_ia_tot}€)", value=(revente_ia_tot > 0))
        revente_final = st.number_input("Prix de revente estimé (€)", value=revente_ia_tot if use_revente_ia else 160000.0)

with c2:
    st.subheader("Chantier & Prêt")
    # Logique Travaux IA
    trav_ia_tot = float(st.session_state.ai_budget_m2 * surface)
    use_trav_ia = st.checkbox(f"Appliquer Travaux IA ({trav_ia_tot}€)", value=(trav_ia_tot > 0))
    trav_final = st.number_input("Budget travaux total (€)", value=trav_ia_tot if use_trav_ia else 0.0)
    
    apport = st.number_input("Apport personnel (€)", value=10000)
    duree = st.number_input("Durée du prêt (ans)", value=20)
    taux = st.number_input("Taux d'intérêt (%)", value=3.5, step=0.1)
    notaire = st.number_input("Frais de notaire (%)", value=8.5 if mode == "Investissement Locatif" else 2.5)

# CALCULS DE SYNTHÈSE
frais_notaire = prix_achat * (notaire / 100)
total_projet = prix_achat + frais_notaire + trav_final
capital_emprunte = max(0, total_projet - apport)
mensualite = calculer_mensualite(capital_emprunte, taux, duree)

st.markdown("### 📊 Résultats de l'opération")
r1, r2, r3 = st.columns(3)

if mode == "Investissement Locatif":
    renta_brute = ((loyer_final * 12) / total_projet) * 100 if total_projet > 0 else 0
    cash_flow = loyer_final - mensualite - (loyer_final * 0.2) # Estimation 20% charges/taxes
    r1.metric("Investissement Total", f"{total_projet:,.0f} €")
    r2.metric("Rentabilité Brute", f"{renta_brute:.2f} %")
    r3.metric("Cash-Flow Net (est.)", f"{cash_flow:,.0f} € / mois")
else:
    marge = revente_final - total_projet
    roi = (marge / total_projet) * 100 if total_projet > 0 else 0
    r1.metric("Prix de Revient", f"{total_projet:,.0f} €")
    r2.metric("Marge Brute", f"{marge:,.0f} €")
    r3.metric("ROI", f"{roi:.1f} %")

# Graphique de répartition
fig = px.pie(
    names=['Prix Achat', 'Travaux', 'Notaire'], 
    values=[prix_achat, trav_final, frais_notaire],
    title="Répartition du capital",
    hole=0.4,
    color_discrete_sequence=['#0F172A', '#334155', '#94A3B8']
)
st.plotly_chart(fig, use_container_width=True)

# Diagnostic discret
with st.expander("🛠️ Diagnostic Technique (Debug)"):
    st.write(f"Mémoire Loyer : {st.session_state.ai_loyer_m2}€/m2")
    st.write(f"Mémoire Prix : {st.session_state.ai_prix_m2}€/m2")
    st.write(f"Mémoire Travaux : {st.session_state.ai_budget_m2}€/m2")
