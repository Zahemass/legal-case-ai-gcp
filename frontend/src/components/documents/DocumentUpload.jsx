import React, { useState } from 'react';
import { uploadDocument } from '../../services/api';
import { useAuth } from '../../contexts/AuthContext';
import './DocumentUpload.css';

export default function DocumentUpload({ caseId, onDocumentUploaded }) {
  const [dragActive, setDragActive] = useState(false);
  const [uploading, setUploading] = useState(false);
  const { currentUser } = useAuth();

  const handleFiles = async (files) => {
    if (!files.length) return;

    setUploading(true);
    try {
      // Upload all selected files in parallel
      const uploadPromises = Array.from(files).map(file =>
        uploadDocument(file, caseId, currentUser.uid)
      );

      const uploadResults = await Promise.all(uploadPromises);

      // Safely extract and handle uploaded document data
      uploadResults.forEach(result => {
        if (result?.data?.documents && Array.isArray(result.data.documents)) {
          result.data.documents.forEach(doc => onDocumentUploaded(doc));
        } else {
          console.warn('⚠️ Unexpected upload response format:', result);
        }
      });

      console.log('✅ Documents uploaded:', uploadResults);
    } catch (error) {
      console.error('❌ Error uploading documents:', error);
    } finally {
      setUploading(false);
    }
  };

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    const files = e.dataTransfer.files;
    handleFiles(files);
  };

  const handleChange = (e) => {
    const files = e.target.files;
    handleFiles(files);
  };

  return (
    <div className="upload-section">
      <div
        className={`upload-area ${dragActive ? 'drag-active' : ''}`}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
      >
        <input
          id="file-upload"
          type="file"
          multiple
          onChange={handleChange}
          accept=".pdf,.doc,.docx,.txt"
        />
        <label htmlFor="file-upload">
          {uploading ? (
            <div className="uploading">
              <div className="spinner"></div>
              <p>Uploading documents...</p>
            </div>
          ) : (
            <>
              <div className="upload-icon">📄</div>
              <p>Drag and drop files here or click to browse</p>
              <p className="upload-hint">Supports PDF, DOC, DOCX, TXT files</p>
            </>
          )}
        </label>
      </div>
    </div>
  );
}
