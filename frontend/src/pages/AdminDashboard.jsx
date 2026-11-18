import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  Ticket,
  Clock,
  CheckCircle2,
  AlertTriangle,
  Users,
  ShieldCheck,
  Star,
  FileSpreadsheet,
  Layers,
  TrendingUp,
  Building,
  ShieldAlert,
  Award,
  RefreshCw,
  Zap
} from 'lucide-react';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  BarChart,
  Bar,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend
} from 'recharts';
import { analyticsService, staffPerformanceService } from '../api/services';
import StatCard from '../components/StatCard';

const COLORS = ['var(--brand-blue)', '#10B981', '#F59E0B', '#8B5CF6', '#EC4899', '#3B82F6', '#14B8A6', '#6366F1'];

export default function AdminDashboard() {
  const [data, setData] = useState(null);
  const [staffPerf, setStaffPerf] = useState(null);
  const [loading, setLoading] = useState(true);
  const [perfLoading, setPerfLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchAll = async () => {
      try {
        const res = await analyticsService.getDashboardMetrics();
        setData(res.data);
        setError('');
      } catch (err) {
        console.error("Failed to fetch analytics:", err);
        setError(err.response?.data?.detail || 'Analytics could not be loaded. Check the API connection and try again.');
      } finally {
        setLoading(false);
      }
      // Load staff performance separately (non-blocking)
      try {
        const perfRes = await staffPerformanceService.getOverview();
        setStaffPerf(perfRes.data);
      } catch (err) {
        console.warn("Staff performance overview unavailable:", err);
      }
    };
    fetchAll();
  }, []);

  const refreshStaffPerf = async () => {
    setPerfLoading(true);
    try {
      const perfRes = await staffPerformanceService.getOverview();
      setStaffPerf(perfRes.data);
    } catch (err) {
      console.warn("Staff performance refresh failed:", err);
    } finally {
      setPerfLoading(false);
    }
  };

  const handleTriggerSlaCheck = async () => {
    setPerfLoading(true);
    try {
      const checkRes = await staffPerformanceService.triggerSlaCheck();
      const count = checkRes.data?.warnings_issued_count || 0;
      alert(count > 0 ? `SLA Check: ${count} warning ticket(s) issued against assigned staff.` : 'SLA Check: All tickets are currently within SLA or grace periods.');
      await refreshStaffPerf();
    } catch (err) {
      alert("Failed to run SLA check");
    } finally {
      setPerfLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="page-wrapper" style={{ textAlign: 'center', padding: '4rem' }}>
        <p style={{ color: 'var(--text-muted)' }}>Loading real-time campus IT analytics...</p>
      </div>
    );
  }

  if (error && !data) {
    return (
      <div className="page-wrapper">
        <div className="page-header"><div><h1 className="page-title">Campus IT Operations</h1><p className="page-subtitle">Executive overview and service performance</p></div></div>
        <div className="card" role="alert"><h2 style={{ marginBottom: '0.5rem' }}>Analytics unavailable</h2><p style={{ color: 'var(--text-muted)', marginBottom: '1rem' }}>{error}</p><button className="btn btn-primary" onClick={() => window.location.reload()}>Retry</button></div>
      </div>
    );
  }

  const kpis = data?.kpis || {};
  const charts = data?.charts || {};

  return (
    <div className="page-wrapper">
      <div className="page-header">
        <div>
          <h1 className="page-title">Campus IT Operations & Executive Analytics</h1>
          <p className="page-subtitle">Centralized oversight of college helpdesk workload, SLA performance, and infrastructure health</p>
        </div>
        <div style={{ display: 'flex', gap: '0.75rem' }}>
          <Link to="/reports" className="btn btn-secondary">
            <FileSpreadsheet size={16} /> Export Reports
          </Link>
          <Link to="/tickets" className="btn btn-navy">
            Manage All Tickets
          </Link>
          <Link to="/admin/administrators" className="btn btn-secondary">
            <ShieldCheck size={16} /> Invite Administrators
          </Link>
        </div>
      </div>

      {/* Primary KPI Row */}
      <div className="grid-4" style={{ marginBottom: '1.25rem' }}>
        <StatCard label="Total Tickets" value={kpis.total_tickets || 0} subtext="Campus lifetime" icon={Ticket} color="var(--brand-blue)" bg="var(--brand-blue-light)" />
        <StatCard label="Open / Pending" value={kpis.open_tickets || 0} subtext="Requires triage" icon={Clock} color="#8B5CF6" bg="#EDE9FE" />
        <StatCard label="Resolved" value={(kpis.resolved_tickets || 0) + (kpis.closed_tickets || 0)} subtext="Fixed by IT staff" icon={CheckCircle2} color="#10B981" bg="#D1FAE5" />
        <StatCard label="Critical Issues" value={kpis.critical_tickets || 0} subtext="Immediate priority" icon={AlertTriangle} color="#EF4444" bg="#FEE2E2" />
      </div>

      {/* Secondary SLA & Quality KPI Row */}
      <div className="grid-4" style={{ marginBottom: '2rem' }}>
        <StatCard label="Overdue Tickets" value={kpis.overdue_tickets || 0} subtext="SLA Target breached" icon={AlertTriangle} color="#DC2626" bg="#FEF2F2" />
        <StatCard label="Avg Resolution Time" value={`${kpis.avg_resolution_hours || 0} hrs`} subtext="From creation to fix" icon={TrendingUp} color="#0D9488" bg="#CCFBF1" />
        <StatCard label="SLA Compliance Rate" value={`${kpis.sla_compliance_rate ?? 100}%`} subtext="Resolved within SLA" icon={ShieldCheck} color="#16A34A" bg="#DCFCE7" />
        <StatCard label="Service Satisfaction" value={`${kpis.average_rating ?? 0} / 5`} subtext="User feedback score" icon={Star} color="#CA8A04" bg="#FEF9C3" />
      </div>

      {/* Recharts Analytics Section 1: Monthly Trends & Category Breakdown */}
      <div className="grid-2" style={{ marginBottom: '1.75rem' }}>
        <div className="card">
          <div className="card-header">
            <h3 className="card-title">
              <TrendingUp size={18} color="var(--brand-blue)" />
              Monthly Complaint Inflow & Resolution
            </h3>
          </div>
          <div style={{ height: '300px', width: '100%' }}>
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={charts.monthly_trends || []}>
                <defs>
                  <linearGradient id="colorSubmitted" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="var(--brand-blue)" stopOpacity={0.8}/>
                    <stop offset="95%" stopColor="var(--brand-blue)" stopOpacity={0}/>
                  </linearGradient>
                  <linearGradient id="colorResolved" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#10B981" stopOpacity={0.8}/>
                    <stop offset="95%" stopColor="#10B981" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--surface-subtle)" />
                <XAxis dataKey="month" stroke="var(--text-subtle)" fontSize={12} />
                <YAxis stroke="var(--text-subtle)" fontSize={12} allowDecimals={false} />
                <Tooltip />
                <Legend />
                <Area type="monotone" dataKey="submitted" stroke="var(--brand-blue)" fillOpacity={1} fill="url(#colorSubmitted)" name="Submitted" />
                <Area type="monotone" dataKey="resolved" stroke="#10B981" fillOpacity={1} fill="url(#colorResolved)" name="Resolved" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="card">
          <div className="card-header">
            <h3 className="card-title">
              <Layers size={18} color="#8B5CF6" />
              Tickets by Category
            </h3>
          </div>
          <div style={{ height: '300px', width: '100%' }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={charts.category_distribution || []} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="var(--surface-subtle)" />
                <XAxis type="number" stroke="var(--text-subtle)" fontSize={12} allowDecimals={false} />
                <YAxis dataKey="name" type="category" stroke="var(--text-subtle)" fontSize={11} width={130} />
                <Tooltip />
                <Bar dataKey="count" fill="var(--brand-blue)" radius={[0, 4, 4, 0]}>
                  {(charts.category_distribution || []).map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Recharts Analytics Section 2: Building Location & Priority */}
      <div className="grid-2" style={{ marginBottom: '1.75rem' }}>
        <div className="card">
          <div className="card-header">
            <h3 className="card-title">
              <Building size={18} color="#0D9488" />
              Campus Facilities & Location Load
            </h3>
          </div>
          <div style={{ height: '260px', width: '100%' }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={charts.building_distribution || []}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--surface-subtle)" />
                <XAxis dataKey="name" stroke="var(--text-subtle)" fontSize={11} />
                <YAxis stroke="var(--text-subtle)" fontSize={12} allowDecimals={false} />
                <Tooltip />
                <Bar dataKey="count" fill="#0D9488" radius={[4, 4, 0, 0]} name="Issues Reported" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="card">
          <div className="card-header">
            <h3 className="card-title">
              <AlertTriangle size={18} color="#EF4444" />
              Tickets by Priority Distribution
            </h3>
          </div>
          <div style={{ height: '260px', width: '100%' }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={charts.priority_distribution || []}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--surface-subtle)" />
                <XAxis dataKey="name" stroke="var(--text-subtle)" fontSize={12} />
                <YAxis stroke="var(--text-subtle)" fontSize={12} allowDecimals={false} />
                <Tooltip />
                <Bar dataKey="count" fill="#F59E0B" radius={[4, 4, 0, 0]} name="Volume">
                  {(charts.priority_distribution || []).map((entry, index) => {
                    const color = entry.name.toLowerCase() === 'critical' ? '#EF4444' : entry.name.toLowerCase() === 'high' ? '#F97316' : entry.name.toLowerCase() === 'medium' ? '#F59E0B' : '#10B981';
                    return <Cell key={`pri-${index}`} fill={color} />;
                  })}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Staff Accountability & Performance Table (Real-time from warning service) */}
      <div className="card">
        <div className="card-header">
          <h3 className="card-title">
            <ShieldAlert size={18} color="#DC2626" />
            Staff Accountability & SLA Performance Monitor
          </h3>
          <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
            <button
              type="button"
              onClick={handleTriggerSlaCheck}
              className="btn btn-secondary btn-sm"
              disabled={perfLoading}
              title="Scan all active tickets past SLA + grace period and issue warning tickets"
              style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}
            >
              <Zap size={14} /> Check SLA Breaches
            </button>
            <button
              type="button"
              onClick={refreshStaffPerf}
              className="btn btn-secondary btn-sm"
              disabled={perfLoading}
              style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}
            >
              <RefreshCw size={14} style={{ animation: perfLoading ? 'spin 1s linear infinite' : 'none' }} />
              {perfLoading ? 'Refreshing...' : 'Refresh'}
            </button>
            <Link to="/users" style={{ fontSize: '0.8125rem', color: 'var(--brand-blue)', fontWeight: '600' }}>
              Manage Accounts →
            </Link>
          </div>
        </div>

        {/* Summary badges for critical attention */}
        {staffPerf && (staffPerf.staff || []).some(s => s.review_required) && (
          <div style={{
            margin: '0 1.25rem 1rem',
            padding: '0.875rem 1.25rem',
            backgroundColor: '#FEE2E2',
            border: '1px solid #FCA5A5',
            borderRadius: '8px',
            display: 'flex',
            alignItems: 'center',
            gap: '0.75rem',
            color: '#991B1B',
            fontSize: '0.875rem'
          }}>
            <ShieldAlert size={20} />
            <div>
              <strong>Administrative Review Required:</strong>{' '}
              {(staffPerf.staff || []).filter(s => s.review_required).map(s => s.staff_name).join(', ')} ha(ve) reached 3 strikes and require immediate performance evaluation.
            </div>
          </div>
        )}

        {!staffPerf ? (
          <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-subtle)' }}>
            Loading staff accountability metrics...
          </div>
        ) : (staffPerf.staff || []).length === 0 ? (
          <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-subtle)' }}>
            No staff members found in this institution.
          </div>
        ) : (
          <div className="table-responsive">
            <table className="table">
              <thead>
                <tr>
                  <th>Staff Member</th>
                  <th>Domain Specialization</th>
                  <th>Capacity</th>
                  <th>SLA Compliance</th>
                  <th>30-Day Warnings</th>
                  <th>Strikes</th>
                  <th>Resolved Total</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {(staffPerf.staff || []).map((s, idx) => (
                  <tr
                    key={idx}
                    style={{
                      backgroundColor: s.review_required ? '#FEF2F2'
                        : s.strikes_count > 0 ? '#FFF7ED'
                        : s.warnings_30d_count > 0 ? '#FFFBEB'
                        : 'inherit'
                    }}
                  >
                    <td>
                      <div style={{ fontWeight: '700', color: 'var(--text-main)' }}>{s.staff_name}</div>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{s.staff_email}</div>
                    </td>
                    <td style={{ fontSize: '0.8rem', color: 'var(--text-muted)', maxWidth: '160px' }}>
                      {(s.specialization || []).slice(0, 2).join(', ') || <em style={{ color: '#9CA3AF' }}>General IT</em>}
                    </td>
                    <td>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <div style={{
                          width: '100%',
                          maxWidth: '80px',
                          height: '8px',
                          backgroundColor: '#E5E7EB',
                          borderRadius: '4px',
                          overflow: 'hidden'
                        }}>
                          <div style={{
                            width: `${Math.min(100, (s.active_tickets / s.capacity_limit) * 100)}%`,
                            height: '100%',
                            backgroundColor: s.active_tickets >= s.capacity_limit ? '#EF4444' : '#3B82F6',
                            borderRadius: '4px'
                          }} />
                        </div>
                        <span style={{ fontSize: '0.8rem', fontWeight: '600', whiteSpace: 'nowrap' }}>
                          {s.active_tickets} / {s.capacity_limit}
                        </span>
                      </div>
                    </td>
                    <td>
                      <span style={{
                        fontWeight: '700',
                        fontSize: '0.9rem',
                        color: s.sla_compliance_rate >= 90 ? '#059669'
                          : s.sla_compliance_rate >= 70 ? '#D97706'
                          : '#DC2626'
                      }}>
                        {s.sla_compliance_rate}%
                      </span>
                    </td>
                    <td>
                      <span style={{
                        display: 'inline-block',
                        padding: '2px 10px',
                        borderRadius: '9999px',
                        fontSize: '0.8rem',
                        fontWeight: '700',
                        backgroundColor: s.warnings_30d_count > 0 ? '#FEE2E2' : '#F3F4F6',
                        color: s.warnings_30d_count > 0 ? '#DC2626' : '#6B7280'
                      }}>
                        {s.warnings_30d_count} / 3
                      </span>
                    </td>
                    <td>
                      <span style={{
                        display: 'inline-block',
                        padding: '2px 10px',
                        borderRadius: '9999px',
                        fontSize: '0.8rem',
                        fontWeight: '700',
                        backgroundColor: s.strikes_count > 0 ? '#FFF7ED' : '#F3F4F6',
                        color: s.strikes_count > 0 ? '#C2410C' : '#6B7280'
                      }}>
                        {s.strikes_count} / 3
                      </span>
                    </td>
                    <td>
                      <span style={{ fontWeight: '600', color: '#10B981' }}>{s.resolved_tickets}</span>
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}> closed</span>
                    </td>
                    <td>
                      {s.review_required ? (
                        <span style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '5px',
                          padding: '3px 10px',
                          borderRadius: '6px',
                          fontSize: '0.75rem',
                          fontWeight: '700',
                          backgroundColor: '#FEE2E2',
                          color: '#991B1B',
                          border: '1px solid #FCA5A5'
                        }}>
                          <ShieldAlert size={12} /> Review Required
                        </span>
                      ) : s.strikes_count > 0 ? (
                        <span style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '4px',
                          padding: '3px 10px',
                          borderRadius: '6px',
                          fontSize: '0.75rem',
                          fontWeight: '700',
                          backgroundColor: '#FFF7ED',
                          color: '#C2410C',
                          border: '1px solid #FDBA74'
                        }}>
                          <Zap size={12} /> {s.strikes_count} Strike(s) Active
                        </span>
                      ) : (
                        <span style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '4px',
                          padding: '3px 10px',
                          borderRadius: '6px',
                          fontSize: '0.75rem',
                          fontWeight: '700',
                          backgroundColor: '#F0FDF4',
                          color: '#166534',
                          border: '1px solid #BBF7D0'
                        }}>
                          <CheckCircle2 size={12} /> Good Standing
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {staffPerf && (
          <div style={{
            padding: '0.75rem 1.25rem',
            borderTop: '1px solid var(--border-color)',
            fontSize: '0.8rem',
            color: 'var(--text-muted)',
            backgroundColor: 'var(--bg-subtle)'
          }}>
            <strong>Capacity Limit:</strong> {staffPerf.capacity_limit} active tickets/staff •{' '}
            <strong>Warning Window:</strong> {staffPerf.rolling_window_days} days rolling •{' '}
            Warnings = SLA Deadline + Grace Period (Critical +2h, High +4h, Medium +6h, Low +8h). 3 warnings = 1 Strike. 3 Strikes = Review Required.
          </div>
        )}
      </div>
    </div>
  );
}
