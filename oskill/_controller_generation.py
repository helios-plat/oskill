"""oskill.controller_generation — controller generation lifecycle helper."""
from __future__ import annotations

from dataclasses import dataclass

from oprim._controller_generation import (
    controller_generation_id,
    next_controller_generation,
)


@dataclass(frozen=True, slots=True)
class ControllerGeneration:
    """Provider-neutral controller generation descriptor."""

    root_run_id: str
    generation: int
    generation_id: str

    @classmethod
    def create(cls, root_run_id: str, previous_generation: int | None = None) -> "ControllerGeneration":
        generation = next_controller_generation(previous_generation)
        return cls(
            root_run_id=root_run_id,
            generation=generation,
            generation_id=controller_generation_id(root_run_id, generation),
        )
