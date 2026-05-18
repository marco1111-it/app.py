import streamlit as st
import pandas as pd

# =====================
# UI
# =====================
st.title("⚙️ CHECK CICLI PRODUTTIVI E KPI")

codice = st.text_input("Codice prodotto (es. 9188)")
ore_teoriche = st.number_input("Ore teoriche turno", value=8.0)

# =====================
# CACHE DATA
# =====================
@st.cache_data
def load_data():
    df_a = pd.read_excel("dati.xlsx", sheet_name="A")
    df_b = pd.read_excel("dati.xlsx", sheet_name="B")
    return df_a, df_b


# =====================
# RUN
# =====================
if codice:

    df_a, df_b = load_data()

    # =====================
    # CLEAN A
    # =====================
    df_a = df_a.copy()
    df_a.columns = df_a.columns.str.strip()

    df_a["REFERENZA"] = df_a["REFERENZA"].astype(str).str.strip()
    df_a["LOTTO"] = df_a["LOTTO"].astype(str).str.strip()
    df_a["TURNO"] = df_a["TURNO"].astype(str).str.strip()

    df_a["ORE TOT FASE"] = pd.to_numeric(df_a["ORE TOT FASE"], errors="coerce")

    # 🔴 MATCH ESATTO (COME EXCEL)
    df_a = df_a[df_a["REFERENZA"] == codice]
    df_a = df_a[df_a["TURNO"] != "2"]

    # ore per lotto
    ore_lotti = df_a.groupby("LOTTO", as_index=False)["ORE TOT FASE"].sum()

    # =====================
    # CLEAN B
    # =====================
    df_b = df_b.copy()
    df_b.columns = df_b.columns.str.strip()

    df_b["CODICE"] = df_b["CODICE"].astype(str).str.strip()
    df_b["LOTTO"] = df_b["LOTTO"].astype(str).str.strip()

    df_b["QUANTITà"] = pd.to_numeric(df_b["QUANTITà"], errors="coerce")

    # 🔴 MATCH ESATTO (COME EXCEL)
    df_b = df_b[df_b["CODICE"] == codice]

    qta_lotti = df_b.groupby("LOTTO", as_index=False)["QUANTITà"].sum()

    # =====================
    # MERGE
    # =====================
    df_merge = pd.merge(ore_lotti, qta_lotti, on="LOTTO", how="inner")

    if df_merge.empty:

        st.error("MERGE VUOTO: nessun lotto comune trovato")
        st.stop()

    # =====================
    # KPI PRODUZIONE (CORRETTO)
    # =====================

    df_merge["ORE_PER_PEZZO"] = (
        df_merge["ORE TOT FASE"] / df_merge["QUANTITà"]
    )

    ore_per_pezzo_medio = df_merge["ORE_PER_PEZZO"].median()

    ore_totali_reali = df_merge["ORE TOT FASE"].sum()
    quantita_totale = df_merge["QUANTITà"].sum()

    # 🔴 FORMULA CORRETTA (IDENTICA EXCEL)
    pezzi_stimati = (
        ore_teoriche / ore_per_pezzo_medio
        if ore_per_pezzo_medio > 0 else 0
    )

    # =====================
    # VOLATILITÀ CICLO
    # =====================
    rate_teorico = (
        pezzi_stimati / ore_teoriche
        if ore_teoriche > 0 else 0
    )

    rate_reale = (
        quantita_totale / ore_totali_reali
        if ore_totali_reali > 0 else 0
    )

    volatilita = (
        abs(rate_reale - rate_teorico) / rate_teorico
        if rate_teorico > 0 else 0
    )

    # =====================
    # OUTPUT KPI
    # =====================
    st.subheader("⚙️ KPI Produzione")

    st.write({
        "ORE_TOT_REALI": round(ore_totali_reali, 2),
        "QUANTITA_TOT": round(quantita_totale, 2),
        "ORE_PER_PEZZO": round(ore_per_pezzo_medio, 4),
        "PEZZI_STIMATI": round(pezzi_stimati, 0),
        "VOLATILITA_CICLO": round(volatilita, 4)
    })

    # =====================
    # KPI ECONOMICI
    # =====================
    st.subheader("💰 KPI Economici")

    civ = st.number_input("CIV", value=0.0)
    costo_fisso = st.number_input("Costo fisso", value=0.0)
    margine = st.number_input("Margine %", value=20.0) / 100

    costo_unitario = (
        (civ + costo_fisso) / pezzi_stimati
        if pezzi_stimati > 0 else 0
    )

    prezzo_vendita = costo_unitario * (1 + margine)

    st.write({
        "COSTO_UNITARIO": round(costo_unitario, 4),
        "PREZZO_VENDITA": round(prezzo_vendita, 4)
    })
