from pydantic import BaseModel


class DivisionSchema(BaseModel):
    division_number: int
    division_name: str


class ItemSchema(BaseModel):
    division_id: int
    item_code: str
    title: str
    description: str