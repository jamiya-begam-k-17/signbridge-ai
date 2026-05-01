import React, { useState, useEffect, useRef } from 'react';
import { getMessages, sendMessage } from '../services/api';
import { useAuth } from '../context/AuthContext';
import './Chat.css';

const Chat = ({ conversation }) => {
  const [messages, setMessages] = useState([]);
  const [newMessage, setNewMessage] = useState('');
  const [loading, setLoading] = useState(true);
  const messagesEndRef = useRef(null);
  const { user } = useAuth();

  useEffect(() => {
    if (conversation) {
      loadMessages();
    }
  }, [conversation]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const loadMessages = async () => {
    try {
      const msgs = await getMessages(conversation.id);
      setMessages(msgs);
    } catch (error) {
      console.error('Failed to load messages:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSendMessage = async () => {
    if (!newMessage.trim()) return;
    try {
      const sentMessage = await sendMessage(conversation.id, newMessage);
      setMessages([...messages, sentMessage]);
      setNewMessage('');
    } catch (error) {
      console.error('Failed to send message:', error);
    }
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  if (!conversation) return <div>Select a conversation to start chatting</div>;

  if (loading) return <div>Loading messages...</div>;

  return (
    <div className="chat">
      <div className="chat-header">
        <h3>Chat with {conversation.teacher_id === user?.id ? 'Student' : 'Teacher'}</h3>
      </div>
      <div className="messages">
        {messages.map(msg => (
          <div key={msg.id} className={`message ${msg.sender_id === user?.id ? 'own' : 'other'}`}>
            <div className="message-content">{msg.content}</div>
            <div className="message-time">
              {new Date(msg.timestamp).toLocaleTimeString()}
            </div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>
      <div className="message-input">
        <input
          type="text"
          value={newMessage}
          onChange={(e) => setNewMessage(e.target.value)}
          onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
          placeholder="Type a message..."
        />
        <button onClick={handleSendMessage}>Send</button>
      </div>
    </div>
  );
};

export default Chat;