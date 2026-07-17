from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

PROMPTS_DIR = Path(__file__).parent / "prompts"

_env = Environment(
    loader=FileSystemLoader(str(PROMPTS_DIR)),
    autoescape=select_autoescape(disabled_extensions=(".j2",), default=False),
    trim_blocks=True,
    lstrip_blocks=True,
)

# Filename encodes the version so bumping a prompt is a new file, keeping old
# versions around for reproducibility of previously stored ai_analyses rows.
PROMPT_TEMPLATES = {
    "summary": "alert_summary_v1.j2",
    "triage": "alert_triage_v1.j2",
    "steps": "alert_investigate_v1.j2",
    "mitre": "alert_mitre_v1.j2",
    "prioritize": "alerts_prioritize_v1.j2",
    "report": "case_report_v1.j2",
    "ioc_summary": "ioc_summary_v1.j2",
    "nl_search": "nl_search_v1.j2",
    "technique_explain": "mitre_explain_v1.j2",
    "investigate_report": "investigate_report_v1.j2",
}


def render_prompt(task: str, **context: object) -> tuple[str, str]:
    """Renders the user-turn prompt for an AI task. Returns (prompt, version)
    — the version is stored alongside the ai_analyses row it produced."""
    template_name = PROMPT_TEMPLATES[task]
    template = _env.get_template(template_name)
    rendered = template.render(**context)
    version = template_name.removesuffix(".j2").rsplit("_", 1)[-1]
    return rendered, version
