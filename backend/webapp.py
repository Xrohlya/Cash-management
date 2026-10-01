from pathlib import Path
from string import Template

WEBAPP_DIR = Path(__file__).resolve().parent.parent / "webapp"


def webapp_html():
    sections = WEBAPP_DIR / "sections"
    names = ("budget", "operations", "plans", "settings", "dialogs", "pets")
    fragments = {name: (sections / f"{name}.html").read_text(encoding="utf-8") for name in names}
    fragments["plans"] = Template(fragments["plans"]).substitute({
        name: (sections / f"{name}.html").read_text(encoding="utf-8")
        for name in ("calendar", "goal", "recurring")
    })
    return Template((WEBAPP_DIR / "index.html").read_text(encoding="utf-8")).substitute(fragments)
