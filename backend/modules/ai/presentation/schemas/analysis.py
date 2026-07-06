from typing import Optional

from pydantic import BaseModel

from modules.ai.domain.value_objects import VALID_AI_PROVIDERS


class AnalyzeRequest(BaseModel):
    provider: Optional[str] = None

    def model_post_init(self, __context) -> None:
        if self.provider is not None and self.provider not in VALID_AI_PROVIDERS:
            raise ValueError(f"provider must be one of {sorted(VALID_AI_PROVIDERS)}")
