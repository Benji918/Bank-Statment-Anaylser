"""Analysis service for managing financial analysis operations"""
from fastapi import HTTPException
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from starlette import status
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

            if not isinstance(analysis_result, dict):
                raise ValidationError("AI service returned unexpected data type")


            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()

            document_info = analysis_result["document_info"]

            analysis = Analysis(
                statement_id=statement_id,
                user_id=user_id,
                analysis_type=analysis_type,
                model_version="gemini-2.0-flash",
                processing_time_seconds=processing_time,
                # Financial summary
                total_income=analysis_result["summary"]["total_income"],
                total_expenses=analysis_result["summary"]["total_expenses"],
                net_cash_flow=analysis_result["summary"]["net_cash_flow"],
                opening_balance=document_info["opening_balance"],
                closing_balance=document_info["closing_balance"],
                financial_health_score=analysis_result["summary"]["financial_health_score"],
                # Analysis results as JSON
                transaction_categories=json.dumps(analysis_result["transaction_categories"]),
                spending_patterns=json.dumps(analysis_result["spending_patterns"]),
                income_analysis=json.dumps(analysis_result["income_analysis"]),
                anomalies=json.dumps(analysis_result["anomalies"]),
                insights=json.dumps(analysis_result["insights"]),
                recommendations=json.dumps(analysis_result["recommendations"]),
                risk_assessment=json.dumps(analysis_result["risk_assessment"]),
                # Raw data - store the complete analysis result
                transactions_data=json.dumps(analysis_result["cash_flow_analysis"]),
                excel_data_summary=json.dumps(document_info),
                # AI-generated content
                summary_text=self._generate_summary_text(analysis_result),
                detailed_analysis=analysis_result["detailed_analysis"],
            )

            db.add(analysis)
            db.commit()
            db.refresh(analysis)


            if document_info["statement_period_start"]:
                statement.statement_period_start = document_info["statement_period_start"]
            if document_info["statement_period_end"]:
                statement.statement_period_end = document_info["statement_period_end"]
            if document_info["bank_name"]:
                statement.bank_name = document_info["bank_name"]
            if document_info["account_type"]:
                statement.account_type = document_info["account_type"]
            
            db.add(statement)
            

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
            
        except (ValidationError, FileProcessingError) as e:

            try:
                pass
                from app.services.statement_service import statement_service
                statement_service.update_processing_status(
                    db, statement_id, StatementStatus.FAILED, str(e)
                )
            except:
                pass
            raise FileProcessingError("Failed to create analysis")
        except Exception as e:

            try:
                pass
                from app.services.statement_service import statement_service
                statement_service.update_processing_status(
                    db, statement_id, StatementStatus.FAILED, str(e)
                )
            except:
                pass
            
            self.log_error(e, "create_analysis", statement_id=statement_id)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create analysis"
            )
    
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
            

            total = query.count()
            

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
            

            avg_processing_time = db.query(
                func.avg(Analysis.processing_time_seconds)
            ).filter(Analysis.user_id == user_id).scalar() or 0
            

            avg_health_score = db.query(
                func.avg(Analysis.financial_health_score)
            ).filter(
                and_(
                    Analysis.user_id == user_id,
                    Analysis.financial_health_score.isnot(None)
                )
            ).scalar() or 0


            # Get analyses with transaction categories
            analyses_with_categories = db.query(Analysis.transaction_categories) \
                .filter(
                and_(
                    Analysis.user_id == user_id,
                    Analysis.transaction_categories.isnot(None)
                )
            ).all()


            category_totals = {}
            for (categories_json,) in analyses_with_categories:
                if categories_json:
                    try:
                        categories = json.loads(categories_json)
                        if isinstance(categories, list):
                            for category in categories:
                                if isinstance(category, dict) and 'category' in category:
                                    cat_name = category['category']
                                    cat_count = category.get('count', 0)

                                    category_totals[cat_name] = category_totals.get(cat_name, 0) + cat_count

                    except (json.JSONDecodeError, TypeError):
                        continue

            # Get top 5 categories by transaction count
            sorted_categories = sorted(category_totals.items(), key=lambda x: x[1], reverse=True)[:5]
            most_common_categories = [
                {"category": cat, "count": count}
                for cat, count in sorted_categories
            ]



            # Recent insights count (last 30 days)
            from datetime import timedelta
            thirty_days_ago = datetime.now() - timedelta(days=30)
            recent_insights_count = db.query(Analysis).filter(
                and_(
                    Analysis.user_id == user_id,
                    Analysis.created_at >= thirty_days_ago
                )
            ).count()
            
            stats = {
                "total_analyses": int(total_analyses),
                "avg_processing_time": round(avg_processing_time, 2),
                "avg_financial_health_score": round(avg_health_score, 2),
                "most_common_categories": most_common_categories,
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