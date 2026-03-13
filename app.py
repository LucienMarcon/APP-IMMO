import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import google.generativeai as genai
from PIL import Image
import re

# --- INITIALISATION DE LA MÉMOIRE (SESSION STATE) ---
if "ai_budget_m2" not in st.session_state:
    st.session_state.ai_budget_m2 = 0

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(layout="wide", page_title="ImmoInvest Pro", page_icon="🏢", initial_sidebar_state="expanded")

# --- STYLE CSS PERSONNALISÉ (Pour un look "Lovable" et épuré) ---
st.markdown("""
    <style>
    .main {background-color: #FAFAFA;}
    h1, h2, h3 {color: #1E293B; font-weight: 600;}
    .stButton>button {background-color: #0F172A; color: white; border-radius: 6px; padding: 0.5rem 1rem;}
    .stButton>button:hover {background-color: #334155; color: white;}
    .block-container {padding-top: 2rem;}
    </style>
""", unsafe_allow_html=True)

# --- CONFIGURATION DE L'API ---
if "GEMINI_API_KEY" in st.secrets:
    API_KEY = st.secrets["GEMINI_API_KEY"]
else:
    API_KEY = "CLE_NON_TROUVEE"

genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash')

# --- FONCTIONS ---
def analyser_travaux_photo(image):
    prompt = """
    Tu es un expert en rénovation immobilière. Analyse cette photo avec un ton professionnel et neutre.
    1. Détaille l'état actuel (sols, murs, équipements visibles).
    2. Liste les travaux nécessaires pour une remise à neuf qualitative.
    3. À la toute fin de ta réponse, tu DOIS inclure une estimation du coût des travaux au mètre carré en utilisant EXACTEMENT ce format : [BUDGET_M2: 500] (remplace 500 par ton estimation haute en euros).
    """
    response = model.generate_content([prompt, image])
    return response.text

def calculer_mensualite(montant_emprunte, taux_annuel, annees):
    if montant_emprunte <= 0 or annees <= 0: return 0.0
    taux_mensuel = (taux_annuel / 100) / 12
    nombre_mois = annees * 12
    if taux_mensuel == 0: return montant_emprunte / nombre_mois
    return montant_emprunte * (taux_mensuel * (1 + taux_mensuel)**nombre_mois) / ((1 + taux_mensuel)**nombre_mois - 1)

# --- BARRE LATÉRALE ---
st.sidebar.markdown("## ImmoInvest Pro")
st.sidebar.markdown("Plateforme d'analyse de rentabilité")
mode = st.sidebar.radio("Type de projet :", ["Investissement Locatif", "Marchand de Biens (Achat/Revente)"])

with st.sidebar.expander("Paramètres techniques"):
    st.write("Statut API : Connectée")
    st.write("Modèle : Vision 2.5")

# --- CORPS DE L'APPLICATION ---
st.title(mode)
st.markdown("---")

# ==========================================
# MODULE : ANALYSE VISUELLE
# ==========================================
st.subheader("1. Analyse de l'existant")
uploaded_file = st.file_uploader("Importez une photographie de l'annonce pour estimer l'enveloppe de travaux", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    col_img, col_txt = st.columns([1, 2])
    
    with col_img:
        st.image(image, use_container_width=True)
    
    with col_txt:
        if st.button("Générer l'audit visuel"):
            with st.spinner("Analyse de la structure et des finitions en cours..."):
                try:
                    resultat = analyser_travaux_photo(image)
                    
                    # Extraction du budget via Regex
                    match = re.search(r'\[BUDGET_M2:\s*(\d+)\]', resultat)
                    if match:
                        st.session_state.ai_budget_m2 = int(match.group(1))
                        # Nettoyer le texte pour ne pas afficher la balise technique à l'utilisateur
                        resultat_propre = re.sub(r'\[BUDGET_M2:\s*\d+\]', '', resultat)
                    else:
                        st.session_state.ai_budget_m2 = 0
                        resultat_propre = resultat
                        
                    st.markdown("### Rapport d'expertise")
                    st.write(resultat_propre.strip())
                    
                except Exception as e:
                    st.error("L'analyse a échoué. Veuillez réessayer.")

st.markdown("---")

# ==========================================
# MODULE : MODÉLISATION FINANCIÈRE
# ==========================================
st.subheader("2. Modélisation financière")

if mode == "Investissement Locatif":
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Acquisition & Rendement**")
        prix_affiche = st.number_input("Prix affiché (€)", value=100000, step=5000)
        surface = st.number_input("Surface (m²)", value=40, step=1)
        loyer_mensuel = st.number_input("Loyer hors charges espéré (€/mois)", value=600, step=50)
        charges_annuelles = st.number_input("Charges de copropriété (annuel)", value=800, step=50)
        taxe_fonciere = st.number_input("Taxe foncière", value=600, step=50)
        
    with col2:
        st.markdown("**Travaux & Financement**")
        
        # Logique de connexion intelligente du budget
        budget_suggere = st.session_state.ai_budget_m2 * surface
        if budget_suggere > 0:
            st.info(f"💡 Audit : Un coût de {st.session_state.ai_budget_m2} €/m² a été identifié.")
            utiliser_ia = st.checkbox("Intégrer automatiquement cette estimation", value=False)
        else:
            utiliser_ia = False
            
        if utiliser_ia:
            budget_travaux = st.number_input("Budget travaux (€)", value=float(budget_suggere), disabled=True)
        else:
            budget_travaux = st.number_input("Budget travaux (€)", value=0.0, step=1000.0)

        taux_notaire = st.number_input("Frais d'acquisition (%)", value=8.5, step=0.1)
        apport = st.number_input("Apport personnel (€)", value=0, step=1000)
        taux_emprunt = st.number_input("Taux d'emprunt (%)", value=3.5, step=0.1)
        duree = st.number_input("Durée (années)", value=20, step=1)

    # Calculs Locatif
    frais_notaire = prix_affiche * (taux_notaire / 100)
    prix_total = prix_affiche + frais_notaire + budget_travaux
    montant_emprunte = max(0, prix_total - apport)
    mensualite = calculer_mensualite(montant_emprunte, taux_emprunt, duree)
    loyer_annuel = loyer_mensuel * 12
    
    renta_brute = (loyer_annuel / prix_total) * 100 if prix_total > 0 else 0
    renta_nette = ((loyer_annuel - charges_annuelles - taxe_fonciere) / prix_total) * 100 if prix_total > 0 else 0
    cash_flow = loyer_mensuel - mensualite - (charges_annuelles/12) - (taxe_fonciere/12)

    # Affichage des KPIs
    st.markdown("<br>", unsafe_allow_html=True)
    st.subheader("3. Viabilité du projet")
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    kpi1.metric("Investissement Total", f"{prix_total:,.0f} €".replace(",", " "))
    kpi2.metric("Rentabilité Brute", f"{renta_brute:.1f} %")
    kpi3.metric("Rentabilité Nette", f"{renta_nette:.1f} %")
    kpi4.metric("Cash-flow mensuel", f"{cash_flow:,.0f} €".replace(",", " "))

# ==========================================
# MODE MARCHAND DE BIENS
# ==========================================
else:
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Acquisition**")
        prix_achat = st.number_input("Prix d'achat négocié (€)", value=150000, step=5000)
        surface = st.number_input("Surface (m²)", value=60, step=1)
        taux_notaire_mdb = st.number_input("Frais d'acquisition (%)", value=8.5, step=0.1, help="En MDB, les frais peuvent être réduits à ~2.5%")
        
    with col2:
        st.markdown("**Travaux & Revente**")
        
        # Logique de connexion intelligente du budget
        budget_suggere = st.session_state.ai_budget_m2 * surface
        if budget_suggere > 0:
            st.info(f"💡 Audit : Un coût de {st.session_state.ai_budget_m2} €/m² a été identifié.")
            utiliser_ia = st.checkbox("Intégrer automatiquement cette estimation", value=False)
        else:
            utiliser_ia = False
            
        if utiliser_ia:
            budget_travaux = st.number_input("Budget travaux global (€)", value=float(budget_suggere), disabled=True)
        else:
            budget_travaux = st.number_input("Budget travaux global (€)", value=20000.0, step=1000.0)

        frais_divers = st.number_input("Frais annexes (géomètre, etc.) (€)", value=2500, step=500)
        prix_revente = st.number_input("Prix de revente total estimé (€)", value=230000, step=5000)

    # Calculs MDB
    frais_notaire = prix_achat * (taux_notaire_mdb / 100)
    prt = prix_achat + frais_notaire + budget_travaux + frais_divers
    marge_brute = prix_revente - prt
    roi = (marge_brute / prt) * 100 if prt > 0 else 0

    # Affichage des KPIs
    st.markdown("<br>", unsafe_allow_html=True)
    st.subheader("3. Viabilité de l'opération")
    kpi1, kpi2, kpi3 = st.columns(3)
    kpi1.metric("Prix de Revient (PRT)", f"{prt:,.0f} €".replace(",", " "))
    kpi2.metric("Marge Brute", f"{marge_brute:,.0f} €".replace(",", " "))
    kpi3.metric("Retour sur Investissement", f"{roi:.1f} %")

    # Graphique MDB (Design épuré)
    fig = go.Figure(go.Waterfall(
        name="Flux", orientation="v",
        measure=["relative", "relative", "relative", "relative", "total"],
        x=["Achat", "Notaire", "Travaux & Frais", "Marge", "Revente"],
        y=[prix_achat, frais_notaire, budget_travaux + frais_divers, marge_brute, prix_revente],
        connector={"line": {"color": "#CBD5E1"}},
        decreasing={"marker": {"color": "#EF4444"}},
        increasing={"marker": {"color": "#0F172A"}},
        totals={"marker": {"color": "#10B981"}}
    ))
    fig.update_layout(title="Décomposition de la création de valeur", template="plotly_white", margin=dict(t=50, b=20, l=20, r=20))
    st.plotly_chart(fig, use_container_width=True)
