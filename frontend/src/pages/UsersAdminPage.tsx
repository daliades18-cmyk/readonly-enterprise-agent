import React, { useState, useEffect } from 'react';
import {
  Users,
  Shield,
  CheckCircle2,
  XCircle,
  Edit3,
  Search,
  RefreshCw,
  Loader2,
  AlertCircle,
  Building,
  Calendar,
  Globe,
  Lock,
  Save,
  X,
  UserCheck,
} from 'lucide-react';
import { AdminUser, UserPersona } from '../types/api';
import { fetchAdminUsers, updateUserPermissions, updateUserStatus } from '../api/client';

interface UsersAdminPageProps {
  token: string | null;
  currentUser: UserPersona | null;
}

const AVAILABLE_ROLES = [
  { key: 'finance', label: 'Finance', desc: 'Access to ERP Invoices, revenue breakdown, and financial queries' },
  { key: 'procurement', label: 'Procurement', desc: 'Access to ERP Purchase Orders and supplier contract POs' },
  { key: 'operations', label: 'Operations', desc: 'Access to system incidents, outages, and telemetry metrics' },
  { key: 'sales', label: 'Sales', desc: 'Access to commercial pricing policy and discount approvals' },
  { key: 'support', label: 'Support', desc: 'Customer support refunds, policy guidance, and ticket resolution' },
  { key: 'admin', label: 'Administrator', desc: 'System governance, role assignment, and database inspection' },
];

const AVAILABLE_REGIONS = [
  { key: 'EMEA', label: 'EMEA (Europe, Middle East, Africa)' },
  { key: 'NA', label: 'NA (North America)' },
  { key: 'APAC', label: 'APAC (Asia-Pacific)' },
];

export const UsersAdminPage: React.FC<UsersAdminPageProps> = ({ token, currentUser }) => {
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');

  // Editing state
  const [editingUser, setEditingUser] = useState<AdminUser | null>(null);
  const [selectedRoles, setSelectedRoles] = useState<string[]>([]);
  const [selectedRegions, setSelectedRegions] = useState<string[]>([]);
  const [isSaving, setIsSaving] = useState(false);

  // Security Invariant: Strict non-admin guard
  if (!currentUser?.roles.includes('admin')) {
    return (
      <div className="flex-1 flex items-center justify-center p-8 bg-slate-950 text-slate-400">
        <div className="p-8 rounded-2xl border border-rose-900/40 bg-rose-950/20 text-center max-w-md space-y-3">
          <Shield className="w-12 h-12 text-rose-500 mx-auto" />
          <h2 className="text-base font-bold text-white">Access Denied: Administrator Only</h2>
          <p className="text-xs text-slate-400">
            User Governance is restricted strictly to enterprise administrators. Your persona (@{currentUser?.username || 'user'}) does not hold the admin role.
          </p>
        </div>
      </div>
    );
  }

  const loadUsers = async () => {
    setLoading(true);
    setError(null);
    try {
      const list = await fetchAdminUsers(token);
      setUsers(list);
    } catch (err: any) {
      setError(err.message || 'Failed to load enterprise users');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadUsers();
  }, [token]);

  const startEdit = (user: AdminUser) => {
    setEditingUser(user);
    setSelectedRoles([...user.roles]);
    setSelectedRegions([...user.regions]);
    setSuccessMsg(null);
  };

  const handleToggleRole = (roleKey: string) => {
    if (selectedRoles.includes(roleKey)) {
      setSelectedRoles(selectedRoles.filter((r) => r !== roleKey));
    } else {
      setSelectedRoles([...selectedRoles, roleKey]);
    }
  };

  const handleToggleRegion = (regionKey: string) => {
    if (selectedRegions.includes(regionKey)) {
      if (selectedRegions.length === 1) return; // Must have at least 1 region
      setSelectedRegions(selectedRegions.filter((r) => r !== regionKey));
    } else {
      setSelectedRegions([...selectedRegions, regionKey]);
    }
  };

  const handleSavePermissions = async () => {
    if (!editingUser) return;
    setIsSaving(true);
    setError(null);
    try {
      await updateUserPermissions(editingUser.id, selectedRoles, selectedRegions, token);
      setSuccessMsg(`Permissions updated for ${editingUser.email} in estate.db.`);
      setEditingUser(null);
      await loadUsers();
    } catch (err: any) {
      setError(err.message || 'Failed to update permissions');
    } finally {
      setIsSaving(false);
    }
  };

  const handleToggleStatus = async (user: AdminUser) => {
    try {
      await updateUserStatus(user.id, !user.is_active, token);
      setSuccessMsg(`Account for ${user.email} ${!user.is_active ? 'enabled' : 'disabled'}.`);
      await loadUsers();
    } catch (err: any) {
      setError(err.message || 'Failed to toggle account status');
    }
  };

  const filteredUsers = users.filter((u) => {
    const q = searchQuery.toLowerCase();
    return (
      u.email.toLowerCase().includes(q) ||
      u.username.toLowerCase().includes(q) ||
      u.department.toLowerCase().includes(q) ||
      u.roles.some((r) => r.toLowerCase().includes(q)) ||
      u.regions.some((reg) => reg.toLowerCase().includes(q))
    );
  });

  return (
    <div className="flex-1 flex flex-col h-full bg-slate-950 text-slate-100 overflow-hidden">
      {/* Header */}
      <header className="p-6 border-b border-slate-800 bg-slate-900/40 backdrop-blur-md flex flex-wrap items-center justify-between gap-4 shrink-0">
        <div>
          <div className="flex items-center space-x-2">
            <div className="p-2 rounded-xl bg-purple-500/10 text-purple-400 border border-purple-500/20">
              <Shield className="w-5 h-5" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-white flex items-center gap-2">
                Enterprise Access Governance
                <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-purple-950 text-purple-300 border border-purple-800/50">
                  Admin Only
                </span>
              </h1>
              <p className="text-xs text-slate-400">
                Manage registered user accounts, assign enterprise roles (Finance, Procurement, Sales), and authorize regional access.
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center space-x-3">
          <button
            onClick={loadUsers}
            disabled={loading}
            className="flex items-center space-x-1.5 px-3 py-2 rounded-xl text-xs font-semibold bg-slate-900 border border-slate-800 hover:bg-slate-800 text-slate-300 transition-colors"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
        </div>
      </header>

      {/* Main Content */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {/* Status Alerts */}
        {error && (
          <div className="p-4 rounded-xl border border-rose-900/60 bg-rose-950/40 text-xs text-rose-300 flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
              <span>{error}</span>
            </div>
            <button onClick={() => setError(null)}><X className="w-4 h-4 text-rose-400" /></button>
          </div>
        )}

        {successMsg && (
          <div className="p-4 rounded-xl border border-emerald-900/60 bg-emerald-950/40 text-xs text-emerald-300 flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
              <span>{successMsg}</span>
            </div>
            <button onClick={() => setSuccessMsg(null)}><X className="w-4 h-4 text-emerald-400" /></button>
          </div>
        )}

        {/* Overview Stats */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="p-4 rounded-xl border border-slate-800 bg-slate-900/50">
            <div className="text-xs text-slate-400 font-medium">Total Registered Users</div>
            <div className="text-2xl font-black text-white mt-1">{users.length}</div>
            <div className="text-[11px] text-slate-400 mt-0.5">Persisted in SQLite <code className="text-slate-300">users</code> table</div>
          </div>
          <div className="p-4 rounded-xl border border-slate-800 bg-slate-900/50">
            <div className="text-xs text-slate-400 font-medium">Elevated Permission Holders</div>
            <div className="text-2xl font-black text-sky-400 mt-1">
              {users.filter((u) => u.roles.some((r) => ['finance', 'procurement', 'sales', 'admin'].includes(r))).length}
            </div>
            <div className="text-[11px] text-slate-400 mt-0.5">Hold specialized department roles</div>
          </div>
          <div className="p-4 rounded-xl border border-slate-800 bg-slate-900/50">
            <div className="text-xs text-slate-400 font-medium">Active Accounts</div>
            <div className="text-2xl font-black text-emerald-400 mt-1">
              {users.filter((u) => u.is_active).length}
            </div>
            <div className="text-[11px] text-slate-400 mt-0.5">Permitted to sign in and query</div>
          </div>
        </div>

        {/* Search Bar */}
        <div className="flex items-center justify-between">
          <div className="relative w-full max-w-sm">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search by email, username, role, or region..."
              className="w-full bg-slate-900 border border-slate-800 rounded-xl pl-9 pr-4 py-2 text-xs text-white placeholder-slate-400 focus:outline-none focus:border-sky-500"
            />
          </div>
          <div className="text-xs text-slate-400">
            Showing <span className="font-semibold text-white">{filteredUsers.length}</span> of {users.length} accounts
          </div>
        </div>

        {/* Users Table */}
        <div className="rounded-xl border border-slate-800 bg-slate-900/40 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-950/80 border-b border-slate-800 text-slate-400 font-semibold uppercase tracking-wider text-[10px]">
                <tr>
                  <th className="py-3 px-4">User</th>
                  <th className="py-3 px-4">Department</th>
                  <th className="py-3 px-4">Assigned Roles</th>
                  <th className="py-3 px-4">Regional Reach</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-sans">
                {loading ? (
                  <tr>
                    <td colSpan={6} className="py-12 text-center text-slate-400">
                      <Loader2 className="w-6 h-6 animate-spin mx-auto mb-2 text-sky-400" />
                      Loading users from real database...
                    </td>
                  </tr>
                ) : filteredUsers.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="py-12 text-center text-slate-400">
                      No matching user accounts found.
                    </td>
                  </tr>
                ) : (
                  filteredUsers.map((user) => (
                    <tr key={user.id} className="hover:bg-slate-800/30 transition-colors">
                      <td className="py-3 px-4">
                        <div className="font-bold text-white">{user.email}</div>
                        <div className="text-[11px] text-slate-400 font-mono">@{user.username}</div>
                      </td>
                      <td className="py-3 px-4">
                        <span className="inline-flex items-center text-slate-300">
                          <Building className="w-3 h-3 mr-1 text-slate-400" />
                          {user.department || 'General'}
                        </span>
                      </td>
                      <td className="py-3 px-4">
                        <div className="flex flex-wrap gap-1">
                          {user.roles.map((r) => (
                            <span
                              key={r}
                              className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                                r === 'admin'
                                  ? 'bg-purple-950 text-purple-300 border border-purple-800/50'
                                  : r === 'finance'
                                  ? 'bg-emerald-950 text-emerald-300 border border-emerald-800/50'
                                  : r === 'procurement'
                                  ? 'bg-amber-950 text-amber-300 border border-amber-800/50'
                                  : r === 'sales'
                                  ? 'bg-blue-950 text-blue-300 border border-blue-800/50'
                                  : 'bg-slate-800 text-slate-300'
                              }`}
                            >
                              {r}
                            </span>
                          ))}
                        </div>
                      </td>
                      <td className="py-3 px-4">
                        <div className="flex flex-wrap gap-1">
                          {user.regions.map((reg) => (
                            <span
                              key={reg}
                              className="px-2 py-0.5 rounded text-[10px] font-bold bg-sky-950 text-sky-300 border border-sky-800/40"
                            >
                              {reg}
                            </span>
                          ))}
                        </div>
                      </td>
                      <td className="py-3 px-4">
                        <button
                          onClick={() => handleToggleStatus(user)}
                          className={`inline-flex items-center px-2 py-1 rounded-full text-[10px] font-semibold transition-colors ${
                            user.is_active
                              ? 'bg-emerald-950/80 text-emerald-300 hover:bg-emerald-900'
                              : 'bg-rose-950/80 text-rose-300 hover:bg-rose-900'
                          }`}
                        >
                          {user.is_active ? (
                            <>
                              <CheckCircle2 className="w-3 h-3 mr-1 text-emerald-400" />
                              Active
                            </>
                          ) : (
                            <>
                              <XCircle className="w-3 h-3 mr-1 text-rose-400" />
                              Disabled
                            </>
                          )}
                        </button>
                      </td>
                      <td className="py-3 px-4 text-right">
                        <button
                          onClick={() => startEdit(user)}
                          className="inline-flex items-center space-x-1 px-3 py-1.5 rounded-lg text-xs font-semibold bg-sky-600/20 text-sky-300 border border-sky-500/30 hover:bg-sky-600/30 transition-colors"
                        >
                          <Edit3 className="w-3 h-3 mr-1" />
                          <span>Assign Roles</span>
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Permission Assignment Modal */}
      {editingUser && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="w-full max-w-xl rounded-2xl border border-slate-800 bg-slate-900 p-6 shadow-2xl space-y-5">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center space-x-2">
                <div className="p-2 rounded-xl bg-sky-500/10 text-sky-400 border border-sky-500/20">
                  <UserCheck className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-white">Assign Enterprise Permissions</h3>
                  <p className="text-xs text-slate-400">{editingUser.email} (@{editingUser.username})</p>
                </div>
              </div>
              <button
                onClick={() => setEditingUser(null)}
                className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Roles Selection */}
            <div className="space-y-2">
              <label className="text-xs font-bold text-slate-300 uppercase tracking-wider block">
                Enterprise Roles
              </label>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                {AVAILABLE_ROLES.map((r) => {
                  const isChecked = selectedRoles.includes(r.key);
                  return (
                    <label
                      key={r.key}
                      onClick={() => handleToggleRole(r.key)}
                      className={`p-3 rounded-xl border cursor-pointer transition-all flex items-start space-x-3 ${
                        isChecked
                          ? 'border-sky-500 bg-sky-950/30 text-white'
                          : 'border-slate-800 bg-slate-950/60 text-slate-400 hover:border-slate-700'
                      }`}
                    >
                      <input
                        type="checkbox"
                        checked={isChecked}
                        onChange={() => {}}
                        className="mt-0.5 rounded border-slate-700 text-sky-600 focus:ring-0"
                      />
                      <div className="text-xs">
                        <div className="font-bold text-white capitalize">{r.label}</div>
                        <div className="text-[11px] text-slate-400 leading-snug mt-0.5">{r.desc}</div>
                      </div>
                    </label>
                  );
                })}
              </div>
            </div>

            {/* Regions Selection */}
            <div className="space-y-2">
              <label className="text-xs font-bold text-slate-300 uppercase tracking-wider block">
                Authorized Regional Reach
              </label>
              <div className="grid grid-cols-3 gap-2">
                {AVAILABLE_REGIONS.map((reg) => {
                  const isChecked = selectedRegions.includes(reg.key);
                  return (
                    <label
                      key={reg.key}
                      onClick={() => handleToggleRegion(reg.key)}
                      className={`p-2.5 rounded-xl border cursor-pointer text-center text-xs font-bold transition-all ${
                        isChecked
                          ? 'border-sky-500 bg-sky-950/40 text-sky-300'
                          : 'border-slate-800 bg-slate-950/60 text-slate-400 hover:border-slate-700'
                      }`}
                    >
                      {reg.key}
                    </label>
                  );
                })}
              </div>
            </div>

            {/* Security Notice */}
            <div className="p-3 rounded-xl border border-sky-900/30 bg-sky-950/20 text-[11px] text-slate-300 flex items-start space-x-2">
              <Lock className="w-4 h-4 text-sky-400 shrink-0 mt-0.5" />
              <span>
                Changes are written directly to the SQLite <code className="text-slate-200">users</code> table. When this user authenticates or makes their next query, the backend will sign a fresh RS256 JWT containing these exact claims.
              </span>
            </div>

            {/* Modal Actions */}
            <div className="flex items-center justify-end space-x-3 pt-2">
              <button
                type="button"
                onClick={() => setEditingUser(null)}
                className="px-4 py-2 rounded-xl text-xs font-semibold bg-slate-800 text-slate-300 hover:bg-slate-700"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleSavePermissions}
                disabled={isSaving}
                className="px-4 py-2 rounded-xl text-xs font-bold bg-sky-600 text-white hover:bg-sky-500 disabled:opacity-50 flex items-center space-x-1.5 shadow-lg shadow-sky-600/20"
              >
                {isSaving ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 animate-spin mr-1" />
                    <span>Saving to Database...</span>
                  </>
                ) : (
                  <>
                    <Save className="w-3.5 h-3.5 mr-1" />
                    <span>Save & Update Entitlements</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
