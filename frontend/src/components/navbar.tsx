"use client";

import Link from "next/link";
import { useState } from "react";
import { useAuth } from "@/lib/auth-context";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";
const BASE_PATH = process.env.NEXT_PUBLIC_BASE_PATH || "";

export function Navbar() {
  const { user, loading } = useAuth();
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <nav className="bg-white border-b border-gray-200 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16">
          <div className="flex items-center">
            <Link href="/pricing" className="text-xl font-bold text-indigo-600">
              ApiHub
            </Link>
          </div>

          {/* Desktop */}
          <div className="hidden md:flex items-center gap-4">
            <Link href="/pricing" className="text-gray-600 hover:text-gray-900">
              Pricing
            </Link>
            {!loading && (
              user ? (
                <Link
                  href="/dashboard"
                  className="bg-indigo-600 text-white px-4 py-2 rounded-lg hover:bg-indigo-700 transition"
                >
                  Dashboard
                </Link>
              ) : (
                <a
                  href={`${API_BASE || BASE_PATH}/api/auth/login`}
                  className="bg-indigo-600 text-white px-4 py-2 rounded-lg hover:bg-indigo-700 transition"
                >
                  Sign In
                </a>
              )
            )}
          </div>

          {/* Mobile hamburger */}
          <div className="md:hidden flex items-center">
            <button
              onClick={() => setMenuOpen(!menuOpen)}
              className="p-2 rounded-md text-gray-600 hover:bg-gray-100"
            >
              <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                {menuOpen ? (
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                ) : (
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                )}
              </svg>
            </button>
          </div>
        </div>
      </div>

      {/* Mobile drawer */}
      {menuOpen && (
        <div className="md:hidden bg-white border-t border-gray-200 px-4 py-3 space-y-2">
          <Link href="/pricing" className="block text-gray-600 hover:text-gray-900 py-2" onClick={() => setMenuOpen(false)}>
            Pricing
          </Link>
          {!loading && (
            user ? (
              <Link href="/dashboard" className="block text-indigo-600 font-medium py-2" onClick={() => setMenuOpen(false)}>
                Dashboard
              </Link>
            ) : (
              <a href={`${API_BASE || BASE_PATH}/api/auth/login`} className="block text-indigo-600 font-medium py-2">
                Sign In
              </a>
            )
          )}
        </div>
      )}
    </nav>
  );
}
