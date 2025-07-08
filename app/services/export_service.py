"""Export service for generating reports in various formats"""

import io
import csv
import json
import tempfile
import os
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, date
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.charts.linecharts import HorizontalLineChart
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.charts.barcharts import VerticalBarChart
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.backends.backend_agg import FigureCanvasAgg
import seaborn as sns
from PIL import Image as PILImage
import base64

from app.models.analysis import Analysis
from app.models.statement import Statement
from app.core.logging import LoggerMixin
from app.core.exceptions import ValidationError, FileProcessingError


class ExportService(LoggerMixin):
    """Service for exporting analysis data in various formats"""

    def __init__(self):
        # Set matplotlib style
        plt.style.use('seaborn-v0_8')
        sns.set_palette("husl")

    def export_analysis_data(
            self,
            db: Session,
            user_id: int,
            export_format: str,
            start_date: Optional[date] = None,
            end_date: Optional[date] = None,
            statement_ids: Optional[List[int]] = None,
            analysis_types: Optional[List[str]] = None,
            include_charts: bool = True
    ) -> bytes:
        """
        Export analysis data in specified format

        Args:
            db: Database session
            user_id: User ID
            export_format: Format to export (pdf, csv, excel, json, png)
            start_date: Start date filter
            end_date: End date filter
            statement_ids: Specific statement IDs to export
            analysis_types: Types of analysis to include
            include_charts: Whether to include charts in export

        Returns:
            bytes: Exported data
        """
        try:
            # Get filtered analysis data
            analyses = self._get_filtered_analyses(
                db, user_id, start_date, end_date, statement_ids, analysis_types
            )

            if not analyses:
                raise ValidationError("No analysis data found for the specified criteria")

            # Export based on format
            if export_format.lower() == 'pdf':
                return self._export_to_pdf(analyses, include_charts)
            elif export_format.lower() == 'csv':
                return self._export_to_csv(analyses)
            elif export_format.lower() == 'excel':
                return self._export_to_excel(analyses, include_charts)
            elif export_format.lower() == 'json':
                return self._export_to_json(analyses)
            elif export_format.lower() == 'png':
                return self._export_charts_to_image(analyses)
            else:
                raise ValidationError(f"Unsupported export format: {export_format}")

        except Exception as e:
            self.log_error(e, "export_analysis_data", user_id=user_id, format=export_format)
            raise FileProcessingError(f"Failed to export data: {str(e)}")

    def _get_filtered_analyses(
            self,
            db: Session,
            user_id: int,
            start_date: Optional[date] = None,
            end_date: Optional[date] = None,
            statement_ids: Optional[List[int]] = None,
            analysis_types: Optional[List[str]] = None
    ) -> List[Analysis]:
        """Get filtered analysis data"""

        query = db.query(Analysis).filter(Analysis.user_id == user_id)

        # Date filters
        if start_date:
            query = query.filter(Analysis.created_at >= start_date)
        if end_date:
            query = query.filter(Analysis.created_at <= end_date)

        # Statement ID filters
        if statement_ids:
            query = query.filter(Analysis.statement_id.in_(statement_ids))

        # Analysis type filters
        if analysis_types:
            query = query.filter(Analysis.analysis_type.in_(analysis_types))

        return query.order_by(Analysis.created_at.desc()).all()

    def _export_to_pdf(self, analyses: List[Analysis], include_charts: bool = True) -> bytes:
        """Export analysis data to PDF format"""

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        styles = getSampleStyleSheet()
        story = []

        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            textColor=colors.HexColor('#1f2937')
        )
        story.append(Paragraph("Financial Analysis Report", title_style))
        story.append(Spacer(1, 20))

        # Summary section
        story.append(Paragraph("Executive Summary", styles['Heading2']))

        # Calculate summary statistics
        total_analyses = len(analyses)
        avg_health_score = sum(a.financial_health_score or 0 for a in analyses) / total_analyses if total_analyses > 0 else 0
        total_income = sum(a.total_income or 0 for a in analyses)
        total_expenses = sum(a.total_expenses or 0 for a in analyses)
        net_cash_flow = total_income - total_expenses

        summary_data = [
            ['Metric', 'Value'],
            ['Total Analyses', str(total_analyses)],
            ['Average Financial Health Score', f"{avg_health_score:.1f}/100"],
            ['Total Income', f"${total_income:,.2f}"],
            ['Total Expenses', f"${total_expenses:,.2f}"],
            ['Net Cash Flow', f"${net_cash_flow:,.2f}"]
        ]

        summary_table = Table(summary_data)
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3b82f6')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))

        story.append(summary_table)
        story.append(Spacer(1, 30))


        story.append(Paragraph("Detailed Analysis Results", styles['Heading2']))

        for i, analysis in enumerate(analyses):
            story.append(Paragraph(f"Analysis {i+1}: {analysis.statement.original_filename if analysis.statement else 'Unknown'}", styles['Heading3']))


            analysis_data = [
                ['Field', 'Value'],
                ['Analysis Type', analysis.analysis_type or 'N/A'],
                ['Date', analysis.created_at.strftime('%Y-%m-%d %H:%M')],
                ['Processing Time', f"{analysis.processing_time_seconds or 0:.2f} seconds"],
                ['Financial Health Score', f"{analysis.financial_health_score or 0:.1f}/100"],
                ['Total Income', f"${analysis.total_income or 0:,.2f}"],
                ['Total Expenses', f"${analysis.total_expenses or 0:,.2f}"],
                ['Net Cash Flow', f"${analysis.net_cash_flow or 0:,.2f}"]
            ]

            analysis_table = Table(analysis_data, colWidths=[2*inch, 3*inch])
            analysis_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#6b7280')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))

            story.append(analysis_table)

            # Add insights if available
            if analysis.summary_text:
                story.append(Spacer(1, 10))
                story.append(Paragraph("Key Insights:", styles['Heading4']))
                story.append(Paragraph(analysis.summary_text, styles['Normal']))

            story.append(Spacer(1, 20))

        # Add charts if requested
        if include_charts:
            story.append(Paragraph("Visual Analysis", styles['Heading2']))
            chart_image = self._generate_summary_chart(analyses)
            if chart_image:
                story.append(chart_image)

        doc.build(story)
        buffer.seek(0)
        return buffer.getvalue()

    def _export_to_csv(self, analyses: List[Analysis]) -> bytes:
        """Export analysis data to CSV format"""

        buffer = io.StringIO()
        writer = csv.writer(buffer)

        # Write header
        headers = [
            'Analysis ID', 'Statement Filename', 'Analysis Type', 'Date Created',
            'Processing Time (seconds)', 'Financial Health Score', 'Total Income',
            'Total Expenses', 'Net Cash Flow', 'Opening Balance', 'Closing Balance',
            'Summary Text'
        ]
        writer.writerow(headers)

        # Write data rows
        for analysis in analyses:
            row = [
                analysis.id,
                analysis.statement.original_filename if analysis.statement else 'N/A',
                analysis.analysis_type or 'N/A',
                analysis.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                analysis.processing_time_seconds or 0,
                analysis.financial_health_score or 0,
                analysis.total_income or 0,
                analysis.total_expenses or 0,
                analysis.net_cash_flow or 0,
                analysis.opening_balance or 0,
                analysis.closing_balance or 0,
                (analysis.summary_text or '').replace('\n', ' ').replace('\r', ' ')
            ]
            writer.writerow(row)

        # Convert to bytes
        csv_content = buffer.getvalue()
        return csv_content.encode('utf-8')

    def _export_to_excel(self, analyses: List[Analysis], include_charts: bool = True) -> bytes:
        """Export analysis data to Excel format with multiple sheets"""

        buffer = io.BytesIO()

        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            # Summary sheet
            summary_data = []
            for analysis in analyses:
                summary_data.append({
                    'Analysis ID': analysis.id,
                    'Statement Filename': analysis.statement.original_filename if analysis.statement else 'N/A',
                    'Analysis Type': analysis.analysis_type or 'N/A',
                    'Date Created': analysis.created_at,
                    'Processing Time (seconds)': analysis.processing_time_seconds or 0,
                    'Financial Health Score': analysis.financial_health_score or 0,
                    'Total Income': analysis.total_income or 0,
                    'Total Expenses': analysis.total_expenses or 0,
                    'Net Cash Flow': analysis.net_cash_flow or 0,
                    'Opening Balance': analysis.opening_balance or 0,
                    'Closing Balance': analysis.closing_balance or 0
                })

            summary_df = pd.DataFrame(summary_data)
            summary_df.to_excel(writer, sheet_name='Summary', index=False)

            # Detailed insights sheet
            insights_data = []
            for analysis in analyses:
                if analysis.insights:
                    try:
                        insights = json.loads(analysis.insights)
                        for insight in insights:
                            insights_data.append({
                                'Analysis ID': analysis.id,
                                'Statement': analysis.statement.original_filename if analysis.statement else 'N/A',
                                'Insight Type': insight.get('type', 'N/A'),
                                'Title': insight.get('title', 'N/A'),
                                'Description': insight.get('description', 'N/A'),
                                'Impact': insight.get('impact', 'N/A'),
                                'Priority': insight.get('priority', 'N/A')
                            })
                    except (json.JSONDecodeError, TypeError):
                        pass

            if insights_data:
                insights_df = pd.DataFrame(insights_data)
                insights_df.to_excel(writer, sheet_name='Insights', index=False)

            # Recommendations sheet
            recommendations_data = []
            for analysis in analyses:
                if analysis.recommendations:
                    try:
                        recommendations = json.loads(analysis.recommendations)
                        for rec in recommendations:
                            recommendations_data.append({
                                'Analysis ID': analysis.id,
                                'Statement': analysis.statement.original_filename if analysis.statement else 'N/A',
                                'Category': rec.get('category', 'N/A'),
                                'Title': rec.get('title', 'N/A'),
                                'Description': rec.get('description', 'N/A'),
                                'Potential Savings': rec.get('potential_savings', 0),
                                'Difficulty': rec.get('difficulty', 'N/A'),
                                'Timeframe': rec.get('timeframe', 'N/A')
                            })
                    except (json.JSONDecodeError, TypeError):
                        pass

            if recommendations_data:
                recommendations_df = pd.DataFrame(recommendations_data)
                recommendations_df.to_excel(writer, sheet_name='Recommendations', index=False)

        buffer.seek(0)
        return buffer.getvalue()

    def _export_to_json(self, analyses: List[Analysis]) -> bytes:
        """Export analysis data to JSON format"""

        export_data = {
            'export_metadata': {
                'generated_at': datetime.utcnow().isoformat(),
                'total_analyses': len(analyses),
                'date_range': {
                    'start': min(a.created_at for a in analyses).isoformat() if analyses else None,
                    'end': max(a.created_at for a in analyses).isoformat() if analyses else None
                }
            },
            'analyses': []
        }

        for analysis in analyses:
            analysis_data = {
                'id': analysis.id,
                'statement_info': {
                    'filename': analysis.statement.original_filename if analysis.statement else None,
                    'statement_id': analysis.statement_id
                },
                'analysis_metadata': {
                    'type': analysis.analysis_type,
                    'created_at': analysis.created_at.isoformat(),
                    'processing_time_seconds': analysis.processing_time_seconds,
                    'model_version': analysis.model_version
                },
                'financial_summary': {
                    'total_income': analysis.total_income,
                    'total_expenses': analysis.total_expenses,
                    'net_cash_flow': analysis.net_cash_flow,
                    'opening_balance': analysis.opening_balance,
                    'closing_balance': analysis.closing_balance,
                    'financial_health_score': analysis.financial_health_score
                },
                'analysis_results': {
                    'transaction_categories': self._parse_json_field(analysis.transaction_categories),
                    'spending_patterns': self._parse_json_field(analysis.spending_patterns),
                    'anomalies': self._parse_json_field(analysis.anomalies),
                    'insights': self._parse_json_field(analysis.insights),
                    'recommendations': self._parse_json_field(analysis.recommendations),
                    'risk_assessment': self._parse_json_field(analysis.risk_assessment)
                },
                'text_analysis': {
                    'summary_text': analysis.summary_text,
                    'detailed_analysis': analysis.detailed_analysis
                }
            }
            export_data['analyses'].append(analysis_data)

        json_content = json.dumps(export_data, indent=2, default=str)
        return json_content.encode('utf-8')

    def _export_charts_to_image(self, analyses: List[Analysis]) -> bytes:
        """Export charts as PNG image"""

        # Create a figure with multiple subplots
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
        fig.suptitle('Financial Analysis Dashboard', fontsize=20, fontweight='bold')

        # Prepare data
        dates = [a.created_at for a in analyses]
        health_scores = [a.financial_health_score or 0 for a in analyses]
        incomes = [a.total_income or 0 for a in analyses]
        expenses = [a.total_expenses or 0 for a in analyses]

        # Chart 1: Financial Health Score Trend
        ax1.plot(dates, health_scores, marker='o', linewidth=2, markersize=6)
        ax1.set_title('Financial Health Score Trend', fontsize=14, fontweight='bold')
        ax1.set_ylabel('Health Score')
        ax1.grid(True, alpha=0.3)
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        ax1.tick_params(axis='x', rotation=45)

        # Chart 2: Income vs Expenses
        width = 0.35
        x = range(len(analyses))
        ax2.bar([i - width/2 for i in x], incomes, width, label='Income', alpha=0.8)
        ax2.bar([i + width/2 for i in x], expenses, width, label='Expenses', alpha=0.8)
        ax2.set_title('Income vs Expenses Comparison', fontsize=14, fontweight='bold')
        ax2.set_ylabel('Amount ($)')
        ax2.set_xlabel('Analysis')
        ax2.legend()
        ax2.grid(True, alpha=0.3)

        # Chart 3: Net Cash Flow
        net_flows = [inc - exp for inc, exp in zip(incomes, expenses)]
        colors_flow = ['green' if nf >= 0 else 'red' for nf in net_flows]
        ax3.bar(x, net_flows, color=colors_flow, alpha=0.7)
        ax3.set_title('Net Cash Flow by Analysis', fontsize=14, fontweight='bold')
        ax3.set_ylabel('Net Cash Flow ($)')
        ax3.set_xlabel('Analysis')
        ax3.axhline(y=0, color='black', linestyle='-', alpha=0.3)
        ax3.grid(True, alpha=0.3)

        # Chart 4: Analysis Type Distribution
        analysis_types = [a.analysis_type or 'Unknown' for a in analyses]
        type_counts = pd.Series(analysis_types).value_counts()
        ax4.pie(type_counts.values, labels=type_counts.index, autopct='%1.1f%%', startangle=90)
        ax4.set_title('Analysis Type Distribution', fontsize=14, fontweight='bold')

        plt.tight_layout()

        # Save to buffer
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', dpi=300, bbox_inches='tight')
        buffer.seek(0)
        plt.close()

        return buffer.getvalue()

    def _generate_summary_chart(self, analyses: List[Analysis]) -> Optional[Image]:
        """Generate a summary chart for PDF inclusion"""

        try:
            # Create a simple chart
            fig, ax = plt.subplots(figsize=(8, 4))

            dates = [a.created_at for a in analyses]
            health_scores = [a.financial_health_score or 0 for a in analyses]

            ax.plot(dates, health_scores, marker='o', linewidth=2)
            ax.set_title('Financial Health Score Trend')
            ax.set_ylabel('Health Score')
            ax.grid(True, alpha=0.3)


            buffer = io.BytesIO()
            plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
            buffer.seek(0)
            plt.close()

            # Create ReportLab Image
            img = Image(buffer, width=6*inch, height=3*inch)

            return img

        except Exception as e:
            self.log_error(e, "_generate_summary_chart")
            return None

    def _parse_json_field(self, json_field: str) -> Any:
        """Parse JSON field safely"""
        if not json_field:
            return None
        try:
            return json.loads(json_field)
        except (json.JSONDecodeError, TypeError):
            return None


export_service = ExportService()