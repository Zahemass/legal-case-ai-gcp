import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { runCaseAnalysis } from '../../services/api';
import './CaseCard.css';

export default function CaseCard({ caseData, onUpdate, onRefresh, index }) {
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const navigate = useNavigate();

  const handleRunAnalysis = async () => {
    try {
      if (!caseData?.id) return console.error('Missing case ID');
      setIsAnalyzing(true);

      const result = await runCaseAnalysis(caseData.id);
      console.log('✅ Analysis started:', result);

      // Navigate to analysis view
      navigate(`/analysis/${caseData.id}`);
    } catch (error) {
      console.error('Error running analysis:', error);
    } finally {
      setIsAnalyzing(false);
    }
  };

  /**
   * 📄 Handle "Upload Docs" button
   * Navigates to the document page for that case.
   * After upload, we auto-refresh the case list.
   */
  const handleUploadDocs = () => {
    if (caseData?.id) {
      navigate(`/documents?caseId=${caseData.id}`);

      // 🔄 Trigger refresh after returning from upload page
      // If onRefresh exists (passed from CasesPage), call it
      if (typeof onRefresh === 'function') {
        setTimeout(() => {
          console.log('🔄 Refreshing case list after document upload...');
          onRefresh();
        }, 1500); // slight delay for upload processing
      }
    }
  };

  const handleAIAgent = () => {
    if (caseData?.id) navigate(`/ai-agent/${caseData.id}`);
  };

  const getPriorityColor = (priority) => {
    const colors = {
      high: '#ef4444',
      medium: '#f59e0b',
      low: '#10b981'
    };
    return colors[priority] || colors.medium;
  };

  const getTypeLabel = (type) => {
    const labels = {
      criminal: 'Criminal',
      civil: 'Civil',
      corporate: 'Corporate',
      family: 'Family',
      other: 'Other'
    };
    return labels[type] || 'General';
  };

  const formatDate = (date) => {
    if (!date) return 'Unknown';
    const parsed = new Date(date);
    if (isNaN(parsed)) return 'Unknown';
    return parsed.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric'
    });
  };

  return (
    <div className="case-card">
      <div className="case-card-header">
        <div className="case-header-top">
          <div
            className="case-type-badge"
            style={{
              background: `${getPriorityColor(caseData?.priority)}15`,
              color: getPriorityColor(caseData?.priority)
            }}
          >
            {getTypeLabel(caseData?.type)}
          </div>
          <div
            className="case-priority-dot"
            style={{ background: getPriorityColor(caseData?.priority) }}
            title={`${caseData?.priority || 'medium'} priority`}
          />
        </div>

        <h3 className="case-title">{caseData?.title || 'Untitled Case'}</h3>

        <div className="case-meta">
          <span className="case-date">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
              <line x1="16" y1="2" x2="16" y2="6" />
              <line x1="8" y1="2" x2="8" y2="6" />
              <line x1="3" y1="10" x2="21" y2="10" />
            </svg>
            {formatDate(caseData?.createdAt)}
          </span>
        </div>
      </div>

      <div className="case-stats-grid">
        <div className="stat-item">
          <div className="stat-icon" style={{ background: '#dbeafe', color: '#2563eb' }}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          </div>
          <div className="stat-content">
            <span className="stat-value">{caseData?.documentCount ?? 0}</span>
            <span className="stat-label">Documents</span>
          </div>
        </div>

        <div className="stat-item">
          <div className="stat-icon" style={{ background: '#f3e8ff', color: '#7c3aed' }}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
            </svg>
          </div>
          <div className="stat-content">
            <span className="stat-value">{caseData?.analysisCount ?? 0}</span>
            <span className="stat-label">Analyses</span>
          </div>
        </div>

        <div className="stat-item stat-item-full">
          <div className="stat-icon" style={{ background: '#dcfce7', color: '#16a34a' }}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <div className="stat-content">
            <span className={`stat-badge status-${caseData?.status || 'active'}`}>
              {caseData?.status || 'Active'}
            </span>
            <span className="stat-label">Case Status</span>
          </div>
        </div>
      </div>

      {/* ✅ Fix: prevent Invalid Date display */}
      {caseData?.lastAnalyzedAt && !isNaN(new Date(caseData.lastAnalyzedAt)) && (
        <div className="case-last-analysis">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="10" />
            <polyline points="12 6 12 12 16 14" />
          </svg>
          Last analyzed {formatDate(caseData.lastAnalyzedAt)}
        </div>
      )}

      <div className="case-actions">
        <button className="btn btn-secondary" onClick={handleUploadDocs}>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
          </svg>
          Upload Docs
        </button>

        <button
          className="btn btn-primary"
          onClick={handleRunAnalysis}
          disabled={isAnalyzing}
        >
          {isAnalyzing ? (
            <>
              <span className="spinner" />
              Analyzing...
            </>
          ) : (
            <>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
              </svg>
              AI Analysis
            </>
          )}
        </button>

        <button className="btn btn-accent" onClick={handleAIAgent}>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
          </svg>
          AI Agent
        </button>
      </div>
    </div>
  );
}
