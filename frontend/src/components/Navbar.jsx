import React from 'react';

export default function Navbar({
  user,
  demoUsers,
  currentTab,
  setCurrentTab,
  onSwitchDemo,
  onLogout,
  onOpenAuth,
  pendingReviewCount
}) {
  const roleColors = {
    admin: 'role-admin',
    reviewer: 'role-reviewer',
    creator: 'role-creator'
  };

  return (
    <header className="app-navbar">
      <div className="navbar-left">
        <div className="navbar-brand" onClick={() => setCurrentTab('dashboard')}>
          <div className="brand-logo-icon">🛡️</div>
          <div className="brand-titles">
            <span className="brand-name">BrandGuard AI</span>
            <span className="brand-phase">Phase 2 · Governance</span>
          </div>
        </div>

        {user && (
          <nav className="nav-tabs">
            <button
              className={`nav-tab-btn ${currentTab === 'dashboard' ? 'active' : ''}`}
              onClick={() => setCurrentTab('dashboard')}
            >
              Dashboard
            </button>
            <button
              className={`nav-tab-btn ${currentTab === 'drafts' ? 'active' : ''}`}
              onClick={() => setCurrentTab('drafts')}
            >
              Drafts & Pre-check
            </button>
            <button
              className={`nav-tab-btn ${currentTab === 'review-queue' ? 'active' : ''}`}
              onClick={() => setCurrentTab('review-queue')}
            >
              Reviewer Queue
              {pendingReviewCount > 0 && (
                <span className="badge-counter">{pendingReviewCount}</span>
              )}
            </button>
            <button
              className={`nav-tab-btn ${currentTab === 'guidelines' ? 'active' : ''}`}
              onClick={() => setCurrentTab('guidelines')}
            >
              Guideline Library
            </button>
            <button
              className={`nav-tab-btn ${currentTab === 'audit' ? 'active' : ''}`}
              onClick={() => setCurrentTab('audit')}
            >
              Audit Trail
            </button>
            <button
              className={`nav-tab-btn ${currentTab === 'phase1' ? 'active' : ''}`}
              onClick={() => setCurrentTab('phase1')}
            >
              Phase 1 Sandbox
            </button>
          </nav>
        )}
      </div>

      <div className="navbar-right">
        {user ? (
          <>
            <div className="workspace-pill" title="Tenant Workspace">
              <span className="tenant-dot"></span>
              <span className="workspace-name">{user.org_name || 'Acme Global Brands'}</span>
            </div>

            <div className="user-profile-widget">
              <span className={`role-badge ${roleColors[user.role] || ''}`}>
                {user.role?.toUpperCase()}
              </span>
              <span className="user-email-text" title={user.email}>{user.email}</span>
            </div>

            {demoUsers && demoUsers.length > 0 && (
              <div className="demo-switch-container">
                <select
                  aria-label="Switch User Identity"
                  className="demo-switch-select"
                  value={user.user_id}
                  onChange={(e) => {
                    const selected = demoUsers.find((u) => u.user_id === e.target.value);
                    if (selected) onSwitchDemo(selected);
                  }}
                >
                  <option disabled value="">Switch Role (Dev)</option>
                  {demoUsers.map((u) => (
                    <option key={u.user_id} value={u.user_id}>
                      {u.display_name} ({u.role})
                    </option>
                  ))}
                </select>
              </div>
            )}

            <button className="btn-logout" onClick={onLogout} title="Sign Out">
              Sign Out
            </button>
          </>
        ) : (
          <button className="btn-primary" onClick={onOpenAuth}>
            Sign In / Demo Access
          </button>
        )}
      </div>
    </header>
  );
}
