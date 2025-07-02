"""Analysis model for storing AI-generated insights"""

from sqlalchemy import Column, String, Integer, ForeignKey, Text, Float, JSON
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class Analysis(BaseModel):
    """Analysis results model"""
    
    __tablename__ = "analyses"
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    statement_id = Column(Integer, ForeignKey("statements.id"), nullable=False)
    
    # Analysis metadata
    analysis_type = Column(String(50), nullable=False)  # basic, advanced, custom
    model_version = Column(String(50), nullable=False)
    processing_time_seconds = Column(Float, nullable=True)
    
    # Financial summary
    total_income = Column(Float, nullable=True)
    total_expenses = Column(Float, nullable=True)
    net_cash_flow = Column(Float, nullable=True)
    opening_balance = Column(Float, nullable=True)
    closing_balance = Column(Float, nullable=True)
    
    # Analysis results (JSON fields)
    transaction_categories = Column(JSON, nullable=True)
    spending_patterns = Column(JSON, nullable=True)
    income_analysis = Column(JSON, nullable=True)
    anomalies = Column(JSON, nullable=True)
    insights = Column(JSON, nullable=True)
    recommendations = Column(JSON, nullable=True)
    risk_assessment = Column(JSON, nullable=True)
    financial_health_score = Column(Float, nullable=True)
    
    # Raw data
    transactions_data = Column(JSON, nullable=True)
    excel_data_summary = Column(JSON, nullable=True)
    
    # AI-generated content
    summary_text = Column(Text, nullable=True)
    detailed_analysis = Column(Text, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="analyses")
    statement = relationship("Statement", back_populates="analyses")
    
    @property
    def savings_rate(self) -> float:
        """Calculate savings rate"""
        if not self.total_income or self.total_income == 0:
            return 0.0
        return round((self.net_cash_flow / self.total_income) * 100, 2)
    
    @property
    def expense_ratio(self) -> float:
        """Calculate expense ratio"""
        if not self.total_income or self.total_income == 0:
            return 0.0
        return round((self.total_expenses / self.total_income) * 100, 2)