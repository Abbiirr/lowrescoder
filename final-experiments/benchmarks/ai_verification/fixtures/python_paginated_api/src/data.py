from __future__ import annotations
from dataclasses import dataclass


@dataclass
class Product:
    id: int
    name: str
    category: str
    price: float


PRODUCTS: list[Product] = [
    Product(i, f"Product {i}", ["electronics", "clothing", "food"][i % 3], round(i * 4.99, 2))
    for i in range(1, 101)
]
