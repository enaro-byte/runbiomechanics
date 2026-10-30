from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from metrics import format_pace, prepare_runs, summarize_runs

st.set_page_config(
    page_title="RunBiomechanics",
    page_icon="🏃",
    layout="wide",
)

BASE_DIR = Path(__file__).parent
SAMPLE_FILE = BASE_DIR / "data" / "sample_runs.csv"

st.title("🏃 RunBiomechanics")
st.subheader("Explorer les données de course à pied")
st.markdown(
    "Un petit laboratoire personnel pour suivre ses sorties et explorer quelques "
    "indicateurs d'entraînement, de physiologie et d'équipement."
)
st.info(
    "**Prototype éducatif :** les résultats décrivent uniquement les données importées. "
    "Ils ne constituent ni une mesure biomécanique complète, ni un diagnostic médical, "
    "ni une recommandation personnalisée d'entraînement."
)

with st.sidebar:
    st.header("1. Choisir les données")
    uploaded_file = st.file_uploader("Importer un fichier CSV", type=["csv"])
    use_demo = st.checkbox("Charger les données de démonstration", value=uploaded_file is None)
    st.caption("Le format CSV attendu est expliqué dans l'onglet « Aide ». ")

try:
    if uploaded_file is not None:
        raw_data = pd.read_csv(uploaded_file)
        data = prepare_runs(raw_data)
        data_source = "Fichier importé"
    elif use_demo:
        data = prepare_runs(pd.read_csv(SAMPLE_FILE))
        data_source = "Données de démonstration"
    else:
        st.warning("Importe un CSV ou active les données de démonstration dans la barre latérale.")
        st.stop()
except (ValueError, pd.errors.ParserError, UnicodeDecodeError) as error:
    st.error(f"Impossible de lire ce fichier : {error}")
    st.stop()

if data.empty:
    st.warning("Aucune séance valide trouvée. Vérifie les dates, distances et durées.")
    st.stop()

with st.sidebar:
    st.markdown("---")
    st.header("2. Filtrer les séances")
    shoe_names = sorted(data["shoes"].unique().tolist())
    selected_shoes = st.multiselect("Chaussures", shoe_names, default=shoe_names)
    surface_names = sorted(data["surface"].unique().tolist())
    selected_surfaces = st.multiselect("Surfaces", surface_names, default=surface_names)

filtered = data[
    data["shoes"].isin(selected_shoes) & data["surface"].isin(selected_surfaces)
].copy()

if filtered.empty:
    st.warning("Aucune séance ne correspond aux filtres sélectionnés.")
    st.stop()

summary = summarize_runs(filtered)
st.caption(f"Source : {data_source} · {len(filtered)} séance(s) affichée(s)")

m1, m2, m3, m4 = st.columns(4)
m1.metric("Séances", f"{summary['sessions']}")
m2.metric("Distance cumulée", f"{summary['distance_km']:.1f} km")
m3.metric(
    "Allure moyenne",
    format_pace(summary["pace_min_km"]) if summary["pace_min_km"] is not None else "—",
)
m4.metric(
    "FC moyenne",
    f"{summary['avg_hr_bpm']:.0f} bpm" if summary["avg_hr_bpm"] is not None else "Non renseignée",
)

overview_tab, physiology_tab, shoes_tab, help_tab = st.tabs(
    ["Vue d'ensemble", "Indicateurs", "Chaussures", "Aide / CSV"]
)

with overview_tab:
    st.markdown("### Distance de chaque sortie")
    distance_chart = px.bar(
        filtered,
        x="date",
        y="distance_km",
        hover_data=["duration_min", "pace_label", "shoes", "surface"],
        labels={"date": "Date", "distance_km": "Distance (km)"},
    )
    st.plotly_chart(distance_chart, use_container_width=True)

    st.markdown("### Historique")
    columns_to_show = ["date", "distance_km", "duration_min", "pace_label", "shoes", "surface"]
    for optional in ["avg_hr_bpm", "cadence_spm", "elevation_m"]:
        if optional in filtered.columns:
            columns_to_show.append(optional)
    st.dataframe(
        filtered[columns_to_show].sort_values("date", ascending=False),
        use_container_width=True,
        hide_index=True,
    )

with physiology_tab:
    st.markdown("### Fréquence cardiaque")
    if "avg_hr_bpm" in filtered.columns and filtered["avg_hr_bpm"].notna().any():
        hr_chart = px.scatter(
            filtered.dropna(subset=["avg_hr_bpm"]),
            x="distance_km",
            y="avg_hr_bpm",
            color="shoes",
            hover_data=["date", "pace_label"],
            labels={"distance_km": "Distance (km)", "avg_hr_bpm": "FC moyenne (bpm)"},
        )
        st.plotly_chart(hr_chart, use_container_width=True)
    else:
        st.write("Aucune fréquence cardiaque disponible. Ajoute la colonne `avg_hr_bpm` au CSV.")

    st.markdown("### Cadence")
    if "cadence_spm" in filtered.columns and filtered["cadence_spm"].notna().any():
        cadence_chart = px.scatter(
            filtered.dropna(subset=["cadence_spm"]),
            x="pace_min_km",
            y="cadence_spm",
            color="shoes",
            hover_data=["date", "distance_km"],
            labels={"pace_min_km": "Allure (min/km)", "cadence_spm": "Cadence (pas/min)"},
        )
        st.plotly_chart(cadence_chart, use_container_width=True)
    else:
        st.write("Aucune cadence disponible. Ajoute la colonne `cadence_spm` au CSV.")

    st.caption(
        "Fréquence cardiaque et cadence varient selon l'allure, le terrain, la fatigue, "
        "les conditions et les caractéristiques individuelles. Une comparaison isolée "
        "ne permet pas de tirer une conclusion médicale ou biomécanique."
    )

with shoes_tab:
    st.markdown("### Comparaison descriptive des chaussures")
    shoe_stats = (
        filtered.groupby("shoes", dropna=False)
        .agg(
            sessions=("distance_km", "count"),
            total_distance_km=("distance_km", "sum"),
            mean_pace_min_km=("pace_min_km", "mean"),
        )
        .reset_index()
    )
    shoe_stats["allure_moyenne"] = shoe_stats["mean_pace_min_km"].map(format_pace)
    st.dataframe(
        shoe_stats[["shoes", "sessions", "total_distance_km", "allure_moyenne"]],
        use_container_width=True,
        hide_index=True,
    )
    if len(shoe_stats) > 1:
        shoe_chart = px.bar(
            shoe_stats,
            x="shoes",
            y="total_distance_km",
            labels={"shoes": "Chaussure", "total_distance_km": "Distance cumulée (km)"},
        )
        st.plotly_chart(shoe_chart, use_container_width=True)
    st.warning(
        "Cette comparaison est descriptive, pas un test scientifique de chaussures : "
        "les parcours, allures, conditions météo et niveaux de fatigue ne sont pas contrôlés."
    )

with help_tab:
    st.markdown("### Format CSV")
    st.write("Colonnes obligatoires : `date`, `distance_km`, `duration_min`.")
    st.write(
        "Colonnes facultatives : `avg_hr_bpm`, `cadence_spm`, `elevation_m`, `shoes`, `surface`."
    )
    st.code(
        "date,distance_km,duration_min,avg_hr_bpm,cadence_spm,elevation_m,shoes,surface\n"
        "2026-10-01,5.2,29,148,166,35,Modèle A,route",
        language="csv",
    )
    st.markdown("### À quoi correspondent les indicateurs ?")
    st.write("- **Allure** : durée moyenne nécessaire pour parcourir un kilomètre.")
    st.write("- **FC moyenne** : fréquence cardiaque moyenne rapportée par ton appareil.")
    st.write("- **Cadence** : nombre de pas par minute, selon la définition de la montre ou de l'application utilisée.")
    st.write("- **Distance cumulée par chaussure** : kilomètres associés à chaque modèle dans les séances importées.")
    st.markdown("### Confidentialité")
    st.write(
        "L'application fonctionne localement lorsque tu la lances sur ton ordinateur. "
        "N'importe pas de données personnelles sensibles dans un dépôt public GitHub. "
        "Le fichier de démonstration est fictif."
    )

st.markdown("---")
st.caption("RunBiomechanics · Projet open source en développement · Contributions bienvenues")
