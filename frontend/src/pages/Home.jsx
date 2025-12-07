import { Link } from 'react-router-dom'
import Navbar from '../components/Navbar'

const mockChats = [
  {
    id: 1,
    lastMessage: 'Last Message',
    updatedAt: 'Today',
  },
]

function Home() {
  return (
    <div className="full-screen-background">
      <Navbar />

      <main className="content">
        <div className="content-box home-box">
          <h2>Welcome back</h2>
          <p>Pick up where you left off, or start a new chat at the top left.</p>

          <ul className="chats-list">
            {mockChats.map((chat) => (
              <li key={chat.id} className="chats-list-item">
                <Link to={`/chat/${chat.id}`}>
                  <div className="chat-list-snippet">{chat.lastMessage}</div>
                  <div className="chat-list-meta">{chat.updatedAt}</div>
                </Link>
              </li>
            ))}
          </ul>
        </div>
      </main>
    </div>
  )
}

export default Home