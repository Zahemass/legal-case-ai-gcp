import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { Container } from 'react-bootstrap';
import CaseList from '../components/cases/CaseList';
import CreateCaseDialog from '../components/cases/CreateCaseDialog';
import { getCases } from '../services/api';
import './CasesPage.css';

export default function CasesPage() {
  const [cases, setCases] = useState([]);
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [loading, setLoading] = useState(true);
  const { currentUser } = useAuth();

  useEffect(() => {
    loadCases();
  }, []);

  const loadCases = async () => {
    try {
      setLoading(true);
      const response = await getCases(currentUser.uid);

      // ✅ Handle backend shape: { success, data: { cases, pagination } }
      if (response.success && Array.isArray(response.data?.cases)) {
        setCases(response.data.cases);
      } else {
        console.warn('Unexpected response shape:', response);
        setCases([]);
      }
    } catch (error) {
      console.error('Error loading cases:', error);
      setCases([]);
    } finally {
      setLoading(false);
    }
  };

  const handleCaseCreated = (newCase) => {
    setCases((prev) => (Array.isArray(prev) ? [...prev, newCase] : [newCase]));
    setShowCreateDialog(false);
  };

  return (
    <div className="cases-page">
      <div className="page-header">
        <Container>
          <div className="d-flex justify-content-between align-items-center">
            <h1>Legal Cases</h1>
            <button 
              className="btn-primary" 
              onClick={() => setShowCreateDialog(true)}
            >
              New Case
            </button>
          </div>
        </Container>
      </div>

      <Container>
        {loading ? (
          <div className="loading">Loading cases...</div>
        ) : (
          <CaseList cases={cases} onCaseUpdate={loadCases} />
        )}
      </Container>

      {showCreateDialog && (
        <CreateCaseDialog
          onClose={() => setShowCreateDialog(false)}
          onCaseCreated={handleCaseCreated}
        />
      )}
    </div>
  );
}
