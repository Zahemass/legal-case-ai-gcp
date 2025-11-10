// frontend/src/components/analysis/AnalysisExport.jsx
import React from 'react';
import { exportAnalysisPDF } from '../../services/api';

export default function AnalysisExport({ caseId }) {
  const handleExport = async () => {
    try {
      const blob = await exportAnalysisPDF(caseId);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `CaseAnalysis_${caseId}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (error) {
      console.error('❌ Error exporting analysis PDF:', error);
    }
  };

  return (
    <button className="btn-accent" onClick={handleExport}>
      📄 Export PDF
    </button>
  );
}
