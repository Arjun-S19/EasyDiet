import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import Navbar from '../components/Navbar'
import AuthTabs from '../components/AuthTabs'

function Login() {
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [activeAuthTab, setActiveAuthTab] = useState('login')
  const navigate = useNavigate()

  const handleLoginSubmit = (event) => {
    event.preventDefault()
    alert('Logged in (demo)')
    setIsAuthenticated(true)
    navigate('/home')   // ← redirect
  }

  const handleSignupSubmit = (event) => {
    event.preventDefault()
    alert('Account created (demo)')
    setIsAuthenticated(true)
    navigate('/home')   // ← redirect
  }

  return (
    <div className="full-screen-background">
      {/* show navbar before redirect if desired */}
      {isAuthenticated && <Navbar />}

      <main className="content">
        <div className="content-box">
          <h1>Easy Diet</h1>
          <p>Your new healthy diet is just <br />a few clicks away!</p>

          <AuthTabs
            activeTab={activeAuthTab}
            onTabChange={setActiveAuthTab}
            onLoginSubmit={handleLoginSubmit}
            onSignupSubmit={handleSignupSubmit}
          />
        </div>
      </main>
    </div>
  )
}

export default Login