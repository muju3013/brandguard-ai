import React from 'react';

export default function DashboardView({
  user,
  drafts,
  guidelines,
  auditLogs,
  setCurrentTab,
  onOpenCreateDraft
}) {
  const inReviewCount = drafts.filter((d) => d.status === 'in_review').length;
  const approvedCount = drafts.filter((d) => d.status === 'approved').length;
  const changesCount = drafts.filter((d) => d.status === 'changes_requested').length;
  const activeGuidelinesCount = guidelines.filter((g) => g.is_active).length;

  return (
    <div className="dashboard-container">
      <div className="welcome-banner">
        <div>
          <h2>Welcome back, {user?.email}</h2>
          <p className="banner-subtitle">
            Workspace: <strong>{user?.org_name || 'Primary Workspace'}</strong> · Role:{' '}
            <span className={`role-badge role-${user?.role}`}>{user?.role?.toUpperCase()}</span>
          </p>
        </div>
        <div className="banner-actions">
          {(user?.role === 'creator' || user?.role === 'admin') && (
            <button className="btn-primary" onClick={onOpenCreateDraft}>
              + New Marketing Draft
            </button>
          )}
          {(user?.role === 'reviewer' || user?.role === 'admin') && (
            <button className="btn-secondary" onClick={() => setCurrentTab('review-queue')}>
              Reviewer Queue ({inReviewCount})
            </button>
          )}
        </div>
      </div>

      <div className="metrics-grid">
        <div className="metric-card" onClick={() => setCurrentTab('drafts')}>
          <div className="metric-header">
            <span className="metric-label">Total Drafts</span>
            <span className="metric-icon">📝</span>
          </div>
          <div className="metric-value">{drafts.length}</div>
          <div className="metric-desc">Marketing assets in workspace</div>
        </div>

        <div className="metric-card highlight-warning" onClick={() => setCurrentTab('review-queue')}>
          <div className="metric-header">
            <span className="metric-label">In Review</span>
            <span className="metric-icon">⏳</span>
          </div>
          <div className="metric-value">{inReviewCount}</div>
          <div className="metric-desc">Awaiting reviewer sign-off</div>
        </div>

        <div className="metric-card highlight-success" onClick={() => setCurrentTab('drafts')}>
          <div className="metric-header">
            <span className="metric-label">Approved</span>
            <span className="metric-icon">✅</span>
          </div>
          <div className="metric-value">{approvedCount}</div>
          <div className="metric-desc">Sign-off complete (Manual release)</div>
        </div>

        <div className="metric-card highlight-danger" onClick={() => setCurrentTab('drafts')}>
          <div className="metric-header">
            <span className="metric-label">Changes Requested</span>
            <span className="metric-icon">⚠️</span>
          </div>
          <div className="metric-value">{changesCount}</div>
          <div className="metric-desc">Needs creator revision</div>
        </div>

        <div className="metric-card" onClick={() => setCurrentTab('guidelines')}>
          <div className="metric-header">
            <span className="metric-label">Active Guidelines</span>
            <span className="metric-icon">⚖️</span>
          </div>
          <div className="metric-value">{activeGuidelinesCount}</div>
          <div className="metric-desc">Authoritative compliance rules</div>
        </div>
      </div>

      <div className="dashboard-columns">
        <div className="dashboard-panel governance-guarantees-panel">
          <div className="panel-title-row">
            <h3>Enterprise Brand Governance Architecture</h3>
            <span className="tag-pill">Phase 2 Verified</span>
          </div>
          <div className="guarantees-list">
            <div className="guarantee-item">
              <span className="guarantee-icon">🔒</span>
              <div>
                <strong>Server-Authoritative RBAC & Multi-Tenant Isolation</strong>
                <p>Browser cannot forge roles or workspace IDs. Every endpoint enforces Firestore tenant boundaries.</p>
              </div>
            </div>
            <div className="guarantee-item">
              <span className="guarantee-icon">🔍</span>
              <div>
                <strong>Evidence-Linked Deterministic Checking</strong>
                <p>Checks evaluate exclusively against active guidelines with rule IDs, version stamps, and exact source labels—no hallucinated citations.</p>
              </div>
            </div>
            <div className="guarantee-item">
              <span className="guarantee-icon">👥</span>
              <div>
                <strong>Separation of Duties</strong>
                <p>Creators cannot approve their own drafts. Reviewer sign-off is logged with persistent audit trails.</p>
              </div>
            </div>
            <div className="guarantee-item">
              <span className="guarantee-icon">🛡️</span>
              <div>
                <strong>No Automatic Publication</strong>
                <p>Governed drafts are verified and marked approved for manual controlled deployment only.</p>
              </div>
            </div>
          </div>
        </div>

        <div className="dashboard-panel recent-activity-panel">
          <div className="panel-title-row">
            <h3>Recent Governance Events</h3>
            <button className="btn-link" onClick={() => setCurrentTab('audit')}>View Full Log</button>
          </div>
          {auditLogs.length === 0 ? (
            <p className="empty-state-text">No activity recorded yet.</p>
          ) : (
            <div className="activity-timeline">
              {auditLogs.slice(0, 6).map((log) => (
                <div key={log.id} className="timeline-item">
                  <div className="timeline-dot"></div>
                  <div className="timeline-content">
                    <div className="timeline-row">
                      <span className={`action-badge action-${log.action}`}>{log.action.replace('_', ' ').toUpperCase()}</span>
                      <span className="timeline-time">{new Date(log.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                    </div>
                    <p className="timeline-actor">
                      <strong>{log.actor_email}</strong> ({log.actor_role}) on {log.entity_type} <code>{log.entity_id}</code>
                    </p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
