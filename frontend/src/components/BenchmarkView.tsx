import React, { useState, useEffect } from 'react';
import { BenchmarkReport, ModelScorecard } from '../types';
import { Award, TrendingUp, RefreshCw, DollarSign, Clock, ShieldCheck } from 'lucide-react';

export const BenchmarkView: React.FC = () => {
  const [report, setReport] = useState<BenchmarkReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [runningBenchmark, setRunningBenchmark] = useState(false);

  const fetchBenchmark = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/benchmark');
      if (res.ok) {
        const data = await res.json();
        setReport(data);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleRunBenchmark = async () => {
    setRunningBenchmark(true);
    try {
      const res = await fetch('/api/benchmark/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ n_benign: 150, fraud_ratio: 0.15 }),
      });
      if (res.ok) {
        const data = await res.json();
        setReport(data);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setRunningBenchmark(false);
    }
  };

  useEffect(() => {
    fetchBenchmark();
  }, []);

  const getFamilyBadge = (family: string) => {
    switch (family) {
      case 'TemporalGraph':
        return <span className="badge badge-purple">Temporal-GNN</span>;
      case 'Graph':
        return <span className="badge badge-blue">Graph Neural Net</span>;
      case 'Anomaly':
        return <span className="badge badge-amber">Anomaly Detector</span>;
      default:
        return <span className="badge badge-green">Tabular Baseline</span>;
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      
      {/* Top Banner: Champion Model & Finding */}
      {report && (
        <div
          className="card"
          style={{
            background: 'linear-gradient(135deg, rgba(15, 23, 42, 0.95), rgba(30, 58, 138, 0.35))',
            borderColor: 'rgba(56, 189, 248, 0.4)',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            flexWrap: 'wrap',
            gap: '1.5rem',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '1.25rem' }}>
            <div
              style={{
                width: 56,
                height: 56,
                borderRadius: 14,
                background: 'linear-gradient(135deg, #f59e0b, #ef4444)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#fff',
                fontSize: '1.75rem',
              }}
            >
              🏆
            </div>
            <div>
              <div style={{ fontSize: '0.75rem', color: '#38bdf8', fontWeight: 700, letterSpacing: '0.05em' }}>
                SCIENTIFIC CHAMPION ARCHITECTURE
              </div>
              <div style={{ fontSize: '1.5rem', fontWeight: 800 }}>{report.champion_model}</div>
              <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                Demonstrated {report.graph_improvement_demonstrated ? 'statistically significant PR-AUC and cost improvements' : 'robust classification performance'} over traditional tabular baselines under time-aware evaluation.
              </div>
            </div>
          </div>

          <div style={{ display: 'flex', gap: '1.5rem' }}>
            <div style={{ background: 'rgba(15, 23, 42, 0.7)', padding: '0.75rem 1rem', borderRadius: 8, border: '1px solid var(--border-color)' }}>
              <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>CHAMPION PR-AUC</div>
              <div style={{ fontSize: '1.3rem', fontWeight: 800, color: '#38bdf8' }}>
                {(report.champion_pr_auc * 100).toFixed(1)}%
              </div>
            </div>

            <div style={{ background: 'rgba(15, 23, 42, 0.7)', padding: '0.75rem 1rem', borderRadius: 8, border: '1px solid var(--border-color)' }}>
              <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>NET PREVENTED SAVINGS</div>
              <div style={{ fontSize: '1.3rem', fontWeight: 800, color: '#34d399' }}>
                ${report.champion_net_savings.toLocaleString()}
              </div>
            </div>

            <button
              onClick={handleRunBenchmark}
              disabled={runningBenchmark}
              style={{
                padding: '0.75rem 1.25rem',
                background: 'linear-gradient(135deg, #0284c7, #38bdf8)',
                border: 'none',
                borderRadius: 8,
                color: '#fff',
                fontWeight: 700,
                fontSize: '0.85rem',
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
              }}
            >
              <RefreshCw size={14} className={runningBenchmark ? 'spin' : ''} />
              {runningBenchmark ? 'Evaluating 8 Models...' : 'Re-Run Evaluation Harness'}
            </button>
          </div>
        </div>
      )}

      {/* 8-Model Comparison Table */}
      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
          <div>
            <h2 style={{ fontSize: '1.1rem', fontWeight: 700 }}>8-Model Progression Hierarchy Comparison Arena</h2>
            <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              Evaluated under identical temporal splits (train / val / test) without data leakage.
            </div>
          </div>
          {report && (
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              Test Samples: <strong>{report.total_test_samples}</strong> • Fraud Rate: <strong>{report.fraud_prevalence_pct}%</strong>
            </div>
          )}
        </div>

        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.825rem' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border-color)', textAlign: 'left', color: 'var(--text-muted)' }}>
                <th style={{ padding: '0.65rem 0.75rem' }}>RANK</th>
                <th style={{ padding: '0.65rem 0.75rem' }}>MODEL ARCHITECTURE</th>
                <th style={{ padding: '0.65rem 0.75rem' }}>FAMILY</th>
                <th style={{ padding: '0.65rem 0.75rem' }}>PR-AUC</th>
                <th style={{ padding: '0.65rem 0.75rem' }}>ROC-AUC</th>
                <th style={{ padding: '0.65rem 0.75rem' }}>FCR @ 1% FPR</th>
                <th style={{ padding: '0.65rem 0.75rem' }}>P99 LATENCY</th>
                <th style={{ padding: '0.65rem 0.75rem' }}>THROUGHPUT</th>
                <th style={{ padding: '0.65rem 0.75rem' }}>FP COST ($)</th>
                <th style={{ padding: '0.65rem 0.75rem' }}>NET SAVINGS ($)</th>
              </tr>
            </thead>
            <tbody>
              {report?.scorecards?.map((sc) => {
                const isChampion = sc.rank === 1;
                return (
                  <tr
                    key={sc.model_name}
                    style={{
                      borderBottom: '1px solid rgba(51, 65, 85, 0.4)',
                      background: isChampion ? 'rgba(56, 189, 248, 0.08)' : 'transparent',
                    }}
                  >
                    <td style={{ padding: '0.75rem', fontWeight: 800 }}>
                      {isChampion ? '🥇 #1' : sc.rank === 2 ? '🥈 #2' : sc.rank === 3 ? '🥉 #3' : `#${sc.rank}`}
                    </td>

                    <td style={{ padding: '0.75rem', fontWeight: 700, color: isChampion ? '#38bdf8' : 'var(--text-primary)' }}>
                      {sc.model_name}
                    </td>

                    <td style={{ padding: '0.75rem' }}>
                      {getFamilyBadge(sc.architecture_family)}
                    </td>

                    <td style={{ padding: '0.75rem', fontWeight: 700, color: '#38bdf8' }}>
                      {(sc.pr_auc * 100).toFixed(1)}%
                    </td>

                    <td style={{ padding: '0.75rem', fontWeight: 600 }}>
                      {(sc.roc_auc * 100).toFixed(1)}%
                    </td>

                    <td style={{ padding: '0.75rem', fontWeight: 600, color: '#34d399' }}>
                      {(sc.fcr_at_1pct_fpr * 100).toFixed(1)}%
                    </td>

                    <td style={{ padding: '0.75rem', fontFamily: 'JetBrains Mono' }}>
                      {sc.p99_latency_ms.toFixed(1)} ms
                    </td>

                    <td style={{ padding: '0.75rem', fontFamily: 'JetBrains Mono' }}>
                      {sc.throughput_tps.toLocaleString()} tps
                    </td>

                    <td style={{ padding: '0.75rem', color: '#f87171' }}>
                      ${sc.false_positive_cost.toFixed(0)}
                    </td>

                    <td style={{ padding: '0.75rem', fontWeight: 800, color: '#34d399' }}>
                      ${sc.net_dollar_savings.toLocaleString()}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Visual PR-AUC vs Net Savings Comparison Bars */}
      {report && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem' }}>
          
          {/* PR-AUC Relative Bar Comparison */}
          <div className="card">
            <h3 style={{ fontSize: '0.95rem', fontWeight: 700, marginBottom: '1rem', color: '#38bdf8' }}>
              Precision-Recall AUC Comparison (Scientific Metric)
            </h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              {report.scorecards.map((sc) => (
                <div key={sc.model_name}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', marginBottom: 2 }}>
                    <span>{sc.model_name}</span>
                    <strong style={{ color: '#38bdf8' }}>{(sc.pr_auc * 100).toFixed(1)}%</strong>
                  </div>
                  <div style={{ width: '100%', height: 8, background: '#1e293b', borderRadius: 4, overflow: 'hidden' }}>
                    <div
                      style={{
                        width: `${Math.max(5, sc.pr_auc * 100)}%`,
                        height: '100%',
                        background: sc.rank === 1 ? 'linear-gradient(90deg, #0284c7, #38bdf8)' : '#334155',
                      }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Net Business Dollar Savings */}
          <div className="card">
            <h3 style={{ fontSize: '0.95rem', fontWeight: 700, marginBottom: '1rem', color: '#34d399' }}>
              Net Dollar Business Savings ($ Fraud Prevented - $ FP Cost)
            </h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              {report.scorecards.map((sc) => {
                const maxSavings = Math.max(...report.scorecards.map((s) => s.net_dollar_savings), 1);
                const pct = Math.max(5, (sc.net_dollar_savings / maxSavings) * 100);
                return (
                  <div key={sc.model_name}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', marginBottom: 2 }}>
                      <span>{sc.model_name}</span>
                      <strong style={{ color: '#34d399' }}>${sc.net_dollar_savings.toLocaleString()}</strong>
                    </div>
                    <div style={{ width: '100%', height: 8, background: '#1e293b', borderRadius: 4, overflow: 'hidden' }}>
                      <div
                        style={{
                          width: `${pct}%`,
                          height: '100%',
                          background: sc.rank === 1 ? 'linear-gradient(90deg, #059669, #34d399)' : '#334155',
                        }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

        </div>
      )}
    </div>
  );
};
