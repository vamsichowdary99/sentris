from pydantic import BaseModel, ValidationError

from app.ai.guardrails import extract_json
from app.ai.prompt_loader import render_prompt
from app.ai.router import LLMResponse, LLMUnavailableError, get_ai_router
from app.core.errors import AIUnavailableError


async def run_structured[T: BaseModel](
    task: str, schema: type[T], **prompt_ctx: object
) -> tuple[T, LLMResponse, str]:
    """Renders the versioned prompt for `task`, calls the AI router in JSON
    mode, and validates the response against `schema` — with one retry via
    a repair prompt if the model's output doesn't parse/validate the first
    time. Shared by AIService and InvestigateService so both AI-report
    features (case reports, IOC investigate reports) get identical
    validation/retry/degradation behavior.
    """
    router = get_ai_router()
    prompt, version = render_prompt(task, **prompt_ctx)
    try:
        response = await router.complete(user=prompt, json_mode=True)
    except LLMUnavailableError as exc:
        raise AIUnavailableError(str(exc)) from exc

    try:
        parsed = schema.model_validate_json(extract_json(response.content))
    except (ValidationError, ValueError):
        repair_prompt = (
            f"{prompt}\n\nYour previous response did not match the required JSON "
            "schema exactly. Respond again with ONLY valid JSON matching the schema."
        )
        response = await router.complete(user=repair_prompt, json_mode=True)
        parsed = schema.model_validate_json(extract_json(response.content))

    return parsed, response, version
