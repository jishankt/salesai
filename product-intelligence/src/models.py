from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any, Union
from datetime import datetime

class ProductPricing(BaseModel):
    amount: float = 0.0
    currency: str = "AED"
    price_type: str = "fixed" # "fixed", "starting_from", "contact_for_price"

class ProductAvailability(BaseModel):
    status: str = "in_stock" # "in_stock", "out_of_stock", "preorder", "unknown"
    stock_count: int = 10
    last_checked_at: Optional[str] = None

class ProductWebsite(BaseModel):
    product_url: str
    image_url: Optional[str] = None
    brochure_url: Optional[str] = None

class ProductSource(BaseModel):
    sheet_row_id: Optional[str] = None
    website_url: Optional[str] = None
    source_type: str = "sheet" # "sheet", "website", "manual", "combined"
    last_synced_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

class ProductRecord(BaseModel):
    id: str
    sku: Optional[str] = None
    name: str
    brand: Optional[str] = "Epson"
    model: Optional[str] = None
    category: str
    subcategory: Optional[str] = None
    product_type: Optional[str] = None
    short_description: Optional[str] = None
    full_description: Optional[str] = None
    specifications: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)
    use_cases: List[str] = Field(default_factory=list)
    pricing: ProductPricing = Field(default_factory=ProductPricing)
    availability: ProductAvailability = Field(default_factory=ProductAvailability)
    website: ProductWebsite
    source: ProductSource = Field(default_factory=ProductSource)
    status: str = "active" # "active", "draft", "inactive"
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

class ProductRelationship(BaseModel):
    id: str
    product_id: str
    related_product_id: str
    relationship_type: str # "ACCESSORY", "COMPATIBLE", "ALTERNATIVE", "UPGRADE", "DOWNGRADE", "SAME_CATEGORY"
    relationship_score: float = 1.0
    relationship_reason: Optional[str] = None

class ProductSearchRequest(BaseModel):
    query: str
    conversation_id: Optional[str] = None
    customer_id: Optional[str] = None
    category: Optional[str] = None
    brand: Optional[str] = None
    limit: int = 5
    required_specifications: Optional[Dict[str, Any]] = None

class ProductMatchedItem(BaseModel):
    id: str
    sku: Optional[str] = None
    name: str
    brand: Optional[str] = None
    category: str
    short_description: Optional[str] = None
    specifications: Dict[str, Any] = Field(default_factory=dict)
    website_url: str
    image_url: Optional[str] = None
    price: float = 0.0
    currency: str = "AED"
    stock_status: str = "in_stock"
    confidence: float = 0.95
    smart_description: Optional[str] = None

class RelatedProductItem(BaseModel):
    id: str
    name: str
    category: str
    relationship_type: str
    relationship_reason: Optional[str] = None
    website_url: str
    price: float = 0.0

class ProductSearchResponse(BaseModel):
    intent: str = "PRODUCT_SEARCH"
    matched_products: List[ProductMatchedItem] = Field(default_factory=list)
    related_products: List[RelatedProductItem] = Field(default_factory=list)
    formatted_whatsapp_message: Optional[str] = None
    needs_clarification: bool = False
    clarification_prompt: Optional[str] = None
