import { fireEvent, render, screen } from '@testing-library/react'
import AuthTabs from '../AuthTabs.jsx'

describe('AuthTabs', () => {
  it('switches between login and signup panels', () => {
    const noop = () => {}
    render(
      <AuthTabs
        activeTab="login"
        onTabChange={noop}
        onLoginSubmit={noop}
        onSignupSubmit={noop}
      />,
    )

    expect(screen.getByLabelText(/Authentication/i)).toBeInTheDocument()

    fireEvent.click(screen.getByText(/Sign Up/i))
    expect(screen.getByPlaceholderText(/Username/i)).toBeInTheDocument()
  })
})