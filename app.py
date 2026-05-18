import streamlit as st
import pandas as pd

st.title("Analisi Coppie Produzione")

# =====================
# INPUT
# =====================
codice = st.text_input("Inserisci codice prodotto (es. L9)")

file = st.file_uploader("Carica file Excel", type=["xlsx"])

if file and codice:

    df = pd.read_excel(file, sheet_name="B")

    df.columns = df.columns.str.strip()

    df["CODICE"] = df["CODICE"].astype(str).str.strip()
    df["LOTTO"] = df["LOTTO"].astype(str).str.strip()
    df["QUANTITà"] = pd.to_numeric(df["QUANTITà"], errors="coerce")

    df["FAMIGLIA"] = df["FAMIGLIA"].astype(str).str.strip()

    # FILTRO FAMIGLIA
    df = df[~df["FAMIGLIA"].str.contains("PANE", case=False, na=False)]
    df = df[~df["FAMIGLIA"].str.contains("GRISSINI", case=False, na=False)]

    # SOLO LOTTI 2 CODICI
    df2 = df.groupby("LOTTO").filter(lambda x: x["CODICE"].nunique() == 2)

    # COPPIE
    per_lotto = (
        df2.groupby("LOTTO")
        .apply(lambda x: pd.Series({
            "COPPIA": "-".join(sorted(x["CODICE"].dropna().unique())),
            "QUANTITA": x["QUANTITà"].sum()
        }))
        .reset_index()
    )

    # FILTRO CODICE
    per_lotto = per_lotto[per_lotto["COPPIA"].str.contains(codice)]

    # COMPAGNO
    per_lotto["A"] = per_lotto["COPPIA"].str.split("-").str[0]
    per_lotto["B"] = per_lotto["COPPIA"].str.split("-").str[1]

    per_lotto["COMPAGNO"] = per_lotto.apply(
        lambda x: x["B"] if x["A"] == codice else x["A"],
        axis=1
    )

    # AGGREGAZIONE
    stats = per_lotto.groupby("COMPAGNO").agg(
        QUANTITA_MEDIA=("QUANTITA", "mean"),
        FREQUENZA=("COMPAGNO", "count")
    ).reset_index()

    if not stats.empty:

        stats["Q_N"] = stats["QUANTITA_MEDIA"] / stats["QUANTITA_MEDIA"].max()
        stats["F_N"] = stats["FREQUENZA"] / stats["FREQUENZA"].max()

        stats["SCORE"] = (stats["Q_N"] * 0.6) + (stats["F_N"] * 0.4)

        K = 5
        stats["CONFIDENCE"] = stats["SCORE"] * (stats["FREQUENZA"] / (stats["FREQUENZA"] + K))

        stats = stats.sort_values("SCORE", ascending=False)

        st.subheader("Risultato")

        st.dataframe(stats)

    else:
        st.warning("Nessun dato trovato per questo codice")
