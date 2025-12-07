function AuthTabs({
  activeTab,
  onTabChange,
  onLoginSubmit,
  onSignupSubmit,
}) {
  const isLogin = activeTab === 'login'

  return (
    <div className="auth">
      {/* Tab buttons */}
      <div className="auth-tabs" role="tablist" aria-label="Authentication">
        <button
          type="button"
          className={`auth-tab ${isLogin ? 'active' : ''}`}
          id="loginTab"
          aria-controls="loginPanel"
          aria-selected={isLogin}
          onClick={() => onTabChange('login')}
        >
          Log In
        </button>
        <button
          type="button"
          className={`auth-tab ${!isLogin ? 'active' : ''}`}
          id="signupTab"
          aria-controls="signupPanel"
          aria-selected={!isLogin}
          onClick={() => onTabChange('signup')}
        >
          Sign Up
        </button>
      </div>

      {/* Login panel */}
      <div
        className={`auth-panel ${isLogin ? '' : 'hidden'}`}
        id="loginPanel"
        role="tabpanel"
        aria-labelledby="loginTab"
      >
        <form onSubmit={onLoginSubmit}>
          <input type="email" placeholder="Email" required />
          <input type="password" placeholder="Password" required />
          <button type="submit">Log In</button>
        </form>
      </div>

      {/* Sign up panel */}
      <div
        className={`auth-panel ${!isLogin ? '' : 'hidden'}`}
        id="signupPanel"
        role="tabpanel"
        aria-labelledby="signupTab"
      >
        <form onSubmit={onSignupSubmit}>
          <input type="text" placeholder="Username" required />
          <input type="email" placeholder="Email" required />
          <input type="password" placeholder="Password" required />
          <button type="submit">Create Account</button>
        </form>
      </div>
    </div>
  )
}

export default AuthTabs