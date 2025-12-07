import { Link } from 'react-router-dom'

function Navbar() {
  return (
    <div className="navbar">
      <nav className="tabs">
        <Link to="/home">Home</Link>
        <Link to="/chat">Chat</Link>
        <Link to="/profile">Profile</Link>
        <Link to="/" className="active">Sign Out</Link>
      </nav>
    </div>
  )
}

export default Navbar