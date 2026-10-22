import React, { useState, useEffect, useRef } from 'react';
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
  if (msg.includes('auth/invalid-email')) {
    return 'Please enter a valid email address.';
  }
  if (msg.includes('auth/configuration-not-found') || msg.includes('CONFIGURATION_NOT_FOUND')) {
    return 'Firebase Authentication is not yet enabled in the Firebase Console. Please enable Email/Password under Authentication -> Sign-in method.';
  }
  if (msg.includes('auth/too-many-requests')) {
    return 'Access temporarily blocked due to multiple failed login attempts. Please try again later or reset your password.';
  }
  if (msg.includes('auth/network-request-failed')) {
    return 'Network connection issue. Please check your internet connection.';
  }
  return msg || 'Authentication failed. Please check your network and credentials.';
}

export default function AuthModal({ isOpen, onClose, demoUsers, onLoginSuccess }) {
  const [mode, setMode] = useState('signin'); // 'signin' | 'signup' | 'reset'
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [successMsg, setSuccessMsg] = useState('');

  const emailInputRef = useRef(null);

  // Focus input and handle Escape key
  useEffect(() => {
    if (!isOpen) return;

    const timer = setTimeout(() => {
      emailInputRef.current?.focus();
    }, 60);

    function handleKeyDown(e) {
      if (e.key === 'Escape') {
        onClose();
      }
    }

    window.addEventListener('keydown', handleKeyDown);
    return () => {
      clearTimeout(timer);
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [isOpen, mode, onClose]);

  if (!isOpen) return null;

  function switchMode(newMode) {
    setMode(newMode);
    setError('');
    setSuccessMsg('');
    setPassword('');
    setConfirmPassword('');
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError('');
    setSuccessMsg('');

    // Validation
    const cleanEmail = email.trim();
    if (!cleanEmail) {
      setError('Please enter your email address.');
      return;
    }

    if (mode === 'signup') {
      if (password.length < 6) {
        setError('Password must be at least 6 characters.');
        return;
      }
      if (password !== confirmPassword) {
        setError('Passwords do not match. Please re-enter your password.');
        return;
      }
    }

    if (mode === 'signin' && !password) {
      setError('Please enter your password.');
      return;
    }

    setLoading(true);

    try {
      if (mode === 'reset') {
        await resetPassword(cleanEmail);
        setSuccessMsg(`Password reset link sent to ${cleanEmail}. Check your inbox.`);
        setLoading(false);
        return;
      }

      let userObj;
      if (mode === 'signup') {
        userObj = await registerWithEmail(cleanEmail, password);
      } else {
        userObj = await loginWithEmail(cleanEmail, password);
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
    <div
      className="modal-backdrop"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
      role="presentation"
    >
      <div
        className="modal-card"
        role="dialog"
        aria-modal="true"
        aria-labelledby="auth-modal-title"
      >
        <div className="modal-header">
          <div className="modal-header-titles">
            <div className="auth-brand-badge" aria-hidden="true">
              🛡️
            </div>
            <h2 id="auth-modal-title">
              {mode === 'signup' && 'Create BrandGuard Account'}
              {mode === 'signin' && 'Sign in to BrandGuard AI'}
              {mode === 'reset' && 'Reset Your Password'}
            </h2>
            <p className="modal-subtitle">
              {mode === 'signup' && 'Register your workspace credentials for AI brand governance.'}
              {mode === 'signin' && 'Enter your workspace credentials to access governance tools.'}
              {mode === 'reset' && 'Enter your registered email to receive reset instructions.'}
            </p>
          </div>
          <button
            type="button"
            className="modal-close-btn"
            onClick={onClose}
            aria-label="Close authentication modal"
            title="Close (Esc)"
          >
            ✕
          </button>
        </div>

        <div className="firebase-status-banner">
          {isFirebaseConfigured ? (
            <span className="badge-online">Live Firebase Auth Connected (brandguard-ai-techwithmujju)</span>
          ) : (
            <span className="badge-dev">Developer Mode (Live Firebase Auth Not Configured)</span>
          )}
        </div>

        {mode !== 'reset' && (
          <div className="auth-mode-tabs" role="tablist" aria-label="Authentication modes">
            <button
              type="button"
              role="tab"
              aria-selected={mode === 'signin'}
              className={`auth-tab-btn ${mode === 'signin' ? 'active' : ''}`}
              onClick={() => switchMode('signin')}
            >
              Sign In
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={mode === 'signup'}
              className={`auth-tab-btn ${mode === 'signup' ? 'active' : ''}`}
              onClick={() => switchMode('signup')}
            >
              Create Account
            </button>
          </div>
        )}

        {error && (
          <div className="auth-alert error" role="alert">
            <span className="auth-alert-icon" aria-hidden="true">⚠️</span>
            <span>{error}</span>
          </div>
        )}

        {successMsg && (
          <div className="auth-alert success" role="status">
            <span className="auth-alert-icon" aria-hidden="true">✓</span>
            <span>{successMsg}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="auth-form" noValidate>
          <div className="auth-field-group">
            <div className="auth-label-row">
              <label htmlFor="auth-email-input" className="auth-label">
                Email Address
              </label>
            </div>
            <div className="auth-input-wrapper">
              <input
                id="auth-email-input"
                ref={emailInputRef}
                type="email"
                required
                autoComplete="email"
                placeholder="name@company.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className={`auth-input ${error && !email ? 'has-error' : ''}`}
                disabled={loading}
              />
            </div>
          </div>

          {mode !== 'reset' && (
            <div className="auth-field-group">
              <div className="auth-label-row">
                <label htmlFor="auth-password-input" className="auth-label">
                  Password
                </label>
                {mode === 'signin' && (
                  <button
                    type="button"
                    className="btn-link-forgot"
                    onClick={() => switchMode('reset')}
                  >
                    Forgot password?
                  </button>
                )}
              </div>
              <div className="auth-input-wrapper">
                <input
                  id="auth-password-input"
                  type={showPassword ? 'text' : 'password'}
                  required
                  autoComplete={mode === 'signup' ? 'new-password' : 'current-password'}
                  minLength={6}
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className={`auth-input auth-input-with-action ${error && !password ? 'has-error' : ''}`}
                  disabled={loading}
                />
                <button
                  type="button"
                  className="auth-input-action-btn"
                  onClick={() => setShowPassword(!showPassword)}
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                  title={showPassword ? 'Hide password' : 'Show password'}
                  tabIndex={0}
                >
                  {showPassword ? (
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                      <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path>
                      <line x1="1" y1="1" x2="23" y2="23"></line>
                    </svg>
                  ) : (
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
                      <circle cx="12" cy="12" r="3"></circle>
                    </svg>
                  )}
                </button>
              </div>
            </div>
          )}

          {mode === 'signup' && (
            <div className="auth-field-group">
              <div className="auth-label-row">
                <label htmlFor="auth-confirm-password-input" className="auth-label">
                  Confirm Password
                </label>
              </div>
              <div className="auth-input-wrapper">
                <input
                  id="auth-confirm-password-input"
                  type={showConfirmPassword ? 'text' : 'password'}
                  required
                  autoComplete="new-password"
                  minLength={6}
                  placeholder="••••••••"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  className={`auth-input auth-input-with-action ${error && confirmPassword && confirmPassword !== password ? 'has-error' : ''}`}
                  disabled={loading}
                />
                <button
                  type="button"
                  className="auth-input-action-btn"
                  onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                  aria-label={showConfirmPassword ? 'Hide confirm password' : 'Show confirm password'}
                  title={showConfirmPassword ? 'Hide confirm password' : 'Show confirm password'}
                  tabIndex={0}
                >
                  {showConfirmPassword ? (
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                      <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path>
                      <line x1="1" y1="1" x2="23" y2="23"></line>
                    </svg>
                  ) : (
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
                      <circle cx="12" cy="12" r="3"></circle>
                    </svg>
                  )}
                </button>
              </div>
              <span className="auth-field-hint">Must be at least 6 characters.</span>
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="btn-primary auth-submit-btn"
          >
            {loading && <span className="auth-spinner" aria-hidden="true"></span>}
            <span>
              {loading ? (
                mode === 'signup' ? 'Creating Account...' :
                mode === 'reset' ? 'Sending Link...' : 'Signing In...'
              ) : (
                mode === 'signup' ? 'Create Account' :
                mode === 'reset' ? 'Send Reset Link' : 'Sign In'
              )}
            </span>
          </button>
        </form>

        <div className="auth-toggle-mode">
          {mode === 'signup' && (
            <p>
              Already have an account?{' '}
              <button
                type="button"
                className="auth-link-inline"
                onClick={() => switchMode('signin')}
              >
                Sign In
              </button>
            </p>
          )}
          {mode === 'signin' && (
            <p>
              New workspace member?{' '}
              <button
                type="button"
                className="auth-link-inline"
                onClick={() => switchMode('signup')}
              >
                Create Account
              </button>
            </p>
          )}
          {mode === 'reset' && (
            <p>
              Remembered your password?{' '}
              <button
                type="button"
                className="auth-link-inline"
                onClick={() => switchMode('signin')}
              >
                Back to Sign In
              </button>
            </p>
          )}
        </div>

        {demoUsers && demoUsers.length > 0 && (
          <div className="demo-accounts-section">
            <div className="divider-text">
              <span>DEVELOPER EVALUATION IDENTITIES</span>
            </div>
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
