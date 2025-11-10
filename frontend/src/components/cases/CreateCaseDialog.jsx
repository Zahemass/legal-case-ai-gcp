import React, { useState } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import { createCase } from '../../services/api';
import './CreateCaseDialog.css';

export default function CreateCaseDialog({ onClose, onCaseCreated }) {
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [priority, setPriority] = useState('medium');
  const [type, setType] = useState('other');
  const [clientName, setClientName] = useState('');
  const [clientEmail, setClientEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const { currentUser } = useAuth();

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!title.trim()) return;

    try {
      setLoading(true);
      const newCase = await createCase({
        title: title.trim(),
        description: description.trim(),
        priority,
        type,
        clientName: clientName.trim(),
        clientEmail: clientEmail.trim(),
        createdBy: currentUser.uid,
        createdAt: new Date().toISOString(),
        status: 'active',
        documentCount: 0,
        analysisCount: 0
      });
      onCaseCreated(newCase);
    } catch (error) {
      console.error('Error creating case:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="dialog-overlay" onClick={onClose}>
      <div className="dialog" onClick={(e) => e.stopPropagation()}>
        <div className="dialog-header">
          <div className="dialog-header-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          </div>
          <h2>Create New Case</h2>
          <button className="close-btn" onClick={onClose} type="button">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="dialog-body">
            <div className="form-row">
              <div className="form-group">
                <label>
                  Case Title <span className="required">*</span>
                </label>
                <input
                  type="text"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="Enter case title"
                  required
                  autoFocus
                />
              </div>
            </div>

            <div className="form-row">
              <div className="form-group">
                <label>Case Type</label>
                <select value={type} onChange={(e) => setType(e.target.value)}>
                  <option value="criminal">Criminal</option>
                  <option value="civil">Civil</option>
                  <option value="corporate">Corporate</option>
                  <option value="family">Family</option>
                  <option value="other">Other</option>
                </select>
              </div>

              <div className="form-group">
                <label>Priority</label>
                <select value={priority} onChange={(e) => setPriority(e.target.value)}>
                  <option value="low">Low Priority</option>
                  <option value="medium">Medium Priority</option>
                  <option value="high">High Priority</option>
                </select>
              </div>
            </div>

            <div className="form-row">
              <div className="form-group">
                <label>Client Name</label>
                <input
                  type="text"
                  value={clientName}
                  onChange={(e) => setClientName(e.target.value)}
                  placeholder="Enter client name"
                />
              </div>

              <div className="form-group">
                <label>Client Email</label>
                <input
                  type="email"
                  value={clientEmail}
                  onChange={(e) => setClientEmail(e.target.value)}
                  placeholder="client@example.com"
                />
              </div>
            </div>

            <div className="form-row">
              <div className="form-group">
                <label>Description</label>
                <textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Enter case description (optional)"
                  rows={4}
                />
              </div>
            </div>
          </div>

          <div className="dialog-footer">
            <button type="button" className="btn-cancel" onClick={onClose}>
              Cancel
            </button>
            <button type="submit" className="btn-submit" disabled={loading || !title.trim()}>
              {loading ? (
                <>
                  <span className="spinner-small" />
                  Creating...
                </>
              ) : (
                <>
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M12 4v16m8-8H4" />
                  </svg>
                  Create Case
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}