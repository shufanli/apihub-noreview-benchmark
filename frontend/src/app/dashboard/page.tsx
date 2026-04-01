"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { api } from "@/lib/api";
import { useSearchParams, useRouter } from "next/navigation";
import dynamic from "next/dynamic";

const LineChart = dynamic(() => import("recharts").then((m) => m.LineChart), { ssr: false });
const Line = dynamic(() => import("recharts").then((m) => m.Line), { ssr: false });
const XAxis = dynamic(() => import("recharts").then((m) => m.XAxis), { ssr: false });
const YAxis = dynamic(() => import("recharts").then((m) => m.YAxis), { ssr: false });
const CartesianGrid = dynamic(() => import("recharts").then((m) => m.CartesianGrid), { ssr: false });
const Tooltip = dynamic(() => import("recharts").then((m) => m.Tooltip), { ssr: false });
const ResponsiveContainer = dynamic(() => import("recharts").then((m) => m.ResponsiveContainer), { ssr: false });

interface Summary {
  today_calls: number;
  yesterday_calls: number;
  change_pct: number;
  month_calls: number;
  month_limit: number;
  plan: string;
}

interface LogItem {
  id: number;
  endpoint: string;
  status_code: number;
  latency_ms: number;
  created_at: string;
}

export default function DashboardPage() {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [chartData, setChartData] = useState<{ date: string; count: number }[]>([]);
  const [chartRange, setChartRange] = useState("7d");
  const [chartLoading, setChartLoading] = useState(false);
  const [logs, setLogs] = useState<LogItem[]>([]);
  const [logsMeta, setLogsMeta] = useState({ total: 0, page: 1, total_pages: 1 });
  const [statusFilter, setStatusFilter] = useState("all");
  const [searchQuery, setSearchQuery] = useState("");
  const searchTimerRef = useRef<NodeJS.Timeout>();
  const router = useRouter();

  // Persist filters in URL
  const searchParams = useSearchParams();

  useEffect(() => {
    const s = searchParams.get("status");
    const q = searchParams.get("search");
    if (s) setStatusFilter(s);
    if (q) setSearchQuery(q);
  }, []);

  // Fetch summary
  useEffect(() => {
    api.getUsageSummary().then(setSummary).catch(() => {});
  }, []);

  // Fetch chart
  useEffect(() => {
    setChartLoading(true);
    api.getUsageChart(chartRange)
      .then(setChartData)
      .catch(() => {})
      .finally(() => setChartLoading(false));
  }, [chartRange]);

  // Fetch logs with debounced search
  const fetchLogs = useCallback((page: number, status: string, search: string) => {
    api.getUsageLogs(page, status, search)
      .then((data) => {
        setLogs(data.items);
        setLogsMeta({ total: data.total, page: data.page, total_pages: data.total_pages });
      })
      .catch(() => {});

    // Update URL params
    const params = new URLSearchParams();
    if (status !== "all") params.set("status", status);
    if (search) params.set("search", search);
    const qs = params.toString();
    window.history.replaceState(null, "", `/dashboard${qs ? `?${qs}` : ""}`);
  }, []);

  useEffect(() => {
    fetchLogs(1, statusFilter, searchQuery);
  }, [statusFilter]);

  useEffect(() => {
    if (searchTimerRef.current) clearTimeout(searchTimerRef.current);
    searchTimerRef.current = setTimeout(() => {
      fetchLogs(1, statusFilter, searchQuery);
    }, 300);
    return () => {
      if (searchTimerRef.current) clearTimeout(searchTimerRef.current);
    };
  }, [searchQuery]);

  // Auto-refresh every 30s
  useEffect(() => {
    const interval = setInterval(() => {
      api.getUsageSummary().then(setSummary).catch(() => {});
      fetchLogs(logsMeta.page, statusFilter, searchQuery);
    }, 30000);
    return () => clearInterval(interval);
  }, [logsMeta.page, statusFilter, searchQuery, fetchLogs]);

  const monthPct = summary ? Math.min(100, (summary.month_calls / summary.month_limit) * 100) : 0;

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Overview</h1>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        {/* Today's calls */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <p className="text-sm text-gray-500 mb-1">Today&apos;s Calls</p>
          <p className="text-3xl font-bold text-gray-900">{summary?.today_calls ?? "-"}</p>
          {summary && summary.change_pct !== 0 && (
            <p className={`text-sm mt-1 ${summary.change_pct > 0 ? "text-green-600" : "text-red-600"}`}>
              {summary.change_pct > 0 ? "+" : ""}{summary.change_pct}% vs yesterday
            </p>
          )}
        </div>

        {/* Monthly usage */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <p className="text-sm text-gray-500 mb-1">Monthly Usage</p>
          <p className="text-3xl font-bold text-gray-900">
            {summary ? `${summary.month_calls.toLocaleString()} / ${summary.month_limit.toLocaleString()}` : "-"}
          </p>
          <div className="mt-3 relative h-2 bg-gray-200 rounded-full overflow-hidden">
            <div
              className={`absolute inset-y-0 left-0 rounded-full transition-all duration-500 ${monthPct > 80 ? "bg-red-500" : "bg-indigo-600"}`}
              style={{ width: `${monthPct}%` }}
            />
          </div>
        </div>

        {/* Current plan */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <p className="text-sm text-gray-500 mb-1">Current Plan</p>
          <p className="text-3xl font-bold text-gray-900 capitalize">{summary?.plan ?? "-"}</p>
          {summary?.plan === "free" && (
            <button
              onClick={() => router.push("/dashboard/billing")}
              className="mt-3 text-sm bg-indigo-600 text-white px-4 py-1.5 rounded-lg hover:bg-indigo-700 transition"
            >
              Upgrade
            </button>
          )}
        </div>
      </div>

      {/* Usage Chart */}
      <div className="bg-white rounded-xl border border-gray-200 p-6 mb-8">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-900">Usage Over Time</h2>
          <div className="flex gap-1">
            {["7d", "30d", "90d"].map((range) => (
              <button
                key={range}
                onClick={() => setChartRange(range)}
                className={`px-3 py-1 text-sm rounded-lg transition ${
                  chartRange === range
                    ? "bg-indigo-600 text-white"
                    : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                }`}
              >
                {range}
              </button>
            ))}
          </div>
        </div>
        {chartLoading ? (
          <div className="flex items-center justify-center h-64">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600" />
          </div>
        ) : (
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis dataKey="date" tick={{ fontSize: 12 }} tickFormatter={(v) => v.slice(5)} />
                <YAxis tick={{ fontSize: 12 }} />
                <Tooltip />
                <Line type="monotone" dataKey="count" stroke="#4f46e5" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

      {/* Recent Logs */}
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Recent API Calls</h2>

        <div className="flex flex-col sm:flex-row gap-3 mb-4">
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="border border-gray-300 rounded-lg px-3 py-2 text-sm bg-white"
          >
            <option value="all">All Status</option>
            <option value="2xx">2xx Success</option>
            <option value="4xx">4xx Client Error</option>
            <option value="5xx">5xx Server Error</option>
          </select>
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search endpoint..."
            className="border border-gray-300 rounded-lg px-3 py-2 text-sm flex-1"
          />
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200">
                <th className="text-left py-3 px-2 text-gray-500 font-medium">Time</th>
                <th className="text-left py-3 px-2 text-gray-500 font-medium">Endpoint</th>
                <th className="text-left py-3 px-2 text-gray-500 font-medium">Status</th>
                <th className="text-left py-3 px-2 text-gray-500 font-medium">Latency</th>
              </tr>
            </thead>
            <tbody>
              {logs.map((log) => (
                <tr key={log.id} className="border-b border-gray-100 hover:bg-gray-50">
                  <td className="py-3 px-2 text-gray-600">{new Date(log.created_at).toLocaleString()}</td>
                  <td className="py-3 px-2 font-mono text-gray-900">{log.endpoint}</td>
                  <td className="py-3 px-2">
                    <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${
                      log.status_code < 300 ? "bg-green-100 text-green-700" :
                      log.status_code < 500 ? "bg-yellow-100 text-yellow-700" :
                      "bg-red-100 text-red-700"
                    }`}>
                      {log.status_code}
                    </span>
                  </td>
                  <td className="py-3 px-2 text-gray-600">{log.latency_ms}ms</td>
                </tr>
              ))}
              {logs.length === 0 && (
                <tr><td colSpan={4} className="py-8 text-center text-gray-500">No logs found</td></tr>
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {logsMeta.total_pages > 1 && (
          <div className="flex items-center justify-between mt-4">
            <p className="text-sm text-gray-500">
              Page {logsMeta.page} of {logsMeta.total_pages} ({logsMeta.total} total)
            </p>
            <div className="flex gap-2">
              <button
                onClick={() => fetchLogs(logsMeta.page - 1, statusFilter, searchQuery)}
                disabled={logsMeta.page <= 1}
                className="px-3 py-1 text-sm border border-gray-300 rounded-lg disabled:opacity-50 hover:bg-gray-50"
              >
                Previous
              </button>
              <button
                onClick={() => fetchLogs(logsMeta.page + 1, statusFilter, searchQuery)}
                disabled={logsMeta.page >= logsMeta.total_pages}
                className="px-3 py-1 text-sm border border-gray-300 rounded-lg disabled:opacity-50 hover:bg-gray-50"
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
