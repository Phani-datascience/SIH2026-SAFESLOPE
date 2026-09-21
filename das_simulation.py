import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, FancyBboxPatch
import time


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="DAS Simulation",
    page_icon="🏔️",
    layout="wide"
)


# ============================================================
# TITLE
# ============================================================

st.title("DAS-Based Landslide Monitoring")

st.caption(
    "LIVE DAS SIMULATION — Synthetic data for demonstration"
)

st.warning(
    "Simulation only — this demonstrates DAS behaviour using synthetic data."
)


# ============================================================
# CONFIGURATION
# ============================================================

FIBER_LENGTH = 1000.0
SPATIAL_RESOLUTION = 2.0

EVENT_LOCATION = 623.0

WAVE_SPEED = 115.0
ATTENUATION = 0.003

FREQUENCIES = (3.0, 8.5, 17.0)
FREQ_WEIGHTS = (1.0, 0.4, 0.2)

RISE_TIME = 0.35
DECAY_TIME = 3.0

DETECTION_THRESHOLD = 0.35

CYCLE_SECONDS = 12.0
EVENT_TIME_IN_CYCLE = 4.0

BACKGROUND_NOISE = 0.03

FPS = 10

np.random.seed(42)


# ============================================================
# FIBER GRID
# ============================================================

x = np.arange(
    0.0,
    FIBER_LENGTH + SPATIAL_RESOLUTION,
    SPATIAL_RESOLUTION
)

n_points = len(x)


# ============================================================
# TERRAIN
# ============================================================

def terrain_elevation(x):

    base = 480 - 0.22 * x

    rng = np.random.RandomState(7)

    coarse = rng.normal(
        0,
        1,
        size=13
    )

    smooth_noise = np.interp(
        x,
        np.linspace(
            0,
            FIBER_LENGTH,
            13
        ),
        coarse
    ) * 9

    dip = -55 * np.exp(
        -0.5 *
        ((x - EVENT_LOCATION) / 55.0) ** 2
    )

    return base + smooth_noise + dip


ELEVATION = terrain_elevation(x)


# ============================================================
# VIBRATION ENVELOPE
# ============================================================

def causal_envelope(tau, rise, decay):

    env = np.zeros_like(tau)

    mask = tau >= 0

    env[mask] = (
        1.0 -
        np.exp(-tau[mask] / rise)
    ) * np.exp(
        -tau[mask] / decay
    )

    return env


# ============================================================
# DAS VIBRATION MODEL
# ============================================================

def vibration_amplitude(cycle_t):

    dist = np.abs(
        x - EVENT_LOCATION
    )

    arrival_delay = (
        dist / WAVE_SPEED
    )

    tau = (
        cycle_t -
        EVENT_TIME_IN_CYCLE -
        arrival_delay
    )

    attenuation = np.exp(
        -ATTENUATION * dist
    )

    envelope = causal_envelope(
        tau,
        RISE_TIME,
        DECAY_TIME
    )

    waveform = np.zeros_like(tau)

    for f, w in zip(
        FREQUENCIES,
        FREQ_WEIGHTS
    ):

        waveform += (
            w *
            np.sin(
                2 *
                np.pi *
                f *
                tau
            )
        )

    event_signal = (
        attenuation *
        envelope *
        waveform
    )

    noise = (
        BACKGROUND_NOISE *
        np.random.randn(n_points)
    )

    return event_signal + noise


# ============================================================
# STREAMLIT PLACEHOLDER
# ============================================================

scene_placeholder = st.empty()

signal_placeholder = st.empty()


# ============================================================
# SIMULATION LOOP
# ============================================================

start_time = time.time()

dust_rng = np.random.RandomState(11)


while True:

    elapsed = time.time() - start_time

    cycle_t = (
        elapsed %
        CYCLE_SECONDS
    )


    # ========================================================
    # CALCULATE VIBRATION
    # ========================================================

    amplitude = vibration_amplitude(
        cycle_t
    )


    peak_amp = float(
        np.max(
            np.abs(amplitude)
        )
    )


    above = (
        np.abs(amplitude)
        > DETECTION_THRESHOLD
    )


    # ========================================================
    # ESTIMATE EVENT LOCATION
    # ========================================================

    if above.any():

        idx_above = np.where(
            above
        )[0]

        weights = (
            amplitude[idx_above] ** 2
        )

        estimated_location = float(
            np.average(
                x[idx_above],
                weights=weights
            )
        )

    else:

        estimated_location = None


    # ========================================================
    # DETERMINE STATE
    # ========================================================

    time_since_event = (
        cycle_t -
        EVENT_TIME_IN_CYCLE
    )


    if (
        not above.any()
        or
        time_since_event < 0
    ):

        state = "NORMAL"

    elif time_since_event < 1.0:

        state = "ANOMALY"

    else:

        state = "HIGH_RISK"


    # ========================================================
    # COLORS
    # ========================================================

    status_colors = {

        "NORMAL": "#27ae60",

        "ANOMALY": "#f39c12",

        "HIGH_RISK": "#c0392b"

    }


    fiber_colors = {

        "NORMAL": "#f1c40f",

        "ANOMALY": "#e67e22",

        "HIGH_RISK": "#e74c3c"

    }


    # ========================================================
    # CREATE FIGURE
    # ========================================================

    fig, axes = plt.subplots(
        2,
        1,
        figsize=(13, 8),
        gridspec_kw={
            "height_ratios": [1.6, 1]
        }
    )


    ax_scene = axes[0]

    ax_signal = axes[1]


    fig.patch.set_facecolor(
        "#0e1420"
    )


    ax_scene.set_facecolor(
        "#0e1420"
    )

    ax_signal.set_facecolor(
        "#0b0f18"
    )


    # ========================================================
    # MOUNTAIN
    # ========================================================

    poly_y = np.concatenate(
        [
            ELEVATION,
            np.full_like(
                ELEVATION,
                ELEVATION.min() - 40
            )
        ]
    )


    poly_x = np.concatenate(
        [
            x,
            x[::-1]
        ]
    )


    slope_color = (
        "#6b5240"
        if state == "HIGH_RISK"
        else "#5b6b57"
    )


    ax_scene.add_patch(
        Polygon(
            np.column_stack(
                [
                    poly_x,
                    poly_y
                ]
            ),
            closed=True,
            facecolor=slope_color,
            edgecolor="none"
        )
    )


    # ========================================================
    # UNSTABLE ZONE
    # ========================================================

    unstable_lo = (
        EVENT_LOCATION - 70
    )

    unstable_hi = (
        EVENT_LOCATION + 70
    )


    ax_scene.axvspan(
        unstable_lo,
        unstable_hi,
        color="#c0392b",
        alpha=(
            0.10
            if state == "NORMAL"
            else 0.22
        )
    )


    # ========================================================
    # ROAD
    # ========================================================

    road_y = (
        ELEVATION - 10
    )


    ax_scene.plot(
        x,
        road_y,
        color="#3a3a3a",
        linewidth=7
    )


    ax_scene.plot(
        x,
        road_y,
        color="#9a9a9a",
        linewidth=1.2,
        linestyle=(0, (6, 6))
    )


    # ========================================================
    # TREES
    # ========================================================

    tree_x = np.arange(
        20,
        FIBER_LENGTH,
        45
    )


    tree_x = tree_x[
        (tree_x < unstable_lo - 15)
        |
        (tree_x > unstable_hi + 15)
    ]


    tree_y = (
        np.interp(
            tree_x,
            x,
            ELEVATION
        ) + 6
    )


    ax_scene.scatter(
        tree_x,
        tree_y,
        marker="^",
        s=45,
        color="#2e5339",
        edgecolor="#1c3320"
    )


    # ========================================================
    # BURIED FIBER
    # ========================================================

    fiber_y = (
        road_y - 6
    )


    ax_scene.plot(
        x,
        fiber_y,
        color=fiber_colors[state],
        linewidth=2.4,
        linestyle=(0, (4, 2))
    )


    ax_scene.text(
        FIBER_LENGTH * 0.42,
        fiber_y.min() - 22,
        "BURIED FIBER-OPTIC DAS CABLE",
        color=fiber_colors[state],
        fontsize=9,
        fontweight="bold",
        ha="center"
    )


    # ========================================================
    # DAS INTERROGATOR
    # ========================================================

    bx = -78
    bw = 72


    ax_scene.add_patch(
        FancyBboxPatch(
            (
                bx,
                fiber_y[0] - 19
            ),
            bw,
            38,
            boxstyle="round,pad=2",
            facecolor="#1b2838",
            edgecolor="#5dade2",
            linewidth=1.4
        )
    )


    ax_scene.text(
        bx + bw / 2,
        fiber_y[0],
        "DAS\nINTERROGATOR",
        color="#5dade2",
        fontsize=7,
        fontweight="bold",
        ha="center",
        va="center"
    )


    ax_scene.plot(
        [
            bx + bw,
            x[0]
        ],
        [
            fiber_y[0],
            fiber_y[0]
        ],
        color="#5dade2",
        linewidth=1.6
    )


    # ========================================================
    # LANDSLIDE DUST
    # ========================================================

    if state in (
        "ANOMALY",
        "HIGH_RISK"
    ):

        n = 35


        px = (
            EVENT_LOCATION
            +
            dust_rng.uniform(
                -45,
                45,
                n
            )
        )


        py = (
            np.interp(
                px,
                x,
                ELEVATION
            )
            +
            dust_rng.uniform(
                2,
                22,
                n
            )
        )


        ax_scene.scatter(
            px,
            py,
            s=dust_rng.uniform(
                2,
                9,
                n
            ),
            color="#8d6e63",
            alpha=0.55
        )


    # ========================================================
    # STATUS
    # ========================================================

    ax_scene.text(
        0.985,
        0.90,
        f" STATUS: {state.replace('_', ' ')} ",
        transform=ax_scene.transAxes,
        ha="right",
        va="top",
        fontsize=12,
        fontweight="bold",
        color="white",
        bbox=dict(
            boxstyle="round,pad=0.4",
            facecolor=status_colors[state],
            edgecolor="none"
        )
    )


    # ========================================================
    # SCENE SETTINGS
    # ========================================================

    ax_scene.set_xlim(
        bx - 20,
        FIBER_LENGTH + 20
    )


    ax_scene.set_ylim(
        ELEVATION.min() - 55,
        ELEVATION.max() + 40
    )


    ax_scene.set_yticks([])


    ax_scene.set_xlabel(
        "Distance along fiber (m)",
        color="#cccccc"
    )


    ax_scene.set_title(
        "HIMALAYAN MOUNTAIN ROAD — DAS-MONITORED SLOPE",
        fontsize=10,
        color="#e8e8e8",
        fontweight="bold"
    )


    # ========================================================
    # VIBRATION GRAPH
    # ========================================================

    ax_signal.plot(
        x,
        amplitude,
        color="#2ecc71",
        linewidth=1.4
    )


    ax_signal.axhline(
        DETECTION_THRESHOLD,
        color="#e74c3c",
        linestyle="--",
        linewidth=1,
        label="Detection threshold"
    )


    ax_signal.set_xlim(
        0,
        FIBER_LENGTH
    )


    ax_signal.set_ylim(
        -1.0,
        1.2
    )


    ax_signal.set_xlabel(
        "Distance along fiber (m)",
        color="#cccccc"
    )


    ax_signal.set_ylabel(
        "DAS vibration amplitude",
        color="#cccccc"
    )


    ax_signal.set_title(
        "LIVE DISTRIBUTED VIBRATION — ENTIRE FIBER",
        fontsize=10,
        color="#dddddd",
        loc="left"
    )


    ax_signal.legend(
        loc="upper right",
        fontsize=8
    )


    # ========================================================
    # STATUS INFORMATION
    # ========================================================

    estimated_text = (
        f"{estimated_location:.1f} m"
        if estimated_location is not None
        else "n/a"
    )


    status_text = (
        f"TRUE EVENT LOCATION: {EVENT_LOCATION:.0f} m    "
        f"ESTIMATED: {estimated_text}\n"
        f"PEAK AMPLITUDE: {peak_amp:.2f}    "
        f"THRESHOLD: {DETECTION_THRESHOLD:.2f}    "
        f"STATE: {state.replace('_', ' ')}"
    )


    ax_signal.text(
        0.01,
        0.90,
        status_text,
        transform=ax_signal.transAxes,
        fontsize=9,
        color="#eeeeee",
        family="monospace",
        va="top",
        bbox=dict(
            boxstyle="round,pad=0.4",
            facecolor="#1b2838",
            edgecolor="#444444"
        )
    )


    # ========================================================
    # LAYOUT
    # ========================================================

    plt.tight_layout(
        rect=[
            0,
            0,
            1,
            0.97
        ]
    )


    # ========================================================
    # SHOW IN STREAMLIT
    # ========================================================

    scene_placeholder.pyplot(
        fig,
        clear_figure=True
    )


    plt.close(fig)


    # ========================================================
    # ANIMATION SPEED
    # ========================================================

    time.sleep(
        1 / FPS
    )