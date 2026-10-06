import React, { useState, useEffect } from 'react';
import { GraphResponse, FraudRing } from '../types';
import { Search, AlertOctagon, RefreshCw } from 'lucide-react';

interface GraphViewProps {
  initialEntityId?: string;
}

export const GraphView: React.FC<GraphViewProps> = ({ initialEntityId }) => {
  const [entityId, setEntityId] = useState(initialEntityId || 'USR_000001');
  const [graphData, setGraphData] = useState<GraphResponse | null>(null);
  const [rings, setRings] = useState<FraudRing[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedNode, setSelectedNode] = useState<any>(null);

  const fetchGraph = async (id: string) => {
    setLoading(true);
    try {
      const res = await fetch(`/api/graph/entity/${id}`);
      if (res.ok) {
        const data = await res.json();
        setGraphData(data);
        setSelectedNode(data.nodes.find((n: any) => n.is_center) || data.nodes[0]);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const fetchRings = async () => {
    try {
      const res = await fetch('/api/graph/rings?min_users=2');
      if (res.ok) {
        const data = await res.json();
        setRings(data.rings || []);
      }
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    if (initialEntityId) {
      setEntityId(initialEntityId);
      fetchGraph(initialEntityId);
    } else {
      fetchGraph('USR_000001');
    }
    fetchRings();
  }, [initialEntityId]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (entityId.trim()) {
      fetchGraph(entityId.trim());
    }
  };

  // Node position calculation for SVG visualization
  const width = 640;
  const height = 480;
  const centerX = width / 2;
  const centerY = height / 2;

  const nodePositions = React.useMemo(() => {
    if (!graphData) return new Map();
    const map = new Map<string, { x: number; y: number }>();
    const otherNodes = graphData.nodes.filter((n) => !n.is_center);
    
    // Center node
    map.set(graphData.center_node, { x: centerX, y: centerY });

    // Concentric ring 1
    const n = otherNodes.length;
    otherNodes.forEach((node, i) => {
      const angle = (2 * Math.PI * i) / Math.max(1, n);
      const radius = 175 + (i % 2 === 0 ? 30 : -30);
      map.set(node.id, {
        x: centerX + radius * Math.cos(angle),
        y: centerY + radius * Math.sin(angle),
      });
    });

    return map;
  }, [graphData]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      
      {/* Top Search & Stats Bar */}
      <div className="card" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
        <form onSubmit={handleSearch} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flex: 1, maxWidth: 450 }}>
          <div style={{ display: 'flex', alignItems: 'center', background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', borderRadius: 6, padding: '0.4rem 0.75rem', width: '100%' }}>
            <Search size={16} style={{ color: 'var(--text-muted)', marginRight: 8 }} />
            <input
              type="text"
              placeholder="Search Entity ID (e.g. USR_000001, DEV_000005, CRD_000010)..."
              value={entityId}
              onChange={(e) => setEntityId(e.target.value)}
              style={{ background: 'transparent', border: 'none', outline: 'none', width: '100%', fontSize: '0.85rem' }}
            />
          </div>
          <button
            type="submit"
            style={{
              padding: '0.45rem 0.9rem',
              background: 'linear-gradient(135deg, #0284c7, #38bdf8)',
              border: 'none',
              borderRadius: 6,
              color: '#fff',
              fontSize: '0.825rem',
              fontWeight: 700,
            }}
          >
            Explore
          </button>
        </form>

        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          {graphData && (
            <div style={{ display: 'flex', gap: '1rem', fontSize: '0.8rem' }}>
              <div><span style={{ color: 'var(--text-muted)' }}>Neighborhood Nodes:</span> <strong>{graphData.node_count}</strong></div>
              <div><span style={{ color: 'var(--text-muted)' }}>Relational Edges:</span> <strong>{graphData.edge_count}</strong></div>
            </div>
          )}
          <button
            onClick={() => { fetchGraph(entityId); fetchRings(); }}
            style={{ display: 'flex', alignItems: 'center', gap: '0.3rem', background: 'transparent', border: '1px solid var(--border-color)', borderRadius: 6, padding: '0.4rem 0.65rem', color: 'var(--text-secondary)', fontSize: '0.75rem' }}
          >
            <RefreshCw size={12} /> Refresh
          </button>
        </div>
      </div>

      {/* Main Grid: Visualizer + Node Info + Fraud Rings */}
      <div style={{ display: 'grid', gridTemplateColumns: '1.8fr 1.2fr', gap: '1.5rem' }}>
        
        {/* SVG Graph Canvas */}
        <div className="card" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: 520, position: 'relative' }}>
          {loading ? (
            <div style={{ color: '#38bdf8', fontWeight: 600 }}>Extracting 2-hop graph neighborhood...</div>
          ) : graphData ? (
            <svg width="100%" height={480} viewBox={`0 0 ${width} ${height}`} style={{ overflow: 'visible' }}>
              <defs>
                <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
                  <feGaussianBlur stdDeviation="4" result="blur" />
                  <feComposite in="SourceGraphic" in2="blur" operator="over" />
                </filter>
              </defs>

              {/* Concentric distance orbit guides */}
              <circle cx={centerX} cy={centerY} r={175} fill="none" stroke="rgba(51, 65, 85, 0.4)" strokeDasharray="4 4" />
              <circle cx={centerX} cy={centerY} r={80} fill="none" stroke="rgba(51, 65, 85, 0.2)" strokeDasharray="4 4" />

              {/* Edges */}
              {graphData.edges.map((e, idx) => {
                const sPos = nodePositions.get(e.source);
                const tPos = nodePositions.get(e.target);
                if (!sPos || !tPos) return null;

                return (
                  <g key={idx}>
                    <line
                      x1={sPos.x}
                      y1={sPos.y}
                      x2={tPos.x}
                      y2={tPos.y}
                      stroke="rgba(148, 163, 184, 0.35)"
                      strokeWidth={1.5}
                    />
                  </g>
                );
              })}

              {/* Nodes */}
              {graphData.nodes.map((node) => {
                const pos = nodePositions.get(node.id);
                if (!pos) return null;
                const isSelected = selectedNode?.id === node.id;
                const r = node.is_center ? 22 : 14;

                return (
                  <g
                    key={node.id}
                    onClick={() => {
                      setSelectedNode(node);
                      if (!node.is_center) {
                        setEntityId(node.id);
                        fetchGraph(node.id);
                      }
                    }}
                    style={{ cursor: 'pointer' }}
                  >
                    <circle
                      cx={pos.x}
                      cy={pos.y}
                      r={r}
                      fill={node.color}
                      stroke={isSelected ? '#ffffff' : 'rgba(15, 23, 42, 0.8)'}
                      strokeWidth={isSelected ? 3 : 2}
                      filter={node.is_center ? 'url(#glow)' : undefined}
                    />
                    <text
                      x={pos.x}
                      y={pos.y + r + 12}
                      textAnchor="middle"
                      fill="#e2e8f0"
                      fontSize="9"
                      fontFamily="JetBrains Mono"
                      fontWeight={600}
                    >
                      {node.id}
                    </text>
                  </g>
                );
              })}
            </svg>
          ) : (
            <div style={{ color: 'var(--text-muted)' }}>Enter an entity ID to inspect topology.</div>
          )}

          {/* Legend */}
          <div style={{ position: 'absolute', bottom: 12, left: 16, display: 'flex', gap: '0.75rem', flexWrap: 'wrap', background: 'rgba(15, 23, 42, 0.9)', padding: '0.3rem 0.6rem', borderRadius: 6, border: '1px solid var(--border-color)', fontSize: '0.7rem' }}>
            <div><span style={{ color: '#3B82F6' }}>●</span> User</div>
            <div><span style={{ color: '#10B981' }}>●</span> Card</div>
            <div><span style={{ color: '#F59E0B' }}>●</span> Device</div>
            <div><span style={{ color: '#8B5CF6' }}>●</span> IP</div>
            <div><span style={{ color: '#EC4899' }}>●</span> Merchant</div>
            <div><span style={{ color: '#64748B' }}>●</span> Address</div>
          </div>
        </div>

        {/* Right Column: Node Details & Fraud Ring Syndicates */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          
          {/* Selected Node Inspector */}
          {selectedNode && (
            <div className="card">
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Inspected Entity</div>
              <div style={{ fontSize: '1.1rem', fontWeight: 800, color: selectedNode.color, fontFamily: 'JetBrains Mono', marginBottom: '0.5rem' }}>
                {selectedNode.id}
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem', fontSize: '0.8rem' }}>
                <div style={{ background: 'var(--bg-secondary)', padding: '0.5rem', borderRadius: 6 }}>
                  <div style={{ color: 'var(--text-muted)', fontSize: '0.7rem' }}>ENTITY TYPE</div>
                  <strong>{selectedNode.type}</strong>
                </div>
                <div style={{ background: 'var(--bg-secondary)', padding: '0.5rem', borderRadius: 6 }}>
                  <div style={{ color: 'var(--text-muted)', fontSize: '0.7rem' }}>GRAPH DEGREE</div>
                  <strong>{selectedNode.degree} connected edges</strong>
                </div>
              </div>
            </div>
          )}

          {/* Active Fraud Rings Syndicate Table */}
          <div className="card" style={{ flex: 1 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                <AlertOctagon size={16} style={{ color: '#ef4444' }} />
                <h3 style={{ fontSize: '0.95rem', fontWeight: 700 }}>Syndicated Fraud Rings</h3>
              </div>
              <span className="badge badge-red">{rings.length} RINGS FOUND</span>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem', maxHeight: 320, overflowY: 'auto' }}>
              {rings.length > 0 ? (
                rings.map((ring) => (
                  <div
                    key={ring.ring_id}
                    onClick={() => {
                      setEntityId(ring.hub_entity_id);
                      fetchGraph(ring.hub_entity_id);
                    }}
                    style={{
                      background: 'rgba(30, 41, 59, 0.6)',
                      border: '1px solid rgba(239, 68, 68, 0.3)',
                      borderRadius: 8,
                      padding: '0.75rem',
                      cursor: 'pointer',
                      transition: 'all 0.15s ease',
                    }}
                    onMouseEnter={(e) => (e.currentTarget.style.borderColor = '#ef4444')}
                    onMouseLeave={(e) => (e.currentTarget.style.borderColor = 'rgba(239, 68, 68, 0.3)')}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.3rem' }}>
                      <span style={{ fontWeight: 800, fontFamily: 'JetBrains Mono', color: '#f87171' }}>
                        {ring.ring_id}
                      </span>
                      <span className="badge badge-red" style={{ fontSize: '0.65rem' }}>
                        {ring.risk_level}
                      </span>
                    </div>

                    <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                      Shared Hub: <strong style={{ color: '#fbbf24' }}>{ring.hub_entity_id}</strong> ({ring.hub_entity_type})
                    </div>
                    <div style={{ fontSize: '0.725rem', color: 'var(--text-muted)', marginTop: '0.2rem' }}>
                      {ring.member_user_ids.length} Linked Users • {ring.member_card_ids.length} Linked Cards
                    </div>
                  </div>
                ))
              ) : (
                <div style={{ color: 'var(--text-muted)', fontSize: '0.8rem', padding: '1rem', textAlign: 'center' }}>
                  No high-degree fraud rings currently detected.
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
