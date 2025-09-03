import numpy as np
from datetime import datetime

class PETPhysicsModel:
    def __init__(self):
        # Constantes del Vision 450
        self.AXFOV_MM = 263.0  # campo de visión axial (mm)
        self.HALF_LIFE_MIN = {
            "FDG": 109.77,          # F-18 FDG
            "PSMA": 109.77,         # F-18 PSMA-1007
        }

        # SNR objetivos
        self.SNR_TARGET_DEFAULT = {"FDG": 12.0, "PSMA": 14.0}
        self.SNR_REF_SITE_DEFAULT = {"FDG": 12.0, "PSMA": 14.0}

        # Perfiles de reconstrucción
        self.RECON_PROFILES = {
            "EARL": {"gain": 1.0, "note": "EARL armonizado"},
            "OSEM_TOF": {"gain": 1.25, "note": "OSEM+TOF sin PSF"},
            "HD_PET": {"gain": 1.6, "note": "TOF+PSF+filtro (Vision)"},
        }

        # Sensibilidad confirmada en literatura (Vision 450)
        self.SYSTEM_SENSITIVITY = {
            "FDG": 9.1,  # kcps/MBq
            "PSMA": 9.1,
        }

        # PEDIATRIC CONSIDERATIONS
        self.PEDIATRIC_WEIGHT_RANGES = {
            "neonate": (0.5, 5.0),
            "infant": (5.0, 15.0),
            "toddler": (15.0, 25.0),
            "child": (25.0, 50.0),
            "adolescent": (50.0, 100.0)
        }

        self.PEDIATRIC_DOSE_FACTORS = {
            "neonate": 0.02,
            "infant": 0.05,
            "toddler": 0.10,
            "child": 0.15,
            "adolescent": 0.75
        }

        self.PEDIATRIC_SNR_TARGETS = {
            "FDG": 8.0,
            "PSMA": 10.0
        }

        self.PEDIATRIC_SCAN_TIME_LIMITS = {
            "neonate": 30.0,
            "infant": 60.0,
            "toddler": 120.0,
            "child": 180.0,
            "adolescent": 240.0
        }

        self.PEDIATRIC_LBM_FACTORS = {
            "neonate": 0.85,
            "infant": 0.80,
            "toddler": 0.75,
            "child": 0.70,
            "adolescent": 0.65
        }

    def tracer_key(self, name: str) -> str:
        return "PSMA" if "PSMA" in str(name).upper() else "FDG"

    def get_system_sensitivity(self, tracer: str) -> float:
        """Sensibilidad base (literatura confirmada) en cps/MBq"""
        base = self.SYSTEM_SENSITIVITY.get(self.tracer_key(tracer), 9.1)
        return base * 1000  # kcps/MBq → cps/MBq

    def recon_gain_val(self, profile, custom_gain=None):
        if custom_gain is not None and custom_gain > 0:
            return float(custom_gain)
        # FIXED: Safe access to RECON_PROFILES
        profile_data = self.RECON_PROFILES.get(profile, {"gain": 1.6})
        return profile_data["gain"]

    def effective_activity_mbq(self, injected_mbq, inj_time, scan_start, tracer="FDG", residual_mbq=0.0):
        """Corrige la actividad inyectada por decaimiento y residual"""
        half_life = self.HALF_LIFE_MIN[self.tracer_key(tracer)]
        lam = np.log(2) / half_life
        dt_min = max((scan_start - inj_time).total_seconds() / 60.0, 0.0)
        A0 = max(injected_mbq - residual_mbq, 0.0)
        return A0 * np.exp(-lam * dt_min)

    def get_pediatric_age_group(self, weight_kg):
        """Determine pediatric age group based on weight"""
        for group, (min_w, max_w) in self.PEDIATRIC_WEIGHT_RANGES.items():
            if min_w <= weight_kg <= max_w:
                return group
        return None

    def is_pediatric_patient(self, weight_kg):
        """Check if patient is likely pediatric"""
        return weight_kg < 35.0

    def get_pediatric_dose_factor(self, weight_kg):
        """Get appropriate dose factor for pediatric patients"""
        age_group = self.get_pediatric_age_group(weight_kg)
        if age_group:
            return self.PEDIATRIC_DOSE_FACTORS.get(age_group, 0.15)
        return 1.0

    def get_pediatric_snr_target(self, tracer, weight_kg):
        """Get appropriate SNR target for pediatric patients"""
        base_target = self.PEDIATRIC_SNR_TARGETS.get(tracer, 8.0)
        dose_factor = self.get_pediatric_dose_factor(weight_kg)
        adjusted_target = base_target * (0.8 + 0.4 * (dose_factor / 0.15))
        return max(5.0, min(12.0, adjusted_target))

    def get_pediatric_scan_time_limit(self, weight_kg):
        """Get maximum recommended scan time for pediatric patients"""
        age_group = self.get_pediatric_age_group(weight_kg)
        if age_group:
            return self.PEDIATRIC_SCAN_TIME_LIMITS.get(age_group, 180.0)
        return 180.0

    def calculate_lbm(self, weight_kg, height_cm, gender="male"):
        # PEDIATRIC LBM CALCULATION
        if self.is_pediatric_patient(weight_kg):
            age_group = self.get_pediatric_age_group(weight_kg)
            if age_group:
                lbm_factor = self.PEDIATRIC_LBM_FACTORS.get(age_group, 0.70)
                return weight_kg * lbm_factor
            else:
                if weight_kg < 10:
                    return weight_kg * 0.85
                elif weight_kg < 30:
                    return weight_kg * 0.80
                else:
                    return weight_kg * 0.75
        else:
            # ADULT LBM CALCULATION
            gender = (gender or "male").lower()
            if gender in ["male", "masculino", "hombre"]:
                lbm = 1.10 * weight_kg - 128 * (weight_kg / height_cm) ** 2
            else:
                lbm = 1.07 * weight_kg - 148 * (weight_kg / height_cm) ** 2
            return max(lbm, 30.0)

    def bmi_multiplier(self, bmi, tracer="FDG", bmi_ref=22.0, bmi_cap=40.0):
        """Aplica solo una vez el factor BMI"""
        tkey = self.tracer_key(tracer)
        exp = 0.6 if tkey == "FDG" else 0.4
        bmi_eff = min(float(bmi), bmi_cap)
        return 1.0 if bmi_eff <= bmi_ref else (bmi_eff / bmi_ref) ** exp

    # ----------- Modelos de NEC y SNR -----------

    def calculate_nec(self, activity_mbq, dwell_time_s, tracer="FDG"):
        sens = self.get_system_sensitivity(tracer)
        return activity_mbq * dwell_time_s * sens

    def calculate_snr_from_nec(self, nec, recon_gain=1.0):
        return np.sqrt(max(nec, 1e-9)) * recon_gain

    def calibrate_k_from_reference(self, t_ref_std_s, A_ref_mbq, recon_gain, snr_ref_site, tracer="FDG", weight_kg=70, height_cm=170):
        """
        Enhanced k calibration using NEC model with LITERATURE-CONFIRMED parameters
        """
        # Calculate reference NEC using confirmed system sensitivity
        sensitivity = self.get_system_sensitivity(tracer)
        nec_ref = A_ref_mbq * t_ref_std_s * sensitivity  # counts
        
        # SNR_ref = k * √(NEC_ref) * recon_gain
        # k = SNR_ref / (√(NEC_ref) * recon_gain)
        sqrt_nec_ref = np.sqrt(max(nec_ref, 1e-9))
        k = snr_ref_site / (sqrt_nec_ref * recon_gain)
        
        return float(max(k, 1e-9))

    # ----------- Solvers de protocolo -----------

    def solve_standard(self, A_eff_mbq, k, recon_gain, snr_target_case, mult_bmi, scan_range_mm, 
                    tracer="FDG", is_pediatric=False, weight_kg=None, height_cm=None):
        nec_req = (snr_target_case / (max(k, 1e-9) * recon_gain)) ** 2
        sens = self.get_system_sensitivity(tracer)
        t_bed = nec_req / (max(A_eff_mbq * sens, 1e-6)) * mult_bmi

        # PEDIATRIC SCAN TIME LIMITATION
        if is_pediatric and weight_kg is not None:
            max_scan_time = self.get_pediatric_scan_time_limit(weight_kg)
            t_bed = min(t_bed, max_scan_time)

        v = self.AXFOV_MM / max(t_bed, 1e-6)
        v = max(0.5, min(v, 50.0))
        v = round(v, 1)
        t_bed_r = self.AXFOV_MM / v

        nec = self.calculate_nec(A_eff_mbq, t_bed_r, tracer)
        snr_pred = k * self.calculate_snr_from_nec(nec, recon_gain)
        cov_pred = 1.0 / snr_pred if snr_pred > 0 else np.nan

        return v, t_bed_r, (scan_range_mm / v) / 60.0, snr_pred, cov_pred, abs(snr_pred - snr_target_case) <= 0.3

    def solve_lowdose(self, low_dpk, weight_kg, k, recon_gain, snr_target_case, mult_bmi, scan_range_mm, 
                    tracer="FDG", is_pediatric=False, height_cm=None):
        # PEDIATRIC DOSE ADJUSTMENT
        if is_pediatric:
            dose_factor = self.get_pediatric_dose_factor(weight_kg)
            A_low = float(low_dpk) * float(weight_kg) * dose_factor
        else:
            A_low = float(low_dpk) * float(weight_kg)
            
        nec_req = (snr_target_case / (max(k, 1e-9) * recon_gain)) ** 2
        sens = self.get_system_sensitivity(tracer)
        t_bed = nec_req / (max(A_low * sens, 1e-6)) * mult_bmi

        # PEDIATRIC SCAN TIME LIMITATION
        if is_pediatric:
            max_scan_time = self.get_pediatric_scan_time_limit(weight_kg)
            t_bed = min(t_bed, max_scan_time)

        v = self.AXFOV_MM / max(t_bed, 1e-6)
        v = max(0.5, min(v, 50.0))
        v = round(v, 1)
        t_bed_r = self.AXFOV_MM / v

        nec = self.calculate_nec(A_low, t_bed_r, tracer)
        snr_pred = k * self.calculate_snr_from_nec(nec, recon_gain)
        cov_pred = 1.0 / snr_pred if snr_pred > 0 else np.nan

        return A_low, v, t_bed_r, (scan_range_mm / v) / 60.0, snr_pred, cov_pred, v > 0.5 + 1e-6

    def solve_fast(self, A_eff_mbq, k, recon_gain, mult_bmi, fast_t_ref_s, scan_range_mm, 
                tracer="FDG", is_pediatric=False, weight_kg=None, height_cm=None):
        t_bed_fast = float(fast_t_ref_s) * mult_bmi

        # PEDIATRIC FAST PROTOCOL ADJUSTMENT
        if is_pediatric and weight_kg is not None:
            reduction_factor = 0.5 + 0.3 * (self.get_pediatric_dose_factor(weight_kg) / 0.15)
            t_bed_fast = t_bed_fast * reduction_factor
            max_scan_time = self.get_pediatric_scan_time_limit(weight_kg) * 0.5
            t_bed_fast = min(t_bed_fast, max_scan_time)

        v = self.AXFOV_MM / max(t_bed_fast, 1e-6)
        v = max(0.5, min(v, 50.0))
        v = round(v, 1)
        t_bed_r = self.AXFOV_MM / v

        nec = self.calculate_nec(A_eff_mbq, t_bed_r, tracer)
        snr_pred = k * self.calculate_snr_from_nec(nec, recon_gain)
        cov_pred = 1.0 / snr_pred if snr_pred > 0 else np.nan

        return v, t_bed_r, (scan_range_mm / v) / 60.0, snr_pred, cov_pred