import streamlit as st
import pandas as pd

# =====================
# INTERFACCIA
# =====================
st.title("⚙️ CHECK CICLI PRODUTTIVI E KPI")

codice = st.text_input("Codice prodotto (es. 9188)")

# NUOVO: ore teoriche del turno
ore_teoriche = st.number_input(
    "Ore teoriche turno",
    value=8.0
)

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

    # =====================
    # LOAD FILE
    # =====================
    df_a, df_b = load_data()

    # =====================
    # PULIZIA FOGLIO B
    # =====================
    df_b = df_b.copy()

    df_b.columns = df_b.columns.str.strip()

    df_b["CODICE"] = df_b["CODICE"].astype(str).str.strip()
    df_b["LOTTO"] = df_b["LOTTO"].astype(str).str.strip()
    df_b["QUANTITà"] = pd.to_numeric(
        df_b["QUANTITà"],
        errors="coerce"
    )
    df_b["FAMIGLIA"] = df_b["FAMIGLIA"].astype(str).str.strip()

    # =====================
    # FILTRO FAMIGLIE
    # =====================
    df_b = df_b[
        ~df_b["FAMIGLIA"].str.contains(
            "PANE",
            case=False,
            na=False
        )
    ]

    df_b = df_b[
        ~df_b["FAMIGLIA"].str.contains(
            "GRISSINI",
            case=False,
            na=False
        )
    ]

    # =====================
    # NORMALIZZAZIONE
    # 1 riga = 1 lotto + 1 codice
    # =====================
    df_b = (
        df_b.groupby(
            ["LOTTO", "CODICE"],
            as_index=False
        )
        .agg({
            "QUANTITà": "sum",
            "FAMIGLIA": "first"
        })
    )

    # =====================
    # SOLO LOTTI CON 2 CODICI
    # =====================
    df_lotti_2 = (
        df_b.groupby("LOTTO")
        .filter(
            lambda x: x["CODICE"].nunique() == 2
        )
    )

    # =====================
    # CREAZIONE COPPIE
    # =====================
    per_lotto = (
        df_lotti_2.groupby("LOTTO")
        .apply(
            lambda x: pd.Series({
                "COPPIA": "-".join(
                    sorted(
                        x["CODICE"]
                        .dropna()
                        .unique()
                    )
                ),
                "QUANTITA": x["QUANTITà"].sum()
            })
        )
        .reset_index()
    )

    # solo coppie che contengono il codice input
    per_lotto = per_lotto[
        per_lotto["COPPIA"]
        .str.contains(codice, na=False)
    ]

    # =====================
    # MIGLIOR SKU DA ASSOCIARE
    # =====================
    if not per_lotto.empty:

        per_lotto["A"] = (
            per_lotto["COPPIA"]
            .str.split("-")
            .str[0]
        )

        per_lotto["B"] = (
            per_lotto["COPPIA"]
            .str.split("-")
            .str[1]
        )

        per_lotto["COMPAGNO"] = per_lotto.apply(
            lambda x:
                x["B"]
                if x["A"] == codice
                else x["A"],
            axis=1
        )

        stats = (
            per_lotto.groupby("COMPAGNO")
            .agg(
                QUANTITA_MEDIA=("QUANTITA", "mean"),
                FREQUENZA=("COMPAGNO", "count")
            )
            .reset_index()
        )

        # normalizzazioni
        stats["Q_N"] = (
            stats["QUANTITA_MEDIA"] /
            stats["QUANTITA_MEDIA"].max()
        )

        stats["F_N"] = (
            stats["FREQUENZA"] /
            stats["FREQUENZA"].max()
        )

        # score
        stats["SCORE"] = (
            stats["Q_N"] * 0.6 +
            stats["F_N"] * 0.4
        )

        # confidence
        stats["CONFIDENCE"] = (
            stats["SCORE"] *
            (
                stats["FREQUENZA"] /
                (stats["FREQUENZA"] + K)
            )
        )

        stats = stats.sort_values(
            "SCORE",
            ascending=False
        )

        st.subheader(
            "🚀 RUN PRODUTTIVO - MIGLIOR SKU DA ASSOCIARE"
        )

        st.dataframe(stats)

    else:
        st.warning("Nessuna coppia trovata")

    # =====================
    # KPI PRODUZIONE
    # =====================
    df_a = df_a.copy()

    df_a.columns = (
        df_a.columns.str.strip()
    )

    df_a["REFERENZA"] = (
        df_a["REFERENZA"]
        .astype(str)
        .str.strip()
    )

    df_a["LOTTO"] = (
        df_a["LOTTO"]
        .astype(str)
        .str.strip()
    )

    df_a["TURNO"] = (
        df_a["TURNO"]
        .astype(str)
        .str.strip()
    )

    df_a = df_a[
        df_a["REFERENZA"]
        .str.contains(codice, na=False)
    ]

    # escludi turno 2
    df_a = df_a[
        df_a["TURNO"] != "2"
    ]

    df_a["ORE TOT FASE"] = pd.to_numeric(
        df_a["ORE TOT FASE"],
        errors="coerce"
    )

    # ore per lotto
    ore_lotti = (
        df_a.groupby(
            "LOTTO",
            as_index=False
        )["ORE TOT FASE"]
        .sum()
    )

    # quantità solo del codice cercato
    qta_lotti = (
        df_b[
            df_b["CODICE"]
            .str.contains(codice, na=False)
        ]
        .groupby(
            "LOTTO",
            as_index=False
        )["QUANTITà"]
        .sum()
    )

    # merge
    df_merge = pd.merge(
        ore_lotti,
        qta_lotti,
        on="LOTTO",
        how="inner"
    )

    if df_merge.empty:

        st.error(
            "Nessun lotto comune trovato tra A e B"
        )

    else:

        # =====================
        # KPI
        # =====================
        df_merge["ORE_PER_PEZZO"] = (
            df_merge["ORE TOT FASE"] /
            df_merge["QUANTITà"]
        )

        ore_per_pezzo = (
            df_merge["ORE_PER_PEZZO"]
            .median()
        )

        ore_totali = (
            df_merge["ORE TOT FASE"]
            .sum()
        )

        qta_totale = (
            df_merge["QUANTITà"]
            .sum()
        )

        # FIX CORRETTO
        # pezzi stimati sul turno teorico
        pezzi_stimati = (
            ore_teoriche / ore_per_pezzo
            if ore_per_pezzo > 0
            else 0
        )

        # volatilità
        rate_teorico = (
            pezzi_stimati / ore_teoriche
            if ore_teoriche > 0
            else 0
        )

        rate_reale = (
            qta_totale / ore_totali
            if ore_totali > 0
            else 0
        )

        volatilita = (
            abs(rate_reale - rate_teorico)
            / rate_teorico
            if rate_teorico > 0
            else 0
        )

        st.subheader("⚙️ KPI Produzione")

        st.write({
            "ORE_TOT_REALI":
                round(ore_totali, 2),

            "QUANTITA_TOT":
                round(qta_totale, 2),

            "ORE_PER_PEZZO":
                round(ore_per_pezzo, 4),

            "PEZZI_STIMATI":
                round(pezzi_stimati, 0),

            "VOLATILITA_CICLO":
                round(volatilita, 4)
        })

        # =====================
        # KPI ECONOMICI
        # =====================
        st.subheader("💰 KPI Economici")

        civ = st.number_input(
            "CIV",
            value=0.0
        )

        costo_fisso = st.number_input(
            "Costo fisso",
            value=0.0
        )

        margine = (
            st.number_input(
                "Margine %",
                value=20.0
            ) / 100
        )

        costo_unitario = (
            (civ + costo_fisso) /
            pezzi_stimati
            if pezzi_stimati > 0
            else 0
        )

        prezzo_vendita = (
            costo_unitario *
            (1 + margine)
        )

        st.write({
            "COSTO_UNITARIO":
                round(costo_unitario, 4),

            "PREZZO_VENDITA":
                round(prezzo_vendita, 4)
        })
