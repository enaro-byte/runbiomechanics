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

    # Regroupement des données par modèle
    aggregations = {
        "sessions": ("distance_km", "count"),
        "total_distance_km": ("distance_km", "sum"),
        "mean_pace_min_km": ("pace_min_km", "mean"),
    }

    if "avg_hr_bpm" in filtered.columns:
        aggregations["mean_hr_bpm"] = ("avg_hr_bpm", "mean")

    if "cadence_spm" in filtered.columns:
        aggregations["mean_cadence_spm"] = ("cadence_spm", "mean")

    shoe_stats = (
        filtered.groupby("shoes", dropna=False)
        .agg(**aggregations)
        .reset_index()
    )
    # Importation des caractéristiques techniques des chaussures
    specs_file = BASE_DIR / "data" / "shoe_specs.csv"

    if specs_file.exists():
        shoe_specs = pd.read_csv(specs_file, skipinitialspace=True)
        shoe_specs["shoes"] = shoe_specs["shoes"].astype(str).str.strip()

        numeric_columns = [
            "weight_g",
            "drop_mm",
            "stack_heel_mm",
            "stack_forefoot_mm",
        ]

        for column in numeric_columns:
            if column in shoe_specs.columns:
                shoe_specs[column] = pd.to_numeric(
                    shoe_specs[column], errors="coerce"
                )

        shoe_stats = shoe_stats.merge(
            shoe_specs,
            on="shoes",
            how="left",
        )
        
    shoe_stats["Allure moyenne"] = shoe_stats["mean_pace_min_km"].map(
        lambda value: format_pace(value) if pd.notna(value) else "—"
    )

    st.markdown("#### Indicateurs par chaussure")

    display_data = shoe_stats[
        ["shoes", "sessions", "total_distance_km", "Allure moyenne"]
    ].rename(columns={
        "shoes": "Chaussure",
        "sessions": "Nombre de sorties",
        "total_distance_km": "Distance cumulée (km)",
    })

    if "mean_hr_bpm" in shoe_stats.columns:
        display_data["FC moyenne (bpm)"] = shoe_stats["mean_hr_bpm"].round(1)

    if "mean_cadence_spm" in shoe_stats.columns:
        display_data["Cadence moyenne (pas/min)"] = (
            shoe_stats["mean_cadence_spm"].round(1)
        )
    # Ajout des caractéristiques techniques au tableau
    technical_columns = {
        "brand": "Marque",
        "category": "Catégorie",
        "weight_g": "Poids (g)",
        "drop_mm": "Drop (mm)",
        "stack_heel_mm": "Hauteur talon (mm)",
        "stack_forefoot_mm": "Hauteur avant-pied (mm)",
    }

    for column, label in technical_columns.items():
        if column in shoe_stats.columns:
            display_data[label] = shoe_stats[column]
    st.dataframe(display_data, use_container_width=True, hide_index=True)

    # Comparaison des distances cumulées
    st.markdown("#### Kilométrage par chaussure")

    distance_chart = px.bar(
        shoe_stats,
        x="shoes",
        y="total_distance_km",
        color="shoes",
        labels={
            "shoes": "Modèle",
            "total_distance_km": "Distance cumulée (km)",
        },
        text_auto=".1f",
    )
    st.plotly_chart(distance_chart, use_container_width=True)

    # Comparaison des allures
    st.markdown("#### Allure moyenne par chaussure")

    pace_chart = px.bar(
        shoe_stats,
        x="shoes",
        y="mean_pace_min_km",
        color="shoes",
        labels={
            "shoes": "Modèle",
            "mean_pace_min_km": "Allure moyenne (min/km)",
        },
    )
    st.plotly_chart(pace_chart, use_container_width=True)
    # Relation entre le poids de la chaussure et l'allure moyenne
    if "weight_g" in shoe_stats.columns:
        weight_data = shoe_stats.dropna(
            subset=["weight_g", "mean_pace_min_km"]
        )

        if not weight_data.empty:
            st.markdown("#### Poids de la chaussure et allure moyenne")

            weight_chart = px.scatter(
                weight_data,
                x="weight_g",
                y="mean_pace_min_km",
                color="shoes",
                size="sessions",
                hover_data=[
                    "shoes",
                    "sessions",
                    "mean_hr_bpm",
                    "mean_cadence_spm",
                ],
                labels={
                    "weight_g": "Poids de la chaussure (g)",
                    "mean_pace_min_km": "Allure moyenne (min/km)",
                    "shoes": "Chaussure",
                    "sessions": "Nombre de sorties",
                },
            )

            st.plotly_chart(weight_chart, use_container_width=True)
    # Répartition des surfaces
    if "surface" in filtered.columns:
        st.markdown("#### Répartition des surfaces")

        surface_data = (
            filtered.groupby(["shoes", "surface"])
            .size()
            .reset_index(name="sessions")
        )

        surface_chart = px.bar(
            surface_data,
            x="shoes",
            y="sessions",
            color="surface",
            barmode="stack",
            labels={
                "shoes": "Chaussure",
                "sessions": "Nombre de sorties",
                "surface": "Surface",
            },
        )
        st.plotly_chart(surface_chart, use_container_width=True)

    st.warning(
        "Ces comparaisons sont descriptives. Elles ne démontrent pas qu'un modèle "
        "est plus performant ou plus efficace qu'un autre. Les conditions de course, "
        "l'allure, le terrain et la fatigue ne sont pas contrôlés."
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
