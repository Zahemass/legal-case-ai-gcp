import React from 'react';
import CaseCard from './CaseCard';
import './CaseList.css';

export default function CaseList({ cases, onCaseUpdate }) {
  const safeCases = Array.isArray(cases) ? cases : [];

  if (safeCases.length === 0) {
    return (
      <div className="empty-state">
        <h3>No cases found</h3>
        <p>Create your first case to get started</p>
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
        />
      ))}
    </div>
  );
}
