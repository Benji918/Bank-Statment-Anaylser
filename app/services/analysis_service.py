"""Analysis service for managing financial analysis operations"""

from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.models.analysis import Analysis
from app.models.statement import Statement, StatementStatus
from app.schemas.analysis import AnalysisCreate, AnalysisListParams
from app.services.base import BaseService
from app.services.file_service import file_service
from app.services.ai_service import ai_service
from app.core.exceptions import ValidationError, FileProcessingError
import json
from datetime import datetime


class AnalysisService(BaseService[Analysis, AnalysisCreate, dict]):
    """Service for managing financial analysis"""
    
    def __init__(self):
        super().__init__(Analysis)
    
    async def create_analysis(
        self, 
        db: Session, 
        statement_id: int, 
        user_id: int,
        analysis_type: str = "comprehensive"
    ) -> Analysis:
        """Create comprehensive financial analysis for a statement"""
        try:
            # Get statement
            statement = db.query(Statement).filter(
                and_(Statement.id == statement_id, Statement.user_id == user_id)
            ).first()
            
            if not statement:
                raise ValidationError("Statement not found")
            
            if statement.status != StatementStatus.UPLOADED:
                raise ValidationError("Statement must be in uploaded status for analysis")
            
            # Update statement status to processing
            from app.services.statement_service import statement_service
            statement_service.update_processing_status(
                db, statement_id, StatementStatus.PROCESSING
            )
            
            # Download file from Cloudinary
            pdf_content = await file_service.download_from_cloudinary(
                statement.cloudinary_public_id
            )
            
            # Perform AI analysis directly with PDF file
            start_time = datetime.utcnow()
            analysis_result = await ai_service.analyze_financial_document(
                pdf_content, 
                statement.original_filename,
                analysis_type
            )
            end_time = datetime.utcnow()
            
            processing_time = (end_time - start_time).total_seconds()
            
            # Extract document info if available
            document_info = analysis_result.get("document_info", {})
            
            # Create analysis record
            analysis = self.create(
                db,
                AnalysisCreate(statement_id=statement_id),
                user_id=user_id,
                analysis_type=analysis_type,
                model_version="gemini-pro-v1",
                processing_time_seconds=processing_time,
                
                # Financial summary
                total_income=analysis_result["summary"].get("total_income"),
                total_expenses=analysis_result["summary"].get("total_expenses"),
                net_cash_flow=analysis_result["summary"].get("net_cash_flow"),
                opening_balance=document_info.get("opening_balance"),
                closing_balance=document_info.get("closing_balance"),
                financial_health_score=analysis_result["summary"].get("financial_health_score"),
                
                # Analysis results as JSON
                transaction_categories=json.dumps(analysis_result.get("transaction_categories", [])),
                spending_patterns=json.dumps(analysis_result.get("spending_patterns", [])),
                income_analysis=json.dumps(analysis_result.get("income_analysis", {})),
                anomalies=json.dumps(analysis_result.get("anomalies", [])),
                insights=json.dumps(analysis_result.get("insights", [])),
                recommendations=json.dumps(analysis_result.get("recommendations", [])),
                risk_assessment=json.dumps(analysis_result.get("risk_assessment", {})),
                
                # Raw data - store the complete analysis result
                transactions_data=json.dumps(analysis_result.get("cash_flow_analysis", {})),
                excel_data_summary=json.dumps(document_info),
                
                # AI-generated content
                summary_text=self._generate_summary_text(analysis_result),
                detailed_analysis=analysis_result.get("detailed_analysis", "")
            )
            
            # Update statement with document info if available
            if document_info.get("statement_period_start"):
                statement.statement_period_start = document_info["statement_period_start"]
            if document_info.get("statement_period_end"):
                statement.statement_period_end = document_info["statement_period_end"]
            if document_info.get("bank_name"):
                statement.bank_name = document_info["bank_name"]
            if document_info.get("account_type"):
                statement.account_type = document_info["account_type"]
            
            db.add(statement)
            
            # Update statement status to completed
            statement_service.update_processing_status(
                db, statement_id, StatementStatus.COMPLETED
            )
            
            self.log_operation(
                "create_analysis",
                analysis_id=analysis.id,
                statement_id=statement_id,
                user_id=user_id,
                processing_time=processing_time
            )
            
            return analysis
            
        except (ValidationError, FileProcessingError):
            # Update statement status to failed
            try:
                from app.services.statement_service import statement_service
                statement_service.update_processing_status(
                    db, statement_id, StatementStatus.FAILED, str(e)
                )
            except:
                pass
            raise
        except Exception as e:
            # Update statement status to failed
            try:
                from app.services.statement_service import statement_service
                statement_service.update_processing_status(
                    db, statement_id, StatementStatus.FAILED, str(e)
                )
            except:
                pass
            
            self.log_error(e, "create_analysis", statement_id=statement_id)
            raise FileProcessingError("Failed to create analysis")
    
    def get_user_analyses(
        self, 
        db: Session, 
        user_id: int, 
        params: AnalysisListParams
    ) -> tuple[List[Analysis], int]:
        """Get user analyses with filtering and pagination"""
        try:
            query = db.query(Analysis).filter(Analysis.user_id == user_id)
            
            # Apply filters
            if params.statement_id:
                query = query.filter(Analysis.statement_id == params.statement_id)
            
            if params.analysis_type:
                query = query.filter(Analysis.analysis_type == params.analysis_type)
            
            if params.start_date:
                query = query.filter(Analysis.created_at >= params.start_date)
            
            if params.end_date:
                query = query.filter(Analysis.created_at <= params.end_date)
            
            # Get total count
            total = query.count()
            
            # Apply pagination
            offset = (params.page - 1) * params.size
            analyses = query.offset(offset).limit(params.size).all()
            
            self.log_operation(
                "get_user_analyses",
                user_id=user_id,
                total=total,
                page=params.page
            )
            
            return analyses, total
            
        except Exception as e:
            self.log_error(e, "get_user_analyses", user_id=user_id)
            raise
    
    def get_analysis_with_statement(
        self, 
        db: Session, 
        analysis_id: int, 
        user_id: int
    ) -> Optional[Analysis]:
        """Get analysis with related statement data"""
        try:
            analysis = db.query(Analysis).filter(
                and_(Analysis.id == analysis_id, Analysis.user_id == user_id)
            ).first()
            
            if analysis:
                # Load related statement
                db.refresh(analysis)
                
            return analysis
            
        except Exception as e:
            self.log_error(e, "get_analysis_with_statement", analysis_id=analysis_id)
            raise
    
    def get_analysis_stats(self, db: Session, user_id: int) -> Dict[str, Any]:
        """Get analysis statistics for user"""
        try:
            total_analyses = db.query(Analysis).filter(
                Analysis.user_id == user_id
            ).count()
            
            if total_analyses == 0:
                return {
                    "total_analyses": 0,
                    "avg_processing_time": 0,
                    "avg_financial_health_score": 0,
                    "most_common_categories": [],
                    "recent_insights_count": 0
                }
            
            # Average processing time
            avg_processing_time = db.query(
                db.func.avg(Analysis.processing_time_seconds)
            ).filter(Analysis.user_id == user_id).scalar() or 0
            
            # Average financial health score
            avg_health_score = db.query(
                db.func.avg(Analysis.financial_health_score)
            ).filter(
                and_(
                    Analysis.user_id == user_id,
                    Analysis.financial_health_score.isnot(None)
                )
            ).scalar() or 0
            
            # Recent insights count (last 30 days)
            from datetime import timedelta
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)
            recent_insights_count = db.query(Analysis).filter(
                and_(
                    Analysis.user_id == user_id,
                    Analysis.created_at >= thirty_days_ago
                )
            ).count()
            
            stats = {
                "total_analyses": total_analyses,
                "avg_processing_time": round(avg_processing_time, 2),
                "avg_financial_health_score": round(avg_health_score, 2),
                "most_common_categories": [],  # Would need to parse JSON data
                "recent_insights_count": recent_insights_count
            }
            
            self.log_operation("get_analysis_stats", user_id=user_id, stats=stats)
            return stats
            
        except Exception as e:
            self.log_error(e, "get_analysis_stats", user_id=user_id)
            return {}
    
    def _generate_summary_text(self, analysis_result: Dict[str, Any]) -> str:
        """Generate human-readable summary text from analysis results"""
        try:
            summary = analysis_result.get("summary", {})
            
            total_income = summary.get("total_income", 0)
            total_expenses = summary.get("total_expenses", 0)
            net_cash_flow = summary.get("net_cash_flow", 0)
            health_score = summary.get("financial_health_score", 0)
            transaction_count = summary.get("transaction_count", 0)
            
            summary_text = f"""
            Financial Analysis Summary:
            
            Total Income: ${total_income:,.2f}
            Total Expenses: ${total_expenses:,.2f}
            Net Cash Flow: ${net_cash_flow:,.2f}
            Transaction Count: {transaction_count}
            Financial Health Score: {health_score:.1f}/100
            
            """
            
            # Add insights summary
            insights = analysis_result.get("insights", [])
            if insights:
                summary_text += "Key Insights:\n"
                for insight in insights[:3]:  # Top 3 insights
                    summary_text += f"• {insight.get('title', 'N/A')}\n"
            
            # Add top recommendations
            recommendations = analysis_result.get("recommendations", [])
            if recommendations:
                summary_text += "\nTop Recommendations:\n"
                for rec in recommendations[:3]:  # Top 3 recommendations
                    summary_text += f"• {rec.get('title', 'N/A')}\n"
            
            return summary_text.strip()
            
        except Exception as e:
            self.log_error(e, "_generate_summary_text")
            return "Analysis completed successfully."


# Create service instance
analysis_service = AnalysisService()