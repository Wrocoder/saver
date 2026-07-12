import {
  Activity,
  AlertTriangle,
  ArrowRight,
  ArrowDown,
  ArrowUp,
  BadgeDollarSign,
  BarChart3,
  Bell,
  BellRing,
  CalendarClock,
  Check,
  ChevronDown,
  ChevronUp,
  Coins,
  CreditCard,
  Download,
  ExternalLink,
  GripVertical,
  History,
  Pencil,
  Flag,
  Landmark,
  ListChecks,
  LogOut,
  Pause,
  PiggyBank,
  ReceiptText,
  Play,
  Plus,
  RefreshCw,
  Repeat,
  RotateCcw,
  Save,
  ShieldCheck,
  SlidersHorizontal,
  Target,
  Trash2,
  Upload,
  WalletCards,
  X
} from "lucide-react";
import { ChangeEvent, DragEvent, FormEvent, ReactNode, useEffect, useMemo, useState } from "react";
import {
  API_BASE_URL,
  apiRequest,
  AllocationStrategySettings,
  AnalyticsSummary,
  AuditLogEntry,
  AuthResponse,
  Contribution,
  CsvContributionImportResponse,
  CsvImportErrorDetail,
  CsvGoalImportResponse,
  Debt,
  ExchangeRate,
  Expense,
  FinancialSummary,
  formatMoney,
  Goal,
  GoalPriceHistory,
  Income,
  MonthlyReport,
  Notification,
  NotificationFrequency,
  NotificationSettings,
  Plan,
  RecurringRule,
  ScenarioPresetsResponse,
  ScenarioResponse,
  trackEvent,
  User
} from "./api";

const TOKEN_KEY = "money_saver_access_token";
const REFRESH_KEY = "money_saver_refresh_token";

type DashboardData = {
  goals: Goal[];
  plan: Plan | null;
  summary: FinancialSummary | null;
  incomes: Income[];
  expenses: Expense[];
  debts: Debt[];
  exchangeRates: ExchangeRate[];
  notifications: Notification[];
  notificationSettings: NotificationSettings | null;
  recurringRules: RecurringRule[];
  monthlyReport: MonthlyReport | null;
  strategy: AllocationStrategySettings | null;
  analyticsSummary: AnalyticsSummary | null;
  auditLog: AuditLogEntry[];
};

type DashboardPanelKey =
  | "overview"
  | "goals"
  | "cashflow"
  | "currency"
  | "scenario"
  | "allocation"
  | "prices"
  | "rules"
  | "notifications"
  | "data"
  | "reports"
  | "analytics"
  | "audit"
  | "monthPlan"
  | "plan";

type PanelStatus = {
  loading: boolean;
  error: string | null;
};

const dashboardPanelKeys: DashboardPanelKey[] = [
  "overview",
  "goals",
  "cashflow",
  "currency",
  "scenario",
  "allocation",
  "prices",
  "rules",
  "notifications",
  "data",
  "reports",
  "analytics",
  "audit",
  "monthPlan",
  "plan"
];

const emptyDashboard: DashboardData = {
  goals: [],
  plan: null,
  summary: null,
  incomes: [],
  expenses: [],
  debts: [],
  exchangeRates: [],
  notifications: [],
  notificationSettings: null,
  recurringRules: [],
  monthlyReport: null,
  strategy: null,
  analyticsSummary: null,
  auditLog: []
};

function buildPanelStatuses(
  loading = false,
  errors: Partial<Record<DashboardPanelKey, string | string[]>> = {}
): Record<DashboardPanelKey, PanelStatus> {
  return Object.fromEntries(
    dashboardPanelKeys.map((key) => {
      const errorValue = errors[key];
      const error = Array.isArray(errorValue) ? errorValue.join(" · ") : errorValue ?? null;
      return [key, { loading, error }];
    })
  ) as Record<DashboardPanelKey, PanelStatus>;
}

export function App() {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem(TOKEN_KEY));
  const [refreshToken, setRefreshToken] = useState<string | null>(() => localStorage.getItem(REFRESH_KEY));
  const [user, setUser] = useState<User | null>(null);
  const [data, setData] = useState<DashboardData>(emptyDashboard);
  const [panelStatuses, setPanelStatuses] = useState<Record<DashboardPanelKey, PanelStatus>>(() => buildPanelStatuses());
  const [loading, setLoading] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [deletingAccount, setDeletingAccount] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const isAuthed = Boolean(token);

  useEffect(() => {
    if (!token) return;
    void loadCurrentUser(token);
    void loadDashboard(token);
  }, [token]);

  async function loadCurrentUser(activeToken: string) {
    try {
      const me = await apiRequest<User>("/api/me", activeToken);
      setUser(me);
    } catch {
      logout();
    }
  }

  async function loadDashboard(activeToken = token) {
    if (!activeToken) return;
    setLoading(true);
    setError(null);
    setPanelStatuses(buildPanelStatuses(true));
    const loadErrors: string[] = [];
    const panelErrors: Partial<Record<DashboardPanelKey, string[]>> = {};
    const addPanelError = (panelKeys: DashboardPanelKey[], message: string) => {
      panelKeys.forEach((panelKey) => {
        panelErrors[panelKey] = [...(panelErrors[panelKey] ?? []), message];
      });
    };
    const loadPart = async <T,>(
      label: string,
      path: string,
      fallback: T,
      panelKeys: DashboardPanelKey[]
    ): Promise<T> => {
      try {
        return await apiRequest<T>(path, activeToken);
      } catch (err) {
        const message = err instanceof Error ? err.message : "Request failed";
        const scopedMessage = `${label}: ${message}`;
        loadErrors.push(scopedMessage);
        addPanelError(panelKeys, scopedMessage);
        return fallback;
      }
    };

    try {
      const [
        goals,
        plan,
        summary,
        incomes,
        expenses,
        debts,
        exchangeRates,
        notifications,
        notificationSettings,
        recurringRules,
        monthlyReport,
        strategy,
        analyticsSummary,
        auditLog
      ] = await Promise.all([
        loadPart<Goal[]>("Goals", "/api/goals", data.goals, ["overview", "goals", "allocation", "prices", "rules", "monthPlan", "plan"]),
        loadPart<Plan | null>("Plan", "/api/plan", data.plan, ["overview", "goals", "scenario", "monthPlan", "plan"]),
        loadPart<FinancialSummary | null>("Financial summary", "/api/financial-summary", data.summary, ["overview", "cashflow", "scenario", "monthPlan", "plan"]),
        loadPart<Income[]>("Income", "/api/incomes", data.incomes, ["cashflow"]),
        loadPart<Expense[]>("Expenses", "/api/expenses", data.expenses, ["cashflow"]),
        loadPart<Debt[]>("Debts", "/api/debts", data.debts, ["cashflow"]),
        loadPart<ExchangeRate[]>("Exchange rates", "/api/exchange-rates", data.exchangeRates, ["currency"]),
        loadPart<Notification[]>("Notifications", "/api/notifications?status_filter=unread", data.notifications, ["notifications"]),
        loadPart<NotificationSettings | null>("Notification settings", "/api/notification-settings", data.notificationSettings, ["notifications"]),
        loadPart<RecurringRule[]>("Recurring rules", "/api/recurring-rules", data.recurringRules, ["rules"]),
        loadPart<MonthlyReport | null>("Monthly report", "/api/reports/monthly", data.monthlyReport, ["reports", "monthPlan"]),
        loadPart<AllocationStrategySettings | null>("Allocation strategy", "/api/plan/strategy", data.strategy, ["allocation"]),
        loadPart<AnalyticsSummary | null>("Analytics", "/api/analytics/summary", data.analyticsSummary, ["analytics"]),
        loadPart<AuditLogEntry[]>("Audit log", "/api/audit-log?limit=20", data.auditLog, ["audit"])
      ]);
      setData({
        goals,
        plan,
        summary,
        incomes,
        expenses,
        debts,
        exchangeRates,
        notifications,
        notificationSettings,
        recurringRules,
        monthlyReport,
        strategy,
        analyticsSummary,
        auditLog
      });
      if (loadErrors.length > 0) {
        setError(loadErrors.join(" · "));
      }
      setPanelStatuses(buildPanelStatuses(false, panelErrors));
    } catch (err) {
      const message = err instanceof Error ? err.message : "Could not load dashboard";
      setError(message);
      setPanelStatuses(buildPanelStatuses(false, Object.fromEntries(dashboardPanelKeys.map((key) => [key, message])) as Partial<Record<DashboardPanelKey, string>>));
    } finally {
      setLoading(false);
    }
  }

  function setAuth(auth: AuthResponse) {
    localStorage.setItem(TOKEN_KEY, auth.access_token);
    localStorage.setItem(REFRESH_KEY, auth.refresh_token);
    setToken(auth.access_token);
    setRefreshToken(auth.refresh_token);
    setUser(auth.user);
  }

  function logout() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(REFRESH_KEY);
    setToken(null);
    setRefreshToken(null);
    setUser(null);
    setData(emptyDashboard);
    setPanelStatuses(buildPanelStatuses());
  }

  async function deleteAccount() {
    if (!token) return;
    const confirmed = window.confirm(
      "Delete your account? Your sessions will be revoked and this login will stop working."
    );
    if (!confirmed) return;

    setDeletingAccount(true);
    setError(null);
    try {
      await apiRequest<void>("/api/me", token, { method: "DELETE" });
      logout();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not delete account");
    } finally {
      setDeletingAccount(false);
    }
  }

  async function exportUserData() {
    if (!token) return;
    setExporting(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE_URL}/api/export/user-data`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (!response.ok) {
        throw new Error(response.statusText || "Could not export data");
      }
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = filenameFromContentDisposition(response.headers.get("Content-Disposition")) ?? "money-saver-export.json";
      link.click();
      URL.revokeObjectURL(url);
      void trackEvent(token, "data_export_downloaded");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not export data");
    } finally {
      setExporting(false);
    }
  }

  if (!isAuthed) {
    return <AuthScreen onAuth={setAuth} />;
  }

  return (
    <div className="app-shell">
      <a className="skip-link" href="#main-content">Skip to content</a>
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">
            <PiggyBank size={23} />
          </div>
          <div>
            <div className="brand-title">Money Saver</div>
            <div className="brand-subtitle">Financial goals</div>
          </div>
        </div>
        <nav className="nav-list" aria-label="Primary navigation">
          <a href="#overview"><WalletCards size={18} /> Overview</a>
          <a href="#goals"><Target size={18} /> Goals</a>
          <a href="#cashflow"><Landmark size={18} /> Cashflow</a>
          <a href="#currency"><Coins size={18} /> Currency</a>
          <a href="#allocation"><BadgeDollarSign size={18} /> Allocation</a>
          <a href="#prices"><ReceiptText size={18} /> Prices</a>
          <a href="#rules"><Repeat size={18} /> Rules</a>
          <a href="#notifications"><Bell size={18} /> Alerts</a>
          <a href="#data"><Download size={18} /> Data</a>
          <a href="#reports"><BarChart3 size={18} /> Reports</a>
          <a href="#analytics"><Activity size={18} /> Analytics</a>
          <a href="#audit"><History size={18} /> Audit</a>
          <a href="#month-plan"><CalendarClock size={18} /> Month plan</a>
          <a href="#plan"><ListChecks size={18} /> Plan</a>
        </nav>
        <div className="sidebar-actions">
          <button className="ghost-button" type="button" onClick={logout}>
            <LogOut size={18} /> Sign out
          </button>
          <button className="ghost-button danger" type="button" onClick={() => void deleteAccount()} disabled={deletingAccount}>
            <Trash2 size={18} /> Delete account
          </button>
        </div>
      </aside>

      <main className="main-content" id="main-content">
        <header className="topbar">
          <div>
            <p className="eyebrow">Workspace</p>
            <h1>{user?.name || user?.email || "Financial plan"}</h1>
          </div>
          <div className="topbar-actions">
            <button className="icon-button wide" type="button" onClick={() => void exportUserData()} disabled={exporting}>
              <Download size={18} /> Export
            </button>
            <button className="icon-button wide" type="button" onClick={() => void loadDashboard()} disabled={loading}>
              <RefreshCw size={18} /> Refresh
            </button>
          </div>
        </header>

        {error && (
          <div className="alert-banner" role="alert">
            <AlertTriangle size={18} />
            <span>{error}</span>
          </div>
        )}

        <OverviewSection data={data} status={panelStatuses.overview} />

        <section className="work-grid">
          <GoalPanel token={token} goals={data.goals} plan={data.plan} status={panelStatuses.goals} onChanged={() => void loadDashboard()} />
          <CashflowPanel token={token} data={data} status={panelStatuses.cashflow} onChanged={() => void loadDashboard()} />
        </section>

        <section className="secondary-grid">
          <CurrencyPanel token={token} rates={data.exchangeRates} status={panelStatuses.currency} onChanged={() => void loadDashboard()} />
          <ScenarioPanel token={token} plan={data.plan} summary={data.summary} status={panelStatuses.scenario} />
          <AllocationStrategyPanel token={token} goals={data.goals} strategy={data.strategy} status={panelStatuses.allocation} onChanged={() => void loadDashboard()} />
          <PriceHistoryPanel token={token} goals={data.goals} status={panelStatuses.prices} onChanged={() => void loadDashboard()} />
          <RecurringRulesPanel token={token} goals={data.goals} rules={data.recurringRules} status={panelStatuses.rules} onChanged={() => void loadDashboard()} />
          <NotificationPanel token={token} notifications={data.notifications} settings={data.notificationSettings} status={panelStatuses.notifications} onChanged={() => void loadDashboard()} />
          <CsvPanel token={token} status={panelStatuses.data} onChanged={() => void loadDashboard()} />
        </section>

        <ReportsPanel token={token} initialReport={data.monthlyReport} status={panelStatuses.reports} />
        <AnalyticsPanel summary={data.analyticsSummary} status={panelStatuses.analytics} />
        <AuditLogPanel entries={data.auditLog} status={panelStatuses.audit} />
        <MonthlyPlanPanel plan={data.plan} goals={data.goals} summary={data.summary} monthlyReport={data.monthlyReport} status={panelStatuses.monthPlan} />
        <PlanSection plan={data.plan} summary={data.summary} refreshToken={refreshToken} status={panelStatuses.plan} />
      </main>
    </div>
  );
}

function AuthScreen({ onAuth }: { onAuth: (auth: AuthResponse) => void }) {
  const [mode, setMode] = useState<"register" | "login">("register");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [baseCurrency, setBaseCurrency] = useState("USD");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const auth = await apiRequest<AuthResponse>(`/api/auth/${mode}`, null, {
        method: "POST",
        body: JSON.stringify(
          mode === "register"
            ? { email, password, name: name || null, base_currency: baseCurrency }
            : { email, password }
        )
      });
      onAuth(auth);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Authentication failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="auth-layout">
      <section className="auth-visual">
        <div className="auth-brand">
          <PiggyBank size={28} />
          <span>Money Saver</span>
        </div>
        <div className="auth-forecast">
          <div className="forecast-line">
            <span>Available this month</span>
            <strong>$1,200</strong>
          </div>
          <div className="forecast-track">
            <div />
          </div>
          <div className="forecast-cards">
            <div>
              <small>Main goal</small>
              <strong>Emergency fund</strong>
            </div>
            <div>
              <small>Projected</small>
              <strong>Oct 2026</strong>
            </div>
          </div>
        </div>
      </section>

      <section className="auth-panel">
        <div className="segmented" aria-label="Authentication mode">
          <button
            className={mode === "register" ? "active" : ""}
            type="button"
            aria-pressed={mode === "register"}
            onClick={() => setMode("register")}
          >
            Create
          </button>
          <button
            className={mode === "login" ? "active" : ""}
            type="button"
            aria-pressed={mode === "login"}
            onClick={() => setMode("login")}
          >
            Login
          </button>
        </div>
        <h1>{mode === "register" ? "Create your plan" : "Continue planning"}</h1>
        <form className="form-stack" onSubmit={submit}>
          <label>
            Email
            <input type="email" value={email} onChange={(event) => setEmail(event.target.value)} required />
          </label>
          <label>
            Password
            <input type="password" value={password} onChange={(event) => setPassword(event.target.value)} minLength={8} required />
          </label>
          {mode === "register" && (
            <>
              <label>
                Name
                <input value={name} onChange={(event) => setName(event.target.value)} />
              </label>
              <label>
                Base currency
                <select value={baseCurrency} onChange={(event) => setBaseCurrency(event.target.value)}>
                  <option>USD</option>
                  <option>EUR</option>
                  <option>PLN</option>
                  <option>GBP</option>
                </select>
              </label>
            </>
          )}
          {error && <div className="inline-error" role="alert">{error}</div>}
          <button className="primary-button" type="submit" disabled={loading}>
            {loading ? "Working..." : mode === "register" ? "Create account" : "Login"}
            <ArrowRight size={18} />
          </button>
        </form>
      </section>
    </main>
  );
}

function PanelNotice({
  status,
  loadingText = "Loading panel data..."
}: {
  status: PanelStatus;
  loadingText?: string;
}) {
  if (status.loading) {
    return (
      <div className="panel-state loading" role="status" aria-live="polite">
        <RefreshCw size={16} />
        <span>{loadingText}</span>
      </div>
    );
  }

  if (status.error) {
    return (
      <div className="panel-state error" role="alert">
        <AlertTriangle size={16} />
        <span>{status.error}</span>
      </div>
    );
  }

  return null;
}

function OverviewSection({ data, status }: { data: DashboardData; status: PanelStatus }) {
  const summary = data.summary;
  const plan = data.plan;
  const activeGoal = plan?.goals[0];
  const totalSaved = useMemo(
    () => data.goals.reduce((sum, goal) => sum + Number(goal.current_amount), 0),
    [data.goals]
  );
  const currency = summary?.base_currency || activeGoal?.currency || "USD";

  return (
    <section id="overview" className="overview-grid" aria-busy={status.loading}>
      <PanelNotice status={status} loadingText="Loading overview..." />
      <MetricCard
        icon={<PiggyBank size={21} />}
        label="Saved in goals"
        value={formatMoney(totalSaved, currency)}
        tone="green"
      />
      <MetricCard
        icon={<WalletCards size={21} />}
        label="Safe monthly capacity"
        value={formatMoney(summary?.effective_monthly_available_amount, summary?.base_currency)}
        tone="blue"
      />
      <MetricCard
        icon={<Target size={21} />}
        label="Active goals"
        value={String(data.goals.length)}
        tone="neutral"
      />
      <MetricCard
        icon={<CalendarClock size={21} />}
        label="Current focus"
        value={activeGoal?.title ?? "No goal yet"}
        tone="amber"
      />
    </section>
  );
}

function MetricCard({ icon, label, value, tone }: { icon: ReactNode; label: string; value: string; tone: string }) {
  return (
    <article className={`metric-card ${tone}`}>
      <div className="metric-icon">{icon}</div>
      <span>{label}</span>
      <strong>{value}</strong>
    </article>
  );
}

function DetailMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="detail-metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

type GoalEditDraft = {
  title: string;
  target_amount: string;
  current_amount: string;
  currency: string;
  desired_date: string;
};

function GoalPanel({
  token,
  goals,
  plan,
  status,
  onChanged
}: {
  token: string | null;
  goals: Goal[];
  plan: Plan | null;
  status: PanelStatus;
  onChanged: () => void;
}) {
  const [title, setTitle] = useState("");
  const [target, setTarget] = useState("");
  const [current, setCurrent] = useState("0");
  const [currency, setCurrency] = useState("USD");
  const [desiredDate, setDesiredDate] = useState("");
  const [orderedGoals, setOrderedGoals] = useState<Goal[]>(goals);
  const [draggedGoalId, setDraggedGoalId] = useState("");
  const [orderSaving, setOrderSaving] = useState(false);
  const [editingGoalId, setEditingGoalId] = useState("");
  const [goalDraft, setGoalDraft] = useState<GoalEditDraft | null>(null);
  const [expandedGoalId, setExpandedGoalId] = useState("");
  const [selectedGoalId, setSelectedGoalId] = useState("");
  const [contributions, setContributions] = useState<Contribution[]>([]);
  const [contributionsLoading, setContributionsLoading] = useState(false);
  const [contributionAmount, setContributionAmount] = useState("");
  const [contributionCurrency, setContributionCurrency] = useState("USD");
  const [contributionSource, setContributionSource] = useState("");
  const [error, setError] = useState<string | null>(null);
  const listedGoals = orderedGoals.length === goals.length ? orderedGoals : goals;
  const planByGoalId = useMemo(
    () => new Map((plan?.goals ?? []).map((goal) => [goal.goal_id, goal])),
    [plan]
  );

  useEffect(() => {
    setOrderedGoals(goals);
  }, [goals]);

  useEffect(() => {
    if (!goals.length) {
      setSelectedGoalId("");
      setContributions([]);
      return;
    }
    if (!selectedGoalId || !goals.some((goal) => goal.id === selectedGoalId)) {
      setSelectedGoalId(goals[0].id);
    }
  }, [goals, selectedGoalId]);

  useEffect(() => {
    if (!selectedGoalId || !token) return;
    void loadContributions(selectedGoalId);
  }, [selectedGoalId, token]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    try {
      const goal = await apiRequest<Goal>("/api/goals", token, {
        method: "POST",
        body: JSON.stringify({
          title,
          target_amount: target,
          current_amount: current || "0",
          currency,
          desired_date: desiredDate || null,
          priority: goals.length + 1
        })
      });
      setTitle("");
      setTarget("");
      setCurrent("0");
      setDesiredDate("");
      void trackEvent(token, "goal_created", {
        goal_id: goal.id,
        currency: goal.currency,
        has_deadline: Boolean(goal.desired_date)
      });
      onChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create goal");
    }
  }

  function beginEditGoal(goal: Goal) {
    setEditingGoalId(goal.id);
    setGoalDraft({
      title: goal.title,
      target_amount: goal.target_amount,
      current_amount: goal.current_amount,
      currency: goal.currency,
      desired_date: goal.desired_date ?? ""
    });
  }

  function cancelEditGoal() {
    setEditingGoalId("");
    setGoalDraft(null);
  }

  function toggleGoalDetails(goalId: string) {
    setExpandedGoalId((current) => {
      const nextGoalId = current === goalId ? "" : goalId;
      if (nextGoalId) {
        void trackEvent(token, "goal_details_opened", { goal_id: goalId });
      }
      return nextGoalId;
    });
  }

  async function saveGoal(goalId: string) {
    if (!goalDraft) return;
    setError(null);
    try {
      await apiRequest<Goal>(`/api/goals/${goalId}`, token, {
        method: "PATCH",
        body: JSON.stringify({
          title: goalDraft.title,
          target_amount: goalDraft.target_amount,
          current_amount: goalDraft.current_amount,
          currency: goalDraft.currency,
          desired_date: goalDraft.desired_date || null
        })
      });
      cancelEditGoal();
      void trackEvent(token, "goal_updated", { goal_id: goalId });
      onChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not update goal");
    }
  }

  async function archiveGoal(goalId: string) {
    setError(null);
    try {
      await apiRequest<void>(`/api/goals/${goalId}`, token, { method: "DELETE" });
      if (selectedGoalId === goalId) {
        setSelectedGoalId("");
        setContributions([]);
      }
      cancelEditGoal();
      void trackEvent(token, "goal_archived", { goal_id: goalId });
      onChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not archive goal");
    }
  }

  async function persistGoalOrder(nextGoals: Goal[]) {
    if (!token || nextGoals.length < 2) return;
    setOrderSaving(true);
    setError(null);
    try {
      await apiRequest<Goal[]>("/api/priorities", token, {
        method: "POST",
        body: JSON.stringify({ ordered_goal_ids: nextGoals.map((goal) => goal.id) })
      });
      void trackEvent(token, "priority_changed", { goal_count: nextGoals.length });
      onChanged();
    } catch (err) {
      setOrderedGoals(goals);
      setError(err instanceof Error ? err.message : "Could not save goal order");
    } finally {
      setOrderSaving(false);
    }
  }

  function reorderGoals(sourceGoalId: string, targetGoalId: string) {
    if (sourceGoalId === targetGoalId) return;
    const sourceIndex = listedGoals.findIndex((goal) => goal.id === sourceGoalId);
    const targetIndex = listedGoals.findIndex((goal) => goal.id === targetGoalId);
    if (sourceIndex < 0 || targetIndex < 0) return;

    const nextGoals = [...listedGoals];
    const [movedGoal] = nextGoals.splice(sourceIndex, 1);
    nextGoals.splice(targetIndex, 0, movedGoal);
    setOrderedGoals(nextGoals);
    void persistGoalOrder(nextGoals);
  }

  function moveGoal(goalId: string, direction: -1 | 1) {
    const sourceIndex = listedGoals.findIndex((goal) => goal.id === goalId);
    const targetIndex = sourceIndex + direction;
    if (sourceIndex < 0 || targetIndex < 0 || targetIndex >= listedGoals.length) return;

    const nextGoals = [...listedGoals];
    [nextGoals[sourceIndex], nextGoals[targetIndex]] = [nextGoals[targetIndex], nextGoals[sourceIndex]];
    setOrderedGoals(nextGoals);
    void persistGoalOrder(nextGoals);
  }

  function handleGoalDragStart(goalId: string) {
    setDraggedGoalId(goalId);
  }

  function handleGoalDragOver(event: DragEvent<HTMLElement>) {
    event.preventDefault();
  }

  function handleGoalDrop(event: DragEvent<HTMLElement>, targetGoalId: string) {
    event.preventDefault();
    if (!draggedGoalId) return;
    reorderGoals(draggedGoalId, targetGoalId);
    setDraggedGoalId("");
  }

  function handleGoalDragEnd() {
    setDraggedGoalId("");
  }

  async function loadContributions(goalId: string) {
    setContributionsLoading(true);
    try {
      const result = await apiRequest<Contribution[]>(`/api/goals/${goalId}/contributions`, token);
      setContributions(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load contributions");
    } finally {
      setContributionsLoading(false);
    }
  }

  async function addContribution(event: FormEvent) {
    event.preventDefault();
    if (!selectedGoalId) return;
    setError(null);
    try {
      await apiRequest<Contribution>(`/api/goals/${selectedGoalId}/contributions`, token, {
        method: "POST",
        body: JSON.stringify({
          type: "add",
          amount: contributionAmount,
          currency: contributionCurrency,
          source: contributionSource || null
        })
      });
      setContributionAmount("");
      setContributionSource("");
      void trackEvent(token, "contribution_added", {
        goal_id: selectedGoalId,
        currency: contributionCurrency
      });
      await loadContributions(selectedGoalId);
      onChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not add contribution");
    }
  }

  async function reverseContribution(contributionId: string) {
    setError(null);
    try {
      await apiRequest<Contribution>(`/api/contributions/${contributionId}/reverse`, token, {
        method: "POST"
      });
      if (selectedGoalId) {
        await loadContributions(selectedGoalId);
      }
      void trackEvent(token, "contribution_reversed", { contribution_id: contributionId });
      onChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not reverse contribution");
    }
  }

  return (
    <section id="goals" className="panel" aria-busy={status.loading}>
      <div className="panel-header">
        <div>
          <p className="eyebrow">Goals</p>
          <h2>Targets and progress</h2>
        </div>
        <Flag size={22} />
      </div>
      <PanelNotice status={status} loadingText="Loading goals and projections..." />
      <form className="compact-form" onSubmit={submit}>
        <input aria-label="Goal name" placeholder="Goal name" value={title} onChange={(event) => setTitle(event.target.value)} required />
        <input aria-label="Goal target amount" placeholder="Target" type="number" min="0" step="0.01" value={target} onChange={(event) => setTarget(event.target.value)} required />
        <input aria-label="Current saved amount" placeholder="Saved" type="number" min="0" step="0.01" value={current} onChange={(event) => setCurrent(event.target.value)} />
        <select aria-label="Goal currency" value={currency} onChange={(event) => setCurrency(event.target.value)}>
          <option>USD</option>
          <option>EUR</option>
          <option>PLN</option>
          <option>GBP</option>
        </select>
        <input aria-label="Desired goal date" type="date" value={desiredDate} onChange={(event) => setDesiredDate(event.target.value)} />
        <button className="primary-button compact" type="submit"><Plus size={17} /> Add</button>
      </form>
      {error && <div className="inline-error" role="alert">{error}</div>}
      {orderSaving && <div className="inline-note">Saving goal order...</div>}
      <div className="goal-list">
        {listedGoals.length === 0 && <EmptyState text="Create a first goal to generate a plan." />}
        {listedGoals.map((goal, index) => {
          const progress = Math.min(100, (Number(goal.current_amount) / Number(goal.target_amount)) * 100 || 0);
          const isEditing = editingGoalId === goal.id && goalDraft;
          const isExpanded = expandedGoalId === goal.id;
          const projection = planByGoalId.get(goal.id);
          const remainingAmount = Math.max(0, Number(goal.target_amount) - Number(goal.current_amount));
          if (isEditing) {
            return (
              <article className="goal-row goal-row-edit" key={goal.id}>
                <input
                  aria-label="Goal title"
                  value={goalDraft.title}
                  onChange={(event) => setGoalDraft({ ...goalDraft, title: event.target.value })}
                />
                <input
                  aria-label="Target amount"
                  type="number"
                  min="0"
                  step="0.01"
                  value={goalDraft.target_amount}
                  onChange={(event) => setGoalDraft({ ...goalDraft, target_amount: event.target.value })}
                />
                <input
                  aria-label="Current amount"
                  type="number"
                  min="0"
                  step="0.01"
                  value={goalDraft.current_amount}
                  onChange={(event) => setGoalDraft({ ...goalDraft, current_amount: event.target.value })}
                />
                <select
                  aria-label="Goal currency"
                  value={goalDraft.currency}
                  onChange={(event) => setGoalDraft({ ...goalDraft, currency: event.target.value })}
                >
                  <option>USD</option>
                  <option>EUR</option>
                  <option>PLN</option>
                  <option>GBP</option>
                </select>
                <input
                  aria-label="Desired date"
                  type="date"
                  value={goalDraft.desired_date}
                  onChange={(event) => setGoalDraft({ ...goalDraft, desired_date: event.target.value })}
                />
                <div className="row-actions">
                  <button className="icon-button small" type="button" onClick={() => void saveGoal(goal.id)} aria-label="Save goal">
                    <Save size={16} />
                  </button>
                  <button className="icon-button small" type="button" onClick={cancelEditGoal} aria-label="Cancel goal edit">
                    <X size={16} />
                  </button>
                </div>
              </article>
            );
          }
          return (
            <article
              className={`goal-row ${draggedGoalId === goal.id ? "dragging" : ""} ${isExpanded ? "expanded" : ""}`}
              key={goal.id}
              draggable={listedGoals.length > 1}
              onDragStart={() => handleGoalDragStart(goal.id)}
              onDragOver={handleGoalDragOver}
              onDrop={(event) => handleGoalDrop(event, goal.id)}
              onDragEnd={handleGoalDragEnd}
            >
              <div className="goal-drag-cell">
                <GripVertical size={18} />
                <span>{index + 1}</span>
              </div>
              <div className="goal-main">
                <strong>{goal.title}</strong>
                <span>{formatMoney(goal.current_amount, goal.currency)} of {formatMoney(goal.target_amount, goal.currency)}</span>
              </div>
              <div className="progress-track">
                <div
                  role="progressbar"
                  aria-label={`${goal.title} progress`}
                  aria-valuemin={0}
                  aria-valuemax={100}
                  aria-valuenow={Math.round(progress)}
                  style={{ width: `${progress}%` }}
                />
              </div>
              <span className={`status-pill ${goal.status}`}>{goal.status}</span>
              <div className="row-actions">
                <button
                  className="icon-button small"
                  type="button"
                  onClick={() => moveGoal(goal.id, -1)}
                  disabled={index === 0 || orderSaving}
                  aria-label={`Move ${goal.title} up`}
                  title="Move up"
                >
                  <ArrowUp size={16} />
                </button>
                <button
                  className="icon-button small"
                  type="button"
                  onClick={() => moveGoal(goal.id, 1)}
                  disabled={index === listedGoals.length - 1 || orderSaving}
                  aria-label={`Move ${goal.title} down`}
                  title="Move down"
                >
                  <ArrowDown size={16} />
                </button>
                <button className="icon-button small" type="button" onClick={() => beginEditGoal(goal)} aria-label={`Edit ${goal.title}`}>
                  <Pencil size={16} />
                </button>
                <button
                  className="icon-button small"
                  type="button"
                  onClick={() => toggleGoalDetails(goal.id)}
                  aria-expanded={isExpanded}
                  aria-controls={`goal-details-${goal.id}`}
                  aria-label={`${isExpanded ? "Hide" : "Show"} ${goal.title} details`}
                >
                  {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                </button>
                <button className="icon-button small danger" type="button" onClick={() => void archiveGoal(goal.id)} aria-label={`Archive ${goal.title}`}>
                  <Trash2 size={16} />
                </button>
              </div>
              {isExpanded && (
                <div className="goal-detail-area" id={`goal-details-${goal.id}`}>
                  <div className="goal-detail-grid">
                    <DetailMetric label="Remaining" value={formatMoney(remainingAmount, goal.currency)} />
                    <DetailMetric label="Progress" value={`${Math.round(progress)}%`} />
                    <DetailMetric label="Target date" value={goal.desired_date ?? "Not set"} />
                    <DetailMetric label="Projected date" value={projection?.expected_completion_date ?? "No projection"} />
                    <DetailMetric
                      label="Required monthly"
                      value={projection?.required_monthly_amount ? formatMoney(projection.required_monthly_amount, goal.currency) : "No deadline"}
                    />
                    <DetailMetric
                      label="First month"
                      value={projection?.allocated_first_month ? formatMoney(projection.allocated_first_month, goal.currency) : formatMoney(0, goal.currency)}
                    />
                    <DetailMetric label="Deadline type" value={goal.deadline_type} />
                    <DetailMetric label="Importance" value={`${goal.importance}/5`} />
                  </div>
                  {projection?.explanation && <div className="goal-detail-note">{projection.explanation}</div>}
                  {projection?.explainability && (
                    <div className="explainability-panel">
                      <strong>Date drivers</strong>
                      <div className="explainability-grid">
                        {projection.explainability.factors.slice(0, 8).map((factor) => (
                          <div className="explainability-factor" key={factor.key}>
                            <span>{factor.label}</span>
                            <strong>{factor.value}</strong>
                            <small>{factor.impact}</small>
                          </div>
                        ))}
                      </div>
                      <div className="explainability-assumptions">
                        {projection.explainability.assumptions.map((assumption) => (
                          <span key={assumption}>{assumption}</span>
                        ))}
                      </div>
                    </div>
                  )}
                  {(goal.category || goal.description || goal.notes || goal.product_url || goal.expected_purchase_date) && (
                    <div className="goal-detail-meta">
                      {goal.category && <span>{goal.category}</span>}
                      {goal.expected_purchase_date && <span>Purchase {goal.expected_purchase_date}</span>}
                      {goal.description && <p>{goal.description}</p>}
                      {goal.notes && <p>{goal.notes}</p>}
                      {goal.product_url && (
                        <a href={goal.product_url} target="_blank" rel="noreferrer">
                          <ExternalLink size={15} /> Product link
                        </a>
                      )}
                    </div>
                  )}
                </div>
              )}
            </article>
          );
        })}
      </div>
      <div className="subsection">
        <div className="subsection-header">
          <h3>Contributions</h3>
          <RotateCcw size={18} />
        </div>
        <form className="compact-form contribution-form" onSubmit={addContribution}>
          <select aria-label="Contribution goal" value={selectedGoalId} onChange={(event) => setSelectedGoalId(event.target.value)} disabled={!listedGoals.length}>
            {listedGoals.map((goal) => (
              <option key={goal.id} value={goal.id}>{goal.title}</option>
            ))}
          </select>
          <input
            aria-label="Contribution amount"
            placeholder="Amount"
            type="number"
            min="0"
            step="0.01"
            value={contributionAmount}
            onChange={(event) => setContributionAmount(event.target.value)}
            required
            disabled={!listedGoals.length}
          />
          <select aria-label="Contribution currency" value={contributionCurrency} onChange={(event) => setContributionCurrency(event.target.value)} disabled={!listedGoals.length}>
            <option>USD</option>
            <option>EUR</option>
            <option>PLN</option>
            <option>GBP</option>
          </select>
          <input
            aria-label="Contribution source"
            placeholder="Source"
            value={contributionSource}
            onChange={(event) => setContributionSource(event.target.value)}
            disabled={!listedGoals.length}
          />
          <button className="primary-button compact" type="submit" disabled={!listedGoals.length}><Plus size={17} /> Add money</button>
        </form>
        <PanelNotice status={{ loading: contributionsLoading, error: null }} loadingText="Loading contribution history..." />
        <div className="operation-list">
          {selectedGoalId && contributions.length === 0 && <EmptyState text="No contributions for this goal yet." />}
          {contributions.map((item) => (
            <article className="operation-row" key={item.id}>
              <div>
                <strong>{formatMoney(item.amount, item.currency)}</strong>
                <span>
                  {item.amount_in_goal_currency
                    ? `${formatMoney(item.amount_in_goal_currency)} in goal currency`
                    : "Same currency"}
                  {item.source ? ` · ${item.source}` : ""}
                </span>
              </div>
              <div className="operation-actions">
                <span className={item.reversed_at ? "status-pill archived" : "status-pill active"}>
                  {item.reversed_at ? "reversed" : item.type}
                </span>
                {!item.reversed_at && (
                  <button className="icon-button small" type="button" onClick={() => void reverseContribution(item.id)} aria-label={`Reverse ${formatMoney(item.amount, item.currency)} contribution`}>
                    <RotateCcw size={16} /> Reverse
                  </button>
                )}
              </div>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}

type CashflowKind = "income" | "expense" | "debt";

type CashflowDraft = {
  kind: CashflowKind;
  id: string;
  label: string;
  amount: string;
  balance: string;
  currency: string;
};

function CashflowPanel({
  token,
  data,
  status,
  onChanged
}: {
  token: string | null;
  data: DashboardData;
  status: PanelStatus;
  onChanged: () => void;
}) {
  return (
    <section id="cashflow" className="panel" aria-busy={status.loading}>
      <div className="panel-header">
        <div>
          <p className="eyebrow">Cashflow</p>
          <h2>Monthly constraints</h2>
        </div>
        <ShieldCheck size={22} />
      </div>
      <PanelNotice status={status} loadingText="Loading monthly constraints..." />
      <QuickCashflowForms token={token} onChanged={onChanged} />
      <div className="summary-table">
        <SummaryLine icon={<BadgeDollarSign size={18} />} label="Income" value={data.summary?.total_monthly_income} currency={data.summary?.base_currency} />
        <SummaryLine icon={<CreditCard size={18} />} label="Expenses" value={data.summary?.total_monthly_expenses} currency={data.summary?.base_currency} />
        <SummaryLine icon={<Landmark size={18} />} label="Debt payments" value={data.summary?.total_monthly_debt_payments} currency={data.summary?.base_currency} />
        <SummaryLine icon={<ShieldCheck size={18} />} label="Emergency reserve" value={data.summary?.emergency_fund_monthly_reserve} currency={data.summary?.base_currency} />
      </div>
      <CashflowEntries token={token} data={data} onChanged={onChanged} />
      {data.summary?.warnings.map((warning) => (
        <div className="mini-warning" key={warning}><AlertTriangle size={16} /> {warning}</div>
      ))}
    </section>
  );
}

function CashflowEntries({ token, data, onChanged }: { token: string | null; data: DashboardData; onChanged: () => void }) {
  const [draft, setDraft] = useState<CashflowDraft | null>(null);
  const [error, setError] = useState<string | null>(null);
  const rows = [
    ...data.incomes.map((item) => ({
      kind: "income" as const,
      id: item.id,
      label: item.source || "Income",
      amount: item.amount,
      balance: "",
      currency: item.currency,
      meta: item.frequency
    })),
    ...data.expenses.map((item) => ({
      kind: "expense" as const,
      id: item.id,
      label: item.category,
      amount: item.amount,
      balance: "",
      currency: item.currency,
      meta: item.frequency
    })),
    ...data.debts.map((item) => ({
      kind: "debt" as const,
      id: item.id,
      label: item.creditor || item.type,
      amount: item.min_monthly_payment,
      balance: item.balance,
      currency: item.currency,
      meta: `${item.status} · balance ${formatMoney(item.balance, item.currency)}`
    }))
  ];

  function beginEdit(row: (typeof rows)[number]) {
    setDraft({
      kind: row.kind,
      id: row.id,
      label: row.label,
      amount: row.amount,
      balance: row.balance,
      currency: row.currency
    });
  }

  async function saveEntry() {
    if (!draft) return;
    setError(null);
    const path =
      draft.kind === "income"
        ? `/api/incomes/${draft.id}`
        : draft.kind === "expense"
          ? `/api/expenses/${draft.id}`
          : `/api/debts/${draft.id}`;
    const payload =
      draft.kind === "income"
        ? { amount: draft.amount, currency: draft.currency, source: draft.label || null }
        : draft.kind === "expense"
          ? { amount: draft.amount, currency: draft.currency, category: draft.label || "expense" }
          : {
              min_monthly_payment: draft.amount,
              balance: draft.balance || "0",
              currency: draft.currency,
              creditor: draft.label || null
            };

    try {
      await apiRequest(path, token, {
        method: "PATCH",
        body: JSON.stringify(payload)
      });
      setDraft(null);
      void trackEvent(token, "cashflow_entry_updated", { kind: draft.kind });
      onChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not update cashflow entry");
    }
  }

  async function deleteEntry(kind: CashflowKind, id: string) {
    setError(null);
    const path =
      kind === "income"
        ? `/api/incomes/${id}`
        : kind === "expense"
          ? `/api/expenses/${id}`
          : `/api/debts/${id}`;

    try {
      await apiRequest<void>(path, token, { method: "DELETE" });
      if (draft?.id === id) {
        setDraft(null);
      }
      void trackEvent(token, "cashflow_entry_deleted", { kind });
      onChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not delete cashflow entry");
    }
  }

  return (
    <div className="subsection">
      <div className="subsection-header">
        <h3>Entries</h3>
        <Landmark size={18} />
      </div>
      {error && <div className="inline-error" role="alert">{error}</div>}
      <div className="entry-list">
        {rows.length === 0 && <EmptyState text="Add income, expenses, or debt payments to calculate safe capacity." />}
        {rows.map((row) => {
          const isEditing = draft?.kind === row.kind && draft.id === row.id;
          if (isEditing && draft) {
            return (
              <article className="entry-row editing" key={`${row.kind}-${row.id}`}>
                <div className="entry-edit-grid">
                  <input
                    aria-label="Entry label"
                    value={draft.label}
                    onChange={(event) => setDraft({ ...draft, label: event.target.value })}
                  />
                  <input
                    aria-label={draft.kind === "debt" ? "Monthly payment" : "Amount"}
                    type="number"
                    min="0"
                    step="0.01"
                    value={draft.amount}
                    onChange={(event) => setDraft({ ...draft, amount: event.target.value })}
                  />
                  {draft.kind === "debt" && (
                    <input
                      aria-label="Debt balance"
                      type="number"
                      min="0"
                      step="0.01"
                      value={draft.balance}
                      onChange={(event) => setDraft({ ...draft, balance: event.target.value })}
                    />
                  )}
                  <select
                    aria-label="Entry currency"
                    value={draft.currency}
                    onChange={(event) => setDraft({ ...draft, currency: event.target.value })}
                  >
                    <option>USD</option>
                    <option>EUR</option>
                    <option>PLN</option>
                    <option>GBP</option>
                  </select>
                  <div className="row-actions">
                    <button className="icon-button small" type="button" onClick={() => void saveEntry()} aria-label="Save cashflow entry">
                      <Save size={16} />
                    </button>
                    <button className="icon-button small" type="button" onClick={() => setDraft(null)} aria-label="Cancel cashflow edit">
                      <X size={16} />
                    </button>
                  </div>
                </div>
              </article>
            );
          }
          return (
            <article className="entry-row" key={`${row.kind}-${row.id}`}>
              <div className="entry-main">
                <strong>{row.label}</strong>
                <span>{formatMoney(row.amount, row.currency)} · {row.meta}</span>
              </div>
              <span className={`entry-kind ${row.kind}`}>{row.kind}</span>
              <div className="row-actions">
                <button className="icon-button small" type="button" onClick={() => beginEdit(row)} aria-label={`Edit ${row.label}`}>
                  <Pencil size={16} />
                </button>
                <button className="icon-button small danger" type="button" onClick={() => void deleteEntry(row.kind, row.id)} aria-label={`Delete ${row.label}`}>
                  <Trash2 size={16} />
                </button>
              </div>
            </article>
          );
        })}
      </div>
    </div>
  );
}

function QuickCashflowForms({ token, onChanged }: { token: string | null; onChanged: () => void }) {
  const [kind, setKind] = useState<"income" | "expense" | "debt">("income");
  const [amount, setAmount] = useState("");
  const [label, setLabel] = useState("");
  const [currency, setCurrency] = useState("USD");
  const [error, setError] = useState<string | null>(null);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    try {
      if (kind === "income") {
        await apiRequest("/api/incomes", token, {
          method: "POST",
          body: JSON.stringify({ amount, currency, frequency: "monthly", source: label || null })
        });
      } else if (kind === "expense") {
        await apiRequest("/api/expenses", token, {
          method: "POST",
          body: JSON.stringify({ amount, currency, frequency: "monthly", category: label || "expense" })
        });
      } else {
        await apiRequest("/api/debts", token, {
          method: "POST",
          body: JSON.stringify({
            type: "other",
            balance: amount,
            currency,
            min_monthly_payment: amount,
            creditor: label || null,
            status: "active"
          })
        });
      }
      setAmount("");
      setLabel("");
      void trackEvent(token, "cashflow_entry_created", { kind, currency });
      onChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save item");
    }
  }

  return (
    <form className="compact-form cashflow-form" onSubmit={submit}>
      <select aria-label="Cashflow entry type" value={kind} onChange={(event) => setKind(event.target.value as typeof kind)}>
        <option value="income">Income</option>
        <option value="expense">Expense</option>
        <option value="debt">Debt payment</option>
      </select>
      <input aria-label="Cashflow amount" placeholder="Amount" type="number" min="0" step="0.01" value={amount} onChange={(event) => setAmount(event.target.value)} required />
      <input aria-label="Cashflow label" placeholder="Label" value={label} onChange={(event) => setLabel(event.target.value)} />
      <select aria-label="Cashflow currency" value={currency} onChange={(event) => setCurrency(event.target.value)}>
        <option>USD</option>
        <option>EUR</option>
        <option>PLN</option>
        <option>GBP</option>
      </select>
      <button className="primary-button compact" type="submit"><Plus size={17} /> Add</button>
      {error && <div className="inline-error form-wide" role="alert">{error}</div>}
    </form>
  );
}

function SummaryLine({ icon, label, value, currency }: { icon: ReactNode; label: string; value?: string; currency?: string }) {
  return (
    <div className="summary-line">
      <span>{icon}{label}</span>
      <strong>{formatMoney(value, currency)}</strong>
    </div>
  );
}

function CurrencyPanel({
  token,
  rates,
  status,
  onChanged
}: {
  token: string | null;
  rates: ExchangeRate[];
  status: PanelStatus;
  onChanged: () => void;
}) {
  const [baseCurrency, setBaseCurrency] = useState("EUR");
  const [quoteCurrency, setQuoteCurrency] = useState("USD");
  const [rate, setRate] = useState("");
  const [rateDate, setRateDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [source, setSource] = useState("manual");
  const [error, setError] = useState<string | null>(null);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    try {
      await apiRequest("/api/exchange-rates", token, {
        method: "POST",
        body: JSON.stringify({
          base_currency: baseCurrency,
          quote_currency: quoteCurrency,
          rate,
          rate_date: rateDate,
          source: source || null
        })
      });
      setRate("");
      void trackEvent(token, "exchange_rate_saved", {
        base_currency: baseCurrency,
        quote_currency: quoteCurrency
      });
      onChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save exchange rate");
    }
  }

  return (
    <section id="currency" className="panel" aria-busy={status.loading}>
      <div className="panel-header">
        <div>
          <p className="eyebrow">Currency</p>
          <h2>Exchange rates</h2>
        </div>
        <Coins size={22} />
      </div>
      <PanelNotice status={status} loadingText="Loading exchange rates..." />
      <form className="compact-form currency-form" onSubmit={submit}>
        <select aria-label="Exchange rate base currency" value={baseCurrency} onChange={(event) => setBaseCurrency(event.target.value)}>
          <option>EUR</option>
          <option>USD</option>
          <option>PLN</option>
          <option>GBP</option>
        </select>
        <select aria-label="Exchange rate quote currency" value={quoteCurrency} onChange={(event) => setQuoteCurrency(event.target.value)}>
          <option>USD</option>
          <option>EUR</option>
          <option>PLN</option>
          <option>GBP</option>
        </select>
        <input aria-label="Exchange rate value" placeholder="Rate" type="number" min="0" step="0.0001" value={rate} onChange={(event) => setRate(event.target.value)} required />
        <input aria-label="Exchange rate date" type="date" value={rateDate} onChange={(event) => setRateDate(event.target.value)} required />
        <input aria-label="Exchange rate source" placeholder="Source" value={source} onChange={(event) => setSource(event.target.value)} />
        <button className="primary-button compact" type="submit"><Plus size={17} /> Save</button>
      </form>
      {error && <div className="inline-error" role="alert">{error}</div>}
      <div className="rate-list">
        {rates.length === 0 && <EmptyState text="Add a rate to use non-base-currency goals and cashflow." />}
        {rates.slice(0, 5).map((item) => (
          <article className="rate-row" key={item.id}>
            <strong>1 {item.base_currency} = {formatMoney(item.rate, item.quote_currency)}</strong>
            <span>{item.rate_date}{item.source ? ` · ${item.source}` : ""}</span>
          </article>
        ))}
      </div>
    </section>
  );
}

function ScenarioPanel({
  token,
  plan,
  summary,
  status
}: {
  token: string | null;
  plan: Plan | null;
  summary: FinancialSummary | null;
  status: PanelStatus;
}) {
  const [amount, setAmount] = useState("");
  const [oneTimeAmount, setOneTimeAmount] = useState("");
  const [oneTimeMonth, setOneTimeMonth] = useState("2");
  const [skipStartMonth, setSkipStartMonth] = useState("1");
  const [skipMonthCount, setSkipMonthCount] = useState("1");
  const [scenario, setScenario] = useState<ScenarioResponse | null>(null);
  const [presets, setPresets] = useState<ScenarioPresetsResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [scenarioLoading, setScenarioLoading] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setScenarioLoading(true);
    setError(null);
    try {
      const result = await apiRequest<ScenarioResponse>("/api/scenarios/monthly-amount", token, {
        method: "POST",
        body: JSON.stringify({
          scenario_name: "monthly_amount_change",
          monthly_available_amount: amount
        })
      });
      setScenario(result);
      setPresets(null);
      void trackEvent(token, "scenario_run", {
        scenario_name: result.scenario_name,
        monthly_available_amount: amount
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not run scenario");
    } finally {
      setScenarioLoading(false);
    }
  }

  async function submitOneTimeInflow(event: FormEvent) {
    event.preventDefault();
    setScenarioLoading(true);
    setError(null);
    try {
      const result = await apiRequest<ScenarioResponse>("/api/scenarios/one-time-inflow", token, {
        method: "POST",
        body: JSON.stringify({
          scenario_name: "one_time_inflow",
          amount: oneTimeAmount,
          month_index: Number(oneTimeMonth)
        })
      });
      setScenario(result);
      setPresets(null);
      void trackEvent(token, "scenario_run", {
        scenario_name: result.scenario_name,
        one_time_amount: oneTimeAmount,
        month_index: Number(oneTimeMonth)
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not run one-time inflow scenario");
    } finally {
      setScenarioLoading(false);
    }
  }

  async function submitSkippedMonths(event: FormEvent) {
    event.preventDefault();
    setScenarioLoading(true);
    setError(null);
    try {
      const result = await apiRequest<ScenarioResponse>("/api/scenarios/skipped-months", token, {
        method: "POST",
        body: JSON.stringify({
          scenario_name: "skipped_months",
          start_month: Number(skipStartMonth),
          month_count: Number(skipMonthCount)
        })
      });
      setScenario(result);
      setPresets(null);
      void trackEvent(token, "scenario_run", {
        scenario_name: result.scenario_name,
        start_month: Number(skipStartMonth),
        month_count: Number(skipMonthCount)
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not run skipped months scenario");
    } finally {
      setScenarioLoading(false);
    }
  }

  async function runPresets() {
    setScenarioLoading(true);
    setError(null);
    try {
      const result = await apiRequest<ScenarioPresetsResponse>("/api/scenarios/presets", token);
      setPresets(result);
      setScenario(null);
      void trackEvent(token, "scenario_run", {
        scenario_name: "scenario_presets",
        preset_count: result.presets.length
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not run scenario presets");
    } finally {
      setScenarioLoading(false);
    }
  }

  const baseFirst = scenario?.base.goals[0];
  const scenarioFirst = scenario?.scenario.goals[0];
  const scenarioCurrency = summary?.base_currency ?? plan?.goals[0]?.currency ?? "USD";

  return (
    <section id="scenario" className="panel" aria-busy={status.loading || scenarioLoading}>
      <div className="panel-header">
        <div>
          <p className="eyebrow">Scenario</p>
          <h2>What changes if...</h2>
        </div>
        <SlidersHorizontal size={22} />
      </div>
      <PanelNotice status={status} loadingText="Loading scenario inputs..." />
      <PanelNotice status={{ loading: scenarioLoading, error: null }} loadingText="Running scenario..." />
      <form className="scenario-form" onSubmit={submit}>
        <label>
          Monthly savings amount
          <input
            type="number"
            min="0"
            step="0.01"
            value={amount}
            placeholder={summary?.effective_monthly_available_amount ?? plan?.monthly_available_amount ?? "300"}
            onChange={(event) => setAmount(event.target.value)}
            required
          />
        </label>
        <button className="primary-button" type="submit" disabled={scenarioLoading}><SlidersHorizontal size={17} /> Run scenario</button>
      </form>
      <form className="scenario-form one-time-form" onSubmit={submitOneTimeInflow}>
        <label>
          One-time inflow
          <input
            type="number"
            min="0"
            step="0.01"
            value={oneTimeAmount}
            placeholder="500"
            onChange={(event) => setOneTimeAmount(event.target.value)}
            required
          />
        </label>
        <label>
          Month
          <input
            type="number"
            min="1"
            max="600"
            step="1"
            value={oneTimeMonth}
            onChange={(event) => setOneTimeMonth(event.target.value)}
            required
          />
        </label>
        <button className="primary-button" type="submit" disabled={scenarioLoading}><Plus size={17} /> Run inflow</button>
      </form>
      <form className="scenario-form skip-months-form" onSubmit={submitSkippedMonths}>
        <label>
          Skip from month
          <input
            type="number"
            min="1"
            max="600"
            step="1"
            value={skipStartMonth}
            onChange={(event) => setSkipStartMonth(event.target.value)}
            required
          />
        </label>
        <label>
          Months skipped
          <input
            type="number"
            min="1"
            max="60"
            step="1"
            value={skipMonthCount}
            onChange={(event) => setSkipMonthCount(event.target.value)}
            required
          />
        </label>
        <button className="primary-button" type="submit" disabled={scenarioLoading}><CalendarClock size={17} /> Run skip</button>
      </form>
      <div className="scenario-actions">
        <button className="secondary-button" type="button" onClick={() => void runPresets()} disabled={scenarioLoading}>
          <BarChart3 size={17} /> Run presets
        </button>
      </div>
      {error && <div className="inline-error" role="alert">{error}</div>}
      {!scenario && !presets && <EmptyState text="Run a scenario to compare projected dates." />}
      {scenario && (
        <div className="scenario-result">
          <div>
            <span>Base first goal</span>
            <strong>{baseFirst?.title ?? "No goal"}</strong>
            <small>{baseFirst?.expected_completion_date ?? "No date"}</small>
          </div>
          <div>
            <span>Scenario first goal</span>
            <strong>{scenarioFirst?.title ?? "No goal"}</strong>
            <small>{scenarioFirst?.expected_completion_date ?? "No date"}</small>
          </div>
        </div>
      )}
      {presets && (
        <div className="preset-scenarios-grid">
          {presets.presets.map((preset) => {
            const firstGoal = preset.plan.goals[0];
            return (
              <article className="preset-scenario-card" key={preset.name}>
                <div className="preset-card-header">
                  <div>
                    <strong>{preset.label}</strong>
                    <span>{preset.description}</span>
                  </div>
                  <small>{formatMoney(preset.monthly_available_amount, scenarioCurrency)}</small>
                </div>
                <div className="preset-card-metrics">
                  <div>
                    <span>First goal</span>
                    <strong>{firstGoal?.title ?? "No goal"}</strong>
                  </div>
                  <div>
                    <span>Date</span>
                    <strong>{firstGoal?.expected_completion_date ?? "No date"}</strong>
                  </div>
                </div>
                <div className="preset-assumptions">
                  {preset.assumptions.map((assumption) => (
                    <span key={assumption}>{assumption}</span>
                  ))}
                </div>
              </article>
            );
          })}
        </div>
      )}
    </section>
  );
}

function AllocationStrategyPanel({
  token,
  goals,
  strategy,
  status,
  onChanged
}: {
  token: string | null;
  goals: Goal[];
  strategy: AllocationStrategySettings | null;
  status: PanelStatus;
  onChanged: () => void;
}) {
  const [type, setType] = useState<AllocationStrategySettings["type"]>("strict_priority");
  const [weights, setWeights] = useState<Record<string, string>>({});
  const [fixedAmounts, setFixedAmounts] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setType(
      strategy?.type === "proportional" ||
      strategy?.type === "nearest_deadline" ||
      strategy?.type === "smallest_goal_first"
        ? strategy.type
        : "strict_priority"
    );
    setWeights(buildWeightDraft(goals, strategy?.weights ?? {}));
    setFixedAmounts(buildFixedAmountDraft(goals, strategy?.fixed_amounts ?? {}));
  }, [goals, strategy]);

  const totalWeight = goals.reduce((sum, goal) => sum + Number(weights[goal.id] || 0), 0);
  const totalFixedAmount = goals.reduce((sum, goal) => sum + Number(fixedAmounts[goal.id] || 0), 0);
  const isProportional = type === "proportional";
  const isCustom = type === "custom";
  const canSave = goals.length > 0 && (
    (isProportional && totalWeight > 0) ||
    (isCustom && totalFixedAmount > 0) ||
    (!isProportional && !isCustom)
  );

  async function saveStrategy(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const payloadWeights = isProportional
        ? Object.fromEntries(
            goals.map((goal) => [goal.id, normalizeWeight(weights[goal.id])])
          )
        : {};
      const payloadFixedAmounts = isCustom
        ? Object.fromEntries(
            goals.map((goal) => [goal.id, normalizeFixedAmount(fixedAmounts[goal.id])])
          )
        : {};
      await apiRequest<Plan>("/api/plan/strategy", token, {
        method: "POST",
        body: JSON.stringify({
          type,
          weights: payloadWeights,
          fixed_amounts: payloadFixedAmounts
        })
      });
      void trackEvent(token, "allocation_strategy_updated", {
        type,
        goals_count: goals.length,
        total_weight: isProportional ? totalWeight : null,
        total_fixed_amount: isCustom ? totalFixedAmount : null
      });
      onChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save allocation strategy");
    } finally {
      setLoading(false);
    }
  }

  function updateWeight(goalId: string, value: string) {
    setWeights((current) => ({ ...current, [goalId]: value }));
  }

  function updateFixedAmount(goalId: string, value: string) {
    setFixedAmounts((current) => ({ ...current, [goalId]: value }));
  }

  function setEqualWeights() {
    if (!goals.length) return;
    const equalWeight = String(Math.floor(100 / goals.length));
    const nextWeights = Object.fromEntries(goals.map((goal) => [goal.id, equalWeight]));
    const remainder = 100 - Number(equalWeight) * goals.length;
    if (remainder > 0) {
      nextWeights[goals[0].id] = String(Number(nextWeights[goals[0].id]) + remainder);
    }
    setWeights(nextWeights);
  }

  return (
    <section id="allocation" className="panel allocation-panel" aria-busy={status.loading || loading}>
      <div className="panel-header">
        <div>
          <p className="eyebrow">Allocation</p>
          <h2>Savings strategy</h2>
        </div>
        <BadgeDollarSign size={22} />
      </div>
      <PanelNotice status={status} loadingText="Loading allocation strategy..." />
      <PanelNotice status={{ loading, error: null }} loadingText="Saving allocation strategy..." />
      <form className="allocation-form" onSubmit={saveStrategy}>
        <div className="segmented allocation-segmented" aria-label="Allocation strategy">
          <button
            type="button"
            className={type === "strict_priority" ? "active" : ""}
            aria-pressed={type === "strict_priority"}
            onClick={() => setType("strict_priority")}
          >
            Strict
          </button>
          <button
            type="button"
            className={type === "proportional" ? "active" : ""}
            aria-pressed={type === "proportional"}
            onClick={() => setType("proportional")}
          >
            Percent
          </button>
          <button
            type="button"
            className={type === "nearest_deadline" ? "active" : ""}
            aria-pressed={type === "nearest_deadline"}
            onClick={() => setType("nearest_deadline")}
          >
            Deadline
          </button>
          <button
            type="button"
            className={type === "smallest_goal_first" ? "active" : ""}
            aria-pressed={type === "smallest_goal_first"}
            onClick={() => setType("smallest_goal_first")}
          >
            Smallest
          </button>
          <button
            type="button"
            className={type === "custom" ? "active" : ""}
            aria-pressed={type === "custom"}
            onClick={() => setType("custom")}
          >
            Fixed
          </button>
        </div>
        {isProportional && (
          <div className="weight-editor">
            <div className="weight-header">
              <span>Total: {Number.isFinite(totalWeight) ? totalWeight : 0}%</span>
              <button className="ghost-button compact" type="button" onClick={setEqualWeights} disabled={!goals.length}>
                Equal split
              </button>
            </div>
            {totalWeight > 0 && totalWeight !== 100 && (
              <div className="weight-note">Weights will be normalized during calculation.</div>
            )}
            {goals.length === 0 && <EmptyState text="Add goals before setting allocation weights." />}
            {goals.map((goal) => (
              <label className="weight-row" key={goal.id}>
                <span>{goal.title}</span>
                <input
                  aria-label={`${goal.title} allocation percent`}
                  type="number"
                  min="0"
                  max="100"
                  step="1"
                  value={weights[goal.id] ?? ""}
                  onChange={(event) => updateWeight(goal.id, event.target.value)}
                />
              </label>
            ))}
          </div>
        )}
        {isCustom && (
          <div className="weight-editor">
            <div className="weight-header">
              <span>Total fixed: {Number.isFinite(totalFixedAmount) ? totalFixedAmount : 0}</span>
            </div>
            {goals.length === 0 && <EmptyState text="Add goals before setting fixed monthly amounts." />}
            {goals.map((goal) => (
              <label className="weight-row" key={goal.id}>
                <span>{goal.title}</span>
                <input
                  aria-label={`${goal.title} fixed monthly amount`}
                  type="number"
                  min="0"
                  step="0.01"
                  value={fixedAmounts[goal.id] ?? ""}
                  onChange={(event) => updateFixedAmount(goal.id, event.target.value)}
                />
              </label>
            ))}
          </div>
        )}
        {error && <div className="inline-error" role="alert">{error}</div>}
        <button className="primary-button compact" type="submit" disabled={loading || !canSave}>
          <Save size={17} /> Save strategy
        </button>
      </form>
    </section>
  );
}

function buildWeightDraft(goals: Goal[], savedWeights: Record<string, string>): Record<string, string> {
  if (!goals.length) return {};
  if (Object.keys(savedWeights).length > 0) {
    return Object.fromEntries(goals.map((goal) => [goal.id, savedWeights[goal.id] ?? "0"]));
  }

  const equalWeight = String(Math.floor(100 / goals.length));
  const weights = Object.fromEntries(goals.map((goal) => [goal.id, equalWeight]));
  const remainder = 100 - Number(equalWeight) * goals.length;
  if (remainder > 0) {
    weights[goals[0].id] = String(Number(weights[goals[0].id]) + remainder);
  }
  return weights;
}

function buildFixedAmountDraft(goals: Goal[], savedFixedAmounts: Record<string, string>): Record<string, string> {
  if (!goals.length) return {};
  return Object.fromEntries(goals.map((goal) => [goal.id, savedFixedAmounts[goal.id] ?? "0"]));
}

function normalizeWeight(value: string | undefined): string {
  const amount = Number(value ?? 0);
  return String(Number.isFinite(amount) && amount > 0 ? amount : 0);
}

function normalizeFixedAmount(value: string | undefined): string {
  const amount = Number(value ?? 0);
  return String(Number.isFinite(amount) && amount > 0 ? amount : 0);
}

function PriceHistoryPanel({
  token,
  goals,
  status,
  onChanged
}: {
  token: string | null;
  goals: Goal[];
  status: PanelStatus;
  onChanged: () => void;
}) {
  const [selectedGoalId, setSelectedGoalId] = useState("");
  const [newAmount, setNewAmount] = useState("");
  const [currency, setCurrency] = useState("USD");
  const [source, setSource] = useState("manual");
  const [note, setNote] = useState("");
  const [history, setHistory] = useState<GoalPriceHistory[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!goals.length) {
      setSelectedGoalId("");
      setHistory([]);
      return;
    }
    if (!selectedGoalId || !goals.some((goal) => goal.id === selectedGoalId)) {
      setSelectedGoalId(goals[0].id);
    }
  }, [goals, selectedGoalId]);

  useEffect(() => {
    const selectedGoal = goals.find((goal) => goal.id === selectedGoalId);
    if (!selectedGoal) return;
    setCurrency(selectedGoal.currency);
    if (!newAmount) {
      setNewAmount(selectedGoal.target_amount);
    }
    if (token) {
      void loadHistory(selectedGoal.id);
    }
  }, [selectedGoalId, token]);

  async function loadHistory(goalId: string) {
    setHistoryLoading(true);
    setError(null);
    try {
      const result = await apiRequest<GoalPriceHistory[]>(`/api/goals/${goalId}/price-history`, token);
      setHistory(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load price history");
    } finally {
      setHistoryLoading(false);
    }
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!selectedGoalId) return;
    setError(null);
    try {
      await apiRequest<GoalPriceHistory>(`/api/goals/${selectedGoalId}/price-history`, token, {
        method: "POST",
        body: JSON.stringify({
          new_amount: newAmount,
          currency,
          source: source || null,
          note: note || null,
          changed_at: new Date().toISOString().slice(0, 10)
        })
      });
      setNote("");
      void trackEvent(token, "goal_price_updated", { currency });
      await loadHistory(selectedGoalId);
      onChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not update price");
    }
  }

  return (
    <section id="prices" className="panel" aria-busy={status.loading || historyLoading}>
      <div className="panel-header">
        <div>
          <p className="eyebrow">Prices</p>
          <h2>Goal price history</h2>
        </div>
        <ReceiptText size={22} />
      </div>
      <PanelNotice status={status} loadingText="Loading goals for price history..." />
      <PanelNotice status={{ loading: historyLoading, error: null }} loadingText="Loading price history..." />
      <form className="compact-form price-form" onSubmit={submit}>
        <select aria-label="Price history goal" value={selectedGoalId} onChange={(event) => setSelectedGoalId(event.target.value)} disabled={!goals.length}>
          {goals.map((goal) => (
            <option key={goal.id} value={goal.id}>{goal.title}</option>
          ))}
        </select>
        <input
          aria-label="New goal price"
          placeholder="New price"
          type="number"
          min="0"
          step="0.01"
          value={newAmount}
          onChange={(event) => setNewAmount(event.target.value)}
          required
          disabled={!goals.length}
        />
        <select aria-label="Price currency" value={currency} onChange={(event) => setCurrency(event.target.value)} disabled={!goals.length}>
          <option>USD</option>
          <option>EUR</option>
          <option>PLN</option>
          <option>GBP</option>
        </select>
        <input aria-label="Price source" placeholder="Source" value={source} onChange={(event) => setSource(event.target.value)} disabled={!goals.length} />
        <input aria-label="Price note" placeholder="Note" value={note} onChange={(event) => setNote(event.target.value)} disabled={!goals.length} />
        <button className="primary-button compact" type="submit" disabled={!goals.length}><Save size={17} /> Save</button>
      </form>
      {error && <div className="inline-error" role="alert">{error}</div>}
      <div className="price-list">
        {goals.length === 0 && <EmptyState text="Create a goal before tracking price changes." />}
        {goals.length > 0 && history.length === 0 && <EmptyState text="No price changes recorded for this goal." />}
        {history.map((item) => (
          <article className="price-row" key={item.id}>
            <div>
              <strong>{formatMoney(item.previous_amount, item.currency)} → {formatMoney(item.new_amount, item.currency)}</strong>
              <span>{item.changed_at}{item.source ? ` · ${item.source}` : ""}{item.note ? ` · ${item.note}` : ""}</span>
            </div>
            <span className={Number(item.new_amount) <= Number(item.previous_amount) ? "severity-pill success" : "severity-pill warning"}>
              {Number(item.new_amount) <= Number(item.previous_amount) ? "lower" : "higher"}
            </span>
          </article>
        ))}
      </div>
    </section>
  );
}

function RecurringRulesPanel({
  token,
  goals,
  rules,
  status,
  onChanged
}: {
  token: string | null;
  goals: Goal[];
  rules: RecurringRule[];
  status: PanelStatus;
  onChanged: () => void;
}) {
  const [goalId, setGoalId] = useState("");
  const [title, setTitle] = useState("");
  const [amount, setAmount] = useState("");
  const [currency, setCurrency] = useState("USD");
  const [frequency, setFrequency] = useState("monthly");
  const [dayOfMonth, setDayOfMonth] = useState("");
  const [nextRunOn, setNextRunOn] = useState(() => new Date().toISOString().slice(0, 10));
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!goalId && goals.length) {
      setGoalId(goals[0].id);
      setCurrency(goals[0].currency);
    }
  }, [goalId, goals]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!goalId) return;
    setError(null);
    try {
      await apiRequest<RecurringRule>("/api/recurring-rules", token, {
        method: "POST",
        body: JSON.stringify({
          goal_id: goalId,
          title,
          amount,
          currency,
          frequency,
          day_of_month: dayOfMonth ? Number(dayOfMonth) : null,
          source: title || null,
          next_run_on: nextRunOn || null
        })
      });
      setTitle("");
      setAmount("");
      setDayOfMonth("");
      void trackEvent(token, "recurring_rule_created", { frequency, currency });
      onChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save recurring rule");
    }
  }

  async function applyRule(ruleId: string) {
    setError(null);
    try {
      await apiRequest<Contribution>(`/api/recurring-rules/${ruleId}/apply`, token, { method: "POST" });
      void trackEvent(token, "recurring_rule_applied");
      onChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not apply recurring rule");
    }
  }

  async function toggleRule(rule: RecurringRule) {
    setError(null);
    try {
      await apiRequest<RecurringRule>(`/api/recurring-rules/${rule.id}`, token, {
        method: "PATCH",
        body: JSON.stringify({ is_active: !rule.is_active })
      });
      void trackEvent(token, "recurring_rule_toggled", { active: !rule.is_active });
      onChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not update recurring rule");
    }
  }

  async function deleteRule(ruleId: string) {
    setError(null);
    try {
      await apiRequest<void>(`/api/recurring-rules/${ruleId}`, token, { method: "DELETE" });
      void trackEvent(token, "recurring_rule_deleted");
      onChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not delete recurring rule");
    }
  }

  const goalName = (id: string) => goals.find((goal) => goal.id === id)?.title ?? "Goal";

  return (
    <section id="rules" className="panel" aria-busy={status.loading}>
      <div className="panel-header">
        <div>
          <p className="eyebrow">Rules</p>
          <h2>Recurring savings</h2>
        </div>
        <Repeat size={22} />
      </div>
      <PanelNotice status={status} loadingText="Loading recurring rules..." />
      <form className="compact-form rules-form" onSubmit={submit}>
        <select aria-label="Recurring rule goal" value={goalId} onChange={(event) => setGoalId(event.target.value)} disabled={!goals.length}>
          {goals.map((goal) => (
            <option key={goal.id} value={goal.id}>{goal.title}</option>
          ))}
        </select>
        <input aria-label="Recurring rule name" placeholder="Rule name" value={title} onChange={(event) => setTitle(event.target.value)} required disabled={!goals.length} />
        <input aria-label="Recurring rule amount" placeholder="Amount" type="number" min="0" step="0.01" value={amount} onChange={(event) => setAmount(event.target.value)} required disabled={!goals.length} />
        <select aria-label="Recurring rule currency" value={currency} onChange={(event) => setCurrency(event.target.value)} disabled={!goals.length}>
          <option>USD</option>
          <option>EUR</option>
          <option>PLN</option>
          <option>GBP</option>
        </select>
        <select aria-label="Recurring rule frequency" value={frequency} onChange={(event) => setFrequency(event.target.value)} disabled={!goals.length}>
          <option value="weekly">Weekly</option>
          <option value="biweekly">Biweekly</option>
          <option value="monthly">Monthly</option>
          <option value="annual">Annual</option>
        </select>
        <input aria-label="Recurring rule day of month" placeholder="Day" type="number" min="1" max="31" value={dayOfMonth} onChange={(event) => setDayOfMonth(event.target.value)} disabled={!goals.length} />
        <input aria-label="Recurring rule next run date" type="date" value={nextRunOn} onChange={(event) => setNextRunOn(event.target.value)} disabled={!goals.length} />
        <button className="primary-button compact" type="submit" disabled={!goals.length}><Plus size={17} /> Add</button>
      </form>
      {error && <div className="inline-error" role="alert">{error}</div>}
      <div className="rule-list">
        {rules.length === 0 && <EmptyState text="Create a rule to repeat planned contributions." />}
        {rules.map((rule) => (
          <article className="rule-row" key={rule.id}>
            <div className="rule-main">
              <strong>{rule.title}</strong>
              <span>
                {formatMoney(rule.amount, rule.currency)} · {rule.frequency} · {goalName(rule.goal_id)}
                {rule.next_run_on ? ` · next ${rule.next_run_on}` : ""}
              </span>
            </div>
            <span className={rule.is_active ? "status-pill active" : "status-pill archived"}>
              {rule.is_active ? "active" : "paused"}
            </span>
            <div className="row-actions">
              <button className="icon-button small" type="button" onClick={() => void applyRule(rule.id)} disabled={!rule.is_active} aria-label={`Apply ${rule.title}`}>
                <Play size={16} />
              </button>
              <button className="icon-button small" type="button" onClick={() => void toggleRule(rule)} aria-label={`Toggle ${rule.title}`}>
                {rule.is_active ? <Pause size={16} /> : <Play size={16} />}
              </button>
              <button className="icon-button small danger" type="button" onClick={() => void deleteRule(rule.id)} aria-label={`Delete ${rule.title}`}>
                <Trash2 size={16} />
              </button>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

type BooleanNotificationSetting =
  | "in_app_enabled"
  | "email_enabled"
  | "plan_warnings"
  | "milestone_updates"
  | "monthly_reminders";

type FrequencyNotificationSetting = "in_app_frequency" | "email_frequency";

function NotificationPanel({
  token,
  notifications,
  settings,
  status,
  onChanged
}: {
  token: string | null;
  notifications: Notification[];
  settings: NotificationSettings | null;
  status: PanelStatus;
  onChanged: () => void;
}) {
  const [error, setError] = useState<string | null>(null);

  async function markRead(notificationId: string) {
    setError(null);
    try {
      await apiRequest<Notification>(`/api/notifications/${notificationId}/read`, token, { method: "POST" });
      void trackEvent(token, "notification_marked_read");
      onChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not update notification");
    }
  }

  async function dismiss(notificationId: string) {
    setError(null);
    try {
      await apiRequest<Notification>(`/api/notifications/${notificationId}/dismiss`, token, { method: "POST" });
      void trackEvent(token, "notification_dismissed");
      onChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not dismiss notification");
    }
  }

  async function toggleSetting(key: BooleanNotificationSetting) {
    if (!settings) return;
    setError(null);
    try {
      await apiRequest<NotificationSettings>("/api/notification-settings", token, {
        method: "PATCH",
        body: JSON.stringify({ [key]: !settings[key] })
      });
      void trackEvent(token, "notification_settings_updated", { key });
      onChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not update notification settings");
    }
  }

  async function updateFrequency(key: FrequencyNotificationSetting, value: NotificationFrequency) {
    setError(null);
    try {
      await apiRequest<NotificationSettings>("/api/notification-settings", token, {
        method: "PATCH",
        body: JSON.stringify({ [key]: value })
      });
      void trackEvent(token, "notification_frequency_updated", { key, value });
      onChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not update notification frequency");
    }
  }

  return (
    <section id="notifications" className="panel" aria-busy={status.loading}>
      <div className="panel-header">
        <div>
          <p className="eyebrow">Alerts</p>
          <h2>Plan notifications</h2>
        </div>
        <BellRing size={22} />
      </div>
      <PanelNotice status={status} loadingText="Loading notifications and settings..." />
      {error && <div className="inline-error" role="alert">{error}</div>}
      <div className="notification-list">
        {notifications.length === 0 && <EmptyState text="No unread alerts right now." />}
        {notifications.map((item) => (
          <article className={`notification-row ${item.severity}`} key={item.id}>
            <div className="notification-main">
              <strong>{item.title}</strong>
              <span>{item.body}</span>
            </div>
            <span className={`severity-pill ${item.severity}`}>{item.severity}</span>
            <div className="row-actions">
              <button className="icon-button small" type="button" onClick={() => void markRead(item.id)} aria-label={`Mark ${item.title} read`}>
                <Check size={16} />
              </button>
              <button className="icon-button small" type="button" onClick={() => void dismiss(item.id)} aria-label={`Dismiss ${item.title}`}>
                <X size={16} />
              </button>
            </div>
          </article>
        ))}
      </div>
      <div className="subsection">
        <div className="subsection-header">
          <h3>Settings</h3>
          <Bell size={18} />
        </div>
        <div className="settings-grid">
          {settings && (
            <>
              <ToggleRow label="In-app alerts" checked={settings.in_app_enabled} onToggle={() => void toggleSetting("in_app_enabled")} />
              <FrequencyRow
                label="In-app frequency"
                value={settings.in_app_frequency}
                disabled={!settings.in_app_enabled}
                onChange={(value) => void updateFrequency("in_app_frequency", value)}
              />
              <ToggleRow label="Email alerts" checked={settings.email_enabled} onToggle={() => void toggleSetting("email_enabled")} />
              <FrequencyRow
                label="Email frequency"
                value={settings.email_frequency}
                disabled={!settings.email_enabled}
                onChange={(value) => void updateFrequency("email_frequency", value)}
              />
              <ToggleRow label="Plan warnings" checked={settings.plan_warnings} onToggle={() => void toggleSetting("plan_warnings")} />
              <ToggleRow label="Milestones" checked={settings.milestone_updates} onToggle={() => void toggleSetting("milestone_updates")} />
              <ToggleRow label="Monthly reminders" checked={settings.monthly_reminders} onToggle={() => void toggleSetting("monthly_reminders")} />
            </>
          )}
        </div>
      </div>
    </section>
  );
}

function CsvPanel({
  token,
  status,
  onChanged
}: {
  token: string | null;
  status: PanelStatus;
  onChanged: () => void;
}) {
  const [goalCsvText, setGoalCsvText] = useState("");
  const [contributionCsvText, setContributionCsvText] = useState("");
  const [goalFileName, setGoalFileName] = useState("");
  const [contributionFileName, setContributionFileName] = useState("");
  const [contributionExportFrom, setContributionExportFrom] = useState("");
  const [contributionExportTo, setContributionExportTo] = useState("");
  const [goalResult, setGoalResult] = useState<CsvGoalImportResponse | null>(null);
  const [contributionResult, setContributionResult] = useState<CsvContributionImportResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function downloadCsv(path: string, filename: string, eventName: string) {
    if (!token) return;
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE_URL}${path}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (!response.ok) {
        throw new Error(response.statusText || "CSV export failed");
      }
      const text = await response.text();
      const blob = new Blob([text], { type: "text/csv;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = filename;
      link.click();
      URL.revokeObjectURL(url);
      void trackEvent(token, eventName);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not download CSV");
    } finally {
      setLoading(false);
    }
  }

  async function exportContributionsPeriod() {
    if (contributionExportFrom && contributionExportTo && contributionExportFrom > contributionExportTo) {
      setError("From date must be earlier than or equal to to date");
      return;
    }

    const params = new URLSearchParams();
    if (contributionExportFrom) {
      params.set("from_date", contributionExportFrom);
    }
    if (contributionExportTo) {
      params.set("to_date", contributionExportTo);
    }
    const query = params.toString();
    const periodSuffix = [contributionExportFrom || "start", contributionExportTo || "today"].join("_");
    await downloadCsv(
      `/api/export/contributions.csv${query ? `?${query}` : ""}`,
      `money-saver-contributions-${periodSuffix}.csv`,
      "csv_contributions_period_exported"
    );
  }

  async function selectCsvFile(kind: "goals" | "contributions", event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    setError(null);
    if (kind === "goals") {
      setGoalResult(null);
    } else {
      setContributionResult(null);
    }
    if (!file) {
      if (kind === "goals") {
        setGoalCsvText("");
        setGoalFileName("");
      } else {
        setContributionCsvText("");
        setContributionFileName("");
      }
      return;
    }
    const text = await file.text();
    if (kind === "goals") {
      setGoalFileName(file.name);
      setGoalCsvText(text);
    } else {
      setContributionFileName(file.name);
      setContributionCsvText(text);
    }
  }

  async function importGoals() {
    if (!goalCsvText.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const response = await apiRequest<CsvGoalImportResponse>("/api/import/goals.csv", token, {
        method: "POST",
        body: JSON.stringify({ csv_text: goalCsvText })
      });
      setGoalResult(response);
      void trackEvent(token, "csv_goals_imported", {
        created_count: response.created_count,
        skipped_count: response.skipped_count,
        errors_count: response.errors.length
      });
      onChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not import CSV");
    } finally {
      setLoading(false);
    }
  }

  async function importContributions() {
    if (!contributionCsvText.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const response = await apiRequest<CsvContributionImportResponse>("/api/import/contributions.csv", token, {
        method: "POST",
        body: JSON.stringify({ csv_text: contributionCsvText })
      });
      setContributionResult(response);
      void trackEvent(token, "csv_contributions_imported", {
        created_count: response.created_count,
        skipped_count: response.skipped_count,
        errors_count: response.errors.length
      });
      onChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not import contributions CSV");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section id="data" className="panel csv-panel" aria-busy={status.loading || loading}>
      <div className="panel-header">
        <div>
          <p className="eyebrow">Data</p>
          <h2>CSV files</h2>
        </div>
        <Download size={22} />
      </div>
      <PanelNotice status={status} loadingText="Preparing data tools..." />
      <PanelNotice status={{ loading, error: null }} loadingText="Processing CSV operation..." />
      <div className="csv-actions">
        <button
          className="icon-button wide"
          type="button"
          disabled={loading}
          onClick={() => void downloadCsv("/api/export/goals.csv", "money-saver-goals.csv", "csv_goals_exported")}
        >
          <Download size={17} /> Goals
        </button>
        <button
          className="icon-button wide"
          type="button"
          disabled={loading}
          onClick={() => void downloadCsv("/api/export/contributions.csv", "money-saver-contributions.csv", "csv_contributions_exported")}
        >
          <Download size={17} /> Contributions
        </button>
        <button
          className="icon-button wide"
          type="button"
          disabled={loading}
          onClick={() => void downloadCsv("/api/import/goals-template.csv", "money-saver-goals-import-template.csv", "csv_goals_template_downloaded")}
        >
          <Download size={17} /> Goal template
        </button>
        <button
          className="icon-button wide"
          type="button"
          disabled={loading}
          onClick={() =>
            void downloadCsv(
              "/api/import/contributions-template.csv",
              "money-saver-contributions-import-template.csv",
              "csv_contributions_template_downloaded"
            )
          }
        >
          <Download size={17} /> Contribution template
        </button>
      </div>
      <div className="subsection">
        <div className="subsection-header">
          <h3>Export contributions period</h3>
          <CalendarClock size={18} />
        </div>
        <div className="csv-period-row">
          <input
            type="date"
            aria-label="Contribution export from date"
            value={contributionExportFrom}
            onChange={(event) => setContributionExportFrom(event.target.value)}
          />
          <input
            type="date"
            aria-label="Contribution export to date"
            value={contributionExportTo}
            onChange={(event) => setContributionExportTo(event.target.value)}
          />
          <button
            className="primary-button compact"
            type="button"
            disabled={loading || (!contributionExportFrom && !contributionExportTo)}
            onClick={() => void exportContributionsPeriod()}
          >
            <Download size={17} /> Export period
          </button>
        </div>
      </div>
      <div className="subsection">
        <div className="subsection-header">
          <h3>Import goals</h3>
          <Upload size={18} />
        </div>
        <div className="csv-import-row">
          <input aria-label="Goals CSV file" type="file" accept=".csv,text/csv" onChange={(event) => void selectCsvFile("goals", event)} />
          <button className="primary-button compact" type="button" disabled={loading || !goalCsvText.trim()} onClick={() => void importGoals()}>
            <Upload size={17} /> Import
          </button>
        </div>
      </div>
      {goalFileName && <div className="csv-file-name">{goalFileName}</div>}
      {error && <div className="inline-error" role="alert">{error}</div>}
      {goalResult && (
        <div className="csv-result">
          <div className="inline-success">
            Created {goalResult.created_count} · Skipped {goalResult.skipped_count}
          </div>
          {goalResult.created_goals.length > 0 && (
            <div className="csv-result-list">
              {goalResult.created_goals.slice(0, 4).map((goal) => (
                <span key={goal.id}>{goal.title}</span>
              ))}
            </div>
          )}
          {goalResult.errors.length > 0 && (
            <CsvImportErrorList details={goalResult.error_details ?? []} fallbackErrors={goalResult.errors} />
          )}
        </div>
      )}
      <div className="subsection">
        <div className="subsection-header">
          <h3>Import contributions</h3>
          <Upload size={18} />
        </div>
        <div className="csv-import-row">
          <input aria-label="Contributions CSV file" type="file" accept=".csv,text/csv" onChange={(event) => void selectCsvFile("contributions", event)} />
          <button className="primary-button compact" type="button" disabled={loading || !contributionCsvText.trim()} onClick={() => void importContributions()}>
            <Upload size={17} /> Import
          </button>
        </div>
      </div>
      {contributionFileName && <div className="csv-file-name">{contributionFileName}</div>}
      {contributionResult && (
        <div className="csv-result">
          <div className="inline-success">
            Created {contributionResult.created_count} · Skipped {contributionResult.skipped_count}
          </div>
          {contributionResult.created_contributions.length > 0 && (
            <div className="csv-result-list">
              {contributionResult.created_contributions.slice(0, 4).map((item) => (
                <span key={item.id}>{item.type} · {formatMoney(item.amount, item.currency)} · {item.occurred_at}</span>
              ))}
            </div>
          )}
          {contributionResult.errors.length > 0 && (
            <CsvImportErrorList
              details={contributionResult.error_details ?? []}
              fallbackErrors={contributionResult.errors}
            />
          )}
        </div>
      )}
    </section>
  );
}

function CsvImportErrorList({
  details,
  fallbackErrors
}: {
  details: CsvImportErrorDetail[];
  fallbackErrors: string[];
}) {
  const visibleDetails = details.slice(0, 5);
  if (visibleDetails.length > 0) {
    return (
      <div className="csv-error-list">
        {visibleDetails.map((detail, index) => (
          <span key={`${detail.row_number ?? "csv"}-${detail.field ?? "row"}-${index}`}>
            {formatCsvImportError(detail)}
          </span>
        ))}
      </div>
    );
  }

  return (
    <div className="csv-error-list">
      {fallbackErrors.slice(0, 5).map((item) => (
        <span key={item}>{item}</span>
      ))}
    </div>
  );
}

function formatCsvImportError(detail: CsvImportErrorDetail) {
  const parts = [detail.row_number == null ? "CSV" : `Row ${detail.row_number}`];
  if (detail.field) {
    parts.push(`Field ${detail.field}`);
  }
  if (detail.value != null) {
    parts.push(`Value ${JSON.stringify(detail.value)}`);
  }
  return `${parts.join(" · ")}: ${detail.message}`;
}

function ToggleRow({ label, checked, onToggle }: { label: string; checked: boolean; onToggle: () => void }) {
  return (
    <label className="toggle-row">
      <span>{label}</span>
      <input type="checkbox" checked={checked} onChange={onToggle} />
    </label>
  );
}

function FrequencyRow({
  label,
  value,
  disabled,
  onChange
}: {
  label: string;
  value: NotificationFrequency;
  disabled: boolean;
  onChange: (value: NotificationFrequency) => void;
}) {
  return (
    <label className="frequency-row">
      <span>{label}</span>
      <select
        value={value}
        disabled={disabled}
        onChange={(event) => onChange(event.target.value as NotificationFrequency)}
      >
        <option value="instant">Instant</option>
        <option value="daily">Daily</option>
        <option value="weekly">Weekly</option>
        <option value="monthly">Monthly</option>
      </select>
    </label>
  );
}

function ReportsPanel({
  token,
  initialReport,
  status
}: {
  token: string | null;
  initialReport: MonthlyReport | null;
  status: PanelStatus;
}) {
  const currentDate = new Date();
  const [year, setYear] = useState(String(currentDate.getFullYear()));
  const [month, setMonth] = useState(String(currentDate.getMonth() + 1));
  const [report, setReport] = useState<MonthlyReport | null>(initialReport);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (initialReport) {
      setReport(initialReport);
    }
  }, [initialReport]);

  async function loadReport(event?: FormEvent) {
    event?.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const result = await apiRequest<MonthlyReport>(`/api/reports/monthly?year=${year}&month=${month}`, token);
      setReport(result);
      void trackEvent(token, "monthly_report_viewed", { year, month });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load monthly report");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section id="reports" className="panel report-panel" aria-busy={status.loading || loading}>
      <div className="panel-header">
        <div>
          <p className="eyebrow">Reports</p>
          <h2>Monthly progress</h2>
        </div>
        <BarChart3 size={22} />
      </div>
      <PanelNotice status={status} loadingText="Loading monthly report..." />
      <PanelNotice status={{ loading, error: null }} loadingText="Loading selected report..." />
      <form className="report-controls" onSubmit={loadReport}>
        <input
          aria-label="Report year"
          type="number"
          min="2000"
          max="2100"
          value={year}
          onChange={(event) => setYear(event.target.value)}
        />
        <select aria-label="Report month" value={month} onChange={(event) => setMonth(event.target.value)}>
          {Array.from({ length: 12 }, (_, index) => (
            <option key={index + 1} value={String(index + 1)}>{index + 1}</option>
          ))}
        </select>
        <button className="primary-button compact" type="submit" disabled={loading}>
          <BarChart3 size={17} /> Load
        </button>
      </form>
      {error && <div className="inline-error" role="alert">{error}</div>}
      {!report && <EmptyState text="Load a month to see contribution progress." />}
      {report && (
        <>
          <div className="report-summary">
            <div>
              <span>Net saved</span>
              <strong>{formatMoney(report.net_saved, report.base_currency)}</strong>
            </div>
            <div>
              <span>Added</span>
              <strong>{formatMoney(report.total_added, report.base_currency)}</strong>
            </div>
            <div>
              <span>Removed</span>
              <strong>{formatMoney(report.total_removed, report.base_currency)}</strong>
            </div>
            <div>
              <span>Safe capacity</span>
              <strong>{formatMoney(report.safe_monthly_capacity, report.base_currency)}</strong>
            </div>
          </div>
          <div className="report-grid">
            <div className="report-block">
              <h3>Goals</h3>
              <div className="report-goal-list">
                {report.goal_reports.length === 0 && <EmptyState text="No goal contributions in this month." />}
                {report.goal_reports.map((goal) => {
                  const progress = Math.min(100, Number(goal.progress_percent) || 0);
                  return (
                    <article className="report-goal-row" key={goal.goal_id}>
                      <div>
                        <strong>{goal.title}</strong>
                        <span>{formatMoney(goal.net_amount, goal.currency)} net · {goal.contributions_count} entries</span>
                      </div>
                      <div className="progress-track">
                        <div
                          role="progressbar"
                          aria-label={`${goal.title} monthly progress`}
                          aria-valuemin={0}
                          aria-valuemax={100}
                          aria-valuenow={Math.round(progress)}
                          style={{ width: `${progress}%` }}
                        />
                      </div>
                      <span className={`status-pill ${goal.status}`}>{goal.status}</span>
                    </article>
                  );
                })}
              </div>
            </div>
            <div className="report-block">
              <h3>Recommendations</h3>
              <div className="recommendation-list">
                {[...report.plan_conflicts, ...report.warnings, ...report.plan_recommendations].slice(0, 8).map((item) => (
                  <div className="recommendation-row" key={item}>
                    <AlertTriangle size={16} />
                    <span>{item}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </>
      )}
    </section>
  );
}

function AnalyticsPanel({ summary, status }: { summary: AnalyticsSummary | null; status: PanelStatus }) {
  const keyMetrics: Array<[string, number]> = [
    ["Goals created", summary?.key_metrics.goals_created ?? 0],
    ["Contributions", summary?.key_metrics.contributions_added ?? 0],
    ["Scenarios", summary?.key_metrics.scenarios_run ?? 0],
    ["Priority changes", summary?.key_metrics.priority_changes ?? 0],
    ["CSV imports", summary?.key_metrics.csv_imports ?? 0],
    ["Exports", summary?.key_metrics.exports ?? 0]
  ];

  return (
    <section id="analytics" className="panel analytics-panel" aria-busy={status.loading}>
      <div className="panel-header">
        <div>
          <p className="eyebrow">Analytics</p>
          <h2>MVP activity</h2>
        </div>
        <Activity size={22} />
      </div>
      <PanelNotice status={status} loadingText="Loading activity analytics..." />
      {!summary && <EmptyState text="Analytics will appear after product events are recorded." />}
      {summary && (
        <>
          <div className="report-summary analytics-summary">
            <div>
              <span>Total events</span>
              <strong>{summary.total_events}</strong>
            </div>
            <div>
              <span>Last 7 days</span>
              <strong>{summary.events_last_7_days}</strong>
            </div>
            <div>
              <span>Last 30 days</span>
              <strong>{summary.events_last_30_days}</strong>
            </div>
            <div>
              <span>Active days</span>
              <strong>{summary.active_days_last_30}</strong>
            </div>
          </div>
          <div className="analytics-grid">
            <div className="report-block">
              <h3>Key actions</h3>
              <div className="analytics-list">
                {keyMetrics.map(([label, value]) => (
                  <div className="analytics-row" key={label}>
                    <span>{label}</span>
                    <strong>{value}</strong>
                  </div>
                ))}
              </div>
            </div>
            <div className="report-block">
              <h3>Top events</h3>
              <div className="analytics-list">
                {summary.event_counts.length === 0 && <EmptyState text="No events recorded yet." />}
                {summary.event_counts.slice(0, 6).map((item) => (
                  <div className="analytics-row" key={item.name}>
                    <span>{formatEventName(item.name)}</span>
                    <strong>{item.count}</strong>
                  </div>
                ))}
              </div>
            </div>
            <div className="report-block">
              <h3>Recent events</h3>
              <div className="analytics-list">
                {summary.recent_events.length === 0 && <EmptyState text="No recent product events." />}
                {summary.recent_events.slice(0, 6).map((event) => (
                  <div className="analytics-row event-row" key={event.id}>
                    <span>{formatEventName(event.name)}</span>
                    <strong>{formatDateTime(event.created_at)}</strong>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </>
      )}
    </section>
  );
}

function AuditLogPanel({ entries, status }: { entries: AuditLogEntry[]; status: PanelStatus }) {
  return (
    <section id="audit" className="panel audit-panel" aria-busy={status.loading}>
      <div className="panel-header">
        <div>
          <p className="eyebrow">Audit</p>
          <h2>Recent changes</h2>
        </div>
        <History size={22} />
      </div>
      <PanelNotice status={status} loadingText="Loading audit log..." />
      {entries.length === 0 && <EmptyState text="Audit entries will appear after financial data changes." />}
      {entries.length > 0 && (
        <div className="audit-list">
          {entries.slice(0, 20).map((entry) => (
            <article className="audit-row" key={entry.id}>
              <div>
                <strong>{formatEventName(entry.action)} {formatEventName(entry.entity_type)}</strong>
                <span>{auditChangeSummary(entry)}</span>
              </div>
              <div className="audit-meta">
                <span>{shortId(entry.entity_id)}</span>
                <strong>{formatDateTime(entry.created_at)}</strong>
              </div>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}

function auditChangeSummary(entry: AuditLogEntry) {
  const afterTitle = valueFromPayload(entry.after_json, "title");
  const beforeTitle = valueFromPayload(entry.before_json, "title");
  const label = afterTitle || beforeTitle;
  const changedFields = Object.keys(entry.after_json ?? {}).filter(
    (key) => JSON.stringify(entry.after_json?.[key]) !== JSON.stringify(entry.before_json?.[key])
  );

  if (label && changedFields.length > 0) {
    return `${label} · ${changedFields.slice(0, 4).join(", ")}`;
  }
  if (label) {
    return label;
  }
  if (changedFields.length > 0) {
    return `Changed ${changedFields.slice(0, 4).join(", ")}`;
  }
  return entry.entity_id;
}

function valueFromPayload(payload: Record<string, unknown> | null, key: string) {
  const value = payload?.[key];
  return typeof value === "string" ? value : null;
}

function shortId(value: string) {
  return value.length > 12 ? `${value.slice(0, 8)}...` : value;
}

function formatEventName(value: string) {
  const normalized = value.replace(/_/g, " ");
  return normalized.charAt(0).toUpperCase() + normalized.slice(1);
}

function formatDateTime(value: string | null) {
  if (!value) return "No events";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit"
  }).format(date);
}

function MonthlyPlanPanel({
  plan,
  goals,
  summary,
  monthlyReport,
  status
}: {
  plan: Plan | null;
  goals: Goal[];
  summary: FinancialSummary | null;
  monthlyReport: MonthlyReport | null;
  status: PanelStatus;
}) {
  const [monthsToShow, setMonthsToShow] = useState(6);
  const goalLookup = useMemo(
    () => new Map(goals.map((goal) => [goal.id, goal])),
    [goals]
  );
  const planGoalLookup = useMemo(
    () => new Map((plan?.goals ?? []).map((goal) => [goal.goal_id, goal])),
    [plan]
  );
  const schedule = plan?.monthly_schedule.slice(0, monthsToShow) ?? [];
  const currency = summary?.base_currency || plan?.goals[0]?.currency || "USD";
  const actualByGoalId = useMemo(
    () => new Map((monthlyReport?.goal_reports ?? []).map((goal) => [goal.goal_id, goal])),
    [monthlyReport]
  );
  const plannedVsActualRows = (plan?.goals ?? [])
    .map((goal) => {
      const actual = actualByGoalId.get(goal.goal_id);
      const plannedAmount = Number(goal.allocated_first_month || 0);
      const actualAmount = Number(actual?.net_amount ?? 0);
      return {
        goalId: goal.goal_id,
        title: goal.title,
        currency: goal.currency,
        plannedAmount,
        actualAmount,
        variance: actualAmount - plannedAmount,
        progressPercent: plannedAmount > 0 ? Math.min(100, Math.max(0, (actualAmount / plannedAmount) * 100)) : 0
      };
    })
    .filter((row) => row.plannedAmount > 0 || row.actualAmount !== 0);
  const plannedTotal = plannedVsActualRows.reduce((sum, row) => sum + row.plannedAmount, 0);
  const actualTotal = plannedVsActualRows.reduce((sum, row) => sum + row.actualAmount, 0);
  const totalVariance = actualTotal - plannedTotal;

  return (
    <section id="month-plan" className="panel monthly-plan-panel" aria-busy={status.loading}>
      <div className="panel-header">
        <div>
          <p className="eyebrow">Month plan</p>
          <h2>Contribution calendar</h2>
        </div>
        <CalendarClock size={22} />
      </div>
      <PanelNotice status={status} loadingText="Loading monthly plan..." />
      <div className="monthly-plan-toolbar">
        <div className="plan-summary compact-summary">
          <div>
            <span>Monthly budget</span>
            <strong>{formatMoney(plan?.monthly_available_amount, currency)}</strong>
          </div>
          <div>
            <span>Strategy</span>
            <strong>{formatStrategyName(plan?.strategy)}</strong>
          </div>
          <div>
            <span>Generated</span>
            <strong>{plan?.generated_at ?? "No plan"}</strong>
          </div>
        </div>
        <div className="segmented month-range" aria-label="Months to show">
          {[3, 6, 12].map((count) => (
            <button
              key={count}
              type="button"
              className={monthsToShow === count ? "active" : ""}
              aria-pressed={monthsToShow === count}
              onClick={() => setMonthsToShow(count)}
            >
              {count}m
            </button>
          ))}
        </div>
      </div>
      {schedule.length === 0 && <EmptyState text="The monthly calendar will appear after the plan has funded goals." />}
      {schedule.length > 0 && (
        <div className="monthly-calendar">
          {schedule.map((month) => {
            const entries = Object.entries(month.allocations)
              .map(([goalId, amount]) => ({
                goalId,
                amount,
                goal: planGoalLookup.get(goalId),
                fallbackGoal: goalLookup.get(goalId)
              }))
              .filter((entry) => Number(entry.amount) > 0);
            const total = entries.reduce((sum, entry) => sum + Number(entry.amount), 0);

            return (
              <article className="calendar-month" key={`${month.month_index}-${month.period_date}`}>
                <div className="calendar-month-header">
                  <div>
                    <span>Month {month.month_index}</span>
                    <strong>{formatMonthLabel(month.period_date)}</strong>
                  </div>
                  <strong>{formatMoney(total, currency)}</strong>
                </div>
                <div className="calendar-allocation-list">
                  {entries.map((entry) => (
                    <div className="calendar-allocation" key={entry.goalId}>
                      <span>{entry.goal?.title ?? entry.fallbackGoal?.title ?? "Goal"}</span>
                      <strong>{formatMoney(entry.amount, entry.goal?.currency ?? currency)}</strong>
                    </div>
                  ))}
                </div>
              </article>
            );
          })}
        </div>
      )}
      <div className="subsection planned-actual-section">
        <div className="subsection-header">
          <h3>Planned vs actual</h3>
          <ReceiptText size={18} />
        </div>
        <div className="planned-actual-summary">
          <div>
            <span>Planned</span>
            <strong>{formatMoney(plannedTotal, currency)}</strong>
          </div>
          <div>
            <span>Actual</span>
            <strong>{formatMoney(actualTotal, currency)}</strong>
          </div>
          <div>
            <span>Variance</span>
            <strong className={totalVariance >= 0 ? "positive-variance" : "negative-variance"}>
              {formatSignedMoney(totalVariance, currency)}
            </strong>
          </div>
        </div>
        {plannedVsActualRows.length === 0 && <EmptyState text="Planned vs actual will appear after goals receive planned or actual contributions this month." />}
        {plannedVsActualRows.length > 0 && (
          <div className="planned-actual-list">
            {plannedVsActualRows.map((row) => (
              <article className="planned-actual-row" key={row.goalId}>
                <div className="planned-actual-main">
                  <strong>{row.title}</strong>
                  <div className="progress-track">
                    <div
                      role="progressbar"
                      aria-label={`${row.title} planned versus actual progress`}
                      aria-valuemin={0}
                      aria-valuemax={100}
                      aria-valuenow={Math.round(row.progressPercent)}
                      style={{ width: `${row.progressPercent}%` }}
                    />
                  </div>
                </div>
                <div className="planned-actual-values">
                  <span>Plan {formatMoney(row.plannedAmount, row.currency)}</span>
                  <span>Actual {formatMoney(row.actualAmount, row.currency)}</span>
                  <strong className={row.variance >= 0 ? "positive-variance" : "negative-variance"}>
                    {formatSignedMoney(row.variance, row.currency)}
                  </strong>
                </div>
              </article>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}

function formatStrategyName(strategy: string | null | undefined) {
  if (!strategy) return "No strategy";
  return strategy.replace(/_/g, " ");
}

function formatMonthLabel(value: string) {
  const date = new Date(`${value}T00:00:00`);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat(undefined, { month: "short", year: "numeric" }).format(date);
}

function formatSignedMoney(value: number, currency = "") {
  const sign = value > 0 ? "+" : value < 0 ? "-" : "";
  return `${sign}${formatMoney(Math.abs(value), currency)}`;
}

function filenameFromContentDisposition(header: string | null) {
  if (!header) return null;
  const utf8Match = header.match(/filename\*=UTF-8''([^;]+)/i);
  if (utf8Match?.[1]) {
    return decodeURIComponent(utf8Match[1]);
  }
  const quotedMatch = header.match(/filename="([^"]+)"/i);
  if (quotedMatch?.[1]) {
    return quotedMatch[1];
  }
  const plainMatch = header.match(/filename=([^;]+)/i);
  return plainMatch?.[1]?.trim() || null;
}

function PlanSection({
  plan,
  summary,
  refreshToken,
  status
}: {
  plan: Plan | null;
  summary: FinancialSummary | null;
  refreshToken: string | null;
  status: PanelStatus;
}) {
  return (
    <section id="plan" className="panel plan-panel" aria-busy={status.loading}>
      <div className="panel-header">
        <div>
          <p className="eyebrow">Plan</p>
          <h2>Projected goal schedule</h2>
        </div>
        <ListChecks size={22} />
      </div>
      <PanelNotice status={status} loadingText="Loading projected schedule..." />
      <div className="plan-summary">
        <div>
          <span>Used for monthly allocation</span>
          <strong>{formatMoney(plan?.monthly_available_amount, summary?.base_currency)}</strong>
        </div>
        <div>
          <span>Calculated safe capacity</span>
          <strong>{formatMoney(summary?.calculated_monthly_available_amount, summary?.base_currency)}</strong>
        </div>
        <div>
          <span>Refresh token</span>
          <strong>{refreshToken ? "Stored" : "Missing"}</strong>
        </div>
      </div>
      {plan && [...plan.conflicts, ...plan.recommendations].length > 0 && (
        <div className="plan-message-list">
          {[...plan.conflicts, ...plan.recommendations].slice(0, 6).map((item) => (
            <div className="recommendation-row" key={item}>
              <AlertTriangle size={16} />
              <span>{item}</span>
            </div>
          ))}
        </div>
      )}
      <div className="projection-list">
        {!plan?.goals.length && <EmptyState text="The projection will appear after you add goals." />}
        {plan?.goals.map((goal) => (
          <article className="projection-row" key={goal.goal_id}>
            <div>
              <strong>{goal.title}</strong>
              <span>{goal.explanation}</span>
            </div>
            <div className="projection-meta">
              <span>{formatMoney(goal.remaining_amount, goal.currency)} left</span>
              <span>{goal.expected_completion_date ?? "No date"}</span>
              <span className={`probability ${goal.probability}`} title="Based on cautious, realistic, and optimistic scenarios">
                {goal.probability}
              </span>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

function EmptyState({ text }: { text: string }) {
  return <div className="empty-state">{text}</div>;
}
