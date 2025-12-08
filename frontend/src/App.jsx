import './App.css'
import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom'
import Login from './pages/Login'
import Chat from './pages/Chat'
import Profile from './pages/Profile'
import { useAuth } from './context/AuthContext.jsx'

function LoadingScreen() {
  return (
    <div className="full-screen-background" style={{ justifyContent: 'center', alignItems: 'center', display: 'flex' }}>
      <p style={{ color: 'white' }}>Loading…</p>
    </div>
  )
}

function RequireAuth({ children }) {
  const { user, loading } = useAuth()
  const location = useLocation()
  if (loading) return <LoadingScreen />
  if (!user) return <Navigate to="/" replace state={{ from: location }} />
  return children
}

function AuthRoute({ children }) {
  const { user, loading } = useAuth()
  if (loading) return <LoadingScreen />
  if (user) return <Navigate to="/chat" replace />
  return children
}

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route
          path="/"
          element={(
            <AuthRoute>
              <Login />
            </AuthRoute>
          )}
        />
        <Route
          path="/chat"
          element={(
            <RequireAuth>
              <Chat />
            </RequireAuth>
          )}
        />
        <Route
          path="/chat/:chatId"
          element={(
            <RequireAuth>
              <Chat />
            </RequireAuth>
          )}
        />
        <Route
          path="/profile"
          element={(
            <RequireAuth>
              <Profile />
            </RequireAuth>
          )}
        />
        <Route path="*" element={<Navigate to="/chat" replace />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App