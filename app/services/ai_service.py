"""AI service for financial analysis using Google Gemini with direct file upload"""

import json
import tempfile
import os
from typing import Dict, List, Any, Optional
from google import genai
from datetime import datetime, timedelta
from app.core.config import settings
from app.core.logging import LoggerMixin
from app.core.exceptions import ExternalServiceError
from app.schemas.analysis import (
    TransactionCategory, SpendingPattern, Anomaly, 
    Insight, Recommendation, RiskAssessment
)


class AIAnalysisService(LoggerMixin):
    """Service for AI-powered financial analysis using Google Gemini with direct file upload"""
    
    def __init__(self):
        # Configure Gemini
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        
    def _create_analysis_prompt(self, analysis_type: str = "comprehensive") -> str:
        """Create comprehensive prompt for financial analysis"""
        
        prompt = f"""
        You are a professional financial analyst with expertise in bank statement analysis. 
        Analyze the uploaded bank statement file and provide comprehensive financial insights.
        
        Please examine the document carefully and provide a detailed analysis including:
        
        1. DOCUMENT STRUCTURE ANALYSIS:
        - Identify the bank name and account type
        - Determine the statement period (start and end dates)
        - Recognize the account number (mask it in output)
        - Identify opening and closing balances
        
        2. TRANSACTION CATEGORIZATION:
        - Categorize all transactions into logical groups (Food & Dining, Transportation, Shopping, Bills & Utilities, Entertainment, Healthcare, Income, etc.)
        - Calculate total amount and percentage for each category
        - Count the number of transactions per category
        - Identify recurring vs one-time transactions
        
        3. SPENDING PATTERNS ANALYSIS:
        - Identify recurring transactions and their frequency (daily, weekly, monthly)
        - Detect seasonal or cyclical spending patterns
        - Calculate average transaction amounts by category
        - Identify largest expense categories and trends
        - Analyze spending velocity (frequency of transactions)
        
        4. INCOME ANALYSIS:
        - Identify all income sources and amounts
        - Determine income stability and frequency patterns
        - Classify primary vs secondary income sources
        - Calculate income growth or decline trends
        - Assess income diversification
        
        5. CASH FLOW ANALYSIS:
        - Calculate net cash flow for the period
        - Identify cash flow patterns throughout the month
        - Determine peak spending and income periods
        - Analyze balance fluctuations and trends
        
        6. ANOMALY DETECTION:
        - Flag unusually large transactions (both income and expenses)
        - Identify duplicate or potentially erroneous transactions
        - Detect spending spikes or unusual patterns
        - Highlight transactions that deviate significantly from normal patterns
        - Identify potential fraud indicators
        
        7. FINANCIAL HEALTH ASSESSMENT:
        - Calculate savings rate (if determinable)
        - Assess expense-to-income ratios
        - Evaluate financial stability indicators
        - Determine cash flow consistency
        - Rate overall financial health on a scale of 1-100
        
        8. INSIGHTS & RECOMMENDATIONS:
        - Identify areas of overspending or potential cost reduction
        - Suggest budget optimizations based on spending patterns
        - Recommend savings opportunities
        - Provide actionable financial advice
        - Highlight positive financial behaviors
        
        9. RISK ASSESSMENT:
        - Evaluate financial stability and potential risks
        - Identify overdraft risks or low balance patterns
        - Assess debt-to-income indicators (if applicable)
        - Rate overall financial risk level
        
        IMPORTANT INSTRUCTIONS:
        - Base your analysis ONLY on the actual data visible in the document
        - Do not make assumptions about data that isn't clearly visible
        - If certain information cannot be determined from the document, state this clearly
        - Provide specific dollar amounts and percentages where possible
        - Use the exact merchant names and transaction descriptions as they appear
        - Be precise about dates and time periods
        
        Please format your response as a valid JSON object with the following structure:
        {{
            "document_info": {{
                "bank_name": "string or null",
                "account_type": "string or null", 
                "statement_period_start": "YYYY-MM-DD or null",
                "statement_period_end": "YYYY-MM-DD or null",
                "opening_balance": float or null,
                "closing_balance": float or null
            }},
            "summary": {{
                "total_income": float,
                "total_expenses": float,
                "net_cash_flow": float,
                "transaction_count": int,
                "financial_health_score": float (0-100)
            }},
            "transaction_categories": [
                {{
                    "category": "string",
                    "amount": float,
                    "count": int,
                    "percentage": float,
                    "avg_transaction_amount": float,
                    "largest_transaction": float,
                    "is_recurring": boolean
                }}
            ],
            "spending_patterns": [
                {{
                    "pattern_type": "string",
                    "description": "string",
                    "frequency": "string",
                    "average_amount": float,
                    "confidence_score": float (0-1),
                    "examples": ["string"]
                }}
            ],
            "income_analysis": {{
                "primary_income": float,
                "secondary_income": float,
                "income_frequency": "string",
                "income_stability": "string",
                "income_sources": [
                    {{
                        "source": "string",
                        "amount": float,
                        "frequency": "string"
                    }}
                ]
            }},
            "cash_flow_analysis": {{
                "average_daily_balance": float,
                "lowest_balance": float,
                "highest_balance": float,
                "balance_volatility": "low|medium|high",
                "cash_flow_trend": "improving|stable|declining"
            }},
            "anomalies": [
                {{
                    "transaction_date": "YYYY-MM-DD",
                    "description": "string",
                    "amount": float,
                    "severity": "low|medium|high",
                    "category": "string",
                    "reason": "string",
                    "confidence_score": float (0-1)
                }}
            ],
            "insights": [
                {{
                    "type": "spending|income|savings|cash_flow|general",
                    "title": "string",
                    "description": "string",
                    "impact": "positive|negative|neutral",
                    "priority": "low|medium|high",
                    "actionable": boolean,
                    "supporting_data": "string"
                }}
            ],
            "recommendations": [
                {{
                    "category": "budgeting|savings|spending|income|general",
                    "title": "string",
                    "description": "string",
                    "potential_savings": float or null,
                    "difficulty": "easy|medium|hard",
                    "timeframe": "immediate|short_term|long_term",
                    "priority": "low|medium|high"
                }}
            ],
            "risk_assessment": {{
                "overall_risk": "low|medium|high",
                "risk_factors": ["string"],
                "risk_score": float (0-100),
                "financial_stability": "stable|moderate|unstable",
                "recommendations": ["string"]
            }},
            "detailed_analysis": "string (comprehensive written analysis of 200-500 words)"
        }}
        
        Ensure all numerical values are realistic and based on the actual data in the document.
        If you cannot determine specific values from the document, use null instead of making assumptions.
        """
        
        return prompt
    
    async def analyze_financial_document(
        self, 
        file_content: bytes, 
        filename: str,
        analysis_type: str = "comprehensive"
    ) -> Dict[str, Any]:
        """Perform comprehensive financial analysis using direct file upload to Gemini"""
        try:
            self.log_operation("ai_analysis_start", filename=filename, analysis_type=analysis_type)
            
            # Create temporary file for upload
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
                temp_file.write(file_content)
                temp_file.flush()
                
                try:
                    # Upload file to Gemini
                    self.log_operation("uploading_file_to_gemini", filename=filename)
                    uploaded_file = self.client.files.upload(
                        file=temp_file.name,
                        # display_name=f"Bank Statement - {filename}"
                    )
                    
                    # Wait for file processing
                    import time
                    while uploaded_file.state.name == "PROCESSING":
                        self.log_operation("waiting_for_file_processing")
                        time.sleep(2)
                        uploaded_file = self.client.files.get(uploaded_file.name)
                    
                    if uploaded_file.state.name == "FAILED":
                        raise ExternalServiceError("File processing failed in Gemini")
                    
                    # Create analysis prompt
                    prompt = self._create_analysis_prompt(analysis_type)
                    
                    # Generate AI analysis with the uploaded file
                    self.log_operation("generating_analysis_with_gemini")
                    response = self.client.models.generate_content(
                        model=settings.GEMINI_MODEL,
                        contents=[
                        uploaded_file,
                        prompt
                    ])
                    
                    if not response.text:
                        raise ExternalServiceError("Empty response from Gemini")
                    
                    # Parse JSON response
                    try:
                        analysis_result = response.text
                        print(analysis_result)
                        self.log_operation("analysis_parsing_successful")
                    except json.JSONDecodeError as e:
                        self.log_error(e, "json_parse_error", response_text=response.text[:500])
                        # Try to extract JSON from response if it's wrapped in markdown
                        response_text = response.text.strip()
                        if response_text.startswith('```json'):
                            response_text = response_text[7:]
                        if response_text.endswith('```'):
                            response_text = response_text[:-3]
                        
                        try:
                            analysis_result = json.loads(response_text.strip())
                        except json.JSONDecodeError:
                            # Fallback: create basic analysis
                            analysis_result = self._create_fallback_analysis(filename)
                    
                    # Validate and enhance the analysis
                    analysis_result = self._validate_and_enhance_analysis(analysis_result, filename)
                    
                    # Clean up uploaded file from Gemini
                    try:
                        self.client.files.delete(name=uploaded_file.name)
                        self.log_operation("gemini_file_cleanup_successful")
                    except Exception as e:
                        self.log_error(e, "gemini_file_cleanup_failed")
                    
                    self.log_operation("ai_analysis_complete", analysis_type=analysis_type)
                    return analysis_result
                    
                finally:
                    # Clean up temporary file
                    try:
                        os.unlink(temp_file.name)
                    except Exception as e:
                        self.log_error(e, "temp_file_cleanup_failed")
                        
        except Exception as e:
            self.log_error(e, "analyze_financial_document", filename=filename)
            # Return fallback analysis instead of failing
            return self._create_fallback_analysis(filename)
    
    def _validate_and_enhance_analysis(self, analysis: Dict[str, Any], filename: str) -> Dict[str, Any]:
        """Validate and enhance AI analysis results"""
        try:
            # Ensure required top-level fields exist
            required_fields = ["summary", "transaction_categories", "spending_patterns", 
                             "income_analysis", "anomalies", "insights", "recommendations", 
                             "risk_assessment"]
            
            for field in required_fields:
                if field not in analysis:
                    analysis[field] = self._get_default_field_value(field)
            
            # Validate summary fields
            if not isinstance(analysis["summary"], dict):
                analysis["summary"] = {}
            
            summary_defaults = {
                "total_income": 0.0,
                "total_expenses": 0.0,
                "net_cash_flow": 0.0,
                "transaction_count": 0,
                "financial_health_score": 50.0
            }
            
            for key, default_value in summary_defaults.items():
                if key not in analysis["summary"] or analysis["summary"][key] is None:
                    analysis["summary"][key] = default_value
            
            # Ensure financial health score is within valid range
            health_score = analysis["summary"].get("financial_health_score", 50.0)
            analysis["summary"]["financial_health_score"] = max(0, min(100, health_score))
            
            # Validate arrays
            array_fields = ["transaction_categories", "spending_patterns", "anomalies", "insights", "recommendations"]
            for field in array_fields:
                if not isinstance(analysis[field], list):
                    analysis[field] = []
            
            # Ensure risk assessment exists
            if not isinstance(analysis["risk_assessment"], dict):
                health_score = analysis["summary"]["financial_health_score"]
                analysis["risk_assessment"] = {
                    "overall_risk": "medium",
                    "risk_factors": ["Limited analysis data available"],
                    "risk_score": max(0, min(100, 100 - health_score)),
                    "financial_stability": "moderate",
                    "recommendations": ["Upload clearer statement for detailed analysis"]
                }
            
            # Add document info if missing
            if "document_info" not in analysis:
                analysis["document_info"] = {
                    "bank_name": None,
                    "account_type": None,
                    "statement_period_start": None,
                    "statement_period_end": None,
                    "opening_balance": None,
                    "closing_balance": None
                }
            
            # Add detailed analysis if missing
            if "detailed_analysis" not in analysis or not analysis["detailed_analysis"]:
                analysis["detailed_analysis"] = self._generate_detailed_analysis_text(analysis, filename)
            
            return analysis
            
        except Exception as e:
            self.log_error(e, "validate_and_enhance_analysis")
            return analysis
    
    def _get_default_field_value(self, field: str) -> Any:
        """Get default value for missing fields"""
        defaults = {
            "summary": {"total_income": 0, "total_expenses": 0, "net_cash_flow": 0, "financial_health_score": 50},
            "transaction_categories": [],
            "spending_patterns": [],
            "income_analysis": {"primary_income": 0, "secondary_income": 0, "income_sources": []},
            "anomalies": [],
            "insights": [],
            "recommendations": [],
            "risk_assessment": {"overall_risk": "medium", "risk_factors": [], "risk_score": 50, "recommendations": []}
        }
        return defaults.get(field, {})
    
    def _generate_detailed_analysis_text(self, analysis: Dict[str, Any], filename: str) -> str:
        """Generate detailed analysis text from structured data"""
        try:
            summary = analysis.get("summary", {})
            total_income = summary.get("total_income", 0)
            total_expenses = summary.get("total_expenses", 0)
            net_cash_flow = summary.get("net_cash_flow", 0)
            health_score = summary.get("financial_health_score", 50)
            
            analysis_text = f"""
            Financial Analysis Summary for {filename}:
            
            This comprehensive analysis reveals a financial health score of {health_score:.1f}/100. 
            During the analyzed period, total income was ${total_income:,.2f} while total expenses 
            amounted to ${total_expenses:,.2f}, resulting in a net cash flow of ${net_cash_flow:,.2f}.
            
            """
            
            # Add insights summary
            insights = analysis.get("insights", [])
            if insights:
                analysis_text += "Key Insights:\n"
                for insight in insights[:3]:  # Top 3 insights
                    analysis_text += f"• {insight.get('title', 'N/A')}: {insight.get('description', 'N/A')}\n"
                analysis_text += "\n"
            
            # Add recommendations summary
            recommendations = analysis.get("recommendations", [])
            if recommendations:
                analysis_text += "Top Recommendations:\n"
                for rec in recommendations[:3]:  # Top 3 recommendations
                    analysis_text += f"• {rec.get('title', 'N/A')}: {rec.get('description', 'N/A')}\n"
            
            return analysis_text.strip()
            
        except Exception as e:
            self.log_error(e, "_generate_detailed_analysis_text")
            return f"Analysis completed for {filename}. Please review the structured data for detailed insights."
    
    def _create_fallback_analysis(self, filename: str) -> Dict[str, Any]:
        """Create basic fallback analysis when AI processing fails"""
        try:
            self.log_operation("creating_fallback_analysis", filename=filename)
            
            return {
                "document_info": {
                    "bank_name": None,
                    "account_type": None,
                    "statement_period_start": None,
                    "statement_period_end": None,
                    "opening_balance": None,
                    "closing_balance": None
                },
                "summary": {
                    "total_income": 0.0,
                    "total_expenses": 0.0,
                    "net_cash_flow": 0.0,
                    "transaction_count": 0,
                    "financial_health_score": 30.0
                },
                "transaction_categories": [],
                "spending_patterns": [],
                "income_analysis": {
                    "primary_income": 0.0,
                    "secondary_income": 0.0,
                    "income_frequency": "Unknown",
                    "income_stability": "Unknown",
                    "income_sources": []
                },
                "cash_flow_analysis": {
                    "average_daily_balance": 0.0,
                    "lowest_balance": 0.0,
                    "highest_balance": 0.0,
                    "balance_volatility": "unknown",
                    "cash_flow_trend": "unknown"
                },
                "anomalies": [],
                "insights": [
                    {
                        "type": "general",
                        "title": "Analysis Limitation",
                        "description": "Unable to perform detailed analysis due to processing limitations. Please try uploading a clearer PDF file.",
                        "impact": "neutral",
                        "priority": "medium",
                        "actionable": True,
                        "supporting_data": "File processing failed"
                    }
                ],
                "recommendations": [
                    {
                        "category": "general",
                        "title": "Improve File Quality",
                        "description": "Upload a higher quality PDF bank statement for more accurate analysis.",
                        "potential_savings": None,
                        "difficulty": "easy",
                        "timeframe": "immediate",
                        "priority": "high"
                    }
                ],
                "risk_assessment": {
                    "overall_risk": "high",
                    "risk_factors": ["Analysis incomplete due to processing limitations"],
                    "risk_score": 70.0,
                    "financial_stability": "unknown",
                    "recommendations": ["Upload a clearer bank statement", "Ensure PDF is text-based, not scanned image"]
                },
                "detailed_analysis": f"Analysis of {filename} could not be completed due to processing limitations. This may be due to poor PDF quality, scanned images instead of text-based PDF, or file corruption. Please try uploading a clearer, text-based PDF bank statement for accurate financial analysis."
            }
            
        except Exception as e:
            self.log_error(e, "create_fallback_analysis")
            return {
                "summary": {"total_income": 0, "total_expenses": 0, "net_cash_flow": 0, "financial_health_score": 0},
                "transaction_categories": [],
                "spending_patterns": [],
                "income_analysis": {"primary_income": 0, "secondary_income": 0, "income_sources": []},
                "anomalies": [],
                "insights": [],
                "recommendations": [],
                "risk_assessment": {"overall_risk": "high", "risk_factors": ["Analysis failed"], "risk_score": 100, "recommendations": []},
                "detailed_analysis": "Analysis could not be completed due to processing errors."
            }


# Create service instance
ai_service = AIAnalysisService()