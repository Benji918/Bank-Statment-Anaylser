"""Analysis schemas"""

from typing import Optional, Dict, List, Any
from datetime import datetime
from pydantic import Field, validator
from app.schemas.base import BaseSchema, TimestampMixin


class AnalysisBase(BaseSchema):
    """Base analysis schema"""
    analysis_type: str = Field(..., description="Type of analysis performed")


class AnalysisCreate(AnalysisBase):
    """Analysis creation schema"""
    statement_id: int


class TransactionCategory(BaseSchema):
    """Transaction category schema"""
    category: str
    amount: float
    count: int
    percentage: float


class SpendingPattern(BaseSchema):
    """Spending pattern schema"""
    pattern_type: str
    description: str
    frequency: str
    average_amount: float
    confidence_score: float


class Anomaly(BaseSchema):
    """Anomaly detection schema"""
    transaction_id: Optional[str] = None
    description: str
    severity: str  # low, medium, high
    amount: float
    date: Optional[datetime] = None
    transaction_date: Optional[str] = None
    category: str
    confidence_score: float


class Insight(BaseSchema):
    """Financial insight schema"""
    type: str  # spending, income, savings, etc.
    title: str
    description: str
    impact: str  # positive, negative, neutral
    priority: str  # low, medium, high
    actionable: bool


class Recommendation(BaseSchema):
    """Financial recommendation schema"""
    category: str
    title: str
    description: str
    potential_savings: Optional[float] = None
    difficulty: str  # easy, medium, hard
    timeframe: str  # immediate, short_term, long_term


class RiskAssessment(BaseSchema):
    """Risk assessment schema"""
    overall_risk: str  # low, medium, high
    risk_factors: List[str]
    risk_score: float  # 0-100
    recommendations: List[str]


class AnalysisResponse(AnalysisBase, TimestampMixin):
    """Analysis response schema"""
    id: int
    user_id: int
    statement_id: int
    model_version: str
    processing_time_seconds: Optional[float] = None
    
    # Financial summary
    total_income: Optional[float] = None
    total_expenses: Optional[float] = None
    net_cash_flow: Optional[float] = None
    opening_balance: Optional[float] = None
    closing_balance: Optional[float] = None
    financial_health_score: Optional[float] = None
    
    # Analysis results
    transaction_categories: Optional[List[TransactionCategory]] = None
    spending_patterns: Optional[List[SpendingPattern]] = None
    anomalies: Optional[List[Anomaly]] = None
    insights: Optional[List[Insight]] = None
    recommendations: Optional[List[Recommendation]] = None
    risk_assessment: Optional[RiskAssessment] = None
    
    # AI-generated content
    summary_text: Optional[str] = None
    detailed_analysis: Optional[str] = None
    
    @property
    def savings_rate(self) -> float:
        if not self.total_income or self.total_income == 0:
            return 0.0
        return round((self.net_cash_flow / self.total_income) * 100, 2)


class AnalysisListParams(BaseSchema):
    """Analysis list parameters"""
    statement_id: Optional[int] = None
    analysis_type: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    page: int = Field(default=1, ge=1)
    size: int = Field(default=20, ge=1, le=100)


class AnalysisStats(BaseSchema):
    """Analysis statistics schema"""
    total_analyses: int
    avg_processing_time: float
    avg_financial_health_score: float
    most_common_categories: List[Dict[str, Any]]
    recent_insights_count: int