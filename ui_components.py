import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

class PETUIComponents:
    def __init__(self, physics_model=None):
        self.physics_model = physics_model

    def sidebar_configuration(self):
        # Default values in case physics_model is not available
        SNR_REF_SITE_DEFAULT = {"FDG": 12.0, "PSMA": 14.0}
        SNR_TARGET_DEFAULT = {"FDG": 12.0, "PSMA": 14.0}
        RECON_PROFILES = {
            "EARL": {"gain": 1.0, "note": "EARL armonizado"},
            "OSEM_TOF": {"gain": 1.25, "note": "OSEM+TOF sin PSF (sitio dependiente)"},
            "HD_PET": {"gain": 1.6, "note": "TOF+PSF+filtro (Vision)"},
        }
        
        # Use physics_model values if available
        if self.physics_model is not None:
            if hasattr(self.physics_model, 'SNR_REF_SITE_DEFAULT'):
                SNR_REF_SITE_DEFAULT = self.physics_model.SNR_REF_SITE_DEFAULT
            if hasattr(self.physics_model, 'SNR_TARGET_DEFAULT'):
                SNR_TARGET_DEFAULT = self.physics_model.SNR_TARGET_DEFAULT
            if hasattr(self.physics_model, 'RECON_PROFILES'):
                RECON_PROFILES = self.physics_model.RECON_PROFILES

        st.sidebar.header("Reconstrucción")
        recon_profile = st.sidebar.selectbox("Perfil", list(RECON_PROFILES.keys()), index=2)
        custom_gain = st.sidebar.number_input("Gain personalizado (opcional)", 0.0, 5.0, 0.0, 0.1)
        
        # Calculate recon_gain
        if self.physics_model is not None and hasattr(self.physics_model, 'recon_gain_val'):
            recon_gain = self.physics_model.recon_gain_val(recon_profile, None if custom_gain==0 else custom_gain)
        else:
            # Fallback calculation
            profile_gain = RECON_PROFILES[recon_profile]["gain"]
            recon_gain = float(custom_gain) if custom_gain > 0 else profile_gain
            
        st.sidebar.caption(RECON_PROFILES[recon_profile]["note"] + f" — gain={recon_gain:.2f}")

        st.sidebar.header("Dwell de referencia (por cama)")
        std_fdg_ref = st.sidebar.number_input("FDG estándar (s)", 60.0, 600.0, 200.0, 5.0)
        fast_fdg_ref = st.sidebar.number_input("FDG rápido (s)", 30.0, 600.0, 120.0, 5.0)
        std_psma_ref = st.sidebar.number_input("PSMA estándar (s)", 60.0, 600.0, 240.0, 5.0)
        fast_psma_ref = st.sidebar.number_input("PSMA rápido (s)", 30.0, 600.0, 150.0, 5.0)

        st.sidebar.header("SNR de referencia del sitio (para k)")
        snr_ref_fdg = st.sidebar.number_input("FDG SNR_ref (sitio)", 6.0, 30.0, SNR_REF_SITE_DEFAULT["FDG"], 0.5)
        snr_ref_psma = st.sidebar.number_input("PSMA SNR_ref (sitio)", 6.0, 30.0, SNR_REF_SITE_DEFAULT["PSMA"], 0.5)

        st.sidebar.header("Calibración de k — referencia de actividad")
        ref_dpk_fdg = st.sidebar.number_input("FDG ref MBq/kg", 1.0, 8.0, 3.7, 0.1)
        ref_dpk_psma = st.sidebar.number_input("PSMA ref MBq/kg", 0.5, 5.0, 2.5, 0.1)

        st.sidebar.header("k del sitio (persistente)")
        use_site_k = st.sidebar.toggle("Usar k del sitio si existe (mediana)", value=True)

        st.sidebar.header("Baja dosis (literatura)")
        ld_fdg_dpk = st.sidebar.number_input("FDG low-dose (MBq/kg)", 1.0, 5.0, 2.5, 0.1)
        ld_psma_dpk = st.sidebar.number_input("PSMA low-dose (MBq/kg)", 0.5, 4.0, 1.5, 0.1)

        st.sidebar.header("SNR objetivo (caso)")
        snr_target_fdg = st.sidebar.number_input("FDG SNR_target (caso)", 6.0, 30.0, SNR_TARGET_DEFAULT["FDG"], 0.5)
        snr_target_psma = st.sidebar.number_input("PSMA SNR_target (caso)", 6.0, 30.0, SNR_TARGET_DEFAULT["PSMA"], 0.5)

        return {
            'recon_profile': recon_profile,
            'recon_gain': recon_gain,
            'std_fdg_ref': std_fdg_ref,
            'fast_fdg_ref': fast_fdg_ref,
            'std_psma_ref': std_psma_ref,
            'fast_psma_ref': fast_psma_ref,
            'snr_ref_fdg': snr_ref_fdg,
            'snr_ref_psma': snr_ref_psma,
            'ref_dpk_fdg': ref_dpk_fdg,
            'ref_dpk_psma': ref_dpk_psma,
            'use_site_k': use_site_k,
            'ld_fdg_dpk': ld_fdg_dpk,
            'ld_psma_dpk': ld_psma_dpk,
            'snr_target_fdg': snr_target_fdg,
            'snr_target_psma': snr_target_psma
        }

    def patient_study_inputs(self):
        st.subheader("Paciente & Estudio")
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            tracer_label = st.selectbox("Trazador", ["FDG", "F-18 PSMA-1007"], index=0)
        with c2:
            weight_kg = st.number_input("Peso (kg)", 0.5, 200.0, 78.0, 0.5)
        with c3:
            height_cm = st.number_input("Talla (cm)", 30.0, 220.0, 172.0, 0.5)
        with c4:
            gender = st.selectbox("Género", ["male", "female", "pediatric"], index=0)

        scan_range_mm = st.number_input("Rango de escaneo (mm)", 50.0, 2500.0, 1050.0, 10.0)

        # Show pediatric information if selected and physics model available
        if gender == "pediatric" and self.physics_model is not None:
            if hasattr(self.physics_model, 'get_pediatric_age_group') and hasattr(self.physics_model, 'get_pediatric_dose_factor'):
                age_group = self.physics_model.get_pediatric_age_group(weight_kg)
                dose_factor = self.physics_model.get_pediatric_dose_factor(weight_kg)
                st.info(f"Edad estimada: {age_group if age_group else 'No determinada'} | Factor de dosis: {dose_factor:.2f}x adulto")

        return tracer_label, weight_kg, height_cm, gender, scan_range_mm

    def activity_time_inputs(self):
        st.subheader("Actividad y tiempos")
        c5, c6, c7 = st.columns(3)
        with c5:
            injected_activity_mbq = st.number_input("Actividad inyectada (MBq)", 1.0, 600.0, 280.0, 1.0)
        with c6:
            inj_time_str = st.text_input("Hora de inyección (AAAA-MM-DD HH:MM)", datetime.now().strftime("%Y-%m-%d %H:%M"))
        with c7:
            start_time_str = st.text_input("Inicio adquisición (AAAA-MM-DD HH:MM)", (datetime.now()+timedelta(minutes=60)).strftime("%Y-%m-%d %H:%M"))
        residual_mbq = st.number_input("Residual (MBq) tras inyección", 0.0, 50.0, 0.0, 0.5)

        return injected_activity_mbq, inj_time_str, start_time_str, residual_mbq

    def display_results(self, patient_data, activity_data, recon_data):
        # Summaries
        st.markdown(f"**Paciente**: Peso {patient_data['weight_kg']:.1f} kg | Talla {patient_data['height_cm']:.1f} cm | BMI {patient_data['bmi']:.1f} | LBM {patient_data['lbm']:.1f} kg")
        st.markdown(f"**Actividad efectiva**: {activity_data['A_eff']:.1f} MBq (residual {activity_data['residual_mbq']:.1f} MBq; Δt={activity_data['delta_t']:.0f} min; T½={activity_data['half_life']} min)")
        st.markdown(f"**Recon**: {recon_data['profile']} (gain={recon_data['gain']:.2f}) | **k**: {recon_data['k']:.5f} ({recon_data['k_mode']}); {recon_data['k_src']}; t_ref_std={recon_data['t_ref_std']:.0f}s, t_ref_fast={recon_data['t_ref_fast']:.0f}s")
        st.markdown(f"**SNR_ref (sitio)**: {recon_data['snr_ref_site']:.1f} | **SNR_target (caso)**: {recon_data['snr_target_case']:.1f}")

    def protocol_block(self, title, activity_mbq, v, tbed, tmin, snr, cov, notes=None):
        st.subheader(title)
        st.write(f"**Actividad usada**: {activity_mbq:.1f} MBq")
        st.metric("Velocidad cama", f"{v:.1f} mm/s")
        st.metric("Dwell/posición", f"{tbed:.1f} s")
        st.metric("Tiempo de escaneo", f"{tmin:.1f} min")
        st.metric("SNR previsto", f"{snr:.2f}")
        st.metric("COV previsto", f"{cov:.3f}")
        if notes:
            st.info(notes)

    def k_store_controls(self):
        st.divider()
        st.markdown("### Calibración del sitio: almacén de k (por trazador y recon)")
        cK1, cK2 = st.columns(2)
        with cK1:
            add_k = st.button("Agregar k actual al almacén")
        with cK2:
            show_summary = st.button("Mostrar resumen de k del sitio")
        
        return add_k, show_summary

    def session_log_display(self, runs_data):
        st.divider()
        st.markdown("#### Bitácora de sesión")
        if runs_data and len(runs_data) > 0:  # Check if there's data
            df = pd.DataFrame(runs_data)
            st.dataframe(df, use_container_width=True)
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button("Descargar CSV", data=csv, file_name="vision450_session_log.csv", mime="text/csv")
        else:
            st.info("No hay datos de sesión disponibles")