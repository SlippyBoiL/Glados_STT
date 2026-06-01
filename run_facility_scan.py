"""One-shot full computer scan → data/facility_brain_state.json"""
import sys

from glados_config import load_config
from facility_brain.brain_core import FacilityBrain

if __name__ == "__main__":
    cfg = load_config()
    fb = FacilityBrain(cfg)
    state = fb.scan()
    try:
        print(fb.get_state_summary())
    except UnicodeEncodeError:
        print(fb.get_state_summary().encode("ascii", "replace").decode("ascii"))
    fs = state.get("file_scan") or {}
    if fs.get("enabled"):
        print(
            f"File index: {fs.get('file_count', 0)} files"
            + (" (truncated at limit)" if fs.get("truncated") else "")
            + f" in {fs.get('scan_seconds', '?')}s"
        )
        print(f"Index: {fs.get('index_path', 'data/facility_file_index.json')}")
    print(f"\nSaved: {fb._state_path}")
