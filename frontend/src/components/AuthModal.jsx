import React, { useState } from 'react';
import {
  isFirebaseConfigured,
  loginWithEmail,
  registerWithEmail,
  resetPassword,
  loginWithDemoIdentity
} from '../firebase';

function formatAuthError(err) {
  const msg = err.message || '';
  if (msg.includes('auth/invalid-credential') || msg.includes('auth/wrong-password')) {
    return 'Invalid email or password. Please verify your credentials.';
  }
  if (msg.includes('auth/user-not-found')) {
    return 'No account exists with this email address.';
  }
  if (msg.includes('auth/email-already-in-use')) {
    return 'An account is already registered with this email.';
  }
  if (msg.includes('auth/weak-password')) {
    return 'Password is too weak. Please use at least 6 characters.';
  }
  if (msg.includes('auth/configuration-not-found') || msg.includes('CONFIGURATION_NOT_FOUND')) {
    return 'Firebase Authentication is not yet enabled in the Firebase Console. Please enable Email/Password under Authentication -> Sign-in method.';
  }
  if (msg.includes('auth/too-many-requests')) {
    return 'Access temporarily blocked due to multiple failed login attempts. Please try again later or reset password.';
  }
  return msg || 'Authentication failed. Please check your network and credentials.';
}

export default function AuthModal({ isOpen, onClose, demoUsers, onLoginSuccess }) {
  const [mode, setMode] = useState('signin'); // 'signin' | 'signup' | 'reset'
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [successMsg, setSuccessMsg] = useState('');

  if (!isOpen) return null;

  async function handleSubmit(e) {
    e.preventDefault();
    setError('');
    setSuccessMsg('');
    setLoading(true);

    try {
      if (mode === 'reset') {
        await resetPassword(email);
        setSuccessMsg(`Password reset link sent to ${email}. Check your inbox.`);
        setLoading(false);
        return;
      }

      let userObj;
      if (mode === 'signup') {
        userObj = await registerWithEmail(email, password);
      } else {
        userObj = await loginWithEmail(email, password);
      }
      onLoginSuccess(userObj);
      onClose();
    } catch (err) {
      setError(formatAuthError(err));
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
          <h2>
            {mode === 'signup' && 'Create BrandGuard Account'}
            {mode === 'signin' && 'Sign in to BrandGuard AI'}
            {mode === 'reset' && 'Reset Your Password'}
          </h2>
          <button className="modal-close-btn" onClick={onClose}>✕</button>
        </div>

        <div className="firebase-status-banner">
          {isFirebaseConfigured ? (
            <span className="badge-online">● Live Firebase Auth Connected (brandguard-ai-techwithmujju)</span>
          ) : (
            <span className="badge-dev">⚡ Developer Mode (Firebase keys optional)</span>
          )}
        </div>

        {error && <div className="alert-box error">{error}</div>}
        {successMsg && <div className="alert-box success">{successMsg}</div>}

        <form onSubmit={handleSubmit} className="auth-form">
          <label>Email Address</label>
          <input
            type="email"
            required
            placeholder="name@company.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />

          {mode !== 'reset' && (
            <>
              <div className="label-with-action">
                <label>Password</label>
                {mode === 'signin' && (
                  <button
                    type="button"
                    className="btn-link-forgot"
                    onClick={() => { setMode('reset'); setError(''); setSuccessMsg(''); }}
                  >
                    Forgot password?
                  </button>
                )}
              </div>
              <input
                type="password"
                required
                minLength={6}
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </>
          )}

          <button type="submit" disabled={loading} className="btn-primary auth-submit-btn">
            {loading ? 'Processing...' : (
              mode === 'signup' ? 'Create Account' :
              mode === 'reset' ? 'Send Reset Link' : 'Sign In'
            )}
          </button>
        </form>

        <div className="auth-toggle-mode">
          {mode === 'signup' && (
            <p>Already have an account? <a href="#" onClick={(e) => { e.preventDefault(); setMode('signin'); setError(''); }}>Sign In</a></p>
          )}
          {mode === 'signin' && (
            <p>New workspace member? <a href="#" onClick={(e) => { e.preventDefault(); setMode('signup'); setError(''); }}>Sign Up</a></p>
          )}
          {mode === 'reset' && (
            <p>Remembered your password? <a href="#" onClick={(e) => { e.preventDefault(); setMode('signin'); setError(''); }}>Back to Sign In</a></p>
          )}
        </div>

        {demoUsers && demoUsers.length > 0 && (
          <div className="demo-accounts-section">
            <div className="divider-text"><span>DEVELOPER EVALUATION IDENTITIES</span></div>
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
