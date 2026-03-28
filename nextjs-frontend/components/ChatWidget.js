'use client';
import { useState, useEffect, useRef, useCallback } from 'react';
import { getBackendUrl } from '../utils/api';

export default function ChatWidget() {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState(null);

  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);
  const panelRef = useRef(null);

  // Auto-scroll to latest message
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  // Focus input when panel opens
  useEffect(() => {
    if (isOpen && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isOpen]);

  // Focus trap when panel is open
  const handleKeyDown = useCallback((e) => {
    if (!isOpen) return;

    if (e.key === 'Escape') {
      setIsOpen(false);
      return;
    }

    if (e.key === 'Tab' && panelRef.current) {
      const focusable = panelRef.current.querySelectorAll(
        'button, input, [tabindex]:not([tabindex="-1"])'
      );
      if (focusable.length === 0) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (e.shiftKey) {
        if (document.activeElement === first) {
          e.preventDefault();
          last.focus();
        }
      } else {
        if (document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
    }
  }, [isOpen]);

  useEffect(() => {
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    const trimmed = input.trim();
    if (!trimmed || isLoading) return;

    const userMessage = {
      role: 'user',
      content: trimmed,
      timestamp: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      const backendUrl = getBackendUrl();
      const res = await fetch(`${backendUrl}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, message: trimmed }),
      });

      if (!res.ok) {
        let errorMsg = 'Something went wrong. Please try again.';
        try {
          const errData = await res.json();
          if (errData.message) errorMsg = errData.message;
        } catch {}
        setMessages((prev) => [
          ...prev,
          { role: 'error', content: errorMsg, timestamp: new Date().toISOString() },
        ]);
        return;
      }

      let data;
      try {
        data = await res.json();
      } catch {
        setMessages((prev) => [
          ...prev,
          { role: 'error', content: 'Something went wrong. Please try again.', timestamp: new Date().toISOString() },
        ]);
        return;
      }

      if (data.session_id) setSessionId(data.session_id);

      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: data.response,
          timestamp: new Date().toISOString(),
          sources: data.sources,
        },
      ]);
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: 'error', content: 'Unable to reach the server. Please try again.', timestamp: new Date().toISOString() },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  // --- Styles ---
  const toggleBtnStyle = {
    position: 'fixed',
    bottom: '24px',
    right: '24px',
    zIndex: 9999,
    width: '56px',
    height: '56px',
    borderRadius: '50%',
    border: 'none',
    background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
    color: '#fff',
    cursor: 'pointer',
    boxShadow: '0 4px 14px rgba(102, 126, 234, 0.5)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    transition: 'transform 0.2s, box-shadow 0.2s',
  };

  const panelStyle = {
    position: 'fixed',
    bottom: '90px',
    right: '24px',
    zIndex: 9999,
    width: 'min(380px, calc(100vw - 32px))',
    maxHeight: 'min(520px, calc(100vh - 120px))',
    borderRadius: '16px',
    background: '#fff',
    boxShadow: '0 8px 32px rgba(0, 0, 0, 0.18)',
    display: 'flex',
    flexDirection: 'column',
    overflow: 'hidden',
  };

  const headerStyle = {
    background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
    color: '#fff',
    padding: '14px 18px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    flexShrink: 0,
  };

  const messagesAreaStyle = {
    flex: 1,
    overflowY: 'auto',
    padding: '14px',
    display: 'flex',
    flexDirection: 'column',
    gap: '10px',
    minHeight: 0,
  };

  const inputBarStyle = {
    display: 'flex',
    padding: '10px 14px',
    borderTop: '1px solid #e5e7eb',
    gap: '8px',
    flexShrink: 0,
    background: '#fafafa',
  };

  const bubbleBase = {
    maxWidth: '80%',
    padding: '10px 14px',
    borderRadius: '14px',
    fontSize: '14px',
    lineHeight: '1.5',
    wordBreak: 'break-word',
  };

  const userBubble = {
    ...bubbleBase,
    alignSelf: 'flex-end',
    background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
    color: '#fff',
    borderBottomRightRadius: '4px',
  };

  const assistantBubble = {
    ...bubbleBase,
    alignSelf: 'flex-start',
    background: '#f3f4f6',
    color: '#1f2937',
    borderBottomLeftRadius: '4px',
  };

  const errorBubble = {
    ...bubbleBase,
    alignSelf: 'flex-start',
    background: '#fef2f2',
    color: '#b91c1c',
    border: '1px solid #fecaca',
    borderBottomLeftRadius: '4px',
  };

  const loadingDots = {
    alignSelf: 'flex-start',
    display: 'flex',
    gap: '4px',
    padding: '10px 14px',
  };

  return (
    <>
      {/* Toggle Button */}
      {!isOpen && (
        <button
          onClick={() => setIsOpen(true)}
          style={toggleBtnStyle}
          aria-label="Open chat assistant"
          title="Chat with legal assistant"
        >
          <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
          </svg>
        </button>
      )}

      {/* Chat Panel */}
      {isOpen && (
        <div ref={panelRef} role="dialog" aria-label="Chat assistant" style={panelStyle}>
          {/* Header */}
          <div style={headerStyle}>
            <span style={{ fontWeight: 600, fontSize: '15px' }}>Legal Assistant</span>
            <button
              onClick={() => setIsOpen(false)}
              aria-label="Close chat"
              style={{
                background: 'none',
                border: 'none',
                color: '#fff',
                cursor: 'pointer',
                padding: '4px',
                display: 'flex',
                alignItems: 'center',
              }}
            >
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <line x1="18" y1="6" x2="6" y2="18" />
                <line x1="6" y1="6" x2="18" y2="18" />
              </svg>
            </button>
          </div>

          {/* Messages */}
          <div style={messagesAreaStyle} role="log" aria-label="Chat messages" aria-live="polite">
            {messages.length === 0 && (
              <div style={{ textAlign: 'center', color: '#9ca3af', fontSize: '13px', marginTop: '40px' }}>
                Ask me anything about legal cases on this platform.
              </div>
            )}
            {messages.map((msg, i) => {
              const style =
                msg.role === 'user' ? userBubble :
                msg.role === 'error' ? errorBubble :
                assistantBubble;
              return (
                <div key={i} style={style}>
                  {msg.content}
                  {msg.sources && msg.sources.length > 0 && (
                    <div style={{ marginTop: '8px', fontSize: '12px', opacity: 0.8, borderTop: '1px solid rgba(0,0,0,0.1)', paddingTop: '6px' }}>
                      <strong>Sources:</strong>
                      {msg.sources.map((s, j) => (
                        <div key={j} style={{ marginTop: '2px' }}>• {s.title || s.case_id}</div>
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
            {isLoading && (
              <div style={loadingDots} aria-label="Loading response">
                {[0, 1, 2].map((i) => (
                  <span
                    key={i}
                    style={{
                      width: '8px',
                      height: '8px',
                      borderRadius: '50%',
                      background: '#667eea',
                      animation: `chatDotPulse 1.2s ease-in-out ${i * 0.2}s infinite`,
                    }}
                  />
                ))}
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Input */}
          <form onSubmit={handleSubmit} style={inputBarStyle}>
            <input
              ref={inputRef}
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Type your message..."
              aria-label="Chat message input"
              disabled={isLoading}
              style={{
                flex: 1,
                border: '1px solid #d1d5db',
                borderRadius: '8px',
                padding: '8px 12px',
                fontSize: '14px',
                outline: 'none',
                transition: 'border-color 0.2s',
              }}
              onFocus={(e) => (e.target.style.borderColor = '#667eea')}
              onBlur={(e) => (e.target.style.borderColor = '#d1d5db')}
            />
            <button
              type="submit"
              disabled={isLoading || !input.trim()}
              aria-label="Send message"
              style={{
                background: isLoading || !input.trim()
                  ? '#c4b5fd'
                  : 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                color: '#fff',
                border: 'none',
                borderRadius: '8px',
                padding: '8px 14px',
                cursor: isLoading || !input.trim() ? 'not-allowed' : 'pointer',
                display: 'flex',
                alignItems: 'center',
                transition: 'opacity 0.2s',
              }}
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <line x1="22" y1="2" x2="11" y2="13" />
                <polygon points="22 2 15 22 11 13 2 9 22 2" />
              </svg>
            </button>
          </form>
        </div>
      )}

      {/* Keyframe animation for loading dots */}
      <style>{`
        @keyframes chatDotPulse {
          0%, 80%, 100% { opacity: 0.3; transform: scale(0.8); }
          40% { opacity: 1; transform: scale(1.1); }
        }
      `}</style>
    </>
  );
}
