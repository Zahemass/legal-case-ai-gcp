import React, { useState } from 'react';
import { getDocumentPreview } from '../../services/api';
import './DocumentPreview.css';

export default function DocumentPreview({ document }) {
  const [showPreview, setShowPreview] = useState(false);
  const [previewContent, setPreviewContent] = useState('');
  const [loading, setLoading] = useState(false);

  const handlePreview = async () => {
    if (showPreview) {
      setShowPreview(false);
      return;
    }

    try {
      setLoading(true);
      const content = await getDocumentPreview(document.id);
      setPreviewContent(content);
      setShowPreview(true);
    } catch (error) {
      console.error('Error loading preview:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <button 
        className="btn-secondary" 
        onClick={handlePreview}
        disabled={loading}
      >
        {loading ? 'Loading...' : showPreview ? 'Hide Preview' : 'Preview'}
      </button>

      {showPreview && (
        <div className="preview-modal">
          <div className="preview-content">
            <div className="preview-header">
              <h3>Document Preview: {document.filename}</h3>
              <button onClick={() => setShowPreview(false)}>×</button>
            </div>
            <div className="preview-body">
              <pre>{previewContent}</pre>
            </div>
          </div>
        </div>
      )}
    </>
  );
}