from pydantic import BaseModel
from typing import List, Dict, Any


class Medication(BaseModel):
    pill_name: str
    count: int


class Recipe(BaseModel):
    medications: Dict[str, List[Medication]]
