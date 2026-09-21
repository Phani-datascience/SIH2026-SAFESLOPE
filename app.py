# ============================================================
# LANDSLIDE RISK INTELLIGENCE BACKEND
# Local Dataset + CRNS + Acoustic Emission
# ============================================================

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta
import sqlite3
import hashlib
from fastapi import HTTPException
from pydantic import BaseModel



# ============================================================
# APP
# ============================================================

app = FastAPI(
    title="Landslide Risk Intelligence API"
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# ============================================================
# AUTHENTICATION
# ============================================================

AUTH_DB = os.path.join(
    os.path.dirname(__file__),
    "users.db"
)


class RegisterRequest(BaseModel):
    username: str
    password: str


class LoginRequest(BaseModel):
    username: str
    password: str


def hash_password(password):
    return hashlib.sha256(
        password.encode()
    ).hexdigest()


def init_auth_db():

    connection = sqlite3.connect(AUTH_DB)
    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)

    connection.commit()
    connection.close()


init_auth_db()


# ============================================================
# REGISTER API
# ============================================================

@app.post("/register")
def register(data: RegisterRequest):

    connection = sqlite3.connect(AUTH_DB)
    cursor = connection.cursor()

    try:

        cursor.execute(
            """
            INSERT INTO users (username, password)
            VALUES (?, ?)
            """,
            (
                data.username,
                hash_password(data.password)
            )
        )

        connection.commit()

    except sqlite3.IntegrityError:

        connection.close()

        raise HTTPException(
            status_code=400,
            detail="Username already exists"
        )

    connection.close()

    return {
        "message": "Registration successful"
    }


# ============================================================
# LOGIN API
# ============================================================

@app.post("/login")
def login(data: LoginRequest):

    connection = sqlite3.connect(AUTH_DB)
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT username, password
        FROM users
        WHERE username = ?
        """,
        (data.username,)
    )

    user = cursor.fetchone()

    connection.close()

    if user is None:

        raise HTTPException(
            status_code=401,
            detail="Invalid username or password"
        )

    if hash_password(data.password) != user[1]:

        raise HTTPException(
            status_code=401,
            detail="Invalid username or password"
        )

    return {
        "message": "Login successful",
        "username": data.username
    }


# ============================================================
# DATASET
# ============================================================

DATASET_PATH = os.path.join(
    os.path.dirname(__file__),
    "prediction_dataset.csv"
)


def load_dataset():

    if not os.path.exists(DATASET_PATH):

        raise FileNotFoundError(
            "prediction_dataset.csv not found inside backend folder"
        )

    return pd.read_csv(DATASET_PATH)


# ============================================================
# HOME / API STATUS
# ============================================================

@app.get("/")
def home():

    return {
        "message": "Landslide Risk Intelligence API is running",
        "status": "online"
    }


# ============================================================
# RISK SUMMARY
# ============================================================

@app.get("/risk")
def get_risk():

    df = load_dataset()

    risk = (
        df["risk_level"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    return {
        "high": int((risk == "HIGH").sum()),
        "medium": int((risk == "MEDIUM").sum()),
        "low": int((risk == "LOW").sum())
    }


# ============================================================
# RISK LOCATIONS
# ============================================================

@app.get("/locations")
def get_locations():

    df = load_dataset()

    locations = []

    for _, row in df.iterrows():

        try:

            locations.append({

                "latitude": float(
                    row["latitude"]
                ),

                "longitude": float(
                    row["longitude"]
                ),

                "rainfall_24h": float(
                    row["rainfall_24h"]
                ),

                "risk_level": str(
                    row["risk_level"]
                ).strip().upper(),

                "risk_score": float(
                    row["risk_score"]
                )

            })

        except (ValueError, TypeError):
            continue

    return locations


# ============================================================
# RAINFALL SUMMARY
# ============================================================

@app.get("/rainfall")
def get_rainfall():

    df = load_dataset()

    return {

        "rainfall_24h": float(
            df["rainfall_24h"].mean()
        ),

        "rainfall_3day": float(
            df["rainfall_3day"].mean()
        ),

        "rainfall_7day": float(
            df["rainfall_7day"].mean()
        )

    }


# ============================================================
# CRNS CONSTANTS
# ============================================================

A0 = 0.0808
A1 = 0.372
A2 = 0.115

N0 = 1000.0

WATCH_MOISTURE = 0.25
CRITICAL_MOISTURE = 0.35


# ============================================================
# CRNS STATE
# ============================================================

crns_history = []

crns_hour = 0

crns_soil_moisture = 0.105

crns_virtual_time = datetime(
    2026,
    7,
    1,
    0,
    0
)


# ============================================================
# DESILETS EQUATION
# ============================================================

def desilets_smc(
    neutron_count,
    reference_count
):

    ratio = neutron_count / reference_count

    ratio = max(
        ratio,
        A1 + 0.01
    )

    theta = (
        A0 /
        (ratio - A1)
    ) - A2

    return float(
        np.clip(
            theta,
            0.0,
            0.60
        )
    )


# ============================================================
# CRNS OBSERVATION
# ============================================================

def generate_crns_observation(hour):

    global crns_soil_moisture
    global crns_virtual_time


    # --------------------------------------------------------
    # RAINFALL SCENARIO
    # --------------------------------------------------------

    if hour < 30:

        rainfall = np.random.gamma(
            0.35,
            0.6
        )

    elif hour < 48:

        rainfall = np.random.gamma(
            1.0,
            1.8
        )

    elif hour < 78:

        rainfall = np.random.gamma(
            2.0,
            4.5
        )

    elif hour < 105:

        rainfall = np.random.gamma(
            2.8,
            6.5
        )

    else:

        rainfall = np.random.gamma(
            0.65,
            1.8
        )


    # --------------------------------------------------------
    # MONSOON BURSTS
    # --------------------------------------------------------

    if (
        55 <= hour <= 100
        and np.random.random() < 0.12
    ):

        rainfall += np.random.uniform(
            8,
            18
        )


    # --------------------------------------------------------
    # SOIL MOISTURE
    # --------------------------------------------------------

    previous = crns_soil_moisture

    infiltration = (
        rainfall * 0.00155
    )

    drainage = (
        0.0008
        + max(previous - 0.28, 0)
        * 0.003
    )

    target_moisture = (
        previous
        + infiltration
        - drainage
    )

    target_moisture = np.clip(
        target_moisture,
        0.08,
        0.48
    )

    new_moisture = (
        0.82 * previous
        + 0.18 * target_moisture
    )

    crns_soil_moisture = float(
        new_moisture
    )


    # --------------------------------------------------------
    # PRESSURE
    # --------------------------------------------------------

    pressure = (

        1013.0

        + 3.0 *
        np.sin(hour / 17.0)

        + np.random.normal(
            0,
            0.6
        )

    )


    # --------------------------------------------------------
    # NEUTRON RESPONSE
    # --------------------------------------------------------

    dry_moisture = 0.10

    moisture_effect = (
        new_moisture
        - dry_moisture
    ) * 850.0

    normal_neutrons = 850.0

    sensor_noise = np.random.normal(
        0,
        9.0
    )

    raw_neutrons = (
        normal_neutrons
        - moisture_effect
        + sensor_noise
    )

    raw_neutrons = float(
        np.clip(
            raw_neutrons,
            430,
            900
        )
    )


    # --------------------------------------------------------
    # ATMOSPHERIC CORRECTION
    # --------------------------------------------------------

    corrected_neutrons = (
        raw_neutrons
        * (1013.0 / pressure)
    )


    # --------------------------------------------------------
    # DESILETS MOISTURE
    # --------------------------------------------------------

    calculated_moisture = desilets_smc(
        corrected_neutrons,
        N0
    )

    calculated_moisture = (
        0.82 * calculated_moisture
        + 0.18 * new_moisture
    )


    # --------------------------------------------------------
    # RECENT RAINFALL
    # --------------------------------------------------------

    rainfall_24h = (

        sum(
            x["rainfall"]
            for x in crns_history[-23:]
        )
        + rainfall

    )

    rainfall_72h = (

        sum(
            x["rainfall"]
            for x in crns_history[-71:]
        )
        + rainfall

    )


    # --------------------------------------------------------
    # DATASET ML SUSCEPTIBILITY
    # --------------------------------------------------------

    df = load_dataset()

    ml_susceptibility = float(
        df["risk_score"].mean()
    )

    ml_susceptibility = float(
        np.clip(
            ml_susceptibility,
            0,
            1
        )
    )


    # --------------------------------------------------------
    # MOISTURE SCORE
    # --------------------------------------------------------

    moisture_score = np.clip(

        (
            calculated_moisture
            - 0.10
        )
        /
        (
            CRITICAL_MOISTURE
            - 0.10
        ),

        0,
        1

    )


    # --------------------------------------------------------
    # RAINFALL SCORE
    # --------------------------------------------------------

    rainfall_score = np.clip(

        rainfall_72h / 180.0,

        0,
        1

    )


    # --------------------------------------------------------
    # ENVIRONMENTAL RISK
    # --------------------------------------------------------

    risk_score = (

        0.45 *
        ml_susceptibility

        + 0.35 *
        moisture_score

        + 0.20 *
        rainfall_score

    )

    risk_score = float(
        np.clip(
            risk_score,
            0,
            1
        )
    )


    # --------------------------------------------------------
    # WARNING
    # --------------------------------------------------------

    if (

        calculated_moisture
        >= CRITICAL_MOISTURE

        and rainfall_72h >= 80

        and risk_score >= 0.75

    ):

        warning = "CRITICAL"


    elif (

        calculated_moisture
        >= WATCH_MOISTURE

        or rainfall_72h >= 50

        or risk_score >= 0.55

    ):

        warning = "WATCH"


    else:

        warning = "NORMAL"


    # --------------------------------------------------------
    # RESULT
    # --------------------------------------------------------

    observation = {

        "timestamp":
            crns_virtual_time.isoformat(),

        "simulation_hour":
            hour,

        "rainfall":
            float(rainfall),

        "rainfall_24h":
            float(rainfall_24h),

        "rainfall_72h":
            float(rainfall_72h),

        "pressure":
            float(pressure),

        "raw_neutrons":
            float(raw_neutrons),

        "corrected_neutrons":
            float(corrected_neutrons),

        "soil_moisture":
            float(calculated_moisture),

        "ml_susceptibility":
            float(ml_susceptibility),

        "risk_score":
            float(risk_score),

        "warning":
            warning

    }

    crns_virtual_time += timedelta(
        hours=1
    )

    return observation


# ============================================================
# CRNS ENDPOINT
# ============================================================

@app.get("/crns")
def get_crns():

    global crns_hour

    observation = generate_crns_observation(
        crns_hour
    )

    crns_history.append(
        observation
    )

    if len(crns_history) > 120:

        del crns_history[:-120]

    crns_hour += 1

    return observation


# ============================================================
# ACOUSTIC EMISSION
# ============================================================

ae_step = 0


def generate_ae_observation(step):

    rng = np.random.default_rng(
        5000 + step
    )

    phase = step % 240


    # --------------------------------------------------------
    # DAMAGE PROGRESSION
    # --------------------------------------------------------

    if phase < 60:

        damage = (
            0.05
            + 0.08 * phase / 60
        )

    elif phase < 140:

        damage = (
            0.13
            + 0.52 *
            (phase - 60) / 80
        )

    elif phase < 185:

        damage = (
            0.65
            + 0.22 *
            (phase - 140) / 45
        )

    else:

        damage = max(
            0.16,
            0.87
            - 0.71 *
            (phase - 185) / 55
        )


    # --------------------------------------------------------
    # SIGNAL
    # --------------------------------------------------------

    fs = 2000

    seconds = 3.0

    t = np.arange(
        int(fs * seconds)
    ) / fs


    raw = (
        0.025 *
        rng.normal(
            size=len(t)
        )
    )


    raw += (

        0.012 *
        np.sin(
            2 *
            np.pi *
            38 *
            t
        )

        +

        0.008 *
        np.sin(
            2 *
            np.pi *
            75 *
            t
        )

    )


    # --------------------------------------------------------
    # AE EVENTS
    # --------------------------------------------------------

    n_events = int(
        2 + damage * 24
    )


    for _ in range(n_events):

        center = rng.uniform(
            0.15,
            seconds - 0.15
        )

        freq = rng.uniform(
            80,
            550
        )

        amp = (
            rng.uniform(
                0.16,
                0.55
            )
            *
            (0.7 + damage)
        )

        width = rng.uniform(
            0.004,
            0.016
        )


        raw += (

            amp *

            np.exp(
                -(
                    (
                        t - center
                    ) / width
                ) ** 2
            )

            *

            np.sin(
                2 *
                np.pi *
                freq *
                (t - center)
            )

        )


    # --------------------------------------------------------
    # FILTER
    # --------------------------------------------------------

    filtered = np.convolve(
        raw,
        np.ones(13) / 13,
        mode="same"
    )

    envelope = np.abs(
        filtered
    )

    threshold = 0.10


    events = int(

        np.sum(

            (
                envelope[1:]
                >= threshold
            )

            &

            (
                envelope[:-1]
                < threshold
            )

        )

    )


    events = max(
        1,
        min(events, 80)
    )


    # --------------------------------------------------------
    # PEAK / ENERGY
    # --------------------------------------------------------

    peak = float(
        np.max(
            np.abs(raw)
        )
    )

    energy = float(
        np.sum(
            raw ** 2
        )
    )

    energy_index = min(
        100,
        energy / 42
    )

    rate = (
        events /
        seconds *
        60
    )


    # --------------------------------------------------------
    # DOMINANT FREQUENCY
    # --------------------------------------------------------

    spectrum = np.abs(
        np.fft.rfft(raw)
    )

    freqs = np.fft.rfftfreq(
        len(raw),
        1 / fs
    )

    band = (
        (freqs >= 40)
        &
        (freqs <= 800)
    )

    dominant = float(

        freqs[band][

            np.argmax(
                spectrum[band]
            )

        ]

    )


    # --------------------------------------------------------
    # AE ANOMALY
    # --------------------------------------------------------

    anomaly = float(

        np.clip(

            0.40 *
            (rate / 350)

            + 0.25 *
            (energy_index / 100)

            + 0.20 *
            min(
                1,
                peak / 1.2
            )

            + 0.15 *
            damage,

            0,
            1

        )

    )


    # --------------------------------------------------------
    # AE STATUS
    # --------------------------------------------------------

    status = (

        "CRITICAL"

        if anomaly >= 0.72

        else

        "WATCH"

        if anomaly >= 0.42

        else

        "NORMAL"

    )


    return {

        "events_per_minute":
            float(rate),

        "peak_amplitude":
            float(peak),

        "energy_index":
            float(energy_index),

        "dominant_frequency":
            float(dominant),

        "damage":
            float(damage),

        "anomaly":
            float(anomaly),

        "status":
            status

    }


# ============================================================
# AE ENDPOINT
# ============================================================

@app.get("/ae")
def get_ae():

    global ae_step

    observation = generate_ae_observation(
        ae_step
    )

    ae_step += 1

    return observation


# ============================================================
# COMBINED RISK
# ============================================================

@app.get("/combined-risk")
def get_combined_risk():

    global crns_hour
    global ae_step


    # --------------------------------------------------------
    # CRNS
    # --------------------------------------------------------

    crns = generate_crns_observation(
        crns_hour
    )

    crns_history.append(
        crns
    )

    if len(crns_history) > 120:

        del crns_history[:-120]

    crns_hour += 1


    # --------------------------------------------------------
    # AE
    # --------------------------------------------------------

    ae = generate_ae_observation(
        ae_step
    )

    ae_step += 1


    # --------------------------------------------------------
    # COMBINE
    # --------------------------------------------------------

    environmental_score = (
        crns["risk_score"]
    )

    ae_score = (
        ae["anomaly"]
    )


    combined_score = (

        0.70 *
        environmental_score

        + 0.30 *
        ae_score

    )


    combined_score = float(
        np.clip(
            combined_score,
            0,
            1
        )
    )


    # --------------------------------------------------------
    # FINAL STATUS
    # --------------------------------------------------------

    if combined_score >= 0.75:

        status = "CRITICAL"

    elif combined_score >= 0.55:

        status = "WATCH"

    else:

        status = "NORMAL"


    # --------------------------------------------------------
    # RESPONSE
    # --------------------------------------------------------

    return {

        "timestamp":
            crns["timestamp"],

        "risk_score":
            combined_score,

        "risk_percent":
            combined_score * 100,

        "status":
            status,

        "rainfall_24h":
            crns["rainfall_24h"],

        "rainfall_72h":
            crns["rainfall_72h"],

        "pressure":
            crns["pressure"],

        "raw_neutrons":
            crns["raw_neutrons"],

        "corrected_neutrons":
            crns["corrected_neutrons"],

        "soil_moisture":
            crns["soil_moisture"],

        "ml_susceptibility":
            crns["ml_susceptibility"],

        "acoustic_emission":
            ae["anomaly"],

        "ae_events_per_minute":
            ae["events_per_minute"],

        "ae_peak":
            ae["peak_amplitude"],

        "ae_energy_index":
            ae["energy_index"],

        "dominant_frequency":
            ae["dominant_frequency"],

        "damage":
            ae["damage"],

        "ae_status":
            ae["status"]

    }


# ============================================================
# DATASET INFORMATION
# ============================================================

@app.get("/dataset-info")
def dataset_info():

    df = load_dataset()

    return {

        "rows":
            int(len(df)),

        "columns":
            list(df.columns),

        "source":
            "Local prediction_dataset.csv"

    }


# ============================================================
# WEBSITE
# ============================================================
# IMPORTANT:
# Keep this AFTER all API routes.
# Website will open at /app/
# ============================================================

FRONTEND_PATH = os.path.join(
    os.path.dirname(__file__),
    ".."
)

app.mount(
    "/app",
    StaticFiles(
        directory=FRONTEND_PATH,
        html=True
    ),
    name="frontend"
)