import { useCallback, useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import DOMPurify from 'dompurify'
import Navbar from '../components/Navbar'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext.jsx'

function normalizeMessages(history) {
  return (history || []).map((msg, index) => ({
    id: `${msg.role}-${index}`,
    sender: msg.role === 'user' ? 'user' : 'ai',
    text: msg.parts?.[0] || '',
  }))
}

function Chat() {
  const { chatId } = useParams()
  const navigate = useNavigate()
  const { session } = useAuth()
  const [messages, setMessages] = useState([])
  const [conversations, setConversations] = useState([])
  const [input, setInput] = useState('')
  const [status, setStatus] = useState('idle')
  const [sidebarLoading, setSidebarLoading] = useState(true)

  const loadConversations = useCallback(async () => {
    if (!session) return
    setSidebarLoading(true)
    try {
      const list = await api.listConversations(session)
      setConversations(list)
    } finally {
      setSidebarLoading(false)
    }
  }, [session])

  useEffect(() => {
    loadConversations()
  }, [loadConversations])

  const loadMessages = useCallback(async (conversationId) => {
    if (!session || !conversationId) return
    setStatus('loading')
    try {
      const history = await api.getMessages(session, conversationId)
      setMessages(normalizeMessages(history))
      setStatus('ready')
    } catch (error) {
      setStatus(error.message)
    }
  }, [session])

  useEffect(() => {
    if (chatId) {
      loadMessages(chatId)
    } else {
      setMessages([])
      setStatus('idle')
    }
  }, [chatId, loadMessages])

  const createConversation = useCallback(async (replace = false) => {
    if (!session) return null
    setStatus('creating')
    try {
      const conversation = await api.createConversation(session, {})
      await loadConversations()
      navigate(`/chat/${conversation.id}`, { replace })
      return conversation.id
    } catch (error) {
      setStatus(error.message)
      return null
    }
  }, [session, loadConversations, navigate])

  const handleSend = async (event) => {
    event.preventDefault()
    const trimmed = input.trim()
    if (!trimmed || !session) return
    const conversationId = chatId || (await createConversation(true))
    if (!conversationId) return

    const userMessage = { id: crypto.randomUUID?.() || Date.now(), sender: 'user', text: trimmed }
    setMessages((prev) => [...prev, userMessage])
    setInput('')
    setStatus('sending')

    try {
      const response = await api.sendMessage(session, {
        message: trimmed,
        conversation_id: conversationId,
      })
      await loadMessages(conversationId)
      if (response.conversation_id && response.conversation_id !== chatId) {
        navigate(`/chat/${response.conversation_id}`, { replace: true })
      }
      await loadConversations()
    } catch (error) {
      setStatus(error.message)
    }
  }

  const handleSelectConversation = (id) => {
    navigate(`/chat/${id}`)
  }

  const handleDeleteConversation = async (id) => {
    if (!session) return
    try {
      await api.deleteConversation(session, id)
      setConversations((prev) => prev.filter((c) => c.id !== id))
      if (id === chatId) {
        navigate('/chat', { replace: true })
      }
      await loadConversations()
    } catch (error) {
      setStatus(error.message)
    }
  }

  const currentTitle = useMemo(() => {
    const current = conversations.find((conv) => conv.id === chatId)
    return current?.title || 'New Chat'
  }, [conversations, chatId])

  const renderMessageBubble = (msg) => {
    if (msg.sender === 'ai') {
      return (
        <div
          className="chat-bubble chat-bubble-html"
          dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(msg.text) }}
        />
      )
    }
    return <div className="chat-bubble">{msg.text}</div>
  }

  return (
    <div className="full-screen-background">
      <Navbar />

      <main className="chat-page chat-layout">
        <aside className="chat-sidebar">
          <div className="chat-sidebar-header">
            <h3>Conversations</h3>
            <button type="button" className="primary-button" onClick={() => createConversation(false)}>
              New
            </button>
          </div>
          {sidebarLoading && <p>Loading…</p>}
          <ul>
            {conversations.map((conversation) => (
              <li key={conversation.id} className={conversation.id === chatId ? 'active' : ''}>
                <button
                  type="button"
                  className="conversation-link"
                  onClick={() => handleSelectConversation(conversation.id)}
                >
                  <div className="chat-list-title">{conversation.title || 'Conversation'}</div>
                  <div className="chat-list-snippet">{conversation.last_message_preview || 'No messages yet'}</div>
                </button>
                <button type="button" className="link-button" onClick={() => handleDeleteConversation(conversation.id)}>
                  Delete
                </button>
              </li>
            ))}
          </ul>
        </aside>

        <div className="chat-container">
          <h2>{currentTitle}</h2>
          {status !== 'ready' && status !== 'sending' && status !== 'idle' && status !== 'loading' && (
            <p style={{ color: 'red' }}>{status}</p>
          )}

          <div className="chat-messages">
            {messages.map((msg) => (
              <div key={msg.id} className={`chat-message chat-message-${msg.sender}`}>
                {renderMessageBubble(msg)}
              </div>
            ))}
            {!chatId && <p>Select a conversation or start a new one.</p>}
            {chatId && !messages.length && <p>No messages yet. Say hello!</p>}
          </div>

          <form className="chat-input-row" onSubmit={handleSend}>
            <input
              type="text"
              placeholder="Type your message..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
            />
            <button type="submit" disabled={status === 'sending'}>
              {status === 'sending' ? 'Sending…' : 'Send'}
            </button>
          </form>
        </div>
      </main>
    </div>
  )
}

export default Chat