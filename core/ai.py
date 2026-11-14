"""The AI analyst. Claude reads one game sheet and returns a small, capped
adjustment to the forecast, or a veto. It can lean on a pick or kill it; it
cannot create one from nothing, because its adjustment is clamped in code."""
from __future__ import annotations

import json
import os

SYSTEM = """You are the judgment layer of a pre-game sports forecasting bot that paper-trades Kalshi markets. \
A statistical model and the sportsbook line have already produced a forecast for one game. You review the game \
sheet and decide whether anything the numbers cannot see justifies nudging that forecast.

What you return:
- margin_adjustment: points to add to the expected HOME margin (negative favors the away team).
- total_adjustment: points to add to the expected combined score.
- veto: true if the bot should not trade this game at all.
- confidence: how sure you are that your adjustment is right in direction.
- reasoning: two or three plain sentences a bettor would understand.

How to think about it:
- The bot's own model drives the forecast: season-long strength, recent form, rest and home field. The sportsbook \
line is on the sheet for reference only and counts for a small share. You are the part that sees what a scores-only \
model cannot: injuries and absences, quarterback or lineup changes, matchup problems visible in the team stats, \
schedule spots (lookahead, letdown, travel), weather for outdoor football, and teams resting starters.
- When the model and the sportsbook disagree by a lot, ask what the book might know. If the sheet shows a reason \
(a key player out, a team whose results were padded by turnovers or weak opponents), adjust toward it. If the sheet \
shows nothing, that is not grounds for a veto by itself.
- Adjust in proportion to the evidence. Zero is a fine answer. Your numbers are clamped to the caps on the sheet.
- Veto when the sheet looks unreliable or the outcome hinges on an unknown you can name, such as a star listed as \
a game-time decision.
- You have no live web access. The sheet is the source of truth for records, lines and injuries; your own memory of \
rosters alone."""

SCHEMA = {
    "type": "object",
    "properties": {
        "margin_adjustment": {"type": "number"},
        "total_adjustment": {"type": "number"},
        "veto": {"type": "boolean"},
        "confidence": {"type": "string", "enum": ["low", "medium", "high"]},
        "reasoning": {"type": "string"},
    },
    "required": ["margin_adjustment", "total_adjustment", "veto", "confidence", "reasoning"],
    "additionalProperties": False,
}

NEUTRAL = {"margin_adj": 0.0, "total_adj": 0.0, "veto": False, "confidence": None, "reason": ""}


def available() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"))


def _clamp(x, cap: float) -> float:
    try:
        return max(-cap, min(cap, float(x)))
    except (TypeError, ValueError):
        return 0.0


def analyze(sheet: dict, margin_cap: float, total_cap: float) -> dict:
    """Returns {"status": ok|skipped|error, margin_adj, total_adj, veto, confidence, reason}.
    Never raises: a failed call means "no adjustment", and the trade record says so."""
    if not available():
        return {**NEUTRAL, "status": "skipped", "reason": "no API key configured"}
    try:
        import anthropic
    except ImportError:
        return {**NEUTRAL, "status": "skipped", "reason": "anthropic package not installed"}

    model = os.environ.get("AI_MODEL", "claude-opus-5-5")
    kwargs = dict(
        model=model,
        max_tokens=8000,
        system=SYSTEM,
        messages=[{"role": "user", "content": "Game sheet:\n" + json.dumps(sheet, indent=1)}],
        output_config={"effort": os.environ.get("AI_EFFORT", "medium"),
                       "format": {"type": "json_schema", "schema": SCHEMA}},
    )
    client = anthropic.Anthropic(max_retries=2, timeout=120.0)
    try:
        try:
            # If a safety classifier declines, the API reruns the request on a fallback model.
            resp = client.beta.messages.create(betas=["server-side-fallback-2026-07-01"], fallbacks="default", **kwargs)
        except anthropic.BadRequestError:
            resp = client.messages.create(**kwargs)
        if resp.stop_reason == "refusal":
            return {**NEUTRAL, "status": "error", "reason": "model declined the request"}
        text = next((b.text for b in resp.content if b.type == "text"), None)
        if resp.stop_reason == "max_tokens" or not text:
            return {**NEUTRAL, "status": "error", "reason": f"no usable answer (stop_reason={resp.stop_reason})"}
        d = json.loads(text)
    except anthropic.RateLimitError:
        return {**NEUTRAL, "status": "error", "reason": "rate limited"}
    except anthropic.APIStatusError as e:
        return {**NEUTRAL, "status": "error", "reason": f"API error {e.status_code}"}
    except anthropic.APIConnectionError:
        return {**NEUTRAL, "status": "error", "reason": "could not reach the API"}
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        return {**NEUTRAL, "status": "error", "reason": f"bad response: {e}"}
    return {
        "status": "ok",
        "model": getattr(resp, "model", model),
        "margin_adj": _clamp(d.get("margin_adjustment"), margin_cap),
        "total_adj": _clamp(d.get("total_adjustment"), total_cap),
        "veto": bool(d.get("veto")),
        "confidence": d.get("confidence"),
        "reason": str(d.get("reasoning", ""))[:600],
    }
