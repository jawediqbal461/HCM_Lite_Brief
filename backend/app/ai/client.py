import json

from sqlalchemy.orm import Session

from app.api.deps import CurrentUser
from app.ai.tools import TOOL_DEFINITIONS, run_tool
from app.core.config import settings

REQUEST_TIMEOUT_SECONDS = 15
MAX_TOOL_ITERATIONS = 4


class AIError(Exception):
    pass


def _anthropic_client():
    import anthropic

    if not settings.ai_api_key:
        raise AIError("AI_API_KEY is not configured")
    return anthropic.Anthropic(api_key=settings.ai_api_key, timeout=REQUEST_TIMEOUT_SECONDS)


def _openai_client():
    from openai import OpenAI

    if not settings.ai_api_key:
        raise AIError("AI_API_KEY is not configured")
    kwargs = {"api_key": settings.ai_api_key, "timeout": REQUEST_TIMEOUT_SECONDS}
    if settings.ai_base_url:
        # Points the same client at any OpenAI-compatible provider, e.g. xAI/Grok.
        kwargs["base_url"] = settings.ai_base_url
    return OpenAI(**kwargs)


def _anthropic_tools():
    return TOOL_DEFINITIONS


def _openai_tools():
    return [
        {"type": "function", "function": {"name": t["name"], "description": t["description"], "parameters": t["input_schema"]}}
        for t in TOOL_DEFINITIONS
    ]


def chat_with_tools(db: Session, user: CurrentUser, system_prompt: str, user_message: str) -> tuple[str, list]:
    tool_calls_log: list[dict] = []
    try:
        if settings.ai_provider == "openai":
            answer = _chat_openai(db, user, system_prompt, user_message, tool_calls_log)
        else:
            answer = _chat_anthropic(db, user, system_prompt, user_message, tool_calls_log)
        return answer, tool_calls_log
    except AIError:
        raise
    except Exception as exc:
        raise AIError(str(exc)) from exc


def _chat_anthropic(db, user, system_prompt, user_message, tool_calls_log):
    client = _anthropic_client()
    messages = [{"role": "user", "content": user_message}]

    for _ in range(MAX_TOOL_ITERATIONS):
        resp = client.messages.create(
            model=settings.ai_model,
            max_tokens=800,
            system=system_prompt,
            tools=_anthropic_tools(),
            messages=messages,
        )
        if resp.stop_reason != "tool_use":
            return "".join(block.text for block in resp.content if block.type == "text").strip() or "I don't have an answer for that."

        messages.append({"role": "assistant", "content": resp.content})
        tool_results = []
        for block in resp.content:
            if block.type == "tool_use":
                result = run_tool(db, user, block.name, block.input or {})
                tool_calls_log.append({"name": block.name, "input": block.input, "result": result})
                tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": json.dumps(result, default=str)})
        messages.append({"role": "user", "content": tool_results})

    return "I looked into this but couldn't finish in time — please try a narrower question."


def _chat_openai(db, user, system_prompt, user_message, tool_calls_log):
    client = _openai_client()
    messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_message}]

    for _ in range(MAX_TOOL_ITERATIONS):
        resp = client.chat.completions.create(model=settings.ai_model, messages=messages, tools=_openai_tools())
        choice = resp.choices[0]
        if not choice.message.tool_calls:
            return (choice.message.content or "").strip() or "I don't have an answer for that."

        # Only the fields the API actually defines. model_dump() would also carry
        # nulls like function_call/refusal/audio and a reasoning field on thinking
        # models; OpenAI ignores those, stricter compatible providers reject them.
        messages.append(
            {
                "role": "assistant",
                "content": choice.message.content or "",
                "tool_calls": [
                    {
                        "id": c.id,
                        "type": "function",
                        "function": {"name": c.function.name, "arguments": c.function.arguments},
                    }
                    for c in choice.message.tool_calls
                ],
            }
        )
        for call in choice.message.tool_calls:
            args = json.loads(call.function.arguments or "{}")
            result = run_tool(db, user, call.function.name, args)
            tool_calls_log.append({"name": call.function.name, "input": args, "result": result})
            messages.append({"role": "tool", "tool_call_id": call.id, "content": json.dumps(result, default=str)})

    return "I looked into this but couldn't finish in time — please try a narrower question."


def simple_text_completion(system_prompt: str, user_message: str) -> str:
    try:
        if settings.ai_provider == "openai":
            client = _openai_client()
            resp = client.chat.completions.create(
                model=settings.ai_model,
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_message}],
            )
            return (resp.choices[0].message.content or "").strip()

        client = _anthropic_client()
        resp = client.messages.create(
            model=settings.ai_model,
            max_tokens=500,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )
        return "".join(block.text for block in resp.content if block.type == "text").strip()
    except AIError:
        raise
    except Exception as exc:
        raise AIError(str(exc)) from exc
