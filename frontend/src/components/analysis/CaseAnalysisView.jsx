// frontend/src/components/analysis/CaseAnalysisView.jsx
import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { getCaseAnalysis } from '../../services/api';
import AnalysisExport from './AnalysisExport';
import './CaseAnalysisView.css';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

export default function CaseAnalysisView() {
  const { caseId } = useParams();
  const [analysis, setAnalysis] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('summary');

  useEffect(() => {
    const fetchAnalysis = async () => {
      try {
        const result = await getCaseAnalysis(caseId);
        setAnalysis(result);
      } catch (error) {
        console.error('❌ Error fetching case analysis:', error);
      } finally {
        setLoading(false);
      }
    };
    fetchAnalysis();
  }, [caseId]);

  if (loading) {
    return (
      <div className="loading-container">
        <div className="spinner"></div>
        <p className="loading-text">🔍 Running AI Analysis...</p>
      </div>
    );
  }

  if (!analysis) {
    return (
      <div className="error-container">
        <div className="error-icon">⚠️</div>
        <p className="error-text">No analysis found for this case.</p>
      </div>
    );
  }

  const formatDate = (timestamp) => {
    if (!timestamp) return 'N/A';
    const date = timestamp.toDate ? timestamp.toDate() : new Date(timestamp);
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const getRiskLevelColor = (level) => {
    const colors = {
      High: '#dc3545',
      Medium: '#ffc107',
      Low: '#28a745'
    };
    return colors[level] || '#6c757d';
  };

  return (
    <div className="analysis-view-container">
      {/* Header Section */}
      <header className="analysis-header">
        <div className="header-content">
          <h1 className="analysis-title">AI Case Analysis Report</h1>
          <div className="header-meta">
            <span className="case-id">
              <strong>Case ID:</strong> {analysis.caseId}
            </span>
            <span className="analysis-type">
              <strong>Type:</strong> {analysis.analysisType}
            </span>
            <span className="analyzed-date">
              <strong>Analyzed:</strong> {formatDate(analysis.analyzedAt)}
            </span>
          </div>
        </div>
        <div className="header-actions">
          <AnalysisExport caseId={caseId} />
        </div>
      </header>

      {/* Confidence & Stats Bar */}
      <div className="stats-bar">
        <div className="stat-card">
          <div className="stat-label">Confidence Score</div>
          <div className="stat-value">
            {(analysis.confidence * 100).toFixed(1)}%
          </div>
          <div className="confidence-progress">
            <div
              className="confidence-bar"
              style={{ width: `${analysis.confidence * 100}%` }}
            ></div>
          </div>
        </div>

        {analysis.documentAnalysis && (
          <>
            <div className="stat-card">
              <div className="stat-label">Documents Analyzed</div>
              <div className="stat-value">{analysis.documentCount || 0}</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Processing Time</div>
              <div className="stat-value">
                {(analysis.processingTime / 1000).toFixed(2)}s
              </div>
            </div>
          </>
        )}

        {analysis.riskAssessment?.overallRiskLevel && (
          <div className="stat-card">
            <div className="stat-label">Overall Risk</div>
            <div
              className="stat-value risk-badge"
              style={{
                color: getRiskLevelColor(analysis.riskAssessment.overallRiskLevel)
              }}
            >
              {analysis.riskAssessment.overallRiskLevel}
            </div>
          </div>
        )}
      </div>

      {/* Tab Navigation */}
      <nav className="tab-navigation">
        <button
          className={`tab-btn ${activeTab === 'summary' ? 'active' : ''}`}
          onClick={() => setActiveTab('summary')}
        >
          📘 Summary
        </button>
        <button
          className={`tab-btn ${activeTab === 'findings' ? 'active' : ''}`}
          onClick={() => setActiveTab('findings')}
        >
          📎 Findings
        </button>
        
        <button
          className={`tab-btn ${activeTab === 'risk' ? 'active' : ''}`}
          onClick={() => setActiveTab('risk')}
        >
          📊 Risk Assessment
        </button>
        <button
          className={`tab-btn ${activeTab === 'strategy' ? 'active' : ''}`}
          onClick={() => setActiveTab('strategy')}
        >
          🧭 Strategy
        </button>
      </nav>

      {/* Content Sections */}
      <div className="analysis-content">
        {/* Executive Summary Tab */}
        {activeTab === 'summary' && (
          <section className="content-section fade-in">
            <h2 className="section-title">📘 Executive Summary</h2>
            <div className="summary-box">
              <div className="summary-text">
  <ReactMarkdown remarkPlugins={[remarkGfm]}>
    {analysis.executiveSummary}
  </ReactMarkdown>
</div>


            </div>

            {analysis.documentAnalysis && (
              <div className="document-stats">
                <h3 className="subsection-title">Document Analysis Overview</h3>
                <div className="stats-grid">
                  <div className="mini-stat">
                    <span className="mini-label">Total Documents</span>
                    <span className="mini-value">
                      {analysis.documentAnalysis.totalDocuments}
                    </span>
                  </div>
                  <div className="mini-stat">
                    <span className="mini-label">Avg Document Size</span>
                    <span className="mini-value">
                      {Math.round(analysis.documentAnalysis.averageDocumentSize)} chars
                    </span>
                  </div>
                  <div className="mini-stat">
                    <span className="mini-label">Documents with Text</span>
                    <span className="mini-value">
                      {analysis.documentAnalysis.documentsWithText}
                    </span>
                  </div>
                </div>

                {analysis.documentAnalysis.topDocuments && (
                  <div className="top-documents">
                    <h4>Top Analyzed Documents</h4>
                    <div className="document-list">
                      {analysis.documentAnalysis.topDocuments.map((doc, idx) => (
                        <div key={idx} className="document-item">
                          <div className="doc-icon">📄</div>
                          <div className="doc-info">
                            <div className="doc-name">{doc.filename}</div>
                            <div className="doc-meta">
                              Relevance: {(doc.relevanceScore * 100).toFixed(1)}% | 
                              Size: {doc.textLength} chars
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </section>
        )}

        {/* Key Findings Tab */}
        {activeTab === 'findings' && (
          <section className="content-section fade-in">
            <h2 className="section-title">📎 Key Findings</h2>
            <div className="findings-list">
  {analysis.keyFindings?.map((finding, i) => (
    <div key={i} className="finding-card">
      <div className="finding-number">{i + 1}</div>
      <div className="finding-content">
        <ReactMarkdown remarkPlugins={[remarkGfm]}>
          {finding}
        </ReactMarkdown>
      </div>
    </div>
  ))}
</div>


            {analysis.recommendations && analysis.recommendations.length > 0 && (
              <div className="recommendations-section">
                <h3 className="subsection-title">💡 Recommendations</h3>
                <div className="recommendations-list">
                  {analysis.recommendations.map((rec, i) => (
                    <div key={i} className="recommendation-card">
                      <div className="rec-header">
                        <span className="rec-number">{i + 1}</span>
                        <strong className="rec-action">{rec.action}</strong>
                      </div>
                      <p className="rec-rationale">{rec.rationale}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </section>
        )}

        {/* Legal Issues Tab */}
        {activeTab === 'legal' && (
          <section className="content-section fade-in">
            <h2 className="section-title">⚖️ Legal Issues</h2>
            {analysis.legalIssues && analysis.legalIssues.length > 0 ? (
              <div className="legal-issues-grid">
                {analysis.legalIssues.map((issue, i) => (
                  <div key={i} className="issue-card">
                    <div className="issue-header">
                      <h4 className="issue-title">{issue.title}</h4>
                      <span className={`severity-badge severity-${issue.severity?.toLowerCase()}`}>
                        {issue.severity}
                      </span>
                    </div>
                    <div className="issue-body">
                      <div className="issue-section">
                        <strong>Description:</strong>
                        <p>{issue.description}</p>
                      </div>
                      <div className="issue-section">
                        <strong>Implications:</strong>
                        <p>{issue.implications}</p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="empty-state">
                <p>No specific legal issues identified in the analysis.</p>
              </div>
            )}
          </section>
        )}

        {/* Risk Assessment Tab */}
        {activeTab === 'risk' && (
          <section className="content-section fade-in">
            <h2 className="section-title">📊 Risk Assessment</h2>

            {analysis.riskAssessment?.riskCategories && (
              <div className="risk-categories">
                {Object.entries(analysis.riskAssessment.riskCategories).map(
                  ([category, data]) => (
                    <div key={category} className="risk-category-card">
                      <div className="risk-category-header">
                        <h3>{category.charAt(0).toUpperCase() + category.slice(1)} Risk</h3>
                        <span
                          className="risk-level-badge"
                          style={{ backgroundColor: getRiskLevelColor(data.level) }}
                        >
                          {data.level}
                        </span>
                      </div>
                      {data.factors && data.factors.length > 0 && (
                        <ul className="risk-factors">
                          {data.factors.map((factor, idx) => (
                            <li key={idx}>{factor}</li>
                          ))}
                        </ul>
                      )}
                    </div>
                  )
                )}
              </div>
            )}

           {analysis.riskAssessment?.keyRiskFactors && (
  <div className="key-risk-factors">
    <h3 className="subsection-title">Key Risk Factors</h3>
    <div className="risk-factors-list">
      {analysis.riskAssessment.keyRiskFactors.map((factor, idx) => (
        <div key={idx} className="risk-factor-item">
          <span className="factor-icon">⚠️</span>

          {/* Render markdown here (wrap container holds styles) */}
          <div className="risk-factor-md">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {factor}
            </ReactMarkdown>
          </div>
        </div>
      ))}
    </div>
  </div>
)}


            {analysis.riskAssessment?.fullAssessment && (
  <details className="full-assessment-details">
    <summary>View Full Risk Assessment Report</summary>
    <div className="full-assessment-content">
      <div className="full-assessment-content">
  <ReactMarkdown remarkPlugins={[remarkGfm]}>
    {analysis.riskAssessment.fullAssessment}
  </ReactMarkdown>
</div>

    </div>
  </details>
)}

          </section>
        )}

        {/* Strategic Advice Tab */}
        {activeTab === 'strategy' && (
          <section className="content-section fade-in">
            <h2 className="section-title">🧭 Strategic Advice</h2>
            <div className="strategy-content">
              <div className="strategy-text">
  <ReactMarkdown remarkPlugins={[remarkGfm]}>
    {analysis.strategicAdvice}
  </ReactMarkdown>
</div>


              {analysis.riskAssessment?.strengthsWeaknesses && (
                <div className="swot-analysis">
                  <div className="swot-section strengths">
                    <h3>💪 Strengths</h3>
                    <ul>
                      {analysis.riskAssessment.strengthsWeaknesses.strengths?.map(
                        (item, idx) => (
                          <li key={idx}>{item}</li>
                        )
                      )}
                    </ul>
                  </div>
                  <div className="swot-section weaknesses">
                    <h3>⚠️ Weaknesses</h3>
                    <ul>
                      {analysis.riskAssessment.strengthsWeaknesses.weaknesses?.map(
                        (item, idx) => (
                          <li key={idx}>{item}</li>
                        )
                      )}
                    </ul>
                  </div>
                </div>
              )}
            </div>
          </section>
        )}
      </div>
    </div>
  );
}