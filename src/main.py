from typing import Union

from fastapi import FastAPI
from pydantic import BaseModel

from .routers import vagrant

# fastapi dev main.py --host 0.0.0.0
app = FastAPI()

class Item(BaseModel):
    name: str
    price: float
    is_offer: Union[bool, None] = None

@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.get("/items/{item_id}")
def read_item(item_id: int, q: Union[str, None] = None):
    return {"item_id": item_id, "p": q}

@app.put("/items/{item_id}")
def update_item(item_id: int, item: Item):
    return {"item_price": item.price, "item_id": item_id}

app.include_router(vagrant.router)
