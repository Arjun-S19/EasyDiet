import { useState } from 'react'
import Navbar from '../components/Navbar'

function Profile() {
  const [form, setForm] = useState({
    name: '',
    email: '',
    height: '',
    weight: '',
    dob: '',
    goal: '',
  })

  const handleChange = (event) => {
    const { name, value } = event.target
    setForm((prev) => ({ ...prev, [name]: value }))
  }

  const handleSubmit = (event) => {
    event.preventDefault()
    alert('Profile saved (demo)')
  }

  return (
    <div className="full-screen-background">
      <Navbar />

      <main className="content">
        <div className="content-box profile-box">
          <form onSubmit={handleSubmit}>
            <label>Name</label>
            <input
              type="text"
              name="name"
              placeholder="Enter your name"
              value={form.name}
              onChange={handleChange}
            />

            <label>Height (inches)</label>
            <input
              type="number"
              name="height"
              placeholder="Enter your height"
              value={form.height}
              onChange={handleChange}
            />

            <label>Weight (lbs)</label>
            <input
              type="number"
              name="weight"
              placeholder="Enter your weight"
              value={form.weight}
              onChange={handleChange}
            />

            <label>Date of Birth</label>
            <input
              type="date"
              name="dob"
              value={form.dob}
              onChange={handleChange}
            />

            <label>Health Goal</label>
            <select
              name="goal"
              value={form.goal}
              onChange={handleChange}
            >
              <option value="">Select…</option>
              <option value="lose">Lose weight</option>
              <option value="gain">Gain weight</option>
              <option value="maintain">Maintain weight</option>
            </select>

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