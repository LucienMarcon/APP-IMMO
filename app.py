import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(layout="wide", page_title="Immo Invest Pro", page_icon="🏢")

# --- FONCTION DE CALCUL DE PRÊT ---
def calculer_mensualite(montant_emprunte, taux_annuel, annees):
    if montant_emprunte <= 0 or annees <= 0:
        return 0.0
    if taux_annuel == 0:
        return montant_emprunte / (annees * 12)
    
    taux_mensuel = (taux_annuel / 100) / 12
    nombre_mois = annees * 12
    mensualite = montant_emprunte * (taux_mensuel * (1 + taux_mensuel)**nombre_mois) / ((1 + taux_mensuel)**nombre_mois - 1)
    return mensualite

# --- BARRE LATÉRALE (MENU) ---
st.sidebar.title("Navigation 🧭")
mode = st.sidebar.radio(
    "Choisissez votre stratégie :",
    ["📊 Investissement Locatif", "🔨 Marchand de Biens"]
)

st.sidebar.markdown("---")
st.sidebar.info("Application d'analyse rapide pour vos projets immobiliers Leboncoin.")

# ==========================================
# MODE : INVESTISSEMENT LOCATIF
# ==========================================
if mode == "📊 Investissement Locatif":
    st.title("📊 Analyse : Investissement Locatif")
    
    # -- Saisie des données --
    with st.expander("📝 Saisie des paramètres du projet", expanded=True):
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("L'Annonce")
            prix_affiche = st.number_input("Prix affiché (€)", min_value=0, value=30240, step=1000)
            surface = st.number_input("Surface (m²)", min_value=1, value=21, step=1)
            loyer_mensuel = st.number_input("Loyer mensuel espéré (€)", min_value=0, value=300, step=10)
            charges_copro = st.number_input("Charges de copro. annuelles (€)", min_value=0, value=300, step=50)
            taxe_fonciere = st.number_input("Taxe foncière annuelle (€)", min_value=0, value=400, step=50)
            
        with col2:
            st.subheader("Financement & Travaux")
            budget_travaux = st.number_input("Budget travaux global (€)", min_value=0, value=3000, step=500)
            taux_notaire = st.number_input("Frais de notaire (%)", min_value=0.0, max_value=15.0, value=8.5, step=0.1)
            apport = st.number_input("Apport personnel (€)", min_value=0, value=0, step=1000)
            taux_emprunt = st.number_input("Taux d'emprunt annuel (%)", min_value=0.0, max_value=10.0, value=3.5, step=0.1)
            duree_pret = st.number_input("Durée du prêt (années)", min_value=1, max_value=30, value=15, step=1)

    # -- Calculs --
    frais_notaire = prix_affiche * (taux_notaire / 100)
    prix_total = prix_affiche + frais_notaire + budget_travaux
    montant_emprunte = max(0, prix_total - apport)
    
    mensualite = calculer_mensualite(montant_emprunte, taux_emprunt, duree_pret)
    loyer_annuel = loyer_mensuel * 12
    
    renta_brute = (loyer_annuel / prix_total) * 100 if prix_total > 0 else 0
    renta_nette = ((loyer_annuel - charges_copro - taxe_fonciere) / prix_total) * 100 if prix_total > 0 else 0
    
    cash_flow_mensuel = loyer_mensuel - mensualite - (charges_copro / 12) - (taxe_fonciere / 12)

    # -- Affichage des Résultats --
    st.markdown("---")
    st.subheader("📈 Résultats de l'analyse")
    
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    kpi1.metric("Coût Total d'Acquisition", f"{prix_total:,.0f} €".replace(",", " "))
    kpi2.metric("Mensualité du Crédit", f"{mensualite:,.0f} €/mois".replace(",", " "))
    kpi3.metric("Rentabilité Brute", f"{renta_brute:.2f} %")
    kpi4.metric("Rentabilité Nette", f"{renta_nette:.2f} %")
    
    # Mise en forme conditionnelle du Cash-Flow
    st.markdown("### Cash-Flow Net Mensuel")
    if cash_flow_mensuel >= 0:
        st.success(f"💰 {cash_flow_mensuel:,.2f} € / mois (Le projet s'autofinance !)")
    else:
        st.error(f"⚠️ {cash_flow_mensuel:,.2f} € / mois (Effort d'épargne requis)")

    # -- Graphique --
    st.markdown("### Répartition de l'investissement")
    labels = ['Prix du bien', 'Frais de Notaire', 'Travaux']
    values = [prix_affiche, frais_notaire, budget_travaux]
    fig = px.pie(names=labels, values=values, hole=0.4, color_discrete_sequence=px.colors.sequential.Teal)
    st.plotly_chart(fig, use_container_width=True)


# ==========================================
# MODE : MARCHAND DE BIENS
# ==========================================
elif mode == "🔨 Marchand de Biens":
    st.title("🔨 Analyse : Marchand de Biens")
    
    # -- Saisie des données --
    with st.expander("📝 Saisie des paramètres du projet", expanded=True):
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("L'Achat")
            prix_achat = st.number_input("Prix d'achat négocié (€)", min_value=0, value=35000, step=1000)
            surface = st.number_input("Surface (m²)", min_value=1, value=66, step=1)
            taux_notaire_mdb = st.number_input("Frais de notaire (%)", min_value=0.0, max_value=15.0, value=8.5, step=0.1, help="En MDB pro, les frais peuvent être réduits (ex: 2.5%).")
            
        with col2:
            st.subheader("Travaux & Revente")
            budget_travaux = st.number_input("Coût total des travaux (€)", min_value=0, value=75000, step=1000)
            frais_divers = st.number_input("Frais annexes (géomètre, archi, etc.) (€)", min_value=0, value=2000, step=500)
            prix_revente_m2 = st.number_input("Prix de revente estimé (€/m²)", min_value=0, value=1800, step=100)

    # -- Calculs --
    frais_notaire = prix_achat * (taux_notaire_mdb / 100)
    prt = prix_achat + frais_notaire + budget_travaux + frais_divers
    ca_revente = prix_revente_m2 * surface
    marge_euros = ca_revente - prt
    marge_pourcent = (marge_euros / prt) * 100 if prt > 0 else 0

    # -- Affichage des Résultats --
    st.markdown("---")
    st.subheader("📈 Viabilité du Projet")
    
    kpi1, kpi2, kpi3 = st.columns(3)
    kpi1.metric("Prix de Revient Total (PRT)", f"{prt:,.0f} €".replace(",", " "))
    kpi2.metric("Chiffre d'Affaires Attendu", f"{ca_revente:,.0f} €".replace(",", " "))
    kpi3.metric("Marge Nette Estimée", f"{marge_euros:,.0f} €".replace(",", " "))
    
    # Analyse de la marge
    if marge_pourcent >= 20:
        st.success(f"🚀 Marge de {marge_pourcent:.1f}% : Excellent projet, rentabilité au rendez-vous !")
    elif marge_pourcent >= 10:
        st.warning(f"⚖️ Marge de {marge_pourcent:.1f}% : Projet tendu, attention aux imprévus de chantier.")
    else:
        st.error(f"❌ Marge de {marge_pourcent:.1f}% : Projet trop risqué ou non viable, il faut renégocier le prix d'achat.")

    # -- Graphique Waterfall --
    st.markdown("### Décomposition de la création de valeur")
    fig = go.Figure(go.Waterfall(
        name="MDB",
        orientation="v",
        measure=["relative", "relative", "relative", "relative", "total"],
        x=["Prix Achat", "Notaire", "Travaux & Frais", "Marge Créée", "Prix de Revente"],
        textposition="outside",
        text=[f"{prix_achat:,.0f}", f"{frais_notaire:,.0f}", f"{budget_travaux + frais_divers:,.0f}", f"{marge_euros:,.0f}", f"{ca_revente:,.0f}"],
        y=[prix_achat, frais_notaire, budget_travaux + frais_divers, marge_euros, ca_revente],
        connector={"line": {"color": "rgb(63, 63, 63)"}},
        decreasing={"marker": {"color": "Maroon"}},
        increasing={"marker": {"color": "Teal"}},
        totals={"marker": {"color": "deepskyblue"}}
    ))
    fig.update_layout(showlegend=False, margin=dict(l=20, r=20, t=40, b=20))
    st.plotly_chart(fig, use_container_width=True)
