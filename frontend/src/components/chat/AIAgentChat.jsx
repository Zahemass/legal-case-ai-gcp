import React, { useState, useEffect, useRef } from 'react';
import ChatMessage from './ChatMessage';
import { useAuth } from '../../contexts/AuthContext';
import './AIAgentChat.css';

export default function AIAgentChat({ caseId }) {
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef(null);
  const { currentUser } = useAuth();
  const wsRef = useRef(null);

  useEffect(() => {
    connectWebSocket();
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [caseId]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const connectWebSocket = () => {
    const wsUrl = `${import.meta.env.VITE_WS_URL}/chat/${caseId}`;
    wsRef.current = new WebSocket(wsUrl);

    wsRef.current.onopen = () => {
      console.log('WebSocket connected');
      // Send initial message
      setMessages([{
        id: 1,
        type: 'ai',
        content: `Hello! I'm your AI legal assistant for this case. I can help you with evidence analysis, case summaries, legal drafts, and general legal questions. How can I assist you today?`,
        timestamp: new Date()
      }]);
    };

    wsRef.current.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setMessages(prev => [...prev, {
        id: Date.now(),
        type: 'ai',
        content: data.message,
        timestamp: new Date(),
        agent: data.agent
      }]);
      setIsTyping(false);
    };

    wsRef.current.onerror = (error) => {
      console.error('WebSocket error:', error);
      setIsTyping(false);
    };
  };

  const sendMessage = () => {
    if (!inputMessage.trim() || !wsRef.current) return;

    const userMessage = {
      id: Date.now(),
      type: 'user',
      content: inputMessage,
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setIsTyping(true);

    wsRef.current.send(JSON.stringify({
      message: inputMessage,
      userId: currentUser.uid,
      caseId: caseId
    }));

    setInputMessage('');
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

  return (
    <div className="ai-chat-container">
      <div className="chat-messages">
        {messages.map(message => (
          <ChatMessage key={message.id} message={message} />
        ))}
        {isTyping && (
          <div className="typing-indicator">
            <div className="typing-dots">
              <span></span>
              <span></span>
              <span></span>
            </div>
            <span>AI is thinking...</span>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className="chat-input-container">
        <div className="chat-input">
          <textarea
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Ask me anything about your case..."
            rows={3}
          />
          <button 
            onClick={sendMessage}
            disabled={!inputMessage.trim() || isTyping}
          >
            Send
          </button>
        </div>
        
        <div className="chat-suggestions">
          <button onClick={() => setInputMessage("Summarize the key evidence in this case")}>
            📋 Summarize Evidence
          </button>
          <button onClick={() => setInputMessage("What are the legal strengths and weaknesses?")}>
            ⚖️ Legal Analysis
          </button>
          <button onClick={() => setInputMessage("Draft a case brief")}>
            📝 Draft Brief
          </button>
        </div>
      </div>
    </div>
  );
}