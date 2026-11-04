from datetime import datetime
from pathlib import Path

from fastapi.templating import Jinja2Templates

from app.core.config import settings

TEMPLATES_DIR = Path(__file__).resolve().parents[1] / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
templates.env.globals.update(
    app_name=settings.app_name,
    current_year=datetime.now().year,
)
