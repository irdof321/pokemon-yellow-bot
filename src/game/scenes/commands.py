import threading
from dataclasses import dataclass, field
from typing import Literal, Optional

@dataclass(frozen=True)
class BattleCommand:
    kind: Literal["move"]  # later: "item", "switch", ...
    move_index: int
    request_id: Optional[str] = None
    created_at: float = 0.0
    # Set by BattleScene._drive_commands() once this specific command finishes executing.
    # Lets a synchronous caller (SceneController) wait for *this* command instead of
    # polling is_ready(), which can be True before the command is even picked up.
    done_event: threading.Event = field(default_factory=threading.Event, compare=False, repr=False)
