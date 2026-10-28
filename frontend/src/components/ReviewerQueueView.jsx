import React, { useState } from 'react';
import { api } from '../api';
import { formatCreatorEmail } from './DraftsStudioView';

export default function ReviewerQueueView({
  user,
  token,
  drafts,
  onRefreshDrafts,
  setCurrentTab
}) {
  const pendingDrafts = drafts.filter((d) => d.status === 'in_review');
  const [selectedDraftId, setSelectedDraftId] = useState(pendingDrafts[0]?.id || null);
  const [reviewComments, setReviewComments] = useState('');
  const [loading, setLoading] = useState(false);
  const [dossierId,setDossierId] = useState('');
  const [exceptionReason,setExceptionReason] = useState('');
  const [feedbackMessage, setFeedbackMessage] = useState(null);
  const [errorMessage, setErrorMessage] = useState('');

  const selectedDraft = pendingDrafts.find((d) => d.id === selectedDraftId) || pendingDrafts[0];

  const isCreatorOfDraft = selectedDraft && selectedDraft.creator_id === user?.user_id;
  const isReviewerOrAdmin = user?.role === 'reviewer' || user?.role === 'admin';

  async function handleApprove() {
    if (!selectedDraft) return;
    if (!reviewComments.trim()) {
      setErrorMessage('Please provide approval verification notes (e.g. cited evidence verified).');
      return;
    }
    setLoading(true);
    setErrorMessage('');
    try {
      const res = await api.approveDraft(token, selectedDraft.id, reviewComments, dossierId.trim()||null, exceptionReason.trim()||null);
      await onRefreshDrafts();
      setReviewComments('');
      setDossierId('');setExceptionReason('');
      setFeedbackMessage(`Approved draft "${selectedDraft.title}". ${res.publication_notice}`);
    } catch (err) {
      setErrorMessage(err.message || 'Approval failed.');
    } finally {
      setLoading(false);
    }
  }

  async function handleRequestChanges() {
    if (!selectedDraft) return;
    if (!reviewComments.trim()) {
      setErrorMessage('Please provide specific feedback detailing the required revisions.');
      return;
    }
    setLoading(true);
    setErrorMessage('');
    try {
      await api.requestChangesDraft(token, selectedDraft.id, reviewComments);
      await onRefreshDrafts();
      setReviewComments('');
      setFeedbackMessage(`Changes requested for "${selectedDraft.title}". Draft returned to creator.`);
    } catch (err) {
      setErrorMessage(err.message || 'Failed to request changes.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="reviewer-queue-container">
      <div className="queue-header-banner">
        <div>
          <h2>Reviewer Compliance Queue</h2>
          <p>
            Authoritative evaluation of marketing assets before external publication.
            Separation of duties enforced.
          </p>
        </div>
        <div className="queue-stat-pill">
          Pending Review: <strong>{pendingDrafts.length}</strong>
        </div>
      </div>

      {feedbackMessage && <div className="alert-box success">{feedbackMessage}</div>}
      {errorMessage && <div className="alert-box error">{errorMessage}</div>}

      {pendingDrafts.length === 0 ? (
        <div className="empty-queue-card">
          <span className="queue-empty-icon">🎉</span>
          <h3>All Clear! No drafts pending review</h3>
          <p>All submitted marketing drafts have been reviewed and resolved.</p>
          <button className="btn-secondary" onClick={() => setCurrentTab('drafts')}>
            Return to Drafts Studio
          </button>
        </div>
      ) : (
        <div className="queue-layout">
          {/* List of drafts in review */}
          <div className="queue-sidebar">
            <label className="sidebar-section-label">Pending Assets ({pendingDrafts.length})</label>
            <div className="queue-cards-list">
              {pendingDrafts.map((d) => (
                <div
                  key={d.id}
                  className={`queue-draft-card ${selectedDraft?.id === d.id ? 'active' : ''}`}
                  onClick={() => {
                    setSelectedDraftId(d.id);
                    setFeedbackMessage(null);
                    setErrorMessage('');
                  }}
                >
                  <div className="card-top-row">
                    <span className="card-channel-pill">{d.channel}</span>
                    <span className="card-time">{new Date(d.created_at).toLocaleDateString()}</span>
                  </div>
                  <h4 className="queue-card-title">{d.title}</h4>
                  <div className="card-bottom-row">
                    <span className="card-creator">{formatCreatorEmail(d.creator_email)}</span>
                    <span className={`finding-count-pill ${d.findings.length > 0 ? 'has-flags' : 'clean'}`}>
                      {d.findings.length === 0 ? '0 Flags' : `${d.findings.length} Flags`}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Selected draft inspection & decision */}
          {selectedDraft && (
            <div className="queue-main-inspection">
              <div className="inspection-card">
                <div className="inspection-header">
                  <div>
                    <h3>{selectedDraft.title}</h3>
                    <div className="inspection-meta">
                      <span>Campaign: <strong>{selectedDraft.campaign}</strong></span>
                      <span>Channel: <strong>{selectedDraft.channel}</strong></span>
                      <span>Audience: <strong>{selectedDraft.audience}</strong></span>
                      <span>Creator: <strong>{formatCreatorEmail(selectedDraft.creator_email)}</strong></span>
                    </div>
                  </div>
                  <span className="status-pill status-in_review">In Review</span>
                </div>

                <div className="inspection-content-box">
                  <label>Draft Copy</label>
                  <div className="draft-copy-view">
                    {selectedDraft.content}
                  </div>
                </div>

                <div className="findings-review-container">
                  <div className="findings-review-header-row">
                    <label>Compliance Evaluation Findings ({selectedDraft.findings.length})</label>
                    <span className="tag-pill">
                      {selectedDraft.ai_status === 'completed' ? '✨ Gemini AI Verified' : '⚡ Deterministic Fallback'}
                    </span>
                  </div>

                  {selectedDraft.findings.length === 0 ? (
                    <div className="alert-box clean-advisory">
                      ✅ <strong>All Checks Clean:</strong> No guideline violations detected in copy by deterministic or AI checks.
                    </div>
                  ) : (
                    <div className="findings-summary-list">
                      {selectedDraft.findings.map((f, i) => (
                        <div key={i} className={`finding-item-row sev-${f.severity} ${f.is_ai_generated ? 'ai-item-row' : ''}`}>
                          <div className="item-row-left">
                            {f.is_ai_generated ? (
                              <span className="ai-verified-badge-sm">🤖 AI GROUNDED</span>
                            ) : (
                              <span className="det-verified-badge-sm">⚡ DET</span>
                            )}
                            <span className={`severity-badge sev-${f.severity}`}>{f.severity.toUpperCase()}</span>
                            <code>{f.rule_id} (v{f.rule_version})</code>
                            <strong>“{f.matched_text}”</strong>
                          </div>
                          <div className="item-row-right">
                            <span className="item-source">Source: {f.source_label}</span>
                          </div>
                          <div className="item-row-reason">
                            <p>{f.reason} — <em>Remedy: {f.suggestion}</em></p>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Reviewer Action Form */}
                <div className="reviewer-decision-card">
                  <h4>Reviewer Decision</h4>
                  <p className="decision-subtitle">
                    Record evidence verification or explain required revisions.
                  </p>

                  {!isReviewerOrAdmin && (
                    <div className="alert-box warning">
                      🔒 Only users with the <strong>Reviewer</strong> or <strong>Admin</strong> role can approve or request changes.
                    </div>
                  )}

                  {isCreatorOfDraft && user?.role !== 'admin' && (
                    <div className="alert-box warning">
                      ⚠️ <strong>Separation of Duties Policy:</strong> You created this draft and cannot approve it yourself. Another reviewer must approve.
                    </div>
                  )}

                  <div className="form-group">
                    <label>Review Notes & Evidence Verification Comments</label>
                    <textarea
                      rows={3}
                      placeholder="e.g. Verified against Substantiation Dossier §4. Approved for release."
                      value={reviewComments}
                      onChange={(e) => setReviewComments(e.target.value)}
                      disabled={!isReviewerOrAdmin}
                    />
                  </div>

                  {selectedDraft.findings.some(f=>f.severity==='high')&&<div className="form-group">
                    <p><strong>High-risk approval protection:</strong> Supply a verified claim dossier ID (the exact dossier claim must appear in this draft), OR a detailed reviewer exception.</p>
                    <label>Approved evidence dossier ID</label>
                    <input value={dossierId} onChange={e=>setDossierId(e.target.value)} placeholder="claim_..." />
                    <label>Reviewer-recorded exception (25+ characters)</label>
                    <textarea rows={3} value={exceptionReason} onChange={e=>setExceptionReason(e.target.value)} placeholder="Explain approval of flagged content."/>
                  </div>}
                  <div className="decision-buttons-row">
                    <button
                      className="btn-danger"
                      onClick={handleRequestChanges}
                      disabled={loading || !isReviewerOrAdmin || !reviewComments.trim()}
                    >
                      {loading ? 'Processing...' : '⚠️ Request Changes'}
                    </button>

                    <button
                      className="btn-success"
                      onClick={handleApprove}
                      disabled={
                        loading ||
                        !isReviewerOrAdmin ||
                        (isCreatorOfDraft && user?.role !== 'admin') ||
                        !reviewComments.trim()
                      }
                    >
                      {loading ? 'Processing...' : '✅ Approve Draft'}
                    </button>
                  </div>

                  <div className="policy-notice">
                    <small>
                      🛡️ <strong>Governance Guarantee:</strong> No automatic publication. Approved drafts remain in workspace for manual release.
                    </small>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
