import React, { useState } from 'react';
import { isFirebaseConfigured, loginWithEmail, registerWithEmail, loginWithDemoIdentity } from '../firebase';

export default function AuthModal({ isOpen, onClose, demoUsers, onLoginSuccess }) {
  const [isSignUp, setIsSignUp] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  if (!isOpen) return null;

  async function handleSubmit(e) {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      let userObj;
      if (isSignUp) {
        userObj = await registerWithEmail(email, password);
      } else {
        userObj = await loginWithEmail(email, password);
      }
      onLoginSuccess(userObj);
      onClose();
    } catch (err) {
      setError(err.message || 'Authentication failed. Please verify credentials.');
    } finally {
      setLoading(false);
    }
  }

  function handleDemoSelect(user) {
    loginWithDemoIdentity(user);
    onLoginSuccess(user);
    onClose();
  }

  return (
    <div className="modal-backdrop">
      <div className="modal-card">
        <div className="modal-header">
          <h2>{isSignUp ? 'Create BrandGuard Account' : 'Sign in to BrandGuard AI'}</h2>
          <button className="modal-close-btn" onClick={onClose}>✕</button>
        </div>

        <div className="firebase-status-banner">
          {isFirebaseConfigured ? (
            <span className="badge-online">● Firebase Auth Connected</span>
          ) : (
            <span className="badge-dev">⚡ Developer Mode (Firebase keys optional)</span>
          )}
        </div>

        {error && <div className="alert-box error">{error}</div>}

        <form onSubmit={handleSubmit} className="auth-form">
          <label>Email Address</label>
          <input
            type="email"
            required
            placeholder="name@company.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />

          <label>Password</label>
          <input
            type="password"
            required
            minLength={6}
            placeholder="••••••••"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />

          <button type="submit" disabled={loading} className="btn-primary auth-submit-btn">
            {loading ? 'Processing...' : (isSignUp ? 'Create Account' : 'Sign In')}
          </button>
        </form>

        <div className="auth-toggle-mode">
          {isSignUp ? (
            <p>Already have an account? <a href="#" onClick={(e) => { e.preventDefault(); setIsSignUp(false); }}>Sign In</a></p>
          ) : (
            <p>New workspace member? <a href="#" onClick={(e) => { e.preventDefault(); setIsSignUp(true); }}>Sign Up</a></p>
          )}
        </div>

        {demoUsers && demoUsers.length > 0 && (
          <div className="demo-accounts-section">
            <div className="divider-text"><span>OR FAST SIGN-IN WITH DEMO IDENTITIES</span></div>
            <div className="demo-users-grid">
              {demoUsers.map((u) => (
                <button
                  key={u.user_id}
                  type="button"
                  className="demo-user-card"
                  onClick={() => handleDemoSelect(u)}
                >
                  <div className="demo-user-info">
                    <strong>{u.display_name}</strong>
                    <span>{u.email}</span>
                  </div>
                  <span className={`role-badge role-${u.role}`}>
                    {u.role.toUpperCase()}
                  </span>
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
