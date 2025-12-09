import { useEffect, useState } from 'react'
import Navbar from '../components/Navbar'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext.jsx'

function Profile() {
  const { session } = useAuth()
  const [form, setForm] = useState({
    fitness_goals: '',
    dietary_restrictions: '',
  })
  const [status, setStatus] = useState('')

  useEffect(() => {
    async function loadProfile() {
      if (!session) return
      try {
        const profile = await api.getProfile(session)
        setForm({
          fitness_goals: profile.fitness_goals || '',
          dietary_restrictions: profile.dietary_restrictions || '',
        })
      } catch (error) {
        setStatus(error.message)
      }
    }
    loadProfile()
  }, [session])

  const handleChange = (event) => {
    const { name, value } = event.target
    setForm((prev) => ({ ...prev, [name]: value }))
  }

  const handleSubmit = async (event) => {
    event.preventDefault()
    if (!session) return
    try {
      await api.updateProfile(session, form)
      setStatus('Profile updated!')
    } catch (error) {
      setStatus(error.message)
    }
  }

  return (
    <div className="full-screen-background">
      <Navbar />

      <main className="content">
        <div className="content-box profile-box">
          <h2 style={{ color: 'black' }}>Nutrition Profile</h2>
          {status && <p>{status}</p>}
          <form onSubmit={handleSubmit}>
            <label style={{ color: 'rgb(0, 0, 0)' }}>Fitness Goals</label>
            <textarea
              name="fitness_goals"
              rows={3}
              placeholder="Lose weight, gain muscle, maintain weight..."
              value={form.fitness_goals}
              onChange={handleChange}
            />

            <label style={{ color: 'rgb(0, 0, 0)' }}>Dietary Restrictions</label>
            <textarea
              name="dietary_restrictions"
              rows={3}
              placeholder="Vegetarian, vegan, halal, allergies, etc."
              value={form.dietary_restrictions}
              onChange={handleChange}
            />

            <div className="button-container">
              <button type="submit">Save</button>
            </div>
          </form>
        </div>
      </main>
    </div>
  )
}

export default Profile