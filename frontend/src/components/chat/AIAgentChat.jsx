import React, { useState, useEffect, useRef } from 'react';
import { io } from 'socket.io-client';
import ChatMessage from './ChatMessage';
import { useAuth } from '../../contexts/AuthContext';
import './AIAgentChat.css';

export default function AIAgentChat({ caseId }) {
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingMessageId, setStreamingMessageId] = useState(null);
  const [aiStatusText, setAiStatusText] = useState('');
  const [connectionStatus, setConnectionStatus] = useState('connecting');

  const aiStatusIndexRef = useRef(0);
  const aiStatusTimerRef = useRef(null);
  const messagesEndRef = useRef(null);
  const textareaRef = useRef(null);
  const { currentUser } = useAuth();
  const wsRef = useRef(null);

  // 🔌 Initialize WebSocket connection
  useEffect(() => {
    if (!caseId || !currentUser) return;
    connectSocket();

    return () => {
      if (wsRef.current) {
        wsRef.current.disconnect();
        wsRef.current = null;
        console.log('🔴 Socket.IO disconnected on cleanup');
      }
      if (aiStatusTimerRef.current) {
        clearInterval(aiStatusTimerRef.current);
      }
    };
  }, [caseId, currentUser]);

  // 🔽 Scroll down whenever messages change
  useEffect(() => {
    scrollToBottom();
  }, [messages, isStreaming]);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 120)}px`;
    }
  }, [inputMessage]);

  const connectSocket = () => {
    setConnectionStatus('connecting');
    
    const socket = io(import.meta.env.VITE_WS_URL, {
      transports: ['websocket'],
      reconnection: true,
      reconnectionAttempts: 10,
      reconnectionDelay: 3000,
      timeout: 90000,
      pingTimeout: 120000,
      pingInterval: 25000,
      auth: {
        userId: currentUser?.uid,
        caseId: caseId,
      },
    });

    wsRef.current = socket;

    // ✅ Connected
    socket.on('connect', () => {
      console.log('✅ Socket.IO connected:', socket.id);
      setConnectionStatus('connected');

      socket.emit('join_case', {
        caseId: caseId,
        userId: currentUser?.uid,
      });

      setMessages([
        {
          id: 1,
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
      ]);
    });

    // 📩 AI message received (streaming support)
    socket.on('message_received', (data) => {
      console.log('📩 Received from AI Agent:', data);

      if (data.userId === currentUser?.uid) return;

      const messageType = data.type === 'ai' ? 'ai' : 'user';
      const newMessageId = data.id || Date.now();

      // Check if this is a streaming message
      if (data.streaming) {
        setIsStreaming(true);
        setStreamingMessageId(newMessageId);
      }

      setMessages((prev) => {
        // Update existing streaming message or add new one
        const existingIndex = prev.findIndex(m => m.id === newMessageId);
        
        if (existingIndex !== -1) {
          const updated = [...prev];
          updated[existingIndex] = {
            ...updated[existingIndex],
            content: data.message,
          };
          return updated;
        }

        return [
          ...prev,
          {
            id: newMessageId,
            type: messageType,
            content: data.message,
            agent: data.agent,
            timestamp: new Date(data.timestamp * 1000 || Date.now()),
          },
        ];
      });

      // Stop streaming when message is complete
      if (!data.streaming) {
        setIsStreaming(false);
        setStreamingMessageId(null);
        setIsTyping(false);
        setAiStatusText('');
        if (aiStatusTimerRef.current) clearInterval(aiStatusTimerRef.current);
      }
    });

    // 🧠 AI starts thinking
    socket.on('ai_thinking', () => {
      setIsTyping(true);
      const statusMessages = [
        '🤖 Initializing AI agents...',
        '🧠 Gemini analyzing your request...',
        '⚖️ Processing case context...',
        '📚 Researching legal precedents...',
        '📄 Drafting response...',
        '✨ Finalizing answer...',
      ];

      aiStatusIndexRef.current = 0;
      setAiStatusText(statusMessages[0]);

      if (aiStatusTimerRef.current) clearInterval(aiStatusTimerRef.current);
      aiStatusTimerRef.current = setInterval(() => {
        aiStatusIndexRef.current =
          (aiStatusIndexRef.current + 1) % statusMessages.length;
        setAiStatusText(statusMessages[aiStatusIndexRef.current]);
      }, 45000);
    });

    // ✅ AI finished thinking
    socket.on('ai_thinking_stop', () => {
      setIsTyping(false);
      setAiStatusText('');
      if (aiStatusTimerRef.current) clearInterval(aiStatusTimerRef.current);
    });

    // ⚠️ Connection handling
    socket.on('connect_error', (err) => {
      console.error('⚠️ Socket connection error:', err.message);
      setConnectionStatus('error');
    });

    socket.on('disconnect', (reason) => {
      console.warn('❌ Socket disconnected:', reason);
      setConnectionStatus('disconnected');
      setIsTyping(false);
      setIsStreaming(false);
      setAiStatusText('');
    });

    socket.on('reconnect', (attempt) => {
      console.log(`🔁 Reconnected after ${attempt} attempts`);
      setConnectionStatus('connected');
      setAiStatusText('');
    });
  };

  // ✉️ Send message to backend
  const sendMessage = () => {
    if (!inputMessage.trim() || !wsRef.current || isTyping) return;

    const message = {
      message: inputMessage.trim(),
      caseId,
      userId: currentUser?.uid,
    };

    setMessages((prev) => [
      ...prev,
      {
        id: Date.now(),
        type: 'user',
        content: inputMessage,
        timestamp: new Date(),
      },
    ]);

    setInputMessage('');
    setIsTyping(true);
    wsRef.current.emit('send_message', message);
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
      {/* Header with Dark Mode Toggle */}
      <div className="ai-chat__header">
        <div className="ai-chat__header-gradient"></div>
        <div className="ai-chat__header-content">
          <div className="ai-chat__header-icon">
            <span className="ai-chat__icon-emoji">⚖️</span>
            <span className="ai-chat__status-indicator" data-status={connectionStatus}>
              <span className="ai-chat__status-dot"></span>
              <span className="ai-chat__status-ring"></span>
            </span>
          </div>
          <div className="ai-chat__header-text">
            <h2 className="ai-chat__title">
              <span className="ai-chat__title-gradient">AI Legal Assistant</span>
            </h2>
            <p className="ai-chat__subtitle">
              {connectionStatus === 'connected' && (
                <>
                  <span className="ai-chat__status-badge ai-chat__status-badge--online">Online</span>
                  Ready to assist with your case
                </>
              )}
              {connectionStatus === 'connecting' && (
                <>
                  <span className="ai-chat__status-badge ai-chat__status-badge--connecting">Connecting</span>
                  Establishing connection...
                </>
              )}
              {connectionStatus === 'disconnected' && (
                <>
                  <span className="ai-chat__status-badge ai-chat__status-badge--offline">Offline</span>
                  Connection lost
                </>
              )}
              {connectionStatus === 'error' && (
                <>
                  <span className="ai-chat__status-badge ai-chat__status-badge--error">Error</span>
                  Connection failed
                </>
              )}
            </p>
          </div>
        </div>
      </div>

      {/* Messages */}
      <div className="ai-chat__messages">
        <div className="ai-chat__messages-bg"></div>
        <div className="ai-chat__messages-inner">
          {messages.map((message) => (
            <ChatMessage 
              key={message.id} 
              message={message}
              isStreaming={isStreaming && message.id === streamingMessageId}
            />
          ))}

          {isTyping && !isStreaming && (
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
              disabled={isTyping || connectionStatus !== 'connected'}
            />
            <button
              className="ai-chat__send-button"
              onClick={sendMessage}
              disabled={!inputMessage.trim() || isTyping || connectionStatus !== 'connected'}
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
