import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import time

st.set_page_config(page_title="AE Slope Monitor", page_icon="◈", layout="wide")

if "step" not in st.session_state:
    st.session_state.step = 0
if "running" not in st.session_state:
    st.session_state.running = True
if "history" not in st.session_state:
    st.session_state.history = []

st.markdown("""
<style>
.block-container{max-width:1450px;padding-top:1rem}
.metric-card{background:#0c1822;border:1px solid #213746;border-radius:12px;padding:14px}
.label{font-size:11px;letter-spacing:1px;color:#8fa5b3}
.value{font-size:27px;font-weight:700}
.sub{font-size:11px;color:#8fa5b3}
</style>
""", unsafe_allow_html=True)

def observe(step):
    rng = np.random.default_rng(5000 + step)
    phase = step % 240
    if phase < 60:
        damage = 0.05 + .08*phase/60
    elif phase < 140:
        damage = .13 + .52*(phase-60)/80
    elif phase < 185:
        damage = .65 + .22*(phase-140)/45
    else:
        damage = max(.16, .87 - .71*(phase-185)/55)

    fs, seconds = 2000, 3.0
    t = np.arange(int(fs*seconds))/fs
    raw = .025*rng.normal(size=len(t))
    raw += .012*np.sin(2*np.pi*38*t) + .008*np.sin(2*np.pi*75*t)

    n_events = int(2 + damage*24)
    for _ in range(n_events):
        center = rng.uniform(.15, seconds-.15)
        freq = rng.uniform(80, 550)
        amp = rng.uniform(.16,.55)*(0.7+damage)
        width = rng.uniform(.004,.016)
        raw += amp*np.exp(-((t-center)/width)**2)*np.sin(2*np.pi*freq*(t-center))

    filtered = np.convolve(raw, np.ones(13)/13, mode="same")
    envelope = np.abs(filtered)
    threshold = .10
    events = int(np.sum((envelope[1:] >= threshold) & (envelope[:-1] < threshold)))
    events = max(1, min(events, 80))
    peak = float(np.max(np.abs(raw)))
    energy = float(np.sum(raw**2))
    energy_index = min(100, energy/42)
    rate = events/seconds*60

    spectrum = np.abs(np.fft.rfft(raw))
    freqs = np.fft.rfftfreq(len(raw), 1/fs)
    band = (freqs>=40)&(freqs<=800)
    dominant = float(freqs[band][np.argmax(spectrum[band])])

    anomaly = float(np.clip(
        .40*(rate/350) + .25*(energy_index/100) +
        .20*min(1,peak/1.2) + .15*damage, 0, 1
    ))
    status = "CRITICAL" if anomaly>=.72 else ("WATCH" if anomaly>=.42 else "NORMAL")
    return dict(t=t,raw=raw,filtered=filtered,damage=damage,events=events,
                rate=rate,peak=peak,energy=energy,energy_index=energy_index,
                dominant=dominant,anomaly=anomaly,status=status)

o = observe(st.session_state.step)

row = dict(time=datetime.now().strftime("%H:%M:%S"), events_min=o["rate"],
           peak=o["peak"], energy=o["energy_index"], anomaly=o["anomaly"]*100,
           status=o["status"])
if not st.session_state.history or st.session_state.history[-1]["time"] != row["time"]:
    st.session_state.history.append(row)
st.session_state.history = st.session_state.history[-60:]

st.title("Acoustic Emission • Slope Integrity Monitor")
st.caption("Real-time AE monitoring prototype — internal damage / deformation indicators")

metrics = [
    ("AE EVENTS", str(o["events"]), "events in current window"),
    ("EVENT RATE", f"{o['rate']:.0f}/min", "detected activity"),
    ("PEAK AMPLITUDE", f"{o['peak']:.2f}", "relative signal"),
    ("DOMINANT FREQUENCY", f"{o['dominant']:.0f} Hz", "40–800 Hz band"),
    ("ANOMALY SCORE", f"{o['anomaly']*100:.0f}/100", o["status"])
]
cols = st.columns(5)
for c,(a,b,d) in zip(cols,metrics):
    c.markdown(f'<div class="metric-card"><div class="label">{a}</div><div class="value">{b}</div><div class="sub">{d}</div></div>', unsafe_allow_html=True)

st.write("")
st.subheader("Live AE waveform")
fig = go.Figure()
fig.add_trace(go.Scatter(x=o["t"], y=o["raw"], name="Raw AE", line=dict(width=1), opacity=.40))
fig.add_trace(go.Scatter(x=o["t"], y=o["filtered"], name="Processed", line=dict(width=2)))
fig.add_hline(y=.10, line_dash="dash", annotation_text="Detection threshold")
fig.add_hline(y=-.10, line_dash="dash")
fig.update_layout(height=330, template="plotly_dark", margin=dict(l=10,r=10,t=10,b=10),
                  xaxis_title="Time (s)", yaxis_title="Amplitude")
st.plotly_chart(fig, use_container_width=True)

left,right = st.columns(2)
with left:
    st.subheader("AE activity trend")
    if len(st.session_state.history)>1:
        h=pd.DataFrame(st.session_state.history)
        f=go.Figure(go.Scatter(x=h.time,y=h.events_min,mode="lines+markers"))
        f.update_layout(height=280,template="plotly_dark",margin=dict(l=10,r=10,t=10,b=10),
                        xaxis_title="Time",yaxis_title="Events / minute")
        st.plotly_chart(f,use_container_width=True)
    else:
        st.info("Collecting history...")
with right:
    st.subheader("Frequency spectrum")
    sp=np.abs(np.fft.rfft(o["raw"]))
    fr=np.fft.rfftfreq(len(o["raw"]),1/2000)
    m=(fr>=20)&(fr<=900)
    sf=go.Figure(go.Scatter(x=fr[m],y=sp[m],fill="tozeroy"))
    sf.add_vline(x=o["dominant"],line_dash="dash",annotation_text=f"{o['dominant']:.0f} Hz")
    sf.update_layout(height=280,template="plotly_dark",margin=dict(l=10,r=10,t=10,b=10),
                     xaxis_title="Frequency (Hz)",yaxis_title="Amplitude")
    st.plotly_chart(sf,use_container_width=True)

st.subheader("Conceptual AE sensor array")
st.caption("Engineering section view; nodes represent physical AE sensor locations.")
x=np.linspace(0,100,220)
surface=60-.18*x+3*np.sin(x/12)
bottom=surface-20
section=go.Figure()
section.add_trace(go.Scatter(x=x,y=surface,mode="lines",fill="tozeroy",
                             fillcolor="rgba(90,130,150,.18)",name="Slope material"))
section.add_trace(go.Scatter(x=x,y=bottom,mode="lines",line=dict(dash="dot"),name="Subsurface boundary"))
sx=np.array([12,28,45,62,78,92])
sy=np.interp(sx,x,surface)-5
sz=8+20*o["damage"]*np.array([.4,.7,1,.85,.6,.35])
section.add_trace(go.Scatter(x=sx,y=sy,mode="markers+text",text=[f"AE-{i}" for i in range(1,7)],
                             textposition="top center",marker=dict(size=sz),name="AE sensors"))
section.add_annotation(x=62,y=np.interp(62,x,surface)+5,text="Increasing activity",showarrow=True,arrowhead=2)
section.update_layout(height=320,template="plotly_dark",margin=dict(l=10,r=10,t=10,b=10),
                      xaxis_title="Slope section (m)",yaxis_title="Relative elevation")
st.plotly_chart(section,use_container_width=True)

c1,c2,c3=st.columns([1,1,3])
if c1.button("Pause" if st.session_state.running else "Resume",use_container_width=True):
    st.session_state.running=not st.session_state.running
if c2.button("Reset",use_container_width=True):
    st.session_state.step=0
    st.session_state.history=[]
    st.rerun()

if o["status"]=="CRITICAL":
    msg="High AE activity detected. Persistent internal activity requires investigation."
elif o["status"]=="WATCH":
    msg="AE activity is above baseline. Continue monitoring for persistence and spatial correlation."
else:
    msg="AE activity remains close to the established baseline."
c3.info(msg)

st.caption("Synthetic prototype data. Physical deployment requires calibrated AE sensors, site-specific coupling, filtering, baseline characterization, and validation.")

if st.session_state.running:
    time.sleep(1)
    st.session_state.step += 1
    st.rerun()
