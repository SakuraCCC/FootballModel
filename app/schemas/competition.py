from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CompetitionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    name: str
    region: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
