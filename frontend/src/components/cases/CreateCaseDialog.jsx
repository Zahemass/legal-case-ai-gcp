import React, { useState } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import { createCase } from '../../services/api';
import './CreateCaseDialog.css';

export default function CreateCaseDialog({ onClose, onCaseCreated }) {
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
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
        createdBy: currentUser.uid,
        createdAt: new Date().toISOString()
      });
      onCaseCreated(newCase);
    } catch (error) {
      console.error('Error creating case:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="dialog-overlay">
      <div className="dialog">
        <div className="dialog-header">
          <h2>Create New Case</h2>
          <button className="close-btn" onClick={onClose}>×</button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>Case Title *</label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Enter case title"
              required
            />
          </div>

          <div className="form-group">
            <label>Description</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Enter case description (optional)"
              rows={4}
            />
          </div>

          <div className="dialog-actions">
            <button type="button" onClick={onClose}>Cancel</button>
            <button type="submit" disabled={loading || !title.trim()}>
              {loading ? 'Creating...' : 'Create Case'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}