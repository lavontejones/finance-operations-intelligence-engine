import json
from pathlib import Path

from foie.pipeline import build_demo

target = Path(__file__).resolve().parents[1] / "examples" / "demo_summary.json"
target.parent.mkdir(parents=True, exist_ok=True)
target.write_text(json.dumps(build_demo(), indent=2, default=str))
print(f"Wrote {target}")

