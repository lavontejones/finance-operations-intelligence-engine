import json
from pathlib import Path

from foie.pipeline import build_demo

target = Path(__file__).resolve().parents[1] / "examples" / "demo_summary.json"
target.write_text(json.dumps(build_demo(), indent=2))
print(f"Wrote {target}")
