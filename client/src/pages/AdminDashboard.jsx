import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { 
  ShieldCheck, 
  Users, 
  UserPlus, 
  Briefcase, 
  Database, 
  Search, 
  RefreshCw, 
  CheckCircle2, 
  AlertCircle, 
  Mail, 
  Lock, 
  Phone, 
  Tag, 
  Building2, 
  Loader2, 
  Layers,
  ChevronRight,
  Sparkles
} from 'lucide-react';

export default function AdminDashboard() {
  const { user } = useAuth();
  
  // Tab states: 'overview', 'staff', 'customers', 'tables'
  const [activeTab, setActiveTab] = useState('overview');
  
  // Data states
  const [dashboardData, setDashboardData] = useState(null);
  const [staffList, setStaffList] = useState([]);
  const [customerList, setCustomerList] = useState([]);
  const [dbTables, setDbTables] = useState({ Users: [], Customers: [], Staff: [] });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // Staff Registration Form Modal State (Admin only)
  const [showStaffModal, setShowStaffModal] = useState(false);
  const [staffForm, setStaffForm] = useState({
    full_name: '',
    email: '',
    password: '',
    department: 'Customer Support',
    position: 'Support Specialist',
    phone: '',
    employee_code: ''
  });
  const [staffLoading, setStaffLoading] = useState(false);
  const [staffError, setStaffError] = useState('');
  const [staffSuccess, setStaffSuccess] = useState('');

  const loadData = async () => {
    setLoading(true);
    setError('');
    try {
      const [dashRes, staffRes, custRes, tablesRes] = await Promise.all([
        api.getAdminDashboard(),
        api.getStaffList(),
        api.getCustomerList(),
        api.getDatabaseTables()
      ]);

      setDashboardData(dashRes);
      setStaffList(staffRes.staff || []);
      setCustomerList(custRes.customers || []);
      setDbTables(tablesRes.tables || { Users: [], Customers: [], Staff: [] });
    } catch (err) {
      setError(err.message || 'Failed to load administrative records.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleStaffChange = (e) => {
    setStaffForm(prev => ({
      ...prev,
      [e.target.name]: e.target.value
    }));
  };

  const handleRegisterStaff = async (e) => {
    e.preventDefault();
    setStaffError('');
    setStaffSuccess('');

    if (!staffForm.full_name || !staffForm.email || !staffForm.password) {
      setStaffError('Full name, email, and password are required for staff registration.');
      return;
    }

    if (staffForm.password.length < 6) {
      setStaffError('Password must be at least 6 characters long.');
      return;
    }

    setStaffLoading(true);
    try {
      const res = await api.registerStaff(staffForm);
      setStaffSuccess(res.message);
      // Reset form
      setStaffForm({
        full_name: '',
        email: '',
        password: '',
        department: 'Customer Support',
        position: 'Support Specialist',
        phone: '',
        employee_code: ''
      });
      // Reload admin data
      loadData();
      setTimeout(() => {
        setShowStaffModal(false);
        setStaffSuccess('');
      }, 2000);
    } catch (err) {
      setStaffError(err.message || 'Staff registration failed.');
    } finally {
      setStaffLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-[70vh] flex flex-col items-center justify-center gap-3">
        <Loader2 className="w-8 h-8 text-amber-600 animate-spin" />
        <p className="text-sm text-slate-500 font-medium">Accessing Admin Command Center...</p>
      </div>
    );
  }

  const metrics = dashboardData?.metrics || {
    totalUsers: 0,
    totalCustomers: 0,
    totalStaff: 0,
    activeUsers: 0
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      
      {/* Top Admin Banner */}
      <div className="relative rounded-3xl bg-gradient-to-r from-slate-900 via-amber-950/80 to-slate-900 text-white p-6 sm:p-8 overflow-hidden shadow-lg mb-8 border border-amber-900/40">
        <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div>
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-amber-500/20 border border-amber-400/30 text-amber-300 text-xs font-semibold mb-3">
              <ShieldCheck className="w-3.5 h-3.5" />
              <span>Administrator Privileges Active</span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight">
              Admin Command & Operations Center
            </h1>
            <p className="mt-1 text-sm text-slate-300 max-w-xl">
              Complete oversight across all Users, Customers, and authorized Staff members.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            {/* Staff Registration Trigger (Admin Only) */}
            <button
              onClick={() => { setShowStaffModal(true); setStaffError(''); setStaffSuccess(''); }}
              className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-amber-500 hover:bg-amber-600 text-slate-950 font-bold text-sm shadow-md transition-colors"
            >
              <UserPlus className="w-4 h-4" />
              <span>Register New Staff</span>
            </button>
            <button
              onClick={loadData}
              className="inline-flex items-center gap-2 px-3.5 py-2.5 rounded-xl bg-slate-800/80 border border-slate-700 text-slate-300 text-sm font-medium hover:bg-slate-800 transition-colors"
              title="Refresh Records"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5 mb-8">
        <div className="p-5 rounded-2xl bg-white border border-slate-200 shadow-xs flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-indigo-50 border border-indigo-100 flex items-center justify-center text-indigo-600">
            <Users className="w-6 h-6" />
          </div>
          <div>
            <div className="text-xs font-medium text-slate-500 uppercase tracking-wider">Total Users</div>
            <div className="text-2xl font-bold text-slate-900 mt-0.5">{metrics.totalUsers}</div>
          </div>
        </div>

        <div className="p-5 rounded-2xl bg-white border border-slate-200 shadow-xs flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-brand-50 border border-brand-100 flex items-center justify-center text-brand-600">
            <Users className="w-6 h-6" />
          </div>
          <div>
            <div className="text-xs font-medium text-slate-500 uppercase tracking-wider">Customers Registered</div>
            <div className="text-2xl font-bold text-slate-900 mt-0.5">{metrics.totalCustomers}</div>
          </div>
        </div>

        <div className="p-5 rounded-2xl bg-white border border-slate-200 shadow-xs flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-amber-50 border border-amber-100 flex items-center justify-center text-amber-600">
            <Briefcase className="w-6 h-6" />
          </div>
          <div>
            <div className="text-xs font-medium text-slate-500 uppercase tracking-wider">Staff Members</div>
            <div className="text-2xl font-bold text-slate-900 mt-0.5">{metrics.totalStaff}</div>
          </div>
        </div>

        <div className="p-5 rounded-2xl bg-white border border-slate-200 shadow-xs flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-emerald-50 border border-emerald-100 flex items-center justify-center text-emerald-600">
            <CheckCircle2 className="w-6 h-6" />
          </div>
          <div>
            <div className="text-xs font-medium text-slate-500 uppercase tracking-wider">Active System Accounts</div>
            <div className="text-2xl font-bold text-slate-900 mt-0.5">{metrics.activeUsers}</div>
          </div>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="border-b border-slate-200 mb-6">
        <nav className="flex space-x-6">
          <button
            onClick={() => setActiveTab('overview')}
            className={`pb-3 text-sm font-semibold border-b-2 transition-colors ${
              activeTab === 'overview'
                ? 'border-amber-600 text-amber-700'
                : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300'
            }`}
          >
            Overview & Quick Stats
          </button>
          <button
            onClick={() => setActiveTab('staff')}
            className={`pb-3 text-sm font-semibold border-b-2 transition-colors ${
              activeTab === 'staff'
                ? 'border-amber-600 text-amber-700'
                : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300'
            }`}
          >
            Staff Directory ({staffList.length})
          </button>
          <button
            onClick={() => setActiveTab('customers')}
            className={`pb-3 text-sm font-semibold border-b-2 transition-colors ${
              activeTab === 'customers'
                ? 'border-amber-600 text-amber-700'
                : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300'
            }`}
          >
            Customer Directory ({customerList.length})
          </button>
          <button
            onClick={() => setActiveTab('tables')}
            className={`pb-3 text-sm font-semibold border-b-2 transition-colors ${
              activeTab === 'tables'
                ? 'border-amber-600 text-amber-700'
                : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300'
            }`}
          >
            Database Tables Inspector
          </button>
        </nav>
      </div>

      {/* TAB 1: OVERVIEW */}
      {activeTab === 'overview' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          
          {/* Recent Customers List */}
          <div className="p-6 rounded-2xl bg-white border border-slate-200 shadow-xs">
            <div className="flex items-center justify-between pb-4 border-b border-slate-100 mb-4">
              <h3 className="font-bold text-slate-900">Recent Customer Registrations</h3>
              <button onClick={() => setActiveTab('customers')} className="text-xs text-amber-600 font-semibold hover:underline">
                View All
              </button>
            </div>
            <div className="space-y-3">
              {customerList.slice(0, 5).map(c => (
                <div key={c.id} className="p-3 rounded-xl bg-slate-50 border border-slate-200/60 flex items-center justify-between">
                  <div>
                    <h4 className="text-sm font-semibold text-slate-900">{c.full_name}</h4>
                    <p className="text-xs text-slate-500">{c.email} · {c.city || 'Location N/A'}</p>
                  </div>
                  <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-brand-50 text-brand-700 border border-brand-200">
                    {c.membership_tier} Tier
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Recent Staff Members List */}
          <div className="p-6 rounded-2xl bg-white border border-slate-200 shadow-xs">
            <div className="flex items-center justify-between pb-4 border-b border-slate-100 mb-4">
              <h3 className="font-bold text-slate-900">Registered Staff Members</h3>
              <button onClick={() => setActiveTab('staff')} className="text-xs text-amber-600 font-semibold hover:underline">
                View All
              </button>
            </div>
            <div className="space-y-3">
              {staffList.slice(0, 5).map(s => (
                <div key={s.id} className="p-3 rounded-xl bg-slate-50 border border-slate-200/60 flex items-center justify-between">
                  <div>
                    <div className="flex items-center gap-2">
                      <h4 className="text-sm font-semibold text-slate-900">{s.full_name}</h4>
                      <span className="text-[10px] font-mono font-bold px-1.5 py-0.5 bg-slate-200 text-slate-700 rounded">
                        {s.employee_code}
                      </span>
                    </div>
                    <p className="text-xs text-slate-500">{s.position} ({s.department})</p>
                  </div>
                  <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-amber-50 text-amber-700 border border-amber-200">
                    Staff
                  </span>
                </div>
              ))}
            </div>
          </div>

        </div>
      )}

      {/* TAB 2: STAFF DIRECTORY */}
      {activeTab === 'staff' && (
        <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
          <div className="p-5 border-b border-slate-100 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <h3 className="font-bold text-slate-900">Staff Members (Admin Only Provisioning)</h3>
              <p className="text-xs text-slate-500">Only administrators are permitted to register and assign staff credentials.</p>
            </div>
            <button
              onClick={() => { setShowStaffModal(true); setStaffError(''); setStaffSuccess(''); }}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-amber-500 hover:bg-amber-600 text-slate-950 font-bold text-xs shadow-xs"
            >
              <UserPlus className="w-3.5 h-3.5" />
              <span>Add New Staff</span>
            </button>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-sm">
              <thead>
                <tr className="bg-slate-50/80 border-b border-slate-200 text-xs font-bold text-slate-600 uppercase tracking-wider">
                  <th className="py-3 px-4">Code</th>
                  <th className="py-3 px-4">Staff Name</th>
                  <th className="py-3 px-4">Email</th>
                  <th className="py-3 px-4">Department & Position</th>
                  <th className="py-3 px-4">Phone</th>
                  <th className="py-3 px-4">Created By</th>
                  <th className="py-3 px-4">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {staffList.map(s => (
                  <tr key={s.id} className="hover:bg-slate-50/50 transition-colors">
                    <td className="py-3 px-4 font-mono font-bold text-xs text-slate-700">{s.employee_code}</td>
                    <td className="py-3 px-4 font-semibold text-slate-900">{s.full_name}</td>
                    <td className="py-3 px-4 text-slate-600 text-xs">{s.email}</td>
                    <td className="py-3 px-4 text-slate-700">
                      <div>{s.position}</div>
                      <div className="text-xs text-slate-400">{s.department}</div>
                    </td>
                    <td className="py-3 px-4 text-slate-600 text-xs">{s.phone || '—'}</td>
                    <td className="py-3 px-4 text-slate-500 text-xs">{s.created_by_admin || 'System Admin'}</td>
                    <td className="py-3 px-4">
                      <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                        {s.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* TAB 3: CUSTOMER DIRECTORY */}
      {activeTab === 'customers' && (
        <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
          <div className="p-5 border-b border-slate-100">
            <h3 className="font-bold text-slate-900">Registered Customers</h3>
            <p className="text-xs text-slate-500">Customers registered via self-service onboarding or admin registration.</p>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-sm">
              <thead>
                <tr className="bg-slate-50/80 border-b border-slate-200 text-xs font-bold text-slate-600 uppercase tracking-wider">
                  <th className="py-3 px-4">ID</th>
                  <th className="py-3 px-4">Customer Name</th>
                  <th className="py-3 px-4">Email</th>
                  <th className="py-3 px-4">Location</th>
                  <th className="py-3 px-4">Phone</th>
                  <th className="py-3 px-4">Membership</th>
                  <th className="py-3 px-4">Points</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {customerList.map(c => (
                  <tr key={c.id} className="hover:bg-slate-50/50 transition-colors">
                    <td className="py-3 px-4 font-mono text-xs text-slate-400">#{c.id}</td>
                    <td className="py-3 px-4 font-semibold text-slate-900">{c.full_name}</td>
                    <td className="py-3 px-4 text-slate-600 text-xs">{c.email}</td>
                    <td className="py-3 px-4 text-slate-700 text-xs">
                      {c.city ? `${c.city}${c.postal_code ? ` (${c.postal_code})` : ''}` : '—'}
                    </td>
                    <td className="py-3 px-4 text-slate-600 text-xs">{c.phone || '—'}</td>
                    <td className="py-3 px-4">
                      <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-brand-50 text-brand-700 border border-brand-200">
                        {c.membership_tier}
                      </span>
                    </td>
                    <td className="py-3 px-4 font-bold text-slate-800">{c.loyalty_points}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* TAB 4: DATABASE TABLES INSPECTOR (Users, Customers, Staff) */}
      {activeTab === 'tables' && (
        <div className="space-y-8">
          
          {/* 1. Users Table */}
          <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
            <div className="p-4 bg-slate-900 text-white flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Database className="w-4 h-4 text-amber-400" />
                <span className="font-bold text-sm tracking-wide">Table: Users</span>
                <span className="text-xs text-slate-400 font-mono">({dbTables.Users.length} records)</span>
              </div>
              <span className="text-xs text-slate-400 font-mono">SQL: SELECT * FROM Users</span>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs font-mono">
                <thead className="bg-slate-100 border-b border-slate-200">
                  <tr>
                    <th className="p-3">id</th>
                    <th className="p-3">email</th>
                    <th className="p-3">role</th>
                    <th className="p-3">status</th>
                    <th className="p-3">last_login</th>
                    <th className="p-3">created_at</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {dbTables.Users.map(u => (
                    <tr key={u.id} className="hover:bg-slate-50">
                      <td className="p-3 font-bold">{u.id}</td>
                      <td className="p-3 text-slate-800 font-medium">{u.email}</td>
                      <td className="p-3">
                        <span className={`px-2 py-0.5 rounded font-bold uppercase text-[10px] ${
                          u.role === 'admin' ? 'bg-amber-100 text-amber-800' : u.role === 'staff' ? 'bg-indigo-100 text-indigo-800' : 'bg-emerald-100 text-emerald-800'
                        }`}>
                          {u.role}
                        </span>
                      </td>
                      <td className="p-3 text-emerald-600 font-bold">{u.status}</td>
                      <td className="p-3 text-slate-500">{u.last_login || 'Never'}</td>
                      <td className="p-3 text-slate-400">{u.created_at}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* 2. Customers Table */}
          <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
            <div className="p-4 bg-slate-900 text-white flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Database className="w-4 h-4 text-brand-400" />
                <span className="font-bold text-sm tracking-wide">Table: Customers</span>
                <span className="text-xs text-slate-400 font-mono">({dbTables.Customers.length} records)</span>
              </div>
              <span className="text-xs text-slate-400 font-mono">SQL: SELECT * FROM Customers</span>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs font-mono">
                <thead className="bg-slate-100 border-b border-slate-200">
                  <tr>
                    <th className="p-3">id</th>
                    <th className="p-3">user_id (FK)</th>
                    <th className="p-3">full_name</th>
                    <th className="p-3">phone</th>
                    <th className="p-3">city</th>
                    <th className="p-3">tier</th>
                    <th className="p-3">loyalty_points</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {dbTables.Customers.map(c => (
                    <tr key={c.id} className="hover:bg-slate-50">
                      <td className="p-3 font-bold">{c.id}</td>
                      <td className="p-3 text-indigo-600 font-bold">{c.user_id}</td>
                      <td className="p-3 text-slate-800 font-medium">{c.full_name}</td>
                      <td className="p-3 text-slate-500">{c.phone || 'null'}</td>
                      <td className="p-3 text-slate-600">{c.city || 'null'}</td>
                      <td className="p-3 text-amber-600 font-bold">{c.membership_tier}</td>
                      <td className="p-3 text-brand-700 font-bold">{c.loyalty_points}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* 3. Staff Table */}
          <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
            <div className="p-4 bg-slate-900 text-white flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Database className="w-4 h-4 text-indigo-400" />
                <span className="font-bold text-sm tracking-wide">Table: Staff</span>
                <span className="text-xs text-slate-400 font-mono">({dbTables.Staff.length} records)</span>
              </div>
              <span className="text-xs text-slate-400 font-mono">SQL: SELECT * FROM Staff</span>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs font-mono">
                <thead className="bg-slate-100 border-b border-slate-200">
                  <tr>
                    <th className="p-3">id</th>
                    <th className="p-3">user_id (FK)</th>
                    <th className="p-3">employee_code</th>
                    <th className="p-3">full_name</th>
                    <th className="p-3">department</th>
                    <th className="p-3">position</th>
                    <th className="p-3">created_by (Admin FK)</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {dbTables.Staff.map(s => (
                    <tr key={s.id} className="hover:bg-slate-50">
                      <td className="p-3 font-bold">{s.id}</td>
                      <td className="p-3 text-indigo-600 font-bold">{s.user_id}</td>
                      <td className="p-3 text-amber-600 font-bold">{s.employee_code}</td>
                      <td className="p-3 text-slate-800 font-medium">{s.full_name}</td>
                      <td className="p-3 text-slate-600">{s.department}</td>
                      <td className="p-3 text-slate-700">{s.position}</td>
                      <td className="p-3 text-slate-500 font-bold">{s.created_by}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

        </div>
      )}

      {/* STAFF REGISTRATION MODAL (Admin Only) */}
      {showStaffModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs">
          <div className="w-full max-w-lg bg-white rounded-2xl border border-slate-200 shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-150">
            
            <div className="p-5 bg-gradient-to-r from-amber-600 to-amber-700 text-white flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <ShieldCheck className="w-6 h-6" />
                <div>
                  <h3 className="font-bold text-lg">Staff Registration</h3>
                  <p className="text-xs text-amber-100">Admin-only operation to provision internal staff accounts</p>
                </div>
              </div>
              <button
                onClick={() => setShowStaffModal(false)}
                className="w-8 h-8 rounded-lg bg-amber-800/40 text-amber-100 flex items-center justify-center hover:bg-amber-800/60 transition-colors"
              >
                ✕
              </button>
            </div>

            <div className="p-6">
              {staffError && (
                <div className="mb-4 p-3 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-xs flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 flex-shrink-0" />
                  <span>{staffError}</span>
                </div>
              )}

              {staffSuccess && (
                <div className="mb-4 p-3 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 flex-shrink-0 text-emerald-600" />
                  <span>{staffSuccess}</span>
                </div>
              )}

              <form onSubmit={handleRegisterStaff} className="space-y-4">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">
                      Staff Full Name *
                    </label>
                    <input
                      type="text"
                      name="full_name"
                      value={staffForm.full_name}
                      onChange={handleStaffChange}
                      placeholder="e.g. David Miller"
                      required
                      className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-amber-500 focus:outline-none"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">
                      Staff Email Address *
                    </label>
                    <input
                      type="email"
                      name="email"
                      value={staffForm.email}
                      onChange={handleStaffChange}
                      placeholder="david@brightloop.com"
                      required
                      className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-amber-500 focus:outline-none"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">
                      Department *
                    </label>
                    <select
                      name="department"
                      value={staffForm.department}
                      onChange={handleStaffChange}
                      className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-amber-500 focus:outline-none"
                    >
                      <option value="Customer Support">Customer Support</option>
                      <option value="Engineering & IT">Engineering & IT</option>
                      <option value="Operations">Operations</option>
                      <option value="Sales & Accounts">Sales & Accounts</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">
                      Position / Title *
                    </label>
                    <input
                      type="text"
                      name="position"
                      value={staffForm.position}
                      onChange={handleStaffChange}
                      placeholder="e.g. Support Specialist"
                      required
                      className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-amber-500 focus:outline-none"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">
                      Temporary Password *
                    </label>
                    <input
                      type="password"
                      name="password"
                      value={staffForm.password}
                      onChange={handleStaffChange}
                      placeholder="Min. 6 chars"
                      required
                      className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-amber-500 focus:outline-none"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">
                      Employee Code (Optional)
                    </label>
                    <input
                      type="text"
                      name="employee_code"
                      value={staffForm.employee_code}
                      onChange={handleStaffChange}
                      placeholder="Auto if empty (e.g. BL-STF-002)"
                      className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-amber-500 focus:outline-none"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">
                    Phone Number
                  </label>
                  <input
                    type="tel"
                    name="phone"
                    value={staffForm.phone}
                    onChange={handleStaffChange}
                    placeholder="+1 (555) 000-0000"
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-amber-500 focus:outline-none"
                  />
                </div>

                <div className="pt-3 flex items-center justify-end gap-3 border-t border-slate-100">
                  <button
                    type="button"
                    onClick={() => setShowStaffModal(false)}
                    className="px-4 py-2 border border-slate-300 rounded-xl text-slate-700 text-sm font-medium hover:bg-slate-50"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={staffLoading}
                    className="flex items-center gap-2 px-5 py-2 rounded-xl bg-amber-600 hover:bg-amber-700 text-white font-bold text-sm shadow-md transition-all disabled:opacity-50"
                  >
                    {staffLoading ? (
                      <>
                        <Loader2 className="w-4 h-4 animate-spin" />
                        <span>Creating Staff Record...</span>
                      </>
                    ) : (
                      <>
                        <UserPlus className="w-4 h-4" />
                        <span>Register Staff</span>
                      </>
                    )}
                  </button>
                </div>
              </form>
            </div>

          </div>
        </div>
      )}

    </div>
  );
}
