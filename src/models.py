from typing import Optional
from pydantic import BaseModel


class OpenSCAPRule(BaseModel):
    title: str
    severity: str
    description: str
    rationale: str
    result: str


class DescriptionLynis(BaseModel):
    field: Optional[str] = None
    desc: Optional[str] = None
    value: Optional[str] = None
    prefval: Optional[str] = None


class DetailItemLynis(BaseModel):
    id: Optional[str]
    service: Optional[str]
    description: Optional[DescriptionLynis] = None


class SuggestionItemLynis(BaseModel):
    id: str
    severity: Optional[str]
    description: Optional[str]
