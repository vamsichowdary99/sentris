import { useQuery } from "@tanstack/react-query";
import { api } from "./api";
import type {
  Alert,
  AlertDetail,
  AlertStatus,
  AnalystMetrics,
  Case,
  CaseDetail,
  CaseStatus,
  MetricsOverview,
  MitreHeatmapEntry,
  MitreTechnique,
  MTTRMetrics,
  Page,
  Report,
  Severity,
} from "./types";

export function useAlerts(filters: {
  status?: AlertStatus | "";
  severity?: Severity | "";
  q?: string;
  page?: number;
  size?: number;
}) {
  return useQuery({
    queryKey: ["alerts", filters],
    queryFn: () =>
      api.get<Page<Alert>>("/alerts", {
        status: filters.status || undefined,
        severity: filters.severity || undefined,
        q: filters.q || undefined,
        page: filters.page ?? 1,
        size: filters.size ?? 25,
      }),
  });
}

export function useAlert(alertId: string) {
  return useQuery({
    queryKey: ["alert", alertId],
    queryFn: () => api.get<AlertDetail>(`/alerts/${alertId}`),
    enabled: Boolean(alertId),
  });
}

export function useCases(filters: { status?: CaseStatus | ""; page?: number; size?: number }) {
  return useQuery({
    queryKey: ["cases", filters],
    queryFn: () =>
      api.get<Page<Case>>("/cases", {
        status: filters.status || undefined,
        page: filters.page ?? 1,
        size: filters.size ?? 25,
      }),
  });
}

export function useCase(caseId: string) {
  return useQuery({
    queryKey: ["case", caseId],
    queryFn: () => api.get<CaseDetail>(`/cases/${caseId}`),
    enabled: Boolean(caseId),
  });
}

export function useCaseReports(caseId: string) {
  return useQuery({
    queryKey: ["case", caseId, "reports"],
    queryFn: () => api.get<Report[]>(`/cases/${caseId}/reports`),
    enabled: Boolean(caseId),
  });
}

export function useMetricsOverview() {
  return useQuery({
    queryKey: ["metrics", "overview"],
    queryFn: () => api.get<MetricsOverview>("/metrics/overview"),
  });
}

export function useMitreHeatmap() {
  return useQuery({
    queryKey: ["metrics", "mitre-heatmap"],
    queryFn: () => api.get<MitreHeatmapEntry[]>("/metrics/mitre-heatmap"),
  });
}

export function useMitreTechniques() {
  return useQuery({
    queryKey: ["mitre", "techniques"],
    queryFn: () => api.get<Page<MitreTechnique>>("/mitre/techniques", { size: 200 }),
    staleTime: 5 * 60_000,
  });
}

export function useMttr() {
  return useQuery({
    queryKey: ["metrics", "mttr"],
    queryFn: () => api.get<MTTRMetrics>("/metrics/mttr"),
  });
}

export function useAnalystMetrics() {
  return useQuery({
    queryKey: ["metrics", "analyst"],
    queryFn: () => api.get<AnalystMetrics[]>("/metrics/analyst"),
  });
}
