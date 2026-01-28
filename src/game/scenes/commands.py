from dataclasses import dataclass
from typing import Literal, Optional

@dataclass(frozen=True)
class BattleCommand:
    kind: Literal["move"]  # later: "item", "switch", ...
    move_index: int
    request_id: Optional[str] = None
    created_at: float = 0.0
