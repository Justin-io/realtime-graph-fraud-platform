import React, { useState, useEffect } from 'react';
import { AnalystDecision, AuditLogEntry } from '../types';
import { ShieldCheck, UserCheck, AlertTriangle, Send, History, FileText } from 'lucide-react';

export const InvestigationView: React.FC = () => {
  const [alerts, setAlerts] = useState<any[]>([]);
  const [decisions, setDecisions] = useState<AnalystDecision[]>([]);
  const [auditLogs, setAuditLogs] = useState<AuditLogEntry[]>([]);
  const [selectedAlert, setSelectedAlert] = useState<any>(null);

  // Form fields
  const [decisionType, setDecisionType] = useState('CONFIRM_FRAUD');
  const [analystNotes, setAnalystNotes] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const fetchInvestigationData = async () => {
    try {
      const [alertsRes, decsRes, auditRes] = await Promise.all([
        fetch('/api/investigation/alerts'),
        fetch('/api/investigation/decisions'),
        fetch('/api/investigation/audit_log'),
      ]);

      if (alertsRes.ok) {
        const data = await alertsRes.json();
        setAlerts(data.alerts || []);
        if (data.alerts && data.alerts.length > 0 && !selectedAlert) {
          setSelectedAlert(data.alerts[0]);
        }
      }
      if (decsRes.ok) {
        const data = await decsRes.json();
        setDecisions(data.decisions || []);
      }
      if (auditRes.ok) {
        const data = await auditRes.json();
        setAuditLogs(data.audit_logs || []);
      }
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    fetchInvestigationData();
    const interval = setInterval(fetchInvestigationData, 4000);
    return () => clearInterval(interval);
  }, []);

  const handleSubmitDecision = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedAlert || !analystNotes.trim()) return;

    setSubmitting(true);
    try {
      const res = await fetch('/api/investigation/decision', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          tx_id: selectedAlert.tx_id,
          user_id: selectedAlert.user_id,
          amount: selectedAlert.amount,
          analyst_id: 'analyst_sarah_chen',
          decision: decisionType,
          notes: analystNotes,
          original_risk_score: selectedAlert.risk_score,
          original_decision: selectedAlert.decision,
        }),
      });

      if (res.ok) {
        setAnalystNotes('');
        await fetchInvestigationData();
      }
    } catch (e) {
      console.error(e);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      
      {/* Investigation Split: Alerts Queue + Decision Workspace */}
      <div style={{ display: 'grid', gridTemplateColumns: '1.1fr 1.9fr', gap: '1.5rem' }}>
        
        {/* Alerts Queue */}
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
            <div>
              <h2 style={{ fontSize: '1.05rem', fontWeight: 700 }}>Flagged Alerts Queue</h2>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Requiring human review decision</div>
            </div>
            <span className="badge badge-amber">{alerts.length} PENDING</span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem', maxHeight: 520, overflowY: 'auto' }}>
            {alerts.length > 0 ? (
              alerts.map((alt) => {
                const isSelected = selectedAlert?.tx_id === alt.tx_id;
                return (
                  <div
                    key={alt.tx_id}
                    onClick={() => setSelectedAlert(alt)}
                    style={{
                      padding: '0.75rem',
                      borderRadius: 8,
                      background: isSelected ? 'rgba(56, 189, 248, 0.15)' : 'rgba(30, 41, 59, 0.5)',
                      border: isSelected ? '1px solid #38bdf8' : '1px solid var(--border-color)',
                      cursor: 'pointer',
                      transition: 'all 0.15s ease',
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.3rem' }}>
                      <span style={{ fontFamily: 'JetBrains Mono', fontWeight: 700, color: '#38bdf8' }}>{alt.tx_id}</span>
                      <span className={`badge ${alt.decision === 'DECLINE' ? 'badge-red' : 'badge-amber'}`}>
                        {alt.decision}
                      </span>
                    </div>

                    <div style={{ fontSize: '0.775rem', color: 'var(--text-secondary)' }}>
                      User: <strong>{alt.user_id}</strong> • Amount: <strong>${alt.amount.toFixed(2)}</strong>
                    </div>

                    <div style={{ fontSize: '0.725rem', color: alt.risk_score >= 80 ? '#f87171' : '#fbbf24', marginTop: '0.3rem', fontWeight: 600 }}>
                      Risk Score: {alt.risk_score} / 100 • {alt.attack_type || 'ALERT'}
                    </div>
                  </div>
                );
              })
            ) : (
              <div style={{ color: 'var(--text-muted)', fontSize: '0.8rem', padding: '2rem', textAlign: 'center' }}>
                No pending high-risk transactions requiring review.
              </div>
            )}
          </div>
        </div>

        {/* Selected Alert Details & Decision Form */}
        <div className="card">
          {selectedAlert ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid var(--border-color)', paddingBottom: '0.75rem' }}>
                <div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>CASE FILE</div>
                  <h3 style={{ fontSize: '1.2rem', fontWeight: 800, fontFamily: 'JetBrains Mono' }}>
                    {selectedAlert.tx_id}
                  </h3>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>ORIGINAL SYSTEM DECISION</div>
                  <span className={`badge ${selectedAlert.decision === 'DECLINE' ? 'badge-red' : 'badge-amber'}`}>
                    {selectedAlert.decision} (SCORE: {selectedAlert.risk_score})
                  </span>
                </div>
              </div>

              {/* Transaction Key Facts */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))', gap: '0.75rem' }}>
                <div style={{ background: 'var(--bg-secondary)', padding: '0.6rem', borderRadius: 6 }}>
                  <div style={{ fontSize: '0.675rem', color: 'var(--text-muted)' }}>USER ID</div>
                  <strong style={{ fontSize: '0.85rem' }}>{selectedAlert.user_id}</strong>
                </div>
                <div style={{ background: 'var(--bg-secondary)', padding: '0.6rem', borderRadius: 6 }}>
                  <div style={{ fontSize: '0.675rem', color: 'var(--text-muted)' }}>AMOUNT</div>
                  <strong style={{ fontSize: '0.85rem' }}>${selectedAlert.amount.toFixed(2)}</strong>
                </div>
                <div style={{ background: 'var(--bg-secondary)', padding: '0.6rem', borderRadius: 6 }}>
                  <div style={{ fontSize: '0.675rem', color: 'var(--text-muted)' }}>CARD ID</div>
                  <strong style={{ fontSize: '0.85rem' }}>{selectedAlert.card_id || 'CRD_LINKED'}</strong>
                </div>
                <div style={{ background: 'var(--bg-secondary)', padding: '0.6rem', borderRadius: 6 }}>
                  <div style={{ fontSize: '0.675rem', color: 'var(--text-muted)' }}>HARDWARE DEVICE</div>
                  <strong style={{ fontSize: '0.85rem' }}>{selectedAlert.device_id || 'DEV_LINKED'}</strong>
                </div>
              </div>

              {/* Evidence & Rules */}
              <div>
                <div style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-secondary)', marginBottom: '0.4rem' }}>
                  AUTOMATED REASONING EVIDENCE:
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.3rem' }}>
                  {selectedAlert.triggered_rules && selectedAlert.triggered_rules.map((r: string, i: number) => (
                    <div key={i} style={{ background: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.3)', padding: '0.4rem 0.6rem', borderRadius: 6, fontSize: '0.75rem', color: '#f87171' }}>
                      🚨 {r}
                    </div>
                  ))}
                  {selectedAlert.reason_codes && selectedAlert.reason_codes.map((rc: string, i: number) => (
                    <div key={i} style={{ background: 'rgba(56, 189, 248, 0.1)', border: '1px solid rgba(56, 189, 248, 0.25)', padding: '0.4rem 0.6rem', borderRadius: 6, fontSize: '0.75rem', color: '#38bdf8' }}>
                      ℹ️ {rc}
                    </div>
                  ))}
                </div>
              </div>

              {/* Decision Form */}
              <form onSubmit={handleSubmitDecision} style={{ borderTop: '1px solid var(--border-color)', paddingTop: '1rem', display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                <div style={{ fontSize: '0.8rem', fontWeight: 700 }}>HUMAN-IN-THE-LOOP ANALYST DETERMINATION:</div>

                {/* Radio options */}
                <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                  {[
                    { id: 'CONFIRM_FRAUD', label: 'Confirm Fraud (Decline)', color: '#ef4444' },
                    { id: 'FALSE_POSITIVE_APPROVE', label: 'False Positive (Approve)', color: '#10b981' },
                    { id: 'ESCALATE_DISPUTE', label: 'Escalate to Dispute', color: '#f59e0b' },
                  ].map((opt) => (
                    <button
                      key={opt.id}
                      type="button"
                      onClick={() => setDecisionType(opt.id)}
                      style={{
                        padding: '0.5rem 0.9rem',
                        borderRadius: 6,
                        border: decisionType === opt.id ? `2px solid ${opt.color}` : '1px solid var(--border-color)',
                        background: decisionType === opt.id ? 'rgba(15, 23, 42, 0.9)' : 'transparent',
                        color: decisionType === opt.id ? opt.color : 'var(--text-secondary)',
                        fontWeight: 700,
                        fontSize: '0.775rem',
                      }}
                    >
                      {opt.label}
                    </button>
                  ))}
                </div>

                {/* Notes textarea */}
                <div>
                  <textarea
                    rows={3}
                    placeholder="Enter analyst justification notes, verified graph indicators, or merchant dispute notes..."
                    value={analystNotes}
                    onChange={(e) => setAnalystNotes(e.target.value)}
                    style={{
                      width: '100%',
                      background: 'var(--bg-secondary)',
                      border: '1px solid var(--border-color)',
                      borderRadius: 6,
                      padding: '0.5rem',
                      fontSize: '0.8rem',
                      color: 'var(--text-primary)',
                      outline: 'none',
                    }}
                  />
                </div>

                <button
                  type="submit"
                  disabled={submitting || !analystNotes.trim()}
                  style={{
                    padding: '0.65rem 1rem',
                    background: 'linear-gradient(135deg, #0284c7, #38bdf8)',
                    color: '#fff',
                    border: 'none',
                    borderRadius: 6,
                    fontWeight: 700,
                    fontSize: '0.85rem',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '0.5rem',
                    cursor: submitting || !analystNotes.trim() ? 'not-allowed' : 'pointer',
                    opacity: submitting || !analystNotes.trim() ? 0.6 : 1,
                  }}
                >
                  <Send size={14} />
                  {submitting ? 'Recording Audit Entry...' : 'Submit & Close Investigation Alert'}
                </button>
              </form>
            </div>
          ) : (
            <div style={{ color: 'var(--text-muted)', textAlign: 'center', padding: '3rem' }}>
              Select an alert from the queue to investigate.
            </div>
          )}
        </div>
      </div>

      {/* Bottom Historical Logs: Decisions & Audit Trail */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem' }}>
        
        {/* Past Analyst Decisions */}
        <div className="card">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', marginBottom: '0.75rem' }}>
            <UserCheck size={16} style={{ color: '#38bdf8' }} />
            <h3 style={{ fontSize: '0.95rem', fontWeight: 700 }}>Analyst Determination Log</h3>
          </div>

          <div style={{ maxHeight: 280, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            {decisions.length > 0 ? (
              decisions.map((d) => (
                <div key={d.decision_id} style={{ background: 'var(--bg-secondary)', padding: '0.6rem 0.75rem', borderRadius: 6, border: '1px solid var(--border-color)', fontSize: '0.75rem' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 2 }}>
                    <span style={{ fontFamily: 'JetBrains Mono', color: '#38bdf8', fontWeight: 700 }}>{d.tx_id}</span>
                    <span className={`badge ${d.decision === 'CONFIRM_FRAUD' ? 'badge-red' : d.decision === 'FALSE_POSITIVE_APPROVE' ? 'badge-green' : 'badge-amber'}`}>
                      {d.decision}
                    </span>
                  </div>
                  <div style={{ color: 'var(--text-secondary)' }}>{d.notes}</div>
                  <div style={{ color: 'var(--text-muted)', fontSize: '0.675rem', marginTop: 2 }}>
                    By {d.analyst_id}
                  </div>
                </div>
              ))
            ) : (
              <div style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>No decisions recorded yet.</div>
            )}
          </div>
        </div>

        {/* Chronological Audit Trail */}
        <div className="card">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', marginBottom: '0.75rem' }}>
            <History size={16} style={{ color: '#a855f7' }} />
            <h3 style={{ fontSize: '0.95rem', fontWeight: 700 }}>Chronological System Audit Trail</h3>
          </div>

          <div style={{ maxHeight: 280, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            {auditLogs.map((entry) => (
              <div key={entry.entry_id} style={{ background: 'var(--bg-secondary)', padding: '0.6rem 0.75rem', borderRadius: 6, border: '1px solid var(--border-color)', fontSize: '0.75rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 2 }}>
                  <span className="badge badge-purple" style={{ fontSize: '0.65rem' }}>{entry.event_type}</span>
                  <span style={{ fontFamily: 'JetBrains Mono', color: 'var(--text-muted)', fontSize: '0.675rem' }}>
                    {entry.entry_id}
                  </span>
                </div>
                <div style={{ fontFamily: 'JetBrains Mono', color: 'var(--text-secondary)', fontSize: '0.7rem' }}>
                  {JSON.stringify(entry.details)}
                </div>
              </div>
            ))}
          </div>
        </div>

      </div>
    </div>
  );
};
