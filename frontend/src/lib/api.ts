const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";
const BASE_PATH = process.env.NEXT_PUBLIC_BASE_PATH || "";

async function fetcher(path: string, options?: RequestInit) {
  const url = API_BASE ? `${API_BASE}${path}` : `${BASE_PATH}${path}`;
  const res = await fetch(url, {
    credentials: "include",
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || res.statusText);
  }
  return res.json();
}

export const api = {
  // Auth
  getMe: () => fetcher("/api/auth/me"),
  logout: () => fetcher("/api/auth/logout", { method: "POST" }),
  devLogin: (userId?: string) =>
    fetcher(`/api/auth/dev-login${userId ? `?user_id=${userId}` : ""}`),

  // Pricing
  getPricing: () => fetcher("/api/pricing"),

  // Keys
  getKeys: () => fetcher("/api/keys"),
  createKey: (data: { name: string; description?: string; permissions: string[] }) =>
    fetcher("/api/keys", { method: "POST", body: JSON.stringify(data) }),
  deleteKey: (keyId: string) =>
    fetcher(`/api/keys/${keyId}`, { method: "DELETE" }),

  // Usage
  getUsageSummary: () => fetcher("/api/usage/summary"),
  getUsageChart: (range: string) => fetcher(`/api/usage/chart?range=${range}`),
  getUsageLogs: (page: number, status: string, search: string) =>
    fetcher(`/api/usage/logs?page=${page}&status=${status}&search=${search}`),

  // Billing
  getCurrentPlan: () => fetcher("/api/billing/current"),
  createCheckout: (plan: string, billingCycle: string) =>
    fetcher("/api/billing/checkout", {
      method: "POST",
      body: JSON.stringify({ plan, billing_cycle: billingCycle }),
    }),
  downgrade: (plan: string) =>
    fetcher("/api/billing/downgrade", {
      method: "POST",
      body: JSON.stringify({ plan }),
    }),
  getInvoices: (page: number) => fetcher(`/api/billing/invoices?page=${page}`),
};
