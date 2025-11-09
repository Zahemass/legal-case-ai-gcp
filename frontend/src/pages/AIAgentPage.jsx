import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { Container } from 'react-bootstrap';
import AIAgentChat from '../components/chat/AIAgentChat';
import { getCaseById } from '../services/api';
import './AIAgentPage.css';

export default function AIAgentPage() {
  const { caseId } = useParams();
  const [caseData, setCaseData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadCase();
  }, [caseId]);

  const loadCase = async () => {
    try {
      const case_ = await getCaseById(caseId);
      setCaseData(case_);
    } catch (error) {
      console.error('Error loading case:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="loading">Loading case data...</div>;
  }

  if (!caseData) {
    return <div className="error">Case not found</div>;
  }

  return (
    <div className="ai-agent-page">
      <div className="page-header">
        <Container>
          <h1>AI Agent - {caseData.title}</h1>
          <p>Ask questions about your case and get AI-powered insights</p>
        </Container>
      </div>

      <Container>
        <AIAgentChat caseId={caseId} />
      </Container>
    </div>
  );
}