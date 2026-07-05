from __future__ import annotations

from dataclasses import dataclass
import json
import re
from typing import Iterable

from app.config import get_program


@dataclass(frozen=True)
class ProgramPriority:
    code: str
    priority: int


class ProfileParseError(ValueError):
    pass


_PROGRAM_PRIORITY_PATTERN = re.compile(r"(?P<code>\d{2}\.\d{2}\.\d{2})\s*[;,]\s*(?P<priority>[1-5])")


def parse_program_priorities(text: str) -> list[ProgramPriority]:
    pairs = [
        ProgramPriority(code=match.group("code"), priority=int(match.group("priority")))
        for match in _PROGRAM_PRIORITY_PATTERN.finditer(text)
    ]
    if not pairs:
        raise ProfileParseError("Укажите направления в формате 01.03.02;1")

    seen_codes: set[str] = set()
    seen_priorities: set[int] = set()
    for pair in pairs:
        if get_program(pair.code) is None:
            raise ProfileParseError(f"Направление {pair.code} не отслеживается. Используйте /programs.")
        if pair.code in seen_codes:
            raise ProfileParseError(f"Направление {pair.code} указано несколько раз.")
        if pair.priority in seen_priorities:
            raise ProfileParseError(f"Приоритет {pair.priority} указан несколько раз.")
        seen_codes.add(pair.code)
        seen_priorities.add(pair.priority)

    return sorted(pairs, key=lambda item: item.priority)


def encode_program_priorities(priorities: Iterable[ProgramPriority]) -> str:
    return json.dumps(
        [
            {
                "code": item.code,
                "priority": item.priority,
            }
            for item in sorted(priorities, key=lambda item: item.priority)
        ],
        ensure_ascii=False,
    )


def decode_program_priorities(value: str | None) -> list[ProgramPriority]:
    if not value:
        return []
    try:
        payload = json.loads(value)
    except (TypeError, ValueError):
        return []
    if not isinstance(payload, list):
        return []

    priorities: list[ProgramPriority] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        code = item.get("code")
        priority = item.get("priority")
        if not isinstance(code, str) or not isinstance(priority, int):
            continue
        if get_program(code) is None or priority < 1 or priority > 5:
            continue
        priorities.append(ProgramPriority(code=code, priority=priority))
    return sorted(priorities, key=lambda item: item.priority)


def format_program_priorities(value: str | None) -> str:
    priorities = decode_program_priorities(value)
    if not priorities:
        return "не заданы"
    lines: list[str] = []
    for item in priorities:
        program = get_program(item.code)
        name = f" {program.name}" if program else ""
        lines.append(f"{item.priority}. {item.code}{name}")
    return "\n".join(lines)


def program_priority_map(value: str | None) -> dict[str, int]:
    return {item.code: item.priority for item in decode_program_priorities(value)}
