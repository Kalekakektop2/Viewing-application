from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ChatTurn:
    role: str  # user | assistant
    text: str


@dataclass
class GameSession:
    """Holds game context for the current play session."""

    game_name: Optional[str] = None
    game_confidence: float = 0.0  # 0..1
    low_confidence_warned: bool = False
    history: list[ChatTurn] = field(default_factory=list)

    CONFIDENCE_THRESHOLD = 0.55

    def update_game(self, name: Optional[str], confidence: float) -> str | None:
        """
        Update detected game. Returns a warning string for the player if needed.
        """
        warning = None
        if name:
            # Keep sticky game once set with decent confidence, unless new is much higher
            if self.game_name and confidence < 0.75 and self.game_confidence >= 0.55:
                # sticky — do not overwrite lightly
                pass
            else:
                self.game_name = name
                self.game_confidence = confidence

        if (
            self.game_name
            and self.game_confidence < self.CONFIDENCE_THRESHOLD
            and not self.low_confidence_warned
        ):
            self.low_confidence_warned = True
            warning = (
                f"⚠ ИИ не уверен в определении игры («{self.game_name}»). "
                "Ответы по этой игре могут быть неточными."
            )
        return warning

    def add_user(self, text: str) -> None:
        self.history.append(ChatTurn(role="user", text=text))

    def add_assistant(self, text: str) -> None:
        self.history.append(ChatTurn(role="assistant", text=text))

    def reset_dialog(self) -> None:
        self.history.clear()

    def context_summary(self) -> str:
        if self.game_name:
            return f"Игра (сессия): {self.game_name} (уверенность ~{self.game_confidence:.0%})"
        return "Игра: ещё не определена"
