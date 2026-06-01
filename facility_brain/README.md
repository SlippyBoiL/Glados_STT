# Facility Brain

Separate from `brain_data.json` (voice intent training) and the web HUD.

## What it does

1. **Scans your PC** — CPU/RAM/disk, network, top processes, installed app hints, skills, SSH devices, alerts.
2. **Saves state** to `data/facility_brain_state.json` (machine-readable; you can edit `custom` section).
3. **Deep scan** (`deep_scan_enabled`) — installed apps, drives, Desktop/Documents names, GPU, startup items, plus **`configs/user_profile.yaml`** so Glados knows you.
4. **Web search** — say *search the web for …* / *google …* — opens your real browser (Chrome/Edge/Firefox from profile).
5. **Glados brain sync** — after every scan, all PC knowledge is written to `data/computer_brain_memory.json` and injected into chat memory + the brain dashboard Memory page.
6. **Full file scan** — indexes up to 25k files under Desktop, Documents, Downloads, Pictures, Videos, Music, OneDrive (+ optional extra drives). Index: `data/facility_file_index.json`. Ask *where is my resume* or *find files about glados*.
3. **Decides actions** from keywords + brain state — **no LLM** for open/close/status/network/server checks.
4. **Executes** via kernel handlers (apps, skills, monitor, network repair).

## Customize

Edit **`configs/facility_brain.yaml`**:

- `routing_mode`: `brain_first` (default), `advisory`, or `brain_only`
- `autonomy.*`: toggle app control, PowerShell, skills, server SSH
- `app_aliases`: map "browser" → chrome, etc.
- `decision_rules`: your keyword → action rules
- `custom_facts`: facts merged into scans

## Enable in Glados

`configs/glados.yaml`:

```yaml
facility_brain_enabled: true
```

## Manual rescan

Say: **"rescan computer"** or **"update brain"**

Or Python:

```python
from facility_brain.brain_core import FacilityBrain
from glados_config import load_config
fb = FacilityBrain(load_config())
fb.scan()
print(fb.get_state_summary())
```

## Routing modes

| Mode | Behavior |
|------|----------|
| `brain_first` | Brain handles actions; LLM only when brain has no match |
| `brain_only` | Brain only (no chat LLM) — use for pure command mode |
| `advisory` | Brain only for status/rescan; LLM for everything else |

## Autonomy

With `autonomy.allow_*` enabled, Glados can open/close apps, run skills, flush DNS, check servers — on your machine. Review `facility_brain.yaml` before enabling on a shared PC.
