import React, { useState } from 'react';
import { api } from '../api';

export default function GuidelinesView({
  user,
  token,
  guidelines,
  onRefreshGuidelines
}) {
  const isAdmin = user?.role === 'admin';

  // Modal states
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [editingRule, setEditingRule] = useState(null);
  const [historyRule, setHistoryRule] = useState(null);

  // Form states
  const [ruleId, setRuleId] = useState('');
  const [category, setCategory] = useState('prohibited_claim');
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [sourceLabel, setSourceLabel] = useState('');
  const [pattern, setPattern] = useState('');
  const [severity, setSeverity] = useState('high');
  const [remedySuggestion, setRemedySuggestion] = useState('');
  const [isActive, setIsActive] = useState(true);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [successMsg, setSuccessMsg] = useState('');

  // Category filter
  const [selectedCategory, setSelectedCategory] = useState('all');

  function openAddModal() {
    setRuleId(`RULE-${category === 'prohibited_claim' ? 'PRH' : category === 'approved_claim' ? 'CLM' : 'TONE'}-${Math.floor(100 + Math.random() * 900)}`);
    setTitle('');
    setDescription('');
    setSourceLabel('');
    setPattern('');
    setSeverity('high');
    setRemedySuggestion('');
    setIsActive(true);
    setError('');
    setIsAddModalOpen(true);
  }

  function openEditModal(rule) {
    setEditingRule(rule);
    setRuleId(rule.rule_id);
    setCategory(rule.category);
    setTitle(rule.title);
    setDescription(rule.description);
    setSourceLabel(rule.source_label);
    setPattern(rule.pattern);
    setSeverity(rule.severity);
    setRemedySuggestion(rule.remedy_suggestion);
    setIsActive(rule.is_active);
    setError('');
  }

  async function handleCreateRule(e) {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      await api.createGuideline(token, {
        rule_id: ruleId,
        category,
        title,
        description,
        source_label: sourceLabel,
        pattern,
        severity,
        remedy_suggestion: remedySuggestion,
        is_active: isActive
      });
      await onRefreshGuidelines();
      setIsAddModalOpen(false);
      setSuccessMsg(`Created guideline ${ruleId}`);
    } catch (err) {
      setError(err.message || 'Failed to create guideline.');
    } finally {
      setLoading(false);
    }
  }

  async function handleUpdateRule(e) {
    e.preventDefault();
    if (!editingRule) return;
    setLoading(true);
    setError('');
    try {
      await api.updateGuideline(token, editingRule.id, {
        title,
        category,
        description,
        source_label: sourceLabel,
        pattern,
        severity,
        remedy_suggestion: remedySuggestion,
        is_active: isActive
      });
      await onRefreshGuidelines();
      setEditingRule(null);
      setSuccessMsg(`Updated guideline ${editingRule.rule_id} to new version.`);
    } catch (err) {
      setError(err.message || 'Failed to update guideline.');
    } finally {
      setLoading(false);
    }
  }

  async function handleToggleActive(rule) {
    if (!isAdmin) return;
    setLoading(true);
    try {
      if (rule.is_active) {
        await api.deactivateGuideline(token, rule.id);
        setSuccessMsg(`Deactivated rule ${rule.rule_id}`);
      } else {
        await api.updateGuideline(token, rule.id, { is_active: true });
        setSuccessMsg(`Reactivated rule ${rule.rule_id}`);
      }
      await onRefreshGuidelines();
    } catch (err) {
      setError(err.message || 'Failed to update rule status.');
    } finally {
      setLoading(false);
    }
  }

  const filteredRules = guidelines.filter((r) => {
    if (selectedCategory === 'all') return true;
    return r.category === selectedCategory;
  });

  return (
    <div className="guidelines-container">
      <div className="guidelines-header-banner">
        <div>
          <h2>Brand Guideline Library</h2>
          <p>
            Authoritative source standards, approved claims, prohibited wording, and tone rules.
            Rules are versioned and linked to evidence citations.
          </p>
        </div>
        <div className="banner-actions">
          {isAdmin ? (
            <button className="btn-primary" onClick={openAddModal}>
              + Add Guideline Rule
            </button>
          ) : (
            <div className="badge-read-only">
              🔒 Read-Only (Admin role required to edit)
            </div>
          )}
        </div>
      </div>

      {successMsg && <div className="alert-box success">{successMsg}</div>}
      {error && <div className="alert-box error">{error}</div>}

      <div className="category-tabs-bar">
        {[
          { key: 'all', label: `All Guidelines (${guidelines.length})` },
          { key: 'prohibited_claim', label: `Prohibited Claims (${guidelines.filter((g) => g.category === 'prohibited_claim').length})` },
          { key: 'approved_claim', label: `Approved Claims (${guidelines.filter((g) => g.category === 'approved_claim').length})` },
          { key: 'tone_rule', label: `Tone & Voice (${guidelines.filter((g) => g.category === 'tone_rule').length})` }
        ].map((tab) => (
          <button
            key={tab.key}
            className={`category-tab-btn ${selectedCategory === tab.key ? 'active' : ''}`}
            onClick={() => setSelectedCategory(tab.key)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div className="rules-grid">
        {filteredRules.length === 0 ? (
          <div className="empty-guidelines-card">
            <span className="empty-icon">⚖️</span>
            <h3>No Guidelines Found</h3>
            <p>
              {isAdmin
                ? "No guidelines match this category. Click '+ Add Guideline Rule' to define authorized claims, prohibited terms, or tone rules."
                : "No brand guidelines have been created for this workspace yet. An administrator must define active claims and rules before evaluation."}
            </p>
            {isAdmin && (
              <button className="btn-primary" onClick={openAddModal}>
                + Add Guideline Rule
              </button>
            )}
          </div>
        ) : (
          filteredRules.map((rule) => (
          <div key={rule.id} className={`rule-card ${!rule.is_active ? 'inactive-rule' : ''}`}>
            <div className="rule-card-top">
              <div className="rule-ids-left">
                <code className="rule-id-pill">{rule.rule_id}</code>
                <span className="version-pill">v{rule.version}</span>
                <span className={`severity-badge sev-${rule.severity}`}>{rule.severity.toUpperCase()}</span>
              </div>
              <div className="rule-status-right">
                <span className={`rule-active-badge ${rule.is_active ? 'active' : 'inactive'}`}>
                  {rule.is_active ? '● Active' : '○ Deactivated'}
                </span>
              </div>
            </div>

            <h3 className="rule-card-title">{rule.title}</h3>
            <p className="rule-card-desc">{rule.description}</p>

            <div className="rule-meta-block">
              <div className="meta-row">
                <span className="meta-label">Source Citation:</span>
                <span className="meta-val source-val">📜 {rule.source_label}</span>
              </div>

              <div className="meta-row">
                <span className="meta-label">Pattern Regex:</span>
                <code className="pattern-code">{rule.pattern}</code>
              </div>

              <div className="meta-row">
                <span className="meta-label">Remedy:</span>
                <span className="meta-val remedy-val">{rule.remedy_suggestion}</span>
              </div>
            </div>

            <div className="rule-card-footer">
              <div className="rule-history-info">
                {rule.version_history.length > 0 ? (
                  <button
                    className="btn-link"
                    onClick={() => setHistoryRule(rule)}
                  >
                    View History ({rule.version_history.length} past revisions)
                  </button>
                ) : (
                  <span className="muted-text">Initial Version</span>
                )}
              </div>

              {isAdmin && (
                <div className="rule-card-actions">
                  <button
                    className="btn-secondary btn-sm"
                    onClick={() => openEditModal(rule)}
                  >
                    Edit
                  </button>
                  <button
                    className="btn-secondary btn-sm"
                    onClick={() => handleToggleActive(rule)}
                  >
                    {rule.is_active ? 'Deactivate' : 'Reactivate'}
                  </button>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Add Rule Modal */}
      {isAddModalOpen && (
        <div className="modal-backdrop">
          <div className="modal-card modal-lg">
            <div className="modal-header">
              <h3>Create Brand Guideline Rule</h3>
              <button className="modal-close-btn" onClick={() => setIsAddModalOpen(false)}>✕</button>
            </div>
            <form onSubmit={handleCreateRule} className="guideline-form">
              <div className="form-row-2">
                <div className="form-group">
                  <label>Rule ID (Unique in Org)</label>
                  <input
                    type="text"
                    required
                    value={ruleId}
                    onChange={(e) => setRuleId(e.target.value.toUpperCase())}
                  />
                </div>
                <div className="form-group">
                  <label>Category</label>
                  <select value={category} onChange={(e) => setCategory(e.target.value)}>
                    <option value="prohibited_claim">Prohibited Claim</option>
                    <option value="approved_claim">Approved Claim</option>
                    <option value="tone_rule">Tone & Voice Rule</option>
                  </select>
                </div>
              </div>

              <div className="form-group">
                <label>Rule Title</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Prohibit Unsubstantiated Medical Cures"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                />
              </div>

              <div className="form-group">
                <label>Source Label (Evidence Citation)</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Legal Compliance Manual 2026 §4.2"
                  value={sourceLabel}
                  onChange={(e) => setSourceLabel(e.target.value)}
                />
              </div>

              <div className="form-row-2">
                <div className="form-group">
                  <label>Pattern / Regex</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. \b(cure|miracle)\b"
                    value={pattern}
                    onChange={(e) => setPattern(e.target.value)}
                  />
                </div>
                <div className="form-group">
                  <label>Severity</label>
                  <select value={severity} onChange={(e) => setSeverity(e.target.value)}>
                    <option value="high">High (Blocks Approval)</option>
                    <option value="medium">Medium (Advisory)</option>
                    <option value="low">Low (Informational)</option>
                  </select>
                </div>
              </div>

              <div className="form-group">
                <label>Rule Description / Reason</label>
                <textarea
                  rows={2}
                  required
                  placeholder="Explain why this wording is governed..."
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                />
              </div>

              <div className="form-group">
                <label>Actionable Remedy Suggestion</label>
                <textarea
                  rows={2}
                  required
                  placeholder="Explain how creators should revise the copy..."
                  value={remedySuggestion}
                  onChange={(e) => setRemedySuggestion(e.target.value)}
                />
              </div>

              <div className="modal-actions-right">
                <button type="button" className="btn-secondary" onClick={() => setIsAddModalOpen(false)}>
                  Cancel
                </button>
                <button type="submit" disabled={loading} className="btn-primary">
                  {loading ? 'Creating...' : 'Create Rule'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Edit Rule Modal */}
      {editingRule && (
        <div className="modal-backdrop">
          <div className="modal-card modal-lg">
            <div className="modal-header">
              <h3>Edit Rule: {editingRule.rule_id} (Currently v{editingRule.version})</h3>
              <button className="modal-close-btn" onClick={() => setEditingRule(null)}>✕</button>
            </div>
            <p className="modal-notice">
              ⚠️ Editing will increment the version number to <strong>v{editingRule.version + 1}</strong> and archive the current version in audit history.
            </p>
            <form onSubmit={handleUpdateRule} className="guideline-form">
              <div className="form-group">
                <label>Rule Title</label>
                <input
                  type="text"
                  required
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                />
              </div>

              <div className="form-group">
                <label>Source Label (Evidence Citation)</label>
                <input
                  type="text"
                  required
                  value={sourceLabel}
                  onChange={(e) => setSourceLabel(e.target.value)}
                />
              </div>

              <div className="form-row-2">
                <div className="form-group">
                  <label>Pattern / Regex</label>
                  <input
                    type="text"
                    required
                    value={pattern}
                    onChange={(e) => setPattern(e.target.value)}
                  />
                </div>
                <div className="form-group">
                  <label>Severity</label>
                  <select value={severity} onChange={(e) => setSeverity(e.target.value)}>
                    <option value="high">High</option>
                    <option value="medium">Medium</option>
                    <option value="low">Low</option>
                  </select>
                </div>
              </div>

              <div className="form-group">
                <label>Description</label>
                <textarea
                  rows={2}
                  required
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                />
              </div>

              <div className="form-group">
                <label>Remedy Suggestion</label>
                <textarea
                  rows={2}
                  required
                  value={remedySuggestion}
                  onChange={(e) => setRemedySuggestion(e.target.value)}
                />
              </div>

              <div className="modal-actions-right">
                <button type="button" className="btn-secondary" onClick={() => setEditingRule(null)}>
                  Cancel
                </button>
                <button type="submit" disabled={loading} className="btn-primary">
                  {loading ? 'Saving...' : `Save as Version ${editingRule.version + 1}`}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Version History Modal */}
      {historyRule && (
        <div className="modal-backdrop">
          <div className="modal-card modal-lg">
            <div className="modal-header">
              <h3>Version History: {historyRule.rule_id}</h3>
              <button className="modal-close-btn" onClick={() => setHistoryRule(null)}>✕</button>
            </div>
            <div className="history-list">
              <div className="current-version-highlight">
                <div className="history-version-header">
                  <span className="version-pill">v{historyRule.version} (Active Version)</span>
                  <span className="history-date">Updated: {new Date(historyRule.updated_at).toLocaleString()} by {historyRule.updated_by}</span>
                </div>
                <p><strong>Title:</strong> {historyRule.title}</p>
                <p><strong>Source:</strong> {historyRule.source_label}</p>
                <p><strong>Pattern:</strong> <code>{historyRule.pattern}</code></p>
                <p><strong>Remedy:</strong> {historyRule.remedy_suggestion}</p>
              </div>

              <h4 className="past-versions-heading">Archived Prior Versions</h4>
              {historyRule.version_history.slice().reverse().map((past, i) => (
                <div key={i} className="past-version-card">
                  <div className="history-version-header">
                    <span className="version-pill muted">v{past.version}</span>
                    <span className="history-date">Archived: {new Date(past.updated_at).toLocaleString()} by {past.updated_by}</span>
                  </div>
                  <p><strong>Title:</strong> {past.title}</p>
                  <p><strong>Source:</strong> {past.source_label}</p>
                  <p><strong>Pattern:</strong> <code>{past.pattern}</code></p>
                  <p><strong>Remedy:</strong> {past.remedy_suggestion}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
