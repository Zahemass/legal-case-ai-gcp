import React, { useState, useEffect } from "react";
import { analyzeDocument } from "../../services/api";
import "./DocumentAnalysis.css";
import ReactDOM from "react-dom";

export default function DocumentAnalysis({ document: documentData, onAnalysisComplete }) {
  const [analyzing, setAnalyzing] = useState(false);
  const [analysis, setAnalysis] = useState(null);
  const [showModal, setShowModal] = useState(false);
  const [activeTab, setActiveTab] = useState(null);

  useEffect(() => {
    document.body.style.overflow = showModal ? "hidden" : "auto";
    return () => (document.body.style.overflow = "auto");
  }, [showModal]);

  const handleAnalyze = async (e) => {
    e.preventDefault();
    e.stopPropagation();
    try {
      setAnalyzing(true);
      const result = await analyzeDocument(documentData.id);
      const data = result.data || result;

      setAnalysis(data);
      setShowModal(true);
      onAnalysisComplete?.();
    } catch (error) {
      console.error("Error analyzing document:", error);
      alert("Failed to analyze document. Please try again.");
    } finally {
      setAnalyzing(false);
    }
  };

  const closeModal = (e) => {
    e?.preventDefault();
    e?.stopPropagation();
    setShowModal(false);
    setActiveTab(null);
  };

  const handleOverlayClick = (e) => {
    if (e.target === e.currentTarget) closeModal(e);
  };

  const handleModalClick = (e) => e.stopPropagation();

  // ✅ Helper to check if a field has usable content
  const hasContent = (val) =>
    val &&
    ((Array.isArray(val) && val.length > 0) ||
      (typeof val === "object" && Object.keys(val).length > 0) ||
      (typeof val === "string" && val.trim() !== ""));

  // ✅ Build only available tabs (no sentiment)
  const availableTabs = [];
  if (hasContent(analysis?.summary)) availableTabs.push({ id: "summary", label: "Summary", icon: "📋" });
  if (hasContent(analysis?.keyPoints)) availableTabs.push({ id: "keyPoints", label: "Key Points", icon: "🔍" });
  if (hasContent(analysis?.recommendations)) availableTabs.push({ id: "recommendations", label: "Recommendations", icon: "💡" });

  // ✅ Default tab
  useEffect(() => {
    if (!activeTab && availableTabs.length > 0) setActiveTab(availableTabs[0].id);
  }, [analysis, availableTabs, activeTab]);

  // ✅ Clean up JSON-style summary
  const getCleanSummary = (raw) => {
    if (!raw) return "No summary available.";
    let clean = raw;

    try {
      // Remove markdown fences like ```json or ```
      clean = clean.replace(/```json|```/gi, "").trim();

      // Handle double-encoded JSON (string within string)
      if (typeof clean === "string" && clean.startsWith("{")) {
        try {
          const parsed = JSON.parse(clean);
          if (parsed.summary) clean = parsed.summary;
        } catch {
          // maybe it's nested inside another JSON
          const inner = clean.match(/"summary"\s*:\s*"([^"]+)"/);
          if (inner && inner[1]) clean = inner[1];
        }
      }

      // Clean up any remaining "summary": or braces
      clean = clean
        .replace(/^\s*{?\s*"*summary"*\s*[:=]\s*/i, "")
        .replace(/[{}"]/g, "")
        .trim();
    } catch (err) {
      console.warn("Summary parsing failed:", err);
    }

    return clean || "No summary available.";
  };

  return (
    <>
      <button className="analyze-btn" onClick={handleAnalyze} disabled={analyzing}>
        {analyzing ? (
          <>
            <span className="spinner"></span> Analyzing...
          </>
        ) : (
          <>
            <span className="icon">🤖</span> AI Analysis
          </>
        )}
      </button>

      {showModal && analysis &&
        ReactDOM.createPortal(
          <div className="analysis-modal-overlay" onClick={handleOverlayClick}>
            <div className="analysis-modal-container" onClick={handleModalClick}>
              {/* Header */}
              <div className="analysis-modal-header">
                <div className="modal-header-content">
                  <div className="modal-header-icon">🤖</div>
                  <div className="modal-header-text">
                    <h2>AI Document Analysis</h2>
                    <p className="modal-document-name">{documentData.filename}</p>
                  </div>
                </div>
                <button className="modal-close-btn" onClick={closeModal}>
                  ✕
                </button>
              </div>

              {/* Tabs */}
              {availableTabs.length > 0 && (
                <div className="modal-tab-navigation">
                  {availableTabs.map((tab) => (
                    <button
                      key={tab.id}
                      className={`modal-tab-btn ${activeTab === tab.id ? "active" : ""}`}
                      onClick={(e) => {
                        e.stopPropagation();
                        setActiveTab(tab.id);
                      }}
                    >
                      <span className="modal-tab-icon">{tab.icon}</span>
                      <span>{tab.label}</span>
                    </button>
                  ))}
                </div>
              )}

              {/* Body */}
              <div className="modal-analysis-body">
                {/* ✅ SUMMARY */}
                {activeTab === "summary" && hasContent(analysis.summary) && (
                  <div className="modal-content-section fade-in">
                    <div className="modal-section-card">
                      <div className="modal-card-header">
                        <span className="modal-card-icon">📋</span>
                        <h3>Summary</h3>
                      </div>
                      <div className="modal-card-body">
                        <p style={{ whiteSpace: "pre-wrap", lineHeight: "1.6" }}>
                          {getCleanSummary(analysis.summary)}
                        </p>
                      </div>
                    </div>
                  </div>
                )}

                {/* ✅ KEY POINTS */}
                {activeTab === "keyPoints" && hasContent(analysis.keyPoints) && (
                  <div className="modal-content-section fade-in">
                    <div className="modal-section-card">
                      <div className="modal-card-header">
                        <span className="modal-card-icon">🔍</span>
                        <h3>Key Points</h3>
                      </div>
                      <ul className="modal-key-points-grid">
                        {analysis.keyPoints.map((point, i) => (
                          <li key={i} className="modal-key-point-item">
                            <div className="modal-point-number">{i + 1}</div>
                            <div className="modal-point-content">{point}</div>
                          </li>
                        ))}
                      </ul>
                    </div>
                  </div>
                )}

                {/* ✅ LEGAL INSIGHTS */}
                {activeTab === "legal" && hasContent(analysis.legalAnalysis) && (
                  <div className="modal-content-section fade-in">
                    <div className="modal-section-card">
                      <div className="modal-card-header">
                        <span className="modal-card-icon">⚖️</span>
                        <h3>Legal Insights</h3>
                      </div>
                      <div className="modal-card-body">
                        {Object.entries(analysis.legalAnalysis).map(([key, val], idx) =>
                          hasContent(val) ? (
                            <div key={idx} className="modal-legal-block">
                              <h4>{key.replace(/([A-Z])/g, " $1").trim()}</h4>
                              {Array.isArray(val) ? (
                                <ul className="modal-key-points-grid">
                                  {val.map((v, i) => (
                                    <li key={i} className="modal-key-point-item">
                                      <div className="modal-point-number">{i + 1}</div>
                                      <div className="modal-point-content">{v}</div>
                                    </li>
                                  ))}
                                </ul>
                              ) : (
                                <p>{val}</p>
                              )}
                            </div>
                          ) : null
                        )}
                      </div>
                    </div>
                  </div>
                )}

                {/* ✅ RECOMMENDATIONS */}
                {activeTab === "recommendations" && hasContent(analysis.recommendations) && (
                  <div className="modal-content-section fade-in">
                    <div className="modal-section-card">
                      <div className="modal-card-header">
                        <span className="modal-card-icon">💡</span>
                        <h3>Recommendations</h3>
                      </div>
                      <ul className="modal-key-points-grid">
                        {analysis.recommendations.map((rec, i) => (
                          <li key={i} className="modal-key-point-item">
                            <div className="modal-point-number">{i + 1}</div>
                            <div className="modal-point-content">{rec}</div>
                          </li>
                        ))}
                      </ul>
                    </div>
                  </div>
                )}
              </div>

              {/* Footer */}
              <div className="modal-action-bar">
                <button className="modal-action-btn secondary" onClick={closeModal}>
                  Close
                </button>
              </div>
            </div>
          </div>,
          document.body
        )}
    </>
  );
}
