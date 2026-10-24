import React, { useState } from 'react';
import { api } from '../api';

export function formatCreatorEmail(email) {
  if (!email || typeof email !== 'string' || email.startsWith('eyJ') || email.includes('undefined')) {
    return 'Creator email unavailable';
  }
  return email;
}

export default function DraftsStudioView({
  user,
  token,
  drafts,
  onRefreshDrafts,
  isCreating,
  setIsCreating
}) {
  const [selectedDraftId, setSelectedDraftId] = useState(drafts[0]?.id || null);
  const [statusFilter, setStatusFilter] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');

  // New Draft Form State
  const [newTitle, setNewTitle] = useState('');
  const [newCampaign, setNewCampaign] = useState('');
  const [newChannel, setNewChannel] = useState('social');
  const [newAudience, setNewAudience] = useState('general_public');
  const [newContent, setNewContent] = useState('');

  // Selected Draft Editor State
  const [editContent, setEditContent] = useState('');
  const [isEditing, setIsEditing] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [actionMessage, setActionMessage] = useState(null);
  const [actionError, setActionError] = useState('');

  const selectedDraft = drafts.find((d) => d.id === selectedDraftId) || drafts[0];

  // Sync editContent when selected draft changes
  React.useEffect(() => {
    if (selectedDraft) {
      setEditContent(selectedDraft.content);
      setIsEditing(false);
      setActionMessage(null);
      setActionError('');
    }
  }, [selectedDraft?.id, selectedDraft?.updated_at]);

  const filteredDrafts = drafts.filter((d) => {
    const matchesStatus = statusFilter === 'all' || d.status === statusFilter;
    const matchesSearch =
      d.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      d.campaign.toLowerCase().includes(searchQuery.toLowerCase()) ||
      d.content.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesStatus && matchesSearch;
  });

  async function handleCreateDraft(e) {
    e.preventDefault();
    setActionLoading(true);
    setActionError('');
    try {
      const created = await api.createDraft(token, {
        title: newTitle,
        campaign: newCampaign,
        channel: newChannel,
        audience: newAudience,
        content: newContent
      });
      await onRefreshDrafts();
      setSelectedDraftId(created.id);
      setIsCreating(false);
      setNewTitle('');
      setActionMessage('Draft created and pre-checked against active guidelines.');
    } catch (err) {
      setActionError(err.message || 'Failed to create draft.');
    } finally {
      setActionLoading(false);
    }
  }

  async function handleRunPrecheck() {
    if (!selectedDraft) return;
    setActionLoading(true);
    setActionError('');
    try {
      const result = await api.checkDraft(token, selectedDraft.id);
      await onRefreshDrafts();
      setActionMessage(`Pre-check completed: ${result.summary}`);
    } catch (err) {
      setActionError(err.message || 'Pre-check failed.');
    } finally {
      setActionLoading(false);
    }
  }

  async function handleSaveRevision() {
    if (!selectedDraft) return;
    setActionLoading(true);
    setActionError('');
    try {
      await api.updateDraft(token, selectedDraft.id, {
        content: editContent
      });
      await onRefreshDrafts();
      setIsEditing(false);
      setActionMessage('Revisions saved and re-evaluated against guidelines.');
    } catch (err) {
      setActionError(err.message || 'Failed to update draft.');
    } finally {
      setActionLoading(false);
    }
  }

  async function handleSubmitForReview() {
    if (!selectedDraft) return;
    setActionLoading(true);
    setActionError('');
    try {
      await api.submitDraft(token, selectedDraft.id);
      await onRefreshDrafts();
      setActionMessage('Draft submitted to Reviewer Queue.');
    } catch (err) {
      setActionError(err.message || 'Failed to submit draft.');
    } finally {
      setActionLoading(false);
    }
  }

  const canEdit =
    (user?.role === 'creator' || user?.role === 'admin') &&
    selectedDraft &&
    (selectedDraft.status === 'draft' || selectedDraft.status === 'changes_requested');

  return (
    <div className="studio-container">
      {/* Sidebar: Draft List */}
      <aside className="studio-sidebar">
        <div className="sidebar-header">
          <div className="sidebar-title-row">
            <h3>Drafts ({drafts.length})</h3>
            {(user?.role === 'creator' || user?.role === 'admin') && (
              <button
                className="btn-primary btn-sm"
                onClick={() => setIsCreating(true)}
              >
                + New
              </button>
            )}
          </div>

          <div className="filter-search-box">
            <input
              type="text"
              placeholder="Search drafts or campaign..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="search-input"
            />
          </div>

          <div className="filter-pills">
            {['all', 'draft', 'in_review', 'changes_requested', 'approved'].map((status) => (
              <button
                key={status}
                className={`filter-pill ${statusFilter === status ? 'active' : ''}`}
                onClick={() => setStatusFilter(status)}
              >
                {status.replace('_', ' ')}
              </button>
            ))}
          </div>
        </div>

        <div className="draft-list-items">
          {filteredDrafts.length === 0 ? (
            <div className="empty-state-card">No matching drafts found.</div>
          ) : (
            filteredDrafts.map((d) => (
              <div
                key={d.id}
                className={`draft-list-card ${selectedDraft?.id === d.id ? 'selected' : ''}`}
                onClick={() => setSelectedDraftId(d.id)}
              >
                <div className="card-top">
                  <span className={`status-pill status-${d.status}`}>
                    {d.status.replace('_', ' ')}
                  </span>
                  <span className="card-channel">{d.channel}</span>
                </div>
                <h4 className="card-title">{d.title}</h4>
                <div className="card-meta">
                  <span className="card-campaign">{d.campaign}</span>
                  <span className="findings-count-badge">
                    {d.findings.length === 0 ? '✓ Clean' : `⚠️ ${d.findings.length} flags`}
                  </span>
                </div>
              </div>
            ))
          )}
        </div>
      </aside>

      {/* Main Studio Area */}
      <main className="studio-main">
        {actionMessage && <div className="alert-box success">{actionMessage}</div>}
        {actionError && <div className="alert-box error">{actionError}</div>}

        {isCreating ? (
          <div className="studio-panel create-draft-panel">
            <div className="panel-header-with-action">
              <h3>Create New Marketing Draft</h3>
              <button className="btn-secondary btn-sm" onClick={() => setIsCreating(false)}>
                Cancel
              </button>
            </div>

            <form onSubmit={handleCreateDraft} className="draft-form">
              <div className="form-row-2">
                <div className="form-group">
                  <label>Draft Title</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. Q3 Radiance Serum Instagram Ad"
                    value={newTitle}
                    onChange={(e) => setNewTitle(e.target.value)}
                  />
                </div>
                <div className="form-group">
                  <label>Campaign Name</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. Summer Glow 2026"
                    value={newCampaign}
                    onChange={(e) => setNewCampaign(e.target.value)}
                  />
                </div>
              </div>

              <div className="form-row-2">
                <div className="form-group">
                  <label>Channel Context</label>
                  <select value={newChannel} onChange={(e) => setNewChannel(e.target.value)}>
                    <option value="social">Social Media (Instagram/LinkedIn)</option>
                    <option value="email">Email Newsletter</option>
                    <option value="press_release">Press Release</option>
                    <option value="website">Website / Landing Page</option>
                    <option value="ad_copy">Performance Ad Copy</option>
                  </select>
                </div>
                <div className="form-group">
                  <label>Target Audience</label>
                  <select value={newAudience} onChange={(e) => setNewAudience(e.target.value)}>
                    <option value="general_public">General Consumer</option>
                    <option value="b2b">B2B Decision Makers</option>
                    <option value="gen_z">Gen Z / Young Adults</option>
                    <option value="existing_customers">Existing Loyalty Members</option>
                  </select>
                </div>
              </div>

              <div className="form-group">
                <label>Draft Content</label>
                <textarea
                  rows={8}
                  required
                  placeholder="Enter your marketing copy..."
                  value={newContent}
                  onChange={(e) => setNewContent(e.target.value)}
                />
              </div>

              <div className="form-actions-right">
                <button
                  type="submit"
                  disabled={actionLoading || !newTitle.trim() || !newContent.trim()}
                  className="btn-primary"
                >
                  {actionLoading ? 'Evaluating against Guidelines...' : 'Save Draft & Run Pre-check'}
                </button>
              </div>
            </form>
          </div>
        ) : selectedDraft ? (
          <div className="draft-detail-layout">
            {/* Header info */}
            <div className="draft-detail-header">
              <div className="header-meta-left">
                <div className="title-row">
                  <h2>{selectedDraft.title}</h2>
                  <span className={`status-pill status-${selectedDraft.status}`}>
                    {selectedDraft.status.replace('_', ' ')}
                  </span>
                </div>
                <div className="context-tags-bar">
                  <span className="context-tag">📢 Campaign: <strong>{selectedDraft.campaign}</strong></span>
                  <span className="context-tag">📱 Channel: <strong>{selectedDraft.channel}</strong></span>
                  <span className="context-tag">🎯 Audience: <strong>{selectedDraft.audience}</strong></span>
                  <span className="context-tag">👤 Creator: <strong>{formatCreatorEmail(selectedDraft.creator_email)}</strong></span>
                </div>
              </div>

              <div className="header-actions-right">
                {canEdit && (
                  <>
                    <button
                      className="btn-secondary btn-sm"
                      onClick={handleRunPrecheck}
                      disabled={actionLoading}
                    >
                      Run Pre-check
                    </button>
                    <button
                      className="btn-primary btn-sm"
                      onClick={handleSubmitForReview}
                      disabled={actionLoading}
                    >
                      Submit for Review ➔
                    </button>
                  </>
                )}
              </div>
            </div>

            {/* Review feedback alert if changes were requested */}
            {selectedDraft.status === 'changes_requested' && (
              <div className="alert-box warning revision-instructions-box">
                <div className="revision-header">
                  <strong>⚠️ Reviewer Feedback ({selectedDraft.reviewed_by_email}):</strong>
                  <span className="reviewed-time">{new Date(selectedDraft.reviewed_at).toLocaleString()}</span>
                </div>
                <p className="revision-notes-text">{selectedDraft.review_notes}</p>
                <small>Please revise the draft content below and resubmit for review.</small>
              </div>
            )}

            {/* Approval badge if approved */}
            {selectedDraft.status === 'approved' && (
              <div className="alert-box success approval-notice-box">
                <div>
                  <strong>✅ Approved by Compliance Reviewer ({selectedDraft.reviewed_by_email})</strong>
                  <p>{selectedDraft.review_notes || 'All claims verified against active guidelines.'}</p>
                  <small>⚠️ Governance Policy: Verified for release. No automatic publication is performed.</small>
                </div>
              </div>
            )}

            {/* In Review banner */}
            {selectedDraft.status === 'in_review' && (
              <div className="alert-box info">
                ⏳ <strong>Draft is Currently In Review.</strong> Direct editing is locked until the reviewer approves or requests revisions.
              </div>
            )}

            {/* Editor or Content view */}
            <div className="content-editor-card">
              <div className="editor-card-header">
                <label>Draft Copy</label>
                <div className="editor-tools">
                  <span className="char-count">{editContent.length} chars · {editContent.trim().split(/\s+/).filter(Boolean).length} words</span>
                  {canEdit && !isEditing && (
                    <button className="btn-link" onClick={() => setIsEditing(true)}>
                      ✏️ Edit Copy
                    </button>
                  )}
                </div>
              </div>

              {canEdit && isEditing ? (
                <div className="editable-wrapper">
                  <textarea
                    rows={8}
                    value={editContent}
                    onChange={(e) => setEditContent(e.target.value)}
                    className="draft-editor-textarea"
                  />
                  <div className="editor-save-row">
                    <button
                      className="btn-secondary btn-sm"
                      onClick={() => {
                        setEditContent(selectedDraft.content);
                        setIsEditing(false);
                      }}
                    >
                      Cancel
                    </button>
                    <button
                      className="btn-primary btn-sm"
                      onClick={handleSaveRevision}
                      disabled={actionLoading}
                    >
                      Save Revisions & Re-check
                    </button>
                  </div>
                </div>
              ) : (
                <div className="content-display-box">
                  <p>{selectedDraft.content}</p>
                </div>
              )}
            </div>

            {/* Overall Assessment Banner */}
            {selectedDraft.outcome && (
              <div className={`assessment-banner assessment-${selectedDraft.outcome}`}>
                <div className="assessment-left">
                  <span className="assessment-icon">
                    {selectedDraft.outcome === 'compliant'
                      ? '🛡️'
                      : selectedDraft.outcome === 'guidelines_not_configured'
                      ? '📋'
                      : selectedDraft.outcome === 'insufficient_evidence'
                      ? '⚖️'
                      : selectedDraft.outcome === 'assessment_incomplete'
                      ? '⏳'
                      : '⚠️'}
                  </span>
                  <div>
                    <span className="assessment-label">Governance Pre-Check Assessment</span>
                    <strong className="assessment-value">
                      {selectedDraft.outcome === 'guidelines_not_configured'
                        ? 'Guidelines Not Configured'
                        : selectedDraft.outcome === 'compliant'
                        ? 'Compliant'
                        : selectedDraft.outcome === 'insufficient_evidence'
                        ? 'Insufficient Evidence / Human Review Required'
                        : selectedDraft.outcome === 'assessment_incomplete'
                        ? 'Assessment Incomplete'
                        : 'Violations Found'}
                    </strong>
                    <div className="assessment-subtext">
                      {selectedDraft.outcome === 'guidelines_not_configured'
                        ? 'No active guidelines are defined in this workspace. Pre-check cannot verify compliance.'
                        : selectedDraft.outcome === 'compliant'
                        ? 'Verified against active guidelines with 0 policy violations.'
                        : selectedDraft.outcome === 'insufficient_evidence'
                        ? 'Promotional claims lack approved evidence in guidelines. Human review required.'
                        : selectedDraft.outcome === 'assessment_incomplete'
                        ? 'Evaluation could not be fully completed.'
                        : `${selectedDraft.findings?.length || 0} policy violation(s) detected. Content must be revised.`}
                    </div>
                  </div>
                </div>
                <div className="assessment-right">
                  <span className={`ai-status-pill status-${selectedDraft.ai_status || 'fallback'}`}>
                    {selectedDraft.ai_status === 'completed'
                      ? `✨ Gemini Grounded AI Active (${selectedDraft.ai_model || 'gemini-3-flash-preview'})`
                      : selectedDraft.ai_status === 'fallback_deterministic_only'
                      ? '⚡ AI Review Unavailable — Deterministic Check Only'
                      : '⚡ Deterministic Fallback'}
                  </span>
                </div>
              </div>
            )}

            {/* Findings Section with Separation */}
            <div className="findings-section">
              <div className="findings-header">
                <div>
                  <h3>Governance Evaluation Findings</h3>
                  <p className="findings-subtitle">
                    Deterministic checks run independently from Gemini AI. All findings are strictly source-grounded in active authorized guidelines.
                  </p>
                </div>
                <div className="findings-counts-summary">
                  <span className="summary-pill det-pill">
                    Deterministic: {selectedDraft.deterministic_findings ? selectedDraft.deterministic_findings.length : selectedDraft.findings.filter(f => !f.is_ai_generated).length}
                  </span>
                  <span className="summary-pill ai-pill">
                    Gemini AI: {selectedDraft.ai_findings ? selectedDraft.ai_findings.length : selectedDraft.findings.filter(f => f.is_ai_generated).length}
                  </span>
                </div>
              </div>

              {/* 1. Deterministic Rule Findings */}
              <div className="findings-group-block">
                <div className="group-title-row">
                  <h4>⚡ Deterministic Rule Findings</h4>
                  <span className="subtle-tag">Exact Regex & Pattern Match</span>
                </div>

                {(() => {
                  const detFindings = selectedDraft.deterministic_findings && selectedDraft.deterministic_findings.length > 0
                    ? selectedDraft.deterministic_findings
                    : selectedDraft.findings.filter(f => !f.is_ai_generated);

                  if (detFindings.length === 0) {
                    return (
                      <div className="clean-findings-subcard">
                        <span>✓ No deterministic pattern violations.</span>
                      </div>
                    );
                  }

                  return (
                    <div className="findings-grid">
                      {detFindings.map((finding, idx) => (
                        <div key={idx} className={`finding-card severity-${finding.severity}`}>
                          <div className="finding-card-top">
                            <span className={`severity-badge sev-${finding.severity}`}>
                              {finding.severity.toUpperCase()}
                            </span>
                            <code className="rule-id-code">{finding.rule_id} (v{finding.rule_version})</code>
                            <span className="finding-category">{finding.category.replace('_', ' ')}</span>
                          </div>

                          <div className="finding-matched-snippet">
                            “{finding.matched_text}”
                            <span className="match-range">chars {finding.start}–{finding.end}</span>
                          </div>

                          <div className="finding-source-evidence">
                            <span className="source-icon">📜</span>
                            <span className="source-label-text">
                              <strong>Active Authoritative Source:</strong> {finding.source_label}
                            </span>
                          </div>

                          <p className="finding-reason">{finding.reason}</p>

                          <div className="finding-remedy">
                            <strong>Actionable Remedy:</strong> {finding.suggestion}
                          </div>
                        </div>
                      ))}
                    </div>
                  );
                })()}
              </div>

              {/* 2. Gemini AI Grounded Governance Findings */}
              <div className="findings-group-block">
                <div className="group-title-row">
                  <h4>✨ Gemini AI Grounded Review Findings</h4>
                  <span className="subtle-tag ai-tag">
                    {selectedDraft.ai_status === 'completed' ? 'Model: Gemini 2.5 Flash' : 'Deterministic Fallback Active'}
                  </span>
                </div>

                {(() => {
                  const aiList = selectedDraft.ai_findings && selectedDraft.ai_findings.length > 0
                    ? selectedDraft.ai_findings
                    : selectedDraft.findings.filter(f => f.is_ai_generated);

                  if (selectedDraft.ai_status === 'fallback_deterministic_only' || (!selectedDraft.ai_status && aiList.length === 0)) {
                    return (
                      <div className="fallback-notice-box">
                        <span className="fallback-icon">ℹ️</span>
                        <div>
                          <strong>Deterministic-Only Fallback Active:</strong>
                          <p>Gemini review is operating in deterministic fallback mode (API key unconfigured or offline). Deterministic governance remains active.</p>
                        </div>
                      </div>
                    );
                  }

                  if (aiList.length === 0) {
                    return (
                      <div className="clean-findings-subcard ai-clean">
                        <span>✓ Gemini AI verified: copy adheres to authorized guideline context.</span>
                      </div>
                    );
                  }

                  return (
                    <div className="findings-grid">
                      {aiList.map((finding, idx) => (
                        <div key={idx} className={`finding-card ai-finding-card severity-${finding.severity}`}>
                          <div className="finding-card-top">
                            <span className="ai-verified-badge">🤖 GEMINI AI GROUNDED</span>
                            <span className={`severity-badge sev-${finding.severity}`}>
                              {finding.severity.toUpperCase()}
                            </span>
                            <code className="rule-id-code">{finding.rule_id} (v{finding.rule_version})</code>
                          </div>

                          <div className="finding-matched-snippet">
                            “{finding.matched_text}”
                            {finding.start !== undefined && (
                              <span className="match-range">chars {finding.start}–{finding.end}</span>
                            )}
                          </div>

                          <div className="finding-source-evidence">
                            <span className="source-icon">📜</span>
                            <span className="source-label-text">
                              <strong>Verified Source:</strong> {finding.source_label}
                            </span>
                          </div>

                          <p className="finding-reason">{finding.reason}</p>

                          <div className="finding-remedy">
                            <strong>Suggested Correction:</strong> {finding.suggestion}
                          </div>
                        </div>
                      ))}
                    </div>
                  );
                })()}
              </div>

              {/* AI Governance & Disclosure Notice */}
              <div className="ai-disclosure-footer">
                <small>
                  🛡️ <strong>AI Disclosure & Policy:</strong> AI findings are generated by Gemini and strictly validated server-side against authorized guideline records. In accordance with enterprise governance policies, AI has no authority to approve, publish, alter permissions, or modify approved brand guidelines.
                </small>
              </div>
            </div>
          </div>
        ) : (
          <div className="empty-studio-state">
            <h3>No Draft Selected</h3>
            <p>Create a marketing draft or select one from the sidebar to inspect governance findings.</p>
          </div>
        )}
      </main>
    </div>
  );
}
