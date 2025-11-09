// frontend/src/components/documents/DocumentAnalysis.jsx
import React, { useState } from 'react';
import { analyzeDocument } from '../../services/api';
import './DocumentAnalysis.css';

export default function DocumentAnalysis({ document, onAnalysisComplete }) {
  const [analyzing, setAnalyzing] = useState(false);
  const [analysis, setAnalysis] = useState(null);
  const [showAnalysis, setShowAnalysis] = useState(false);
  const [activeTab, setActiveTab] = useState('summary');

  const handleAnalyze = async () => {
    try {
      setAnalyzing(true);
      const analysisResult = await analyzeDocument(document.id);
      setAnalysis(analysisResult);
      setShowAnalysis(true);
      onAnalysisComplete?.();
    } catch (error) {
      console.error('Error analyzing document:', error);
      alert('Failed to analyze document. Please try again.');
    } finally {
      setAnalyzing(false);
    }
  };

  const handleClose = () => {
    setShowAnalysis(false);
    setActiveTab('summary');
  };

  const tabs = [
    { id: 'summary', label: 'Summary', icon: '📋' },
    { id: 'keyPoints', label: 'Key Points', icon: '🔍' },
    { id: 'legal', label: 'Legal Analysis', icon: '⚖️' }
  ];

  return (
    <>
      <button 
        className="analyze-btn" 
        onClick={handleAnalyze}
        disabled={analyzing}
      >
        {analyzing ? (
          <>
            <span className="spinner"></span>
            <span>Analyzing...</span>
          </>
        ) : (
          <>
            <span className="icon">🤖</span>
            <span>AI Analysis</span>
          </>
        )}
      </button>

      {showAnalysis && analysis && (
        <div className="analysis-modal" onClick={handleClose}>
          <div className="analysis-container" onClick={(e) => e.stopPropagation()}>
            {/* Header */}
            <div className="analysis-header">
              <div className="header-content">
                <div className="header-icon">🤖</div>
                <div className="header-text">
                  <h2>AI Document Analysis</h2>
                  <p className="document-name">{document.filename}</p>
                </div>
              </div>
              <button className="close-btn" onClick={handleClose} aria-label="Close">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <line x1="18" y1="6" x2="6" y2="18"></line>
                  <line x1="6" y1="6" x2="18" y2="18"></line>
                </svg>
              </button>
            </div>

            {/* Tab Navigation */}
            <div className="tab-navigation">
              {tabs.map((tab) => (
                <button
                  key={tab.id}
                  className={`tab-btn ${activeTab === tab.id ? 'active' : ''}`}
                  onClick={() => setActiveTab(tab.id)}
                >
                  <span className="tab-icon">{tab.icon}</span>
                  <span className="tab-label">{tab.label}</span>
                </button>
              ))}
            </div>

            {/* Content Area */}
            <div className="analysis-body">
              <div className="tab-content">
                {/* Summary Tab */}
                {activeTab === 'summary' && (
                  <div className="content-section fade-in">
                    <div className="section-card">
                      <div className="card-header">
                        <span className="card-icon">📋</span>
                        <h3>Document Summary</h3>
                      </div>
                      <div className="card-body">
                        <p className="summary-text">{analysis.summary || 'No summary available.'}</p>
                      </div>
                      <div className="card-stats">
                        <div className="stat-item">
                          <span className="stat-icon">📄</span>
                          <div className="stat-content">
                            <span className="stat-label">Document Type</span>
                            <span className="stat-value">{document.contentType}</span>
                          </div>
                        </div>
                        <div className="stat-item">
                          <span className="stat-icon">⏱️</span>
                          <div className="stat-content">
                            <span className="stat-label">Analyzed</span>
                            <span className="stat-value">{new Date().toLocaleDateString()}</span>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                {/* Key Points Tab */}
                {activeTab === 'keyPoints' && (
                  <div className="content-section fade-in">
                    <div className="section-card">
                      <div className="card-header">
                        <span className="card-icon">🔍</span>
                        <h3>Key Points & Insights</h3>
                      </div>
                      <div className="card-body">
                        {analysis.keyPoints && analysis.keyPoints.length > 0 ? (
                          <div className="key-points-grid">
                            {analysis.keyPoints.map((point, index) => (
                              <div key={index} className="key-point-item">
                                <div className="point-number">{index + 1}</div>
                                <div className="point-content">
                                  <p>{point}</p>
                                </div>
                              </div>
                            ))}
                          </div>
                        ) : (
                          <div className="empty-state">
                            <span className="empty-icon">🔍</span>
                            <p>No key points identified</p>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                )}

                {/* Legal Analysis Tab */}
                {activeTab === 'legal' && (
                  <div className="content-section fade-in">
                    <div className="section-card">
                      <div className="card-header">
                        <span className="card-icon">⚖️</span>
                        <h3>Legal Relevance & Analysis</h3>
                      </div>
                      <div className="card-body">
                        {analysis.legalRelevance ? (
                          <>
                            <div className="legal-content">
                              <p>{analysis.legalRelevance}</p>
                            </div>
                            {analysis.entities && (
                              <div className="entities-section">
                                <h4>Identified Entities</h4>
                                <div className="entities-grid">
                                  {Object.entries(analysis.entities).map(([key, value]) => (
                                    <div key={key} className="entity-tag">
                                      <span className="entity-label">{key}:</span>
                                      <span className="entity-value">{value}</span>
                                    </div>
                                  ))}
                                </div>
                              </div>
                            )}
                          </>
                        ) : (
                          <div className="empty-state">
                            <span className="empty-icon">⚖️</span>
                            <p>No legal analysis available</p>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {/* Action Buttons */}
              <div className="action-bar">
                <button className="action-btn secondary" onClick={handleClose}>
                  <span>Close</span>
                </button>
                <button className="action-btn primary">
                  <span className="icon">📥</span>
                  <span>Export Analysis</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}