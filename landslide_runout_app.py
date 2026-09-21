import io
import os
import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
from rasterio.transform import rowcol
from shapely.geometry import Point, LineString, Polygon
import streamlit as st
import folium
from streamlit_folium import st_folium

st.set_page_config(page_title="Runout — Landslide Field Model", layout="wide", initial_sidebar_state="expanded")

# ----------------------------------------------------------------------------
# DESIGN TOKENS
# Grounded in topographic survey / field-report material: parchment map
# paper, contour-line hachure, surveyor's rust/ochre/moss marking pens.
# ----------------------------------------------------------------------------
# Color   bg #211f1b (umber charcoal)  panel #29261f  paper #efe8d8
#         ink #f1ebdc  muted #a79c86  line #48412f
#         rust #c1502e (risk)  ochre #c99a3a (path)  moss #6f8a56 (impact zone)
# Type    Display: Fraunces (serif, survey-report character)
#         UI: IBM Plex Sans   Data: IBM Plex Mono (coordinates, distances)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,300;9..144,500;9..144,600&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap');

:root{
    --bg:#211f1b; --panel:#29261f; --paper:#efe8d8; --ink:#f1ebdc;
    --muted:#a79c86; --line:#48412f; --rust:#c1502e; --ochre:#c99a3a; --moss:#6f8a56;
}

html, body, [class*="css"]{ font-family:'IBM Plex Sans', sans-serif; color:var(--ink); }
.stApp{
    background-color:var(--bg);
    background-image:
        repeating-linear-gradient(115deg, rgba(241,235,220,0.028) 0px, rgba(241,235,220,0.028) 1px, transparent 1px, transparent 34px),
        repeating-linear-gradient(115deg, rgba(241,235,220,0.018) 0px, rgba(241,235,220,0.018) 1px, transparent 1px, transparent 11px);
}

/* ---- Hero: left-aligned survey masthead, no gradient block, no badge ---- */
.hero{
    border-top:1px solid var(--line);
    border-bottom:1px solid var(--line);
    padding:1.9rem 0 1.6rem 0;
    margin-bottom:1.4rem;
    animation:rise .5s ease-out;
}
@keyframes rise{ from{opacity:0; transform:translateY(6px);} to{opacity:1; transform:translateY(0);} }
.hero .kicker{
    font-family:'IBM Plex Mono', monospace;
    font-size:0.74rem; color:var(--ochre); letter-spacing:0.02em;
    margin-bottom:0.5rem;
}
.hero h1{
    font-family:'Fraunces', serif; font-weight:500; font-style:normal;
    font-size:2.5rem; line-height:1.08; color:var(--ink); margin:0 0 0.55rem 0; max-width:20ch;
}
.hero p{ color:var(--muted); font-size:1rem; max-width:60ch; margin:0; line-height:1.5; }

/* ---- Legend strip: color swatches, not icon soup ---- */
.legend{ display:flex; gap:1.6rem; margin:0.9rem 0 1.3rem 0; flex-wrap:wrap; }
.legend .item{ display:flex; align-items:center; gap:0.5rem; font-size:0.85rem; color:var(--muted); }
.legend .swatch{ width:11px; height:11px; border-radius:2px; display:inline-block; }

/* ---- Stat strip: hairline-divided figures, not shadowed cards ---- */
.stat-strip{
    display:flex; border-top:1px solid var(--line); border-bottom:1px solid var(--line);
    margin-bottom:1.6rem;
}
.stat{ flex:1; padding:0.9rem 1.3rem; border-left:1px solid var(--line); }
.stat:first-child{ border-left:none; }
.stat .n{ font-family:'IBM Plex Mono', monospace; font-weight:500; font-size:1.55rem; color:var(--ink); }
.stat .n.rust{ color:var(--rust); } .stat .n.moss{ color:var(--moss); }
.stat .t{ font-size:0.78rem; color:var(--muted); margin-top:0.15rem; }

/* ---- Section labels ---- */
.section-label{
    font-family:'Fraunces', serif; font-weight:500; font-size:1.15rem;
    color:var(--ink); margin:0.2rem 0 0.7rem 0;
}

/* ---- Sidebar: field-panel look ---- */
section[data-testid="stSidebar"]{ background:var(--panel); border-right:1px solid var(--line); }
section[data-testid="stSidebar"] h2{ font-family:'Fraunces', serif; font-weight:500; color:var(--ink); }
section[data-testid="stSidebar"] .field-label{
    font-family:'IBM Plex Mono', monospace; font-size:0.76rem; color:var(--muted);
    margin:1rem 0 0.3rem 0; border-top:1px solid var(--line); padding-top:0.7rem;
}
section[data-testid="stSidebar"] .field-label:first-of-type{ border-top:none; margin-top:0; padding-top:0; }
.status-line{ font-family:'IBM Plex Mono', monospace; font-size:0.76rem; color:var(--muted); margin:0.15rem 0; }
.status-line.on{ color:var(--moss); }

/* ---- Widgets ---- */
.stButton>button, .stDownloadButton>button{
    border-radius:3px; border:1px solid var(--rust); background:transparent; color:var(--rust);
    font-weight:500; font-family:'IBM Plex Sans', sans-serif;
}
.stButton>button:hover, .stDownloadButton>button:hover{ background:var(--rust); color:var(--paper); }
[data-testid="stDataFrame"]{ border:1px solid var(--line); border-radius:3px; }
.stAlert{ border-radius:3px; border:1px solid var(--line); }
[data-testid="stFileUploader"] section{ background:var(--bg); border:1px dashed var(--line); border-radius:3px; }
.stTabs [data-baseweb="tab"]{ font-family:'IBM Plex Sans', sans-serif; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hero">
    <div class="kicker">DEM-derived slope trace · field estimate, not an engineering model</div>
    <h1>Where the ground goes after it lets go</h1>
    <p>XGBoost marks a slope as likely to fail. This model walks the terrain downhill from each
    point to trace where the debris would probably travel, and checks it against nearby villages and roads.</p>
</div>
""", unsafe_allow_html=True)


def read_risk(file):
    df = pd.read_csv(file)
    cols = {c.lower().strip(): c for c in df.columns}
    lat = cols.get("latitude", cols.get("lat"))
    lon = cols.get("longitude", cols.get("lon", cols.get("lng")))
    if not lat or not lon:
        raise ValueError("Risk CSV must contain latitude/longitude (or lat/lon) columns.")
    if "risk" in cols:
        df = df[df[cols["risk"]].astype(str).str.upper().isin(["HIGH", "VERY HIGH", "1", "TRUE"])]
    return df, lat, lon


def sample_dem(src, lon, lat):
    if src.crs is None:
        raise ValueError("DEM has no CRS.")
    p = gpd.GeoSeries([Point(lon, lat)], crs="EPSG:4326").to_crs(src.crs).iloc[0]
    try:
        r, c = rowcol(src.transform, p.x, p.y)
        if r < 0 or c < 0 or r >= src.height or c >= src.width:
            return None
        return float(src.read(1)[r, c]), p.x, p.y
    except Exception:
        return None


def runout_path(src, x, y, max_distance_m, step_m=30):
    if src.crs.is_geographic:
        raise ValueError("Please use a DEM in a projected CRS with metres (for example a suitable UTM CRS).")

    band = src.read(1, masked=True).astype("float64")
    arr = band.filled(np.nan)

    r, c = rowcol(src.transform, x, y)
    if not (0 <= r < src.height and 0 <= c < src.width) or np.isnan(arr[r, c]):
        raise ValueError("High-risk point is outside the valid DEM area.")

    cell = abs(src.transform.a)
    if abs(src.transform.e) > 0:
        cell = (cell + abs(src.transform.e)) / 2

    gy, gx = np.gradient(arr, cell, cell)
    dx = -gx[r, c]
    dy = -gy[r, c]
    mag = np.hypot(dx, dy)
    if not np.isfinite(mag) or mag < 1e-9:
        return LineString([(x, y)])

    ux, uy = dx / mag, dy / mag
    points = [(x, y)]
    distance = 0.0

    while distance < max_distance_m:
        nx, ny = points[-1][0] + ux * step_m, points[-1][1] + uy * step_m
        rr, cc = rowcol(src.transform, nx, ny)
        if not (0 <= rr < src.height and 0 <= cc < src.width) or np.isnan(arr[rr, cc]):
            break

        ddx = -gx[rr, cc]
        ddy = -gy[rr, cc]
        mm = np.hypot(ddx, ddy)
        if not np.isfinite(mm) or mm < 1e-9:
            break
        if mm < 0.01:
            break

        ux, uy = ddx / mm, ddy / mm
        points.append((nx, ny))
        distance += step_m

    return LineString(points)


def make_corridor(line, width_m):
    return line.buffer(width_m / 2)


# ----------------------------------------------------------------------------
# ----------------------------------------------------------------------------
# SIDEBAR — field control panel
# Bundled Sikkim sample data (sample_data/ next to this script) is used for
# any input the user hasn't uploaded — so the app opens with a working
# example instead of an empty state, and uploading a file simply overrides
# that one input.
# ----------------------------------------------------------------------------
SAMPLE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sample_data")
SAMPLE_DEM = os.path.join(SAMPLE_DIR, "dem_sample.tif")
SAMPLE_RISK = os.path.join(SAMPLE_DIR, "risk_points_sample.csv")
SAMPLE_VILLAGES = os.path.join(SAMPLE_DIR, "villages_sample.geojson")
SAMPLE_ROADS = os.path.join(SAMPLE_DIR, "roads_sample.geojson")
sample_available = os.path.isfile(SAMPLE_DEM) and os.path.isfile(SAMPLE_RISK)

with st.sidebar:
    st.header("Survey inputs")

    if sample_available:
        st.markdown(
            '<div class="status-line on">Showing bundled Sikkim sample data — upload your own files below to replace any of it</div>',
            unsafe_allow_html=True,
        )

    st.markdown('<div class="field-label">01 — Elevation model</div>', unsafe_allow_html=True)
    dem_file = st.file_uploader("DEM (.tif)", type=["tif", "tiff"], label_visibility="collapsed")

    st.markdown('<div class="field-label">02 — High-risk points (XGBoost)</div>', unsafe_allow_html=True)
    risk_file = st.file_uploader("Risk CSV", type=["csv"], label_visibility="collapsed")

    st.markdown('<div class="field-label">03 — Villages (optional)</div>', unsafe_allow_html=True)
    village_file = st.file_uploader("Villages", type=["geojson", "gpkg", "zip"], label_visibility="collapsed")

    st.markdown('<div class="field-label">04 — Roads (optional)</div>', unsafe_allow_html=True)
    road_file = st.file_uploader("Roads", type=["geojson", "gpkg", "zip"], label_visibility="collapsed")

    st.markdown('<div class="field-label">Model parameters</div>', unsafe_allow_html=True)
    max_distance = st.slider("Max runout distance (m)", 100, 3000, 500, 50)
    width = st.slider("Runout width (m)", 20, 500, 100, 10)

    st.markdown('<div class="field-label">Layer status</div>', unsafe_allow_html=True)
    for label, uploaded, sample_ok in [
        ("dem.tif", dem_file is not None, os.path.isfile(SAMPLE_DEM)),
        ("risk.csv", risk_file is not None, os.path.isfile(SAMPLE_RISK)),
        ("villages", village_file is not None, os.path.isfile(SAMPLE_VILLAGES)),
        ("roads", road_file is not None, os.path.isfile(SAMPLE_ROADS)),
    ]:
        if uploaded:
            cls, mark = "status-line on", "loaded"
        elif sample_ok:
            cls, mark = "status-line", "sample"
        else:
            cls, mark = "status-line", "—"
        st.markdown(f'<div class="{cls}">{label} · {mark}</div>', unsafe_allow_html=True)

# Resolve each input: an upload always wins; otherwise fall back to the
# bundled sample; if neither exists, it's genuinely missing.
dem_source = dem_file if dem_file is not None else (SAMPLE_DEM if os.path.isfile(SAMPLE_DEM) else None)
risk_source = risk_file if risk_file is not None else (SAMPLE_RISK if os.path.isfile(SAMPLE_RISK) else None)
village_source = village_file if village_file is not None else (SAMPLE_VILLAGES if os.path.isfile(SAMPLE_VILLAGES) else None)
road_source = road_file if road_file is not None else (SAMPLE_ROADS if os.path.isfile(SAMPLE_ROADS) else None)

if dem_source is None or risk_source is None:
    st.info("Load a DEM and the risk CSV in the sidebar to trace the first runout.")
    with st.expander("Expected risk CSV format"):
        st.code("latitude,longitude,risk\n13.512,75.821,HIGH\n13.489,75.803,HIGH\n13.527,75.835,LOW", language="text")
        st.caption("Only HIGH / VERY HIGH rows are used when a risk column is present.")
    st.stop()

try:
    risk_df, lat_col, lon_col = read_risk(risk_source)
except Exception as e:
    st.error(str(e))
    st.stop()

dem_bytes = dem_source.getvalue() if hasattr(dem_source, "getvalue") else open(dem_source, "rb").read()

with rasterio.MemoryFile(dem_bytes) as mem:
    with mem.open() as src:
        if src.crs is None:
            st.error("DEM must have a coordinate reference system (CRS).")
            st.stop()

        results = []
        paths = []
        zones = []

        with st.spinner("Walking each point downhill across the DEM..."):
            for idx, row in risk_df.iterrows():
                lat, lon = float(row[lat_col]), float(row[lon_col])
                sampled = sample_dem(src, lon, lat)
                if sampled is None:
                    results.append({"id": idx, "latitude": lat, "longitude": lon, "status": "Outside DEM"})
                    continue

                _, x, y = sampled
                try:
                    line = runout_path(src, x, y, max_distance)
                    zone = make_corridor(line, width)
                    paths.append((idx, line))
                    zones.append((idx, zone))

                    affected_villages = []
                    affected_roads = []
                    if village_source:
                        vg = gpd.read_file(village_source)
                        if vg.crs != src.crs:
                            vg = vg.to_crs(src.crs)
                        hits = vg[vg.geometry.intersects(zone)]
                        affected_villages = hits.index.astype(str).tolist()

                    if road_source:
                        rd = gpd.read_file(road_source)
                        if rd.crs != src.crs:
                            rd = rd.to_crs(src.crs)
                        hits = rd[rd.geometry.intersects(zone)]
                        affected_roads = hits.index.astype(str).tolist()

                    results.append({
                        "id": idx,
                        "latitude": lat,
                        "longitude": lon,
                        "status": "Processed",
                        "runout_m": round(line.length, 1),
                        "affected_villages": ", ".join(affected_villages) if affected_villages else "None / not uploaded",
                        "affected_roads": ", ".join(affected_roads) if affected_roads else "None / not uploaded",
                    })
                except Exception as e:
                    results.append({"id": idx, "latitude": lat, "longitude": lon, "status": f"Error: {e}"})

        out = pd.DataFrame(results)

        # --------------------------------------------------------------
        # LEGEND + STAT STRIP
        # --------------------------------------------------------------
        st.markdown("""
        <div class="legend">
            <div class="item"><span class="swatch" style="background:#c1502e"></span>High-risk point</div>
            <div class="item"><span class="swatch" style="background:#c99a3a"></span>Traced runout</div>
            <div class="item"><span class="swatch" style="background:#6f8a56"></span>Impact corridor</div>
        </div>
        """, unsafe_allow_html=True)

        n_total = len(out)
        n_processed = int((out["status"] == "Processed").sum()) if "status" in out else 0
        n_flagged = int((out["affected_villages"] != "None / not uploaded").sum()) if "affected_villages" in out.columns else 0
        avg_runout = round(out.loc[out["status"] == "Processed", "runout_m"].mean(), 1) if n_processed else 0

        st.markdown(f"""
        <div class="stat-strip">
            <div class="stat"><div class="n">{n_total}</div><div class="t">Points submitted</div></div>
            <div class="stat"><div class="n moss">{n_processed}</div><div class="t">Runouts traced</div></div>
            <div class="stat"><div class="n rust">{n_flagged}</div><div class="t">Villages in corridor</div></div>
            <div class="stat"><div class="n">{avg_runout} m</div><div class="t">Average runout length</div></div>
        </div>
        """, unsafe_allow_html=True)

        tab_map, tab_table, tab_export = st.tabs(["Map", "Results", "Export"])

        processed = [p for p in paths]

        with tab_map:
            if processed:
                all_points = [pt for _, line in processed for pt in line.coords]
                center_x = np.mean([p[0] for p in all_points])
                center_y = np.mean([p[1] for p in all_points])
                center = gpd.GeoSeries([Point(center_x, center_y)], crs=src.crs).to_crs("EPSG:4326").iloc[0]

                m = folium.Map(location=[center.y, center.x], zoom_start=13, tiles=None)

                # Esri World Imagery as the default base — real satellite detail
                # even in remote terrain where OpenStreetMap has little mapped.
                folium.TileLayer(
                    tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
                    attr="Tiles &copy; Esri — Source: Esri, Maxar, Earthstar Geographics, and the GIS User Community",
                    name="Satellite", overlay=False, control=True,
                ).add_to(m)

                # Topographic contour basemap — fits the survey aesthetic and
                # shows relief/contours the imagery layer doesn't.
                folium.TileLayer(
                    tiles="https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png",
                    attr="Map data: &copy; OpenStreetMap contributors, SRTM — Map style: &copy; OpenTopoMap (CC-BY-SA)",
                    name="Terrain / contours", overlay=False, control=True,
                ).add_to(m)

                folium.TileLayer("CartoDB positron", name="Plain / labels", overlay=False, control=True).add_to(m)
                folium.TileLayer("OpenStreetMap", name="Streets", overlay=False, control=True).add_to(m)

                for idx, row in risk_df.iterrows():
                    lat, lon = float(row[lat_col]), float(row[lon_col])
                    folium.CircleMarker(
                        [lat, lon], radius=6, color="#c1502e", fill=True,
                        fill_color="#c1502e", fill_opacity=0.95, weight=1.5,
                        tooltip=f"High-risk point {idx}",
                    ).add_to(m)

                for idx, line in paths:
                    ll = gpd.GeoSeries([line], crs=src.crs).to_crs("EPSG:4326").iloc[0]
                    folium.GeoJson(
                        ll.__geo_interface__, name=f"Runout {idx}",
                        style_function=lambda x: {"color": "#c99a3a", "weight": 3},
                    ).add_to(m)

                for idx, zone in zones:
                    zz = gpd.GeoSeries([zone], crs=src.crs).to_crs("EPSG:4326").iloc[0]
                    folium.GeoJson(
                        zz.__geo_interface__, name=f"Impact zone {idx}",
                        style_function=lambda x: {"fillColor": "#6f8a56", "color": "#6f8a56", "fillOpacity": 0.22, "weight": 1.5},
                    ).add_to(m)

                folium.LayerControl(collapsed=False).add_to(m)
                st_folium(m, use_container_width=True, height=650)
            else:
                st.info("No runout paths could be traced for the uploaded points.")

        with tab_table:
            st.dataframe(out, use_container_width=True, hide_index=True)

        with tab_export:
            if zones:
                zone_gdf = gpd.GeoDataFrame(
                    [{"risk_id": idx, "geometry": zone} for idx, zone in zones],
                    crs=src.crs
                ).to_crs("EPSG:4326")
                geojson = zone_gdf.to_json()

                c1, c2 = st.columns(2)
                with c1:
                    st.download_button("Download impact zones (GeoJSON)", geojson, "impact_zones.geojson", "application/geo+json", use_container_width=True)
                with c2:
                    st.download_button("Download results (CSV)", out.to_csv(index=False), "runout_results.csv", "text/csv", use_container_width=True)
            else:
                st.info("Nothing to export yet — no paths were traced.")

st.caption("Simplified, educational runout estimate. Not a calibrated emergency-warning or engineering model.")
