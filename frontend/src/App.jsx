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
  const loadWorkspaceData = useCallback(async (authToken) => {
    if (!authToken) return;
    try {
      const [profileData, draftsData, guidelinesData, auditData] = await Promise.all([
        api.fetchProfile(authToken),
        api.fetchDrafts(authToken),
        api.fetchGuidelines(authToken),
        api.fetchAuditLogs(authToken)
      ]);

      setUser({
        ...profileData,
        token: authToken
      });
      setDrafts(draftsData || []);
      setGuidelines(guidelinesData || []);
      setAuditLogs(auditData || []);
    } catch (err) {
      console.error('Failed to load workspace data:', err);
      setGlobalError(err.message || 'Error connecting to BrandGuard backend.');
    }
  }, []);

  // Listen to auth changes
  useEffect(() => {
    const unsubscribe = subscribeToAuthState(async (authUser) => {
      setLoading(true);
      if (authUser?.token) {
        setToken(authUser.token);
        await loadWorkspaceData(authUser.token);
      } else {
        // In development / demo mode, default to the seeded demo Creator for instant hands-on testing
        if (isDemoAuthEnabled) {
          try {
            const demos = await api.fetchDemoUsers();
            if (demos && demos.length > 0) {
              const defaultDemo = demos[2] || demos[0]; // Jordan Creator
              await loginWithDemoIdentity(defaultDemo);
              setToken(defaultDemo.token);
              await loadWorkspaceData(defaultDemo.token);
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
      await loadWorkspaceData(demoUser.token);
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
        <div className="global-error-banner">
          <span>⚠️ {globalError}</span>
          <button className="btn-link" onClick={() => setGlobalError('')}>✕</button>
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
            onRefreshDrafts={() => loadWorkspaceData(token)}
            isCreating={isCreatingDraft}
            setIsCreating={setIsCreatingDraft}
          />
        )}

        {currentTab === 'review-queue' && (
          <ReviewerQueueView
            user={user}
            token={token}
            drafts={drafts}
            onRefreshDrafts={() => loadWorkspaceData(token)}
            setCurrentTab={setCurrentTab}
          />
        )}

        {currentTab === 'guidelines' && (
          <GuidelinesView
            user={user}
            token={token}
            guidelines={guidelines}
            onRefreshGuidelines={() => loadWorkspaceData(token)}
          />
        )}

        {currentTab === 'audit' && (
          <AuditTrailView
            auditLogs={auditLogs}
            onRefresh={() => loadWorkspaceData(token)}
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
          setToken(authUser.token);
          await loadWorkspaceData(authUser.token);
        }}
      />
    </div>
  );
}
