import React, { useState } from 'react';

export default function AuditTrailView({ auditLogs, onRefresh }) {
  const [filterAction, setFilterAction] = useState('all');
  const [filterEntity, setFilterEntity] = useState('');
  const [selectedLog, setSelectedLog] = useState(null);

  const filteredLogs = auditLogs.filter((log) => {
    const matchesAction = filterAction === 'all' || log.action === filterAction;
    const matchesEntity =
      !filterEntity.trim() ||
      log.entity_id.toLowerCase().includes(filterEntity.toLowerCase()) ||
      log.actor_email.toLowerCase().includes(filterEntity.toLowerCase());
    return matchesAction && matchesEntity;
  });

  return (
    <div className="audit-trail-container">
      <div className="audit-header-banner">
        <div>
          <h2>Governance Audit Trail</h2>
          <p>
            Immutable, chronological record of all compliance checks, submissions, approvals,
            revisions, and guideline version updates.
          </p>
        </div>
        <button className="btn-secondary btn-sm" onClick={onRefresh}>
          ↻ Refresh Trail
        </button>
      </div>

      <div className="audit-filters-bar">
        <div className="filter-group">
          <label>Filter Action:</label>
          <select value={filterAction} onChange={(e) => setFilterAction(e.target.value)}>
            <option value="all">All Actions ({auditLogs.length})</option>
            <option value="created">Draft Created</option>
            <option value="checked">Pre-check Run</option>
            <option value="submitted">Draft Submitted</option>
            <option value="approved">Draft Approved</option>
            <option value="changes_requested">Changes Requested</option>
            <option value="updated">Draft Revised</option>
            <option value="guideline_created">Guideline Created</option>
            <option value="guideline_updated">Guideline Updated</option>
            <option value="guideline_deactivated">Guideline Deactivated</option>
          </select>
        </div>

        <div className="filter-group search-flex">
          <label>Search Entity or Actor:</label>
          <input
            type="text"
            placeholder="e.g. draft_101 or user email..."
            value={filterEntity}
            onChange={(e) => setFilterEntity(e.target.value)}
          />
        </div>
      </div>

      <div className="audit-table-wrapper">
        <table className="audit-table">
          <thead>
            <tr>
              <th>Timestamp</th>
              <th>Action</th>
              <th>Entity</th>
              <th>Actor</th>
              <th>Role</th>
              <th>Details</th>
            </tr>
          </thead>
          <tbody>
            {filteredLogs.length === 0 ? (
              <tr>
                <td colSpan={6} className="table-empty-cell">
                  No audit records match the current filters.
                </td>
              </tr>
            ) : (
              filteredLogs.map((log) => (
                <tr key={log.id} onClick={() => setSelectedLog(log)} className="clickable-row">
                  <td className="timestamp-cell">
                    {new Date(log.timestamp).toLocaleString()}
                  </td>
                  <td>
                    <span className={`action-badge action-${log.action}`}>
                      {log.action.replace('_', ' ').toUpperCase()}
                    </span>
                  </td>
                  <td>
                    <span className="entity-type-badge">{log.entity_type}</span>{' '}
                    <code>{log.entity_id}</code>
                  </td>
                  <td className="actor-email-cell">{log.actor_email}</td>
                  <td>
                    <span className={`role-badge role-${log.actor_role}`}>
                      {log.actor_role.toUpperCase()}
                    </span>
                  </td>
                  <td className="details-summary-cell">
                    {JSON.stringify(log.details)}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {selectedLog && (
        <div className="modal-backdrop">
          <div className="modal-card">
            <div className="modal-header">
              <h3>Audit Event Inspection</h3>
              <button className="modal-close-btn" onClick={() => setSelectedLog(null)}>✕</button>
            </div>
            <div className="audit-detail-body">
              <p><strong>Event ID:</strong> <code>{selectedLog.id}</code></p>
              <p><strong>Timestamp:</strong> {new Date(selectedLog.timestamp).toISOString()}</p>
              <p><strong>Action:</strong> <span className={`action-badge action-${selectedLog.action}`}>{selectedLog.action}</span></p>
              <p><strong>Actor:</strong> {selectedLog.actor_email} ({selectedLog.actor_id})</p>
              <p><strong>Role:</strong> {selectedLog.actor_role}</p>
              <p><strong>Entity:</strong> {selectedLog.entity_type} · <code>{selectedLog.entity_id}</code></p>
              <label>Event Metadata Payload</label>
              <pre className="json-inspector">{JSON.stringify(selectedLog.details, null, 2)}</pre>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
