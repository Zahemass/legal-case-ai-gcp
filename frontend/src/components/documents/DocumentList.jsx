// frontend/src/components/documents/DocumentList.jsx
import React, { useState } from 'react';
import DocumentPreview from './DocumentPreview';
import DocumentAnalysis from './DocumentAnalysis';
import './DocumentList.css';

export default function DocumentList({ documents, onDocumentUpdate }) {
  const [sortBy, setSortBy] = useState('date'); // 'date', 'name', 'pages'
  const [viewMode, setViewMode] = useState('grid'); // 'grid', 'list'
  
  // ✅ Always normalize documents to an array
  const safeDocuments = Array.isArray(documents) ? documents : [];

  // Sort documents
  const sortedDocuments = [...safeDocuments].sort((a, b) => {
    switch (sortBy) {
      case 'name':
        return (a.filename || '').localeCompare(b.filename || '');
      case 'pages':
        return (b.pageCount || 0) - (a.pageCount || 0);
      case 'date':
      default:
        const dateA = a.uploadedAt instanceof Date ? a.uploadedAt : new Date(a.uploadedAt?.seconds ? a.uploadedAt.seconds * 1000 : a.uploadedAt || 0);
        const dateB = b.uploadedAt instanceof Date ? b.uploadedAt : new Date(b.uploadedAt?.seconds ? b.uploadedAt.seconds * 1000 : b.uploadedAt || 0);
        return dateB - dateA;
    }
  });

  // ✅ Handle loading or empty states gracefully
  if (!safeDocuments || safeDocuments.length === 0) {
    return (
      <div className="document-list-container">
        <div className="empty-state">
          <div className="empty-icon">📁</div>
          <h3>No Documents Yet</h3>
          <p>Upload your legal documents to get started with AI-powered analysis</p>
          <div className="empty-features">
            <div className="feature-item">
              <span className="feature-icon">🤖</span>
              <span>AI Analysis</span>
            </div>
            <div className="feature-item">
              <span className="feature-icon">📊</span>
              <span>Smart Insights</span>
            </div>
            <div className="feature-item">
              <span className="feature-icon">⚖️</span>
              <span>Legal Review</span>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="document-list-container">
      {/* Header with Controls */}
      <div className="list-header">
        <div className="header-left">
          <h2 className="list-title">
            <span className="title-icon">📚</span>
            Document Library
          </h2>
          <div className="document-count">
            {safeDocuments.length} {safeDocuments.length === 1 ? 'Document' : 'Documents'}
          </div>
        </div>
        
        <div className="header-controls">
          {/* Sort Dropdown */}
          <div className="control-group">
            <label htmlFor="sort-select">
              <span className="control-icon">🔽</span>
              Sort by:
            </label>
            <select 
              id="sort-select"
              className="sort-select"
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
            >
              <option value="date">Upload Date</option>
              <option value="name">Name</option>
              <option value="pages">Page Count</option>
            </select>
          </div>

          {/* View Mode Toggle */}
          <div className="view-toggle">
            <button
              className={`view-btn ${viewMode === 'grid' ? 'active' : ''}`}
              onClick={() => setViewMode('grid')}
              aria-label="Grid view"
              title="Grid view"
            >
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <rect x="3" y="3" width="7" height="7"></rect>
                <rect x="14" y="3" width="7" height="7"></rect>
                <rect x="14" y="14" width="7" height="7"></rect>
                <rect x="3" y="14" width="7" height="7"></rect>
              </svg>
            </button>
            <button
              className={`view-btn ${viewMode === 'list' ? 'active' : ''}`}
              onClick={() => setViewMode('list')}
              aria-label="List view"
              title="List view"
            >
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <line x1="8" y1="6" x2="21" y2="6"></line>
                <line x1="8" y1="12" x2="21" y2="12"></line>
                <line x1="8" y1="18" x2="21" y2="18"></line>
                <line x1="3" y1="6" x2="3.01" y2="6"></line>
                <line x1="3" y1="12" x2="3.01" y2="12"></line>
                <line x1="3" y1="18" x2="3.01" y2="18"></line>
              </svg>
            </button>
          </div>
        </div>
      </div>

      {/* Documents Grid/List */}
      <div className={`documents-container ${viewMode}-view`}>
        {sortedDocuments.map((doc, index) => {
          const uploadedAt =
            doc.uploadedAt instanceof Date
              ? doc.uploadedAt
              : new Date(
                  doc.uploadedAt?.seconds
                    ? doc.uploadedAt.seconds * 1000
                    : doc.uploadedAt || Date.now()
                );

          return (
            <div 
              key={doc.id || Math.random()} 
              className="document-card"
              style={{ animationDelay: `${index * 0.05}s` }}
            >
              {/* Document Icon/Type Badge */}
              <div className="document-visual">
                <div className="doc-icon-large">
                  📄
                </div>
                <div className="doc-type-badge">
                  {doc.contentType?.includes('pdf') ? 'PDF' : 'DOC'}
                </div>
              </div>

              {/* Document Info */}
              <div className="document-content">
                <div className="document-header">
                  <h3 className="document-title" title={doc.filename}>
                    {doc.filename || 'Untitled Document'}
                  </h3>
                  <div className="document-meta">
                    <div className="meta-item">
                      <span className="meta-icon">📅</span>
                      <span className="meta-text">
                        {uploadedAt.toLocaleDateString('en-US', { 
                          month: 'short', 
                          day: 'numeric',
                          year: 'numeric'
                        })}
                      </span>
                    </div>
                    <div className="meta-item">
                      <span className="meta-icon">⏰</span>
                      <span className="meta-text">
                        {uploadedAt.toLocaleTimeString('en-US', { 
                          hour: '2-digit', 
                          minute: '2-digit'
                        })}
                      </span>
                    </div>
                    {doc.pageCount && (
                      <div className="meta-item">
                        <span className="meta-icon">📊</span>
                        <span className="meta-text">
                          {doc.pageCount} {doc.pageCount === 1 ? 'page' : 'pages'}
                        </span>
                      </div>
                    )}
                  </div>
                </div>

                {/* Additional Info (List View Only) */}
                {viewMode === 'list' && (
                  <div className="document-details">
                    {doc.size && (
                      <span className="detail-badge">
                        <span className="badge-icon">💾</span>
                        {(doc.size / 1024).toFixed(2)} KB
                      </span>
                    )}
                    {doc.analyzed && (
                      <span className="detail-badge analyzed">
                        <span className="badge-icon">✅</span>
                        Analyzed
                      </span>
                    )}
                  </div>
                )}

                {/* Actions */}
                <div className="document-actions">
                  <DocumentPreview document={doc} />
                  <DocumentAnalysis
                    document={doc}
                    onAnalysisComplete={onDocumentUpdate}
                  />
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}