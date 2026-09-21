import sqlite3
import uuid
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st


# ============================================================
# APPLICATION CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Live Disaster Field Reporting",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ============================================================
# PATHS
# ============================================================

APP_DIR = Path(__file__).parent

DB_PATH = APP_DIR / "field_reports.db"

UPLOAD_DIR = APP_DIR / "uploads"

UPLOAD_DIR.mkdir(exist_ok=True)


# ============================================================
# OPTIONS
# ============================================================

OBSERVATION_TYPES = [
    "LANDSLIDE",
    "FLOOD",
    "EARTHQUAKE",
    "CYCLONE",
    "FIRE",
    "OTHER"
]

SEVERITIES = [
    "LOW",
    "MEDIUM",
    "HIGH",
    "CRITICAL"
]

STATUSES = [
    "NEW",
    "UNDER_REVIEW",
    "VERIFIED",
    "REJECTED"
]


# ============================================================
# DATABASE CONNECTION
# ============================================================

def get_connection():

    connection = sqlite3.connect(DB_PATH)

    connection.row_factory = sqlite3.Row

    return connection


# ============================================================
# CREATE DATABASE
# ============================================================

def init_database():

    with get_connection() as connection:

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS field_reports (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                report_id TEXT UNIQUE NOT NULL,

                officer_name TEXT NOT NULL,

                officer_id TEXT NOT NULL,

                latitude REAL NOT NULL,

                longitude REAL NOT NULL,

                location_name TEXT NOT NULL,

                observation_type TEXT NOT NULL,

                severity TEXT NOT NULL,

                description TEXT,

                photo_path TEXT,

                video_path TEXT,

                created_at TEXT NOT NULL,

                status TEXT NOT NULL

            )
            """
        )

        connection.commit()


init_database()


# ============================================================
# SAVE UPLOADED FILE
# ============================================================

def save_uploaded_file(uploaded_file):

    if uploaded_file is None:

        return None

    extension = Path(
        uploaded_file.name
    ).suffix

    filename = (
        f"{uuid.uuid4()}{extension}"
    )

    file_path = UPLOAD_DIR / filename

    with open(file_path, "wb") as file:

        file.write(
            uploaded_file.getbuffer()
        )

    return str(file_path)


# ============================================================
# CREATE REPORT
# ============================================================

def create_report(
    officer_name,
    officer_id,
    latitude,
    longitude,
    location_name,
    observation_type,
    severity,
    description,
    photo_file,
    video_file
):

    report_id = (
        "IR-"
        + datetime.now().strftime("%Y%m%d")
        + "-"
        + uuid.uuid4().hex[:6].upper()
    )

    created_at = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    photo_path = save_uploaded_file(
        photo_file
    )

    video_path = save_uploaded_file(
        video_file
    )

    with get_connection() as connection:

        connection.execute(
            """
            INSERT INTO field_reports (

                report_id,
                officer_name,
                officer_id,
                latitude,
                longitude,
                location_name,
                observation_type,
                severity,
                description,
                photo_path,
                video_path,
                created_at,
                status

            )

            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,

            (
                report_id,
                officer_name,
                officer_id,
                latitude,
                longitude,
                location_name,
                observation_type,
                severity,
                description,
                photo_path,
                video_path,
                created_at,
                "NEW"
            )
        )

        connection.commit()

    return report_id


# ============================================================
# GET ALL REPORTS
# ============================================================

def get_all_reports():

    with get_connection() as connection:

        dataframe = pd.read_sql_query(
            """
            SELECT *
            FROM field_reports
            ORDER BY created_at DESC
            """,
            connection
        )

    return dataframe


# ============================================================
# UPDATE STATUS
# ============================================================

def update_status(report_id, status):

    with get_connection() as connection:

        connection.execute(
            """
            UPDATE field_reports
            SET status = ?
            WHERE report_id = ?
            """,
            (
                status,
                report_id
            )
        )

        connection.commit()


# ============================================================
# CUSTOM CSS
# ============================================================

st.markdown(
    """
    <style>

    .main-title {
        font-size: 38px;
        font-weight: 800;
        color: #10233f;
        margin-bottom: 5px;
    }

    .subtitle {
        font-size: 16px;
        color: #6b7b91;
        margin-bottom: 25px;
    }

    .section-title {
        font-size: 25px;
        font-weight: 750;
        color: #10233f;
        margin-top: 20px;
        margin-bottom: 10px;
    }

    .sidebar-title {
        font-size: 24px;
        font-weight: 800;
        color: white;
    }

    .sidebar-subtitle {
        color: #b9c9dd;
        font-size: 13px;
    }

    .status-box {
        padding: 14px;
        border-radius: 12px;
        background: #123a67;
        color: white;
        font-weight: 600;
        margin-top: 20px;
    }

    </style>
    """,
    unsafe_allow_html=True
)


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.markdown(
        '<div class="sidebar-title">◆ LIVE<br>REPORTING</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="sidebar-subtitle">Disaster Management System</div>',
        unsafe_allow_html=True
    )

    st.markdown("---")

    st.markdown("### OPERATIONS")

    page = st.radio(
        "Navigation",
        [
            "🏠 Dashboard",
            "🗺️ Live Map",
            "📝 New Report",
            "📋 All Reports",
            "📊 Analytics"
        ],
        label_visibility="collapsed"
    )

    st.markdown("---")

    st.markdown(
        """
        <div class="status-box">
        ● Backend Connected
        </div>
        """,
        unsafe_allow_html=True
    )

    st.caption(
        "Local SQLite reporting system"
    )


# ============================================================
# LOAD DATA
# ============================================================

reports_df = get_all_reports()


# ============================================================
# DASHBOARD
# ============================================================

if page == "🏠 Dashboard":

    st.markdown(
        '<div class="main-title">Operations Dashboard</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="subtitle">Real-time overview of field disaster reports.</div>',
        unsafe_allow_html=True
    )


    # --------------------------------------------------------
    # NEW REPORT BUTTON
    # --------------------------------------------------------

    if st.button(
        "＋ New Report",
        type="primary"
    ):

        st.session_state["open_new_report"] = True


    # --------------------------------------------------------
    # METRICS
    # --------------------------------------------------------

    if reports_df.empty:

        total_reports = 0

        high_risk = 0

        verified = 0

        locations = 0

    else:

        total_reports = len(
            reports_df
        )

        high_risk = len(
            reports_df[
                reports_df["severity"].isin(
                    ["HIGH", "CRITICAL"]
                )
            ]
        )

        verified = len(
            reports_df[
                reports_df["status"] == "VERIFIED"
            ]
        )

        locations = reports_df[
            "location_name"
        ].nunique()


    st.markdown(
        "### Overview"
    )

    col1, col2, col3, col4 = st.columns(4)


    with col1:

        st.metric(
            "TOTAL REPORTS",
            total_reports
        )


    with col2:

        st.metric(
            "⚠ HIGH RISK",
            high_risk
        )


    with col3:

        st.metric(
            "✓ VERIFIED",
            verified
        )


    with col4:

        st.metric(
            "📍 LOCATIONS",
            locations
        )


    st.markdown("")


    # --------------------------------------------------------
    # RECENT REPORTS
    # --------------------------------------------------------

    left_col, right_col = st.columns(
        [2, 1]
    )


    with left_col:

        st.markdown(
            "### Recent Reports"
        )

        if reports_df.empty:

            st.info(
                "No incident reports submitted yet."
            )

        else:

            recent = reports_df[
                [
                    "report_id",
                    "location_name",
                    "observation_type",
                    "severity",
                    "status",
                    "created_at"
                ]
            ].head(8)

            st.dataframe(
                recent,
                use_container_width=True,
                hide_index=True
            )


    with right_col:

        st.markdown(
            "### Report Types"
        )

        if reports_df.empty:

            st.info(
                "Report type analytics will appear here."
            )

        else:

            type_counts = (
                reports_df[
                    "observation_type"
                ]
                .value_counts()
            )

            st.bar_chart(
                type_counts
            )


# ============================================================
# NEW REPORT
# ============================================================

elif page == "📝 New Report":

    st.markdown(
        '<div class="main-title">New Incident Report</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="subtitle">Submit a new field disaster incident.</div>',
        unsafe_allow_html=True
    )


    with st.form(
        "incident_report_form"
    ):

        st.markdown(
            "### Reporter Information"
        )

        col1, col2 = st.columns(2)


        with col1:

            officer_name = st.text_input(
                "Officer / Reporter Name"
            )


        with col2:

            officer_id = st.text_input(
                "Officer ID"
            )


        st.markdown(
            "### Incident Location"
        )

        col1, col2, col3 = st.columns(3)


        with col1:

            latitude = st.number_input(
                "Latitude",
                value=27.3300,
                format="%.6f"
            )


        with col2:

            longitude = st.number_input(
                "Longitude",
                value=88.6100,
                format="%.6f"
            )


        with col3:

            location_name = st.text_input(
                "Location Name"
            )


        st.markdown(
            "### Incident Details"
        )

        col1, col2 = st.columns(2)


        with col1:

            observation_type = st.selectbox(
                "Incident Type",
                OBSERVATION_TYPES
            )


        with col2:

            severity = st.selectbox(
                "Severity",
                SEVERITIES
            )


        description = st.text_area(
            "Incident Description",
            height=140
        )


        st.markdown(
            "### Evidence"
        )

        photo_file = st.file_uploader(
            "Upload Photo",
            type=[
                "jpg",
                "jpeg",
                "png",
                "webp"
            ]
        )


        video_file = st.file_uploader(
            "Upload Video",
            type=[
                "mp4",
                "mov",
                "avi"
            ]
        )


        submitted = st.form_submit_button(
            "🚨 Submit Incident Report",
            type="primary"
        )


        if submitted:

            if officer_name.strip() == "":

                st.error(
                    "Please enter reporter name."
                )

            elif officer_id.strip() == "":

                st.error(
                    "Please enter Officer ID."
                )

            elif location_name.strip() == "":

                st.error(
                    "Please enter location name."
                )

            elif description.strip() == "":

                st.error(
                    "Please enter incident description."
                )

            else:

                report_id = create_report(
                    officer_name,
                    officer_id,
                    latitude,
                    longitude,
                    location_name,
                    observation_type,
                    severity,
                    description,
                    photo_file,
                    video_file
                )

                st.success(
                    f"Incident report submitted successfully! "
                    f"Report ID: {report_id}"
                )


# ============================================================
# LIVE MAP
# ============================================================

elif page == "🗺️ Live Map":

    st.markdown(
        '<div class="main-title">Live Incident Map</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="subtitle">Geographic overview of reported incident locations.</div>',
        unsafe_allow_html=True
    )


    if reports_df.empty:

        st.info(
            "No incident locations available yet."
        )

    else:

        map_data = reports_df[
            [
                "latitude",
                "longitude",
                "location_name",
                "severity",
                "observation_type"
            ]
        ].copy()


        st.map(
            map_data[
                [
                    "latitude",
                    "longitude"
                ]
            ]
        )


        st.markdown(
            "### Reported Locations"
        )

        st.dataframe(
            map_data,
            use_container_width=True,
            hide_index=True
        )


# ============================================================
# ALL REPORTS
# ============================================================

elif page == "📋 All Reports":

    st.markdown(
        '<div class="main-title">All Reports</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="subtitle">Complete list of submitted incident reports.</div>',
        unsafe_allow_html=True
    )


    if reports_df.empty:

        st.info(
            "No reports submitted yet."
        )

    else:

        st.dataframe(
            reports_df,
            use_container_width=True,
            hide_index=True
        )


        st.markdown(
            "### Update Report Status"
        )

        report_ids = reports_df[
            "report_id"
        ].tolist()


        selected_report = st.selectbox(
            "Select Report",
            report_ids
        )


        selected_status = st.selectbox(
            "New Status",
            STATUSES
        )


        if st.button(
            "Update Status"
        ):

            update_status(
                selected_report,
                selected_status
            )

            st.success(
                "Report status updated successfully."
            )

            st.rerun()


# ============================================================
# ANALYTICS
# ============================================================

elif page == "📊 Analytics":

    st.markdown(
        '<div class="main-title">Incident Analytics</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="subtitle">Summary of reported incidents and severity levels.</div>',
        unsafe_allow_html=True
    )


    if reports_df.empty:

        st.info(
            "Analytics will appear after reports are submitted."
        )

    else:

        col1, col2 = st.columns(2)


        with col1:

            st.markdown(
                "### Severity Distribution"
            )

            severity_counts = (
                reports_df[
                    "severity"
                ]
                .value_counts()
            )

            st.bar_chart(
                severity_counts
            )


        with col2:

            st.markdown(
                "### Incident Type Distribution"
            )

            type_counts = (
                reports_df[
                    "observation_type"
                ]
                .value_counts()
            )

            st.bar_chart(
                type_counts
            )


        st.markdown(
            "### Report Status"
        )

        status_counts = (
            reports_df[
                "status"
            ]
            .value_counts()
        )

        st.bar_chart(
            status_counts
        )


# ============================================================
# END
# ============================================================