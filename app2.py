import streamlit as st
import numpy as np
import pandas as pd
import time


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="DAS Simulation",
    page_icon="📡",
    layout="wide"
)


# ============================================================
# CUSTOM CSS
# ============================================================

st.markdown(
    """
    <style>

    .main-title {
        font-size: 42px;
        font-weight: 700;
        color: #26364a;
        margin-bottom: 5px;
    }

    .subtitle {
        font-size: 17px;
        color: #7a8491;
        margin-bottom: 25px;
    }

    .info-box {
        background-color: #fff9df;
        border-left: 5px solid #e0b000;
        padding: 14px 18px;
        border-radius: 6px;
        color: #665800;
        margin-bottom: 25px;
    }

    .status-normal {
        background-color: #28b463;
        color: white;
        padding: 9px 20px;
        border-radius: 8px;
        font-weight: bold;
        display: inline-block;
    }

    .status-warning {
        background-color: #f39c12;
        color: white;
        padding: 9px 20px;
        border-radius: 8px;
        font-weight: bold;
        display: inline-block;
    }

    .status-danger {
        background-color: #e74c3c;
        color: white;
        padding: 9px 20px;
        border-radius: 8px;
        font-weight: bold;
        display: inline-block;
    }

    .metric-box {
        background-color: #f4f7fa;
        border-radius: 10px;
        padding: 15px;
        text-align: center;
        border: 1px solid #e1e6eb;
    }

    </style>
    """,
    unsafe_allow_html=True
)


# ============================================================
# HEADER
# ============================================================

st.markdown(
    '<div class="main-title">DAS-Based Landslide Monitoring</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="subtitle">LIVE DAS SIMULATION — Synthetic data for demonstration</div>',
    unsafe_allow_html=True
)

st.markdown(
    """
    <div class="info-box">
        Simulation only — this demonstrates DAS behaviour using synthetic data.
    </div>
    """,
    unsafe_allow_html=True
)


# ============================================================
# SIDEBAR - SIMULATION CONTROLS
# ============================================================

st.sidebar.header("DAS Simulation Controls")

strain_level = st.sidebar.slider(
    "Ground Strain",
    min_value=0.0,
    max_value=10.0,
    value=2.0,
    step=0.1
)

vibration_level = st.sidebar.slider(
    "Ground Vibration",
    min_value=0.0,
    max_value=10.0,
    value=2.0,
    step=0.1
)

movement_level = st.sidebar.slider(
    "Slope Movement",
    min_value=0.0,
    max_value=10.0,
    value=2.0,
    step=0.1
)


# ============================================================
# RISK CALCULATION
# ============================================================

risk_score = (
    strain_level * 0.4
    + vibration_level * 0.25
    + movement_level * 0.35
)


if risk_score < 3.0:

    status = "NORMAL"
    status_class = "status-normal"

elif risk_score < 6.0:

    status = "WARNING"
    status_class = "status-warning"

else:

    status = "LANDSLIDE RISK"
    status_class = "status-danger"


# ============================================================
# STATUS
# ============================================================

col1, col2 = st.columns([4, 1])

with col2:

    st.markdown(
        '<div class="' + status_class + '">STATUS: '
        + status
        + '</div>',
        unsafe_allow_html=True
    )


# ============================================================
# DAS MONITORED SLOPE VISUALIZATION
# ============================================================

st.markdown(
    """
    <div style="
        background: linear-gradient(180deg, #10192c, #17243a);
        padding: 18px;
        border-radius: 10px;
        margin-top: 10px;
        color: white;
    ">

    <div style="
        text-align:center;
        font-size:18px;
        font-weight:bold;
        margin-bottom:12px;
    ">
        HIMALAYAN MOUNTAIN ROAD — DAS-MONITORED SLOPE
    </div>

    <svg width="100%" height="360" viewBox="0 0 1200 360">

        <!-- Mountain -->
        <polygon
            points="100,55 190,105 320,135 450,165 580,195
                    670,225 720,280 800,305 875,270
                    960,255 1060,280 1150,300
                    1150,350 100,350"
            fill="#9aa98e"
        />

        <!-- Road -->
        <polyline
            points="100,55 190,105 320,135 450,165 580,195
                    670,225 720,280 800,305 875,270
                    960,255 1060,280 1150,300"
            fill="none"
            stroke="#555555"
            stroke-width="15"
        />

        <!-- DAS cable -->
        <polyline
            points="100,55 190,105 320,135 450,165 580,195
                    670,225 720,280 800,305 875,270
                    960,255 1060,280 1150,300"
            fill="none"
            stroke="#ffd21c"
            stroke-width="5"
            stroke-dasharray="15,10"
        />

        <!-- DAS Interrogator -->
        <rect
            x="20"
            y="35"
            width="130"
            height="65"
            rx="8"
            fill="#15263e"
            stroke="#4db9ff"
            stroke-width="3"
        />

        <text
            x="85"
            y="62"
            fill="#ffffff"
            font-size="16"
            text-anchor="middle"
            font-weight="bold"
        >
            DAS
        </text>

        <text
            x="85"
            y="84"
            fill="#4db9ff"
            font-size="14"
            text-anchor="middle"
        >
            INTERROGATOR
        </text>

        <!-- Cable label -->
        <text
            x="600"
            y="345"
            fill="#ffd21c"
            font-size="15"
            text-anchor="middle"
            font-weight="bold"
        >
            BURIED FIBER-OPTIC DAS CABLE
        </text>

    </svg>

    </div>
    """,
    unsafe_allow_html=True
)


# ============================================================
# SENSOR METRICS
# ============================================================

st.markdown("### DAS Sensor Readings")

m1, m2, m3, m4 = st.columns(4)

with m1:

    st.markdown(
        '<div class="metric-box">'
        '<b>Strain</b><br>'
        + str(round(strain_level, 2))
        + ' με</div>',
        unsafe_allow_html=True
    )

with m2:

    st.markdown(
        '<div class="metric-box">'
        '<b>Vibration</b><br>'
        + str(round(vibration_level, 2))
        + ' mm/s</div>',
        unsafe_allow_html=True
    )

with m3:

    st.markdown(
        '<div class="metric-box">'
        '<b>Slope Movement</b><br>'
        + str(round(movement_level, 2))
        + ' mm</div>',
        unsafe_allow_html=True
    )

with m4:

    st.markdown(
        '<div class="metric-box">'
        '<b>Risk Score</b><br>'
        + str(round(risk_score, 2))
        + '</div>',
        unsafe_allow_html=True
    )


# ============================================================
# SYNTHETIC DAS SIGNAL
# ============================================================

st.markdown("### Live DAS Signal")

x = np.linspace(0, 20, 500)

noise = np.random.normal(
    0,
    0.08 + vibration_level * 0.02,
    500
)

signal = (
    np.sin(x * 2)
    * (0.3 + strain_level * 0.08)
    + noise
)

if movement_level > 5:

    signal = signal + np.sin(x * 8) * movement_level * 0.05


signal_df = pd.DataFrame(
    {
        "DAS Signal": signal
    },
    index=x
)

st.line_chart(signal_df, height=300)


# ============================================================
# INTERPRETATION
# ============================================================

st.markdown("### Monitoring Interpretation")

if status == "NORMAL":

    st.success(
        "Ground conditions are currently stable. "
        "DAS sensor readings are within the normal range."
    )

elif status == "WARNING":

    st.warning(
        "Abnormal ground activity detected. "
        "The slope should be monitored closely."
    )

else:

    st.error(
        "High ground movement detected. "
        "Potential landslide activity requires immediate attention."
    )


# ============================================================
# AUTO SIMULATION
# ============================================================

st.markdown("### Automatic DAS Demonstration")

if st.button("▶ Start Live Simulation"):

    progress = st.progress(0)

    for i in range(101):

        progress.progress(i)

        time.sleep(0.02)

    st.success(
        "DAS simulation completed successfully."
    )


# ============================================================
# FOOTER
# ============================================================

st.markdown("---")

st.caption(
    "DAS-Based Landslide Monitoring | Synthetic Demonstration"
)