from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from garmin_personal_api import (
    GarminPersonalApiClient,
    PersonalApiAuthenticator,
)
from metrics import format_pace, prepare_runs, summarize_runs


# =====================================================
# CONFIGURATION
# =====================================================

st.set_page_config(
    page_title="RunBiomechanics",
    page_icon="🏃",
    layout="wide",
)

BASE_DIR = Path(__file__).parent
SAMPLE_FILE = BASE_DIR / "data" / "sample_runs.csv"

# Conserve les activités Garmin entre les rechargements Streamlit.
if "garmin_activities" not in st.session_state:
    st.session_state.garmin_activities = None


# =====================================================
# IDENTITÉ VISUELLE — RUNBIOMECHANICS
# =====================================================

st.markdown(
    """
    <style>
        .stApp {
            background-color: #080F17;
            color: #F0F5F8;
        }

        .block-container {
            max-width: 1450px;
            padding-top: 2.5rem;
            padding-bottom: 3rem;
        }

        section[data-testid="stSidebar"] {
            background-color: #0D1722;
            border-right: 1px solid #233342;
        }

        h1, h2, h3, h4 {
            color: #F0F5F8 !important;
        }

        .stCaption, [data-testid="stCaptionContainer"] {
            color: #8FA3B5;
        }

        [data-testid="stMetric"] {
            background-color: #111D29;
            border: 1px solid #233746;
            border-radius: 12px;
            padding: 18px;
        }

        [data-testid="stMetricLabel"] {
            color: #8FA3B5 !important;
        }

        [data-testid="stMetricValue"] {
            color: #20DCC3 !important;
        }

        .stTabs [data-baseweb="tab"] {
            color: #8FA3B5;
            font-weight: 600;
        }

        .stTabs [aria-selected="true"] {
            color: #20DCC3 !important;
        }

        .stTabs [data-baseweb="tab-highlight"] {
            background-color: #20DCC3;
        }

        .stButton > button {
            background-color: #20DCC3;
            color: #08131B;
            border: none;
            border-radius: 8px;
            font-weight: 600;
        }

        .stButton > button:hover {
            background-color: #61EAD8;
            color: #08131B;
        }

        [data-testid="stDataFrame"] {
            border: 1px solid #233746;
            border-radius: 10px;
        }

        hr {
            border-color: #233746;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

px.defaults.template = "plotly_dark"
px.defaults.color_discrete_sequence = [
    "#20DCC3",
    "#4D9DE0",
    "#A78BFA",
    "#F0B45A",
    "#F1789B",
]

st.html(
    """
    <div style="
        padding: 28px 30px;
        background: linear-gradient(120deg, #111D29, #142C38);
        border: 1px solid #284353;
        border-radius: 16px;
        margin-bottom: 25px;
    ">
        <div style="
            color: #20DCC3;
            font-size: 12px;
            font-weight: 700;
            letter-spacing: 3px;
            margin-bottom: 12px;
        ">
            RUNNING PERFORMANCE LAB
        </div>

        <div style="
            font-size: 38px;
            font-weight: 800;
            color: #F0F5F8;
            letter-spacing: -1px;
        ">
            RunBiomechanics<span style="color:#20DCC3;">.</span>
        </div>

        <div style="
            color: #A6B8C7;
            font-size: 16px;
            margin-top: 8px;
        ">
            Explorer · Mesurer · Comprendre la performance en course à pied
        </div>
    </div>
    """
)

st.info(
    "**Prototype éducatif :** les résultats décrivent uniquement les données importées. "
    "Ils ne constituent ni une mesure biomécanique complète, ni un diagnostic médical, "
    "ni une recommandation personnalisée d'entraînement."
)


# =====================================================
# FONCTIONS DE CONVERSION ET CONNEXION GARMIN
# =====================================================

def prepare_garmin_runs(raw_data):
    """Convertit un export CSV Garmin en données RunBiomechanics."""

    if "Type d'activité" not in raw_data.columns:
        raise ValueError("Ce fichier ne semble pas être un export Garmin Connect.")

    runs = raw_data[
        raw_data["Type d'activité"].astype(str).str.strip() == "Course à pied"
    ].copy()

    if runs.empty:
        return pd.DataFrame(
            columns=["date", "distance_km", "duration_min"]
        )

    duration = pd.to_timedelta(runs["Durée"], errors="coerce")
    result = pd.DataFrame(index=runs.index)

    result["date"] = pd.to_datetime(runs["Date"], errors="coerce")
    result["distance_km"] = pd.to_numeric(runs["Distance"], errors="coerce")
    result["duration_min"] = duration.dt.total_seconds() / 60

    csv_columns = {
        "avg_hr_bpm": "Fréquence cardiaque moyenne",
        "max_hr_bpm": "Fréquence cardiaque maximale",
        "cadence_spm": "Cadence de course moyenne",
        "stride_length_m": "Longueur moyenne des foulées",
        "vertical_ratio_pct": "Rapport vertical moyen",
        "vertical_oscillation_cm": "Oscillation verticale moyenne",
        "ground_contact_time_ms": "Temps de contact moyen avec le sol",
        "avg_power_w": "Puissance moyenne",
        "max_power_w": "Puissance max.",
        "elevation_m": "Ascension totale",
    }

    for output_column, csv_column in csv_columns.items():
        if csv_column in runs.columns:
            result[output_column] = pd.to_numeric(
                runs[csv_column], errors="coerce"
            )

    result["shoes"] = "Nike Pegasus 41"
    result["surface"] = "Non renseignée"

    return result.reset_index(drop=True)


def test_garmin_connection():
    """Récupère tout l'historique des courses Garmin, par pages de 20."""

    api_key = st.secrets.get("GARMIN_PERSONAL_API_KEY")

    if not api_key:
        raise ValueError("Clé Garmin introuvable dans les Secrets.")

    all_activities = []
    start = 0
    page_size = 20

    with PersonalApiAuthenticator() as authenticator:
        token = authenticator.obtain_token(api_key)

    with GarminPersonalApiClient(token.access_token) as client:
        while True:
            page = client.search_activities(
                start=start,
                limit=page_size,
                activity_type="running",
            )

            if not page:
                break

            # Garmin peut regrouper plusieurs types de course.
            # On conserve uniquement la course à pied classique.
            running_activities = [
                activity
                for activity in page
                if isinstance(activity.get("activityType"), dict)
                and activity["activityType"].get("typeKey") == "running"
            ]

            all_activities.extend(running_activities)

            # L'offset avance du nombre d'activités reçues,
            # pas du nombre conservé après filtrage.
            start += len(page)

            if len(page) < page_size:
                break

    return all_activities


def convert_garmin_activities(activities):
    """Convertit les activités de l'API Garmin au format RunBiomechanics."""

    rows = []

    for activity in activities:
        rows.append(
            {
                "date": pd.to_datetime(
                    activity.get("startTimeLocal"), errors="coerce"
                ),
                "distance_km": pd.to_numeric(
                    activity.get("distance"), errors="coerce"
                ) / 1000,
                "duration_min": pd.to_numeric(
                    activity.get("duration"), errors="coerce"
                ) / 60,
                "avg_hr_bpm": pd.to_numeric(
                    activity.get("averageHR"), errors="coerce"
                ),
                "max_hr_bpm": pd.to_numeric(
                    activity.get("maxHR"), errors="coerce"
                ),
                "cadence_spm": pd.to_numeric(
                    activity.get(
                        "averageRunningCadenceInStepsPerMinute"
                    ),
                    errors="coerce",
                ),
                "stride_length_m": pd.to_numeric(
                    activity.get("avgStrideLength"), errors="coerce"
                ) / 100,
                "vertical_ratio_pct": pd.to_numeric(
                    activity.get("avgVerticalRatio"), errors="coerce"
                ),
                "vertical_oscillation_cm": pd.to_numeric(
                    activity.get("avgVerticalOscillation"), errors="coerce"
                ),
                "ground_contact_time_ms": pd.to_numeric(
                    activity.get("avgGroundContactTime"), errors="coerce"
                ),
                "avg_power_w": pd.to_numeric(
                    activity.get("avgPower"), errors="coerce"
                ),
                "max_power_w": pd.to_numeric(
                    activity.get("maxPower"), errors="coerce"
                ),
                "elevation_m": pd.to_numeric(
                    activity.get("elevationGain"), errors="coerce"
                ),
                "shoes": "Nike Pegasus 41",
                "surface": "Non renseignée",
            }
        )

    return pd.DataFrame(rows)


# =====================================================
# BARRE LATÉRALE — IMPORT ET CONNEXION
# =====================================================

with st.sidebar:
    st.header("1. Choisir les données")

    uploaded_file = st.file_uploader(
        "Importer un fichier CSV",
        type=["csv"],
    )

    use_demo = st.checkbox(
        "Charger les données de démonstration",
        value=uploaded_file is None,
    )

    st.caption(
        "Le format CSV attendu est expliqué dans l'onglet « Aide »."
    )

    st.markdown("---")
    st.header("3. Connexion Garmin")

    if st.button("Récupérer tout mon historique Garmin"):
        try:
            activities = test_garmin_connection()
            st.session_state.garmin_activities = activities

            if activities:
                st.success(
                    f"{len(activities)} sortie(s) de course à pied récupérée(s)."
                )
            else:
                st.warning("Connexion réussie, mais aucune activité trouvée.")

        except Exception as error:
            st.error(f"Erreur Garmin : {error}")

    if st.button("Revenir au CSV / démonstration"):
        st.session_state.garmin_activities = None
        st.rerun()


# =====================================================
# CHARGEMENT DES DONNÉES
# =====================================================

if st.session_state.garmin_activities is not None:
    garmin_data = convert_garmin_activities(
        st.session_state.garmin_activities
    )
    data = prepare_runs(garmin_data)
    data_source = "Garmin Connect (API)"

elif uploaded_file is not None:
    raw_data = pd.read_csv(uploaded_file, encoding="utf-8-sig")

    if "Type d'activité" in raw_data.columns:
        garmin_data = prepare_garmin_runs(raw_data)
        data = prepare_runs(garmin_data)
        data_source = "Garmin Connect"
    else:
        data = prepare_runs(raw_data)
        data_source = "Fichier importé"

elif use_demo:
    raw_data = pd.read_csv(SAMPLE_FILE)
    data = prepare_runs(raw_data)
    data_source = "Données de démonstration"

else:
    st.info(
        "Importe un fichier CSV, connecte Garmin ou active les données de démonstration."
    )
    st.stop()


if data.empty:
    st.warning(
        "Aucune séance valide trouvée. Vérifie les dates, distances et durées."
    )
    st.stop()


# =====================================================
# FILTRES ET INDICATEURS
# =====================================================

with st.sidebar:
    st.markdown("---")
    st.header("2. Filtrer les séances")

    shoe_names = sorted(data["shoes"].dropna().unique().tolist())
    selected_shoes = st.multiselect(
        "Chaussures",
        shoe_names,
        default=shoe_names,
    )

    surface_names = sorted(data["surface"].dropna().unique().tolist())
    selected_surfaces = st.multiselect(
        "Surfaces",
        surface_names,
        default=surface_names,
    )

    if data_source.startswith("Garmin Connect"):
        initial_shoe_km = st.number_input(
            "Kilométrage avant le début du suivi (km)",
            min_value=0.0,
            value=0.0,
            step=10.0,
            help=(
                "Indique les kilomètres déjà parcourus avec cette paire "
                "avant le premier enregistrement importé."
            ),
        )
    else:
        initial_shoe_km = 0.0


filtered = data[
    data["shoes"].isin(selected_shoes)
    & data["surface"].isin(selected_surfaces)
].copy()

if filtered.empty:
    st.warning("Aucune séance ne correspond aux filtres sélectionnés.")
    st.stop()

summary = summarize_runs(filtered)

st.caption(
    f"Source : {data_source} · {len(filtered)} séance(s) affichée(s)"
)

m1, m2, m3, m4 = st.columns(4)

m1.metric("Séances", f"{summary['sessions']}")
m2.metric("Distance cumulée", f"{summary['distance_km']:.1f} km")

m3.metric(
    "Allure moyenne",
    (
        format_pace(summary["pace_min_km"])
        if summary["pace_min_km"] is not None
        else "—"
    ),
)

m4.metric(
    "FC moyenne",
    (
        f"{summary['avg_hr_bpm']:.0f} bpm"
        if summary["avg_hr_bpm"] is not None
        else "Non renseignée"
    ),
)


# =====================================================
# ONGLETS
# =====================================================

overview_tab, physiology_tab, biomechanics_tab, shoes_tab, help_tab = st.tabs(
    [
        "Vue d'ensemble",
        "Indicateurs",
        "Biomécanique",
        "Chaussures",
        "Aide / CSV",
    ]
)


# =====================================================
# VUE D'ENSEMBLE
# =====================================================

with overview_tab:
    st.markdown("### Distance de chaque sortie")

    distance_chart = px.bar(
        filtered,
        x="date",
        y="distance_km",
        hover_data=[
            column
            for column in ["duration_min", "pace_label", "shoes", "surface"]
            if column in filtered.columns
        ],
        labels={
            "date": "Date",
            "distance_km": "Distance (km)",
        },
    )

    st.plotly_chart(distance_chart, use_container_width=True)

    st.markdown("### Historique")

    columns_to_show = [
        column
        for column in [
            "date",
            "distance_km",
            "duration_min",
            "pace_label",
            "shoes",
            "surface",
            "avg_hr_bpm",
            "cadence_spm",
            "elevation_m",
        ]
        if column in filtered.columns
    ]

    st.dataframe(
        filtered[columns_to_show].sort_values(
            "date",
            ascending=False,
        ),
        use_container_width=True,
        hide_index=True,
    )


# =====================================================
# INDICATEURS PHYSIOLOGIQUES
# =====================================================

with physiology_tab:
    st.markdown("### Fréquence cardiaque")

    if (
        "avg_hr_bpm" in filtered.columns
        and filtered["avg_hr_bpm"].notna().any()
    ):
        hr_data = filtered.dropna(subset=["avg_hr_bpm"])

        hr_chart = px.scatter(
            hr_data,
            x="distance_km",
            y="avg_hr_bpm",
            color="shoes",
            hover_data=[
                column
                for column in ["date", "pace_label"]
                if column in hr_data.columns
            ],
            labels={
                "distance_km": "Distance (km)",
                "avg_hr_bpm": "FC moyenne (bpm)",
            },
        )

        st.plotly_chart(hr_chart, use_container_width=True)
    else:
        st.write(
            "Aucune fréquence cardiaque disponible. "
            "Ajoute la colonne `avg_hr_bpm` au CSV."
        )

    st.markdown("### Cadence")

    if (
        "cadence_spm" in filtered.columns
        and filtered["cadence_spm"].notna().any()
    ):
        cadence_data = filtered.dropna(subset=["cadence_spm"])

        cadence_chart = px.scatter(
            cadence_data,
            x="pace_min_km",
            y="cadence_spm",
            color="shoes",
            hover_data=[
                column
                for column in ["date", "distance_km"]
                if column in cadence_data.columns
            ],
            labels={
                "pace_min_km": "Allure (min/km)",
                "cadence_spm": "Cadence (pas/min)",
            },
        )

        st.plotly_chart(cadence_chart, use_container_width=True)
    else:
        st.write(
            "Aucune cadence disponible. "
            "Ajoute la colonne `cadence_spm` au CSV."
        )

    st.caption(
        "Fréquence cardiaque et cadence varient selon l'allure, le terrain, "
        "la fatigue, les conditions et les caractéristiques individuelles. "
        "Une comparaison isolée ne permet pas de tirer une conclusion "
        "médicale ou biomécanique."
    )


# =====================================================
# BIOMÉCANIQUE
# =====================================================

with biomechanics_tab:
    st.markdown("### Analyse de ta foulée")

    st.write(
        "Explore l'évolution de tes indicateurs biomécaniques "
        "au fil de tes sorties de course à pied."
    )

    biomechanics_metrics = [
        (
            "stride_length_m",
            "Longueur moyenne de foulée",
            "Longueur (m)",
        ),
        (
            "cadence_spm",
            "Cadence de course",
            "Cadence (pas/min)",
        ),
        (
            "vertical_oscillation_cm",
            "Oscillation verticale",
            "Oscillation (cm)",
        ),
        (
            "ground_contact_time_ms",
            "Temps de contact au sol",
            "Temps (ms)",
        ),
    ]

    for column, title, axis_label in biomechanics_metrics:
        st.markdown(f"#### {title}")

        if column not in filtered.columns:
            st.info(
                f"L'indicateur {title} n'est pas présent dans les données."
            )
            continue

        chart_data = (
            filtered.dropna(subset=[column])
            .sort_values("date")
        )

        if not chart_data.empty:
            chart = px.line(
                chart_data,
                x="date",
                y=column,
                markers=True,
                hover_data=[
                    item
                    for item in ["distance_km", "pace_label"]
                    if item in chart_data.columns
                ],
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


# =====================================================
# CHAUSSURES
# =====================================================

with shoes_tab:
    st.markdown("### Comparaison descriptive des chaussures")
    st.markdown("### Suivi de tes Nike Pegasus 41")

    shoe_history = data[
        data["shoes"] == "Nike Pegasus 41"
    ].sort_values("date").copy()

    if not shoe_history.empty:
        shoe_history["shoe_cumulative_km"] = (
            initial_shoe_km + shoe_history["distance_km"].cumsum()
        )

        total_shoe_km = shoe_history["shoe_cumulative_km"].iloc[-1]

        st.metric(
            "Kilométrage cumulé de ta paire",
            f"{total_shoe_km:.1f} km",
        )

        st.markdown("#### Évolution du kilométrage")

        mileage_chart = px.line(
            shoe_history,
            x="date",
            y="shoe_cumulative_km",
            markers=True,
            labels={
                "date": "Date",
                "shoe_cumulative_km": "Kilométrage cumulé (km)",
            },
        )

        st.plotly_chart(mileage_chart, use_container_width=True)

        st.markdown("#### Biomécanique selon le kilométrage")

        mileage_metrics = [
            ("stride_length_m", "Longueur de foulée", "Longueur (m)"),
            ("cadence_spm", "Cadence", "Cadence (pas/min)"),
            (
                "vertical_oscillation_cm",
                "Oscillation verticale",
                "Oscillation (cm)",
            ),
            (
                "ground_contact_time_ms",
                "Temps de contact au sol",
                "Temps (ms)",
            ),
        ]

        for column, title, axis_label in mileage_metrics:
            if column not in shoe_history.columns:
                st.info(
                    f"La colonne {column} est absente des données."
                )
                continue

            chart_data = shoe_history.dropna(subset=[column])

            if not chart_data.empty:
                st.markdown(f"##### {title}")

                chart = px.scatter(
                    chart_data,
                    x="shoe_cumulative_km",
                    y=column,
                    hover_data=[
                        item
                        for item in ["date", "pace_label"]
                        if item in chart_data.columns
                    ],
                    labels={
                        "shoe_cumulative_km": (
                            "Kilométrage de la paire (km)"
                        ),
                        column: axis_label,
                    },
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
        shoe_specs = pd.read_csv(
            specs_file,
            skipinitialspace=True,
        )
        shoe_specs["shoes"] = (
            shoe_specs["shoes"].astype(str).str.strip()
        )

        numeric_columns = [
            "weight_g",
            "drop_mm",
            "stack_heel_mm",
            "stack_forefoot_mm",
        ]

        for column in numeric_columns:
            if column in shoe_specs.columns:
                shoe_specs[column] = pd.to_numeric(
                    shoe_specs[column],
                    errors="coerce",
                )

        shoe_stats = shoe_stats.merge(
            shoe_specs,
            on="shoes",
            how="left",
        )

    shoe_stats["Allure moyenne"] = shoe_stats[
        "mean_pace_min_km"
    ].map(
        lambda value: (
            format_pace(value) if pd.notna(value) else "—"
        )
    )

    st.markdown("#### Indicateurs par chaussure")

    display_data = shoe_stats[
        [
            "shoes",
            "sessions",
            "total_distance_km",
            "Allure moyenne",
        ]
    ].rename(
        columns={
            "shoes": "Chaussure",
            "sessions": "Nombre de sorties",
            "total_distance_km": "Distance cumulée (km)",
        }
    )

    if "mean_hr_bpm" in shoe_stats.columns:
        display_data["FC moyenne (bpm)"] = (
            shoe_stats["mean_hr_bpm"].round(1)
        )

    if "mean_cadence_spm" in shoe_stats.columns:
        display_data["Cadence moyenne (pas/min)"] = (
            shoe_stats["mean_cadence_spm"].round(1)
        )

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

    st.dataframe(
        display_data,
        use_container_width=True,
        hide_index=True,
    )

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
            st.markdown(
                "#### Poids de la chaussure et allure moyenne"
            )

            weight_hover = [
                column
                for column in [
                    "shoes",
                    "sessions",
                    "mean_hr_bpm",
                    "mean_cadence_spm",
                ]
                if column in weight_data.columns
            ]

            weight_chart = px.scatter(
                weight_data,
                x="weight_g",
                y="mean_pace_min_km",
                color="shoes",
                size="sessions",
                hover_data=weight_hover,
                labels={
                    "weight_g": "Poids de la chaussure (g)",
                    "mean_pace_min_km": "Allure moyenne (min/km)",
                    "shoes": "Chaussure",
                    "sessions": "Nombre de sorties",
                },
            )

            st.plotly_chart(
                weight_chart,
                use_container_width=True,
            )

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

        st.plotly_chart(
            surface_chart,
            use_container_width=True,
        )

    st.warning(
        "Ces comparaisons sont descriptives. Elles ne démontrent pas qu'un modèle "
        "est plus performant ou plus efficace qu'un autre. Les conditions de course, "
        "l'allure, le terrain et la fatigue ne sont pas contrôlés."
    )


# =====================================================
# AIDE / CSV
# =====================================================

with help_tab:
    st.markdown("### Format CSV")

    st.write(
        "Colonnes obligatoires : `date`, `distance_km`, `duration_min`."
    )

    st.write(
        "Colonnes facultatives : `avg_hr_bpm`, `cadence_spm`, "
        "`elevation_m`, `shoes`, `surface`."
    )

    st.code(
        "date,distance_km,duration_min,avg_hr_bpm,cadence_spm,elevation_m,shoes,surface\n"
        "2026-10-01,5.2,29,148,166,35,Modèle A,route",
        language="csv",
    )

    st.markdown("### À quoi correspondent les indicateurs ?")

    st.write(
        "- **Allure** : durée moyenne nécessaire pour parcourir un kilomètre."
    )
    st.write(
        "- **FC moyenne** : fréquence cardiaque moyenne rapportée par ton appareil."
    )
    st.write(
        "- **Cadence** : nombre de pas par minute, selon la définition "
        "de la montre ou de l'application utilisée."
    )
    st.write(
        "- **Distance cumulée par chaussure** : kilomètres associés "
        "à chaque modèle dans les séances importées."
    )

    st.markdown("### Confidentialité")

    st.write(
        "L'application fonctionne sur Streamlit. Les données personnelles "
        "de course ne doivent pas être ajoutées au dépôt public GitHub. "
        "Le fichier de démonstration est fictif."
    )


st.markdown("---")
st.caption(
    "RunBiomechanics · Projet open source en développement · Contributions bienvenues"
)
