export type Severity = "info" | "low" | "medium" | "high" | "critical";
export type AlertStatus = "new" | "triaging" | "investigating" | "closed" | "false_positive";
export type CaseStatus = "open" | "investigating" | "contained" | "closed";
export type IOCType = "ip" | "domain" | "hash" | "url";
export type MitreMappingSource = "ai" | "rule" | "analyst";

export interface AuthUserRead {
  id: string;
  org_id: string;
  email: string;
  full_name: string;
  is_active: boolean;
  last_login_at: string | null;
  created_at: string;
}

export interface TokenPairResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: AuthUserRead;
}

export interface MeResponse {
  user: AuthUserRead;
  roles: string[];
  permissions: string[];
}

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
}

export interface Alert {
  id: string;
  org_id: string;
  source: string;
  external_id: string | null;
  title: string;
  severity: Severity;
  ai_severity: Severity | null;
  priority: number | null;
  status: AlertStatus;
  rule_name: string | null;
  src_ip: string | null;
  dst_ip: string | null;
  host_asset_id: string | null;
  user_subject: string | null;
  occurred_at: string;
  ingested_at: string;
  created_at: string;
  updated_at: string;
}

export interface Enrichment {
  id: string;
  ioc_id: string;
  provider: string;
  verdict: string | null;
  score: number | null;
  raw: Record<string, unknown>;
  fetched_at: string;
}

export interface IOCDetail {
  id: string;
  org_id: string;
  type: IOCType;
  value: string;
  reputation: string | null;
  first_seen: string | null;
  last_seen: string | null;
  source: string | null;
  created_at: string;
  updated_at: string;
  enrichments: Enrichment[];
}

export interface MitreTechnique {
  id: string;
  name: string;
  tactic: string;
  description: string;
  url: string;
}

export interface AlertMitreMapping {
  technique: MitreTechnique;
  source: MitreMappingSource;
  confidence: number | null;
}

export interface AIAnalysis {
  id: string;
  task: string;
  model: string;
  provider: string;
  prompt_version: string;
  output: Record<string, unknown>;
  created_at: string;
}

export interface AlertDetail extends Alert {
  raw: Record<string, unknown>;
  iocs: IOCDetail[];
  mitre: AlertMitreMapping[];
  ai_analyses: AIAnalysis[];
}

export interface AlertEvent {
  id: string;
  alert_id: string;
  event_ts: string;
  payload: Record<string, unknown>;
}

export interface TimelineEvent {
  id: string;
  case_id: string;
  ts: string;
  kind: string;
  actor_id: string | null;
  description: string;
  meta: Record<string, unknown> | null;
}

export interface Comment {
  id: string;
  entity_type: string;
  entity_id: string;
  user_id: string;
  body: string;
  created_at: string;
}

export interface Case {
  id: string;
  org_id: string;
  title: string;
  summary: string | null;
  status: CaseStatus;
  severity: Severity;
  assignee_id: string | null;
  created_by: string;
  opened_at: string;
  closed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface CaseDetail extends Case {
  alerts: Alert[];
  timeline: TimelineEvent[];
  comments: Comment[];
}

export interface MetricsOverview {
  total_alerts: number;
  total_cases: number;
  open_cases: number;
  alerts_by_status: Record<string, number>;
  alerts_by_severity: Record<string, number>;
  cases_by_status: Record<string, number>;
}

export interface MTTRMetrics {
  average_hours: number | null;
  sample_size: number;
}

export interface MitreHeatmapEntry {
  technique_id: string;
  technique_name: string;
  tactic: string;
  alert_count: number;
}

export interface AnalystMetrics {
  analyst_id: string;
  full_name: string;
  assigned_cases: number;
  closed_cases: number;
}

export interface Report {
  id: string;
  case_id: string;
  format: "markdown" | "pdf";
  content: string;
  generated_by: string;
  created_at: string;
}

export interface NLSearchFilterOut {
  status: AlertStatus | null;
  severity: Severity | null;
  source: string | null;
  src_ip: string | null;
  q: string | null;
  mitre: string | null;
  occurred_from: string | null;
  occurred_to: string | null;
}

export interface NLSearchResponse {
  filter: NLSearchFilterOut;
  items: Alert[];
  total: number;
}

export interface AlertPriorityResult {
  id: string;
  severity: Severity;
  priority: number;
  reasoning: string;
}

export interface AlertsPrioritizeResponse {
  results: AlertPriorityResult[];
}

export interface IOCSummaryResponse {
  summary: string;
  provider: string;
  model: string;
}

export interface TechniqueExplainResponse {
  explanation: string;
  provider: string;
  model: string;
}

export interface Asset {
  id: string;
  org_id: string;
  hostname: string;
  ip: string | null;
  os: string | null;
  owner: string | null;
  criticality: "low" | "medium" | "high" | "critical";
  tags: string[] | null;
  created_at: string;
  updated_at: string;
}

// --- Investigate module (Phase 6.5) ---

export type ProviderStatus =
  | "ok"
  | "cached"
  | "timeout"
  | "error"
  | "misconfigured"
  | "rate_limited"
  | "scanning";

export interface IntegrationStatus {
  provider: string;
  mode: "live" | "mocked";
  configured: boolean;
  last_status: string | null;
  supported_types: IOCType[];
}

export interface ProviderOutcome {
  provider: string;
  status: ProviderStatus;
  verdict: string | null;
  score: number | null;
  raw: Record<string, unknown>;
  fetched_at: string | null;
}

export interface InvestigateIOC {
  id: string;
  org_id: string;
  type: IOCType;
  value: string;
  reputation: string | null;
  first_seen: string | null;
  last_seen: string | null;
  source: string | null;
  created_at: string;
  updated_at: string;
}

export interface InvestigateResponse {
  ioc: InvestigateIOC;
  detected_type: IOCType;
  providers: ProviderOutcome[];
}

export interface InvestigateDetailResponse extends InvestigateResponse {
  related_alerts: Alert[];
  related_cases: Case[];
  latest_report: Record<string, unknown> | null;
}

export interface ReportAttribution {
  malware_family: string | null;
  campaign: string | null;
  threat_actor: string | null;
  summary: string;
}

export interface ReportContext {
  geo: string | null;
  asn: string | null;
  first_seen: string | null;
  last_seen: string | null;
  scanner_classification: string | null;
  exposure: string | null;
}

export interface RecommendedAction {
  action: string;
  rationale: string;
}

export interface InvestigateReportOutput {
  verdict: "malicious" | "suspicious" | "benign" | "unknown";
  confidence: number;
  rationale: string;
  attribution: ReportAttribution;
  evidence: string[];
  context: ReportContext;
  conflicts: string[];
  recommended_actions: RecommendedAction[];
}

export interface InvestigateReportResponse {
  id: string;
  ioc_id: string;
  model: string;
  provider: string;
  prompt_version: string;
  report: InvestigateReportOutput;
  related_alerts: Alert[];
  related_cases: Case[];
  created_at: string;
}
