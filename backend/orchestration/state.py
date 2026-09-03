from dataclasses import dataclass, field, asdict
from typing import Optional, Literal, List, Dict, Any
import datetime

Intent = Literal[
    "general",
    "product_discovery",
    "product_search",
    "product_details",
    "product_comparison",
    "consumables",
    "pricing",
    "quotation",
    "cart",
    "checkout",
    "order_tracking",
    "support",
    "human_handoff",
]

SalesStage = Literal[
    "discovery",
    "qualification",
    "recommendation",
    "evaluation",
    "pricing",
    "quotation",
    "closing",
]

BuyingIntent = Literal[
    "none",
    "low",
    "medium",
    "high",
]


@dataclass
class ConversationAIState:
    session_id: str

    intent: Intent = "general"
    sales_stage: SalesStage = "discovery"

    # Product requirement / Qualification
    category: Optional[str] = None
    use_case: Optional[str] = None
    print_size: Optional[str] = None
    daily_volume: Optional[int] = None
    monthly_volume: Optional[int] = None
    scan_required: Optional[bool] = None
    color_required: Optional[bool] = None
    quantity: Optional[int] = None
    budget: Optional[float] = None
    location: Optional[str] = None

    # Product resolution
    mentioned_models: List[str] = field(default_factory=list)
    selected_product_id: Optional[str] = None
    selected_sku: Optional[str] = None
    selected_product_name: Optional[str] = None

    # Conversation control
    last_question_field: Optional[str] = None
    next_action: Optional[str] = None
    asked_fields: List[str] = field(default_factory=list)

    # Commercial & Sales
    buying_intent: BuyingIntent = "none"

    # Safety & Escalation
    needs_human: bool = False
    frustration_detected: bool = False

    # Metadata & Tracking
    turn_count: int = 0
    updated_at: str = field(default_factory=lambda: datetime.datetime.utcnow().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConversationAIState":
        if not data:
            return cls(session_id="default")
        valid_keys = cls.__dataclass_fields__.keys()
        clean_data = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**clean_data)
