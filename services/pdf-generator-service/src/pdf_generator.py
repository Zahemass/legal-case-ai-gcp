import logging
import os
import time
import tempfile
from typing import Dict, Any, Optional, List
from datetime import datetime
import json

from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from jinja2 import Template
import matplotlib.pyplot as plt
from google.cloud import firestore, storage

logger = logging.getLogger(__name__)

class PDFGenerator:
    """Service for generating PDF reports from case analysis"""
    
    def __init__(self, firestore_client, storage_client):
        self.firestore_client = firestore_client
        self.storage_client = storage_client
        self.storage_bucket = os.environ.get('STORAGE_BUCKET', 'legal-case-documents')
        
        # Initialize styles
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
        
        logger.info("✅ PDFGenerator initialized")

    def _setup_custom_styles(self):
        """Setup custom paragraph styles"""
        # Title style
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Title'],
            fontSize=18,
            spaceAfter=20,
            textColor=colors.darkblue,
            alignment=TA_CENTER
        ))
        
        # Section heading style
        self.styles.add(ParagraphStyle(
            name='SectionHeading',
            parent=self.styles['Heading2'],
            fontSize=14,
            spaceBefore=16,
            spaceAfter=10,
            textColor=colors.darkblue,
            borderWidth=1,
            borderColor=colors.lightgrey,
            borderPadding=5
        ))
        
        # Subsection heading style
        self.styles.add(ParagraphStyle(
            name='SubsectionHeading',
            parent=self.styles['Heading3'],
            fontSize=12,
            spaceBefore=12,
            spaceAfter=6,
            textColor=colors.darkgreen
        ))
        
        # Key points style
        self.styles.add(ParagraphStyle(
            name='KeyPoint',
            parent=self.styles['Normal'],
            leftIndent=20,
            bulletIndent=10,
            spaceBefore=3,
            spaceAfter=3
        ))

    def generate_report(self, case_id: str, report_type: str, user_id: str) -> Dict[str, Any]:
        """Generate PDF report for a case"""
        try:
            logger.info(f"📄 Generating {report_type} report for case {case_id}")
            start_time = time.time()
            
            # Get case data
            case_data = self._get_case_data(case_id)
            if not case_data:
                return {'success': False, 'error': 'Case not found'}
            
            # Verify user access
            if case_data.get('createdBy') != user_id:
                return {'success': False, 'error': 'Access denied'}
            
            # Generate PDF based on report type
            if report_type == 'case_analysis':
                pdf_path = self._generate_case_analysis_report(case_id, case_data)
            elif report_type == 'document_summary':
                pdf_path = self._generate_document_summary_report(case_id, case_data)
            elif report_type == 'timeline_report':
                pdf_path = self._generate_timeline_report(case_id, case_data)
            elif report_type == 'executive_summary':
                pdf_path = self._generate_executive_summary_report(case_id, case_data)
            else:
                return {'success': False, 'error': f'Unknown report type: {report_type}'}
            
            if not pdf_path:
                return {'success': False, 'error': 'PDF generation failed'}
            
            # Upload to Cloud Storage
            storage_key = f"reports/{case_id}/{report_type}_{int(time.time())}.pdf"
            upload_result = self._upload_to_storage(pdf_path, storage_key)
            
            if not upload_result:
                return {'success': False, 'error': 'Failed to upload PDF'}
            
            # Save report metadata to Firestore
            report_id = self._save_report_metadata(
                case_id, user_id, report_type, storage_key, 
                case_data.get('title', 'Unknown Case')
            )
            
            # Clean up temporary file
            try:
                os.unlink(pdf_path)
            except:
                pass
            
            processing_time = time.time() - start_time
            
            logger.info(f"✅ PDF report generated successfully in {processing_time:.2f}s")
            
            return {
                'success': True,
                'reportId': report_id,
                'reportType': report_type,
                'storageKey': storage_key,
                'processingTime': processing_time,
                'downloadUrl': f'/download/{report_id}'
            }
            
        except Exception as e:
            logger.error(f"❌ PDF generation error: {e}")
            return {'success': False, 'error': str(e)}

    def _generate_case_analysis_report(self, case_id: str, case_data: Dict[str, Any]) -> Optional[str]:
        """Generate comprehensive case analysis report"""
        try:
            # Create temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
                pdf_path = temp_file.name
            
            # Create PDF document
            doc = SimpleDocTemplate(pdf_path, pagesize=A4)
            story = []
            
            # Title page
            story.extend(self._create_title_page(case_data, 'Comprehensive Case Analysis Report'))
            story.append(PageBreak())
            
            # Table of contents
            story.extend(self._create_table_of_contents())
            story.append(PageBreak())
            
            # Executive summary
            story.extend(self._create_executive_summary_section(case_id))
            
            # Case overview
            story.extend(self._create_case_overview_section(case_data))
            
            # Document analysis
            story.extend(self._create_document_analysis_section(case_id))
            
            # Key findings
            story.extend(self._create_key_findings_section(case_id))
            
            # Legal analysis
            story.extend(self._create_legal_analysis_section(case_id))
            
            # Risk assessment
            story.extend(self._create_risk_assessment_section(case_id))
            
            # Recommendations
            story.extend(self._create_recommendations_section(case_id))
            
            # Timeline
            story.extend(self._create_timeline_section(case_id))
            
            # Appendices
            story.extend(self._create_appendices_section(case_id))
            
            # Build PDF
            doc.build(story)
            
            return pdf_path
            
        except Exception as e:
            logger.error(f"❌ Case analysis report generation error: {e}")
            return None

    def _generate_document_summary_report(self, case_id: str, case_data: Dict[str, Any]) -> Optional[str]:
        """Generate document summary report"""
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
                pdf_path = temp_file.name
            
            doc = SimpleDocTemplate(pdf_path, pagesize=A4)
            story = []
            
            # Title page
            story.extend(self._create_title_page(case_data, 'Document Summary Report'))
            story.append(PageBreak())
            
            # Document overview
            story.extend(self._create_document_overview_section(case_id))
            
            # Document details
            story.extend(self._create_document_details_section(case_id))
            
            # Document analysis summary
            story.extend(self._create_document_analysis_summary_section(case_id))
            
            # Build PDF
            doc.build(story)
            
            return pdf_path
            
        except Exception as e:
            logger.error(f"❌ Document summary report generation error: {e}")
            return None

    def _generate_timeline_report(self, case_id: str, case_data: Dict[str, Any]) -> Optional[str]:
        """Generate timeline report"""
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
                pdf_path = temp_file.name
            
            doc = SimpleDocTemplate(pdf_path, pagesize=A4)
            story = []
            
            # Title page
            story.extend(self._create_title_page(case_data, 'Case Timeline Report'))
            story.append(PageBreak())
            
            # Timeline overview
            story.extend(self._create_timeline_overview_section(case_id))
            
            # Detailed timeline
            story.extend(self._create_detailed_timeline_section(case_id))
            
            # Timeline analysis
            story.extend(self._create_timeline_analysis_section(case_id))
            
            # Build PDF
            doc.build(story)
            
            return pdf_path
            
        except Exception as e:
            logger.error(f"❌ Timeline report generation error: {e}")
            return None

    def _generate_executive_summary_report(self, case_id: str, case_data: Dict[str, Any]) -> Optional[str]:
        """Generate executive summary report"""
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
                pdf_path = temp_file.name
            
            doc = SimpleDocTemplate(pdf_path, pagesize=A4)
            story = []
            
            # Title page
            story.extend(self._create_title_page(case_data, 'Executive Summary Report'))
            story.append(PageBreak())
            
            # Executive summary
            story.extend(self._create_executive_summary_section(case_id))
            
            # Key highlights
            story.extend(self._create_key_highlights_section(case_id))
            
            # Quick stats
            story.extend(self._create_quick_stats_section(case_id, case_data))
            
            # Build PDF
            doc.build(story)
            
            return pdf_path
            
        except Exception as e:
            logger.error(f"❌ Executive summary report generation error: {e}")
            return None

    # Section creation methods
    def _create_title_page(self, case_data: Dict[str, Any], report_title: str) -> List:
        """Create title page elements"""
        elements = []
        
        # Logo/Header space
        elements.append(Spacer(1, 1*inch))
        
        # Report title
        elements.append(Paragraph(report_title, self.styles['CustomTitle']))
        elements.append(Spacer(1, 0.5*inch))
        
        # Case information
        case_title = case_data.get('title', 'Unknown Case')
        case_type = case_data.get('type', 'General')
        created_date = case_data.get('createdAt', 'Unknown')
        
        case_info = f"""
        <b>Case:</b> {case_title}<br/>
        <b>Type:</b> {case_type}<br/>
        <b>Created:</b> {created_date}<br/>
        <b>Report Generated:</b> {datetime.now().strftime('%B %d, %Y at %I:%M %p')}
        """
        
        elements.append(Paragraph(case_info, self.styles['Normal']))
        elements.append(Spacer(1, 1*inch))
        
        # Disclaimer
        disclaimer = """
        <b>CONFIDENTIAL LEGAL DOCUMENT</b><br/><br/>
        This report contains confidential and privileged information prepared for legal analysis purposes. 
        Distribution is restricted to authorized parties only. This analysis is based on available 
        information and should be reviewed by qualified legal counsel.
        """
        
        elements.append(Paragraph(disclaimer, self.styles['Normal']))
        
        return elements

    def _create_table_of_contents(self) -> List:
        """Create table of contents"""
        elements = []
        
        elements.append(Paragraph("Table of Contents", self.styles['SectionHeading']))
        elements.append(Spacer(1, 0.2*inch))
        
        toc_items = [
            "1. Executive Summary .......................... 3",
            "2. Case Overview .............................. 4", 
            "3. Document Analysis .......................... 5",
            "4. Key Findings ............................... 6",
            "5. Legal Analysis ............................. 7",
            "6. Risk Assessment ............................ 8",
            "7. Recommendations ............................ 9",
            "8. Timeline ................................... 10",
            "9. Appendices ................................. 11"
        ]
        
        for item in toc_items:
            elements.append(Paragraph(item, self.styles['Normal']))
            elements.append(Spacer(1, 0.1*inch))
        
        return elements

    def _create_executive_summary_section(self, case_id: str) -> List:
        """Create executive summary section"""
        elements = []
        
        elements.append(Paragraph("1. Executive Summary", self.styles['SectionHeading']))
        
        # Get case analysis data
        analysis_data = self._get_case_analysis_data(case_id)
        
        if analysis_data:
            summary = analysis_data.get('executiveSummary', 'Executive summary not available.')
            elements.append(Paragraph(summary, self.styles['Normal']))
        else:
            elements.append(Paragraph("Case analysis not yet completed. Executive summary will be available after comprehensive analysis is performed.", self.styles['Normal']))
        
        elements.append(Spacer(1, 0.3*inch))
        
        return elements

    def _create_case_overview_section(self, case_data: Dict[str, Any]) -> List:
        """Create case overview section"""
        elements = []
        
        elements.append(Paragraph("2. Case Overview", self.styles['SectionHeading']))
        
        # Case details table
        case_details = [
            ['Field', 'Value'],
            ['Case Title', case_data.get('title', 'Unknown')],
            ['Case Type', case_data.get('type', 'General')],
            ['Status', case_data.get('status', 'Active')],
            ['Priority', case_data.get('priority', 'Medium')],
            ['Created Date', case_data.get('createdAt', 'Unknown')],
            ['Last Updated', case_data.get('updatedAt', 'Unknown')],
            ['Document Count', str(case_data.get('documentCount', 0))]
        ]
        
        table = Table(case_details, colWidths=[2*inch, 4*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('BACKGROUND', (0, 1), (0, -1), colors.lightgrey),
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 0.2*inch))
        
        # Case description
        if case_data.get('description'):
            elements.append(Paragraph("Case Description", self.styles['SubsectionHeading']))
            elements.append(Paragraph(case_data['description'], self.styles['Normal']))
        
        elements.append(Spacer(1, 0.3*inch))
        
        return elements

    def _create_document_analysis_section(self, case_id: str) -> List:
        """Create document analysis section"""
        elements = []
        
        elements.append(Paragraph("3. Document Analysis", self.styles['SectionHeading']))
        
        # Get document statistics
        doc_stats = self._get_document_statistics(case_id)
        
        if doc_stats:
            elements.append(Paragraph("Document Statistics", self.styles['SubsectionHeading']))
            elements.append(Paragraph(doc_stats, self.styles['Normal']))
            elements.append(Spacer(1, 0.2*inch))
        
        # Get document list
        documents = self._get_case_documents(case_id)
        if documents:
            elements.append(Paragraph("Document Inventory", self.styles['SubsectionHeading']))
            
            doc_table_data = [['Document Name', 'Type', 'Size', 'Status', 'Upload Date']]
            
            for doc in documents[:20]:  # Limit to 20 documents
                size_mb = round(doc.get('size', 0) / (1024*1024), 2)
                doc_table_data.append([
                    doc.get('filename', 'Unknown')[:30],
                    doc.get('contentType', 'Unknown').split('/')[-1],
                    f"{size_mb} MB",
                    doc.get('extractionStatus', 'Unknown'),
                    doc.get('uploadedAt', 'Unknown')[:10]
                ])
            
            doc_table = Table(doc_table_data, colWidths=[2*inch, 0.8*inch, 0.8*inch, 1*inch, 1*inch])
            doc_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            elements.append(doc_table)
        
        elements.append(Spacer(1, 0.3*inch))
        
        return elements

    def _create_key_findings_section(self, case_id: str) -> List:
        """Create key findings section"""
        elements = []
        
        elements.append(Paragraph("4. Key Findings", self.styles['SectionHeading']))
        
        # Get key findings from analysis
        analysis_data = self._get_case_analysis_data(case_id)
        
        if analysis_data and analysis_data.get('keyFindings'):
            findings = analysis_data['keyFindings']
            
            for i, finding in enumerate(findings[:10], 1):  # Limit to 10 findings
                elements.append(Paragraph(f"{i}. {finding}", self.styles['KeyPoint']))
                elements.append(Spacer(1, 0.1*inch))
        else:
            elements.append(Paragraph("Key findings will be available after case analysis is completed.", self.styles['Normal']))
        
        elements.append(Spacer(1, 0.3*inch))
        
        return elements

    def _create_legal_analysis_section(self, case_id: str) -> List:
        """Create legal analysis section"""
        elements = []
        
        elements.append(Paragraph("5. Legal Analysis", self.styles['SectionHeading']))
        
        analysis_data = self._get_case_analysis_data(case_id)
        
        if analysis_data:
            # Legal issues
            legal_issues = analysis_data.get('legalIssues', [])
            if legal_issues:
                elements.append(Paragraph("Legal Issues Identified", self.styles['SubsectionHeading']))
                
                for issue in legal_issues[:5]:  # Limit to 5 issues
                    issue_title = issue.get('title', 'Legal Issue')
                    issue_desc = issue.get('description', 'No description available')
                    severity = issue.get('severity', 'Medium')
                    
                    issue_text = f"<b>{issue_title}</b> (Severity: {severity})<br/>{issue_desc}"
                    elements.append(Paragraph(issue_text, self.styles['Normal']))
                    elements.append(Spacer(1, 0.1*inch))
            
            # Strengths and weaknesses
            strengths_weaknesses = analysis_data.get('strengthsWeaknesses', {})
            if strengths_weaknesses:
                elements.append(Paragraph("Case Strengths and Weaknesses", self.styles['SubsectionHeading']))
                
                strengths = strengths_weaknesses.get('strengths', [])
                if strengths:
                    elements.append(Paragraph("<b>Strengths:</b>", self.styles['Normal']))
                    for strength in strengths[:5]:
                        elements.append(Paragraph(f"• {strength}", self.styles['KeyPoint']))
                
                weaknesses = strengths_weaknesses.get('weaknesses', [])
                if weaknesses:
                    elements.append(Paragraph("<b>Weaknesses:</b>", self.styles['Normal']))
                    for weakness in weaknesses[:5]:
                        elements.append(Paragraph(f"• {weakness}", self.styles['KeyPoint']))
        else:
            elements.append(Paragraph("Legal analysis will be available after case analysis is completed.", self.styles['Normal']))
        
        elements.append(Spacer(1, 0.3*inch))
        
        return elements

    def _create_risk_assessment_section(self, case_id: str) -> List:
        """Create risk assessment section"""
        elements = []
        
        elements.append(Paragraph("6. Risk Assessment", self.styles['SectionHeading']))
        
        analysis_data = self._get_case_analysis_data(case_id)
        
        if analysis_data and analysis_data.get('riskAssessment'):
            risk_data = analysis_data['riskAssessment']
            
            # Overall risk level
            overall_risk = risk_data.get('overallRiskLevel', 'Unknown')
            elements.append(Paragraph(f"<b>Overall Risk Level:</b> {overall_risk}", self.styles['Normal']))
            elements.append(Spacer(1, 0.1*inch))
            
            # Key risk factors
            risk_factors = risk_data.get('keyRiskFactors', [])
            if risk_factors:
                elements.append(Paragraph("Key Risk Factors", self.styles['SubsectionHeading']))
                for risk in risk_factors[:8]:
                    elements.append(Paragraph(f"• {risk}", self.styles['KeyPoint']))
            
            # Mitigation strategies
            mitigation = risk_data.get('mitigationStrategies', [])
            if mitigation:
                elements.append(Paragraph("Mitigation Strategies", self.styles['SubsectionHeading']))
                for strategy in mitigation[:5]:
                    elements.append(Paragraph(f"• {strategy}", self.styles['KeyPoint']))
        else:
            elements.append(Paragraph("Risk assessment will be available after case analysis is completed.", self.styles['Normal']))
        
        elements.append(Spacer(1, 0.3*inch))
        
        return elements

    def _create_recommendations_section(self, case_id: str) -> List:
        """Create recommendations section"""
        elements = []
        
        elements.append(Paragraph("7. Recommendations", self.styles['SectionHeading']))
        
        analysis_data = self._get_case_analysis_data(case_id)
        
        if analysis_data and analysis_data.get('recommendations'):
            recommendations = analysis_data['recommendations']
            
            for i, rec in enumerate(recommendations[:8], 1):
                action = rec.get('action', 'Recommended action')
                priority = rec.get('priority', 'Medium')
                timeline = rec.get('timeline', 'TBD')
                
                rec_text = f"<b>{i}. {action}</b><br/>Priority: {priority} | Timeline: {timeline}"
                elements.append(Paragraph(rec_text, self.styles['Normal']))
                elements.append(Spacer(1, 0.1*inch))
        else:
            elements.append(Paragraph("Recommendations will be available after case analysis is completed.", self.styles['Normal']))
        
        elements.append(Spacer(1, 0.3*inch))
        
        return elements

    def _create_timeline_section(self, case_id: str) -> List:
        """Create timeline section"""
        elements = []
        
        elements.append(Paragraph("8. Case Timeline", self.styles['SectionHeading']))
        
        analysis_data = self._get_case_analysis_data(case_id)
        
        if analysis_data and analysis_data.get('timeline'):
            timeline_events = analysis_data['timeline']
            
            if timeline_events:
                timeline_data = [['Date', 'Event', 'Significance']]
                
                for event in timeline_events[:15]:  # Limit to 15 events
                    timeline_data.append([
                        event.get('date', 'Unknown')[:10],
                        event.get('event', 'Event')[:40],
                        event.get('significance', 'N/A')[:30]
                    ])
                
                timeline_table = Table(timeline_data, colWidths=[1*inch, 2.5*inch, 2.5*inch])
                timeline_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 0), (-1, -1), 9),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))
                
                elements.append(timeline_table)
            else:
                elements.append(Paragraph("No timeline events identified in current analysis.", self.styles['Normal']))
        else:
            elements.append(Paragraph("Timeline will be available after case analysis is completed.", self.styles['Normal']))
        
        elements.append(Spacer(1, 0.3*inch))
        
        return elements

    def _create_appendices_section(self, case_id: str) -> List:
        """Create appendices section"""
        elements = []
        
        elements.append(Paragraph("9. Appendices", self.styles['SectionHeading']))
        
        # Appendix A: Document List
        elements.append(Paragraph("Appendix A: Complete Document List", self.styles['SubsectionHeading']))
        
        documents = self._get_case_documents(case_id)
        if documents:
            for i, doc in enumerate(documents, 1):
                doc_info = f"{i}. {doc.get('filename', 'Unknown')} ({doc.get('contentType', 'Unknown')})"
                elements.append(Paragraph(doc_info, self.styles['Normal']))
        else:
            elements.append(Paragraph("No documents available.", self.styles['Normal']))
        
        elements.append(Spacer(1, 0.2*inch))
        
        # Appendix B: Analysis Metadata
        elements.append(Paragraph("Appendix B: Analysis Metadata", self.styles['SubsectionHeading']))
        
        analysis_data = self._get_case_analysis_data(case_id)
        if analysis_data:
            metadata = analysis_data.get('metadata', {})
            confidence = analysis_data.get('confidence', 0)
            processing_time = analysis_data.get('processingTime', 0)
            analyzed_at = analysis_data.get('analyzedAt', 'Unknown')
            
            metadata_text = f"""
            Analysis Confidence: {confidence:.1%}<br/>
            Processing Time: {processing_time:.2f} seconds<br/>
            Analysis Date: {analyzed_at}<br/>
            Analysis Type: {analysis_data.get('analysisType', 'Unknown')}
            """
            
            elements.append(Paragraph(metadata_text, self.styles['Normal']))
        else:
            elements.append(Paragraph("Analysis metadata not available.", self.styles['Normal']))
        
        return elements

    # Document-specific sections
    def _create_document_overview_section(self, case_id: str) -> List:
        """Create document overview section"""
        elements = []
        
        elements.append(Paragraph("Document Overview", self.styles['SectionHeading']))
        
        doc_stats = self._get_document_statistics(case_id)
        elements.append(Paragraph(doc_stats, self.styles['Normal']))
        elements.append(Spacer(1, 0.3*inch))
        
        return elements

    def _create_document_details_section(self, case_id: str) -> List:
        """Create detailed document information section"""
        elements = []
        
        elements.append(Paragraph("Document Details", self.styles['SectionHeading']))
        
        documents = self._get_case_documents(case_id)
        
        for doc in documents[:10]:  # Limit to 10 documents for detail
            elements.append(Paragraph(f"<b>{doc.get('filename', 'Unknown')}</b>", self.styles['SubsectionHeading']))
            
            doc_details = f"""
            Type: {doc.get('contentType', 'Unknown')}<br/>
            Size: {round(doc.get('size', 0) / (1024*1024), 2)} MB<br/>
            Upload Date: {doc.get('uploadedAt', 'Unknown')}<br/>
            Extraction Status: {doc.get('extractionStatus', 'Unknown')}<br/>
            Analysis Status: {doc.get('analysisStatus', 'Unknown')}
            """
            
            elements.append(Paragraph(doc_details, self.styles['Normal']))
            elements.append(Spacer(1, 0.2*inch))
        
        return elements

    def _create_document_analysis_summary_section(self, case_id: str) -> List:
        """Create document analysis summary section"""
        elements = []
        
        elements.append(Paragraph("Document Analysis Summary", self.styles['SectionHeading']))
        
        # Get document analysis results
        doc_analyses = self._get_document_analyses(case_id)
        
        if doc_analyses:
            for analysis in doc_analyses[:5]:  # Limit to 5 analyses
                filename = analysis.get('filename', 'Unknown Document')
                summary = analysis.get('summary', 'No summary available')
                
                elements.append(Paragraph(f"<b>{filename}</b>", self.styles['SubsectionHeading']))
                elements.append(Paragraph(summary, self.styles['Normal']))
                elements.append(Spacer(1, 0.2*inch))
        else:
            elements.append(Paragraph("Document analyses not yet available.", self.styles['Normal']))
        
        return elements

    # Timeline-specific sections
    def _create_timeline_overview_section(self, case_id: str) -> List:
        """Create timeline overview section"""
        elements = []
        
        elements.append(Paragraph("Timeline Overview", self.styles['SectionHeading']))
        
        analysis_data = self._get_case_analysis_data(case_id)
        timeline_events = analysis_data.get('timeline', []) if analysis_data else []
        
        if timeline_events:
            overview_text = f"""
            This timeline contains {len(timeline_events)} key events identified from case documents and analysis.
            Events are presented in chronological order with their significance to the case.
            """
            elements.append(Paragraph(overview_text, self.styles['Normal']))
        else:
            elements.append(Paragraph("Timeline data is not yet available. Please run case analysis to generate timeline information.", self.styles['Normal']))
        
        elements.append(Spacer(1, 0.3*inch))
        
        return elements

    def _create_detailed_timeline_section(self, case_id: str) -> List:
        """Create detailed timeline section"""
        elements = []
        
        elements.append(Paragraph("Detailed Timeline", self.styles['SectionHeading']))
        
        analysis_data = self._get_case_analysis_data(case_id)
        timeline_events = analysis_data.get('timeline', []) if analysis_data else []
        
        if timeline_events:
            for i, event in enumerate(timeline_events, 1):
                event_date = event.get('date', 'Unknown Date')
                event_desc = event.get('event', 'Event description not available')
                event_significance = event.get('significance', 'Significance not specified')
                
                event_text = f"""
                <b>{i}. {event_date}</b><br/>
                <b>Event:</b> {event_desc}<br/>
                <b>Significance:</b> {event_significance}
                """
                
                elements.append(Paragraph(event_text, self.styles['Normal']))
                elements.append(Spacer(1, 0.2*inch))
        else:
            elements.append(Paragraph("No timeline events available.", self.styles['Normal']))
        
        return elements

    def _create_timeline_analysis_section(self, case_id: str) -> List:
        """Create timeline analysis section"""
        elements = []
        
        elements.append(Paragraph("Timeline Analysis", self.styles['SectionHeading']))
        
        analysis_data = self._get_case_analysis_data(case_id)
        
        if analysis_data and analysis_data.get('timeline'):
            timeline_events = analysis_data['timeline']
            
            analysis_text = f"""
            The case timeline spans {len(timeline_events)} documented events. Key patterns and 
            considerations identified from the chronological analysis include critical dates, 
            event sequences, and potential statute of limitations considerations.
            
            Legal practitioners should pay particular attention to events marked with high 
            significance ratings and ensure all procedural deadlines are properly tracked.
            """
            
            elements.append(Paragraph(analysis_text, self.styles['Normal']))
        else:
            elements.append(Paragraph("Timeline analysis not available.", self.styles['Normal']))
        
        return elements

    # Executive summary specific sections
    def _create_key_highlights_section(self, case_id: str) -> List:
        """Create key highlights section for executive summary"""
        elements = []
        
        elements.append(Paragraph("Key Highlights", self.styles['SectionHeading']))
        
        analysis_data = self._get_case_analysis_data(case_id)
        
        if analysis_data:
            # Top 5 key findings
            key_findings = analysis_data.get('keyFindings', [])[:5]
            if key_findings:
                elements.append(Paragraph("Top Findings", self.styles['SubsectionHeading']))
                for finding in key_findings:
                    elements.append(Paragraph(f"• {finding}", self.styles['KeyPoint']))
            
            # Critical risks
            risk_assessment = analysis_data.get('riskAssessment', {})
            if risk_assessment:
                overall_risk = risk_assessment.get('overallRiskLevel', 'Unknown')
                elements.append(Paragraph(f"Risk Level: {overall_risk}", self.styles['SubsectionHeading']))
            
            # Top recommendations
            recommendations = analysis_data.get('recommendations', [])[:3]
            if recommendations:
                elements.append(Paragraph("Priority Actions", self.styles['SubsectionHeading']))
                for rec in recommendations:
                    action = rec.get('action', 'Action')
                    priority = rec.get('priority', 'Medium')
                    elements.append(Paragraph(f"• {action} (Priority: {priority})", self.styles['KeyPoint']))
        else:
            elements.append(Paragraph("Key highlights will be available after case analysis.", self.styles['Normal']))
        
        return elements

    def _create_quick_stats_section(self, case_id: str, case_data: Dict[str, Any]) -> List:
        """Create quick statistics section"""
        elements = []
        
        elements.append(Paragraph("Quick Statistics", self.styles['SectionHeading']))
        
        # Basic case stats
        stats_data = [
            ['Metric', 'Value'],
            ['Documents', str(case_data.get('documentCount', 0))],
            ['Analysis Count', str(case_data.get('analysisCount', 0))],
            ['Case Age', self._calculate_case_age(case_data.get('createdAt', ''))],
            ['Last Updated', case_data.get('updatedAt', 'Unknown')[:10]],
            ['Status', case_data.get('status', 'Unknown')],
            ['Priority', case_data.get('priority', 'Unknown')]
        ]
        
        stats_table = Table(stats_data, colWidths=[2*inch, 2*inch])
        stats_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        elements.append(stats_table)
        
        return elements

    # Helper methods
    def _get_case_data(self, case_id: str) -> Optional[Dict[str, Any]]:
        """Get case data from Firestore"""
        try:
            case_ref = self.firestore_client.collection('cases').document(case_id)
            case_doc = case_ref.get()
            return case_doc.to_dict() if case_doc.exists else None
        except Exception as e:
            logger.error(f"Error getting case data: {e}")
            return None

    def _get_case_analysis_data(self, case_id: str) -> Optional[Dict[str, Any]]:
        """Get the most recent case analysis data"""
        try:
            analysis_query = self.firestore_client.collection('case_analysis')\
                .where('caseId', '==', case_id)\
                .order_by('analyzedAt', direction=firestore.Query.DESCENDING)\
                .limit(1)
            
            docs = analysis_query.get()
            return docs[0].to_dict() if docs else None
        except Exception as e:
            logger.error(f"Error getting case analysis: {e}")
            return None

    def _get_case_documents(self, case_id: str) -> List[Dict[str, Any]]:
        """Get all case documents"""
        try:
            docs_query = self.firestore_client.collection('documents')\
                .where('caseId', '==', case_id)\
                .where('status', '!=', 'deleted')
            
            documents = []
            for doc in docs_query.get():
                doc_data = doc.to_dict()
                doc_data['id'] = doc.id
                documents.append(doc_data)
            
            return documents
        except Exception as e:
            logger.error(f"Error getting documents: {e}")
            return []

    def _get_document_statistics(self, case_id: str) -> str:
        """Get document statistics as formatted text"""
        try:
            documents = self._get_case_documents(case_id)
            
            if not documents:
                return "No documents found in this case."
            
            total_docs = len(documents)
            total_size = sum(doc.get('size', 0) for doc in documents)
            size_mb = round(total_size / (1024*1024), 2)
            
            # Document type breakdown
            doc_types = {}
            extraction_status = {'completed': 0, 'pending': 0, 'error': 0}
            
            for doc in documents:
                content_type = doc.get('contentType', 'unknown')
                doc_type = content_type.split('/')[0] if '/' in content_type else content_type
                doc_types[doc_type] = doc_types.get(doc_type, 0) + 1
                
                status = doc.get('extractionStatus', 'pending')
                if status in extraction_status:
                    extraction_status[status] += 1
            
            stats_text = f"""
            Total Documents: {total_docs}
            Total Size: {size_mb} MB
            Average Size: {round(size_mb / total_docs, 2)} MB per document
            
            Document Types:
            {chr(10).join([f'  • {doc_type}: {count}' for doc_type, count in doc_types.items()])}
            
            Extraction Status:
            • Completed: {extraction_status['completed']}
            • Pending: {extraction_status['pending']}
            • Error: {extraction_status['error']}
            """
            
            return stats_text.strip()
        except Exception as e:
            logger.error(f"Error getting document statistics: {e}")
            return "Document statistics unavailable."

    def _get_document_analyses(self, case_id: str) -> List[Dict[str, Any]]:
        """Get document analysis results"""
        try:
            analyses_query = self.firestore_client.collection('document_analysis')\
                .where('caseId', '==', case_id)\
                .limit(10)
            
            analyses = []
            for doc in analyses_query.get():
                analysis_data = doc.to_dict()
                analyses.append(analysis_data)
            
            return analyses
        except Exception as e:
            logger.error(f"Error getting document analyses: {e}")
            return []

    def _calculate_case_age(self, created_at: str) -> str:
        """Calculate case age in human readable format"""
        try:
            if not created_at:
                return "Unknown"
            
            # This is a simplified calculation
            # You might need to parse the date format used in your system
            from datetime import datetime
            
            # Assuming ISO format, adjust as needed
            created_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            now = datetime.now()
            
            diff = now - created_date
            days = diff.days
            
            if days < 1:
                return "Less than 1 day"
            elif days < 30:
                return f"{days} days"
            elif days < 365:
                months = days // 30
                return f"{months} months"
            else:
                years = days // 365
                return f"{years} years"
                
        except Exception as e:
            logger.error(f"Error calculating case age: {e}")
            return "Unknown"

    def _upload_to_storage(self, file_path: str, storage_key: str) -> bool:
        """Upload PDF to Cloud Storage"""
        try:
            bucket = self.storage_client.bucket(self.storage_bucket)
            blob = bucket.blob(storage_key)
            
            blob.upload_from_filename(file_path)
            
            logger.info(f"✅ PDF uploaded to storage: {storage_key}")
            return True
        except Exception as e:
            logger.error(f"❌ Storage upload error: {e}")
            return False

    def _save_report_metadata(self, case_id: str, user_id: str, report_type: str, 
                             storage_key: str, case_title: str) -> str:
        """Save report metadata to Firestore"""
        try:
            report_data = {
                'caseId': case_id,
                'userId': user_id,
                'reportType': report_type,
                'storageKey': storage_key,
                'filename': f"{case_title}_{report_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                'generatedAt': firestore.SERVER_TIMESTAMP,
                'status': 'completed'
            }
            
            doc_ref = self.firestore_client.collection('pdf_reports').add(report_data)
            
            logger.info(f"✅ Report metadata saved: {doc_ref[1].id}")
            return doc_ref[1].id
        except Exception as e:
            logger.error(f"❌ Error saving report metadata: {e}")
            return f"error_{int(time.time())}"