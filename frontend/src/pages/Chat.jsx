import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import Navbar from '../components/Navbar'

const defaultGreeting = [
  { id: 1, sender: 'ai', text: 'Hi! I’m your diet assistant. How can I help today?' },
]

const exampleConversationsById = {
  '1': [
    { id: 101, sender: 'ai', text: 'First Message' },
    { id: 102, sender: 'user', text: 'Second Message' },
    { id: 103, sender: 'ai', text: 'Last Message' },
  ]
}

function Chat() {
  const { chatId } = useParams() // undefined for /chat, string for /chat/:chatId
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')

  // load messages from chat ID
  useEffect(() => {
    if (chatId && exampleConversationsById[chatId]) {
      setMessages(exampleConversationsById[chatId])
    } else {
      setMessages(defaultGreeting)
    }
  }, [chatId])

  const handleSubmit = (event) => {
    event.preventDefault()
    const trimmed = input.trim()
    if (!trimmed) return

    const userMessage = {
      id: Date.now(),
      sender: 'user',
      text: trimmed,
    }

    const aiMessage = {
      id: Date.now() + 1,
      sender: 'ai',
      text: `test: "${trimmed}"`,
    }

    setMessages((prev) => [...prev, userMessage, aiMessage])
    setInput('')
  }

  return (
    <div className="full-screen-background">
      <Navbar />

      <main className="chat-page">
        <div className="chat-container">
          <h2>
            {chatId ? `Chat #${chatId}` : 'New Chat'}
          </h2>

          <div className="chat-messages">
            {messages.map((msg) => (
              <div
                key={msg.id}
                className={`chat-message chat-message-${msg.sender}`}
              >
                <div className="chat-bubble">{msg.text}</div>
              </div>
            ))}
          </div>

          <form className="chat-input-row" onSubmit={handleSubmit}>
            <input
              type="text"
              placeholder="Type your message..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
            />
            <button type="submit">Send</button>
          </form>
        </div>
      </main>
    </div>
  )
}

export default Chat