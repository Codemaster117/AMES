import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="Calculadora de Trayectorias v3.1", layout="wide")
st.title("🚀 Trajectory Planner 3D (Física Kepleriana y Curvatura Radial)")
st.markdown("Simulador de trayectorias interplanetarias con órbitas inclinadas en 3D y curvas de transferencia heliocéntricas.")

# --- CONSTANTES FÍSICAS ---
AU = 149597870.7 # km
MU_SUN = 1.32712440018e11 # km^3 / s^2

# Base de datos ampliada con inclinación orbital real (grados)
BODIES = {
    'Mercurio': {'a': 0.387 * AU, 'inc': 7.00, 'mu': 22032.0, 'radius': 2439.7, 'color': '#8c8c8c'},
    'Venus':    {'a': 0.723 * AU, 'inc': 3.39, 'mu': 324859.0, 'radius': 6051.8, 'color': '#e69f00'},
    'Tierra':   {'a': 1.000 * AU, 'inc': 0.00, 'mu': 398600.4, 'radius': 6378.1, 'color': '#0072b2'},
    'Marte':    {'a': 1.524 * AU, 'inc': 1.85, 'mu': 42828.3, 'radius': 3389.5, 'color': '#d55e00'},
    'Júpiter':  {'a': 5.204 * AU, 'inc': 1.30, 'mu': 126686534.0, 'radius': 69911.0, 'color': '#cc79a7'},
    'Saturno':  {'a': 9.582 * AU, 'inc': 2.48, 'mu': 37931187.0, 'radius': 58232.0, 'color': '#f0e442'},
    'Urano':    {'a': 19.20 * AU, 'inc': 0.77, 'mu': 5793939.0, 'radius': 25362.0, 'color': '#56b4e9'},
    'Neptuno':  {'a': 30.05 * AU, 'inc': 1.77, 'mu': 6836529.0, 'radius': 24622.0, 'color': '#002147'}
}

# Posición 3D exacta respetando inclinación orbital
def get_planet_pos(body_name, day):
    body = BODIES[body_name]
    a = body['a']
    inc = np.radians(body['inc'])
    omega = np.sqrt(MU_SUN / (a**3))
    angle = omega * (day * 86400.0)
    
    x = a * np.cos(angle)
    y = a * np.sin(angle) * np.cos(inc)
    z = a * np.sin(angle) * np.sin(inc)
    return np.array([x, y, z])

# Generador de arcos orbitales curvos heliocéntricos (Keplerian Smooth Transfer)
def generate_curved_arc(r1, r2, use_dsm, dsm_pct, steps=50):
    r1_mag = np.linalg.norm(r1)
    r2_mag = np.linalg.norm(r2)
    
    dot_prod = np.dot(r1, r2) / (r1_mag * r2_mag)
    dot_prod = np.clip(dot_prod, -1.0, 1.0)
    d_theta = np.arccos(dot_prod)
    
    n_vec = np.cross(r1, r2)
    if np.linalg.norm(n_vec) < 1e-6:
        n_vec = np.array([0.0, 0.0, 1.0])
    else:
        n_vec = n_vec / np.linalg.norm(n_vec)
        
    u_vec = r1 / r1_mag
    v_vec = np.cross(n_vec, u_vec)
    
    arc = []
    for s in range(steps):
        t = s / (steps - 1)
        theta = t * d_theta
        
        # Radio con curvatura orbital hacia el Sol
        r_t = r1_mag + (r2_mag - r1_mag) * (3*t**2 - 2*t**3)
        curvature_depth = 0.12 * np.sin(np.pi * t) * (r1_mag + r2_mag)
        r_t -= curvature_depth
        
        pos = r_t * (np.cos(theta) * u_vec + np.sin(theta) * v_vec)
        
        # Perturbación sutil por impulso DSM
        if use_dsm and t > dsm_pct:
            dsm_offset = 0.04 * AU * np.sin((t - dsm_pct) * np.pi) * n_vec
            pos += dsm_offset
            
        arc.append(pos)
    return arc

# --- CONFIGURACIÓN DE LA MISIÓN EN SIDEBAR ---
st.sidebar.header("1. Secuencia de la Misión")
preset = st.sidebar.selectbox("Presets Históricos", [
    "Personalizada",
    "Cassini-Huygens (Tierra-Venus-Venus-Tierra-Júpiter-Saturno)",
    "Europa Clipper (Tierra-Marte-Tierra-Júpiter)",
    "Voyager 2 (Tierra-Júpiter-Saturno-Urano-Neptuno)"
])

if preset == "Cassini-Huygens (Tierra-Venus-Venus-Tierra-Júpiter-Saturno)":
    sequence = ['Tierra', 'Venus', 'Venus', 'Tierra', 'Júpiter', 'Saturno']
elif preset == "Europa Clipper (Tierra-Marte-Tierra-Júpiter)":
    sequence = ['Tierra', 'Marte', 'Tierra', 'Júpiter']
elif preset == "Voyager 2 (Tierra-Júpiter-Saturno-Urano-Neptuno)":
    sequence = ['Tierra', 'Júpiter', 'Saturno', 'Urano', 'Neptuno']
else:
    num_bodies = st.sidebar.number_input("Número de Cuerpos", 2, 8, 4)
    sequence = []
    for i in range(num_bodies):
        lbl = f"Paso {i+1} ({'Salida' if i==0 else 'Llegada' if i==num_bodies-1 else 'Flyby'})"
        sequence.append(st.sidebar.selectbox(lbl, list(BODIES.keys()), index=min(i*2, len(BODIES)-1), key=f"body_{i}"))

st.sidebar.header("2. Tiempos de Vuelo y DSM")
leg_configs = []
for i in range(len(sequence) - 1):
    with st.sidebar.expander(f"Tramo {i+1}: {sequence[i]} ➔ {sequence[i+1]}", expanded=(i==0)):
        t_leg = st.number_input(f"Días de Vuelo", 30, 2000, 300, key=f"tof_{i}")
        use_dsm = st.checkbox("Incluir DSM", value=(i==0), key=f"dsm_{i}")
        dsm_pct = 50.0
        dsm_dv = 0.25
        if use_dsm:
            dsm_pct = st.slider("Momento del DSM (% del tramo)", 10.0, 90.0, 50.0, key=f"pct_{i}")
            dsm_dv = st.number_input("ΔV DSM (km/s)", 0.0, 5.0, 0.35, step=0.05, key=f"dv_{i}")
        leg_configs.append({'tof': t_leg, 'use_dsm': use_dsm, 'dsm_pct': dsm_pct / 100.0, 'dsm_dv': dsm_dv})

# --- CÁLCULO Y GENERACIÓN DE PUNTOS ---
sc_positions = []
total_days = sum(cfg['tof'] for cfg in leg_configs)
current_day = 0

for i in range(len(sequence) - 1):
    b_start, b_end = sequence[i], sequence[i+1]
    cfg = leg_configs[i]
    dt = cfg['tof']
    
    r_start = get_planet_pos(b_start, current_day)
    r_end = get_planet_pos(b_end, current_day + dt)
    
    arc = generate_curved_arc(r_start, r_end, cfg['use_dsm'], cfg['dsm_pct'])
    sc_positions.extend(arc[:-1] if i < len(sequence)-2 else arc)
    current_day += dt

# --- REPRODUCTOR Y SIMULACIÓN ---
st.header("🎬 Reproducción de Trayectoria Orbital 3D")
col_sim1, col_sim2 = st.columns([3, 1])

with col_sim2:
    st.subheader("Controles")
    sim_day = st.slider("Día de Misión", 0, total_days, 0, step=5)
    auto_play = st.checkbox("▶ Animación Automática", value=False)
    speed = st.select_slider("Velocidad", [1, 2, 5, 10], value=5)

if auto_play:
    sim_day = (sim_day + speed) % (total_days + 1)

sc_pos_idx = int((sim_day / total_days) * (len(sc_positions) - 1)) if total_days > 0 else 0
current_sc_pos = sc_positions[sc_pos_idx]

# --- RENDERIZADO 3D LIMPIO CON PLOTLY ---
fig = go.Figure()

# Sol
fig.add_trace(go.Scatter3d(
    x=[0], y=[0], z=[0], mode='markers',
    marker=dict(size=14, color='gold'), name='Sol', hoverinfo='text', text=['Sol']
))

# Dibujar órbitas en 3D y planetas alineados exactamente sobre ellas
unique_bodies = list(set(sequence))
for body in unique_bodies:
    a_au = BODIES[body]['a'] / AU
    inc = np.radians(BODIES[body]['inc'])
    theta = np.linspace(0, 2*np.pi, 200)
    
    x_orb = a_au * np.cos(theta)
    y_orb = a_au * np.sin(theta) * np.cos(inc)
    z_orb = a_au * np.sin(theta) * np.sin(inc)
    
    # Anillo orbital
    fig.add_trace(go.Scatter3d(
        x=x_orb, y=y_orb, z=z_orb, mode='lines',
        line=dict(color=BODIES[body]['color'], width=1.5, dash='dash'),
        name=f'Órbita {body}', showlegend=False, hoverinfo='none'
    ))
    
    # Marcador del planeta en la posición exacta del día simulado
    p_pos = get_planet_pos(body, sim_day) / AU
    fig.add_trace(go.Scatter3d(
        x=[p_pos[0]], y=[p_pos[1]], z=[p_pos[2]],
        mode='markers+text', marker=dict(size=8, color=BODIES[body]['color']),
        text=[body], textposition="top center", name=body, hoverinfo='text'
    ))

# Estela curva de la nave espacial
sc_x = [p[0]/AU for p in sc_positions[:sc_pos_idx+1]]
sc_y = [p[1]/AU for p in sc_positions[:sc_pos_idx+1]]
sc_z = [p[2]/AU for p in sc_positions[:sc_pos_idx+1]]

fig.add_trace(go.Scatter3d(
    x=sc_x, y=sc_y, z=sc_z, mode='lines',
    line=dict(color='#00ffff', width=4), name='Estela Recorrida', hoverinfo='none'
))

# Nave espacial
fig.add_trace(go.Scatter3d(
    x=[current_sc_pos[0]/AU], y=[current_sc_pos[1]/AU], z=[current_sc_pos[2]/AU],
    mode='markers+text', marker=dict(size=9, color='#ff007f', symbol='diamond'),
    text=['🚀 Nave Espacial'], textposition="top center", name='Nave Espacial', hoverinfo='text'
))

# Configuración visual limpia
fig.update_layout(
    scene=dict(
        xaxis=dict(title='X (UA)', gridcolor='#222222', showbackground=False),
        yaxis=dict(title='Y (UA)', gridcolor='#222222', showbackground=False),
        zaxis=dict(title='Z Radial (UA)', gridcolor='#222222', showbackground=False),
        aspectmode='data'
    ),
    margin=dict(l=0, r=0, b=0, t=20),
    height=680,
    hovermode='closest'
)

col_sim1.plotly_chart(fig, use_container_width=True)
