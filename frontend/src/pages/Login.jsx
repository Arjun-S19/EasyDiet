import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import AuthTabs from '../components/AuthTabs'
import { useAuth } from '../context/AuthContext.jsx'

function Login() {
  const [activeAuthTab, setActiveAuthTab] = useState('login')
  const [feedback, setFeedback] = useState(null)
  const navigate = useNavigate()
  const { signIn, signUp } = useAuth()

  const handleLoginSubmit = async (event) => {
    event.preventDefault()
    const data = new FormData(event.currentTarget)
    const email = data.get('email')?.toString().trim()
    const password = data.get('password')?.toString().trim()
    if (!email || !password) return
    try {
      await signIn({ email, password })
      navigate('/home')
    } catch (error) {
      setFeedback(error.message)
    }
  }

  const handleSignupSubmit = async (event) => {
    event.preventDefault()
    const data = new FormData(event.currentTarget)
    const email = data.get('email')?.toString().trim()
    const password = data.get('password')?.toString().trim()
    const username = data.get('username')?.toString().trim()
    if (!email || !password) return
    try {
      const session = await signUp({ email, password, metadata: { username } })
      if (session) {
        navigate('/home')
      } else {
        setFeedback('Check your email to confirm your account.')
      }
    } catch (error) {
      setFeedback(error.message)
    }
  }

  return (
    <div className="full-screen-background">
      <main className="content">
        <div className="content-box">
          <h1>Easy Diet</h1>
          <p>Your new healthy diet is just <br />a few clicks away!</p>
          {feedback && <p style={{ color: 'red' }}>{feedback}</p>}
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