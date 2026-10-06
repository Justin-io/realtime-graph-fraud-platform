import React, { useState, useEffect } from 'react';
import { OverallDriftAssessment } from '../types';
import { AlertTriangle, CheckCircle, RefreshCw, Zap, Flame, ShieldAlert } from 'lucide-react';

export const DriftView: React.FC = () => {
  const [assessment, setAssessment] = useState<OverallDriftAssessment | null>(null);
  const [loading, setLoading] = useState(false);
  const [simulating, setSimulating] = useState(false);
  const [retraining, setRetraining] = useState(false);
  const [retrainEvent, setRetrainEvent] = useState<any>(null);

  const fetchDrift = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/monitoring/drift');
      if (res.ok) {
        const data = await res.json();
        setAssessment(data);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleSimulateDrift = async () => {
    setSimulating(true);
    try {
      const res = await fetch('/api/monitoring/simulate_drift', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ shift_feature: 'amount', multiplier: 4.8 }),
      });
      if (res.ok) {
        const data = await res.json();
        setAssessment(data.report);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setSimulating(false);
    }
  };

  const handleRetrain = async () => {
    setRetraining(true);
    try {
      const res = await fetch('/api/monitoring/retrain', { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        setRetrainEvent(data.event);
        await fetchDrift();
      }
    } catch (e) {
      console.error(e);
    } finally {
      setRetraining(false);
    }
  };

  useEffect(() => {
    fetchDrift();
  }, []);

  const isCritical = assessment?.overall_status === 'CRITICAL_DRIFT';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      
      {/* Top Drift Assessment Banner */}
      {assessment && (
        <div
          className="card"
          style={{
            background: isCritical
              ? 'linear-gradient(135deg, rgba(239, 68, 68, 0.2), rgba(15, 23, 42, 0.95))'
              : 'linear-gradient(135deg, rgba(16, 185, 129, 0.15), rgba(15, 23, 42, 0.95))',
            borderColor: isCritical ? '#ef4444' : 'rgba(16, 185, 129, 0.4)',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            flexWrap: 'wrap',
            gap: '1rem',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
            <div
              style={{
                width: 52,
                height: 52,
                borderRadius: 12,
                background: isCritical ? 'rgba(239, 68, 68, 0.25)' : 'rgba(16, 185, 129, 0.25)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: isCritical ? '#ef4444' : '#10b981',
              }}
            >
              {isCritical ? <Flame size={28} /> : <CheckCircle size={28} />}
            </div>
            <div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                Population Stability Index (PSI) Drift Monitor
              </div>
              <div style={{ fontSize: '1.4rem', fontWeight: 800, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                Status: {assessment.overall_status}
                <span className={`badge ${isCritical ? 'badge-red' : 'badge-green'}`}>
                  {isCritical ? 'RETRAINING REQUIRED' : 'POPULATION STABLE'}
                </span>
              </div>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                Max Feature PSI: <strong>{assessment.max_psi}</strong> (Threshold: &ge; 0.25 critical drift)
              </div>
            </div>
          </div>

          <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
            <button
              onClick={handleSimulateDrift}
              disabled={simulating}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.4rem',
                padding: '0.6rem 1rem',
                background: 'rgba(245, 158, 11, 0.2)',
                border: '1px solid #f59e0b',
                borderRadius: 6,
                color: '#fbbf24',
                fontSize: '0.8rem',
                fontWeight: 700,
              }}
            >
              <Zap size={14} />
              {simulating ? 'Injecting Shift...' : 'Simulate Sudden Population Drift'}
            </button>

            <button
              onClick={handleRetrain}
              disabled={retraining}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.4rem',
                padding: '0.6rem 1.2rem',
                background: 'linear-gradient(135deg, #0284c7, #38bdf8)',
                border: 'none',
                borderRadius: 6,
                color: '#fff',
                fontSize: '0.8rem',
                fontWeight: 700,
              }}
            >
              <RefreshCw size={14} className={retraining ? 'spin' : ''} />
              {retraining ? 'Retraining Champion...' : 'Trigger Automated Retraining'}
            </button>
          </div>
        </div>
      )}

      {/* Retraining Event Result Banner */}
      {retrainEvent && (
        <div className="card" style={{ background: 'rgba(56, 189, 248, 0.1)', borderColor: '#38bdf8' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
            <div style={{ fontWeight: 800, color: '#38bdf8' }}>
              🎉 Retraining Workflow Executed: {retrainEvent.event_id}
            </div>
            <span className="badge badge-green">
              {retrainEvent.deployed ? 'CHALLENGER DEPLOYED AS CHAMPION' : 'RETAINED PREVIOUS CHAMPION'}
            </span>
          </div>
          <div style={{ fontSize: '0.825rem', color: 'var(--text-secondary)' }}>
            Previous PR-AUC: <strong>{(retrainEvent.previous_pr_auc * 100).toFixed(1)}%</strong> &rarr; New PR-AUC: <strong>{(retrainEvent.new_pr_auc * 100).toFixed(1)}%</strong> (Gain: +{(retrainEvent.performance_gain * 100).toFixed(2)}%)
          </div>
        </div>
      )}

      {/* Feature Drift Statistics Table */}
      <div className="card">
        <h2 style={{ fontSize: '1.05rem', fontWeight: 700, marginBottom: '0.75rem' }}>
          Feature Distribution Drift Analysis
        </h2>

        <div style={{ overflowX: 'auto', maxHeight: 520, overflowY: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.825rem' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border-color)', textAlign: 'left', color: 'var(--text-muted)' }}>
                <th style={{ padding: '0.6rem 0.75rem' }}>FEATURE NAME</th>
                <th style={{ padding: '0.6rem 0.75rem' }}>PSI SCORE</th>
                <th style={{ padding: '0.6rem 0.75rem' }}>KS STATISTIC</th>
                <th style={{ padding: '0.6rem 0.75rem' }}>KS P-VALUE</th>
                <th style={{ padding: '0.6rem 0.75rem' }}>DRIFT STATUS</th>
                <th style={{ padding: '0.6rem 0.75rem' }}>RETRAINING ACTION</th>
              </tr>
            </thead>
            <tbody>
              {assessment &&
                Object.values(assessment.feature_reports || {}).map((report) => {
                  const isFeatDrift = report.drift_status === 'CRITICAL_DRIFT';
                  const isModDrift = report.drift_status === 'MODERATE_DRIFT';

                  return (
                    <tr
                      key={report.feature_name}
                      style={{
                        borderBottom: '1px solid rgba(51, 65, 85, 0.4)',
                        background: isFeatDrift ? 'rgba(239, 68, 68, 0.08)' : 'transparent',
                      }}
                    >
                      <td style={{ padding: '0.65rem 0.75rem', fontFamily: 'JetBrains Mono', fontWeight: 600 }}>
                        {report.feature_name}
                      </td>

                      <td style={{ padding: '0.65rem 0.75rem', fontWeight: 700, color: isFeatDrift ? '#f87171' : isModDrift ? '#fbbf24' : '#34d399' }}>
                        {report.psi_score.toFixed(4)}
                      </td>

                      <td style={{ padding: '0.65rem 0.75rem', fontFamily: 'JetBrains Mono' }}>
                        {report.ks_statistic.toFixed(4)}
                      </td>

                      <td style={{ padding: '0.65rem 0.75rem', fontFamily: 'JetBrains Mono', color: 'var(--text-muted)' }}>
                        {report.ks_p_value < 0.0001 ? '< 0.0001' : report.ks_p_value.toFixed(4)}
                      </td>

                      <td style={{ padding: '0.65rem 0.75rem' }}>
                        <span className={`badge ${isFeatDrift ? 'badge-red' : isModDrift ? 'badge-amber' : 'badge-green'}`}>
                          {report.drift_status}
                        </span>
                      </td>

                      <td style={{ padding: '0.65rem 0.75rem' }}>
                        {report.retraining_recommended ? (
                          <span style={{ color: '#f87171', fontWeight: 700 }}>⚠️ Retrain Triggered</span>
                        ) : (
                          <span style={{ color: 'var(--text-muted)' }}>In Tolerance</span>
                        )}
                      </td>
                    </tr>
                  );
                })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
