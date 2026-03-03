from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()


class Item(BaseModel):
    id: int
    name: str
    description: str = ""


class ItemCreate(BaseModel):
    name: str
    description: str = ""


# In-memory store — replace with a real DB
_items: list[Item] = [
    Item(id=1, name="Example Item", description="A sample item to get started"),
]
_next_id = 2


@router.get("/", response_model=list[Item])
def list_items():
    return _items


@router.get("/{item_id}", response_model=Item)
def get_item(item_id: int):
    for item in _items:
        if item.id == item_id:
            return item
    raise HTTPException(status_code=404, detail="Item not found")


@router.post("/", response_model=Item, status_code=201)
def create_item(payload: ItemCreate):
    global _next_id
    item = Item(id=_next_id, **payload.model_dump())
    _next_id += 1
    _items.append(item)
    return item


@router.delete("/{item_id}", status_code=204)
def delete_item(item_id: int):
    global _items
    original_len = len(_items)
    _items = [i for i in _items if i.id != item_id]
    if len(_items) == original_len:
        raise HTTPException(status_code=404, detail="Item not found")
