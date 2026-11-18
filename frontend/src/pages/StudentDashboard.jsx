import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  PlusCircle,
  Ticket,
  Clock,
  CheckCircle2,
  AlertTriangle,
  ArrowRight,
  BookOpen,
  Search,
  ThumbsUp,
  HelpCircle,
  Wrench,
  Sparkles,
  Layers,
  MapPin,
  Users,
  GraduationCap,
  Globe,
  Lock,
  Zap
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { ticketService, knowledgeBaseService } from '../api/services';
import StatusBadge from '../components/StatusBadge';
import PriorityBadge from '../components/PriorityBadge';
import StatCard from '../components/StatCard';
import EmptyState from '../components/EmptyState';
import ComplaintBoardPage from './ComplaintBoardPage';

// Common problems, causes, and quick-fix self-help guides
const QUICK_FIX_GUIDES = [
  {
    id: 'qf-1',
    category: 'Network & Internet',
    title: 'Wi-Fi "Connected, no internet" or Auth Rejection',
    cause: 'Stale cached credentials, DHCP lease timeout, or access point radio channel congestion.',
    solution: 'Forget "NIE-Student-WiFi" on your device, toggle Airplane Mode for 5 seconds, and reconnect. Ensure you accept the campus security certificate.',
    diyTime: '2 mins'
  },
  {
    id: 'qf-2',
    category: 'Projector & AV',
    title: 'Classroom Projector Displays "No Signal" via HDMI',
    cause: 'Laptop display projection mode is set to "PC Screen Only" or incorrect input source selected on the wall panel.',
    solution: 'Press Win + P on Windows (or Cmd + F1 on Mac) and choose "Duplicate". Ensure the wall input switcher is set to "HDMI 1".',
    diyTime: '1 min'
  },
  {
    id: 'qf-3',
    category: 'Computer & Hardware',
    title: 'Lab Workstation Monitor Black Screen / Standby',
    cause: 'Loose display cable connection, monitor input channel toggled to VGA instead of DisplayPort, or PC in deep sleep.',
    solution: 'Firmly reseat the HDMI/DisplayPort cable on both ends. Press the power button once to wake the CPU. Press the monitor "Source" button to cycle inputs.',
    diyTime: '3 mins'
  },
  {
    id: 'qf-4',
    category: 'Electrical & Power',
    title: 'Workstation / Bench Power Socket Dead',
    cause: 'Individual bench miniature circuit breaker (MCB) tripped due to overload or loose master plug.',
    solution: 'Check if neighboring desks have power. Verify the switch is fully clicked ON. If breaker is tripped, report ticket for electrician reset.',
    diyTime: 'Requires Staff'
  },
  {
    id: 'qf-5',
    category: 'Software & Applications',
    title: 'MATLAB / Python IDE "License Server Unreachable"',
    cause: 'Client machine is on external mobile hotspot instead of campus intranet subnet.',
    solution: 'Connect to campus Ethernet or NIE Wi-Fi to establish a direct route to the internal campus license manager server.',
    diyTime: '2 mins'
  }
];

export default function StudentDashboard() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState('complaints'); // 'complaints' | 'report' | 'my-tickets' | 'kb'
  const [myTickets, setMyTickets] = useState([]);
  const [upvotedTickets, setUpvotedTickets] = useState([]);
  const [kbArticles, setKbArticles] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadDashboardData = async () => {
      try {
        setLoading(true);
        // Load user's tickets including upvoted
        const [ticketsRes, kbRes] = await Promise.all([
          ticketService.getTickets({ include_upvoted: true, limit: 100 }),
          knowledgeBaseService.getArticles({ limit: 6 })
        ]);

        const all = ticketsRes.data || [];
        const myOwn = all.filter((t) => t.created_by?.id === user?.id);
        const upvoted = all.filter((t) => t.user_has_upvoted || (t.upvotes && t.upvotes.includes(user?.id)));

        setMyTickets(myOwn);
        setUpvotedTickets(upvoted);
        setKbArticles(kbRes.data || []);
      } catch (err) {
        console.error('Failed to load student dashboard:', err);
      } finally {
        setLoading(false);
      }
    };

    loadDashboardData();
  }, [user?.id]);

  const total = myTickets.length;
  const active = myTickets.filter((t) => ['open', 'assigned', 'in_progress', 'on_hold', 'reopened'].includes(t.status)).length;
  const resolved = myTickets.filter((t) => ['resolved', 'closed'].includes(t.status)).length;
  const upvotedCount = upvotedTickets.length;

  return (
    <div className="page-wrapper">
      {/* Welcome Banner */}
      <div
        style={{
          background: 'linear-gradient(135deg, var(--primary-navy) 0%, var(--primary-navy-dark) 100%)',
          color: '#FFFFFF',
          borderRadius: '12px',
          padding: '1.75rem 2rem',
          marginBottom: '1.75rem',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '1rem',
          boxShadow: 'var(--shadow-md)'
        }}
      >
        <div>
          <span
            style={{
              fontSize: '0.8125rem',
              color: '#93C5FD',
              fontWeight: '700',
              textTransform: 'uppercase',
              letterSpacing: '0.05em',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '0.4rem'
            }}
          >
            <GraduationCap size={16} /> Student Portal
          </span>
          <h1 style={{ fontSize: '1.75rem', fontWeight: '800', marginTop: '0.25rem', letterSpacing: '-0.02em' }}>
            Welcome back, {user?.name}
          </h1>
          <p style={{ color: '#BFDBFE', fontSize: '0.875rem', marginTop: '0.25rem' }}>
            Department of {user?.department || 'Computer Science & Engineering'} • Campus IT Support
          </p>
        </div>

        <Link
          to="/tickets/new"
          className="btn btn-primary"
          style={{ padding: '0.75rem 1.5rem', fontWeight: '700', display: 'inline-flex', alignItems: 'center', gap: '0.5rem' }}
        >
          <PlusCircle size={18} /> Report an Issue
        </Link>
      </div>

      {/* KPI Cards */}
      <div className="grid-4" style={{ marginBottom: '2rem' }}>
        <StatCard label="My Tickets" value={total} subtext="Reported by you" icon={Ticket} color="var(--brand-blue)" bg="var(--brand-blue-light)" />
        <StatCard label="Active / In Progress" value={active} subtext="Under resolution" icon={Clock} color="#F59E0B" bg="#FEF3C7" />
        <StatCard label="Resolved Issues" value={resolved} subtext="Successfully fixed" icon={CheckCircle2} color="#10B981" bg="#D1FAE5" />
        <StatCard label="Issues I Upvoted" value={upvotedCount} subtext="Tracked campus issues" icon={ThumbsUp} color="#8B5CF6" bg="#EDE9FE" />
      </div>

      {/* 4 Portal Navigation Sections */}
      <div
        style={{
          display: 'flex',
          borderBottom: '2px solid var(--border-color)',
          marginBottom: '1.75rem',
          gap: '0.5rem',
          overflowX: 'auto'
        }}
      >
        {[
          { key: 'complaints', label: 'Complaint Section', icon: Layers, badge: null },
          { key: 'report', label: 'Report an Issue', icon: PlusCircle, badge: null },
          { key: 'my-tickets', label: 'My Tickets & Upvoted', icon: Ticket, badge: total + upvotedCount },
          { key: 'kb', label: 'Knowledge Base & Quick Fixes', icon: BookOpen, badge: null }
        ].map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.key;
          return (
            <button
              key={tab.key}
              type="button"
              onClick={() => setActiveTab(tab.key)}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '0.5rem',
                padding: '0.85rem 1.25rem',
                border: 'none',
                borderBottom: isActive ? '3px solid var(--primary-navy)' : '3px solid transparent',
                backgroundColor: 'transparent',
                color: isActive ? 'var(--primary-navy)' : 'var(--text-muted)',
                fontWeight: isActive ? '800' : '600',
                fontSize: '0.925rem',
                cursor: 'pointer',
                whiteSpace: 'nowrap',
                transition: 'all 0.15s ease'
              }}
            >
              <Icon size={18} />
              {tab.label}
              {tab.badge !== null && tab.badge > 0 && (
                <span
                  style={{
                    backgroundColor: isActive ? 'var(--primary-navy)' : 'var(--bg-main)',
                    color: isActive ? '#FFFFFF' : 'var(--text-muted)',
                    fontSize: '0.725rem',
                    fontWeight: '700',
                    padding: '0.15rem 0.5rem',
                    borderRadius: '999px',
                    marginLeft: '0.25rem'
                  }}
                >
                  {tab.badge}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* SECTION 1: Complaint Section (Public Complaint Board with ML Priority & Upvotes) */}
      {activeTab === 'complaints' && (
        <div>
          <ComplaintBoardPage roleFilter="all" />
        </div>
      )}

      {/* SECTION 2: Report an Issue */}
      {activeTab === 'report' && (
        <div className="card" style={{ padding: '2.5rem', textAlign: 'center', maxWidth: '680px', margin: '0 auto' }}>
          <div
            style={{
              width: '64px',
              height: '64px',
              borderRadius: '16px',
              backgroundColor: 'var(--brand-blue-light)',
              color: 'var(--brand-blue)',
              display: 'grid',
              placeItems: 'center',
              margin: '0 auto 1.25rem'
            }}
          >
            <PlusCircle size={32} />
          </div>
          <h2 style={{ fontSize: '1.4rem', fontWeight: '800', color: 'var(--text-main)', marginBottom: '0.5rem' }}>
            Ready to submit a new complaint?
          </h2>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', marginBottom: '1.5rem', lineHeight: '1.5' }}>
            Provide the issue title, detailed description, campus building, floor, room, and number of affected users.
            FixIt's scikit-learn ML engine will automatically predict category, technical domain, and priority level!
          </p>
          <div style={{ display: 'flex', justifyContent: 'center', gap: '1rem', flexWrap: 'wrap' }}>
            <Link to="/tickets/new" className="btn btn-navy" style={{ padding: '0.85rem 2rem', fontWeight: '700' }}>
              Launch Issue Report Form →
            </Link>
            <button type="button" onClick={() => setActiveTab('complaints')} className="btn btn-secondary">
              Check Existing Complaints First
            </button>
          </div>
        </div>
      )}

      {/* SECTION 3: My Tickets & Upvoted Issues */}
      {activeTab === 'my-tickets' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
          {/* Subsection A: Issues Registered by Respective User */}
          <div className="card">
            <div className="card-header">
              <h3 className="card-title">
                <Ticket size={18} color="var(--brand-blue)" />
                Complaints Registered By Me ({myTickets.length})
              </h3>
              <Link to="/tickets/new" className="btn btn-primary btn-sm">
                <PlusCircle size={14} /> New Ticket
              </Link>
            </div>

            {loading ? (
              <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-muted)' }}>Loading tickets...</div>
            ) : myTickets.length === 0 ? (
              <EmptyState
                title="No complaints registered by you"
                description="You haven't reported any tickets yet. Experience an issue in class or lab? Report it to campus IT."
                action={
                  <Link to="/tickets/new" className="btn btn-primary btn-sm">
                    <PlusCircle size={14} /> Report First Issue
                  </Link>
                }
              />
            ) : (
              <div className="table-responsive">
                <table className="table">
                  <thead>
                    <tr>
                      <th>Ticket ID</th>
                      <th>Title & Category</th>
                      <th>Visibility</th>
                      <th>Priority (ML)</th>
                      <th>Status</th>
                      <th>Upvotes</th>
                      <th>Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {myTickets.map((t) => (
                      <tr key={t.id}>
                        <td style={{ fontWeight: '700', fontFamily: 'monospace', color: 'var(--brand-blue)', fontSize: '0.8125rem' }}>
                          {t.ticket_id}
                        </td>
                        <td>
                          <div style={{ fontWeight: '600', color: 'var(--text-main)', maxWidth: '240px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                            {t.title}
                          </div>
                          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                            {t.category} • {t.building} ({t.room})
                          </div>
                        </td>
                        <td>
                          <span
                            style={{
                              fontSize: '0.725rem',
                              fontWeight: '600',
                              padding: '0.15rem 0.5rem',
                              borderRadius: '4px',
                              backgroundColor: t.visibility === 'public' ? '#ECFDF5' : '#F3F4F6',
                              color: t.visibility === 'public' ? '#065F46' : '#4B5563'
                            }}
                          >
                            <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}>
                              {t.visibility === 'public' ? <><Globe size={12} /> Public</> : <><Lock size={12} /> Private</>}
                            </span>
                          </span>
                        </td>
                        <td>
                          <PriorityBadge priority={t.priority} />
                        </td>
                        <td>
                          <StatusBadge status={t.status} />
                        </td>
                        <td>
                          <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem', fontSize: '0.85rem', fontWeight: '700', color: 'var(--text-main)' }}>
                            <ThumbsUp size={13} /> {t.upvote_count || (t.upvotes ? t.upvotes.length : 0)}
                          </span>
                        </td>
                        <td>
                          <Link to={`/tickets/${t.id}`} className="btn btn-secondary btn-sm">
                            View
                          </Link>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Subsection B: Issues Upvoted by This User */}
          <div className="card">
            <div className="card-header">
              <h3 className="card-title">
                <ThumbsUp size={18} color="#8B5CF6" />
                Issues I Upvoted ({upvotedTickets.length})
              </h3>
              <button type="button" onClick={() => setActiveTab('complaints')} className="btn btn-secondary btn-sm">
                Browse Complaint Board →
              </button>
            </div>

            {upvotedTickets.length === 0 ? (
              <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.875rem' }}>
                You haven't upvoted any complaints yet. When other students or faculty post issues that also affect you, upvote them on the Complaint Board to escalate their priority!
              </div>
            ) : (
              <div className="table-responsive">
                <table className="table">
                  <thead>
                    <tr>
                      <th>Ticket ID</th>
                      <th>Issue Title</th>
                      <th>Reported By</th>
                      <th>Priority</th>
                      <th>Status</th>
                      <th>Total Upvotes</th>
                      <th>Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {upvotedTickets.map((t) => (
                      <tr key={t.id}>
                        <td style={{ fontWeight: '700', fontFamily: 'monospace', color: 'var(--brand-blue)', fontSize: '0.8125rem' }}>
                          {t.ticket_id}
                        </td>
                        <td>
                          <div style={{ fontWeight: '600', color: 'var(--text-main)', maxWidth: '240px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                            {t.title}
                          </div>
                          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                            {t.building} • {t.room}
                          </div>
                        </td>
                        <td>
                          <span
                            style={{
                              fontSize: '0.725rem',
                              fontWeight: '700',
                              padding: '0.15rem 0.5rem',
                              borderRadius: '4px',
                              backgroundColor: t.complainant_role === 'faculty' ? '#F0FDF4' : '#EFF6FF',
                              color: t.complainant_role === 'faculty' ? '#15803D' : '#1D4ED8'
                            }}
                          >
                            {t.complainant_role === 'faculty' ? 'Faculty' : 'Student'}
                          </span>
                        </td>
                        <td>
                          <PriorityBadge priority={t.priority} />
                        </td>
                        <td>
                          <StatusBadge status={t.status} />
                        </td>
                        <td>
                          <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem', fontSize: '0.85rem', fontWeight: '800', color: 'var(--brand-blue)' }}>
                            <ThumbsUp size={13} /> {t.upvote_count || (t.upvotes ? t.upvotes.length : 0)}
                          </span>
                        </td>
                        <td>
                          <Link to={`/tickets/${t.id}`} className="btn btn-secondary btn-sm">
                            View Updates
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
      )}

      {/* SECTION 4: Knowledge Base & Quick Fix Self-Help Suggestions */}
      {activeTab === 'kb' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          {/* Header */}
          <div className="card" style={{ padding: '1.5rem' }}>
            <h2 style={{ fontSize: '1.25rem', fontWeight: '800', color: 'var(--text-main)', marginBottom: '0.35rem' }}>
              Common Campus Problems & DIY Quick-Fix Solutions
            </h2>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem', margin: 0 }}>
              Many common network, lab, and classroom issues can be quickly resolved in minutes by following verified troubleshooting steps.
            </p>
          </div>

          {/* Quick-Fix Cards */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '1.25rem' }}>
            {QUICK_FIX_GUIDES.map((item) => (
              <div
                key={item.id}
                className="card"
                style={{
                  padding: '1.5rem',
                  display: 'flex',
                  flexDirection: 'column',
                  justifyContent: 'space-between',
                  borderTop: '3px solid var(--brand-blue)'
                }}
              >
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                    <span style={{ fontSize: '0.725rem', fontWeight: '700', textTransform: 'uppercase', color: 'var(--brand-blue)', letterSpacing: '0.04em' }}>
                      {item.category}
                    </span>
                    <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.3rem', fontSize: '0.725rem', color: '#10B981', fontWeight: '700', backgroundColor: '#D1FAE5', padding: '0.15rem 0.5rem', borderRadius: '4px' }}>
                      <Zap size={12} /> DIY: {item.diyTime}
                    </span>
                  </div>

                  <h3 style={{ fontSize: '1rem', fontWeight: '700', color: 'var(--text-main)', marginBottom: '0.75rem' }}>
                    {item.title}
                  </h3>

                  <div style={{ backgroundColor: '#FEF3C7', padding: '0.65rem 0.85rem', borderRadius: '6px', marginBottom: '0.85rem' }}>
                    <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem', fontSize: '0.75rem', fontWeight: '750', color: '#92400E', marginBottom: '0.15rem' }}>
                      <Search size={13} /> Why it occurs:
                    </span>
                    <span style={{ fontSize: '0.8rem', color: '#78350F', display: 'block' }}>
                      {item.cause}
                    </span>
                  </div>

                  <div style={{ backgroundColor: '#EFF6FF', padding: '0.65rem 0.85rem', borderRadius: '6px', marginBottom: '1rem' }}>
                    <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem', fontSize: '0.75rem', fontWeight: '750', color: '#1E40AF', marginBottom: '0.15rem' }}>
                      <Wrench size={13} /> Quick Fix Solution:
                    </span>
                    <span style={{ fontSize: '0.8rem', color: '#1E3A8A', display: 'block' }}>
                      {item.solution}
                    </span>
                  </div>
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderTop: '1px solid var(--border-light)', paddingTop: '0.75rem' }}>
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Problem still persists?</span>
                  <Link to="/tickets/new" className="btn btn-secondary btn-sm" style={{ fontWeight: '600' }}>
                    Report Ticket →
                  </Link>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
