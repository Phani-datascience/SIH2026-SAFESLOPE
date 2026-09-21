// =====================================================
// LANDSLIDE RISK INTELLIGENCE DASHBOARD
// =====================================================


// =====================================================
// 1. LOAD RISK SUMMARY
// =====================================================

async function loadRiskData() {

    try {

        const response = await fetch(
            "http://127.0.0.1:8000/risk"
        );

        const data = await response.json();

        document.getElementById("highRisk").innerText =
            data.high ?? 0;

        document.getElementById("mediumRisk").innerText =
            data.medium ?? 0;

        document.getElementById("lowRisk").innerText =
            data.low ?? 0;

    } catch (error) {

        console.error(
            "Risk data loading error:",
            error
        );

    }

}


// =====================================================
// 2. LOAD RISK MAP
// =====================================================

async function loadRiskMap() {

    try {

        const response = await fetch(
            "http://127.0.0.1:8000/locations"
        );

        const locations = await response.json();

        console.log(
            "Total locations received:",
            locations.length
        );


        // CREATE MAP

        const map = L.map("riskMap").setView(
            [27.35, 88.60],
            8
        );


        // OPEN STREET MAP

        L.tileLayer(
            "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
            {
                attribution:
                    "&copy; OpenStreetMap contributors"
            }
        ).addTo(map);


        // ADD MARKERS

        locations.forEach(function (location) {

            let markerColor = "#24ad6b";


            if (
                String(location.risk_level).toUpperCase()
                === "HIGH"
            ) {

                markerColor = "#ef4050";

            }

            else if (
                String(location.risk_level).toUpperCase()
                === "MEDIUM"
            ) {

                markerColor = "#f3a712";

            }


            const marker = L.circleMarker(

                [
                    location.latitude,
                    location.longitude
                ],

                {
                    radius: 10,

                    color: "#ffffff",

                    weight: 3,

                    fillColor: markerColor,

                    fillOpacity: 1,

                    opacity: 1
                }

            ).addTo(map);


            marker.bindPopup(`

                <div style="min-width:190px;">

                    <h3>
                        Landslide Risk
                    </h3>

                    <b>Risk Level:</b>
                    ${location.risk_level}

                    <br><br>

                    <b>Risk Score:</b>
                    ${Number(location.risk_score).toFixed(3)}

                    <br><br>

                    <b>Rainfall (24h):</b>
                    ${Number(location.rainfall_24h).toFixed(2)}
                    mm

                    <br><br>

                    <b>Latitude:</b>
                    ${Number(location.latitude).toFixed(4)}

                    <br>

                    <b>Longitude:</b>
                    ${Number(location.longitude).toFixed(4)}

                </div>

            `);

        });


        // FIT MAP TO LOCATIONS

        if (locations.length > 0) {

            const bounds = L.latLngBounds(

                locations.map(function (location) {

                    return [
                        location.latitude,
                        location.longitude
                    ];

                })

            );

            map.fitBounds(
                bounds,
                {
                    padding: [30, 30]
                }
            );

        }

    } catch (error) {

        console.error(
            "Map loading error:",
            error
        );

    }

}


// =====================================================
// 3. LOAD RAINFALL CHART
// =====================================================

async function loadRainfallChart() {

    try {

        const response = await fetch(
            "http://127.0.0.1:8000/rainfall"
        );

        const data = await response.json();


        const canvas =
            document.getElementById("rainfallChart");


        if (!canvas) {

            console.error(
                "rainfallChart canvas not found"
            );

            return;

        }


        new Chart(

            canvas,

            {

                type: "bar",

                data: {

                    labels: [
                        "24 Hours",
                        "3 Days",
                        "7 Days"
                    ],

                    datasets: [

                        {

                            label:
                                "Average Rainfall (mm)",

                            data: [

                                Number(
                                    data.rainfall_24h
                                ),

                                Number(
                                    data.rainfall_3day
                                ),

                                Number(
                                    data.rainfall_7day
                                )

                            ],

                            borderWidth: 1,

                            borderRadius: 8

                        }

                    ]

                },

                options: {

                    responsive: true,

                    maintainAspectRatio: false,

                    plugins: {

                        legend: {

                            display: true

                        }

                    },

                    scales: {

                        y: {

                            beginAtZero: true,

                            title: {

                                display: true,

                                text: "Rainfall (mm)"

                            }

                        }

                    }

                }

            }

        );

    } catch (error) {

        console.error(
            "Rainfall chart loading error:",
            error
        );

    }

}


// =====================================================
// 4. DAS SIMULATION
// =====================================================

function openSimulator() {

    window.open(
        "http://localhost:8503",
        "_blank"
    );

}


// =====================================================
// 5. INCIDENT REPORTING
// =====================================================

function openReporting() {

    window.open(
        "http://localhost:8516",
        "_blank"
    );

}


// =====================================================
// 6. SATELLITE INTELLIGENCE
// =====================================================

function openAerialView() {

    window.open(
        "https://sih-hackathon-m9srkgsxsfs4kmg7mt3zyn.streamlit.app",
        "_blank"
    );

}


// =====================================================
// 7. START DASHBOARD
// =====================================================

loadRiskData();

loadRiskMap();

loadRainfallChart();
// ============================================================
// LOGIN + SESSION
// ============================================================

document.addEventListener("DOMContentLoaded", function () {

    const loginScreen =
        document.getElementById("loginScreen");

    const loggedIn =
        localStorage.getItem("landslideLoggedIn");

    if (loggedIn === "true") {

        loginScreen.style.display = "none";

    } else {

        loginScreen.style.display = "flex";

    }

});


async function loginUser() {

    const username =
        document.getElementById("loginUsername").value.trim();

    const password =
        document.getElementById("loginPassword").value;

    const message =
        document.getElementById("loginMessage");


    if (!username || !password) {

        message.innerText =
            "Please enter username and password.";

        message.style.color = "red";

        return;
    }


    try {

        const response = await fetch(
            "http://127.0.0.1:8000/login",
            {
                method: "POST",

                headers: {
                    "Content-Type": "application/json"
                },

                body: JSON.stringify({
                    username: username,
                    password: password
                })
            }
        );


        const data = await response.json();


        if (response.ok) {

            // Save login status
            localStorage.setItem(
                "landslideLoggedIn",
                "true"
            );

            localStorage.setItem(
                "landslideUsername",
                username
            );


            message.innerText =
                "Login successful!";

            message.style.color = "green";


            // Hide login screen
            document.getElementById(
                "loginScreen"
            ).style.display = "none";


        } else {

            message.innerText =
                data.detail ||
                "Invalid username or password.";

            message.style.color = "red";

        }


    } catch (error) {

        console.error(
            "Login error:",
            error
        );

        message.innerText =
            "Unable to connect to server.";

        message.style.color = "red";

    }

}