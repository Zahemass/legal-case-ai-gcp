import React, { useState, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeRaw from 'rehype-raw';
import './ChatMessage.css';

export default function ChatMessage({ message, isStreaming = false }) {
  const [displayedContent, setDisplayedContent] = useState('');
  const [currentIndex, setCurrentIndex] = useState(0);

  // Typing animation effect
  useEffect(() => {
    if (isStreaming && currentIndex < message.content.length) {
      const timeout = setTimeout(() => {
        setDisplayedContent(message.content.slice(0, currentIndex + 1));
        setCurrentIndex(currentIndex + 1);
      }, 20); // Adjust speed here (lower = faster)

      return () => clearTimeout(timeout);
    } else if (!isStreaming) {
      setDisplayedContent(message.content);
      setCurrentIndex(message.content.length);
    }
  }, [isStreaming, currentIndex, message.content]);

  const getAgentIcon = (agent) => {
    const icons = {
      evidence: '🔍',
      summary: '📋',
      draft: '📝',
      general: '⚖️',
    };
    return icons[agent] || '🤖';
  };

  const getAgentColor = (agent) => {
    const colors = {
      evidence: '#10b981',
      summary: '#3b82f6',
      draft: '#8b5cf6',
      general: '#f59e0b',
    };
    return colors[agent] || '#6366f1';
  };

  const isUser = message.type === 'user';
  const icon = isUser ? '👤' : getAgentIcon(message.agent);
  const agentColor = getAgentColor(message.agent);
  const contentToDisplay = isStreaming ? displayedContent : message.content;

  return (
    <div className={`chat-message ${isUser ? 'chat-message--user' : 'chat-message--ai'} ${isStreaming ? 'chat-message--streaming' : ''}`}>
      <div 
        className="chat-message__avatar"
        style={!isUser ? { background: `${agentColor}15` } : {}}
      >
        <span className="chat-message__avatar-icon">{icon}</span>
        {isStreaming && !isUser && (
          <div className="chat-message__avatar-pulse" style={{ borderColor: agentColor }}></div>
        )}
      </div>
      
      <div className="chat-message__content">
        {!isUser && message.agent && (
          <div 
            className="chat-message__agent-badge"
            style={{ background: agentColor }}
          >
            <span className="chat-message__agent-badge-dot"></span>
            {message.agent.charAt(0).toUpperCase() + message.agent.slice(1)} Agent
          </div>
        )}

        <div className="chat-message__bubble">
          <div className="chat-message__text">
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              rehypePlugins={[rehypeRaw]}
              components={{
                h1: ({ node, ...props }) => (
                  <h1 className="markdown-h1" {...props} />
                ),
                h2: ({ node, ...props }) => (
                  <h2 className="markdown-h2" {...props} />
                ),
                h3: ({ node, ...props }) => (
                  <h3 className="markdown-h3" {...props} />
                ),
                ul: ({ node, ...props }) => (
                  <ul className="markdown-list" {...props} />
                ),
                ol: ({ node, ...props }) => (
                  <ol className="markdown-list markdown-list--ordered" {...props} />
                ),
                li: ({ node, ...props }) => (
                  <li className="markdown-list-item" {...props} />
                ),
                p: ({ node, ...props }) => (
                  <p className="markdown-paragraph" {...props} />
                ),
                strong: ({ node, ...props }) => (
                  <strong className="markdown-strong" {...props} />
                ),
                em: ({ node, ...props }) => (
                  <em className="markdown-em" {...props} />
                ),
                code: ({ node, inline, ...props }) => 
                  inline ? (
                    <code className="markdown-code-inline" {...props} />
                  ) : (
                    <code className="markdown-code-block" {...props} />
                  ),
                pre: ({ node, ...props }) => (
                  <pre className="markdown-pre" {...props} />
                ),
                blockquote: ({ node, ...props }) => (
                  <blockquote className="markdown-blockquote" {...props} />
                ),
                a: ({ node, ...props }) => (
                  <a className="markdown-link" target="_blank" rel="noopener noreferrer" {...props} />
                ),
                table: ({ node, ...props }) => (
                  <div className="markdown-table-wrapper">
                    <table className="markdown-table" {...props} />
                  </div>
                ),
              }}
            >
              {contentToDisplay}
            </ReactMarkdown>
            {isStreaming && <span className="chat-message__cursor"></span>}
          </div>

          {!isStreaming && (
            <div className="chat-message__timestamp">
              {message.timestamp instanceof Date
                ? message.timestamp.toLocaleTimeString('en-US', { 
                    hour: '2-digit', 
                    minute: '2-digit' 
                  })
                : new Date(message.timestamp).toLocaleTimeString('en-US', { 
                    hour: '2-digit', 
                    minute: '2-digit' 
                  })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}