import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { api } from '../services/api';
import { 
  User, 
  Award, 
  Calendar, 
  MapPin, 
  Phone, 
  Mail, 
  Clock, 
  CheckCircle2, 
  Sparkles, 
  ArrowRight, 
  ShieldCheck, 
  Package, 
  CreditCard, 
  FileText,
  Loader2,
  RefreshCw
} from 'lucide-react';

export default function CustomerDashboard() {
  const { user } = useAuth();
  const [dashboardData, setDashboardData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const fetchDashboard = async () => {
    setLoading(true);
    setError('');
    try {
      const data = await api.getCustomerDashboard();
      setDashboardData(data);
    } catch (err) {
      setError(err.message || 'Failed to load customer dashboard details.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboard();
  }, []);

  if (loading) {
    return (
      <div className="min-h-[70vh] flex flex-col items-center justify-center gap-3">
        <Loader2 className="w-8 h-8 text-brand-600 animate-spin" />
        <p className="text-sm text-slate-500 font-medium">Loading your personalized dashboard...</p>
      </div>
    );
  }

  const customer = dashboardData?.customer || user?.profile || {};
  const stats = dashboardData?.stats || {
    loyaltyPoints: customer.loyalty_points || 100,
    membershipTier: customer.membership_tier || 'Standard',
    activeOrders: 1,
    savedAddresses: 1
  };
  const activities = dashboardData?.activities || [];

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      
      {/* Top Welcome Banner */}
      <div className="relative rounded-3xl bg-gradient-to-r from-slate-900 via-brand-950 to-slate-900 text-white p-6 sm:p-8 overflow-hidden shadow-lg mb-8">
        {/* Glow */}
        <div className="absolute top-0 right-0 -mr-16 -mt-16 w-80 h-80 rounded-full bg-brand-500/20 blur-3xl pointer-events-none" />

        <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div>
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-brand-500/20 border border-brand-400/30 text-brand-300 text-xs font-semibold mb-3">
              <Sparkles className="w-3.5 h-3.5" />
              <span>Customer Portal Verified</span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight">
              Welcome back, {customer.full_name || 'Valued Customer'}!
            </h1>
            <p className="mt-1 text-sm text-slate-300 max-w-xl">
              Here is your BrightLoop summary, service overview, and customer loyalty rewards.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <Link
              to="/profile"
              className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-white text-slate-900 text-sm font-semibold hover:bg-slate-100 transition-colors shadow-sm"
            >
              <User className="w-4 h-4 text-brand-600" />
              <span>Manage Profile</span>
            </Link>
            <button
              onClick={fetchDashboard}
              className="inline-flex items-center gap-2 px-3.5 py-2.5 rounded-xl bg-slate-800/80 border border-slate-700 text-slate-300 text-sm font-medium hover:bg-slate-800 transition-colors"
              title="Refresh Dashboard"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Quick Metrics Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5 mb-8">
        
        {/* Loyalty Points */}
        <div className="p-5 rounded-2xl bg-white border border-slate-200 shadow-xs flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-brand-50 border border-brand-100 flex items-center justify-center text-brand-600 flex-shrink-0">
            <Award className="w-6 h-6" />
          </div>
          <div>
            <div className="text-xs font-medium text-slate-500 uppercase tracking-wider">Loyalty Points</div>
            <div className="text-2xl font-bold text-slate-900 mt-0.5">{stats.loyaltyPoints} pts</div>
          </div>
        </div>

        {/* Membership Tier */}
        <div className="p-5 rounded-2xl bg-white border border-slate-200 shadow-xs flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-amber-50 border border-amber-100 flex items-center justify-center text-amber-600 flex-shrink-0">
            <Sparkles className="w-6 h-6" />
          </div>
          <div>
            <div className="text-xs font-medium text-slate-500 uppercase tracking-wider">Membership Level</div>
            <div className="text-2xl font-bold text-amber-600 mt-0.5">{stats.membershipTier} Tier</div>
          </div>
        </div>

        {/* Active Requests */}
        <div className="p-5 rounded-2xl bg-white border border-slate-200 shadow-xs flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-indigo-50 border border-indigo-100 flex items-center justify-center text-indigo-600 flex-shrink-0">
            <Package className="w-6 h-6" />
          </div>
          <div>
            <div className="text-xs font-medium text-slate-500 uppercase tracking-wider">Active Services</div>
            <div className="text-2xl font-bold text-slate-900 mt-0.5">{stats.activeOrders} Active</div>
          </div>
        </div>

        {/* Account Status */}
        <div className="p-5 rounded-2xl bg-white border border-slate-200 shadow-xs flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-emerald-50 border border-emerald-100 flex items-center justify-center text-emerald-600 flex-shrink-0">
            <ShieldCheck className="w-6 h-6" />
          </div>
          <div>
            <div className="text-xs font-medium text-slate-500 uppercase tracking-wider">Account Status</div>
            <div className="text-2xl font-bold text-emerald-600 capitalize mt-0.5">Active</div>
          </div>
        </div>

      </div>

      {/* Main Two-Column Content: Customer Info & Activities */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Left Column: Customer Information Card */}
        <div className="lg:col-span-1 space-y-6">
          <div className="p-6 rounded-2xl bg-white border border-slate-200 shadow-xs">
            <div className="flex items-center justify-between pb-4 border-b border-slate-100 mb-4">
              <h2 className="text-base font-bold text-slate-900">Personal Information</h2>
              <Link to="/profile" className="text-xs font-semibold text-brand-600 hover:underline">
                Edit
              </Link>
            </div>

            <div className="space-y-3.5 text-sm">
              <div className="flex items-start gap-3">
                <User className="w-4 h-4 text-slate-400 mt-0.5 flex-shrink-0" />
                <div>
                  <div className="text-xs text-slate-500">Full Name</div>
                  <div className="font-medium text-slate-900">{customer.full_name || 'N/A'}</div>
                </div>
              </div>

              <div className="flex items-start gap-3">
                <Mail className="w-4 h-4 text-slate-400 mt-0.5 flex-shrink-0" />
                <div>
                  <div className="text-xs text-slate-500">Email Address</div>
                  <div className="font-medium text-slate-900">{customer.email || user.email}</div>
                </div>
              </div>

              <div className="flex items-start gap-3">
                <Phone className="w-4 h-4 text-slate-400 mt-0.5 flex-shrink-0" />
                <div>
                  <div className="text-xs text-slate-500">Contact Number</div>
                  <div className="font-medium text-slate-900">{customer.phone || 'Not provided yet'}</div>
                </div>
              </div>

              <div className="flex items-start gap-3">
                <MapPin className="w-4 h-4 text-slate-400 mt-0.5 flex-shrink-0" />
                <div>
                  <div className="text-xs text-slate-500">Registered Address</div>
                  <div className="font-medium text-slate-900">
                    {customer.address ? `${customer.address}, ${customer.city || ''} ${customer.postal_code || ''}` : 'No address saved'}
                  </div>
                </div>
              </div>

              <div className="flex items-start gap-3">
                <Clock className="w-4 h-4 text-slate-400 mt-0.5 flex-shrink-0" />
                <div>
                  <div className="text-xs text-slate-500">Customer Since</div>
                  <div className="font-medium text-slate-900">
                    {customer.account_created || customer.created_at 
                      ? new Date(customer.account_created || customer.created_at).toLocaleDateString()
                      : 'October 2026'}
                  </div>
                </div>
              </div>
            </div>

            <div className="mt-6 pt-4 border-t border-slate-100">
              <div className="p-3 rounded-xl bg-brand-50/70 border border-brand-100 text-xs text-brand-900 leading-relaxed">
                🎉 <strong>Loyalty Perk:</strong> As a {stats.membershipTier} member, you enjoy priority service response and bonus loyalty points on every engagement.
              </div>
            </div>
          </div>

          {/* Quick Action Buttons */}
          <div className="p-6 rounded-2xl bg-white border border-slate-200 shadow-xs">
            <h3 className="text-base font-bold text-slate-900 mb-4">Quick Actions</h3>
            <div className="space-y-2">
              <button
                type="button"
                onClick={() => alert('New Service Request dialog opened!')}
                className="w-full flex items-center justify-between p-3 rounded-xl border border-slate-200 hover:border-brand-300 hover:bg-brand-50/50 text-slate-700 hover:text-brand-700 text-sm font-medium transition-colors"
              >
                <span>Request New Smart Service</span>
                <ArrowRight className="w-4 h-4" />
              </button>
              <button
                type="button"
                onClick={() => alert('Invoices & Receipts view')}
                className="w-full flex items-center justify-between p-3 rounded-xl border border-slate-200 hover:border-brand-300 hover:bg-brand-50/50 text-slate-700 hover:text-brand-700 text-sm font-medium transition-colors"
              >
                <span>View Billing & Invoices</span>
                <ArrowRight className="w-4 h-4" />
              </button>
              <Link
                to="/profile"
                className="w-full flex items-center justify-between p-3 rounded-xl border border-slate-200 hover:border-brand-300 hover:bg-brand-50/50 text-slate-700 hover:text-brand-700 text-sm font-medium transition-colors"
              >
                <span>Security & Password Settings</span>
                <ArrowRight className="w-4 h-4" />
              </Link>
            </div>
          </div>
        </div>

        {/* Right Column: Recent Activity Feed & Service Status */}
        <div className="lg:col-span-2 space-y-6">
          
          {/* Active Services Overview */}
          <div className="p-6 rounded-2xl bg-white border border-slate-200 shadow-xs">
            <div className="flex items-center justify-between pb-4 border-b border-slate-100 mb-4">
              <div>
                <h2 className="text-base font-bold text-slate-900">Current Subscriptions & Services</h2>
                <p className="text-xs text-slate-500">Live overview of your enrolled BrightLoop modules</p>
              </div>
              <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800">
                1 Operational
              </span>
            </div>

            <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-brand-600 text-white flex items-center justify-center font-bold">
                  BL
                </div>
                <div>
                  <h4 className="text-sm font-bold text-slate-900">BrightLoop Intelligent Home & Energy Monitor</h4>
                  <p className="text-xs text-slate-500">Plan: Enterprise Standard · Billing: Active</p>
                </div>
              </div>
              <span className="px-3 py-1 rounded-lg bg-emerald-50 text-emerald-700 text-xs font-semibold border border-emerald-200">
                Connected & Active
              </span>
            </div>
          </div>

          {/* Activity Log */}
          <div className="p-6 rounded-2xl bg-white border border-slate-200 shadow-xs">
            <div className="flex items-center justify-between pb-4 border-b border-slate-100 mb-4">
              <h2 className="text-base font-bold text-slate-900">Recent Customer Activity</h2>
              <span className="text-xs text-slate-400">Past 30 days</span>
            </div>

            <div className="space-y-4">
              {activities.map((act) => (
                <div key={act.id} className="flex items-start gap-3.5 p-3.5 rounded-xl hover:bg-slate-50 transition-colors">
                  <div className="w-8 h-8 rounded-lg bg-slate-100 border border-slate-200 flex items-center justify-center text-slate-600 flex-shrink-0 mt-0.5">
                    <CheckCircle2 className="w-4 h-4 text-brand-600" />
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center justify-between">
                      <h4 className="text-sm font-semibold text-slate-900">{act.title}</h4>
                      <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-slate-100 text-slate-700">
                        {act.status}
                      </span>
                    </div>
                    <p className="text-xs text-slate-600 mt-1">{act.description}</p>
                    <span className="text-[11px] text-slate-400 block mt-1">{act.date}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

        </div>

      </div>

    </div>
  );
}
