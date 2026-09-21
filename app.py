import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="Calculadora de Trayectorias v3", layout="wide")
st.title("🚀 Trajectory Planner & Mission Designer v3")
st.markdown("Planificador interplanetario e interlunar con **Maniobras de Espacio Profundo (DSM)**, **Presupuesto $\\Delta V$**, **Base de Datos Extendida (Lunas/Asteroides)** y **Animación 3D Continua**.")

# --- CONSTANTES FÍSICAS ---
AU = 149597870.7 # km
MU_SUN = 1.32712440018e11 # km^3 / s^2

# Base de datos ampliada de cuerpos celestes
BODIES = {
    # Planetas
    'Mercurio': {'a': 0.387 * AU, 'mu': 22032.0, 'radius': 2439.7, 'color': '#8c8c8c', 'type': 'Planeta'},
    'Venus':    {'a': 0.723 * AU, 'mu': 324859.0, 'radius': 6051.8, 'color': '#e69f00', 'type': 'Planeta'},
    'Tierra':   {'a': 1.000 * AU, 'mu': 398600.4, 'radius': 6378.1, 'color': '#0072b2', 'type': 'Planeta'},
    'Marte':    {'a': 1.524 * AU, 'mu': 42828.3, 'radius': 3389.5, 'color': '#d55e00', 'type': 'Planeta'},
    'Júpiter':  {'a': 5.204 * AU, 'mu': 126686534.0, 'radius': 69911.0, 'color': '#cc79a7', 'type': 'Planeta'},
    'Saturno':  {'a': 9.582 * AU, 'mu': 37931187.0, 'radius': 58232.0, 'color': '#f0e442', 'type': 'Planeta'},
    'Urano':    {'a': 19.20 * AU, 'mu': 5793939.0, 'radius': 25362.0, 'color': '#56b4e9', 'type': 'Planeta'},
    'Neptuno':  {'a': 30.05 * AU, 'mu': 6836529.0, 'radius': 24622.0, 'color': '#002147', 'type': 'Planeta'},
    # Lunas (Sistemas Joviano y Saturniano)
    'Io (Júpiter)':        {'a': 5.204 * AU + 421700, 'mu': 5959.9, 'radius': 1821.6, 'color': '#f39c12', 'type': 'Luna'},
    'Europa (Júpiter)':    {'a': 5.204 * AU + 670900, 'mu': 3202.7, 'radius': 1560.8, 'color': '#bdc3c7', 'type': 'Luna'},
    'Ganímedes (Júpiter)': {'a': 5.204 * AU + 1070400, 'mu': 9887.8, 'radius': 2634.1, 'color': '#7f8c8d', 'type': 'Luna'},
    'Calisto (Júpiter)':   {'a': 5.204 * AU + 1882700, 'mu': 7179.3, 'radius': 2410.3, 'color': '#34495e', 'type': 'Luna'},
    'Titán (Saturno)':     {'a': 9.582 * AU + 1221870, 'mu': 8978.1, 'radius': 2574.7, 'color': '#e67e22', 'type': 'Luna'},
    'Encélado (Saturno)':  {'a': 9.582 * AU + 238000, 'mu': 7.2, 'radius': 252.1, 'color': '#ecf0f1', 'type': 'Luna'},
    # Enanos / Asteroides
    'Ceres':    {'a': 2.767 * AU, 'mu': 62.6, 'radius': 469.7, 'color': '#95a5a6', 'type': 'Asteroide'},
    'Plutón':   {'a': 39.48 * AU, 'mu': 869.6, 'radius': 1188.3, 'color': '#9b59b6', 'type': 'Enano'}
}

def get_planet_pos_vel(body_name, day):
    a = BODIES[body_name]['a']
    omega = np.sqrt(MU_SUN / (a**3))
    angle = omega * (day * 86400.0)
    r = np.array([a * np.cos(angle), a * np.sin(angle), 0.0])
    v = np.array([-a * omega * np.sin(angle), a * omega * np.cos(angle), 0.0])
    return r, v

# --- SIDEBAR: CONFIGURACIÓN DE LA MISIÓN ---
st.sidebar.header("1. Configuración de la Misión")
preset = st.sidebar.selectbox("Presets Históricos", [
    "Personalizada",
    "Cassini-Huygens (Tierra-Venus-Venus-Tierra-Júpiter-Saturno)",
    "Europa Clipper (Tierra-Marte-Tierra-Júpiter)",
    "Galileo (Tierra-Venus-Tierra-Tierra-Júpiter)",
    "Voyager 2 (Tierra-Júpiter-Saturno-Urano-Neptuno)"
])

if preset == "Cassini-Huygens (Tierra-Venus-Venus-Tierra-Júpiter-Saturno)":
    sequence = ['Tierra', 'Venus', 'Venus', 'Tierra', 'Júpiter', 'Saturno']
elif preset == "Europa Clipper (Tierra-Marte-Tierra-Júpiter)":
    sequence = ['Tierra', 'Marte', 'Tierra', 'Júpiter']
elif preset == "Galileo (Tierra-Venus-Tierra-Tierra-Júpiter)":
    sequence = ['Tierra', 'Venus', 'Tierra', 'Tierra', 'Júpiter']
elif preset == "Voyager 2 (Tierra-Júpiter-Saturno-Urano-Neptuno)":
    sequence = ['Tierra', 'Júpiter', 'Saturno', 'Urano', 'Neptuno']
else:
    num_bodies = st.sidebar.number_input("Número de Cuerpos", 2, 8, 4)
    sequence = []
    for i in range(num_bodies):
        lbl = f"Cuerpo {i+1} ({'Salida' if i==0 else 'Llegada' if i==num_bodies-1 else 'Flyby'})"
        sequence.append(st.sidebar.selectbox(lbl, list(BODIES.keys()), index=min(i*2, len(BODIES)-1), key=f"body_{i}"))

st.sidebar.header("2. Tiempos de Vuelo y Maniobras DSM")
leg_configs = []

for i in range(len(sequence) - 1):
    with st.sidebar.expander(f"Tramo {i+1}: {sequence[i]} ➔ {sequence[i+1]}", expanded=(i==0)):
        t_leg = st.number_input(f"Tiempo de Vuelo (Días)", 30, 2000, 300, key=f"tof_{i}")
        use_dsm = st.checkbox("Incluir Maniobra DSM", value=(i==0), key=f"use_dsm_{i}")
        dsm_pct = 50.0
        dsm_dv = 0.25
        if use_dsm:
            dsm_pct = st.slider("Momento de DSM (% del tramo)", 10.0, 90.0, 50.0, key=f"dsm_pct_{i}")
            dsm_dv = st.number_input("Magnitud ΔV DSM (km/s)", 0.0, 5.0, 0.35, step=0.05, key=f"dsm_dv_{i}")
        leg_configs.append({'tof': t_leg, 'use_dsm': use_dsm, 'dsm_pct': dsm_pct / 100.0, 'dsm_dv': dsm_dv})

# --- CÁLCULOS ASTRODINÁMICOS & PRESUPUESTO DELTA-V ---
itinerary_data = []
sc_positions = []
total_mission_days = sum(cfg['tof'] for cfg in leg_configs)

current_day = 0
total_dv = 0.0

for i in range(len(sequence) - 1):
    b_start = sequence[i]
    b_end = sequence[i+1]
    cfg = leg_configs[i]
    dt = cfg['tof']
    
    r_start, v_start_p = get_planet_pos_vel(b_start, current_day)
    r_end, v_end_p = get_planet_pos_vel(b_end, current_day + dt)
    
    v_sc_in = (r_end - r_start) / (dt * 86400)
    
    v_inf_in = np.linalg.norm(v_sc_in - v_start_p) / 1000.0
    v_inf_out = np.linalg.norm(v_sc_in - v_end_p) / 1000.0
    
    leg_dv = 0.0
    event_type = "Transferencia Directa"
    
    if i == 0:
        c3 = (v_inf_in)**2
        leg_dv = v_inf_in
        event_type = f"Inyección (C3 = {c3:.1f} km²/s²)"
    else:
        mu_body = BODIES[b_start]['mu']
        r_body = BODIES[b_start]['radius']
        hp_est = max(200.0, r_body * 0.1)
        rp = r_body + hp_est
        delta_angle = 2 * np.arcsin(1 / (1 + (rp * (v_inf_in * 1000)**2) / mu_body)) * (180 / np.pi)
        event_type = f"Flyby (h_p ≈ {int(hp_est)} km, δ ≈ {delta_angle:.1f}°)"
        leg_dv = 0.0
        
    dsm_val = cfg['dsm_dv'] if cfg['use_dsm'] else 0.0
    leg_dv += dsm_val
    total_dv += leg_dv
    
    itinerary_data.append({
        'Tramo': f"Tramo {i+1}",
        'Origen': b_start,
        'Destino': b_end,
        'Duración (Días)': dt,
        'Evento Principal': event_type,
        'V_inf Relativa (km/s)': round(v_inf_in, 2),
        'DSM ΔV (km/s)': round(dsm_val, 2) if cfg['use_dsm'] else "--",
        'ΔV Subtotal (km/s)': round(leg_dv, 2)
    })
    
    steps = 40
    for s in range(steps):
        frac = s / steps
        if cfg['use_dsm'] and frac > cfg['dsm_pct']:
            pos = r_start + (r_end - r_start) * frac + np.array([0.05 * AU * np.sin(frac*np.pi), 0.05 * AU * np.cos(frac*np.pi), 0])
        else:
            pos = r_start + (r_end - r_start) * frac
        sc_positions.append(pos)
        
    current_day += dt

# Inserción orbital final
arrival_body = sequence[-1]
v_arr_inf = itinerary_data[-1]['V_inf Relativa (km/s)']
arrival_capture_dv = round(v_arr_inf * 0.4, 2)
total_dv += arrival_capture_dv

itinerary_data.append({
    'Tramo': 'Llegada Final',
    'Origen': sequence[-2],
    'Destino': arrival_body,
    'Duración (Días)': 0,
    'Evento Principal': f'Captura Orbital en {arrival_body}',
    'V_inf Relativa (km/s)': round(v_arr_inf, 2),
    'DSM ΔV (km/s)': '--',
    'ΔV Subtotal (km/s)': arrival_capture_dv
})

# --- TABLERO DE MÉTRICAS ---
col1, col2, col3, col4 = st.columns(4)
col1.metric("ΔV Total Estimado", f"{total_dv:.2f} km/s")
col2.metric("Duración Total", f"{total_mission_days} Días", f"{total_mission_days/365.25:.2f} Años")
col3.metric("Nº de Flybys", len(sequence) - 2)
col4.metric("Nº de DSMs", sum(1 for c in leg_configs if c['use_dsm']))

st.markdown("---")

# --- REPRODUCTOR DE ANIMACIÓN CONTINUA ---
st.header("🎬 Animación 3D Continua de la Misión")

col_anim1, col_anim2 = st.columns([3, 1])
with col_anim2:
    st.subheader("Control de Simulación")
    sim_day = st.slider("Día de la Misión", 0, total_mission_days, 0, step=5)
    auto_play = st.checkbox("▶ Reproducción Automática", value=False)
    speed = st.select_slider("Velocidad de Animación", options=[1, 2, 5, 10], value=5)

if auto_play:
    sim_day = (sim_day + speed) % (total_mission_days + 1)

sc_pos_idx = int((sim_day / total_mission_days) * (len(sc_positions) - 1)) if total_mission_days > 0 else 0
current_sc_pos = sc_positions[sc_pos_idx]

# --- RENDERIZADO CON PLOTLY ANIMADO ---
fig = go.Figure()

# Sol
fig.add_trace(go.Scatter3d(x=[0], y=[0], z=[0], mode='markers', marker=dict(size=14, color='gold'), name='Sol'))

unique_bodies = list(set(sequence))
for body in unique_bodies:
    a_au = BODIES[body]['a'] / AU
    theta = np.linspace(0, 2*np.pi, 100)
    fig.add_trace(go.Scatter3d(
        x=a_au * np.cos(theta), y=a_au * np.sin(theta), z=np.zeros(100),
        mode='lines', line=dict(color=BODIES[body]['color'], width=1, dash='dash'),
        name=f'Órbita {body}', showlegend=False
    ))
    
    p_pos, _ = get_planet_pos_vel(body, sim_day)
    p_pos_au = p_pos / AU
    fig.add_trace(go.Scatter3d(
        x=[p_pos_au[0]], y=[p_pos_au[1]], z=[p_pos_au[2]],
        mode='markers+text', marker=dict(size=8, color=BODIES[body]['color']),
        text=[body], textposition="top center", name=body
    ))

# Estela de la nave espacial
sc_x = [p[0]/AU for p in sc_positions[:sc_pos_idx+1]]
sc_y = [p[1]/AU for p in sc_positions[:sc_pos_idx+1]]
sc_z = [p[2]/AU for p in sc_positions[:sc_pos_idx+1]]
fig.add_trace(go.Scatter3d(
    x=sc_x, y=sc_y, z=sc_z, mode='lines',
    line=dict(color='#00ffcc', width=4), name='Estela Recorrida'
))

# Nave Espacial
fig.add_trace(go.Scatter3d(
    x=[current_sc_pos[0]/AU], y=[current_sc_pos[1]/AU], z=[current_sc_pos[2]/AU],
    mode='markers+text', marker=dict(size=10, color='#ff007f', symbol='diamond'),
    text=['🚀 Nave Espacial'], textposition="top center", name='Nave Espacial'
))

fig.update_layout(
    scene=dict(
        xaxis_title='X (UA)', yaxis_title='Y (UA)', zaxis_title='Z (UA)',
        aspectmode='data'
    ),
    margin=dict(l=0, r=0, b=0, t=20),
    height=650
)

col_anim1.plotly_chart(fig, use_container_width=True)

# --- PRESUPUESTO DELTA-V Y DESCARGA DE DATOS ---
st.header("📊 Tabla de Itinerario y Presupuesto $\\Delta V$")

df_itinerary = pd.DataFrame(itinerary_data)
st.dataframe(df_itinerary, use_container_width=True)

col_exp1, col_exp2 = st.columns(2)

csv_data = df_itinerary.to_csv(index=False).encode('utf-8')
col_exp1.download_button(
    label="📄 Descargar Itinerario en CSV",
    data=csv_data,
    file_name="itinerario_mision_espacial.csv",
    mime="text/csv"
)

html_report = f"""
<html>
<head><style>body{{font-family:sans-serif; padding:20px;}} table{{width:100%; border-collapse:collapse;}} th,td{{border:1px solid #ccc; padding:8px;}} th{{background:#f4f4f4;}}</style></head>
<body>
<h2>Reporte de Misión Espacial</h2>
<p><b>Secuencia:</b> {' ➔ '.join(sequence)}</p>
<p><b>ΔV Total:</b> {total_dv:.2f} km/s | <b>Duración:</b> {total_mission_days} Días</p>
{df_itinerary.to_html(index=False)}
</body>
</html>
"""

col_exp2.download_button(
    label="🌐 Descargar Reporte HTML del Plan de Vuelo",
    data=html_report.encode('utf-8'),
    file_name="reporte_mision_espacial.html",
    mime="text/html"
)
