export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8001";

export type User = {
  id: string;
  email: string;
  name: string | null;
  base_currency: string;
};

export type AuthResponse = {
  token_type: "bearer";
  access_token: string;
  refresh_token: string;
  user: User;
};

export type Goal = {
  id: string;
  title: string;
  category: string | null;
  description: string | null;
  target_amount: string;
  currency: string;
  current_amount: string;
  desired_date: string | null;
  created_at: string;
  priority: number;
  importance: number;
  deadline_type: string;
  status: string;
  allocation_weight: string | null;
  product_url: string | null;
  expected_purchase_date: string | null;
  notes: string | null;
};

export type GoalPriceHistory = {
  id: string;
  user_id: string;
  goal_id: string;
  previous_amount: string;
  new_amount: string;
  currency: string;
  source: string | null;
  note: string | null;
  changed_at: string;
  created_at: string;
};

export type ProjectionFactor = {
  key: string;
  label: string;
  value: string;
  impact: string;
};

export type ProjectionExplainability = {
  factors: ProjectionFactor[];
  assumptions: string[];
};

export type PlanGoal = {
  goal_id: string;
  title: string;
  currency: string;
  target_amount: string;
  current_amount: string;
  remaining_amount: string;
  progress_percent: string;
  allocated_first_month: string;
  required_monthly_amount: string | null;
  expected_completion_date: string | null;
  status: string;
  probability: string;
  explanation: string;
  explainability: ProjectionExplainability;
};

export type MonthlyAllocation = {
  month_index: number;
  period_date: string;
  allocations: Record<string, string>;
};

export type Plan = {
  monthly_available_amount: string;
  strategy: string;
  generated_at: string;
  goals: PlanGoal[];
  monthly_schedule: MonthlyAllocation[];
  conflicts: string[];
  recommendations: string[];
};

export type ScenarioResponse = {
  scenario_name: string;
  base: Plan;
  scenario: Plan;
};

export type ScenarioPreset = {
  name: string;
  label: string;
  description: string;
  assumptions: string[];
  monthly_available_amount: string;
  skipped_months: number[];
  plan: Plan;
};

export type ScenarioPresetsResponse = {
  base: Plan;
  presets: ScenarioPreset[];
};

export type AllocationStrategySettings = {
  type: "strict_priority" | "proportional" | "nearest_deadline" | "smallest_goal_first" | "custom";
  weights: Record<string, string>;
  fixed_amounts: Record<string, string>;
};

export type FinancialSummary = {
  base_currency: string;
  manual_monthly_available_amount: string;
  total_monthly_income: string;
  total_monthly_expenses: string;
  total_monthly_debt_payments: string;
  emergency_fund_gap: string;
  emergency_fund_monthly_reserve: string;
  calculated_monthly_available_amount: string;
  effective_monthly_available_amount: string;
  warnings: string[];
};

export type Income = {
  id: string;
  amount: string;
  currency: string;
  frequency: string;
  source: string | null;
  is_recurring: boolean;
  received_at: string | null;
  created_at: string;
};

export type Expense = {
  id: string;
  amount: string;
  currency: string;
  category: string;
  frequency: string;
  is_mandatory: boolean;
  is_recurring: boolean;
  occurred_at: string | null;
  created_at: string;
};

export type Debt = {
  id: string;
  type: string;
  creditor: string | null;
  balance: string;
  currency: string;
  min_monthly_payment: string;
  status: string;
  created_at: string;
};

export type Contribution = {
  id: string;
  goal_id: string;
  type: string;
  amount: string;
  currency: string;
  exchange_rate: string | null;
  amount_in_goal_currency: string | null;
  amount_in_base_currency: string | null;
  source: string | null;
  comment: string | null;
  occurred_at: string;
  created_at: string;
  reversed_at: string | null;
};

export type ExchangeRate = {
  id: string;
  base_currency: string;
  quote_currency: string;
  rate: string;
  source: string | null;
  rate_date: string;
  created_at: string;
};

export type AnalyticsEvent = {
  id: string;
  user_id: string;
  name: string;
  source: string;
  properties: Record<string, unknown>;
  created_at: string;
};

export type AnalyticsEventCount = {
  name: string;
  count: number;
};

export type AnalyticsSummary = {
  total_events: number;
  events_last_7_days: number;
  events_last_30_days: number;
  active_days_last_30: number;
  last_event_at: string | null;
  key_metrics: Record<string, number>;
  event_counts: AnalyticsEventCount[];
  recent_events: AnalyticsEvent[];
};

export type AuditLogEntry = {
  id: number;
  actor_user_id: string | null;
  entity_type: string;
  entity_id: string;
  action: string;
  before_json: Record<string, unknown> | null;
  after_json: Record<string, unknown> | null;
  created_at: string;
};

export type Notification = {
  id: string;
  user_id: string;
  type: string;
  title: string;
  body: string;
  channel: string;
  severity: string;
  status: string;
  metadata_json: Record<string, unknown>;
  scheduled_for: string | null;
  read_at: string | null;
  created_at: string;
};

export type NotificationFrequency = "instant" | "daily" | "weekly" | "monthly";

export type NotificationSettings = {
  in_app_enabled: boolean;
  plan_warnings: boolean;
  milestone_updates: boolean;
  monthly_reminders: boolean;
  email_enabled: boolean;
  in_app_frequency: NotificationFrequency;
  email_frequency: NotificationFrequency;
};

export type RecurringRule = {
  id: string;
  user_id: string;
  goal_id: string;
  title: string;
  amount: string;
  currency: string;
  frequency: string;
  day_of_month: number | null;
  source: string | null;
  is_active: boolean;
  next_run_on: string | null;
  last_run_on: string | null;
  created_at: string;
  updated_at: string;
};

export type MonthlyGoalReport = {
  goal_id: string;
  title: string;
  currency: string;
  added_amount: string;
  removed_amount: string;
  net_amount: string;
  contributions_count: number;
  current_amount: string;
  target_amount: string;
  progress_percent: string;
  status: string;
};

export type MonthlyReport = {
  period_start: string;
  period_end: string;
  base_currency: string;
  total_added: string;
  total_removed: string;
  net_saved: string;
  contributions_count: number;
  reversed_contributions_count: number;
  safe_monthly_capacity: string;
  goal_reports: MonthlyGoalReport[];
  plan_recommendations: string[];
  plan_conflicts: string[];
  warnings: string[];
};

export type CsvImportErrorDetail = {
  row_number: number | null;
  field: string | null;
  value: string | null;
  message: string;
};

export type CsvGoalImportResponse = {
  created_count: number;
  skipped_count: number;
  errors: string[];
  error_details: CsvImportErrorDetail[];
  created_goals: Goal[];
};

export type CsvContributionImportResponse = {
  created_count: number;
  skipped_count: number;
  errors: string[];
  error_details: CsvImportErrorDetail[];
  created_contributions: Contribution[];
};

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

export async function apiRequest<T>(
  path: string,
  token: string | null,
  options: RequestInit = {}
): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers
    }
  });

  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    const detail = payload?.detail ?? response.statusText;
    throw new ApiError(response.status, Array.isArray(detail) ? "Validation error" : detail);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

export function formatMoney(value: string | number | null | undefined, currency = "") {
  const amount = Number(value ?? 0);
  const formatted = new Intl.NumberFormat(undefined, {
    maximumFractionDigits: 2,
    minimumFractionDigits: 0
  }).format(Number.isFinite(amount) ? amount : 0);
  return currency ? `${formatted} ${currency}` : formatted;
}

export async function trackEvent(
  token: string | null,
  name: string,
  properties: Record<string, unknown> = {}
) {
  if (!token) return;
  try {
    await apiRequest<AnalyticsEvent>("/api/analytics/events", token, {
      method: "POST",
      body: JSON.stringify({ name, source: "web", properties })
    });
  } catch {
    // Product analytics must not block core financial workflows.
  }
}
