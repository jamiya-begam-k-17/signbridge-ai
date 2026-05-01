import React, { useState, useEffect } from 'react';
import { getConversations, createConversation, getUsers } from '../services/api';
import './ConversationList.css';

const ConversationList = ({ onSelectConversation }) => {
  const [conversations, setConversations] = useState([]);
  const [students, setStudents] = useState([]);
  const [selectedStudent, setSelectedStudent] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [convs, studs] = await Promise.all([getConversations(), getUsers()]);
      setConversations(convs);
      setStudents(studs);
    } catch (error) {
      console.error('Failed to load data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateConversation = async () => {
    if (!selectedStudent) return;
    try {
      const newConv = await createConversation(parseInt(selectedStudent));
      setConversations([...conversations, newConv]);
      setSelectedStudent('');
    } catch (error) {
      console.error('Failed to create conversation:', error);
    }
  };

  if (loading) return <div>Loading conversations...</div>;

  return (
    <div className="conversation-list">
      <h3>Conversations</h3>
      <div className="create-conversation">
        <select
          value={selectedStudent}
          onChange={(e) => setSelectedStudent(e.target.value)}
        >
          <option value="">Select Student</option>
          {students.map(student => (
            <option key={student.id} value={student.id}>{student.username}</option>
          ))}
        </select>
        <button onClick={handleCreateConversation} disabled={!selectedStudent}>
          Start Conversation
        </button>
      </div>
      <div className="conversations">
        {conversations.map(conv => (
          <div
            key={conv.id}
            className="conversation-item"
            onClick={() => onSelectConversation(conv)}
          >
            <div className="conversation-info">
              <span className="conversation-partner">
                {conv.teacher_id === 1 ? `Student ${conv.student_id}` : `Teacher ${conv.teacher_id}`}
              </span>
              <span className="conversation-date">
                {new Date(conv.created_at).toLocaleDateString()}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default ConversationList;