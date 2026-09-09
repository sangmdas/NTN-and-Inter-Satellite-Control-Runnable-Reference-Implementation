from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .models import RadioCommand


class DefiniteEffectFailure(Exception):
    """Hardware confirms that no external RF/ISL effect occurred."""


class UnknownEffectResult(Exception):
    """Software cannot determine whether the effect occurred."""


class EffectAdapter(Protocol):
    def effect(self, command: RadioCommand, authority_id: str) -> str: ...


@dataclass
class SimulatedEffectSink:
    effects: list[tuple[str, RadioCommand]]

    def __init__(self) -> None:
        self.effects = []

    def effect(self, command: RadioCommand, authority_id: str) -> str:
        effect_id = f"effect-{command.act_type.lower()}-{len(self.effects) + 1}"
        self.effects.append((authority_id, command))
        return effect_id

