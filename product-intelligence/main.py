import os
import uvicorn
from fastapi import FastAPI, HTTPException, Header, Depends
from typing import Optional
from src.models import (
    ProductSearchRequest,
    ProductSearchResponse,
    ProductRecord
)
from src.repository import ProductRepository
from src.search import HybridProductSearch
from src.formatter import format_whatsapp_response
from src.validator import ResponseValidator
from src.ingest import ingest_from_csv_and_json

app = FastAPI(
    title="Kepler Tech LLC - Product Intelligence Microservice",
    version="1.0.0",
    description="Standalone intelligence service for product discovery, hybrid search, compatible recommendations, and direct website routing."
)

repo = ProductRepository()
searcher = HybridProductSearch(repo)

@app.on_event("startup")
def startup_event():
    # Initial data bootstrap from local catalog CSV & JSON
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    # Look for products.json and db.json in root salesai project
    salesai_root = os.path.dirname(base_dir)
    json_path = os.path.join(salesai_root, "products.json")
    # Ingest catalog
    print("Bootstrap: Initializing Product Intelligence DB...")
    # Check if products table is empty
    if not repo.get_all_products():
        # Create temporary mock csv data if none exists
        csv_path = os.path.join(base_dir, "catalog.csv")
        ingest_from_csv_and_json(repo, csv_path=csv_path, json_path=json_path)
    print("Bootstrap: Ready.")

@app.get("/health")
def health_check():
    count = len(repo.get_all_products())
    return {"status": "healthy", "service": "product-intelligence", "total_products": count}

@app.post("/api/v1/products/search", response_model=ProductSearchResponse)
def search_products_api(req: ProductSearchRequest):
    matched, related = searcher.search(req)
    
    # URL and Grounding validation layer
    for item in matched:
        if not ResponseValidator.validate_url(item.website_url):
            item.website_url = "https://www.keplertechllc.com"

    formatted_wa = format_whatsapp_response(matched, related)

    return ProductSearchResponse(
        intent="PRODUCT_SEARCH" if matched else "NO_RESULT",
        matched_products=matched,
        related_products=related,
        formatted_whatsapp_message=formatted_wa,
        needs_clarification=len(matched) == 0
    )

@app.get("/api/v1/products/{product_id}")
def get_product_details(product_id: str):
    p = repo.get_product(product_id)
    if not p:
        raise HTTPException(status_code=404, detail="Product not found")
    rels = repo.get_relationships_for_product(p.id)
    return {"product": p, "relationships": rels}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8005, reload=True)
