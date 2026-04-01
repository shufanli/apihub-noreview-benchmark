"use client";

import { useState, useEffect } from "react";
import { Navbar } from "@/components/navbar";
import { useAuth } from "@/lib/auth-context";
import { api } from "@/lib/api";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";
const BASE_PATH = process.env.NEXT_PUBLIC_BASE_PATH || "";

interface Plan {
  id: string;
  name: string;
  price_monthly: number;
  price_yearly: number;
  limit: number;
  features: string[];
  popular: boolean;
}

const faqs = [
  { q: "How does the free plan work?", a: "The free plan gives you 1,000 API calls per month. No credit card required. Perfect for testing and small projects." },
  { q: "Can I upgrade or downgrade anytime?", a: "Yes! Upgrades take effect immediately. Downgrades take effect at the end of your current billing period." },
  { q: "What happens if I exceed my API call limit?", a: "You'll receive a warning at 80% usage. At 100%, additional calls will return a 429 status code until the next billing cycle." },
  { q: "Do you offer refunds?", a: "We offer a 14-day money-back guarantee on all paid plans. Contact support for assistance." },
  { q: "Is there a rate limit?", a: "Free plans have a rate limit of 10 requests/second. Pro plans get 100 req/s, and Enterprise gets 1,000 req/s." },
];

export default function PricingPage() {
  const [yearly, setYearly] = useState(false);
  const [plans, setPlans] = useState<Plan[]>([]);
  const [openFaq, setOpenFaq] = useState<number | null>(null);
  const { user } = useAuth();

  useEffect(() => {
    api.getPricing().then(setPlans).catch(() => {});
  }, []);

  const handleSelect = (planId: string) => {
    if (!user) {
      window.location.href = `${API_BASE || BASE_PATH}/api/auth/login?redirect=/dashboard/billing`;
      return;
    }
    if (planId === "free") return;
    window.location.href = `/dashboard/billing?upgrade=${planId}`;
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold text-gray-900 mb-4">
            Simple, transparent pricing
          </h1>
          <p className="text-xl text-gray-600 max-w-2xl mx-auto">
            Choose the plan that fits your needs. Scale as you grow.
          </p>
        </div>

        {/* Monthly/Yearly toggle */}
        <div className="flex items-center justify-center gap-3 mb-12">
          <span className={`text-sm ${!yearly ? "text-gray-900 font-medium" : "text-gray-500"}`}>
            Monthly
          </span>
          <button
            onClick={() => setYearly(!yearly)}
            className={`relative w-14 h-7 rounded-full transition-colors ${yearly ? "bg-indigo-600" : "bg-gray-300"}`}
          >
            <span
              className={`absolute top-0.5 left-0.5 w-6 h-6 bg-white rounded-full shadow transition-transform ${yearly ? "translate-x-7" : ""}`}
            />
          </button>
          <span className={`text-sm ${yearly ? "text-gray-900 font-medium" : "text-gray-500"}`}>
            Yearly <span className="text-green-600 font-medium">(Save ~17%)</span>
          </span>
        </div>

        {/* Pricing cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-5xl mx-auto mb-20">
          {plans.map((plan) => (
            <div
              key={plan.id}
              className={`bg-white rounded-2xl shadow-sm border-2 p-8 relative flex flex-col ${
                plan.popular ? "border-indigo-600 shadow-lg" : "border-gray-200"
              }`}
            >
              {plan.popular && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2 bg-indigo-600 text-white text-xs font-bold px-3 py-1 rounded-full">
                  Most Popular
                </div>
              )}
              <h3 className="text-lg font-semibold text-gray-900">{plan.name}</h3>
              <div className="mt-4 flex items-baseline">
                <span className="text-4xl font-bold text-gray-900 transition-all duration-300">
                  ${yearly ? plan.price_yearly : plan.price_monthly}
                </span>
                <span className="text-gray-500 ml-1">/month</span>
              </div>
              <ul className="mt-6 space-y-3 flex-1">
                {plan.features.map((feature, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-gray-600">
                    <svg className="w-5 h-5 text-green-500 flex-shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                    {feature}
                  </li>
                ))}
              </ul>
              <button
                onClick={() => handleSelect(plan.id)}
                className={`mt-8 w-full py-3 rounded-lg font-medium transition ${
                  plan.popular
                    ? "bg-indigo-600 text-white hover:bg-indigo-700"
                    : "bg-gray-100 text-gray-900 hover:bg-gray-200"
                }`}
              >
                {plan.id === "free" ? "Get Started" : "Subscribe"}
              </button>
            </div>
          ))}
        </div>

        {/* FAQ */}
        <div className="max-w-3xl mx-auto">
          <h2 className="text-2xl font-bold text-gray-900 text-center mb-8">
            Frequently Asked Questions
          </h2>
          <div className="space-y-3">
            {faqs.map((faq, i) => (
              <div key={i} className="bg-white rounded-lg border border-gray-200">
                <button
                  onClick={() => setOpenFaq(openFaq === i ? null : i)}
                  className="w-full px-6 py-4 text-left flex justify-between items-center"
                >
                  <span className="font-medium text-gray-900">{faq.q}</span>
                  <svg
                    className={`w-5 h-5 text-gray-500 transition-transform ${openFaq === i ? "rotate-180" : ""}`}
                    fill="none" viewBox="0 0 24 24" stroke="currentColor"
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </button>
                {openFaq === i && (
                  <div className="px-6 pb-4 text-gray-600">{faq.a}</div>
                )}
              </div>
            ))}
          </div>
        </div>
      </main>
    </div>
  );
}
