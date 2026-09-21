import streamlit as st
import numpy as np
import plotly.graph_objects as go

st.set_page_config(page_title="Calculadora Multi-Asistencia 3D", layout="wide")
st.title("🚀 Planificador de Múltiples Asistencias Gravitatorias")
st.markdown("Visualiza secuencias de sobrevuelos encadenados y reproduce la trayectoria en movimiento.")

AU = 149597870.7 # km
MU_SUN = 1.32712440018e11 # km^3 / s^2

BODIES = {
    'Mercurio': {'a': 0.387 * AU, 'color': 'gray'},
    'Venus':    {'a': 0.723 * AU, 'color': 'orange'},
    'Tierra':   {'a': 1.000 * AU, 'color': 'royalblue'},
    'Marte':    {'a': 1.524 * AU, 'color': 'firebrick'},
    'Júpiter':  {'a': 5.204 * AU, 'color': 'chocolate'},
    'Saturno':  {'a': 9.582 * AU, 'color': 'goldenrod'},
    'Urano':    {'a': 19.20 * AU, 'color': 'lightseagreen'},
    'Neptuno':  {'a': 30.05 * AU, 'color': 'darkblue'}
}

def get_planet_pos(body_name, day):
    a = BODIES[body_name]['a']
    omega = np.sqrt(MU_SUN / (a**3))
    angle = omega * (day * 86400.0)
    return np.array([a * np.cos(angle), a * np.sin(angle), 0.0])

def get_transfer_point(r1, r2, fraction):
    r1_norm, r2_norm = np.linalg.norm(r1), np.linalg.norm(r2)
    theta1 = np.arctan2(r1[1], r1[0])
    theta2 = np.arctan2(r2[1], r2[0])
    
    if theta2 < theta1:
        theta2 += 2 * np.pi
        
    current_theta = theta1 + (theta2 - theta1) * fraction
    current_r = r1_norm + (r2_norm - r1_norm) * fraction
    return np.array([current_r * np.cos(current_theta), current_r * np.sin(current_theta), 0.0])

# --- CONTROLES DE LA BARRA LATERAL ---
st.sidebar.header("1. Secuencia de Misión")
preset = st.sidebar.selectbox("Misiones Históricas Predefinidas", [
    "Personalizada",
    "Cassini (Tierra - Venus - Venus - Tierra - Júpiter - Saturno)",
    "Galileo (Tierra - Venus - Tierra - Tierra - Júpiter)",
    "Voyager (Tierra - Júpiter - Saturno - Urano)"
])

if preset == "Cassini (Tierra - Venus - Venus - Tierra - Júpiter - Saturno)":
    sequence = ['Tierra', 'Venus', 'Venus', 'Tierra', 'Júpiter', 'Saturno']
elif preset == "Galileo (Tierra - Venus - Tierra - Tierra - Júpiter)":
    sequence = ['Tierra', 'Venus', 'Tierra', 'Tierra', 'Júpiter']
elif preset == "Voyager (Tierra - Júpiter - Saturno - Urano)":
    sequence = ['Tierra', 'Júpiter', 'Saturno', 'Urano']
else:
    num_bodies = st.sidebar.number_input("Cantidad de cuerpos en la secuencia", 2, 8, 4)
    sequence = []
    for i in range(num_bodies):
        lbl = f"Paso {i+1} ({'Salida' if i==0 else 'Llegada' if i==num_bodies-1 else 'Asistencia'})"
        sequence.append(st.sidebar.selectbox(lbl, list(BODIES.keys()), index=min(i, len(BODIES)-1), key=f"seq_{i}"))

st.sidebar.header("2. Tiempos de Vuelo por Tramo (Días)")
leg_times = []
for i in range(len(sequence) - 1):
    t_leg = st.sidebar.slider(f"Tramo: {sequence[i]} ➔ {sequence[i+1]}", 50, 1500, 300, key=f"leg_{i}")
    leg_times.append(t_leg)

total_days = sum(leg_times)

# --- CÁLCULO DE LA TRAYECTORIA ---
sc_positions = []
current_day = 0
for i in range(len(sequence) - 1):
    b_start, b_end = sequence[i], sequence[i+1]
    dt = leg_times[i]
    
    r_start = get_planet_pos(b_start, current_day)
    r_end = get_planet_pos(b_end, current_day + dt)
    
    steps = 50
    for s in range(steps):
        frac = s / steps
        pos = get_transfer_point(r_start, r_end, frac)
        sc_positions.append(pos)
        
    current_day += dt

# --- REPRODUCTOR DE ANIMACIÓN ---
st.header("🎬 Reproducción de Trayectoria en Movimiento")
sim_day = st.slider("Arrastra el deslizador para avanzar en la línea de tiempo (Día de misión)", 0, total_days, 0, step=2)

sc_pos_idx = int((sim_day / total_days) * (len(sc_positions) - 1)) if total_days > 0 else 0
current_sc_pos = sc_positions[sc_pos_idx]

# --- GRÁFICO 3D INTERACTIVO CON PLOTLY ---
fig = go.Figure()

# Sol
fig.add_trace(go.Scatter3d(x=[0], y=[0], z=[0], mode='markers', marker=dict(size=12, color='gold'), name='Sol'))

# Órbitas y posiciones actuales de planetas
unique_bodies = list(set(sequence))
for body in unique_bodies:
    a_au = BODIES[body]['a'] / AU
    theta = np.linspace(0, 2*np.pi, 100)
    fig.add_trace(go.Scatter3d(
        x=a_au * np.cos(theta), y=a_au * np.sin(theta), z=np.zeros(100),
        mode='lines', line=dict(color=BODIES[body]['color'], width=1, dash='dash'),
        name=f'Órbita {body}', showlegend=False
    ))
    
    p_pos = get_planet_pos(body, sim_day) / AU
    fig.add_trace(go.Scatter3d(
        x=[p_pos[0]], y=[p_pos[1]], z=[p_pos[2]],
        mode='markers+text', marker=dict(size=8, color=BODIES[body]['color']),
        text=[body], textposition="top center", name=body
    ))

# Estela de la nave espacial
sc_x = [p[0]/AU for p in sc_positions[:sc_pos_idx+1]]
sc_y = [p[1]/AU for p in sc_positions[:sc_pos_idx+1]]
sc_z = [p[2]/AU for p in sc_positions[:sc_pos_idx+1]]
fig.add_trace(go.Scatter3d(
    x=sc_x, y=sc_y, z=sc_z, mode='lines',
    line=dict(color='magenta', width=4), name='Estela Recorrida'
))

# Posición actual de la nave espacial
fig.add_trace(go.Scatter3d(
    x=[current_sc_pos[0]/AU], y=[current_sc_pos[1]/AU], z=[current_sc_pos[2]/AU],
    mode='markers+text', marker=dict(size=10, color='magenta', symbol='diamond'),
    text=['🚀 Nave Espacial'], textposition="top center", name='Nave Espacial'
))

fig.update_layout(
    scene=dict(
        xaxis_title='X (UA)', yaxis_title='Y (UA)', zaxis_title='Z (UA)',
        aspectmode='data'
    ),
    margin=dict(l=0, r=0, b=0, t=30),
    height=700
)

st.plotly_chart(fig, use_container_width=True)
