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

def prepare_garmin_runs(raw_data):
    """Convertit l'export Garmin en données compatibles avec RunBiomechanics."""

    if "Type d'activité" not in raw_data.columns:
        raise ValueError("Ce fichier ne semble pas être un export Garmin Connect.")

    # On conserve uniquement les sorties de course à pied
    runs = raw_data[
        raw_data["Type d'activité"].astype(str).str.strip() == "Course à pied"
    ].copy()

    if runs.empty:
        return pd.DataFrame(
            columns=["date", "distance_km", "duration_min"]
        )

    # Conversion des durées Garmin en minutes
    duration = pd.to_timedelta(runs["Durée"], errors="coerce")

    result = pd.DataFrame(index=runs.index)

    result["date"] = pd.to_datetime(runs["Date"], errors="coerce")
    result["distance_km"] = pd.to_numeric(
        runs["Distance"], errors="coerce"
    )
    result["duration_min"] = duration.dt.total_seconds() / 60

    # Données physiologiques
    result["avg_hr_bpm"] = pd.to_numeric(
        runs["Fréquence cardiaque moyenne"], errors="coerce"
    )
    result["max_hr_bpm"] = pd.to_numeric(
        runs["Fréquence cardiaque maximale"], errors="coerce"
    )
    result["cadence_spm"] = pd.to_numeric(
        runs["Cadence de course moyenne"], errors="coerce"
    )

    # Données biomécaniques
    result["stride_length_m"] = pd.to_numeric(
        runs["Longueur moyenne des foulées"], errors="coerce"
    )
    result["vertical_ratio_pct"] = pd.to_numeric(
        runs["Rapport vertical moyen"], errors="coerce"
    )
    result["vertical_oscillation_cm"] = pd.to_numeric(
        runs["Oscillation verticale moyenne"], errors="coerce"
    )
    result["ground_contact_time_ms"] = pd.to_numeric(
        runs["Temps de contact moyen avec le sol"], errors="coerce"
    )

    # Puissance et dénivelé
    result["avg_power_w"] = pd.to_numeric(
        runs["Puissance moyenne"], errors="coerce"
    )
    result["max_power_w"] = pd.to_numeric(
        runs["Puissance max."], errors="coerce"
    )
    result["elevation_m"] = pd.to_numeric(
        runs["Ascension totale"], errors="coerce"
    )

    # Informations sur les chaussures utilisées
    result["shoes"] = "Nike Pegasus 41"
    result["surface"] = "Non renseignée"

    return result.reset_index(drop=True)


if uploaded_file is not None:
    raw_data = pd.read_csv(uploaded_file, encoding="utf-8-sig")

    if "Type d'activité" in raw_data.columns:
        garmin_data = prepare_garmin_runs(raw_data)
        data = prepare_runs(garmin_data)
        data_source = "Garmin Connect"
    else:
        data = prepare_runs(raw_data)
        data_source = "Fichier importé"

elif use_demo:
    raw_data = pd.read_csv("data/sample_runs.csv")
    data = prepare_runs(raw_data)
    data_source = "Données de démonstration"

else:
    st.info("Importe un fichier CSV ou active les données de démonstration.")
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
    if data_source == "Garmin Connect":
        initial_shoe_km = st.number_input(
            "Kilométrage avant le début du suivi (km)",
            min_value=0.0,
            value=0.0,
            step=10.0,
            help="Indique les kilomètres déjà parcourus avec cette paire avant le premier enregistrement importé."
        )
    else:
        initial_shoe_km = 0.0
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

overview_tab, physiology_tab, biomechanics_tab, shoes_tab, help_tab = st.tabs(
    ["Vue d'ensemble", "Indicateurs", "Biomécanique", "Chaussures", "Aide / CSV"]
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


with biomechanics_tab:
    st.markdown("### Analyse de ta foulée")

    st.write(
        "Explore l'évolution de tes indicateurs biomécaniques "
        "au fil de tes sorties de course à pied."
    )

    biomechanics_metrics = [
        ("stride_length_m", "Longueur moyenne de foulée", "Longueur (m)"),
        ("cadence_spm", "Cadence de course", "Cadence (pas/min)"),
        ("vertical_oscillation_cm", "Oscillation verticale", "Oscillation (cm)"),
        ("ground_contact_time_ms", "Temps de contact au sol", "Temps (ms)"),
    ]

    for column, title, axis_label in biomechanics_metrics:
        st.markdown(f"#### {title}")

        if column not in filtered.columns:
            st.info(f"L'indicateur {title} n'est pas présent dans les données.")
            continue

        chart_data = filtered.dropna(subset=[column]).sort_values("date")

        if not chart_data.empty:
            chart = px.line(
                chart_data,
                x="date",
                y=column,
                markers=True,
                hover_data=["distance_km", "pace_label"],
                labels={
                    "date": "Date",
                    column: axis_label,
                    "distance_km": "Distance (km)",
                    "pace_label": "Allure",
                },
            )

            st.plotly_chart(chart, use_container_width=True)
            st.caption(
                f"{len(chart_data)} sortie(s) avec une donnée disponible."
            )
        else:
            st.info(f"Aucune donnée disponible pour {title}.")

    st.warning(
        "Ces graphiques permettent d'observer des évolutions et des associations. "
        "Ils ne permettent pas, à eux seuls, de conclure à une amélioration "
        "ou à une dégradation de ta technique de course."
    )

with shoes_tab:
    st.markdown("### Comparaison descriptive des chaussures")
    st.markdown("### Suivi de tes Nike Pegasus 41")

    shoe_history = data[
        data["shoes"] == "Nike Pegasus 41"
    ].sort_values("date").copy()
st.write("### Diagnostic des chaussures")

st.write("Nombre total de séances :", len(data))
st.write("Distance totale :", data["distance_km"].sum())

st.write("Répartition des chaussures :")
st.write(data["shoes"].value_counts(dropna=False))

st.write(
    "Distance associée aux Pegasus 41 :",
    shoe_history["distance_km"].sum()
)
    if not shoe_history.empty:

        shoe_history["shoe_cumulative_km"] = (
            initial_shoe_km + shoe_history["distance_km"].cumsum()
        )

        total_shoe_km = shoe_history["shoe_cumulative_km"].iloc[-1]

        st.metric(
            "Kilométrage cumulé de ta paire",
            f"{total_shoe_km:.1f} km"
        )

        st.markdown("#### Évolution du kilométrage")

        mileage_chart = px.line(
            shoe_history,
            x="date",
            y="shoe_cumulative_km",
            markers=True,
            labels={
                "date": "Date",
                "shoe_cumulative_km": "Kilométrage cumulé (km)"
            }
        )

        st.plotly_chart(mileage_chart, use_container_width=True)

        st.markdown("#### Biomécanique selon le kilométrage")

        mileage_metrics = [
            ("stride_length_m", "Longueur de foulée", "Longueur (m)"),
            ("cadence_spm", "Cadence", "Cadence (pas/min)"),
            ("vertical_oscillation_cm", "Oscillation verticale", "Oscillation (cm)"),
            ("ground_contact_time_ms", "Temps de contact au sol", "Temps (ms)")
        ]

        for column, title, axis_label in mileage_metrics:
            if column not in shoe_history.columns:
    st.info(f"La colonne {column} est absente des données.")
    continue

chart_data = shoe_history.dropna(subset=[column])
            if not chart_data.empty:
                st.markdown(f"##### {title}")

                chart = px.scatter(
                    chart_data,
                    x="shoe_cumulative_km",
                    y=column,
                    hover_data=["date", "pace_label"],
                    labels={
                        "shoe_cumulative_km": "Kilométrage de la paire (km)",
                        column: axis_label
                    }
                )

                st.plotly_chart(chart, use_container_width=True)

    else:
        st.info("Aucune sortie associée aux Nike Pegasus 41.")
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
