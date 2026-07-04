from fastapi import FastAPI
from src.data import PRODUCTS

app = FastAPI()


@app.get("/products")
def list_products() -> list[dict]:
    return [{"id": p.id, "name": p.name, "category": p.category, "price": p.price}
            for p in PRODUCTS]


@app.get("/products/{product_id}")
def get_product(product_id: int) -> dict:
    for p in PRODUCTS:
        if p.id == product_id:
            return {"id": p.id, "name": p.name, "category": p.category, "price": p.price}
    from fastapi import HTTPException
    raise HTTPException(status_code=404, detail="not found")
