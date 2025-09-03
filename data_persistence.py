import json
from pathlib import Path
import numpy as np

class KFactorStore:
    def __init__(self, store_file="k_store.json"):
        self.store_file = Path(store_file)

    def load_store(self):
        if self.store_file.exists():
            try:
                data = json.loads(self.store_file.read_text(encoding="utf-8"))
                return data
            except Exception:
                return {}
        return {}

    def save_store(self, store):
        try:
            self.store_file.write_text(json.dumps(store, indent=2), encoding="utf-8")
        except Exception:
            pass

    def add_k_measurement(self, store, tracer, recon_profile, k_value):
        key = f"{tracer}_{recon_profile}"
        arr = store.get(key, [])
        arr.append(float(k_value))
        store[key] = arr
        self.save_store(store)
        return store

    def summarize_k(self, store, tracer, recon_profile):
        key = f"{tracer}_{recon_profile}"
        vals = store.get(key, [])
        if not vals:
            return None
        a = np.array(vals)
        return float(np.median(a)), float(np.percentile(a, 25)), float(np.percentile(a, 75)), len(a)

    def get_site_k_summary(self, tracer, recon_profile):
        store = self.load_store()
        return self.summarize_k(store, tracer, recon_profile)