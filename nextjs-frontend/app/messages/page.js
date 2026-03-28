'use client';

import { useState, useEffect, useRef } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { getCurrentUser, isAuthenticated } from '../../utils/auth';
import { authenticatedFetch } from '../../utils/api';

import { Suspense } from 'react';

function MessagesContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const initialConnectionId = searchParams.get('connectionId');

  const [user, setUser] = useState(null);
  const [mounted, setMounted] = useState(false);
  
  const [conversations, setConversations] = useState([]);
  const [loadingConv, setLoadingConv] = useState(true);
  
  const [activeConnectionId, setActiveConnectionId] = useState(null);
  const [activeChatUser, setActiveChatUser] = useState(null);
  const [messages, setMessages] = useState([]);
  const [loadingMessages, setLoadingMessages] = useState(false);
  
  const [messageInput, setMessageInput] = useState('');
  const [sending, setSending] = useState(false);
  
  const messagesEndRef = useRef(null);
  const pollingInterval = useRef(null);

  useEffect(() => {
    setMounted(true);
    if (!isAuthenticated()) {
      router.push('/auth');
      return;
    }
    const currentUser = getCurrentUser();
    setUser(currentUser);
    if (currentUser) {
      fetchConversations();
    }
    
    return () => {
       if (pollingInterval.current) clearInterval(pollingInterval.current);
    }
  }, [router]);

  useEffect(() => {
    if (initialConnectionId && conversations.length > 0 && !activeConnectionId) {
       selectConversation(initialConnectionId);
    }
  }, [initialConnectionId, conversations]);

  const fetchConversations = async () => {
    try {
      const res = await authenticatedFetch('/api/messages/conversations');
      if (res.ok) {
        const data = await res.json();
        setConversations(data);
      }
    } catch (err) {
      console.error("Failed to fetch conversations", err);
    } finally {
      setLoadingConv(false);
    }
  };

  const selectConversation = async (connectionId) => {
    setActiveConnectionId(connectionId);
    setLoadingMessages(true);
    
    // Find the user info from conversations list or fetch it
    const conv = conversations.find(c => c.connection_id === parseInt(connectionId));
    if (conv) {
        setActiveChatUser(conv.receiver_name);
    } else {
        setActiveChatUser("Loading...");
    }

    await loadMessages(connectionId);
    setLoadingMessages(false);
    
    if (pollingInterval.current) clearInterval(pollingInterval.current);
    pollingInterval.current = setInterval(() => loadMessages(connectionId, false), 5000);
  };

  const loadMessages = async (connectionId, scrollToBottom = true) => {
    try {
      const res = await authenticatedFetch(`/api/messages/conversation/${connectionId}`);
      if (res.ok) {
        const data = await res.json();
        setMessages(data);
        if (scrollToBottom) {
            setTimeout(() => {
                messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
            }, 100);
        }
      }
    } catch (err) {
      console.error("Failed to load messages", err);
    }
  };

  const sendMessage = async (e) => {
    e.preventDefault();
    if (!messageInput.trim() || !activeConnectionId) return;

    setSending(true);
    try {
      const res = await authenticatedFetch('/api/messages', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          connection_id: activeConnectionId,
          content: messageInput.trim()
        })
      });

      if (res.ok) {
        setMessageInput('');
        await loadMessages(activeConnectionId);
        // Update conversation list to bump recent message
        fetchConversations();
      } else {
        alert("Failed to send message");
      }
    } catch (err) {
      alert("Error: " + err.message);
    } finally {
      setSending(false);
    }
  };
  
  const closeChat = () => {
      setActiveConnectionId(null);
      if (pollingInterval.current) clearInterval(pollingInterval.current);
  };

  if (!mounted || !user) {
    return <div className="loading-container"><div className="loading-spinner"></div></div>;
  }

  return (
    <div style={{display: 'flex', height: 'calc(100vh - 70px)', background: '#f8fafc', overflow: 'hidden'}}>
        {/* Sidebar */}
        <div style={{width: activeConnectionId ? '350px' : '100%', maxWidth: '350px', background: '#fff', borderRight: '1px solid #e2e8f0', display: activeConnectionId ? 'none' : 'flex', display: 'flex', flexDirection: 'column'}}>
           <div style={{padding: '20px', borderBottom: '1px solid #e2e8f0', display: 'flex', justifyContent: 'space-between', alignItems: 'center'}}>
               <h2 style={{fontSize: '1.25rem', fontWeight: 600, margin: 0}}>Messages</h2>
           </div>
           
           <div style={{flex: 1, overflowY: 'auto'}}>
               {loadingConv ? (
                   <div style={{padding: '20px', textAlign: 'center', color: '#64748b'}}>Loading conversations...</div>
               ) : conversations.length === 0 ? (
                   <div style={{padding: '40px 20px', textAlign: 'center', color: '#64748b'}}>
                       <p>No conversations yet.</p>
                       <p style={{fontSize: '0.85rem', marginTop: '8px'}}>Accept a connection request to start messaging.</p>
                   </div>
               ) : (
                   conversations.map(conv => (
                       <div 
                         key={conv.connection_id}
                         onClick={() => selectConversation(conv.connection_id)}
                         style={{padding: '20px', borderBottom: '1px solid #f1f5f9', cursor: 'pointer', background: activeConnectionId == conv.connection_id ? '#f8fafc' : '#fff', transition: 'background 0.2s'}}
                       >
                          <div style={{display: 'flex', justifyContent: 'space-between', marginBottom: '4px'}}>
                              <strong style={{color: '#1e293b'}}>{conv.receiver_name}</strong>
                          </div>
                          <div style={{color: '#64748b', fontSize: '0.9rem', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis'}}>
                              {conv.last_message || 'Start chatting...'}
                          </div>
                       </div>
                   ))
               )}
           </div>
        </div>

        {/* Main Chat Area */}
        <div style={{flex: 1, display: activeConnectionId ? 'flex' : 'none', flexDirection: 'column', background: '#f1f5f9'}}>
            {activeConnectionId ? (
                <>
                    {/* Chat Header */}
                    <div style={{padding: '20px', background: '#fff', borderBottom: '1px solid #e2e8f0', display: 'flex', alignItems: 'center', justifyContent: 'space-between', boxShadow: '0 1px 3px rgba(0,0,0,0.05)', zIndex: 10}}>
                        <div style={{display: 'flex', alignItems: 'center', gap: '12px'}}>
                            <button onClick={closeChat} style={{background: 'none', border: 'none', fontSize: '1.5rem', cursor: 'pointer', display: 'none', color: '#64748b'}}>&larr;</button>
                            <h3 style={{margin: 0, fontSize: '1.1rem'}}>{activeChatUser}</h3>
                        </div>
                    </div>

                    {/* Messages List */}
                    <div style={{flex: 1, overflowY: 'auto', padding: '24px', display: 'flex', flexDirection: 'column', gap: '16px'}}>
                        {loadingMessages ? (
                            <div style={{textAlign: 'center', padding: '20px', color: '#64748b'}}>Loading messages...</div>
                        ) : messages.length === 0 ? (
                            <div style={{textAlign: 'center', padding: '40px', color: '#64748b'}}>
                                <p>No messages yet.</p>
                                <p style={{fontSize: '0.85rem'}}>Send a message to start the conversation.</p>
                            </div>
                        ) : (
                            messages.map(msg => {
                                const isMe = msg.sender_id === user.user_id;
                                return (
                                    <div key={msg.id} style={{alignSelf: isMe ? 'flex-end' : 'flex-start', maxWidth: '70%'}}>
                                        <div style={{
                                            padding: '12px 16px', 
                                            borderRadius: '16px', 
                                            borderBottomRightRadius: isMe ? '4px' : '16px',
                                            borderBottomLeftRadius: !isMe ? '4px' : '16px',
                                            background: isMe ? 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' : '#fff',
                                            color: isMe ? '#fff' : '#1e293b',
                                            boxShadow: '0 2px 4px rgba(0,0,0,0.05)',
                                            fontSize: '0.95rem',
                                            lineHeight: '1.5'
                                        }}>
                                            {msg.content}
                                        </div>
                                        <div style={{fontSize: '0.75rem', color: '#94a3b8', marginTop: '4px', textAlign: isMe ? 'right' : 'left'}}>
                                            {new Date(msg.created_at).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}
                                        </div>
                                    </div>
                                )
                            })
                        )}
                        <div ref={messagesEndRef} />
                    </div>

                    {/* Chat Input */}
                    <div style={{padding: '20px', background: '#fff', borderTop: '1px solid #e2e8f0'}}>
                        <form onSubmit={sendMessage} style={{display: 'flex', gap: '12px'}}>
                            <input 
                                type="text"
                                value={messageInput}
                                onChange={e => setMessageInput(e.target.value)}
                                placeholder="Type a message..."
                                style={{flex: 1, padding: '14px', borderRadius: '24px', border: '1px solid #cbd5e1', background: '#f8fafc', outline: 'none', transition: 'border 0.2s'}}
                                required
                            />
                            <button 
                                type="submit" 
                                disabled={sending || !messageInput.trim()}
                                style={{
                                    width: '48px', height: '48px', borderRadius: '50%', background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)', color: 'white', border: 'none', display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: (sending || !messageInput.trim()) ? 'not-allowed' : 'pointer', opacity: (sending || !messageInput.trim()) ? 0.7 : 1, transition: 'transform 0.2s'
                                }}
                            >
                                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                    <line x1="22" y1="2" x2="11" y2="13"></line>
                                    <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
                                </svg>
                            </button>
                        </form>
                    </div>
                </>
            ) : (
                <div style={{flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', color: '#94a3b8'}}>
                    <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{marginBottom: '16px'}}>
                        <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
                    </svg>
                    <h3 style={{fontSize: '1.25rem', margin: '0 0 8px 0', color: '#64748b'}}>Select a conversation</h3>
                    <p style={{margin: 0}}>Choose a connection from the list to start messaging.</p>
                </div>
            )}
        </div>
    </div>
  );
}

export default function Messages() {
    return (
        <Suspense fallback={<div className="loading-container"><div className="loading-spinner"></div></div>}>
            <MessagesContent />
        </Suspense>
    );
}
