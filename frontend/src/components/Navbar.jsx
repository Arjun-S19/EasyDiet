import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext.jsx'

function Navbar() {
  const { signOut, user } = useAuth()
  const navigate = useNavigate()

  const handleSignOut = async () => {
    await signOut()
    navigate('/')
  }

  return (
    <div className="navbar">
      <nav className="tabs">
        <Link to="/chat">Chat</Link>
        <Link to="/profile">Profile</Link>
      </nav>
      <div className="navbar-actions">
        <span className="navbar-user">{user?.email}</span>
        <button type="button" className="link-button" onClick={handleSignOut}>
          Sign Out
        </button>
      </div>
    </div>
  )
}

export default Navbar