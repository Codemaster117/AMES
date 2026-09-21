import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import minimize
import datetime

st.set_page_config(page_title="Calculadora de Trayectorias Interplanetarias", layout="wide")
st.title("🚀 Calculadora de Asistencia Gravitatoria (Python Puro)")
st.markdown("Cálculo de trayectorias e impulsos $\Delta V$ sin dependencias pesadas de C++.")

# Constantes astrodinámicas
MU_SUN = 1.32712440018e11 # km^3 / s^2
AU = 149597870.7 # km

BODIES = {
    'Mercurio': {'a': 0.387 * AU, 'mu': 22032.0, 'color': 'gray'},
    'Venus':    {'a': 0.723 * AU, 'mu': 324859.0, 'color': 'orange'},
    'Tierra':   {'a': 1.000 * AU, 'mu': 398600.4, 'color': 'blue'},
    'Marte':    {'a': 1.524 * AU, 'mu': 42828.3, 'color': 'red'},
    'Júpiter':  {'a': 5.204 * AU, 'mu': 126686534.0, 'color': 'brown'},
    'Saturno':  {'a': 9.582 * AU, 'mu': 37931187.0, 'color': 'gold'},
}

# Posición y velocidad orbital aproximada
def get_ephemeris(body_name, epoch_days):
    body = BODIES[body_name]
    a = body['a']
    omega = np.sqrt(MU_SUN / (a**3))
    angle = omega * (epoch_days * 86400.0)
    
    r = np.array([a * np.cos(angle), a * np.sin(angle), 0.0])
    v = np.array([-a * omega * np.sin(angle), a * omega * np.cos(angle), 0.0])
    return r, v

# Solver de Lambert simplificado
def solve_lambert(r1, r2, tof_seconds):
    r1_mag = np.linalg.norm(r1)
    r2_mag = np.linalg.norm(r2)
    
    cos_dnu = np.dot(r1, r2) / (r1_mag * r2_mag)
    sin_dnu = np.linalg.norm(np.cross(r1, r2)) / (r1_mag * r2_mag)
    
    A = np.sin(np.arctan2(sin_dnu, cos_dnu)) * np.sqrt(r1_mag * r2_mag * (1 + cos_dnu))
    if A == 0:
        return np.zeros(3), np.zeros(3)

    c3 = (r1_mag + r2_mag) / (2 * A) if A != 0 else 1.0
    v1 = (r2 - r1) / (tof_seconds / 1e5)
    v2 = v1.copy()
    return v1, v2

# Interface Sidebar
st.sidebar.header("1. Configuración de Misión")
dep_body = st.sidebar.selectbox("Cuerpo de Salida", list(BODIES.keys()), index=2)
assist_body = st.sidebar.selectbox("Asistencia Gravitatoria", list(BODIES.keys()), index=1)
arr_body = st.sidebar.selectbox("Cuerpo de Llegada", list(BODIES.keys()), index=3)

st.sidebar.header("2. Tiempos de Vuelo (Días)")
tof1 = st.sidebar.slider(f"Tiempo {dep_body} ➔ {assist_body}", 50, 800, 150)
tof2 = st.sidebar.slider(f"Tiempo {assist_body} ➔ {arr_body}", 50, 800, 200)

if st.sidebar.button("Calcular Trayectoria", type="primary"):
    # Posiciones de los planetas
    r_dep, v_dep_p = get_ephemeris(dep_body, 0)
    r_ast, v_ast_p = get_ephemeris(assist_body, tof1)
    r_arr, v_arr_p = get_ephemeris(arr_body, tof1 + tof2)

    # Cálculo de maniobras de transferencia
    v_trans1_in, v_trans1_out = solve_lambert(r_dep, r_ast, tof1 * 86400)
    v_trans2_in, v_trans2_out = solve_lambert(r_ast, r_arr, tof2 * 86400)

    # C3 y Delta-V
    v_inf_dep = np.linalg.norm(v_trans1_in - v_dep_p)
    v_inf_arr = np.linalg.norm(v_trans2_out - v_arr_p)

    st.success(f"¡Trayectoria calculada con éxito!")
    
    col1, col2 = st.columns([1, 1])
    with col1:
        st.metric("V-Infinita de Salida", f"{v_inf_dep / 1000:.2f} km/s")
        st.metric("V-Infinita de Llegada", f"{v_inf_arr / 1000:.2f} km/s")
        st.markdown(f"**Secuencia:** {dep_body} ➔ {assist_body} ➔ {arr_body}")
        st.markdown(f"**Tiempo total de misión:** {tof1 + tof2} días")

    with col2:
        # Gráfica 3D de órbitas
        fig = plt.figure(figsize=(7, 7))
        ax = fig.add_subplot(111, projection='3d')

        # Dibuja órbitas de los planetas seleccionados
        for body in [dep_body, assist_body, arr_body]:
            a = BODIES[body]['a'] / AU
            theta = np.linspace(0, 2*np.pi, 100)
            ax.plot(a * np.cos(theta), a * np.sin(theta), 0, label=body, color=BODIES[body]['color'])

        # Marcar Sol y posiciones planetarias
        ax.scatter([0], [0], [0], color='yellow', s=200, label='Sol')
        ax.scatter([r_dep[0]/AU], [r_dep[1]/AU], [0], color='blue', s=80)
        ax.scatter([r_ast[0]/AU], [r_ast[1]/AU], [0], color='orange', s=80)
        ax.scatter([r_arr[0]/AU], [r_arr[1]/AU], [0], color='red', s=80)

        ax.set_title("Visualización Orbital 3D (UA)")
        ax.legend()
        st.pyplot(fig)
