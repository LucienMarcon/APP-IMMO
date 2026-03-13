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

# Initialisation des variables en mémoire
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
    .reportview-container .main .block-container {padding-top: 2rem;}
    h1, h2, h3 {color: #1E293B;}
    </style>
""", unsafe_allow_html=True)

# ==========================================
# CONNEXION API GEMINI
# ==========================================
if "GEMINI_API_KEY" in st.secrets:
    API_KEY = st.secrets["GEMINI_API_KEY"]
else:
    API_KEY = "CLE_NON_TROUVEE"

genai.configure(api_key=API_KEY)

# Utilisation des modèles de dernière génération identifiés dans votre diagnostic
model_vision = genai.GenerativeModel('gemini-2.5-flash')
model_research = genai.GenerativeModel('gemini-2.5-pro')

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
        # Tentative A : Avec la recherche internet en temps réel
        response = model_research.generate_content(prompt, tools=[{'google_search_retrieval': {}}])
        return response.text
    except Exception as e:
        # Si erreur (comme ResourceExhausted), on passe au Plan B
        if "ResourceExhausted" in str(e) or "429" in str(e):
            st.warning("⏱️ Quota de recherche web atteint. L'IA utilise son historique de données.")
            # Tentative B : On enlève l'outil de recherche web (tools=...)
            response_fallback = model_research.generate_content(prompt)
            return response_fallback.text
        else:
            # Si c'est une autre erreur, on l'affiche
            return f"Erreur technique : {e}"

def calculer_mensualite(capital, taux, annees):
    if capital <= 0 or annees <= 0: return 0.0
    tm = (taux / 100) / 12
    n = annees * 12
    if tm == 0: return capital / n
    return capital * (tm * (1 + tm)**n) / ((1 + tm)**n - 1)

# ==========================================
# BARRE LATÉRALE ET NAVIGATION
# ==========================================
st.sidebar.title("🏢 ImmoInvest Pro")
mode = st.sidebar.radio("Stratégie d'investissement :", ["Investissement Locatif", "Marchand de Biens"])
st.sidebar.markdown("---")
with st.sidebar.expander("Diagnostic Système"):
    st.write("API Gemini: Connectée")
    st.write("Modèles: 2.5 Flash & Pro")

# ==========================================
# ÉTAPE 1 : LOCALISATION (API ÉTAT)
# ==========================================
st.header("📍 Localisation & Marché")
query = st.text_input("Rechercher une adresse ou une ville :", placeholder="Ex: 10 rue de la Paix, Châteauroux...")

if query:
    api_url = f"https://api-adresse.data.gouv.fr/search/?q={query}&limit=5"
    res = requests.get(api_url).json()
    if res['features']:
        options = {f["properties"]["label"]: f["properties"] for f in res['features']}
        selection = st.selectbox("Confirmez l'emplacement :", options.keys())
        st.session_state.adresse_valide = options[selection]
        
        ville = st.session_state.adresse_valide['city']
        cp = st.session_state.adresse_valide['postcode']
        st.success(f"Bien situé à {ville} ({cp})")
        
        if st.button("🔍 Analyser les prix du quartier avec l'IA"):
            with st.spinner("Recherche des données de marché en cours..."):
                rapport = analyser_marche_local(ville, cp)
                
                # Extraction des données
                p_m2 = re.search(r'\[PRIX_M2:\s*(\d+)\]', rapport)
                l_m2 = re.search(r'\[LOYER_M2:\s*(\d+)\]', rapport)
                
                if p_m2: st.session_state.ai_prix_m2 = int(p_m2.group(1))
                if l_m2: st.session_state.ai_loyer_m2 = int(l_m2.group(1))
                
                st.markdown("### Rapport de Marché")
                st.write(re.sub(r'\[.*?\]', '', rapport)) # Affiche le texte sans les balises
    else:
        st.error("Adresse introuvable.")

st.markdown("---")

# ==========================================
# ÉTAPE 2 : AUDIT TRAVAUX (VISION)
# ==========================================
st.header("📸 Expertise Travaux")
up = st.file_uploader("Importez une photo du bien pour estimer le chantier :", type=["jpg","png","jpeg"])

if up:
    img = Image.open(up)
    col_i, col_t = st.columns([1, 2])
    col_i.image(img, use_container_width=True)
    
    if col_t.button("✨ Lancer l'expertise visuelle"):
        with st.spinner("Analyse des matériaux et de l'état général..."):
            audit = analyser_travaux_photo(img)
            b_m2 = re.search(r'\[BUDGET_M2:\s*(\d+)\]', audit)
            if b_m2: st.session_state.ai_budget_m2 = int(b_m2.group(1))
            col_t.markdown("### Rapport Travaux")
            col_t.write(re.sub(r'\[.*?\]', '', audit))

st.markdown("---")

# ==========================================
# ÉTAPE 3 : MODÉLISATION FINANCIÈRE
# ==========================================
st.header(f"💰 Simulation : {mode}")

col_a, col_b = st.columns(2)

with col_a:
    st.subheader("Données de base")
    surface = st.number_input("Surface totale (m²)", value=50, min_value=1)
    prix_bien = st.number_input("Prix d'acquisition (€)", value=100000)
    
    # Intégration intelligente du prix de revente / loyer
    if mode == "Investissement Locatif":
        loyer_estime = st.session_state.ai_loyer_m2 * surface
        if loyer_estime > 0:
            st.info(f"L'IA suggère un loyer de {loyer_estime}€ ({st.session_state.ai_loyer_m2}€/m²)")
            opt_loyer = st.checkbox("Utiliser l'estimation de loyer IA")
            val_loyer = float(loyer_estime) if opt_loyer else 500.0
        else:
            val_loyer = 500.0
        loyer_final = st.number_input("Loyer mensuel HC (€)", value=val_loyer)
    else:
        revente_estime = st.session_state.ai_prix_m2 * surface
        if revente_estime > 0:
            st.info(f"L'IA suggère une revente à {revente_estime}€ ({st.session_state.ai_prix_m2}€/m²)")
            opt_rev = st.checkbox("Utiliser l'estimation de revente IA")
            val_rev = float(revente_estime) if opt_rev else 150000.0
        else:
            val_rev = 150000.0
        revente_final = st.number_input("Prix de revente estimé (€)", value=val_rev)

with col_b:
    st.subheader("Travaux & Frais")
    # Intégration intelligente du budget travaux
    travaux_estime = st.session_state.ai_budget_m2 * surface
    if travaux_estime > 0:
        st.info(f"L'IA estime les travaux à {travaux_estime}€ ({st.session_state.ai_budget_m2}€/m²)")
        opt_trav = st.checkbox("Appliquer l'enveloppe travaux IA")
        val_trav = float(travaux_estime) if opt_trav else 0.0
    else:
        val_trav = 0.0
    
    travaux_final = st.number_input("Budget travaux global (€)", value=val_trav)
    notaire = st.number_input("Frais de notaire (%)", value=8.5 if mode=="Investissement Locatif" else 2.5)
    apport = st.number_input("Apport personnel (€)", value=10000)
    duree = st.number_input("Durée crédit (ans)", value=20)
    taux = st.number_input("Taux d'intérêt (%)", value=3.5)

# CALCULS FINAUX
frais_notaire = prix_bien * (notaire / 100)
investissement_total = prix_bien + frais_notaire + travaux_final
montant_emprunt = max(0, investissement_total - apport)
mensualite = calculer_mensualite(montant_emprunt, taux, duree)

st.markdown("### 📊 Résultats")
k1, k2, k3 = st.columns(3)

if mode == "Investissement Locatif":
    renta_brute = ((loyer_final * 12) / investissement_total) * 100 if investissement_total > 0 else 0
    cash_flow = loyer_final - mensualite - (loyer_final * 0.2) # Estimation 20% charges/taxes
    k1.metric("Investissement Total", f"{investissement_total:,.0f} €")
    k2.metric("Rentabilité Brute", f"{renta_brute:.2f} %")
    k3.metric("Cash-Flow (est.)", f"{cash_flow:,.0f} € / mois")
else:
    marge = revente_final - investissement_total
    roi = (marge / investissement_total) * 100 if investissement_total > 0 else 0
    k1.metric("Prix de Revient", f"{investissement_total:,.0f} €")
    k2.metric("Marge Brute", f"{marge:,.0f} €")
    k3.metric("Rentabilité (ROI)", f"{roi:.1f} %")

# Graphique de répartition
labels = ['Achat', 'Travaux', 'Notaire']
values = [prix_bien, travaux_final, frais_notaire]
fig = px.pie(names=labels, values=values, title="Répartition du capital engagé", hole=0.4)
st.plotly_chart(fig, use_container_width=True)

# Diagnostic discret en bas
with st.expander("Diagnostic Technique"):
    st.write(f"Mémoire IA - Travaux: {st.session_state.ai_budget_m2}€/m²")
    st.write(f"Mémoire IA - Prix: {st.session_state.ai_prix_m2}€/m²")
    st.write(f"Mémoire IA - Loyer: {st.session_state.ai_loyer_m2}€/m²")
