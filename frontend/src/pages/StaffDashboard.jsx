import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { 
  UserCheck, Clock, AlertTriangle, CheckCircle2, ArrowRight, 
  Filter, ShieldAlert, AlertCircle, Award, History, Layers
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { ticketService, staffPerformanceService } from '../api/services';
import StatusBadge from '../components/StatusBadge';
import PriorityBadge from '../components/PriorityBadge';
import StatCard from '../components/StatCard';
import EmptyState from '../components/EmptyState';

export default function StaffDashboard() {
  const { user } = useAuth();
  const [assignedTickets, setAssignedTickets] = useState([]);
  const [openQueue, setOpenQueue] = useState([]);
  const [accountability, setAccountability] = useState(null);
  const [showWarningHistory, setShowWarningHistory] = useState(false);
  const [loading, setLoading] = useState(true);

  const loadData = async () => {
    try {
      const [assignedRes, openRes, perfRes] = await Promise.all([
        ticketService.getTickets({ assigned_to_me: true }),
        ticketService.getTickets({ status: 'open' }),
        staffPerformanceService.getMyWarnings().catch(() => ({ data: null }))
      ]);
      setAssignedTickets(assignedRes.data || []);
      setOpenQueue(openRes.data || []);
      if (perfRes?.data) {
        setAccountability(perfRes.data);
      }
    } catch (err) {
      console.error("Staff dashboard load failed:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const myActive = assignedTickets.filter(t => ['assigned', 'in_progress', 'on_hold', 'reopened'].includes(t.status));
  const myResolved = assignedTickets.filter(t => ['resolved', 'closed'].includes(t.status));
  const myOverdue = assignedTickets.filter(t => t.is_overdue && ['assigned', 'in_progress', 'on_hold', 'reopened'].includes(t.status));
  const criticalCount = assignedTickets.filter(t => t.priority === 'critical' && ['assigned', 'in_progress', 'on_hold', 'reopened'].includes(t.status)).length;

  const activeCount = accountability?.active_tickets ?? myActive.length;
  const capacityLimit = accountability?.capacity_limit ?? 3;
  const warnings30d = accountability?.warnings_30d_count ?? 0;
  const strikesCount = accountability?.strikes_count ?? 0;
  const isReviewRequired = accountability?.review_required ?? false;
  const complianceRate = accountability?.sla_compliance_rate ?? 100;
  const warningsList = accountability?.warnings || [];

  return (
    <div className="page-wrapper">
      <div className="page-header">
        <div>
          <h1 className="page-title">IT Staff Support Console</h1>
          <p className="page-subtitle">
            Logged in as <strong>{user?.name}</strong> • Domain: {user?.specialization?.join(', ') || 'General IT Support'}
          </p>
        </div>
        <div style={{ display: 'flex', gap: '0.75rem' }}>
          <button 
            type="button" 
            onClick={() => setShowWarningHistory(!showWarningHistory)}
            className="btn btn-secondary"
          >
            <History size={16} /> {showWarningHistory ? 'Hide Warnings History' : 'Accountability & SLA Log'}
          </button>
          <Link to="/tickets" className="btn btn-navy">
            View All Tickets
          </Link>
        </div>
      </div>

      {/* Capacity & Auto-Assign Status Banner */}
      <div style={{
        backgroundColor: activeCount >= capacityLimit ? '#FFFBEB' : '#F0FDF4',
        border: `1px solid ${activeCount >= capacityLimit ? '#FDE68A' : '#BBF7D0'}`,
        borderRadius: '10px',
        padding: '0.9rem 1.25rem',
        marginBottom: '1.25rem',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        color: activeCount >= capacityLimit ? '#92400E' : '#166534',
        fontSize: '0.875rem'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <Layers size={20} />
          <div>
            <strong>Active Task Capacity: {activeCount} / {capacityLimit} slots occupied</strong>
            <div style={{ fontSize: '0.8rem', opacity: 0.9 }}>
              {activeCount >= capacityLimit 
                ? 'Queue locked: You are currently at maximum capacity. Resolve an active ticket to automatically receive your next waiting assignment.'
                : `Ready for tasks: You have ${capacityLimit - activeCount} slot(s) open. New campus complaints matching your domain will be routed to your queue.`}
            </div>
          </div>
        </div>
        <span style={{
          display: 'inline-block',
          padding: '4px 12px',
          borderRadius: '9999px',
          fontWeight: '700',
          fontSize: '0.75rem',
          backgroundColor: activeCount >= capacityLimit ? '#F59E0B' : '#10B981',
          color: 'white'
        }}>
          {activeCount >= capacityLimit ? 'CAPACITY FULL' : 'AVAILABLE FOR TASKS'}
        </span>
      </div>

      {/* Critical Review / Strike Warning Banner */}
      {isReviewRequired ? (
        <div style={{
          backgroundColor: '#FEE2E2',
          border: '2px solid #EF4444',
          borderRadius: '10px',
          padding: '1.25rem',
          marginBottom: '1.5rem',
          display: 'flex',
          alignItems: 'center',
          gap: '1rem',
          color: '#991B1B'
        }}>
          <ShieldAlert size={32} />
          <div>
            <div style={{ fontWeight: '800', fontSize: '1rem' }}>ADMINISTRATIVE PERFORMANCE REVIEW REQUIRED</div>
            <div style={{ fontSize: '0.875rem', marginTop: '0.25rem' }}>
              Your profile has reached 3 strikes due to repeated SLA deadline breaches beyond allowable grace periods. 
              The system has flagged your account for administrative performance audit. Please contact the college administrator.
            </div>
          </div>
        </div>
      ) : strikesCount > 0 ? (
        <div style={{
          backgroundColor: '#FFF7ED',
          border: '1px solid #FDBA74',
          borderRadius: '10px',
          padding: '1rem 1.25rem',
          marginBottom: '1.5rem',
          display: 'flex',
          alignItems: 'center',
          gap: '0.75rem',
          color: '#C2410C'
        }}>
          <AlertTriangle size={24} />
          <div>
            <div style={{ fontWeight: '700', fontSize: '0.925rem' }}>Active Penalty Strikes: {strikesCount} / 3</div>
            <div style={{ fontSize: '0.8125rem' }}>
              You have accumulated {strikesCount} strike(s). Accumulating 3 strikes flags your profile for Administrative Review. (Every 3 SLA warnings in 30 days = 1 Strike).
            </div>
          </div>
        </div>
      ) : warnings30d > 0 ? (
        <div style={{
          backgroundColor: '#FEF3C7',
          border: '1px solid #FCD34D',
          borderRadius: '10px',
          padding: '0.875rem 1.25rem',
          marginBottom: '1.5rem',
          display: 'flex',
          alignItems: 'center',
          gap: '0.75rem',
          color: '#92400E'
        }}>
          <AlertCircle size={22} />
          <div>
            <div style={{ fontWeight: '700', fontSize: '0.9rem' }}>SLA Warning Notice: {warnings30d} warning(s) in rolling 30-day window</div>
            <div style={{ fontSize: '0.8rem' }}>
              Warning tickets are issued when tasks exceed SLA targets plus grace periods (Critical +2h, High +4h, Medium +6h, Low +8h). 3 warnings within 30 days result in an official strike.
            </div>
          </div>
        </div>
      ) : null}

      {/* Overdue Warning Alert */}
      {myOverdue.length > 0 && (
        <div style={{
          backgroundColor: '#FEE2E2',
          border: '1px solid #FCA5A5',
          borderRadius: '10px',
          padding: '1rem 1.25rem',
          marginBottom: '1.5rem',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          color: '#991B1B'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <ShieldAlert size={24} />
            <div>
              <div style={{ fontWeight: '700', fontSize: '0.925rem' }}>SLA Deadline Alert: {myOverdue.length} Overdue Task(s)</div>
              <div style={{ fontSize: '0.8125rem' }}>Complete these immediately to avoid grace-period expiration and accountability warnings.</div>
            </div>
          </div>
          <Link to="/tickets?assigned_to_me=true" className="btn btn-danger btn-sm">
            Inspect Tasks
          </Link>
        </div>
      )}

      {/* KPI Cards */}
      <div className="grid-4" style={{ marginBottom: '2rem' }}>
        <StatCard 
          label="Active Workload" 
          value={`${activeCount} / ${capacityLimit}`} 
          subtext={activeCount >= capacityLimit ? "Capacity Limit Reached" : `${capacityLimit - activeCount} slot(s) free`} 
          icon={UserCheck} 
          color="var(--brand-blue)" 
          bg="var(--brand-blue-light)" 
        />
        <StatCard 
          label="SLA Compliance Score" 
          value={`${complianceRate}%`} 
          subtext="Resolution on-time rate" 
          icon={Award} 
          color="#10B981" 
          bg="#D1FAE5" 
        />
        <StatCard 
          label="30-Day SLA Warnings" 
          value={`${warnings30d} / 3`} 
          subtext="3 warnings = 1 strike" 
          icon={AlertTriangle} 
          color={warnings30d > 0 ? "#EA580C" : "#6B7280"} 
          bg={warnings30d > 0 ? "#FFEDD5" : "#F3F4F6"} 
        />
        <StatCard 
          label="Strikes Accumulated" 
          value={`${strikesCount} / 3`} 
          subtext={isReviewRequired ? "Review Required" : "3 strikes = Review"} 
          icon={ShieldAlert} 
          color={strikesCount > 0 ? "#DC2626" : "#6B7280"} 
          bg={strikesCount > 0 ? "#FEE2E2" : "#F3F4F6"} 
        />
      </div>

      {/* Collapsible Accountability & Warning History Section */}
      {showWarningHistory && (
        <div className="card" style={{ marginBottom: '2rem', border: '1px solid #E2E8F0' }}>
          <div className="card-header" style={{ backgroundColor: '#F8FAFC' }}>
            <h3 className="card-title">
              <History size={18} color="var(--brand-blue)" />
              SLA Breach Warning Records & Accountability Log
            </h3>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              Rolling 30-Day Window: {warnings30d} active | Total: {warningsList.length}
            </span>
          </div>
          {warningsList.length === 0 ? (
            <div style={{ padding: '2.5rem', textAlign: 'center', color: 'var(--text-subtle)', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem' }}>
              <CheckCircle2 size={18} color="#059669" /> Clean record! You have zero SLA breach warnings issued against your profile.
            </div>
          ) : (
            <div className="table-responsive">
              <table className="table">
                <thead>
                  <tr>
                    <th>Warning ID</th>
                    <th>Ticket ID & Title</th>
                    <th>Priority</th>
                    <th>Issued Date</th>
                    <th>Grace Period</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {warningsList.map((w) => (
                    <tr key={w._id} style={{ backgroundColor: w.pardoned ? '#F9FAFB' : '#FEF2F2' }}>
                      <td style={{ fontFamily: 'monospace', fontWeight: '600', fontSize: '0.8rem' }}>{w._id}</td>
                      <td>
                        <Link to={`/tickets/${w.ticket_id}`} style={{ fontWeight: '600', color: 'var(--brand-blue)' }}>
                          {w.ticket_number}
                        </Link>
                        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{w.ticket_title}</div>
                      </td>
                      <td><PriorityBadge priority={w.priority} /></td>
                      <td style={{ fontSize: '0.8rem' }}>
                        {new Date(w.issued_at).toLocaleString()}
                      </td>
                      <td style={{ fontSize: '0.8rem' }}>+{w.grace_hours}h allowed</td>
                      <td>
                        {w.pardoned ? (
                          <span style={{
                            display: 'inline-block',
                            padding: '2px 8px',
                            borderRadius: '4px',
                            fontSize: '0.75rem',
                            fontWeight: '600',
                            backgroundColor: '#DEF7EC',
                            color: '#03543F'
                          }}>
                            Pardoned by Admin ({w.pardon_reason || 'Excused'})
                          </span>
                        ) : (
                          <span style={{
                            display: 'inline-block',
                            padding: '2px 8px',
                            borderRadius: '4px',
                            fontSize: '0.75rem',
                            fontWeight: '600',
                            backgroundColor: '#FDE8E8',
                            color: '#9B1C1C'
                          }}>
                            Active Breach Warning
                          </span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* My Assigned Tickets Table */}
      <div className="card" style={{ marginBottom: '2rem' }}>
        <div className="card-header">
          <h3 className="card-title">
            <UserCheck size={18} color="var(--brand-blue)" />
            My Active Task Queue ({assignedTickets.length})
          </h3>
          <span style={{ fontSize: '0.8125rem', color: 'var(--text-muted)' }}>
            Max 3 tasks concurrently • Auto-assign resumes once a task is resolved
          </span>
        </div>

        {loading ? (
          <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-subtle)' }}>Loading assignments...</div>
        ) : assignedTickets.length === 0 ? (
          <EmptyState
            title="No tickets assigned to you"
            description="You currently have zero active assignments. Check the open campus queue below to pick up tickets or await auto-assignment."
          />
        ) : (
          <div className="table-responsive">
            <table className="table">
              <thead>
                <tr>
                  <th>Ticket ID</th>
                  <th>Issue Title & Category</th>
                  <th>Priority</th>
                  <th>Status</th>
                  <th>Location</th>
                  <th>SLA Remaining</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {assignedTickets.map((t) => (
                  <tr key={t.id} style={{ backgroundColor: t.is_overdue ? '#FEF2F2' : 'inherit' }}>
                    <td style={{ fontWeight: '600', fontFamily: 'monospace', color: 'var(--brand-blue)', fontSize: '0.8125rem' }}>
                      {t.ticket_id}
                    </td>
                    <td>
                      <div style={{ fontWeight: '600', color: 'var(--text-main)' }}>{t.title}</div>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{t.category} • Reported by {t.created_by?.name}</div>
                    </td>
                    <td>
                      <PriorityBadge priority={t.priority} />
                    </td>
                    <td>
                      <StatusBadge status={t.status} />
                    </td>
                    <td style={{ fontSize: '0.8125rem' }}>
                      {t.building} - {t.room}
                    </td>
                    <td>
                      {t.status === 'resolved' || t.status === 'closed' ? (
                        <span style={{ fontSize: '0.75rem', color: '#10B981', fontWeight: '600' }}>Resolved</span>
                      ) : t.is_overdue ? (
                        <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.3rem', fontSize: '0.75rem', color: '#EF4444', fontWeight: '700' }}>
                          <AlertCircle size={12} /> OVERDUE
                        </span>
                      ) : (
                        <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                          {Math.floor((t.time_remaining_minutes || 0) / 60)}h {(t.time_remaining_minutes || 0) % 60}m
                        </span>
                      )}
                    </td>
                    <td>
                      <Link to={`/tickets/${t.id}`} className="btn btn-navy btn-sm">
                        Work On Ticket
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Open Unassigned Campus Queue */}
      <div className="card">
        <div className="card-header">
          <h3 className="card-title">
            <Clock size={18} color="#8B5CF6" />
            Unassigned Campus Queue ({openQueue.length})
          </h3>
          <span style={{ fontSize: '0.8125rem', color: 'var(--text-muted)' }}>
            Waiting tickets auto-assigned to you when you resolve an active ticket
          </span>
        </div>

        {openQueue.length === 0 ? (
          <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-subtle)', fontSize: '0.875rem' }}>
            No unassigned tickets in the campus queue.
          </div>
        ) : (
          <div className="table-responsive">
            <table className="table">
              <thead>
                <tr>
                  <th>Ticket ID</th>
                  <th>Title</th>
                  <th>Category</th>
                  <th>Priority</th>
                  <th>Location</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {openQueue.map((t) => (
                  <tr key={t.id}>
                    <td style={{ fontWeight: '600', fontFamily: 'monospace', color: 'var(--brand-blue)' }}>{t.ticket_id}</td>
                    <td style={{ fontWeight: '600' }}>{t.title}</td>
                    <td style={{ fontSize: '0.8125rem', color: 'var(--text-muted)' }}>{t.category}</td>
                    <td><PriorityBadge priority={t.priority} /></td>
                    <td style={{ fontSize: '0.8125rem' }}>{t.building} - {t.room}</td>
                    <td>
                      <Link to={`/tickets/${t.id}`} className="btn btn-secondary btn-sm">
                        Accept & Investigate
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
