"use client";

import { useState, useEffect, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { api } from "@/lib/api";

interface PlanInfo {
  plan: string;
  plan_name: string;
  price_monthly: number;
  limit: number;
  usage: number;
  stripe_customer_id: string | null;
}

interface Invoice {
  id: string;
  amount_cents: number;
  status: string;
  pdf_url: string;
  created_at: string;
}

const ALL_PLANS = [
  { id: "free", name: "Free", price: 0, limit: 1000 },
  { id: "pro", name: "Pro", price: 2900, limit: 50000 },
  { id: "enterprise", name: "Enterprise", price: 19900, limit: 500000 },
];

function BillingContent() {
  const searchParams = useSearchParams();
  const [planInfo, setPlanInfo] = useState<PlanInfo | null>(null);
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [invoiceMeta, setInvoiceMeta] = useState({ page: 1, total_pages: 1 });
  const [showChangePlan, setShowChangePlan] = useState(false);
  const [selectedPlan, setSelectedPlan] = useState<string | null>(null);
  const [animatedLimit, setAnimatedLimit] = useState(0);
  const [toast, setToast] = useState<string | null>(null);

  useEffect(() => {
    api.getCurrentPlan().then(setPlanInfo).catch(() => {});
    fetchInvoices(1);
  }, []);

  // Toast for Stripe return
  useEffect(() => {
    if (searchParams.get("success") === "true") {
      setToast("Payment successful! Your plan has been upgraded.");
      // Update plan if specified
      const plan = searchParams.get("plan");
      if (plan) {
        api.getCurrentPlan().then(setPlanInfo).catch(() => {});
      }
    } else if (searchParams.get("canceled") === "true") {
      setToast("Payment was canceled.");
    }
    if (searchParams.get("upgrade")) {
      setShowChangePlan(true);
      setSelectedPlan(searchParams.get("upgrade"));
    }
  }, [searchParams]);

  // Animate limit change
  useEffect(() => {
    if (!selectedPlan) return;
    const target = ALL_PLANS.find((p) => p.id === selectedPlan)?.limit || 0;
    const start = animatedLimit;
    const duration = 500;
    const startTime = Date.now();

    const animate = () => {
      const elapsed = Date.now() - startTime;
      const progress = Math.min(elapsed / duration, 1);
      setAnimatedLimit(Math.round(start + (target - start) * progress));
      if (progress < 1) requestAnimationFrame(animate);
    };
    animate();
  }, [selectedPlan]);

  const fetchInvoices = (page: number) => {
    api.getInvoices(page).then((data) => {
      setInvoices(data.items);
      setInvoiceMeta({ page: data.page, total_pages: data.total_pages });
    }).catch(() => {});
  };

  const handleUpgrade = async (planId: string) => {
    try {
      const result = await api.createCheckout(planId, "monthly");
      if (result.checkout_url) {
        window.location.href = result.checkout_url;
      }
    } catch (err) {
      alert(err instanceof Error ? err.message : "Checkout failed");
    }
  };

  const handleDowngrade = async (planId: string) => {
    if (!confirm("Are you sure? The downgrade will take effect at the end of your current billing period.")) return;
    try {
      await api.downgrade(planId);
      setToast("Plan will be downgraded at end of current period.");
      setShowChangePlan(false);
      api.getCurrentPlan().then(setPlanInfo).catch(() => {});
    } catch (err) {
      alert(err instanceof Error ? err.message : "Downgrade failed");
    }
  };

  const usagePct = planInfo ? Math.min(100, (planInfo.usage / planInfo.limit) * 100) : 0;

  return (
    <div>
      {/* Toast */}
      {toast && (
        <div className="mb-6 p-4 rounded-lg bg-indigo-50 border border-indigo-200 text-indigo-700 flex justify-between items-center">
          <span>{toast}</span>
          <button onClick={() => setToast(null)} className="text-indigo-500 hover:text-indigo-700">&times;</button>
        </div>
      )}

      <h1 className="text-2xl font-bold text-gray-900 mb-6">Billing</h1>

      {/* Current Plan */}
      <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm text-gray-500">Current Plan</p>
            <p className="text-2xl font-bold text-gray-900 capitalize">{planInfo?.plan_name || "-"}</p>
            <p className="text-gray-600 mt-1">
              {planInfo ? `$${(planInfo.price_monthly / 100).toFixed(0)}/month` : "-"}
              {" · "}
              {planInfo ? `${planInfo.limit.toLocaleString()} calls/month` : "-"}
            </p>
          </div>
          <button
            onClick={() => {
              setShowChangePlan(true);
              setSelectedPlan(null);
              setAnimatedLimit(planInfo?.limit || 0);
            }}
            className="bg-indigo-600 text-white px-4 py-2 rounded-lg hover:bg-indigo-700 transition text-sm font-medium"
          >
            Change Plan
          </button>
        </div>
      </div>

      {/* Usage bar */}
      <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6">
        <p className="text-sm text-gray-500 mb-2">Usage This Month</p>
        <div className="flex items-center justify-between mb-2">
          <span className="text-lg font-semibold">{planInfo?.usage?.toLocaleString() || 0}</span>
          <span className="text-sm text-gray-500">of {planInfo?.limit?.toLocaleString() || 0}</span>
        </div>
        <div className="h-3 bg-gray-200 rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full transition-all duration-500 ${
              usagePct > 90 ? "bg-red-500" : usagePct > 70 ? "bg-yellow-500" : "bg-indigo-600"
            }`}
            style={{ width: `${usagePct}%` }}
          />
        </div>
        {usagePct > 80 && (
          <p className="text-sm text-amber-600 mt-2">
            You&apos;re approaching your usage limit. Consider upgrading your plan.
          </p>
        )}
      </div>

      {/* Invoices */}
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Invoices</h2>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200">
                <th className="text-left py-3 px-2 text-gray-500 font-medium">Date</th>
                <th className="text-left py-3 px-2 text-gray-500 font-medium">Amount</th>
                <th className="text-left py-3 px-2 text-gray-500 font-medium">Status</th>
                <th className="text-left py-3 px-2 text-gray-500 font-medium">PDF</th>
              </tr>
            </thead>
            <tbody>
              {invoices.map((inv) => (
                <tr key={inv.id} className="border-b border-gray-100">
                  <td className="py-3 px-2 text-gray-600">{new Date(inv.created_at).toLocaleDateString()}</td>
                  <td className="py-3 px-2 text-gray-900 font-medium">${(inv.amount_cents / 100).toFixed(2)}</td>
                  <td className="py-3 px-2">
                    <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${
                      inv.status === "paid" ? "bg-green-100 text-green-700" : "bg-yellow-100 text-yellow-700"
                    }`}>
                      {inv.status}
                    </span>
                  </td>
                  <td className="py-3 px-2">
                    {inv.pdf_url && (
                      <a href={inv.pdf_url} target="_blank" rel="noopener noreferrer" className="text-indigo-600 hover:underline text-xs">
                        Download
                      </a>
                    )}
                  </td>
                </tr>
              ))}
              {invoices.length === 0 && (
                <tr><td colSpan={4} className="py-8 text-center text-gray-500">No invoices yet</td></tr>
              )}
            </tbody>
          </table>
        </div>

        {invoiceMeta.total_pages > 1 && (
          <div className="flex gap-2 justify-end mt-4">
            <button
              onClick={() => fetchInvoices(invoiceMeta.page - 1)}
              disabled={invoiceMeta.page <= 1}
              className="px-3 py-1 text-sm border border-gray-300 rounded-lg disabled:opacity-50"
            >
              Previous
            </button>
            <button
              onClick={() => fetchInvoices(invoiceMeta.page + 1)}
              disabled={invoiceMeta.page >= invoiceMeta.total_pages}
              className="px-3 py-1 text-sm border border-gray-300 rounded-lg disabled:opacity-50"
            >
              Next
            </button>
          </div>
        )}
      </div>

      {/* Change Plan Modal */}
      {showChangePlan && planInfo && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 w-full max-w-2xl mx-4">
            <h3 className="text-lg font-semibold text-gray-900 mb-6">Change Plan</h3>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
              {ALL_PLANS.map((plan) => {
                const isCurrent = plan.id === planInfo.plan;
                const isSelected = plan.id === selectedPlan;
                return (
                  <button
                    key={plan.id}
                    onClick={() => {
                      if (!isCurrent) {
                        setSelectedPlan(plan.id);
                      }
                    }}
                    className={`p-4 rounded-xl border-2 text-left transition ${
                      isSelected ? "border-indigo-600 bg-indigo-50" :
                      isCurrent ? "border-gray-300 bg-gray-50" :
                      "border-gray-200 hover:border-gray-300"
                    }`}
                  >
                    <p className="font-semibold text-gray-900">{plan.name}</p>
                    <p className="text-2xl font-bold mt-1">${(plan.price / 100).toFixed(0)}<span className="text-sm text-gray-500">/mo</span></p>
                    <p className="text-sm text-gray-500 mt-1">{plan.limit.toLocaleString()} calls</p>
                    {isCurrent && (
                      <span className="inline-block mt-2 text-xs bg-gray-200 text-gray-600 px-2 py-0.5 rounded">Current</span>
                    )}
                  </button>
                );
              })}
            </div>

            {selectedPlan && (
              <div className="bg-gray-50 rounded-lg p-4 mb-6">
                <p className="text-sm text-gray-600">New API call limit:</p>
                <p className="text-2xl font-bold text-indigo-600">{animatedLimit.toLocaleString()}</p>
              </div>
            )}

            <div className="flex gap-3 justify-end">
              <button
                onClick={() => setShowChangePlan(false)}
                className="px-4 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-50"
              >
                Cancel
              </button>
              {selectedPlan && (
                (() => {
                  const planOrder: Record<string, number> = { free: 0, pro: 1, enterprise: 2 };
                  const isUpgrade = planOrder[selectedPlan] > planOrder[planInfo.plan];
                  return isUpgrade ? (
                    <button
                      onClick={() => handleUpgrade(selectedPlan)}
                      className="px-4 py-2 text-sm bg-indigo-600 text-white rounded-lg hover:bg-indigo-700"
                    >
                      Upgrade to {ALL_PLANS.find((p) => p.id === selectedPlan)?.name}
                    </button>
                  ) : (
                    <button
                      onClick={() => handleDowngrade(selectedPlan)}
                      className="px-4 py-2 text-sm bg-gray-600 text-white rounded-lg hover:bg-gray-700"
                    >
                      Downgrade to {ALL_PLANS.find((p) => p.id === selectedPlan)?.name}
                    </button>
                  );
                })()
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default function BillingPage() {
  return (
    <Suspense fallback={<div className="p-8">Loading...</div>}>
      <BillingContent />
    </Suspense>
  );
}
