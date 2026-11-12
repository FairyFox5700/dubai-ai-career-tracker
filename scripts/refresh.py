from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from career_tracker.refresh import refresh


def main():
    config = json.loads((ROOT / "config" / "tracker.json").read_text(encoding="utf-8"))
    report = refresh(
        config["sources"],
        ROOT / "data" / "jobs.json",
        ROOT / "data" / "refresh-report.json",
        ROOT / "data" / "jobs.csv",
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
