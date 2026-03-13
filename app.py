import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import google.generativeai as genai
from PIL import Image
import requests
import re
import pandas as pd

# ==========================================
# 1. CONFIGURATION ET MÉMOIRE (SESSION STATE)
# ==========================================
st.set_page_config(layout="wide", page_title="ImmoInvest Pro", page_icon="🏢")

# Initialisation de la mémoire
if "ai_budget_m2" not in st.session_state: st.session_state.ai_budget_m2 = 0
if "ai_prix_m2" not in st.session_state: st.session_state.ai_prix_m2 = 0
if "ai_loyer_m2" not in st.session_state: st.session_state.ai_loyer_m2 = 0

# Nouvelles métriques IA Mémorisées
if "ai_tension_locative" not in st.session_state: st.session_state.ai_tension_locative = ""
if "ai_taux_vacance" not in st.session_state: st.session_state.ai_taux_vacance = 0
if "ai_type_locataires" not in st.session_state: st.session_state.ai_type_locataires = ""
if "ai_risque_marche" not in st.session_state: st.session_state.ai_risque_marche = ""
if "ai_etat_general" not in st.session_state: st.session_state.ai_etat_general = ""
if "ai_dpe_probable" not in st.session_state: st.session_state.ai_dpe_probable = ""
if "ai_type_renovation" not in st.session_state: st.session_state.ai_type_renovation = ""

if "rapport_marche" not in st.session_state: st.session_state.rapport_marche = ""
if "rapport_travaux" not in st.session_state: st.session_state.rapport_travaux = ""
if "is_pro_active" not in st.session_state: st.session_state.is_pro_active = False
if "last_tested_key" not in st.session_state: st.session_state.last_tested_key = ""

# CSS Personnalisé
st.markdown("""
    <style>
    .main {background-color: #F8FAFC;}
    .stMetric {background-color: #ffffff; padding: 15px; border-radius: 10px; border: 1px solid #E2E8F0; box-shadow: 0 1px 3px rgba(0,0,0,0.1);}
    div.stButton > button:first-child { background-color: #0F172A; color: white; border-radius: 8px; width: 100%; height: 3.5em; font-weight: 600; }
    div.stButton > button:hover {background-color: #334155; border: none;}
    .stExpander {background-color: white; border-radius: 10px;}
    h1 {color: #1E293B; font-weight: 800; border-bottom: 2px solid #E2E8F0; padding-bottom: 10px; margin-top: 30px;}
    h2, h3 {color: #1E293B; font-weight: 700;}
    .score-box {text-align: center; padding: 20px; border-radius: 15px; color: white; font-size: 24px; font-weight: bold;}
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. GESTION DES CLÉS API ET QUOTAS
# ==========================================
st.sidebar.title("🏢 ImmoInvest Pro")
st.sidebar.markdown("---")
st.sidebar.subheader("🔑 Paramètres API")

user_key = st.sidebar.text_input("Votre clé API personnelle (Optionnel) :", type="password", help="Ajoutez votre clé pour utiliser vos propres quotas.")

is_user_key = bool(user_key)
API_KEY = user_key if is_user_key else st.secrets.get("GEMINI_API_KEY", "")

if API_KEY:
    genai.configure(api_key=API_KEY)
    
    if API_KEY != st.session_state.last_tested_key:
        try:
            tmp_model = genai.GenerativeModel('gemini-2.5-pro')
            tmp_model.generate_content("ping", generation_config={"max_output_tokens": 1})
            st.session_state.is_pro_active = True
        except Exception:
            st.session_state.is_pro_active = False
        st.session_state.last_tested_key = API_KEY

    if is_user_key:
        if st.session_state.is_pro_active: st.sidebar.success("✅ **Clé personnelle validée**\n\n🚀 Quotas PRO (Recherche Web active)")
        else: st.sidebar.warning("⚠️ **Clé personnelle validée**\n\n🐢 Quota PRO épuisé (Mode ÉCO actif)")
    else:
        if st.session_state.is_pro_active: st.sidebar.success("🌍 **Clé partagée active**\n\n🚀 Mode PRO disponible")
        else: st.sidebar.warning("🌍 **Clé partagée active**\n\n🐢 Quota partagé épuisé (Mode ÉCO actif)")
else:
    st.sidebar.error("❌ Aucune clé API détectée.")

# ==========================================
# 3. FONCTIONS UTILES & CACHE (PERFORMANCE)
# ==========================================

def extraire_nombre(texte, balise):
    pattern = rf"\[{balise}:\s*(\d+)\]"
    match = re.search(pattern, texte)
    return int(match.group(1)) if match else 0

def extraire_texte(texte, balise):
    pattern = rf"\[{balise}:\s*(.*?)\]"
    match = re.search(pattern, texte)
    return match.group(1).strip() if match else "Non spécifié"

@st.cache_data(show_spinner=False, ttl=3600)
def analyser_marche_local_cached(ville, cp, is_pro, _api_key):
    genai.configure(api_key=_api_key)
    prompt = f"""Analyse précise du marché immobilier à {ville} ({cp}). 
    Donne le prix m² moyen de vente et le loyer m² moyen HC.
    Ajoute les informations suivantes : tension locative, taux de vacance, type de locataires, niveau de risque marché.
    FINIS PAR CES BALISES STRICTEMENT : 
    [PRIX_M2: XXX] 
    [LOYER_M2: YYY]
    [TENSION_LOCATIVE: ZZZ] (Forte, Moyenne ou Faible)
    [TAUX_VACANCE: XX] (Uniquement le nombre entier)
    [TYPE_LOCATAIRES: ZZZ]
    [RISQUE_MARCHE: ZZZ] (Faible, Moyen ou Fort)"""
    try:
        if is_pro:
            model = genai.GenerativeModel('gemini-2.5-pro')
            res = model.generate_content(prompt, tools=[{'google_search_retrieval': {}}])
        else:
            model = genai.GenerativeModel('gemini-2.5-flash')
            res = model.generate_content(prompt)
        return res.text
    except Exception as e:
        return f"Erreur de quota. [PRIX_M2: 2500] [LOYER_M2: 12] [TENSION_LOCATIVE: Moyenne] [TAUX_VACANCE: 5] [TYPE_LOCATAIRES: Mixte] [RISQUE_MARCHE: Moyen]"

@st.cache_data(show_spinner=False, ttl=3600)
def analyser_travaux_photo_cached(_image, _api_key):
    genai.configure(api_key=_api_key)
    model = genai.GenerativeModel('gemini-2.5-flash')
    prompt = """Tu es maître d'œuvre. Analyse l'état et les matériaux sur cette photo.
    Détaille les rénovations à prévoir, l'état général, le DPE probable et le type de rénovation.
    Donne une estimation au m².
    FINIS PAR CES BALISES STRICTEMENT : 
    [BUDGET_M2: XXX] 
    [ETAT_GENERAL: YYY] 
    [DPE_PROBABLE: ZZZ] (Une lettre de A à G)
    [TYPE_RENOVATION: WWW] (Léger, Rafraîchissement, Lourd, Total)"""
    res = model.generate_content([prompt, _image])
    return res.text

def calculer_mensualite(capital, taux, annees):
    if capital <= 0 or annees <= 0: return 0.0
    tm = (taux / 100) / 12
    n = annees * 12
    if tm == 0: return capital / n
    return capital * (tm * (1 + tm)**n) / ((1 + tm)**n - 1)

def calculer_crd(capital, taux, annees, annee_cible):
    """Calcule le Capital Restant Dû à une année donnée"""
    if annee_cible == 0: return capital
    if annee_cible >= annees: return 0.0
    tm = (taux / 100) / 12
    n = annees * 12
    p = annee_cible * 12
    if tm == 0: return capital - (capital / n) * p
    return capital * ((1 + tm)**n - (1 + tm)**p) / ((1 + tm)**n - 1)

# ==========================================
# INTERFACE PRINCIPALE
# ==========================================
mode = st.sidebar.radio("Stratégie d'investissement :", ["Investissement Locatif", "Marchand de Biens"])

# ==========================================
# BLOC 1 : LOCALISATION & ANALYSE MARCHÉ
# ==========================================
st.markdown("<h1>1️⃣ Localisation & Analyse de Marché</h1>", unsafe_allow_html=True)

addr_query = st.text_input("Commencez à taper une adresse ou une ville...", placeholder="Ex: 15 rue de Rivoli, Paris")

if len(addr_query) > 3:
    url_ban = f"https://api-adresse.data.gouv.fr/search/?q={addr_query}&limit=5"
    data_ban = requests.get(url_ban).json()
    if data_ban['features']:
        adresses_dict = {f["properties"]["label"]: f["properties"] for f in data_ban['features']}
        choix = st.selectbox("Sélectionnez l'adresse exacte :", adresses_dict.keys())
        
        info = adresses_dict[choix]
        ville, cp = info['city'], info['postcode']
        st.success(f"📍 Bien localisé : **{ville} ({cp})**")
        
        if st.button("📊 Lancer l'analyse du marché local (IA)"):
            with st.spinner(f"L'IA étudie les données immobilières de {ville}..."):
                rapport = analyser_marche_local_cached(ville, cp, st.session_state.is_pro_active, API_KEY)
                st.session_state.rapport_marche = rapport
                st.session_state.ai_prix_m2 = extraire_nombre(rapport, "PRIX_M2")
                st.session_state.ai_loyer_m2 = extraire_nombre(rapport, "LOYER_M2")
                st.session_state.ai_tension_locative = extraire_texte(rapport, "TENSION_LOCATIVE")
                st.session_state.ai_taux_vacance = extraire_nombre(rapport, "TAUX_VACANCE")
                st.session_state.ai_type_locataires = extraire_texte(rapport, "TYPE_LOCATAIRES")
                st.session_state.ai_risque_marche = extraire_texte(rapport, "RISQUE_MARCHE")
                st.rerun()

if st.session_state.rapport_marche:
    st.info(f"💡 **Data IA** : Tension **{st.session_state.ai_tension_locative}** | Risque **{st.session_state.ai_risque_marche}** | Locataires : **{st.session_state.ai_type_locataires}** | Vacance est. : **{st.session_state.ai_taux_vacance}%**")
    with st.expander("📄 Voir l'analyse détaillée du quartier", expanded=False):
        st.write(re.sub(r'\[.*?\]', '', st.session_state.rapport_marche))

# ==========================================
# BLOC 2 : EXPERTISE TRAVAUX
# ==========================================
st.markdown("<h1>2️⃣ Expertise Travaux par Vision</h1>", unsafe_allow_html=True)
photo = st.file_uploader("Importez une photo de l'annonce :", type=["jpg", "jpeg", "png"])

if photo:
    img = Image.open(photo)
    col_img, col_btn = st.columns([1, 2])
    col_img.image(img, use_container_width=True)
    
    if col_btn.button("✨ Estimer le montant des travaux"):
        with st.spinner("Analyse visuelle des finitions..."):
            rapport_t = analyser_travaux_photo_cached(img, API_KEY)
            st.session_state.rapport_travaux = rapport_t
            st.session_state.ai_budget_m2 = extraire_nombre(rapport_t, "BUDGET_M2")
            st.session_state.ai_etat_general = extraire_texte(rapport_t, "ETAT_GENERAL")
            st.session_state.ai_dpe_probable = extraire_texte(rapport_t, "DPE_PROBABLE")
            st.session_state.ai_type_renovation = extraire_texte(rapport_t, "TYPE_RENOVATION")
            st.rerun()

if st.session_state.rapport_travaux:
    st.warning(f"🔧 **Bilan IA** : État **{st.session_state.ai_etat_general}** | Rénovation **{st.session_state.ai_type_renovation}** | DPE probable : **{st.session_state.ai_dpe_probable}**")
    with st.expander("🔨 Détails des travaux estimés", expanded=False):
        st.write(re.sub(r'\[.*?\]', '', st.session_state.rapport_travaux))

# ==========================================
# BLOC 3 : SIMULATION FINANCIÈRE
# ==========================================
st.markdown(f"<h1>3️⃣ Simulation Financière ({mode})</h1>", unsafe_allow_html=True)

c1, c2 = st.columns(2)

with c1:
    st.subheader("Acquisition")
    surface = st.number_input("Surface du bien (m²)", value=50, step=1)
    prix_achat = st.number_input("Prix d'achat net vendeur (€)", value=100000, step=1000)
    
    # Détection Bonne Affaire
    prix_m2_achat = prix_achat / surface if surface > 0 else 0
    if st.session_state.ai_prix_m2 > 0:
        ecart = (prix_m2_achat - st.session_state.ai_prix_m2) / st.session_state.ai_prix_m2
        if ecart < -0.05: st.success(f"✅ **Excellente affaire !** Sous le marché de {abs(ecart)*100:.1f}%")
        elif ecart > 0.05: st.error(f"⚠️ **Bien surévalué !** Au-dessus du marché de {ecart*100:.1f}%")
        else: st.info("⚖️ **Bien au prix du marché.**")
    
    if mode == "Investissement Locatif":
        loyer_ia_tot = float(st.session_state.ai_loyer_m2 * surface)
        use_loyer_ia = st.checkbox(f"Appliquer Loyer IA ({loyer_ia_tot}€)", value=(loyer_ia_tot > 0))
        loyer_final = st.number_input("Loyer mensuel HC (€)", value=loyer_ia_tot if use_loyer_ia else 500.0)
    else:
        revente_ia_tot = float(st.session_state.ai_prix_m2 * surface)
        use_revente_ia = st.checkbox(f"Appliquer Revente IA ({revente_ia_tot}€)", value=(revente_ia_tot > 0))
        revente_final = st.number_input("Prix de revente estimé (€)", value=revente_ia_tot if use_revente_ia else 160000.0)

with c2:
    st.subheader("Chantier & Prêt")
    trav_ia_tot = float(st.session_state.ai_budget_m2 * surface)
    use_trav_ia = st.checkbox(f"Appliquer Travaux IA ({trav_ia_tot}€)", value=(trav_ia_tot > 0))
    trav_final = st.number_input("Budget travaux total (€)", value=trav_ia_tot if use_trav_ia else 0.0)
    
    apport = st.number_input("Apport personnel (€)", value=10000)
    duree = st.number_input("Durée du prêt (ans)", value=20)
    taux = st.number_input("Taux d'intérêt (%)", value=3.5, step=0.1)
    notaire = st.number_input("Frais de notaire (%)", value=8.5 if mode == "Investissement Locatif" else 2.5)

# ==========================================
# BLOC 4 & 5 : CHARGES & FISCALITÉ (Uniquement Locatif)
# ==========================================
if mode == "Investissement Locatif":
    col_ch, col_fisc = st.columns(2)
    
    with col_ch:
        st.markdown("<h1>4️⃣ Charges d'Exploitation</h1>", unsafe_allow_html=True)
        taxe_fonciere = st.number_input("Taxe foncière annuelle (€)", value=800)
        charges_non_recup = st.number_input("Charges de copro non récupérables (€/an)", value=600)
        assurance_pno = st.number_input("Assurance PNO (€/an)", value=150)
        entretien_annuel = st.number_input("Entretien annuel (€)", value=int(prix_achat*0.01), help="Généralement 1% du prix")
        gestion_locative = st.number_input("Frais de gestion locative (%)", value=0.0)
        vacance_locative = st.number_input("Vacance locative anticipée (%)", value=float(st.session_state.ai_taux_vacance) if st.session_state.ai_taux_vacance else 5.0)

    with col_fisc:
        st.markdown("<h1>5️⃣ Fiscalité</h1>", unsafe_allow_html=True)
        regime_fiscal = st.selectbox("Régime fiscal", ["Micro foncier", "Réel foncier", "LMNP (Amortissement)", "SCI à l'IS"])
        tmi = st.selectbox("Taux Marginal d'Imposition (TMI)", [0, 11, 30, 41, 45], index=2)

# ==========================================
# CALCULS GLOBAUX
# ==========================================
frais_notaire = prix_achat * (notaire / 100)
total_projet = prix_achat + frais_notaire + trav_final
capital_emprunte = max(0, total_projet - apport)
mensualite = calculer_mensualite(capital_emprunte, taux, duree)
credit_annuel = mensualite * 12

if mode == "Investissement Locatif":
    revenus_bruts_annuels = loyer_final * 12
    revenus_effectifs = revenus_bruts_annuels * (1 - vacance_locative/100)
    charges_annuelles = taxe_fonciere + charges_non_recup + assurance_pno + entretien_annuel + (revenus_effectifs * gestion_locative/100)
    
    interets_an1 = capital_emprunte * (taux / 100)
    
    # Calcul Impôt (Simplifié Année 1)
    base_imposable = 0
    if regime_fiscal == "Micro foncier":
        base_imposable = revenus_effectifs * 0.70
        impot_annuel = base_imposable * ((tmi + 17.2) / 100)
    elif regime_fiscal == "Réel foncier":
        base_imposable = max(0, revenus_effectifs - charges_annuelles - interets_an1)
        impot_annuel = base_imposable * ((tmi + 17.2) / 100)
    elif regime_fiscal == "LMNP (Amortissement)":
        impot_annuel = 0 # Simplification: amortissement gomme l'impôt
    elif regime_fiscal == "SCI à l'IS":
        amortissement_comptable = prix_achat * 0.03
        base_imposable = max(0, revenus_effectifs - charges_annuelles - interets_an1 - amortissement_comptable)
        impot_annuel = base_imposable * 0.15 # Taux réduit IS

    cash_flow_net_annuel = revenus_effectifs - charges_annuelles - credit_annuel - impot_annuel
    cash_flow_net_mensuel = cash_flow_net_annuel / 12
    
    renta_brute = (revenus_bruts_annuels / total_projet) * 100 if total_projet > 0 else 0
    renta_nette = ((revenus_effectifs - charges_annuelles) / total_projet) * 100 if total_projet > 0 else 0
    renta_nette_nette = ((revenus_effectifs - charges_annuelles - impot_annuel) / total_projet) * 100 if total_projet > 0 else 0

# ==========================================
# BLOC 6 : SYNTHÈSE & SCORE
# ==========================================
st.markdown("<h1>6️⃣ Synthèse & Score d'Investissement</h1>", unsafe_allow_html=True)

if mode == "Investissement Locatif":
    # Calcul du Score (/100)
    score = 0
    score += min(20, max(0, renta_nette * 2.5)) # 8% net = 20 pts
    score += min(20, max(0, (cash_flow_net_mensuel + 100) / 10)) # 100€ CF = 20 pts
    score += 20 if st.session_state.ai_tension_locative == "Forte" else (10 if st.session_state.ai_tension_locative == "Moyenne" else 0)
    ecart_prix = ((st.session_state.ai_prix_m2 - prix_m2_achat) / prix_m2_achat) * 100 if prix_m2_achat > 0 and st.session_state.ai_prix_m2 > 0 else 0
    score += min(20, max(0, ecart_prix * 2)) # 10% sous le marché = 20 pts
    score += 20 if st.session_state.ai_risque_marche == "Faible" else (10 if st.session_state.ai_risque_marche == "Moyen" else 0)
    
    color = "#10B981" if score >= 75 else ("#F59E0B" if score >= 50 else "#EF4444")
    
    c_score, c_kpi = st.columns([1, 2])
    with c_score:
        st.markdown(f"<div class='score-box' style='background-color: {color};'>Score Investissement<br><span style='font-size: 48px;'>{int(score)}/100</span></div>", unsafe_allow_html=True)
    
    with c_kpi:
        r1, r2, r3, r4 = st.columns(4)
        r1.metric("Rendement Brut", f"{renta_brute:.2f} %")
        r2.metric("Rendement Net", f"{renta_nette:.2f} %")
        r3.metric("Rendement Net Net", f"{renta_nette_nette:.2f} %")
        r4.metric("Cash-Flow Net/mois", f"{cash_flow_net_mensuel:,.0f} €")
else:
    marge = revente_final - total_projet
    roi = (marge / total_projet) * 100 if total_projet > 0 else 0
    r1, r2, r3 = st.columns(3)
    r1.metric("Prix de Revient", f"{total_projet:,.0f} €")
    r2.metric("Marge Brute", f"{marge:,.0f} €")
    r3.metric("Rentabilité (ROI)", f"{roi:.1f} %")

# Graphique de répartition du capital (Original conservé)
fig_pie = px.pie(
    names=['Prix Achat', 'Travaux', 'Notaire'], 
    values=[prix_achat, trav_final, frais_notaire],
    title="Répartition du capital engagé",
    hole=0.4,
    color_discrete_sequence=['#0F172A', '#334155', '#94A3B8']
)
st.plotly_chart(fig_pie, use_container_width=True)

# ==========================================
# BLOC 7 : PROJECTION FINANCIÈRE À 10 ANS
# ==========================================
if mode == "Investissement Locatif":
    st.markdown("<h1>7️⃣ Projection Financière (10 ans)</h1>", unsafe_allow_html=True)
    
    col_p1, col_p2 = st.columns([1, 3])
    with col_p1:
        duree_detention = st.slider("Durée de projection (Années)", 5, 20, 10)
        revalo_bien = st.number_input("Revalorisation annuelle du bien (%)", value=1.0, step=0.1)
        revalo_loyer = st.number_input("Revalorisation annuelle des loyers (%)", value=1.0, step=0.1)
    
    # Génération des données sur X années
    annees_liste = list(range(0, duree_detention + 1))
    valeurs_bien = []
    crds = []
    patrimoines = []
    cashflows_cumules = []
    
    cf_cumul = 0
    for annee in annees_liste:
        val_bien = (prix_achat + trav_final) * ((1 + revalo_bien/100)**annee)
        crd = calculer_crd(capital_emprunte, taux, duree, annee)
        
        if annee > 0:
            loyer_annee = revenus_effectifs * ((1 + revalo_loyer/100)**annee)
            cf_annee = loyer_annee - charges_annuelles - credit_annuel - impot_annuel
            cf_cumul += cf_annee
            
        valeurs_bien.append(val_bien)
        crds.append(crd)
        cashflows_cumules.append(cf_cumul)
        patrimoines.append(val_bien - crd + cf_cumul)

    df_proj = pd.DataFrame({
        "Année": annees_liste,
        "Valeur du Bien": valeurs_bien,
        "Capital Restant Dû": crds,
        "Patrimoine Net": patrimoines
    })

    with col_p2:
        fig_proj = px.line(df_proj, x="Année", y=["Valeur du Bien", "Capital Restant Dû", "Patrimoine Net"],
                           title="Évolution de la création de richesse",
                           labels={"value": "Montant (€)", "variable": "Indicateur"},
                           color_discrete_map={"Valeur du Bien": "#3B82F6", "Capital Restant Dû": "#EF4444", "Patrimoine Net": "#10B981"})
        fig_proj.update_layout(hovermode="x unified")
        st.plotly_chart(fig_proj, use_container_width=True)
        
    s1, s2, s3 = st.columns(3)
    s1.metric(f"Valeur à {duree_detention} ans", f"{valeurs_bien[-1]:,.0f} €")
    s2.metric("Capital remboursé", f"{capital_emprunte - crds[-1]:,.0f} €")
    s3.metric("Patrimoine Net Final", f"{patrimoines[-1]:,.0f} €")

# Diagnostic caché pour debug
with st.expander("🛠️ Diagnostic Technique (Debug)"):
    st.write(f"Clé Testée: {st.session_state.last_tested_key[:10]}...")
    st.write(f"Tension Loc: {st.session_state.ai_tension_locative}")
