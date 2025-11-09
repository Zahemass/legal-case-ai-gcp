import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Container } from 'react-bootstrap';
import DocumentList from '../components/documents/DocumentList';
import DocumentUpload from '../components/documents/DocumentUpload';
import { getDocuments, getCases } from '../services/api';
import { useAuth } from '../contexts/AuthContext';
import './DocumentsPage.css';

export default function DocumentsPage() {
  const [documents, setDocuments] = useState([]);
  const [cases, setCases] = useState([]);
  const [selectedCaseId, setSelectedCaseId] = useState('');
  const [loading, setLoading] = useState(true);
  const [searchParams] = useSearchParams();
  const { currentUser } = useAuth();

  useEffect(() => {
    loadData();
    const caseId = searchParams.get('caseId');
    if (caseId) {
      setSelectedCaseId(caseId);
    }
  }, []);

  useEffect(() => {
    if (selectedCaseId) {
      loadDocuments();
    }
  }, [selectedCaseId]);

  const loadData = async () => {
    try {
      const casesData = await getCases(currentUser.uid);
      setCases(casesData);
    } catch (error) {
      console.error('Error loading data:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadDocuments = async () => {
  if (!selectedCaseId) return;
  try {
    const docs = await getDocuments(selectedCaseId);
    setDocuments(Array.isArray(docs) ? docs : []);
  } catch (error) {
    console.error('Error loading documents:', error);
  }
};


  const handleDocumentUploaded = (newDoc) => {
    setDocuments([...documents, newDoc]);
  };

  return (
    <div className="documents-page">
      <div className="page-header">
        <Container>
          <div className="d-flex justify-content-between align-items-center flex-wrap">
            <h1>Document Management</h1>
            <div className="case-selector">
              <label>Select Case:</label>
              <select 
                value={selectedCaseId} 
                onChange={(e) => setSelectedCaseId(e.target.value)}
              >
                <option value="">Choose a case...</option>
                {Array.isArray(cases) && cases.map((caseItem) => (
  <option key={caseItem.id} value={caseItem.id}>
    {caseItem.title || caseItem.name || 'Untitled Case'}
  </option>
))}


              </select>
            </div>
          </div>
        </Container>
      </div>

      <Container>
        {selectedCaseId ? (
          <>
            <DocumentUpload 
              caseId={selectedCaseId}
              onDocumentUploaded={handleDocumentUploaded}
            />
            <DocumentList 
              documents={documents}
              onDocumentUpdate={loadDocuments}
            />
          </>
        ) : (
          <div className="no-case-selected">
            <div className="empty-icon">📁</div>
            <h3>Select a Case</h3>
            <p>Choose a case from the dropdown above to manage its documents</p>
          </div>
        )}
      </Container>
    </div>
  );
}