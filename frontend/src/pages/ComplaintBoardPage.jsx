import React, { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import {
  ThumbsUp,
  AlertTriangle,
  Clock,
  Filter,
  Search,
  PlusCircle,
  MapPin,
  Users,
  Eye,
  CheckCircle,
  ShieldAlert,
  GraduationCap,
  Briefcase
} from 'lucide-react';
import { ticketService } from '../api/services';
import { useAuth } from '../context/AuthContext';
import PriorityBadge from '../components/PriorityBadge';
import StatusBadge from '../components/StatusBadge';
import EmptyState from '../components/EmptyState';

const ROLE_STYLES = {
  student: {
    bg: '#EFF6FF',
    color: '#1D4ED8',
    border: '#BFDBFE',
    label: 'Student',
    icon: GraduationCap
  },
  faculty: {
    bg: '#F0FDF4',
    color: '#15803D',
    border: '#BBF7D0',
    label: 'Faculty',
    icon: Briefcase
  }
};

export default function ComplaintBoardPage({ roleFilter: externalRoleFilter }) {
  const { user } = useAuth();
  const isFaculty = user?.role === 'faculty';
  const [complaints, setComplaints] = useState([]);
  const [loading, setLoading] = useState(true);
  const [roleFilter, setRoleFilter] = useState(externalRoleFilter || 'all'); // 'all' | 'student' | 'faculty'
  const [search, setSearch] = useState('');
  const [upvotingId, setUpvotingId] = useState(null);

  const fetchComplaints = useCallback(async () => {
    setLoading(true);
    try {
      const params = {};
      if (roleFilter !== 'all') {
        params.complainant_role = roleFilter;
      }
      if (search.trim()) {
        params.search = search.trim();
      }
      const { data } = await ticketService.getPublicComplaints(params);
      setComplaints(data || []);
    } catch (err) {
      console.error('Failed to load public complaints:', err);
    } finally {
      setLoading(false);
    }
  }, [roleFilter, search]);

  useEffect(() => {
    fetchComplaints();
  }, [fetchComplaints]);

  const handleUpvote = async (ticket) => {
    if (upvotingId) return;
    setUpvotingId(ticket.id);
    try {
      const { data } = await ticketService.upvoteTicket(ticket.id || ticket.ticket_id);
      setComplaints((prev) =>
        prev.map((c) => {
          if (c.id === ticket.id || c.ticket_id === ticket.ticket_id) {
            return {
              ...c,
              upvote_count: data.upvote_count ?? data.count,
              user_has_upvoted: data.upvoted
            };
          }
          return c;
        })
      );
    } catch (err) {
      console.error('Upvote failed:', err);
    } finally {
      setUpvotingId(null);
    }
  };

  return (
    <div>
      {/* Header bar */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '1rem',
          marginBottom: '1.5rem'
        }}
      >
        <div>
          <h2 style={{ fontSize: '1.35rem', fontWeight: '800', color: 'var(--text-main)', margin: 0 }}>
            Public Complaint Board
          </h2>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem', marginTop: '0.25rem', marginBottom: 0 }}>
            Browse open campus issues. Upvote common issues to increase their resolution priority.
          </p>
        </div>

        <Link to="/tickets/new" className="btn btn-primary btn-sm" style={{ fontWeight: '600' }}>
          <PlusCircle size={16} /> Report an Issue
        </Link>
      </div>

      {/* Filter and Search Bar */}
      <div
        className="card"
        style={{
          padding: '1rem 1.25rem',
          marginBottom: '1.5rem',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '1rem'
        }}
      >
        {/* Search */}
        <div style={{ position: 'relative', flex: '1', minWidth: '240px' }}>
          <Search
            size={16}
            style={{ position: 'absolute', left: '0.85rem', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }}
          />
          <input
            type="text"
            className="form-control"
            placeholder="Search complaints by title, room, keywords..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            style={{ paddingLeft: '2.5rem', fontSize: '0.875rem' }}
          />
        </div>

        {/* Role segregation filters for faculty / portal */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontWeight: '600' }}>Category:</span>
          {['all', 'student', 'faculty'].map((rf) => {
            const active = roleFilter === rf;
            return (
              <button
                key={rf}
                type="button"
                onClick={() => setRoleFilter(rf)}
                style={{
                  padding: '0.4rem 0.85rem',
                  borderRadius: '6px',
                  border: active ? '1px solid var(--primary-navy)' : '1px solid var(--border-color)',
                  backgroundColor: active ? 'var(--primary-navy)' : 'var(--bg-main)',
                  color: active ? '#FFFFFF' : 'var(--text-main)',
                  fontSize: '0.8rem',
                  fontWeight: active ? '700' : '500',
                  cursor: 'pointer',
                  transition: 'all 0.15s ease'
                }}
              >
                <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}>
                  {rf === 'student' && <GraduationCap size={14} />}
                  {rf === 'faculty' && <Briefcase size={14} />}
                  {rf === 'all' ? 'All Roles' : rf === 'student' ? 'Students' : 'Faculty'}
                </span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Complaints List */}
      {loading ? (
        <div style={{ padding: '3.5rem', textAlign: 'center', color: 'var(--text-muted)' }}>
          Loading public complaints...
        </div>
      ) : complaints.length === 0 ? (
        <EmptyState
          title="No open public complaints found"
          description="There are currently no open public complaints matching your criteria. Encountering an issue? Be the first to report it!"
          action={
            <Link to="/tickets/new" className="btn btn-primary btn-sm">
              <PlusCircle size={14} /> Report an Issue
            </Link>
          }
        />
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          {complaints.map((item, index) => {
            const roleKey = item.complainant_role || 'student';
            const roleStyle = ROLE_STYLES[roleKey] || ROLE_STYLES.student;
            const RoleIcon = roleStyle.icon;
            const hasUpvoted = item.user_has_upvoted;
            const isCritical = item.priority === 'critical';

            return (
              <div
                key={item.id || item.ticket_id}
                className="card"
                style={{
                  padding: '1.25rem 1.5rem',
                  display: 'flex',
                  gap: '1.25rem',
                  alignItems: 'flex-start',
                  borderLeft: isCritical ? '4px solid #EF4444' : item.priority === 'high' ? '4px solid #F59E0B' : '1px solid var(--border-color)',
                  transition: 'transform 0.15s ease, box-shadow 0.15s ease'
                }}
              >
                {/* Upvote Button Column */}
                <button
                  type="button"
                  onClick={() => handleUpvote(item)}
                  disabled={upvotingId === item.id}
                  title={hasUpvoted ? 'Remove upvote' : 'I also have this problem! Upvote to raise priority'}
                  style={{
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '0.25rem',
                    minWidth: '58px',
                    padding: '0.6rem 0.5rem',
                    borderRadius: '8px',
                    border: hasUpvoted ? '2px solid var(--brand-blue)' : '1px solid var(--border-color)',
                    backgroundColor: hasUpvoted ? 'var(--brand-blue-light, #EFF6FF)' : 'var(--bg-main)',
                    color: hasUpvoted ? 'var(--brand-blue)' : 'var(--text-muted)',
                    cursor: 'pointer',
                    flexShrink: 0,
                    transition: 'all 0.15s ease'
                  }}
                >
                  <ThumbsUp size={18} fill={hasUpvoted ? 'currentColor' : 'none'} />
                  <span style={{ fontSize: '0.85rem', fontWeight: '800' }}>{item.upvote_count || 0}</span>
                  <span style={{ fontSize: '0.65rem', textTransform: 'uppercase', letterSpacing: '0.02em' }}>
                    {hasUpvoted ? 'Voted' : 'Upvote'}
                  </span>
                </button>

                {/* Complaint Details */}
                <div style={{ flex: 1, minWidth: 0 }}>
                  {/* Top badges */}
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', alignItems: 'center', marginBottom: '0.5rem' }}>
                    <span
                      style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '0.3rem',
                        fontSize: '0.725rem',
                        fontWeight: '700',
                        padding: '0.2rem 0.6rem',
                        borderRadius: '999px',
                        backgroundColor: roleStyle.bg,
                        color: roleStyle.color,
                        border: `1px solid ${roleStyle.border}`
                      }}
                    >
                      <RoleIcon size={12} />
                      {roleStyle.label}
                    </span>

                    <PriorityBadge priority={item.priority} />
                    <StatusBadge status={item.status} />

                    <span style={{ fontSize: '0.75rem', fontFamily: 'monospace', color: 'var(--text-muted)' }}>
                      #{item.ticket_id}
                    </span>

                    <span
                      style={{
                        marginLeft: 'auto',
                        fontSize: '0.75rem',
                        color: 'var(--text-muted)',
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '0.25rem'
                      }}
                    >
                      <Clock size={12} />
                      {item.created_at ? new Date(item.created_at).toLocaleDateString() : 'Recent'}
                    </span>
                  </div>

                  {/* Title */}
                  <h3 style={{ fontSize: '1.05rem', fontWeight: '700', color: 'var(--text-main)', marginBottom: '0.4rem' }}>
                    {item.title}
                  </h3>

                  {/* Description */}
                  <p
                    style={{
                      fontSize: '0.875rem',
                      color: 'var(--text-muted)',
                      marginBottom: '0.75rem',
                      lineHeight: '1.45',
                      overflow: 'hidden',
                      display: '-webkit-box',
                      WebkitLineClamp: 2,
                      WebkitBoxOrient: 'vertical'
                    }}
                  >
                    {item.description}
                  </p>

                  {/* Image thumbnail if attached */}
                  {item.image_url && (
                    <div style={{ marginBottom: '0.75rem' }}>
                      <img
                        src={item.image_url}
                        alt="Issue attachment"
                        style={{
                          maxHeight: '140px',
                          borderRadius: '6px',
                          border: '1px solid var(--border-color)',
                          objectFit: 'cover'
                        }}
                      />
                    </div>
                  )}

                  {/* Meta footer: Location & Affected scale */}
                  <div
                    style={{
                      display: 'flex',
                      flexWrap: 'wrap',
                      gap: '1.25rem',
                      fontSize: '0.8rem',
                      color: 'var(--text-subtle, var(--text-muted))',
                      borderTop: '1px solid var(--border-light, #F3F4F6)',
                      paddingTop: '0.5rem',
                      alignItems: 'center'
                    }}
                  >
                    <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}>
                      <MapPin size={14} color="var(--brand-blue)" />
                      {item.building} {item.floor ? `· ${item.floor}` : ''} {item.room ? `· ${item.room}` : ''}
                    </span>

                    <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}>
                      <Users size={14} color="var(--primary-navy)" />
                      <strong>{item.affected_users || 1}</strong> users affected
                    </span>

                    <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                      Category: <strong>{item.category}</strong>
                    </span>

                    <Link
                      to={`/tickets/${item.id || item.ticket_id}`}
                      style={{
                        marginLeft: 'auto',
                        fontSize: '0.8rem',
                        color: 'var(--brand-blue)',
                        fontWeight: '700',
                        textDecoration: 'none'
                      }}
                    >
                      View Discussion & Updates →
                    </Link>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
