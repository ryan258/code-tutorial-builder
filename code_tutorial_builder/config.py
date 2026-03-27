from dataclasses import dataclass
from typing import Optional

@dataclass
class Config:
    """Configuration for tutorial generation."""
    steps: int = 5
    template: Optional[str] = None
    
    def __post_init__(self):
        if self.steps < 1:
            raise ValueError("Number of steps must be at least 1")