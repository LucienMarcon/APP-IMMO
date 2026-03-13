import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import google.generativeai as genai
from PIL import Image

# --- CONFIGURATION DE L'IA (GEMINI) ---
# Sur Streamlit Cloud, on utilisera st.secrets pour la sécurité
if "GEMINI_API_KEY" in st.secrets:
    API_KEY = st.secrets["GEMINI_API_KEY"]
else:
    API_KEY = "AIzaSyBWSlYPySBaUiQ9h6quYFXbEiDLBJwiuBQ" # À remplacer pour vos tests locaux

genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash-latest')

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(layout="wide", page_title="Immo Invest Pro", page_icon="🏢")

# --- FONCTION D'ANALYSE D'IMAGE ---
def analyser_travaux_photo(image):
    prompt = """
    Agis comme un expert en rénovation de bâtiments (maître d'œuvre). 
    Analyse cette photo de bien immobilier (intérieur ou extérieur).
    1. Identifie les travaux visibles (sols, murs, électricité apparente, plomberie, menuiseries, etc.).
    2. Donne une estimation rapide du budget de rénovation au m² pour ce que tu vois.
    3. Conclue par un montant total estimé des travaux si la surface est de 50m² (pour donner un ordre d'idée).
    Réponds de manière concise et professionnelle.
    """
    response = model.generate_content([prompt, image])
    return response.text

# --- FONCTION DE CALCUL DE PRÊT ---
def calculer_mensualite(montant_emprunte, taux_annuel, annees):
    if montant_emprunte <= 0 or annees <= 0: return 0.0
    taux_mensuel = (taux_annuel / 100) / 12
    nombre_mois = annees * 12
    if taux_mensuel == 0: return montant_emprunte / nombre_mois
    return montant_emprunte * (taux_mensuel * (1 + taux_mensuel)**nombre_mois) / ((1 + taux_mensuel)**nombre_mois - 1)

# --- BARRE LATÉRALE (MENU) ---
st.sidebar.title("Navigation 🧭")
mode = st.sidebar.radio("Stratégie :", ["📊 Investissement Locatif", "🔨 Marchand de Biens"])

# ==========================================
# SECTION ANALYSE PHOTO (COMMUNE)
# ==========================================
st.title("📸 Analyse IA Vision")
uploaded_file = st.file_uploader("Déposez une photo du bien (salon, façade, cuisine...) pour estimer les travaux", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, caption="Photo importée", width=400)
    
    if st.button("Lancer l'analyse par l'IA ✨"):
        with st.spinner("L'IA examine la photo..."):
            try:
                resultat = analyser_travaux_photo(image)
                st.info(resultat)
            except Exception as e:
                st.error(f"Erreur d'analyse : {e}")

st.markdown("---")

# ==========================================
# RESTE DU CODE (LOGIQUE FINANCIÈRE)
# ==========================================
if mode == "📊 Investissement Locatif":
    st.subheader("📊 Simulation Financière : Locatif")
    col1, col2 = st.columns(2)
    with col1:
        prix_affiche = st.number_input("Prix affiché (€)", value=30000)
        surface = st.number_input("Surface (m²)", value=20)
        loyer = st.number_input("Loyer mensuel (€)", value=300)
    with col2:
        # L'utilisateur peut ici taper le budget suggéré par l'IA au-dessus
        budget_travaux = st.number_input("Budget travaux estimé (€)", value=5000)
        apport = st.number_input("Apport (€)", value=0)
        duree = st.number_input("Durée prêt (ans)", value=15)

    # ... (les calculs de renta du code précédent restent les mêmes ici)
    frais_notaire = prix_affiche * 0.085
    total_acq = prix_affiche + frais_notaire + budget_travaux
    mensu = calculer_mensualite(max(0, total_acq - apport), 3.5, duree)
    st.metric("Mensualité estimée", f"{mensu:.2f} €")
    st.metric("Cash-flow", f"{loyer - mensu - 50:.2f} € (estimé)") # -50€ de charges fictives

# (Idem pour la section Marchand de biens...)
