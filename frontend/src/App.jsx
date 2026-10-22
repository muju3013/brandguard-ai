import React, { useState, useEffect, useCallback } from 'react';
import { api } from './api';
import { subscribeToAuthState, logoutUser, loginWithDemoIdentity, isDemoAuthEnabled } from './firebase';

import Navbar from './components/Navbar';
import AuthModal from './components/AuthModal';
import DashboardView from './components/DashboardView';
import DraftsStudioView from './components/DraftsStudioView';
import ReviewerQueueView from './components/ReviewerQueueView';
import GuidelinesView from './components/GuidelinesView';
import AuditTrailView from './components/AuditTrailView';
import Phase1SandboxView from './components/Phase1SandboxView';

export default function App() {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(null);
  const [demoUsers, setDemoUsers] = useState([]);
  const [drafts, setDrafts] = useState([]);
  const [guidelines, setGuidelines] = useState([]);
  const [auditLogs, setAuditLogs] = useState([]);

  const [currentTab, setCurrentTab] = useState('dashboard');
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);
  const [isCreatingDraft, setIsCreatingDraft] = useState(false);

  const [loading, setLoading] = useState(true);
  const [globalError, setGlobalError] = useState('');

  // Fetch demo identities only if demo auth is enabled
  useEffect(() => {
    if (isDemoAuthEnabled) {
      api.fetchDemoUsers()
        .then((data) => setDemoUsers(data))
        .catch((err) => console.warn('Could not load demo users:', err));
    } else {
      setDemoUsers([]);
    }
  }, []);

  // Refresh workspace data
  const loadWorkspaceData = useCallback(async (authToken, fallbackUser = null) => {
    if (!authToken) return;
    setGlobalError('');

    try {
      // 1. Authoritative server-side profile fetch
      const profileData = await api.fetchProfile(authToken);
      const authenticatedUser = {
        ...(fallbackUser || {}),
        ...profileData,
        token: authToken
      };
      setUser(authenticatedUser);

      // 2. Fetch role-appropriate workspace resources using Promise.allSettled
      // Prevents 403 on non-admin users from breaking the entire application
      const isUserAdmin = profileData.role === 'admin';
      const [draftsRes, guidelinesRes, auditRes] = await Promise.allSettled([
        api.fetchDrafts(authToken),
        api.fetchGuidelines(authToken),
        isUserAdmin ? api.fetchAuditLogs(authToken) : Promise.resolve([])
      ]);

      if (draftsRes.status === 'fulfilled') {
        setDrafts(draftsRes.value || []);
      } else {
        console.warn('Failed to load drafts:', draftsRes.reason);
      }

      if (guidelinesRes.status === 'fulfilled') {
        setGuidelines(guidelinesRes.value || []);
      } else {
        console.warn('Failed to load guidelines:', guidelinesRes.reason);
      }

      if (auditRes.status === 'fulfilled') {
        setAuditLogs(auditRes.value || []);
      } else {
        console.warn('Failed to load audit logs:', auditRes.reason);
      }
    } catch (err) {
      console.error('Failed to load workspace data:', err);

      // Ensure the navbar retains the authenticated identity if Firebase login succeeded
      if (fallbackUser) {
        setUser((prev) => prev || fallbackUser);
      }

      // Distinguish exact error categories per Task 10
      if (err.isNetworkError || err.status === 0) {
        setGlobalError(
          `Network Error: Cannot connect to BrandGuard API at ${api.getBaseUrl()}. The backend service is currently offline or waking up.`
        );
      } else if (err.status === 401) {
        setGlobalError('Session Expired: Your authentication token is invalid or expired. Please sign in again.');
      } else if (err.status === 403) {
        setGlobalError('Access Denied: Your account role does not have authorization for this resource.');
      } else if (err.status === 404) {
        setGlobalError('Account Not Found: No organization membership exists in Firestore for your account.');
      } else if (err.status === 503) {
        setGlobalError('Backend Unavailable (503): Database or authentication credentials temporarily unreachable.');
      } else {
        setGlobalError(err.message || 'Error connecting to BrandGuard backend.');
      }
    }
  }, []);

  // Listen to auth changes
  useEffect(() => {
    const unsubscribe = subscribeToAuthState(async (authUser) => {
      setLoading(true);
      if (authUser?.token) {
        const baseUser = {
          user_id: authUser.uid || authUser.user_id,
          email: authUser.email,
          role: authUser.role || 'creator',
          org_name: authUser.org_name || 'BrandGuard Workspace',
          token: authUser.token,
          mode: authUser.mode
        };
        setUser((prev) => prev || baseUser);
        setToken(authUser.token);
        await loadWorkspaceData(authUser.token, baseUser);
      } else {
        // In development / demo mode, default to the seeded demo Creator for instant hands-on testing
        if (isDemoAuthEnabled) {
          try {
            const demos = await api.fetchDemoUsers();
            if (demos && demos.length > 0) {
              const defaultDemo = demos[2] || demos[0]; // Jordan Creator
              await loginWithDemoIdentity(defaultDemo);
              setToken(defaultDemo.token);
              await loadWorkspaceData(defaultDemo.token, defaultDemo);
            }
          } catch {
            setUser(null);
            setToken(null);
            setIsAuthModalOpen(true);
          }
        } else {
          setUser(null);
          setToken(null);
          setIsAuthModalOpen(true);
        }
      }
      setLoading(false);
    });

    return () => {
      if (typeof unsubscribe === 'function') unsubscribe();
    };
  }, [loadWorkspaceData]);

  // Fast demo role switch
  async function handleSwitchDemo(demoUser) {
    try {
      await loginWithDemoIdentity(demoUser);
      setToken(demoUser.token);
      await loadWorkspaceData(demoUser.token, demoUser);
    } catch (err) {
      setGlobalError(`Failed to switch to ${demoUser.email}: ${err.message}`);
    }
  }

  // Handle logout
  async function handleLogout() {
    await logoutUser();
    setUser(null);
    setToken(null);
    setDrafts([]);
    setGuidelines([]);
    setAuditLogs([]);
    setIsAuthModalOpen(true);
  }

  const pendingReviewCount = drafts.filter((d) => d.status === 'in_review').length;

  if (loading && !user) {
    return (
      <div className="app-loading-screen">
        <div className="loading-spinner"></div>
        <p>Connecting to BrandGuard AI Governance Workspace...</p>
      </div>
    );
  }

  return (
    <div className="app-root">
      <Navbar
        user={user}
        demoUsers={demoUsers}
        currentTab={currentTab}
        setCurrentTab={setCurrentTab}
        onSwitchDemo={handleSwitchDemo}
        onLogout={handleLogout}
        onOpenAuth={() => setIsAuthModalOpen(true)}
        pendingReviewCount={pendingReviewCount}
      />

      {globalError && (
        <div className="global-error-banner" role="alert">
          <div className="global-error-content">
            <span className="global-error-icon" aria-hidden="true">⚠️</span>
            <span className="global-error-text">{globalError}</span>
          </div>
          <div className="global-error-actions">
            {token && (
              <button
                type="button"
                className="btn-retry"
                onClick={() => loadWorkspaceData(token, user)}
              >
                Retry
              </button>
            )}
            <button
              type="button"
              className="btn-close-banner"
              onClick={() => setGlobalError('')}
              aria-label="Dismiss error banner"
            >
              ✕
            </button>
          </div>
        </div>
      )}

      <main className="app-main-content">
        {currentTab === 'dashboard' && (
          <DashboardView
            user={user}
            drafts={drafts}
            guidelines={guidelines}
            auditLogs={auditLogs}
            setCurrentTab={setCurrentTab}
            onOpenCreateDraft={() => {
              setIsCreatingDraft(true);
              setCurrentTab('drafts');
            }}
          />
        )}

        {currentTab === 'drafts' && (
          <DraftsStudioView
            user={user}
            token={token}
            drafts={drafts}
            onRefreshDrafts={() => loadWorkspaceData(token, user)}
            isCreating={isCreatingDraft}
            setIsCreating={setIsCreatingDraft}
          />
        )}

        {currentTab === 'review-queue' && (
          <ReviewerQueueView
            user={user}
            token={token}
            drafts={drafts}
            onRefreshDrafts={() => loadWorkspaceData(token, user)}
            setCurrentTab={setCurrentTab}
          />
        )}

        {currentTab === 'guidelines' && (
          <GuidelinesView
            user={user}
            token={token}
            guidelines={guidelines}
            onRefreshGuidelines={() => loadWorkspaceData(token, user)}
          />
        )}

        {currentTab === 'audit' && (
          <AuditTrailView
            auditLogs={auditLogs}
            onRefresh={() => loadWorkspaceData(token, user)}
          />
        )}

        {currentTab === 'phase1' && (
          <Phase1SandboxView />
        )}
      </main>

      <AuthModal
        isOpen={isAuthModalOpen}
        onClose={() => setIsAuthModalOpen(false)}
        demoUsers={demoUsers}
        onLoginSuccess={async (authUser) => {
          const immediateUser = {
            user_id: authUser.uid || authUser.user_id,
            email: authUser.email,
            role: authUser.role || 'creator',
            org_name: authUser.org_name || 'BrandGuard Workspace',
            token: authUser.token,
            mode: authUser.mode
          };
          setUser(immediateUser);
          setToken(authUser.token);
          await loadWorkspaceData(authUser.token, immediateUser);
        }}
      />
    </div>
  );
}
