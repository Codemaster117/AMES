import streamlit as st
import pygmo as pg
import pykep as pk
# Import the Sims-Flanagan Multi-DSM model instead of mga_1dsm
from pykep.trajopt import sims_flanagan 
import matplotlib.pyplot as plt
import io
import contextlib
import datetime

st.set_page_config(page_title="Multi-DSM Gravity Assist Planner", layout="wide")
st.title("🚀 Multi-DSM & Low-Thrust Trajectory Planner")

# ... (Keep the previous Sidebar Inputs for Planets and Timewarp here) ...

st.sidebar.header("4. Spacecraft & Multi-DSM Settings")
# Sims-Flanagan requires spacecraft physical properties
sc_mass = st.sidebar.number_input("Spacecraft Initial Mass (kg)", value=1500.0)
sc_isp = st.sidebar.number_input("Engine Isp (seconds)", value=3000.0, help="3000s for Ion, 320s for Chemical")
sc_thrust = st.sidebar.number_input("Max Thrust (Newtons)", value=0.5, help="0.5N for Ion, >500N for Chemical")

# This is the magic variable: How many DSMs allowed between each planet?
n_segments = st.sidebar.slider("Maneuvers (Segments) per leg", 3, 20, 5)

if st.sidebar.button("Compute Multi-DSM Trajectory", type="primary"):
    with st.spinner("Slicing trajectory and computing multiple maneuvers..."):
        try:
            seq = [pk.planet.jpl_lp(body) for body in seq_names]
            
            t0 = [pk.epoch_from_string(f"{target_launch} 00:00:00.000").mjd2000, 
                  pk.epoch_from_string(f"{target_launch + datetime.timedelta(days=10)} 00:00:00.000").mjd2000]
            
            tof = [[50, tof_max] for _ in range(len(seq_names) - 1)]
            vinf = [0, 5.0] 
            
            # --- THE MULTI-DSM ENGINE ---
            # Slices each leg into N segments, allowing a Delta-V maneuver in each one.
            n_seg_list = [n_segments] * (len(seq) - 1) 
            
            prob_multi_dsm = sims_flanagan(
                seq=seq,
                t0=t0,
                tof=tof,
                vinf_dep=vinf,
                vinf_arr=vinf,
                mass=[sc_mass],
                Tmax=[sc_thrust],
                Isp=[sc_isp],
                n_seg=n_seg_list
            )
            
            # 4. Optimize
            prob = pg.problem(prob_multi_dsm)
            algo = pg.algorithm(pg.sade(gen=generations))
            pop = pg.population(prob, size=50)
            pop = algo.evolve(pop)
            
            best_decision = pop.champion_x
            best_fitness = pop.champion_f[0] # Note: Sims-Flanagan optimizes for delivered MASS, not Delta-V
            mass_consumed = sc_mass - best_fitness
            
            # 5. Capture Maneuver Log
            f = io.StringIO()
            with contextlib.redirect_stdout(f):
                prob_multi_dsm.pretty(best_decision)
            log_output = f.getvalue()
            
            # 6. Display Results
            st.success(f"Optimal Trajectory Found! Fuel Consumed: **{mass_consumed:.2f} kg** (Delivered Mass: {best_fitness:.2f} kg)")
            
            col1, col2 = st.columns([1, 1.5])
            
            with col1:
                st.subheader("Multi-Segment Maneuver Log")
                st.code(log_output, language="text")
                
            with col2:
                st.subheader("3D Trajectory Visualization")
                fig, ax = plt.subplots(figsize=(10, 10), subplot_kw={"projection": "3d"})
                
                # PyKEP plots all N segments and highlights where the burns occur
                prob_multi_dsm.plot(best_decision, axes=ax)
                
                ax.scatter([0], [0], [0], color='orange', s=200, label='Sun')
                
                ax.xaxis.pane.fill = False
                ax.yaxis.pane.fill = False
                ax.zaxis.pane.fill = False
                
                st.pyplot(fig)
                
        except Exception as e:
            st.error(f"Solver Error: {e}")