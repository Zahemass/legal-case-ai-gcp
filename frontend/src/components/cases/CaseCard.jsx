import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { runCaseAnalysis } from '../../services/api';
import './CaseCard.css';

export default function CaseCard({ caseData, onUpdate }) {
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const navigate = useNavigate();

  const handleRunAnalysis = async () => {
    try {
      if (!caseData?.id) return console.error('Missing case ID');
      setIsAnalyzing(true);
      await runCaseAnalysis(caseData.id);
      onUpdate();
    } catch (error) {
      console.error('Error running analysis:', error);
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleUploadDocs = () => {
    if (caseData?.id) navigate(`/documents?caseId=${caseData.id}`);
  };

  const handleAIAgent = () => {
    if (caseData?.id) navigate(`/ai-agent/${caseData.id}`);
  };

  return (
    <div className="case-card">
      <div className="case-header">
        <h3>{caseData?.title || 'Untitled Case'}</h3>
        <span className="case-date">
          Created:{' '}
          {caseData?.createdAt
            ? new Date(caseData.createdAt).toLocaleDateString()
            : 'Unknown date'}
        </span>
      </div>

      <div className="case-stats">
        <div className="stat">
          <span className="stat-label">Documents:</span>
          <span className="stat-value">{caseData?.documentCount ?? 0}</span>
        </div>
        <div className="stat">
          <span className="stat-label">Status:</span>
          <span className={`stat-value status-${caseData?.status || 'active'}`}>
            {caseData?.status || 'Active'}
          </span>
        </div>
      </div>

      <div className="case-actions">
        <button className="btn-secondary" onClick={handleUploadDocs}>
          Upload Documents
        </button>
        <button
          className="btn-primary"
          onClick={handleRunAnalysis}
          disabled={isAnalyzing}
        >
          {isAnalyzing ? 'Analyzing...' : 'Run AI Analysis'}
        </button>
        <button className="btn-accent" onClick={handleAIAgent}>
          AI Agent
        </button>
      </div>
    </div>
  );
}
