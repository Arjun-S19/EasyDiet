const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

async function request(path, { method = 'GET', body, session } = {}) {
  const headers = { 'Content-Type': 'application/json' }
  if (session?.access_token) {
    headers.Authorization = `Bearer ${session.access_token}`
  }

  const response = await fetch(`${API_BASE}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  })

  if (!response.ok) {
    const text = await response.text()
    throw new Error(text || 'Request failed')
  }
  return response.json()
}

export const api = {
  getProfile: (session) => request('/api/profile', { session }),
  updateProfile: (session, payload) => request('/api/profile', { method: 'PUT', session, body: payload }),
  listConversations: (session) => request('/api/conversations', { session }),
  createConversation: (session, payload) => request('/api/conversations', { method: 'POST', session, body: payload }),
  deleteConversation: (session, conversationId) => request(`/api/conversations/${conversationId}`, { method: 'DELETE', session }),
  getMessages: (session, conversationId) => request(`/api/conversations/${conversationId}/messages`, { session }),
  sendMessage: (session, payload) => request('/api/chat', { method: 'POST', session, body: payload }),
}
