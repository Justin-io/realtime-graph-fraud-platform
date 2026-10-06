import React, { useState, useEffect, useRef } from 'react';
import { Navbar } from './components/Navbar';
import { LiveStreamView } from './components/LiveStreamView';
import { GraphView } from './components/GraphView';
import { BenchmarkView } from './components/BenchmarkView';
import { DriftView } from './components/DriftView';
import { InvestigationView } from './components/InvestigationView';
import { ScoringResult } from './types';

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState('stream');
  const [championModel, setChampionModel] = useState('Temporal-GNN');
  const [transactions, setTransactions] = useState<ScoringResult[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [inspectedEntityId, setInspectedEntityId] = useState<string>('USR_000001');

  const sseRef = useRef<EventSource | null>(null);

  // 1. Fetch initial health & recent transactions
  useEffect(() => {
    const fetchInitial = async () => {
      try {
        const healthRes = await fetch('/health');
        if (healthRes.ok) {
          const hData = await healthRes.json();
          if (hData.champion_model) setChampionModel(hData.champion_model);
        }

        const recRes = await fetch('/api/stream/recent?limit=40');
        if (recRes.ok) {
          const rData = await recRes.json();
          if (rData.transactions) {
            setTransactions(rData.transactions);
          }
        }
      } catch (e) {
        console.error('Initialization fetch error:', e);
      }
    };
    fetchInitial();
  }, []);

  // 2. Setup Server-Sent Events (SSE) stream
  useEffect(() => {
    if (isPaused) {
      if (sseRef.current) {
        sseRef.current.close();
        setIsStreaming(false);
      }
      return;
    }

    const eventSource = new EventSource('/api/stream?delay_ms=900');
    sseRef.current = eventSource;

    eventSource.onopen = () => {
      setIsStreaming(true);
    };

    eventSource.onmessage = (event) => {
      try {
        const txData: ScoringResult = JSON.parse(event.data);
        if (txData && txData.tx_id) {
          setTransactions((prev) => [txData, ...prev.slice(0, 199)]);
        }
      } catch (err) {
        console.error('SSE JSON error:', err);
      }
    };

    eventSource.onerror = () => {
      setIsStreaming(false);
    };

    return () => {
      eventSource.close();
      setIsStreaming(false);
    };
  }, [isPaused]);

  // Attack Injection handler
  const handleInjectAttack = async (type: string) => {
    try {
      await fetch('/api/stream/inject', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ attack_type: type, burst_size: 8 }),
      });
    } catch (e) {
      console.error('Attack injection error:', e);
    }
  };

  const handleSelectEntity = (entityId: string) => {
    setInspectedEntityId(entityId);
    setActiveTab('graph');
  };

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <Navbar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        championModel={championModel}
        isStreaming={isStreaming}
        onInjectAttack={handleInjectAttack}
      />

      <main style={{ maxWidth: 1440, width: '100%', margin: '0 auto', padding: '1.5rem', flex: 1 }}>
        {activeTab === 'stream' && (
          <LiveStreamView
            transactions={transactions}
            isPaused={isPaused}
            setIsPaused={setIsPaused}
            onSelectEntity={handleSelectEntity}
          />
        )}

        {activeTab === 'graph' && (
          <GraphView initialEntityId={inspectedEntityId} />
        )}

        {activeTab === 'benchmark' && (
          <BenchmarkView />
        )}

        {activeTab === 'drift' && (
          <DriftView />
        )}

        {activeTab === 'investigation' && (
          <InvestigationView />
        )}
      </main>

      <footer style={{ borderTop: '1px solid var(--border-color)', padding: '1rem 1.5rem', textAlign: 'center', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
        FraudShield AI • Scientific Graph Fraud Detection Platform • Sub-Second Inference Engine • 8-Model Progression
      </footer>
    </div>
  );
};
