import React, { useState, useEffect } from "react";
import ReactDOM from "react-dom";
import { getDocumentPreview } from "../../services/api";
import "./DocumentPreview.css";

export default function DocumentPreview({ document: doc }) {
  const [showModal, setShowModal] = useState(false);
  const [previewContent, setPreviewContent] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (typeof window !== "undefined" && window.document) {
      window.document.body.style.overflow = showModal ? "hidden" : "auto";
    }
    return () => {
      if (typeof window !== "undefined" && window.document) {
        window.document.body.style.overflow = "auto";
      }
    };
  }, [showModal]);

  const handlePreview = async (e) => {
    e.preventDefault();
    e.stopPropagation();

    if (showModal) return;

    try {
      setLoading(true);
      const content = await getDocumentPreview(doc.id);
      setPreviewContent(content);
      setShowModal(true);
    } catch (error) {
      console.error("❌ Error loading preview:", error);
      setPreviewContent("⚠️ Unable to load preview.");
      setShowModal(true);
    } finally {
      setLoading(false);
    }
  };

  const closeModal = (e) => {
    e?.stopPropagation();
    setShowModal(false);
  };

  const handleOverlayClick = (e) => {
    if (e.target === e.currentTarget) closeModal(e);
  };

  return (
    <>
      <button
        className="btn-secondary"
        onClick={handlePreview}
        disabled={loading}
      >
        {loading ? (
          <>
            <span className="spinner" /> Loading...
          </>
        ) : (
          <>Preview</>
        )}
      </button>

      {showModal &&
        ReactDOM.createPortal(
          <div className="preview-modal-overlay" onClick={handleOverlayClick}>
            <div className="preview-modal-container" onClick={(e) => e.stopPropagation()}>
              <div className="preview-header">
                <div className="header-info">
                  <div className="header-icon">📄</div>
                  <div>
                    <h2>Document Preview</h2>
                    <p className="filename">{doc.filename}</p>
                  </div>
                </div>
                <button className="close-btn" onClick={closeModal}>
                  ✕
                </button>
              </div>

              <div className="preview-body">
                <pre>{previewContent || "No preview available."}</pre>
              </div>

              <div className="preview-footer">
                  
              </div>
            </div>
          </div>,
          window.document.body
        )}
    </>
  );
}
