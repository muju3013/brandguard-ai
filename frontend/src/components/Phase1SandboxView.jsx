import React, { useState } from 'react';
import { api } from '../api';

export default function Phase1SandboxView() {
  const [draft, setDraft] = useState('Our skincare product cures acne in 24 hours. Guaranteed results!');
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  async function run() {
    setLoading(true);
    setError('');
    setResult(null);
    try {
      const data = await api.runPhase1Review(draft, 'social');
      setResult(data);
    } catch (e) {
      setError(e.message + ' — check that FastAPI is running.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="phase1-container">
      <div className="phase1-header-banner">
        <div>
          <h2>Phase 1 Starter Demo Sandbox</h2>
          <p>
            Preserved backwards-compatible sandbox executing against legacy <code>/review</code> pattern endpoint.
          </p>
        </div>
        <span className="tag-pill">Legacy Starter</span>
      </div>

      <section className="panel">
        <div className="tag">DETERMINISTIC DEMO · NOT AI-VERIFIED</div>
        <h2>Review a marketing draft</h2>
        <label htmlFor="phase1-draft">Draft content</label>
        <textarea
          id="phase1-draft"
          rows={6}
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
        />
        <button disabled={!draft.trim() || loading} onClick={run} className="btn-primary">
          {loading ? 'Checking...' : 'Run pre-check'}
        </button>
      </section>

      {error && <p role="alert" className="error">{error}</p>}

      {result && (
        <section className="panel">
          <h2>Review result</h2>
          <p><strong>Outcome:</strong> {result.outcome.replace('_', ' ')}</p>
          <p className="muted">{result.note}</p>
          {result.findings.length === 0 ? (
            <p>No demo-pattern matches. This is not proof of compliance.</p>
          ) : (
            result.findings.map((f, i) => (
              <article key={i}>
                <div className="tag">{f.rule_id} · {f.severity}</div>
                <h3>“{f.matched_text}”</h3>
                <p>{f.reason}</p>
                <p><strong>Suggested action:</strong> {f.suggestion}</p>
                <small>Position: {f.start}–{f.end} · Evidence: {f.evidence_status}</small>
              </article>
            ))
          )}
        </section>
      )}
    </div>
  );
}
