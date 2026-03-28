from dataclasses import dataclass
from typing import Optional

VALID_FORMATS = ("lesson", "handout")


@dataclass
class Config:
    """Configuration for tutorial generation."""

    steps: int = 5
    template: Optional[str] = None
    output_format: str = "lesson"
    use_ai: bool = False
    env_search_path: Optional[str] = None
    method_split_threshold: int = 4

    def __post_init__(self):
        if self.steps < 1:
            raise ValueError("Number of steps must be at least 1")
        if self.output_format not in VALID_FORMATS:
            raise ValueError(
                f"Invalid format '{self.output_format}'."
                f" Choose from: {', '.join(VALID_FORMATS)}"
            )
