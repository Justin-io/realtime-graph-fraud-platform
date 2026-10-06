import React, { useState } from 'react';
import { ScoringResult } from '../types';
import { ShieldAlert, CheckCircle, AlertTriangle, Filter, Pause, Play, ChevronRight } from 'lucide-react';

interface LiveStreamViewProps {
  transactions: ScoringResult[];
  isPaused: boolean;
  setIsPaused: (val: boolean) => void;
  onSelectEntity: (entityId: string) => void;
}

export const LiveStreamView: React.FC<LiveStreamViewProps> = ({
  transactions,
  isPaused,
  setIsPaused,
  onSelectEntity,
}) => {
  const [filter, setFilter] = useState<'ALL' | 'HIGH_RISK' | 'ATTACKS_ONLY'>('ALL');
  const [selectedTx, setSelectedTx] = useState<ScoringResult | null>(null);

  // Compute stats
  const total = transactions.length;
  const approves = transactions.filter((t) => t.decision === 'APPROVE').length;
  const challenges = transactions.filter((t) => t.decision === 'CHALLENGE').length;
  const declines = transactions.filter((t) => t.decision === 'DECLINE').length;
  const avgLatency = transactions.length
    ? (transactions.reduce((acc, t) => acc + t.latency_ms, 0) / transactions.length).toFixed(1)
    : '0.0';

  const filtered = transactions.filter((t) => {
    if (filter === 'HIGH_RISK') return t.decision === 'DECLINE' || t.decision === 'CHALLENGE';
    if (filter === 'ATTACKS_ONLY') return t.attack_type && t.attack_type !== 'BENIGN';
    return true;
  });

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      
      {/* KPI Stats Strip */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '1rem' }}>
        <div className="card" style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <div style={{ width: 44, height: 44, borderRadius: 10, background: 'rgba(56, 189, 248, 0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#38bdf8' }}>
            📊
          </div>
          <div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Ingested Volume</div>
            <div style={{ fontSize: '1.4rem', fontWeight: 800 }}>{total.toLocaleString()}</div>
          </div>
        </div>

        <div className="card" style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <div style={{ width: 44, height: 44, borderRadius: 10, background: 'rgba(16, 185, 129, 0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#10b981' }}>
            <CheckCircle size={22} />
          </div>
          <div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Frictionless Approvals</div>
            <div style={{ fontSize: '1.4rem', fontWeight: 800, color: '#34d399' }}>{approves}</div>
          </div>
        </div>

        <div className="card" style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <div style={{ width: 44, height: 44, borderRadius: 10, background: 'rgba(245, 158, 11, 0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#f59e0b' }}>
            <AlertTriangle size={22} />
          </div>
          <div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Step-up Challenges</div>
            <div style={{ fontSize: '1.4rem', fontWeight: 800, color: '#fbbf24' }}>{challenges}</div>
          </div>
        </div>

        <div className="card" style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <div style={{ width: 44, height: 44, borderRadius: 10, background: 'rgba(239, 68, 68, 0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#ef4444' }}>
            <ShieldAlert size={22} />
          </div>
          <div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Prevented Declines</div>
            <div style={{ fontSize: '1.4rem', fontWeight: 800, color: '#f87171' }}>{declines}</div>
          </div>
        </div>

        <div className="card" style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <div style={{ width: 44, height: 44, borderRadius: 10, background: 'rgba(168, 85, 247, 0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#a855f7' }}>
            ⚡
          </div>
          <div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Sub-Second Latency</div>
            <div style={{ fontSize: '1.4rem', fontWeight: 800, color: '#c084fc' }}>{avgLatency} <span style={{ fontSize: '0.8rem', fontWeight: 500 }}>ms</span></div>
          </div>
        </div>
      </div>

      {/* Stream Controls & Table Layout */}
      <div style={{ display: 'grid', gridTemplateColumns: selectedTx ? '2fr 1fr' : '1fr', gap: '1.5rem' }}>
        
        {/* Table View */}
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem', flexWrap: 'wrap', gap: '0.5rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
              <h2 style={{ fontSize: '1.1rem', fontWeight: 700 }}>Real-Time Ingestion Feed</h2>
              <span className="badge badge-blue">{filtered.length} EVENTS</span>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              {/* Filter */}
              <div style={{ display: 'flex', alignItems: 'center', background: 'var(--bg-secondary)', borderRadius: 6, padding: '0.2rem 0.5rem', border: '1px solid var(--border-color)' }}>
                <Filter size={14} style={{ color: 'var(--text-muted)', marginRight: 6 }} />
                <select
                  value={filter}
                  onChange={(e) => setFilter(e.target.value as any)}
                  style={{ background: 'transparent', border: 'none', fontSize: '0.75rem', color: 'var(--text-primary)', outline: 'none' }}
                >
                  <option value="ALL" style={{ background: '#0f172a' }}>All Transactions</option>
                  <option value="HIGH_RISK" style={{ background: '#0f172a' }}>Threats Only (Challenge/Decline)</option>
                  <option value="ATTACKS_ONLY" style={{ background: '#0f172a' }}>Adversarial Attacks Only</option>
                </select>
              </div>

              {/* Pause/Resume */}
              <button
                onClick={() => setIsPaused(!isPaused)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.3rem',
                  padding: '0.35rem 0.75rem',
                  background: isPaused ? 'rgba(16, 185, 129, 0.2)' : 'rgba(239, 68, 68, 0.2)',
                  border: isPaused ? '1px solid #10b981' : '1px solid #ef4444',
                  borderRadius: 6,
                  color: isPaused ? '#34d399' : '#f87171',
                  fontSize: '0.75rem',
                  fontWeight: 600,
                }}
              >
                {isPaused ? <Play size={12} /> : <Pause size={12} />}
                {isPaused ? 'Resume Stream' : 'Pause Stream'}
              </button>
            </div>
          </div>

          <div style={{ overflowX: 'auto', maxHeight: 600, overflowY: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.825rem' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border-color)', textAlign: 'left', color: 'var(--text-muted)' }}>
                  <th style={{ padding: '0.6rem 0.75rem' }}>TX ID</th>
                  <th style={{ padding: '0.6rem 0.75rem' }}>USER & ENTITY</th>
                  <th style={{ padding: '0.6rem 0.75rem' }}>AMOUNT</th>
                  <th style={{ padding: '0.6rem 0.75rem' }}>RISK SCORE</th>
                  <th style={{ padding: '0.6rem 0.75rem' }}>DECISION</th>
                  <th style={{ padding: '0.6rem 0.75rem' }}>ATTACK / PATTERN</th>
                  <th style={{ padding: '0.6rem 0.75rem' }}>LATENCY</th>
                  <th style={{ padding: '0.6rem 0.75rem' }}>ACTIONS</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((tx) => {
                  const isDecline = tx.decision === 'DECLINE';
                  const isChallenge = tx.decision === 'CHALLENGE';
                  const isAttack = tx.attack_type && tx.attack_type !== 'BENIGN' && tx.attack_type !== 'API_SUBMITTED';

                  return (
                    <tr
                      key={tx.tx_id}
                      onClick={() => setSelectedTx(tx)}
                      style={{
                        borderBottom: '1px solid rgba(51, 65, 85, 0.4)',
                        cursor: 'pointer',
                        background: selectedTx?.tx_id === tx.tx_id ? 'rgba(56, 189, 248, 0.1)' : 'transparent',
                        transition: 'background 0.15s ease',
                      }}
                      onMouseEnter={(e) => (e.currentTarget.style.background = 'rgba(30, 41, 59, 0.6)')}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.background =
                          selectedTx?.tx_id === tx.tx_id ? 'rgba(56, 189, 248, 0.1)' : 'transparent';
                      }}
                    >
                      <td style={{ padding: '0.65rem 0.75rem', fontFamily: 'JetBrains Mono', color: 'var(--color-blue)' }}>
                        {tx.tx_id}
                      </td>

                      <td style={{ padding: '0.65rem 0.75rem' }}>
                        <div
                          onClick={(e) => {
                            e.stopPropagation();
                            onSelectEntity(tx.user_id);
                          }}
                          style={{ color: '#38bdf8', fontWeight: 600, textDecoration: 'underline', cursor: 'pointer' }}
                        >
                          {tx.user_id}
                        </div>
                      </td>

                      <td style={{ padding: '0.65rem 0.75rem', fontWeight: 700 }}>
                        ${tx.amount.toFixed(2)}
                      </td>

                      <td style={{ padding: '0.65rem 0.75rem' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                          <span style={{
                            fontWeight: 800,
                            color: isDecline ? '#f87171' : isChallenge ? '#fbbf24' : '#34d399',
                            width: 32,
                          }}>
                            {tx.risk_score}
                          </span>
                          <div style={{ width: 60, height: 6, background: '#1e293b', borderRadius: 3, overflow: 'hidden' }}>
                            <div
                              style={{
                                width: `${Math.min(100, tx.risk_score)}%`,
                                height: '100%',
                                background: isDecline ? '#ef4444' : isChallenge ? '#f59e0b' : '#10b981',
                              }}
                            />
                          </div>
                        </div>
                      </td>

                      <td style={{ padding: '0.65rem 0.75rem' }}>
                        <span className={`badge ${isDecline ? 'badge-red' : isChallenge ? 'badge-amber' : 'badge-green'}`}>
                          {tx.decision}
                        </span>
                      </td>

                      <td style={{ padding: '0.65rem 0.75rem' }}>
                        {isAttack ? (
                          <span className="badge badge-purple" style={{ fontSize: '0.65rem' }}>
                            ⚠️ {tx.attack_type}
                          </span>
                        ) : (
                          <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>Normal Spend</span>
                        )}
                      </td>

                      <td style={{ padding: '0.65rem 0.75rem', fontFamily: 'JetBrains Mono', color: 'var(--text-muted)' }}>
                        {tx.latency_ms}ms
                      </td>

                      <td style={{ padding: '0.65rem 0.75rem' }}>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            onSelectEntity(tx.user_id);
                          }}
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '0.2rem',
                            padding: '0.2rem 0.45rem',
                            borderRadius: 4,
                            background: 'rgba(56, 189, 248, 0.15)',
                            border: '1px solid rgba(56, 189, 248, 0.3)',
                            color: '#38bdf8',
                            fontSize: '0.7rem',
                          }}
                        >
                          Graph <ChevronRight size={12} />
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        {/* Selected Transaction Inspector Drawer */}
        {selectedTx && (
          <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: '1rem', height: 'fit-content' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid var(--border-color)', paddingBottom: '0.75rem' }}>
              <div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Transaction Deep-Dive</div>
                <div style={{ fontSize: '1rem', fontWeight: 800, fontFamily: 'JetBrains Mono' }}>{selectedTx.tx_id}</div>
              </div>
              <button
                onClick={() => setSelectedTx(null)}
                style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', fontSize: '1.2rem' }}
              >
                ✕
              </button>
            </div>

            {/* Decision & Score */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'var(--bg-secondary)', padding: '0.75rem', borderRadius: 8 }}>
              <div>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>DECISION</div>
                <span className={`badge ${selectedTx.decision === 'DECLINE' ? 'badge-red' : selectedTx.decision === 'CHALLENGE' ? 'badge-amber' : 'badge-green'}`}>
                  {selectedTx.decision}
                </span>
              </div>
              <div>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>RISK SCORE</div>
                <div style={{ fontSize: '1.2rem', fontWeight: 800, color: selectedTx.decision === 'DECLINE' ? '#f87171' : '#34d399' }}>
                  {selectedTx.risk_score} / 100
                </div>
              </div>
              <div>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>LATENCY</div>
                <div style={{ fontSize: '1.1rem', fontWeight: 700, fontFamily: 'JetBrains Mono' }}>{selectedTx.latency_ms} ms</div>
              </div>
            </div>

            {/* Model Breakdown */}
            <div>
              <div style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-secondary)', marginBottom: '0.4rem' }}>
                8-MODEL PROBABILITY MATRIX:
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.4rem' }}>
                {Object.entries(selectedTx.model_breakdown || {}).map(([model, prob]) => (
                  <div key={model} style={{ background: 'var(--bg-secondary)', padding: '0.4rem 0.6rem', borderRadius: 6, fontSize: '0.75rem' }}>
                    <div style={{ color: 'var(--text-muted)', fontSize: '0.675rem' }}>{model}</div>
                    <div style={{ fontWeight: 700, color: prob > 0.5 ? '#f87171' : '#38bdf8' }}>
                      {(prob * 100).toFixed(1)}% risk
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Triggered Rules & Reasons */}
            <div>
              <div style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-secondary)', marginBottom: '0.4rem' }}>
                TRIGGERED HEURISTICS & REASONS:
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.3rem' }}>
                {selectedTx.triggered_rules && selectedTx.triggered_rules.length > 0 ? (
                  selectedTx.triggered_rules.map((rule, idx) => (
                    <div key={idx} style={{ background: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.3)', padding: '0.4rem 0.6rem', borderRadius: 6, fontSize: '0.725rem', color: '#f87171' }}>
                      🚨 {rule}
                    </div>
                  ))
                ) : (
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>No hard violation rules triggered.</div>
                )}
                {selectedTx.reason_codes && selectedTx.reason_codes.map((rc, idx) => (
                  <div key={idx} style={{ background: 'rgba(56, 189, 248, 0.1)', border: '1px solid rgba(56, 189, 248, 0.25)', padding: '0.4rem 0.6rem', borderRadius: 6, fontSize: '0.725rem', color: '#38bdf8' }}>
                    ℹ️ {rc}
                  </div>
                ))}
              </div>
            </div>

            {/* Action button */}
            <button
              onClick={() => onSelectEntity(selectedTx.user_id)}
              style={{
                marginTop: '0.5rem',
                padding: '0.6rem',
                background: 'linear-gradient(135deg, #0284c7, #38bdf8)',
                color: '#fff',
                border: 'none',
                borderRadius: 6,
                fontWeight: 700,
                fontSize: '0.8rem',
              }}
            >
              Explore 2-Hop Graph Ego-Network
            </button>
          </div>
        )}
      </div>
    </div>
  );
};
