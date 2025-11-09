import React from 'react';
import './ChatMessage.css';

export default function ChatMessage({ message }) {
  const getAgentIcon = (agent) => {
    switch (agent) {
      case 'evidence': return '🔍';
      case 'summary': return '📋';
      case 'draft': return '📝';
      case 'general': return '⚖️';
      default: return '🤖';
    }
  };

  return (
    <div className={`message ${message.type}`}>
      <div className="message-avatar">
        {message.type === 'user' ? '👤' : getAgentIcon(message.agent)}
      </div>
      <div className="message-content">
        {message.agent && (
          <div className="agent-label">
            {message.agent.charAt(0).toUpperCase() + message.agent.slice(1)} Agent
          </div>
        )}
        <div className="message-text">
          {message.content}
        </div>
        <div className="message-timestamp">
          {message.timestamp.toLocaleTimeString()}
        </div>
      </div>
    </div>
  );
}