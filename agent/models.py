# models.py
from pydantic import BaseModel, HttpUrl, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from typing import Any, Dict, Literal
from pydantic import BaseModel

class CompareQuery(BaseModel):
    text: str                           # 如 "iPhone 15 Pro 256GB Blue"
    region: str = "AU"                  # 区域影响税费/运费策略（此版先不细分）
    currency: str = "AUD"               # 统一目标币种
    prefs: Dict[str, Any] = {}          # 偏好：only_new, max_results, domains_whitelist, budget...

class PriceItem(BaseModel):
    title: str
    brand: Optional[str] = None
    model: Optional[str] = None
    variant: Optional[str] = None
    price: float
    currency: str = "AUD"
    shipping_cost: float = 0.0
    tax_cost: float = 0.0
    seller: str
    seller_rating: Optional[float] = None     # 0~5
    condition: str = "new"                    # new/used/refurbished/unknown
    url: HttpUrl
    source: str                               
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    @property
    def total_cost(self) -> float:
        return self.price + self.shipping_cost + self.tax_cost

class CompareResult(BaseModel):
    items: List[PriceItem]
    deduped: int
    filtered: int
    citations: List[Dict[str, str]] = []      # 可选：来源链接 [{title,url}]


class AgentQuery(BaseModel):
    text: str
    intent: Optional[str] = None
    user_id: Optional[str] = None
    prefs: Optional[Dict[str, Any]] = None
    history: Optional[List[Dict[str, Any]]] = None
    region: Optional[str] = None
    currency: Optional[str] = None

