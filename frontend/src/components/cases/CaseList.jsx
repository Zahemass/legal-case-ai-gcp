import React from 'react';
import CaseCard from './CaseCard';
import './CaseList.css';

export default function CaseList({ cases, onCaseUpdate, onRefresh }) {
  const safeCases = Array.isArray(cases) ? cases : [];

  if (safeCases.length === 0) {
    return (
      <div className="empty-state">
        <div className="empty-state-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
        </div>
        <h3>No cases yet</h3>
        <p>Create your first case to start managing your legal documents and analyses</p>
      </div>
    );
  }

  return (
    <div className="case-list">
      {safeCases.map((case_, index) => (
        <CaseCard
          key={case_.id || `case-${index}`}
          caseData={case_}
          onUpdate={onCaseUpdate}
          onRefresh={onRefresh} // ✅ Added here
          index={index}
        />
      ))}
    </div>
  );
}
