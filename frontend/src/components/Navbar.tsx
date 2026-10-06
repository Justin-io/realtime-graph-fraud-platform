import React, { useState } from 'react';
import { Activity, ShieldAlert, Cpu, Radio, Zap } from 'lucide-react';

interface NavbarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  championModel: string;
  isStreaming: boolean;
  onInjectAttack: (type: string) => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  activeTab,
  setActiveTab,
  championModel,
  isStreaming,
  onInjectAttack,
}) => {
  const [injecting, setInjecting] = useState<string | null>(null);

  const attacks = [
    { id: 'CARD_TESTING', label: 'Card Testing Burst', icon: '⚡' },
    { id: 'FRAUD_RING', label: 'Fraud Syndicate Ring', icon: '🕸️' },
    { id: 'IMPOSSIBLE_TRAVEL', label: 'Impossible Travel', icon: '✈️' },
    { id: 'ACCOUNT_TAKEOVER', label: 'Account Takeover', icon: '👤' },
    { id: 'IP_ROTATION_BOTNET', label: 'Proxy Botnet Farm', icon: '🤖' },
  ];

  const handleInject = async (type: string) => {
    setInjecting(type);
    await onInjectAttack(type);
    setTimeout(() => setInjecting(null), 1000);
  };

  const tabs = [
    { id: 'stream', label: 'Live Stream & Triage', icon: <Radio size={16} /> },
    { id: 'graph', label: 'Graph & Fraud Rings', icon: <Cpu size={16} /> },
    { id: 'benchmark', label: '8-Model Scientific Arena', icon: <Activity size={16} /> },
    { id: 'drift', label: 'Concept Drift & Retraining', icon: <Zap size={16} /> },
    { id: 'investigation', label: 'Analyst Console & Audit', icon: <ShieldAlert size={16} /> },
  ];

  return (
    <header style={{ borderBottom: '1px solid var(--border-color)', background: 'rgba(15, 23, 42, 0.95)', backdropFilter: 'blur(10px)', position: 'sticky', top: 0, zIndex: 50 }}>
      <div style={{ maxWidth: 1440, margin: '0 auto', padding: '0.75rem 1.5rem', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '1rem' }}>
        
        {/* Brand & Champion */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <div style={{ width: 34, height: 34, borderRadius: 8, background: 'linear-gradient(135deg, #0284c7, #38bdf8)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 800, color: '#fff', fontSize: '1.1rem' }}>
              FS
            </div>
            <div>
              <div style={{ fontWeight: 800, fontSize: '1.05rem', letterSpacing: '-0.02em', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                FraudShield AI
                <span className="badge badge-blue" style={{ fontSize: '0.65rem' }}>v1.0-PROD</span>
              </div>
              <div style={{ fontSize: '0.725rem', color: 'var(--text-muted)' }}>Real-Time Graph Intelligence Platform</div>
            </div>
          </div>

          <div style={{ height: 28, width: 1, background: 'var(--border-color)', margin: '0 0.5rem' }} />

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>Champion Model:</span>
            <span className="badge badge-purple" style={{ fontSize: '0.75rem', fontWeight: 700 }}>
              🏆 {championModel || 'Temporal-GNN'}
            </span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', marginLeft: '0.5rem' }}>
            <span style={{
              width: 8,
              height: 8,
              borderRadius: '50%',
              backgroundColor: isStreaming ? '#10b981' : '#ef4444',
              display: 'inline-block',
              boxShadow: isStreaming ? '0 0 8px #10b981' : 'none'
            }} />
            <span style={{ fontSize: '0.75rem', color: isStreaming ? '#34d399' : '#f87171', fontWeight: 600 }}>
              {isStreaming ? 'SSE INGESTION ACTIVE' : 'STREAM DISCONNECTED'}
            </span>
          </div>
        </div>

        {/* Quick Attack Injectors */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
          <span style={{ fontSize: '0.725rem', color: 'var(--text-muted)', fontWeight: 600 }}>INJECT ATTACK BURST:</span>
          {attacks.map((a) => (
            <button
              key={a.id}
              onClick={() => handleInject(a.id)}
              disabled={injecting === a.id}
              style={{
                background: injecting === a.id ? 'rgba(239, 68, 68, 0.3)' : 'rgba(30, 41, 59, 0.7)',
                border: '1px solid var(--border-color)',
                borderRadius: 6,
                padding: '0.3rem 0.6rem',
                fontSize: '0.75rem',
                color: 'var(--text-primary)',
                display: 'flex',
                alignItems: 'center',
                gap: '0.3rem',
                transition: 'all 0.15s ease',
              }}
              onMouseEnter={(e) => (e.currentTarget.style.borderColor = 'var(--color-blue)')}
              onMouseLeave={(e) => (e.currentTarget.style.borderColor = 'var(--border-color)')}
            >
              <span>{a.icon}</span>
              <span>{a.label}</span>
              {injecting === a.id && <span style={{ fontSize: '0.65rem', color: '#f87171' }}>...</span>}
            </button>
          ))}
        </div>
      </div>

      {/* Tabs navigation */}
      <div style={{ maxWidth: 1440, margin: '0 auto', padding: '0 1.5rem', display: 'flex', gap: '0.5rem', overflowX: 'auto' }}>
        {tabs.map((tab) => {
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                padding: '0.65rem 1rem',
                fontSize: '0.85rem',
                fontWeight: isActive ? 700 : 500,
                color: isActive ? '#38bdf8' : 'var(--text-secondary)',
                border: 'none',
                background: 'transparent',
                borderBottom: isActive ? '2px solid #38bdf8' : '2px solid transparent',
                transition: 'all 0.15s ease',
                whiteSpace: 'nowrap',
              }}
            >
              {tab.icon}
              {tab.label}
            </button>
          );
        })}
      </div>
    </header>
  );
};
