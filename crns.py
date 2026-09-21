import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import time
from datetime import datetime, timedelta

# ============================================================
# PAGE
# ============================================================

st.set_page_config(
    page_title="CRNS Live Landslide Monitor",
    page_icon="◉",
    layout="wide"
)

st.markdown("""
<style>
.block-container {padding-top: 1.2rem; padding-bottom: 1rem;}
.live-dot {
    display:inline-block; width:10px; height:10px; border-radius:50%;
    background:#21c55d; margin-right:7px;
    box-shadow:0 0 10px #21c55d;
}
.status-box {
    padding:12px 16px; border-radius:10px; text-align:center;
    border:1px solid rgba(255,255,255,.15);
}
.small-label {font-size:12px; color:#8b949e;}
.big-value {font-size:24px; font-weight:700;}
</style>
""", unsafe_allow_html=True)

# ============================================================
# CONSTANTS
# ============================================================

A0 = 0.0808
A1 = 0.372
A2 = 0.115

N0 = 1000.0

WATCH_MOISTURE = 0.25
CRITICAL_MOISTURE = 0.35

# ============================================================
# SESSION STATE
# ============================================================

defaults = {
    "history": [],
    "sim_hour": 0,
    "soil_moisture": 0.105,
    "running": True,
    "virtual_time": datetime(2026, 7, 1, 0, 0),
    "last_update": time.time(),
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value

# ============================================================
# DESILETS CONVERSION
# ============================================================

def desilets_smc(neutron_count, reference_count):
    ratio = neutron_count / reference_count
    ratio = max(ratio, A1 + 0.01)
    theta = (A0 / (ratio - A1)) - A2
    return float(np.clip(theta, 0.0, 0.60))

# ============================================================
# GENERATE ONE REALISTIC OBSERVATION
# ============================================================

def generate_observation(hour):
    """
    Synthetic demonstration scenario:
    dry period -> rainfall onset -> heavy monsoon -> recovery.
    The environmental state changes gradually.
    """

    # -----------------------------
    # Rainfall scenario
    # -----------------------------
    if hour < 30:
        rainfall = np.random.gamma(0.35, 0.6)

    elif hour < 48:
        rainfall = np.random.gamma(1.0, 1.8)

    elif hour < 78:
        rainfall = np.random.gamma(2.0, 4.5)

    elif hour < 105:
        rainfall = np.random.gamma(2.8, 6.5)

    else:
        rainfall = np.random.gamma(0.65, 1.8)

    # Occasional monsoon bursts
    if 55 <= hour <= 100 and np.random.random() < 0.12:
        rainfall += np.random.uniform(8, 18)

    # -----------------------------
    # Soil moisture dynamics
    # -----------------------------
    previous = st.session_state.soil_moisture

    infiltration = rainfall * 0.00155
    drainage = 0.0008 + max(previous - 0.28, 0) * 0.003

    target_moisture = previous + infiltration - drainage
    target_moisture = np.clip(target_moisture, 0.08, 0.48)

    # Slow soil response
    new_moisture = (
        0.82 * previous +
        0.18 * target_moisture
    )

    st.session_state.soil_moisture = float(new_moisture)

    # -----------------------------
    # Atmospheric conditions
    # -----------------------------
    pressure = (
        1013.0
        + 3.0 * np.sin(hour / 17.0)
        + np.random.normal(0, 0.6)
    )

    # -----------------------------
    # Neutron response
    # -----------------------------
    # More hydrogen/water -> lower neutron population.
    dry_moisture = 0.10
    moisture_effect = (new_moisture - dry_moisture) * 850.0

    normal_neutrons = 850.0
    sensor_noise = np.random.normal(0, 9.0)

    raw_neutrons = (
        normal_neutrons
        - moisture_effect
        + sensor_noise
    )

    raw_neutrons = float(np.clip(raw_neutrons, 430, 900))

    # -----------------------------
    # Atmospheric correction
    # -----------------------------
    corrected_neutrons = raw_neutrons * (1013.0 / pressure)

    # -----------------------------
    # Desilets estimate
    # -----------------------------
    calculated_moisture = desilets_smc(
        corrected_neutrons,
        N0
    )

    # Keep measurement response smooth for the demo
    calculated_moisture = (
        0.82 * calculated_moisture
        + 0.18 * new_moisture
    )

    # -----------------------------
    # Recent rainfall
    # -----------------------------
    previous_records = st.session_state.history

    rainfall_24h = (
        sum(x["Rainfall"] for x in previous_records[-23:])
        + rainfall
    )

    rainfall_72h = (
        sum(x["Rainfall"] for x in previous_records[-71:])
        + rainfall
    )

    # -----------------------------
    # Existing XGBoost susceptibility
    # -----------------------------
    # Replace this constant with the selected location's
    # actual prediction when integrating with Databricks.
    ml_susceptibility = 0.82

    # -----------------------------
    # Risk calculation
    # -----------------------------
    moisture_score = np.clip(
        (calculated_moisture - 0.10) /
        (CRITICAL_MOISTURE - 0.10),
        0,
        1
    )

    rainfall_score = np.clip(
        rainfall_72h / 180.0,
        0,
        1
    )

    risk_score = (
        0.45 * ml_susceptibility +
        0.35 * moisture_score +
        0.20 * rainfall_score
    )

    risk_score = float(np.clip(risk_score, 0, 1))

    # -----------------------------
    # Warning logic
    # -----------------------------
    if (
        calculated_moisture >= CRITICAL_MOISTURE
        and rainfall_72h >= 80
        and risk_score >= 0.75
    ):
        warning = "CRITICAL"

    elif (
        calculated_moisture >= WATCH_MOISTURE
        or rainfall_72h >= 50
        or risk_score >= 0.55
    ):
        warning = "WATCH"

    else:
        warning = "NORMAL"

    current_virtual_time = st.session_state.virtual_time

    observation = {
        "Timestamp": current_virtual_time,
        "Simulation_Hour": hour,
        "Rainfall": float(rainfall),
        "Rainfall_24h": float(rainfall_24h),
        "Rainfall_72h": float(rainfall_72h),
        "Pressure": float(pressure),
        "Raw_Neutrons": raw_neutrons,
        "Corrected_Neutrons": float(corrected_neutrons),
        "Soil_Moisture": float(calculated_moisture),
        "Risk": risk_score,
        "ML_Susceptibility": ml_susceptibility,
        "Warning": warning,
    }

    st.session_state.virtual_time += timedelta(hours=1)

    return observation

# ============================================================
# HEADER
# ============================================================

head1, head2 = st.columns([4, 1])

with head1:
    st.title("CRNS LANDSLIDE MONITOR")
    st.caption(
        "Cosmic-Ray Neutron Sensing • Soil Moisture • "
        "Multi-Signal Risk Assessment"
    )

with head2:
    st.markdown(
        '<div class="status-box">'
        '<span class="live-dot"></span>'
        '<b>LIVE MONITORING</b>'
        '</div>',
        unsafe_allow_html=True
    )

# ============================================================
# CONTROLS
# ============================================================

c1, c2, c3 = st.columns([1, 1, 5])

with c1:
    if st.button(
        "⏸ Pause" if st.session_state.running else "▶ Resume",
        use_container_width=True
    ):
        st.session_state.running = not st.session_state.running

with c2:
    if st.button("↻ Reset", use_container_width=True):
        st.session_state.history = []
        st.session_state.sim_hour = 0
        st.session_state.soil_moisture = 0.105
        st.session_state.virtual_time = datetime(2026, 7, 1, 0, 0)

# ============================================================
# GENERATE DATA
# ============================================================

if st.session_state.running:
    observation = generate_observation(
        st.session_state.sim_hour
    )

    st.session_state.history.append(observation)
    st.session_state.history = st.session_state.history[-120:]
    st.session_state.sim_hour += 1

df = pd.DataFrame(st.session_state.history)

if df.empty:
    st.info("Waiting for first CRNS observation...")
    st.stop()

latest = df.iloc[-1]

# ============================================================
# STATUS
# ============================================================

if latest["Warning"] == "CRITICAL":
    status = "CRITICAL WARNING"
    status_color = "#ff453a"

elif latest["Warning"] == "WATCH":
    status = "WATCH"
    status_color = "#ffb020"

else:
    status = "NORMAL"
    status_color = "#30d158"

# ============================================================
# METRICS
# ============================================================

m1, m2, m3, m4, m5 = st.columns(5)

m1.metric(
    "Corrected Neutrons",
    f"{latest['Corrected_Neutrons']:.0f} cps"
)

m2.metric(
    "Estimated Soil Moisture",
    f"{latest['Soil_Moisture'] * 100:.1f}%"
)

m3.metric(
    "Rainfall — 24h",
    f"{latest['Rainfall_24h']:.1f} mm"
)

m4.metric(
    "72h Rainfall",
    f"{latest['Rainfall_72h']:.1f} mm"
)

with m5:
    st.markdown(
        f"""
        <div class="status-box" style="border-color:{status_color};">
            <div class="small-label">SYSTEM STATUS</div>
            <div class="big-value" style="color:{status_color};">
                {status}
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

# ============================================================
# ALERT
# ============================================================

if status == "CRITICAL WARNING":
    st.error(
        "🚨 CRITICAL: Estimated soil moisture and accumulated "
        "rainfall are contributing to elevated landslide risk."
    )

elif status == "WATCH":
    st.warning(
        "⚠️ WATCH: Environmental conditions are becoming "
        "unfavorable in the monitored high-susceptibility area."
    )

else:
    st.success(
        "✓ NORMAL: No critical environmental condition detected."
    )

# ============================================================
# CHART HELPERS
# ============================================================

def base_layout(height=360):
    return dict(
        height=height,
        margin=dict(l=45, r=20, t=45, b=45),
        hovermode="x unified",
        template="plotly_dark",
        legend=dict(orientation="h")
    )

# ============================================================
# ROW 1 — NEUTRONS + SOIL MOISTURE
# ============================================================

left, right = st.columns(2)

with left:
    st.subheader("CRNS Neutron Signal")

    fig1 = go.Figure()

    fig1.add_trace(
        go.Scatter(
            x=df["Timestamp"],
            y=df["Raw_Neutrons"],
            mode="lines",
            name="Raw",
            line=dict(width=1.5)
        )
    )

    fig1.add_trace(
        go.Scatter(
            x=df["Timestamp"],
            y=df["Corrected_Neutrons"],
            mode="lines",
            name="Corrected",
            line=dict(width=2.5)
        )
    )

    fig1.update_layout(
        **base_layout(),
        xaxis_title="Observation Time",
        yaxis_title="Neutron Count (cps)"
    )

    st.plotly_chart(
        fig1,
        use_container_width=True,
        key="neutron_chart"
    )

with right:
    st.subheader("Estimated Soil Moisture")

    fig2 = go.Figure()

    fig2.add_trace(
        go.Scatter(
            x=df["Timestamp"],
            y=df["Soil_Moisture"] * 100,
            mode="lines",
            name="CRNS Estimate",
            line=dict(width=3)
        )
    )

    fig2.add_hline(
        y=WATCH_MOISTURE * 100,
        line_dash="dash",
        annotation_text="WATCH"
    )

    fig2.add_hline(
        y=CRITICAL_MOISTURE * 100,
        line_dash="dash",
        annotation_text="CRITICAL"
    )

    fig2.update_layout(
        **base_layout(),
        xaxis_title="Observation Time",
        yaxis_title="Volumetric Soil Moisture (%)"
    )

    st.plotly_chart(
        fig2,
        use_container_width=True,
        key="moisture_chart"
    )

# ============================================================
# ROW 2 — RAINFALL + RISK
# ============================================================

left2, right2 = st.columns(2)

with left2:
    st.subheader("Rainfall Forcing")

    fig3 = go.Figure()

    fig3.add_trace(
        go.Bar(
            x=df["Timestamp"],
            y=df["Rainfall"],
            name="Hourly Rainfall"
        )
    )

    fig3.update_layout(
        **base_layout(),
        xaxis_title="Observation Time",
        yaxis_title="Rainfall (mm)"
    )

    st.plotly_chart(
        fig3,
        use_container_width=True,
        key="rain_chart"
    )

with right2:
    st.subheader("Combined Landslide Risk")

    fig4 = go.Figure()

    fig4.add_trace(
        go.Scatter(
            x=df["Timestamp"],
            y=df["Risk"],
            mode="lines",
            name="Risk Score",
            line=dict(width=3)
        )
    )

    fig4.add_hline(
        y=0.55,
        line_dash="dash",
        annotation_text="WATCH"
    )

    fig4.add_hline(
        y=0.75,
        line_dash="dash",
        annotation_text="HIGH"
    )

    fig4.update_layout(
        **base_layout(),
        xaxis_title="Observation Time",
        yaxis_title="Risk Score",
        yaxis_range=[0, 1]
    )

    st.plotly_chart(
        fig4,
        use_container_width=True,
        key="risk_chart"
    )

# ============================================================
# LIVE OBSERVATION DETAILS
# ============================================================

st.divider()

st.subheader("Current CRNS Observation")

d1, d2, d3, d4 = st.columns(4)

d1.metric(
    "Raw Neutrons",
    f"{latest['Raw_Neutrons']:.1f} cps"
)

d2.metric(
    "Corrected Neutrons",
    f"{latest['Corrected_Neutrons']:.1f} cps"
)

d3.metric(
    "Atmospheric Pressure",
    f"{latest['Pressure']:.1f} hPa"
)

d4.metric(
    "ML Susceptibility",
    f"{latest['ML_Susceptibility']:.2f}"
)

st.caption(
    f"Latest observation: {latest['Timestamp'].strftime('%d %b %Y, %H:%M')} "
    f"• Prototype hour: {int(latest['Simulation_Hour'])}"
)

# ============================================================
# PHYSICS CALCULATION
# ============================================================

with st.expander("View current Desilets calculation"):

    ratio = latest["Corrected_Neutrons"] / N0

    st.latex(
        r"\theta = \frac{a_0}{(N/N_0)-a_1}-a_2"
    )

    st.write(
        f"**N:** {latest['Corrected_Neutrons']:.2f} cps"
    )

    st.write(f"**N₀:** {N0:.2f} cps")
    st.write(f"**N / N₀:** {ratio:.4f}")
    st.write(
        f"**Estimated volumetric soil moisture:** "
        f"{latest['Soil_Moisture'] * 100:.2f}%"
    )

# ============================================================
# LIVE DATA TABLE
# ============================================================

with st.expander("Live CRNS observation history"):

    display_df = df[
        [
            "Timestamp",
            "Rainfall",
            "Rainfall_24h",
            "Rainfall_72h",
            "Pressure",
            "Raw_Neutrons",
            "Corrected_Neutrons",
            "Soil_Moisture",
            "Risk",
            "Warning"
        ]
    ].copy()

    display_df["Soil_Moisture"] = (
        display_df["Soil_Moisture"] * 100
    ).round(2)

    display_df["Risk"] = display_df["Risk"].round(3)

    st.dataframe(
        display_df.tail(25),
        use_container_width=True,
        hide_index=True
    )

# ============================================================
# ARCHITECTURE
# ============================================================

st.divider()

st.subheader("CRNS Monitoring Pipeline")

st.markdown("""
<div style="
    padding:18px;
    border:1px solid rgba(255,255,255,.12);
    border-radius:12px;
    text-align:center;
    font-size:17px;
">
    Cosmic-Ray Neutrons
    &nbsp; → &nbsp;
    CRNS Detector
    &nbsp; → &nbsp;
    Atmospheric Correction
    &nbsp; → &nbsp;
    Desilets Equation
    &nbsp; → &nbsp;
    Soil Moisture
    &nbsp; → &nbsp;
    Rainfall + XGBoost
    &nbsp; → &nbsp;
    Risk Engine
    &nbsp; → &nbsp;
    Early Warning
</div>
""", unsafe_allow_html=True)

st.caption(
    "Synthetic CRNS observations for software demonstration. "
    "Physical CRNS deployment requires calibrated instrumentation, "
    "site-specific parameters and field validation."
)

# ============================================================
# AUTO UPDATE
# ============================================================

if st.session_state.running:
    time.sleep(1)
    st.rerun()
