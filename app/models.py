from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class AdItem(BaseModel):
    name: str = Field(..., description="Nama iklan")
    cost: float = Field(..., description="Biaya iklan")
    impressions: int = Field(..., description="Jumlah impressions")
    clicks: int = Field(..., description="Jumlah klik")

class FuzzyRankingRequest(BaseModel):
    ads: List[AdItem] = Field(..., description="Daftar iklan yang akan diranking")

class RankedAdItem(BaseModel):
    name: str = Field(..., description="Nama iklan")
    cost: float = Field(..., description="Biaya iklan")
    impressions: int = Field(..., description="Jumlah impressions")
    clicks: int = Field(..., description="Jumlah klik")
    ranking: float = Field(..., description="Nilai ranking (0-1)")
    cost_norm: Optional[float] = Field(None, description="Nilai cost yang sudah dinormalisasi")
    impressions_norm: Optional[float] = Field(None, description="Nilai impressions yang sudah dinormalisasi")
    clicks_norm: Optional[float] = Field(None, description="Nilai clicks yang sudah dinormalisasi")

class FuzzyRankingResponse(BaseModel):
    ranked_ads: List[RankedAdItem] = Field(..., description="Daftar iklan yang sudah diranking")