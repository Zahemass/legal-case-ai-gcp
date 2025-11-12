// frontend/src/components/chat/AIAgentChat.jsx
import React, { useState, useEffect, useRef } from 'react';
import ChatMessage from './ChatMessage';
import { useAuth } from '../../contexts/AuthContext';
import './AIAgentChat.css';

const AI_API_URL = import.meta.env.VITE_AI_AGENT_API_URL || 'http://localhost:8080';

export default function AIAgentChat({ caseId }) {
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [aiStatusText, setAiStatusText] = useState('');

  const messagesEndRef = useRef(null);
  const textareaRef = useRef(null);
  const { currentUser } = useAuth();

  // Load chat history on mount
  useEffect(() => {
    if (caseId) {
      loadChatHistory();
    }
  }, [caseId]);

  // Scroll to bottom when messages change
  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 120)}px`;
    }
  }, [inputMessage]);

  const loadChatHistory = async () => {
    try {
      console.log('📚 Loading chat history...');
      const response = await fetch(`${AI_API_URL}/chat/history/${caseId}`);
      const data = await response.json();
      
      if (data.success && data.messages) {
        setMessages([
          {
            id: 0,
            type: 'ai',
            content: `Hello! 👋 I'm your **AI Legal Assistant** for this case.

I can help you with:

- 🔍 **Evidence Analysis** - Review and analyze case evidence
- 📋 **Case Summaries** - Generate comprehensive summaries
- 📝 **Legal Drafts** - Create legal documents and briefs
- ⚖️ **Legal Questions** - Answer general legal inquiries

*How can I assist you today?*`,
            timestamp: new Date(),
            agent: 'general',
          },
          ...data.messages.map(msg => ({
            id: msg.id,
            type: msg.type,
            content: msg.message,
            timestamp: msg.timestamp ? new Date(msg.timestamp._seconds * 1000) : new Date(),
            agent: msg.type === 'ai' ? 'general' : undefined
          }))
        ]);
      }
    } catch (error) {
      console.error('❌ Error loading history:', error);
    }
  };

  const sendMessage = async () => {
    const trimmedMessage = inputMessage.trim();
    
    console.log('\n🚀 SENDING MESSAGE');
    console.log('   Message:', trimmedMessage);
    console.log('   Case ID:', caseId);
    console.log('   User ID:', currentUser?.uid);
    
    if (!trimmedMessage) {
      console.log('⚠️ Empty message');
      return;
    }
    
    if (!caseId || !currentUser?.uid) {
      console.error('❌ Missing case ID or user ID');
      return;
    }

    if (isTyping) {
      console.log('⚠️ AI is typing, please wait');
      return;
    }

    // Add user message to UI immediately
    const userMessage = {
      id: Date.now(),
      type: 'user',
      content: trimmedMessage,
      timestamp: new Date(),
    };
    
    setMessages(prev => [...prev, userMessage]);
    setInputMessage('');
    setIsTyping(true);
    setAiStatusText('🤖 AI is thinking...');

    try {
      console.log('📤 Sending HTTP POST request...');
      const startTime = Date.now();
      
      const response = await fetch(`${AI_API_URL}/chat/send`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: trimmedMessage,
          caseId: caseId,
          userId: currentUser.uid,
        }),
      });

      const responseTime = Date.now() - startTime;
      console.log(`✅ Response received in ${responseTime}ms`);

      const data = await response.json();
      
      if (data.success) {
        // Add AI response
        const aiMessage = {
          id: Date.now() + 1,
          type: 'ai',
          content: data.message,
          agent: data.agent || 'general',
          timestamp: new Date(data.timestamp * 1000),
        };
        
        setMessages(prev => [...prev, aiMessage]);
        console.log('✅ AI response added to UI');
      } else {
        console.error('❌ API error:', data.error);
        // Add error message
        setMessages(prev => [...prev, {
          id: Date.now() + 1,
          type: 'ai',
          content: 'I apologize, but I encountered an error. Please try again.',
          agent: 'error',
          timestamp: new Date(),
        }]);
      }
      
    } catch (error) {
      console.error('❌ Network error:', error);
      setMessages(prev => [...prev, {
        id: Date.now() + 1,
        type: 'ai',
        content: 'Connection error. Please check your internet and try again.',
        agent: 'error',
        timestamp: new Date(),
      }]);
    } finally {
      setIsTyping(false);
      setAiStatusText('');
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const handleSuggestionClick = (suggestion) => {
    setInputMessage(suggestion);
    textareaRef.current?.focus();
  };

  return (
    <div className="ai-chat">
      {/* Header */}
      <div className="ai-chat__header">
        <div className="ai-chat__header-gradient"></div>
        <div className="ai-chat__header-content">
          <div className="ai-chat__header-icon">
            <span className="ai-chat__icon-emoji">⚖️</span>
            <span className="ai-chat__status-indicator" data-status="connected">
              <span className="ai-chat__status-dot"></span>
              <span className="ai-chat__status-ring"></span>
            </span>
          </div>
          <div className="ai-chat__header-text">
            <h2 className="ai-chat__title">
              <span className="ai-chat__title-gradient">AI Legal Assistant</span>
            </h2>
            <p className="ai-chat__subtitle">
              <span className="ai-chat__status-badge ai-chat__status-badge--online">Online</span>
              Ready to assist with your case
            </p>
          </div>
        </div>
      </div>

      {/* Messages */}
      <div className="ai-chat__messages">
        <div className="ai-chat__messages-bg"></div>
        <div className="ai-chat__messages-inner">
          {messages.map((message) => (
            <ChatMessage key={message.id} message={message} />
          ))}

          {isTyping && (
            <div className="ai-chat__typing">
              <div className="ai-chat__typing-avatar">
                <span>🤖</span>
                <div className="ai-chat__typing-avatar-ring"></div>
              </div>
              <div className="ai-chat__typing-content">
                <div className="ai-chat__typing-bubble">
                  <div className="ai-chat__typing-dots">
                    <span></span>
                    <span></span>
                    <span></span>
                  </div>
                  <p className="ai-chat__typing-text">{aiStatusText}</p>
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input Area */}
      <div className="ai-chat__input-area">
        {/* Suggestions */}
        <div className="ai-chat__suggestions">
          <button
            className="ai-chat__suggestion"
            onClick={() => handleSuggestionClick('Summarize the key evidence in this case')}
            disabled={isTyping}
          >
            <span className="ai-chat__suggestion-icon">📋</span>
            <span className="ai-chat__suggestion-text">Summarize Evidence</span>
          </button>
          <button
            className="ai-chat__suggestion"
            onClick={() => handleSuggestionClick('What are the legal strengths and weaknesses?')}
            disabled={isTyping}
          >
            <span className="ai-chat__suggestion-icon">⚖️</span>
            <span className="ai-chat__suggestion-text">Legal Analysis</span>
          </button>
          <button
            className="ai-chat__suggestion"
            onClick={() => handleSuggestionClick('Draft a case brief')}
            disabled={isTyping}
          >
            <span className="ai-chat__suggestion-icon">📝</span>
            <span className="ai-chat__suggestion-text">Draft Brief</span>
          </button>
        </div>

        {/* Input Box */}
        <div className="ai-chat__input-wrapper">
          <div className="ai-chat__input-container">
            <textarea
              ref={textareaRef}
              className="ai-chat__input"
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Ask me anything about your case..."
              rows={1}
              disabled={isTyping}
            />
            <button
              className="ai-chat__send-button"
              onClick={sendMessage}
              disabled={!inputMessage.trim() || isTyping}
              aria-label="Send message"
            >
              <svg
                className="ai-chat__send-icon"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <line x1="22" y1="2" x2="11" y2="13"></line>
                <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
              </svg>
              <span className="ai-chat__send-ripple"></span>
            </button>
          </div>
          <p className="ai-chat__input-hint">
            <kbd>Enter</kbd> to send • <kbd>Shift + Enter</kbd> for new line
          </p>
        </div>
      </div>
    </div>
  );
}
