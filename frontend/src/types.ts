export interface ScoringResult {
  tx_id: string;
  user_id: string;
  card_id?: string;
  device_id?: string;
  ip_address?: string;
  merchant_id?: string;
  amount: number;
  timestamp: number;
  risk_score: number;
  calibrated_probability: number;
  decision: 'APPROVE' | 'CHALLENGE' | 'DECLINE';
  latency_ms: number;
  reason_codes: string[];
  graph_evidence?: any;
  model_breakdown: Record<string, number>;
  triggered_rules: string[];
  attack_type?: string;
}

export interface GraphNode {
  id: string;
  label: string;
  type: string;
  color: string;
  degree: number;
  is_center?: boolean;
}

export interface GraphEdge {
  source: string;
  target: string;
  relation: string;
  weight: number;
}

export interface GraphResponse {
  center_node: string;
  node_count: number;
  edge_count: number;
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface FraudRing {
  ring_id: string;
  member_count: number;
  hub_entity_id: string;
  hub_entity_type: string;
  member_user_ids: string[];
  member_card_ids: string[];
  risk_level: string;
}

export interface ModelScorecard {
  model_name: string;
  architecture_family: string;
  precision: number;
  recall: number;
  pr_auc: number;
  roc_auc: number;
  fcr_at_1pct_fpr: number;
  false_positive_cost: number;
  fraud_prevented_dollars: number;
  net_dollar_savings: number;
  p99_latency_ms: number;
  throughput_tps: number;
  brier_score: number;
  rank: number;
}

export interface BenchmarkReport {
  total_test_samples: number;
  fraud_test_samples: number;
  fraud_prevalence_pct: number;
  champion_model: string;
  champion_pr_auc: number;
  champion_net_savings: number;
  graph_improvement_demonstrated: boolean;
  scorecards: ModelScorecard[];
}

export interface DriftReport {
  feature_name: string;
  psi_score: number;
  ks_statistic: number;
  ks_p_value: number;
  drift_status: 'STABLE' | 'MODERATE_DRIFT' | 'CRITICAL_DRIFT';
  retraining_recommended: boolean;
}

export interface OverallDriftAssessment {
  overall_status: string;
  total_features_evaluated: number;
  features_in_drift: string[];
  max_psi: number;
  requires_retraining: boolean;
  feature_reports: Record<string, DriftReport>;
}

export interface AnalystDecision {
  decision_id: string;
  tx_id: string;
  user_id: string;
  amount: number;
  analyst_id: string;
  decision: string;
  notes: string;
  timestamp: number;
  original_risk_score: number;
  original_decision: string;
}

export interface AuditLogEntry {
  entry_id: string;
  timestamp: number;
  event_type: string;
  details: Record<string, any>;
}
