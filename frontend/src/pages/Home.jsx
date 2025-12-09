import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import Navbar from '../components/Navbar'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext.jsx'

function formatDate(value) {
  if (!value) return ''
  try {
    return new Date(value).toLocaleString()
  } catch (error) {
    return value
  }
}

function Home() {
  const { session } = useAuth()
  const [conversations, setConversations] = useState([])
  const [status, setStatus] = useState('loading')
  const navigate = useNavigate()

  const loadConversations = useCallback(async () => {
    if (!session) return
    setStatus('loading')
    try {
      const list = await api.listConversations(session)
      setConversations(list)
      setStatus('idle')
    } catch (error) {
      setStatus(error.message)
    }
  }, [session])

  useEffect(() => {
    loadConversations()
  }, [loadConversations])

  const handleNewChat = async () => {
    if (!session) return
    try {
      const conversation = await api.createConversation(session, {})
      navigate(`/chat/${conversation.id}`)
    } catch (error) {
      setStatus(error.message)
    }
  }

  const handleDelete = async (conversationId) => {
    if (!session) return
    try {
      await api.deleteConversation(session, conversationId)
      setConversations((prev) => prev.filter((c) => c.id !== conversationId))
    } catch (error) {
      setStatus(error.message)
    }
  }

  return (
    <div className="full-screen-background">
      <Navbar />

      <main className="content">
        <div className="content-box home-box">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <h2 style={{ color: 'rgb(0, 0, 0)' }}>Welcome back</h2>
              <p>Pick up where you left off, or start a new chat.</p>
            </div>
            <button type="button" className="primary-button" onClick={handleNewChat}>New Chat</button>
          </div>

          {status !== 'idle' && status !== 'loading' && (
            <p style={{ color: 'red' }}>{status}</p>
          )}

          <ul className="chats-list">
            {conversations.map((chat) => (
              <li key={chat.id} className="chats-list-item">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <Link to={`/chat/${chat.id}`} style={{ flex: 1 }}>
                    <div className="chat-list-title">{chat.title || 'Conversation'}</div>
                    <div className="chat-list-snippet">{chat.last_message_preview || 'No messages yet'}</div>
                    <div className="chat-list-meta">{formatDate(chat.updated_at)}</div>
                  </Link>
                  <button type="button" className="link-button link-button-dark" onClick={() => handleDelete(chat.id)}>
                    Delete
                  </button>
                </div>
              </li>
            ))}
            {status === 'loading' && <li>Loading conversations…</li>}
            {!conversations.length && status === 'idle' && <li>No conversations yet.</li>}
          </ul>
        </div>
      </main>
    </div>
  )
}

export default Home