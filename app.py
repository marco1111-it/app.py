import streamlit as st
import pandas as pd

st.title("⚙️ CHECK CICLI PRODUTTIVI E KPI")

codice = st.text_input("Codice prodotto (es. 9188)")
ore_teoriche = st.number_input("Ore teoriche turno", value=8.0)


@st.cache_data
def load_data():
    return (
        pd.read_excel("dati.xlsx", sheet_name="A"),
        pd.read_excel("dati.xlsx", sheet_name="B")
    )


if codice:

    df_a, df_b = load_data()

    # =====================
    # CLEAN A (SAFE)
    # =====================
    df_a = df_a.copy()
    df_a.columns = df_a.columns.str.strip()

    df_a["REFERENZA"] = df_a["REFERENZA"].astype(str).str.strip()
    df_a["LOTTO"] = df_a["LOTTO"].astype(str).str.strip()
    df_a["TURNO"] = df_a["TURNO"].astype(str).str.strip()

    df_a["ORE TOT FASE"] = pd.to_numeric(df_a["ORE TOT FASE"], errors="coerce")

    # DEBUG IMPORTANTE
    st.write("DEBUG A - righe totali:", len(df_a))

    df_a = df_a[df_a["TURNO"] != "2"]

    # ⚠️ match più tollerante (evita blocchi)
    df_a_filt = df_a[df_a["REFERENZA"].eq(str(codice).strip())]

    st.write("DEBUG A filtrato:", len(df_a_filt))

    ore_lotti = df_a_filt.groupby("LOTTO", as_index=False)["ORE TOT FASE"].sum()

    # =====================
    # CLEAN B (SAFE)
    # =====================
    df_b = df_b.copy()
    df_b.columns = df_b.columns.str.strip()

    df_b["CODICE"] = df_b["CODICE"].astype(str).str.strip()
    df_b["LOTTO"] = df_b["LOTTO"].astype(str).str.strip()

    df_b["QUANTITà"] = pd.to_numeric(df_b["QUANTITà"], errors="coerce")

    st.write("DEBUG B - righe totali:", len(df_b))

    df_b_filt = df_b[df_b["CODICE"].eq(str(codice).strip())]

    st.write("DEBUG B filtrato:", len(df_b_filt))

    qta_lotti = df_b_filt.groupby("LOTTO", as_index=False)["QUANTITà"].sum()

    # =====================
    # MERGE
    # =====================
    df_merge = pd.merge(ore_lotti, qta_lotti, on="LOTTO", how="inner")

    st.write("DEBUG MERGE:", len(df_merge))

    if df_merge.empty:
        st.error(
            "MERGE VUOTO → problema di matching tra A e B (CODICE o LOTTI)"
        )
        st.stop()

    # =====================
    # KPI CORRETTO
    # =====================
    df_merge["ORE_PER_PEZZO"] = (
        df_merge["ORE TOT FASE"] / df_merge["QUANTITà"]
    )

    ore_per_pezzo_medio = df_merge["ORE_PER_PEZZO"].median()

    ore_totali_reali = df_merge["ORE TOT FASE"].sum()
    quantita_totale = df_merge["QUANTITà"].sum()

    pezzi_stimati = (
        ore_teoriche / ore_per_pezzo_medio
        if ore_per_pezzo_medio > 0 else 0
    )

    # =====================
    # OUTPUT
    # =====================
    st.subheader("⚙️ KPI Produzione")

    st.write({
        "ORE_TOT_REALI": ore_totali_reali,
        "QUANTITA_TOT": quantita_totale,
        "ORE_PER_PEZZO": ore_per_pezzo_medio,
        "PEZZI_STIMATI": pezzi_stimati
    })
