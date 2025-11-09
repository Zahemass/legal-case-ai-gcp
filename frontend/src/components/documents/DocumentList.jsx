// frontend/src/components/documents/DocumentList.jsx
import React from 'react';
import DocumentPreview from './DocumentPreview';
import DocumentAnalysis from './DocumentAnalysis';
import './DocumentAnalysis.css';

export default function DocumentList({ documents, onDocumentUpdate }) {
  // ✅ Always normalize documents to an array
  const safeDocuments = Array.isArray(documents) ? documents : [];

  // ✅ Handle loading or empty states gracefully
  if (!safeDocuments || safeDocuments.length === 0) {
    return (
      <div className="empty-state">
        <h3>No documents uploaded</h3>
        <p>Upload documents to get started with analysis</p>
      </div>
    );
  }

  return (
    <div className="document-list">
      <h2>Uploaded Documents</h2>

      <div className="documents-grid">
        {safeDocuments.map((doc) => {
          const uploadedAt =
            doc.uploadedAt instanceof Date
              ? doc.uploadedAt
              : new Date(
                  doc.uploadedAt?.seconds
                    ? doc.uploadedAt.seconds * 1000
                    : doc.uploadedAt || Date.now()
                );

          return (
            <div key={doc.id || Math.random()} className="document-card">
              <div className="document-info">
                <h3>{doc.filename || 'Untitled Document'}</h3>
                <p>
                  Uploaded: {uploadedAt.toLocaleDateString()} at{' '}
                  {uploadedAt.toLocaleTimeString()}
                </p>
                <p>Pages: {doc.pageCount || 'N/A'}</p>
              </div>

              <div className="document-actions">
                <DocumentPreview document={doc} />
                <DocumentAnalysis
                  document={doc}
                  onAnalysisComplete={onDocumentUpdate}
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
