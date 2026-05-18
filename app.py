import streamlit as st
import pandas as pd

st.title("📊 Produzione + Coppie + KPI Economici")

codice = st.text_input("Codice prodotto (es. 9188)")

K = 5  # stabilità confidence

# =====================
# CARICAMENTO DATI
# =====================
@st.cache_data
def load_data():
    df_a = pd.read_excel("dati.xlsx", sheet_name="A")
    df_b = pd.read_excel("dati.xlsx", sheet_name="B")
    return df_a, df_b


if codice:

    df_a, df_b = load_data()

    # =====================
    # PULIZIA FOGLIO B (FONDAMENTALE)
    # =====================
    df_b = df_b.copy()

    df_b.columns = df_b.columns.str.strip()

    df_b["CODICE"] = df_b["CODICE"].astype(str).str.strip()
    df_b["LOTTO"] = df_b["LOTTO"].astype(str).str.strip()
    df_b["QUANTITà"] = pd.to_numeric(df_b["QUANTITà"], errors="coerce")
    df_b["FAMIGLIA"] = df_b["FAMIGLIA"].astype(str).str.strip()

    # filtro famiglie
    df_b = df_b[~df_b["FAMIGLIA"].str.contains("PANE", case=False, na=False)]
    df_b = df_b[~df_b["FAMIGLIA"].str.contains("GRISSINI", case=False, na=False)]

    # 🔥 FIX VERO: normalizzazione 1 riga per (LOTTO + CODICE)
    df_b = df_b.groupby(["LOTTO", "CODICE"], as_index=False).agg({
        "QUANTITà": "sum",
        "FAMIGLIA": "first"
    })

    # =====================
    # COPPIE (BASE CORRETTA)
    # =====================
    df_pair = df_b.groupby("LOTTO").apply(lambda x: pd.Series({
        "COPPIA": "-".join(sorted(x["CODICE"].dropna().unique())),
        "QUANTITA": x["QUANTITà"].sum()
    })).reset_index()

    df_pair = df_pair[df_pair["COPPIA"].str.contains(codice)]

    # =====================
    # COMPAGNO MIGLIORE
    # =====================
    if not df_pair.empty:

        df_pair["A"] = df_pair["COPPIA"].str.split("-").str[0]
        df_pair["B"] = df_pair["COPPIA"].str.split("-").str[1]

        df_pair["COMPAGNO"] = df_pair.apply(
            lambda x: x["B"] if x["A"] == codice else x["A"],
            axis=1
        )

        stats = df_pair.groupby("COMPAGNO").agg(
            QUANTITA_MEDIA=("QUANTITA", "mean"),
            FREQUENZA=("COMPAGNO", "count")
        ).reset_index()

        stats["Q_N"] = stats["QUANTITA_MEDIA"] / stats["QUANTITA_MEDIA"].max()
        stats["F_N"] = stats["FREQUENZA"] / stats["FREQUENZA"].max()

        stats["SCORE"] = (stats["Q_N"] * 0.6) + (stats["F_N"] * 0.4)

        stats["CONFIDENCE"] = stats["SCORE"] * (
            stats["FREQUENZA"] / (stats["FREQUENZA"] + K)
        )

        stats = stats.sort_values("SCORE", ascending=False)

        st.subheader("🔗 Miglior Compagno")
        st.dataframe(stats)

    else:
        st.warning("Nessuna coppia trovata")

    # =====================
    # KPI PRODUZIONE (FOGLIO A)
    # =====================
    df_a = df_a.copy()

    df_a.columns = df_a.columns.str.strip()

    df_a["REFERENZA"] = df_a["REFERENZA"].astype(str).str.strip()
    df_a["LOTTO"] = df_a["LOTTO"].astype(str).str.strip()
    df_a["TURNO"] = df_a["TURNO"].astype(str).str.strip()

    df_a = df_a[df_a["REFERENZA"].str.contains(codice, na=False)]
    df_a = df_a[df_a["TURNO"] != "2"]

    df_a["ORE TOT FASE"] = pd.to_numeric(df_a["ORE TOT FASE"], errors="coerce")

    ore_lotti = df_a.groupby("LOTTO", as_index=False)["ORE TOT FASE"].sum()

    # =====================
    # MERGE CORRETTO (df_b già pulito)
    # =====================
    qta_lotti = df_b.groupby("LOTTO", as_index=False)["QUANTITà"].sum()

    df_merge = pd.merge(ore_lotti, qta_lotti, on="LOTTO", how="inner")

    if not df_merge.empty:

        df_merge["ORE_PER_PEZZO"] = df_merge["ORE TOT FASE"] / df_merge["QUANTITà"]

        ore_per_pezzo = df_merge["ORE_PER_PEZZO"].median()

        ore_totali = df_merge["ORE TOT FASE"].sum()
        qta_totale = df_merge["QUANTITà"].sum()

        pezzi_stimati = ore_totali / ore_per_pezzo if ore_per_pezzo > 0 else 0

        # =====================
        # VOLATILITÀ
        # =====================
        rate_teorico = pezzi_stimati / ore_totali if ore_totali > 0 else 0
        rate_reale = qta_totale / ore_totali if ore_totali > 0 else 0

        volatilita = abs(rate_reale - rate_teorico) if rate_teorico > 0 else 0

        st.subheader("⚙️ KPI Produzione")

        st.write({
            "ORE_TOT_REALI": ore_totali,
            "QUANTITA_TOT": qta_totale,
            "ORE_PER_PEZZO": ore_per_pezzo,
            "PEZZI_STIMATI": pezzi_stimati,
            "VOLATILITA_CICLO": volatilita
        })

        # =====================
        # COSTI
        # =====================
        st.subheader("💰 KPI Economici")

        civ = st.number_input("CIV", value=0.0)
        costo_fisso = st.number_input("Costo fisso", value=0.0)
        margine = st.number_input("Margine %", value=20.0) / 100

        costo_unitario = (civ + costo_fisso) / pezzi_stimati if pezzi_stimati > 0 else 0
        prezzo_vendita = costo_unitario * (1 + margine)

        st.write({
            "COSTO_UNITARIO": costo_unitario,
            "PREZZO_VENDITA": prezzo_vendita
        })
