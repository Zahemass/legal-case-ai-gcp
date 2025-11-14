// src/pages/AIAnalysisDetailsPage.jsx
import React, { useEffect, useState } from "react";
import { doc, getDoc } from "firebase/firestore";
import { db } from "../firebase";
import { useParams, useNavigate } from "react-router-dom";
import MarkdownIt from "markdown-it";
import { 
  Scale,
  ArrowLeft,
  Calendar,
  FileText,
  AlertTriangle,
  CheckCircle,
  TrendingUp,
  Target,
  Clock,
  BarChart3,
  Shield,
  Lightbulb,
  Archive,
  Award,
  Zap,
  Download,
  Share2
} from "lucide-react";
import "./AIAnalysisDetailsPage.css";

// Initialize MarkdownIt
const md = new MarkdownIt({
  html: true,
  linkify: true,
  typographer: true,
  breaks: true
});

export default function AIAnalysisDetailsPage() {
  const { analysisId } = useParams();
  const navigate = useNavigate();
  const [analysis, setAnalysis] = useState(null);
  const [caseData, setCaseData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        setLoading(true);
        const ref = doc(db, "case_analyses", analysisId);
        const snap = await getDoc(ref);

        if (snap.exists()) {
          const analysisData = snap.data();
          setAnalysis(analysisData);

          // Fetch case details if caseId exists
          if (analysisData.caseId) {
            const caseRef = doc(db, "cases", analysisData.caseId);
            const caseSnap = await getDoc(caseRef);
            if (caseSnap.exists()) {
              setCaseData(caseSnap.data());
            }
          }
        }
      } catch (error) {
        console.error("Error loading analysis:", error);
      } finally {
        setLoading(false);
      }
    };

    load();
  }, [analysisId]);

  // Render markdown content
  const renderMarkdown = (content) => {
    if (!content) return "";
    return { __html: md.render(content) };
  };

  const getConfidenceColor = (confidence) => {
    if (!confidence) return "#94A3B8";
    const value = parseFloat(confidence);
    if (value >= 90) return "#059669";
    if (value >= 70) return "#D97706";
    return "#DC2626";
  };

  const getPriorityColor = (priority) => {
    const colors = {
      high: "#DC2626",
      medium: "#D97706",
      low: "#059669",
      critical: "#7C2D12"
    };
    return colors[priority?.toLowerCase()] || "#64748B";
  };

  const getPriorityIcon = (priority) => {
    switch(priority?.toLowerCase()) {
      case 'high':
      case 'critical':
        return <AlertTriangle size={16} />;
      case 'medium':
        return <TrendingUp size={16} />;
      case 'low':
        return <CheckCircle size={16} />;
      default:
        return <Target size={16} />;
    }
  };

  const handleDownload = () => {
    // Create a formatted text version for download
    let content = `AI CASE ANALYSIS REPORT\n`;
    content += `========================\n\n`;
    content += `Case: ${caseData?.title || "Unknown Case"}\n`;
    content += `Analysis Date: ${analysis.analyzedAt ? new Date(analysis.analyzedAt).toLocaleDateString() : "Unknown"}\n\n`;
    content += `EXECUTIVE SUMMARY\n-----------------\n${analysis.executiveSummary}\n\n`;
    
    if (analysis.keyFindings?.length) {
      content += `KEY FINDINGS\n------------\n`;
      analysis.keyFindings.forEach((f, i) => {
        content += `${i + 1}. ${f}\n`;
      });
      content += '\n';
    }

    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `analysis-${analysisId}.txt`;
    a.click();
  };

  if (loading) {
    return (
      <div className="details-loading">
        <div className="loader-large"></div>
        <p className="loading-text">Loading analysis details...</p>
      </div>
    );
  }

  if (!analysis) {
    return (
      <div className="details-error">
        <AlertTriangle size={64} color="#DC2626" />
        <h2>Analysis Not Found</h2>
        <p>The requested analysis could not be loaded.</p>
        <button onClick={() => navigate("/analysis")} className="back-button">
          Return to Analyses
        </button>
      </div>
    );
  }

  return (
    <div className="details-page-container">
      {/* Top Navigation */}
      <div className="top-nav">
        <div className="nav-content">
          <div className="logo-section">
            <div className="logo-icon">
              <Scale size={24} strokeWidth={2.5} />
            </div>
            <span className="logo-text">LegalAI</span>
          </div>

          {/* Action Buttons */}
          <div className="nav-actions">
            <button className="action-btn" onClick={handleDownload}>
              <Download size={18} />
              <span>Download</span>
            </button>
            <button className="action-btn">
              <Share2 size={18} />
              <span>Share</span>
            </button>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="details-content">
        {/* Back Button */}
        <button onClick={() => navigate("/analysis")} className="back-nav">
          <ArrowLeft size={20} />
          <span>Back to All Analyses</span>
        </button>

        {/* Header Section */}
        <div className="details-header">
          <div className="header-left">
            <div className="analysis-icon">
              <Scale size={32} />
            </div>
            <div>
              <h1 className="details-title">
                {caseData?.title || "Case Analysis"}
              </h1>
              <div className="header-meta">
                <span className="meta-badge">
                  {analysis.analysisType || "Full Analysis"}
                </span>
                <span className="meta-separator">•</span>
                <div className="meta-item">
                  <Calendar size={16} />
                 
                </div>
              </div>
            </div>
          </div>

          {/* Confidence Score */}
          {analysis.confidence && (
            <div className="confidence-card">
              <div className="confidence-icon">
                <Award size={24} />
              </div>
              <div>
                <p className="confidence-label">Confidence Score</p>
                <p 
                  className="confidence-value"
                  style={{ color: getConfidenceColor(analysis.confidence) }}
                >
                  {(analysis.confidence * 100).toFixed(2)}%
                </p>
              </div>
            </div>
          )}
        </div>

        {/* Quick Stats */}
        <div className="quick-stats">
          <div className="quick-stat-item">
            <FileText size={20} />
            <div>
              <p className="stat-value">{analysis.totalDocuments || analysis.documentCount || 0}</p>
              <p className="stat-label">Documents</p>
            </div>
          </div>

          <div className="quick-stat-item">
            <Archive size={20} />
            <div>
              <p className="stat-value">{(analysis.totalTextLength || 0).toLocaleString()}</p>
              <p className="stat-label">Total Characters</p>
            </div>
          </div>

          <div className="quick-stat-item">
            <Clock size={20} />
            <div>
              <p className="stat-value">{analysis.processingTime || "N/A"}</p>
              <p className="stat-label">Processing Time</p>
            </div>
          </div>

          <div className="quick-stat-item">
            <Zap size={20} />
            <div>
              <p className="stat-value">{analysis.keyFindings?.length || 0}</p>
              <p className="stat-label">Key Findings</p>
            </div>
          </div>
        </div>

        {/* Executive Summary with Markdown */}
        <div className="content-section featured">
          <div className="section-header">
            <div className="section-icon" style={{background: '#EEF2FF'}}>
              <BarChart3 size={22} color="#4F46E5" />
            </div>
            <h2 className="section-title">Executive Summary</h2>
          </div>
          <div className="section-content">
            <div 
              className="markdown-content summary-text"
              dangerouslySetInnerHTML={renderMarkdown(analysis.executiveSummary || "No summary available.")}
            />
          </div>
        </div>

        {/* Key Findings */}
        {analysis.keyFindings && analysis.keyFindings.length > 0 && (
          <div className="content-section">
            <div className="section-header">
              <div className="section-icon" style={{background: '#FEF3C7'}}>
                <CheckCircle size={22} color="#D97706" />
              </div>
              <h2 className="section-title">Key Findings</h2>
            </div>
            <div className="section-content">
              <ul className="findings-list">
                {analysis.keyFindings.map((finding, i) => (
                  <li key={i} className="finding-item">
                    <div className="finding-marker">{i + 1}</div>
                    <div 
                      className="markdown-content"
                      dangerouslySetInnerHTML={renderMarkdown(finding)}
                    />
                  </li>
                ))}
              </ul>
            </div>
          </div>
        )}

        {/* Top Documents */}
        {analysis.topDocuments && analysis.topDocuments.length > 0 && (
          <div className="content-section">
            <div className="section-header">
              <div className="section-icon" style={{background: '#DBEAFE'}}>
                <FileText size={22} color="#2563EB" />
              </div>
              <h2 className="section-title">Top Documents</h2>
            </div>
            <div className="section-content">
              <div className="documents-grid">
                {analysis.topDocuments.map((doc, i) => (
                  <div key={i} className="document-card">
                    <div className="doc-header">
                      <FileText size={18} />
                      <span className="doc-rank">#{i + 1}</span>
                    </div>
                    <h4 className="doc-filename">{doc.filename}</h4>
                    <div className="doc-stats">
                      <div className="doc-stat">
                        <span className="doc-stat-label">Text Length</span>
                        <span className="doc-stat-value">{doc.textLength?.toLocaleString()}</span>
                      </div>
                      <div className="doc-stat">
                        <span className="doc-stat-label">Relevance</span>
                        <span className="doc-stat-value">{doc.relevanceScore}</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Recommendations */}
        {analysis.recommendations && analysis.recommendations.length > 0 && (
          <div className="content-section">
            <div className="section-header">
              <div className="section-icon" style={{background: '#DCFCE7'}}>
                <Target size={22} color="#059669" />
              </div>
              <h2 className="section-title">Recommendations</h2>
            </div>
            <div className="section-content">
              <div className="recommendations-list">
                {analysis.recommendations.map((rec, i) => (
                  <div key={i} className="recommendation-card">
                    <div className="rec-header">
                      <div 
                        className="rec-priority"
                        style={{ 
                          background: `${getPriorityColor(rec.priority)}15`,
                          color: getPriorityColor(rec.priority)
                        }}
                      >
                        {getPriorityIcon(rec.priority)}
                        <span>{rec.priority?.toUpperCase()}</span>
                      </div>
                      {rec.timeline && (
                        <div className="rec-timeline">
                          <Clock size={14} />
                          <span>{rec.timeline}</span>
                        </div>
                      )}
                    </div>
                    <h4 className="rec-action">{rec.action}</h4>
                    {rec.details && (
                      <div 
                        className="markdown-content rec-details"
                        dangerouslySetInnerHTML={renderMarkdown(rec.details)}
                      />
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Risk Assessment */}
        {analysis.riskAssessment && (
          <div className="content-section alert">
            <div className="section-header">
              <div className="section-icon" style={{background: '#FEE2E2'}}>
                <Shield size={22} color="#DC2626" />
              </div>
              <h2 className="section-title">Risk Assessment</h2>
            </div>
            <div className="section-content">
              <div 
                className="markdown-content risk-text"
                dangerouslySetInnerHTML={renderMarkdown(
                  analysis.riskAssessment.fullAssessment || analysis.riskAssessment
                )}
              />
            </div>
          </div>
        )}

        {/* Strategic Advice */}
        {analysis.strategicAdvice && (
          <div className="content-section">
            <div className="section-header">
              <div className="section-icon" style={{background: '#F3E8FF'}}>
                <Lightbulb size={22} color="#7C3AED" />
              </div>
              <h2 className="section-title">Strategic Legal Advice</h2>
            </div>
            <div className="section-content">
              <div 
                className="markdown-content advice-text"
                dangerouslySetInnerHTML={renderMarkdown(analysis.strategicAdvice)}
              />
            </div>
          </div>
        )}

        {/* Additional Metadata */}
        <div className="metadata-section">
          <h3 className="metadata-title">Analysis Metadata</h3>
          <div className="metadata-grid">
            <div className="metadata-item">
              <span className="metadata-label">Analysis ID</span>
              <span className="metadata-value">{analysisId}</span>
            </div>
            {analysis.caseId && (
              <div className="metadata-item">
                <span className="metadata-label">Case ID</span>
                <span className="metadata-value">{analysis.caseId}</span>
              </div>
            )}
            <div className="metadata-item">
              <span className="metadata-label">Document Count</span>
              <span className="metadata-value">{analysis.documentCount || 0}</span>
            </div>
            <div className="metadata-item">
              <span className="metadata-label">Total Text Length</span>
              <span className="metadata-value">{analysis.totalTextLength?.toLocaleString() || 0}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
