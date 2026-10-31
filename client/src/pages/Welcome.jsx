import React from 'react';
import { Link } from 'react-router-dom';
import { 
  Sparkles, 
  ArrowRight, 
  ShieldCheck, 
  Users, 
  Briefcase, 
  KeyRound, 
  Layers, 
  CheckCircle2, 
  Database,
  Lock,
  ArrowUpRight
} from 'lucide-react';

export default function Welcome() {
  return (
    <div className="relative min-h-[calc(100vh-4rem)] flex flex-col justify-between overflow-hidden">
      
      {/* Background Decorative Gradients */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-full max-w-7xl h-96 bg-gradient-to-b from-brand-100/60 to-transparent -z-10 blur-3xl pointer-events-none" />
      <div className="absolute -top-24 -right-24 w-96 h-96 bg-teal-200/40 rounded-full blur-3xl -z-10 pointer-events-none" />

      {/* Hero Section */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-12 pb-16 flex-1 flex flex-col items-center justify-center text-center">
        
        {/* Status Pill */}
        <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-brand-50 border border-brand-200 text-brand-800 text-xs sm:text-sm font-semibold mb-6 shadow-xs">
          <Sparkles className="w-4 h-4 text-brand-600 animate-pulse" />
          <span>Role-Based Authentication & Operations Platform</span>
        </div>

        {/* Hero Title */}
        <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold tracking-tight text-slate-900 max-w-4xl leading-tight">
          Seamless portal experience for <br className="hidden sm:inline" />
          <span className="bg-gradient-to-r from-brand-600 to-teal-500 bg-clip-text text-transparent">
            Customers & Enterprise Staff
          </span>
        </h1>

        {/* Hero Description */}
        <p className="mt-6 text-lg sm:text-xl text-slate-600 max-w-2xl leading-relaxed">
          Welcome to <strong className="text-slate-900 font-semibold">BrightLoop</strong>. A unified system offering instant customer onboarding, secure credentials management, and restricted staff management for administrators.
        </p>

        {/* CTA Buttons */}
        <div className="mt-8 flex flex-col sm:flex-row items-center gap-4 w-full sm:w-auto">
          <Link
            to="/register"
            className="w-full sm:w-auto flex items-center justify-center gap-2 px-7 py-3.5 rounded-xl font-semibold text-white bg-brand-600 hover:bg-brand-700 shadow-md shadow-brand-600/30 transition-all hover:scale-[1.02]"
          >
            <span>Register as Customer</span>
            <ArrowRight className="w-4 h-4" />
          </Link>
          <Link
            to="/login"
            className="w-full sm:w-auto flex items-center justify-center gap-2 px-7 py-3.5 rounded-xl font-semibold text-slate-700 bg-white hover:bg-slate-50 border border-slate-300 shadow-xs transition-all hover:border-slate-400"
          >
            <span>Sign In to Portal</span>
          </Link>
        </div>

        {/* Interactive Feature Cards */}
        <div className="mt-16 grid grid-cols-1 md:grid-cols-3 gap-6 text-left w-full max-w-5xl">
          
          {/* Card 1: Customer Space */}
          <div className="p-6 rounded-2xl bg-white border border-slate-200 shadow-xs hover:shadow-md transition-shadow">
            <div className="w-12 h-12 rounded-xl bg-brand-50 border border-brand-100 flex items-center justify-center text-brand-600 mb-4">
              <Users className="w-6 h-6" />
            </div>
            <h3 className="text-lg font-bold text-slate-900">Customer Dashboard</h3>
            <p className="mt-2 text-sm text-slate-600 leading-relaxed">
              Customers can register self-serve, manage their personal profile, track activity, and earn loyalty perks.
            </p>
            <div className="mt-4 pt-4 border-t border-slate-100 flex items-center text-xs font-semibold text-brand-600">
              <Link to="/register" className="inline-flex items-center gap-1 hover:underline">
                Create Customer Account <ArrowUpRight className="w-3.5 h-3.5" />
              </Link>
            </div>
          </div>

          {/* Card 2: Admin Control */}
          <div className="p-6 rounded-2xl bg-white border border-slate-200 shadow-xs hover:shadow-md transition-shadow">
            <div className="w-12 h-12 rounded-xl bg-amber-50 border border-amber-100 flex items-center justify-center text-amber-600 mb-4">
              <ShieldCheck className="w-6 h-6" />
            </div>
            <h3 className="text-lg font-bold text-slate-900">Admin Command Center</h3>
            <p className="mt-2 text-sm text-slate-600 leading-relaxed">
              Full administrative governance. Only administrators are authorized to register and provision Staff accounts.
            </p>
            <div className="mt-4 pt-4 border-t border-slate-100 flex items-center text-xs font-semibold text-amber-600">
              <Link to="/login" className="inline-flex items-center gap-1 hover:underline">
                Admin Sign In <ArrowUpRight className="w-3.5 h-3.5" />
              </Link>
            </div>
          </div>

          {/* Card 3: Database & Security */}
          <div className="p-6 rounded-2xl bg-white border border-slate-200 shadow-xs hover:shadow-md transition-shadow">
            <div className="w-12 h-12 rounded-xl bg-indigo-50 border border-indigo-100 flex items-center justify-center text-indigo-600 mb-4">
              <Database className="w-6 h-6" />
            </div>
            <h3 className="text-lg font-bold text-slate-900">Relational Database</h3>
            <p className="mt-2 text-sm text-slate-600 leading-relaxed">
              Structured SQLite relational tables: <span className="font-semibold text-slate-800">Users</span>, <span className="font-semibold text-slate-800">Customers</span>, and <span className="font-semibold text-slate-800">Staff</span> with foreign keys.
            </p>
            <div className="mt-4 pt-4 border-t border-slate-100 flex items-center text-xs font-semibold text-indigo-600">
              <span className="inline-flex items-center gap-1">
                Foreign Key Protected <CheckCircle2 className="w-3.5 h-3.5" />
              </span>
            </div>
          </div>

        </div>

        {/* Demo Quick-Login Credentials Section */}
        <div className="mt-12 w-full max-w-4xl p-5 rounded-2xl bg-slate-900 text-slate-200 text-left border border-slate-800 shadow-xl">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-slate-800">
            <div className="flex items-center gap-2">
              <KeyRound className="w-5 h-5 text-brand-400" />
              <h4 className="font-semibold text-white">Pre-configured Demo Credentials</h4>
            </div>
            <span className="text-xs text-slate-400">Clicking Sign In allows testing with these accounts immediately</span>
          </div>

          <div className="mt-4 grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs font-mono">
            <div className="p-3 rounded-lg bg-slate-800/80 border border-slate-700/60">
              <div className="text-amber-400 font-bold text-sm mb-1 font-sans">Admin Account</div>
              <div><span className="text-slate-400">Email:</span> admin@brightloop.com</div>
              <div><span className="text-slate-400">Pass:</span> AdminPassword123!</div>
              <div className="mt-1 text-slate-400 text-[11px] font-sans">→ Goes to Admin Dashboard</div>
            </div>

            <div className="p-3 rounded-lg bg-slate-800/80 border border-slate-700/60">
              <div className="text-brand-400 font-bold text-sm mb-1 font-sans">Customer Account</div>
              <div><span className="text-slate-400">Email:</span> customer@brightloop.com</div>
              <div><span className="text-slate-400">Pass:</span> CustomerPassword123!</div>
              <div className="mt-1 text-slate-400 text-[11px] font-sans">→ Goes to Customer Dashboard</div>
            </div>

            <div className="p-3 rounded-lg bg-slate-800/80 border border-slate-700/60">
              <div className="text-indigo-400 font-bold text-sm mb-1 font-sans">Staff Account</div>
              <div><span className="text-slate-400">Email:</span> staff@brightloop.com</div>
              <div><span className="text-slate-400">Pass:</span> StaffPassword123!</div>
              <div className="mt-1 text-slate-400 text-[11px] font-sans">→ Registered by Admin only</div>
            </div>
          </div>
        </div>

      </main>

      {/* Footer */}
      <footer className="border-t border-slate-200 bg-white py-6 text-center text-xs text-slate-500">
        <div className="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-2">
          <p>© 2026 BrightLoop Enterprise Inc. All rights reserved.</p>
          <div className="flex items-center gap-4">
            <span className="text-slate-400">Role-Based System</span>
            <span>•</span>
            <span className="text-slate-400">Users · Customers · Staff</span>
          </div>
        </div>
      </footer>

    </div>
  );
}
