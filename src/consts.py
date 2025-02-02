from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent
DATA_DIR = ROOT_DIR / "data"
REPORTS_DIR = ROOT_DIR / "reports"
OPENSCAP_REPORT = REPORTS_DIR / "openscap-report.json"
LYNIS_REPORT = REPORTS_DIR / "lynis-report.json"
GENERATED_DIR = ROOT_DIR / "generated_reports"
DATABASE_URL = "sqlite:///reports.sqlite"

DATA_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
GENERATED_DIR.mkdir(parents=True, exist_ok=True)
