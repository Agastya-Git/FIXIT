import React, { useState, useEffect, useMemo } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { PlusCircle, AlertTriangle, ArrowRight, ExternalLink, Upload, Image as ImageIcon, Globe, Lock } from 'lucide-react';
import PriorityBadge from '../components/PriorityBadge';
import { ticketService, categoryService, campusService, knowledgeBaseService } from '../api/services';
import { useAuth } from '../context/AuthContext';
import SLAIndicator from '../components/SLAIndicator';

// Extensive list of 40+ campus categories for the single category dropdown
const CAMPUS_CATEGORIES = [
  "Wi-Fi & Wireless Connectivity",
  "LAN, Ethernet & Network Cables",
  "Network Switches, Routers & Firewalls",
  "Desktop Computers & Lab Workstations",
  "Laptops & Portable Devices",
  "Monitors, Screens & Displays",
  "Keyboards, Mice & Input Peripherals",
  "Classroom Projectors & Screens",
  "Interactive Smart Boards & Digital Displays",
  "Audio Systems, Microphones & Speakers",
  "Digital Podium & AV Equipment",
  "Operating System & Boot Errors",
  "Software Installation & Applications",
  "Software Licenses & Key Activation",
  "Compiler, IDE & Development Tools",
  "Campus ERP, Student Portal & Marks Entry",
  "College Email & Account Access",
  "Antivirus, Security & Malware",
  "Printers, Scanners & Copiers",
  "Power Sockets & Electrical Outlets",
  "Ceiling Fans & Regulators",
  "Air Conditioning (AC) & Cooling",
  "Lighting, Tube Lights & Bulbs",
  "Electrical Switchboards, MCB & Breakers",
  "UPS & Power Backup Battery",
  "Drinking Water Coolers & Purifiers",
  "Restrooms, Plumbing & Sanitation",
  "Student Benches, Desks & Classroom Seating",
  "Faculty Desks, Chairs & Office Furniture",
  "Doors, Windows, Glass & Locks",
  "Whiteboards, Notice Boards & Markers",
  "Elevators, Lifts & Accessibility",
  "CCTV Cameras & Campus Surveillance",
  "Laboratory Apparatus & Test Instruments",
  "Hostel Accommodation & Facilities",
  "Library Workstations & RFID Scanners",
  "Auditorium Stage Sound & Lighting",
  "Cafeteria Facilities & Dining Area",
  "Sports Complex & Gymnasium Equipment",
  "General Campus Facilities & Maintenance"
];

// 22 Predefined Campus Buildings
const PREDEFINED_BUILDINGS = [
  "Main Academic Block",
  "Computer Science & Engineering (CSE) Block",
  "Electronics & Communication (ECE) Block",
  "Mechanical Engineering Block",
  "Electrical Engineering Block",
  "Civil Engineering Block",
  "Information Science Block",
  "Central Library & Information Center",
  "Advanced Computing & Data Science Lab Block",
  "Administrative & Dean Block",
  "Main Auditorium & Convention Hall",
  "Central Workshop & Manufacturing Lab Block",
  "Basic Sciences & Research Block",
  "Boys Hostel Block A",
  "Boys Hostel Block B",
  "Girls Hostel Block A",
  "Girls Hostel Block B",
  "Sports Complex & Indoor Gymnasium",
  "Placement & Corporate Relations Block",
  "Cafeteria & Student Center",
  "Health Center & Campus Clinic",
  "Campus Outdoor / Ground Facilities"
];

// Predefined Floors
const PREDEFINED_FLOORS = [
  "Basement Level",
  "Ground Floor",
  "1st Floor",
  "2nd Floor",
  "3rd Floor",
  "4th Floor",
  "5th Floor",
  "6th Floor",
  "Rooftop / Terrace",
  "Outdoor / Ground Area",
  "Other"
];

// Predefined Rooms & Locations
const PREDEFINED_ROOMS = [
  "Classroom 101", "Classroom 102", "Classroom 103", "Classroom 104",
  "Classroom 201", "Classroom 202", "Classroom 203", "Classroom 204",
  "Classroom 301", "Classroom 302", "Classroom 303", "Classroom 304",
  "Smart Classroom 101", "Smart Classroom 102", "Smart Classroom 201", "Smart Classroom 202",
  "Computer Lab 1 (Programming)", "Computer Lab 2 (Data Science)", "Computer Lab 3 (AI & ML)", "Computer Lab 4 (Networks)",
  "Hardware & Microprocessor Lab", "Electronics & VLSI Lab", "Embedded Systems Lab",
  "Physics Laboratory", "Chemistry Laboratory", "Mechanical CAD/CAM Lab",
  "Seminar Hall 1", "Seminar Hall 2", "Conference Board Room", "Executive Meeting Room",
  "Faculty Chamber - Ground Floor", "Faculty Chamber - 1st Floor", "Faculty Chamber - 2nd Floor", "Staff Common Room",
  "Department HOD Office", "Administrative Office Counter", "Accounts & Examination Section",
  "Server Room / IT Data Center", "Network Distribution Room (MDF)",
  "Central Library - Reading Hall", "Central Library - Digital Resource Center",
  "Main Auditorium Stage", "Workshop Floor", "Student Activity Center", "Campus Cafeteria",
  "Hostel Room", "Hostel Study Hall", "Sports Gym Area"
];

export default function CreateTicketPage() {
  const { user } = useAuth();
  const navigate = useNavigate();

  const [categories, setCategories] = useState([]);
  const [campuses, setCampuses] = useState([]);
  const [hierarchy, setHierarchy] = useState([]);
  const [customLocations, setCustomLocations] = useState([]);
  const [suggestedArticles, setSuggestedArticles] = useState([]);
  const [duplicates, setDuplicates] = useState([]);
  const [hasRestrictedDuplicates, setHasRestrictedDuplicates] = useState(false);

  const [formData, setFormData] = useState({
    title: '',
    description: '',
    problem_domain: 'technical',
    location_type: 'campus',
    category: '',
    priority: null, // Initially not set
    campus_id: '',
    building: '',
    floor: '',
    room: '',
    department: user?.department || '',
    affected_users: 1,
    visibility: 'public',
    image_url: null,
  });

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [imagePreview, setImagePreview] = useState(null);

  // Fetch categories & full dynamic campus hierarchy
  useEffect(() => {
    const initData = async () => {
      try {
        const [catsRes, campusesRes, hierRes] = await Promise.all([
          categoryService.getCategories(),
          campusService.getCampuses(),
          campusService.getHierarchy()
        ]);
        const cats = catsRes.data || [];
        const campusRows = campusesRes.data || [];
        const blds = hierRes.data?.buildings || [];

        setCategories(cats);
        setCampuses(campusRows);
        setHierarchy(blds);
        setCustomLocations(hierRes.data?.locations || []);
        if (campusRows.length > 0) {
          setFormData(prev => ({ ...prev, campus_id: prev.campus_id || campusRows[0].id }));
        }
      } catch (err) {
        console.error("Failed to load ticket initial data:", err);
      }
    };
    initData();
  }, []);

  // Priority and Category Auto-Detection Hook
  // Triggers ONLY once BOTH Title and Description have been provided!
  useEffect(() => {
    const hasTitle = formData.title.trim().length >= 4;
    const hasDesc = formData.description.trim().length >= 5;

    if (hasTitle && hasDesc) {
      const timer = setTimeout(async () => {
        try {
          const res = await ticketService.mlClassify({
            title: formData.title,
            description: formData.description,
            affected_users: parseInt(formData.affected_users, 10) || 1,
            category: formData.category || undefined
          });
          const result = res.data;
          setFormData(prev => ({
            ...prev,
            priority: result.priority || 'medium',
            category: prev.category || result.category || 'Wi-Fi & Wireless Connectivity',
            problem_domain: prev.problem_domain || result.problem_domain || 'technical',
          }));
        } catch (e) {
          console.error('Classification error:', e);
        }
      }, 400);
      return () => clearTimeout(timer);
    } else {
      // In the start or if either field is cleared, level is not set!
      setFormData(prev => ({ ...prev, priority: null }));
    }
  }, [formData.title, formData.description, formData.affected_users]);

  const handleImageFileChange = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (file.size > 5 * 1024 * 1024) {
      setError('Image file must be under 5MB.');
      return;
    }
    const reader = new FileReader();
    reader.onloadend = () => {
      setImagePreview(reader.result);
      setFormData(prev => ({ ...prev, image_url: reader.result }));
    };
    reader.readAsDataURL(file);
  };

  // Fetch suggested KB articles when category changes
  useEffect(() => {
    if (formData.category) {
      knowledgeBaseService.getArticles({ category: formData.category })
        .then(res => setSuggestedArticles(res.data?.articles || []))
        .catch(err => console.error(err));
    }
  }, [formData.category]);

  // Real-time Duplicate Detection (debounced)
  useEffect(() => {
    if (formData.title.length >= 6 && formData.building && formData.room) {
      const timer = setTimeout(async () => {
        try {
          const res = await ticketService.checkDuplicates({
            title: formData.title,
            category: formData.category,
            building: formData.building,
            room: formData.room,
            campus_id: formData.campus_id || null
          });
          setDuplicates(res.data.potential_duplicates || []);
          setHasRestrictedDuplicates(Boolean(res.data.has_restricted_matches));
        } catch (e) {
          console.error(e);
        }
      }, 500);
      return () => clearTimeout(timer);
    } else {
      setDuplicates([]);
      setHasRestrictedDuplicates(false);
    }
  }, [formData.title, formData.category, formData.campus_id, formData.building, formData.room]);

  // Comprehensive buildings list
  // Campus buildings: dynamic hierarchy buildings first, followed by general list
  const configuredBuildings = useMemo(() => {
    return hierarchy.map(b => b.name).filter(Boolean);
  }, [hierarchy]);

  // When configured buildings exist, show ONLY those to prevent building name mismatches
  const allBuildings = useMemo(() => {
    if (configuredBuildings.length > 0) return configuredBuildings;
    return PREDEFINED_BUILDINGS;
  }, [configuredBuildings]);

  // Resolve selected building
  const selectedBuildingObj = hierarchy.find(
    b => b.name?.toLowerCase() === formData.building?.trim().toLowerCase()
  );

  // Floors: configured floors for selected building first
  const configuredFloors = useMemo(() => {
    if (selectedBuildingObj && selectedBuildingObj.floors?.length > 0) {
      return selectedBuildingObj.floors.map(f => f.floor_name).filter(Boolean);
    }
    return [];
  }, [selectedBuildingObj]);

  // When configured floors exist for the selected building, show ONLY those
  // (prevents user from picking e.g. "1st Floor" when DB has "First Floor")
  const allFloors = useMemo(() => {
    if (configuredFloors.length > 0) return configuredFloors;
    return PREDEFINED_FLOORS;
  }, [configuredFloors]);

  // Resolve selected floor
  const selectedFloorObj = selectedBuildingObj?.floors?.find(
    f => f.floor_name?.toLowerCase() === formData.floor?.trim().toLowerCase()
  );

  // Rooms: configured rooms for selected floor first with department metadata
  const configuredRooms = useMemo(() => {
    if (selectedFloorObj?.rooms?.length > 0) {
      return selectedFloorObj.rooms.map(r => ({
        value: r.room_number,
        label: `${r.room_number}${r.room_name ? ` - ${r.room_name}` : ''}${r.department ? ` (${r.department})` : ''}`,
        department: r.department || ''
      }));
    }
    return [];
  }, [selectedFloorObj]);

  const allRooms = useMemo(() => {
    // When configured rooms exist for selected floor, show ONLY those.
    // This prevents submitting values like "Classroom 101" that the backend
    // cannot validate against the room hierarchy.
    if (configuredRooms.length > 0) {
      return { configured: configuredRooms, additional: [] };
    }
    // No configured rooms → fall back to predefined list
    return { configured: [], additional: PREDEFINED_ROOMS };
  }, [configuredRooms]);

  // Comprehensive categories list
  const allCategories = useMemo(() => {
    const set = new Set(CAMPUS_CATEGORIES);
    categories.forEach(c => {
      if (c.name) set.add(c.name);
    });
    return Array.from(set);
  }, [categories]);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => {
      if (name === 'building') return { ...prev, building: value, floor: '', room: '' };
      if (name === 'floor') return { ...prev, floor: value, room: '' };
      if (name === 'room') {
        const found = configuredRooms.find(r => r.value === value);
        return {
          ...prev,
          room: value,
          department: found?.department || prev.department
        };
      }
      return { ...prev, [name]: value };
    });
  };

  // Map priority to SLA target
  const slaTargetMap = {
    critical: 2,
    high: 8,
    medium: 24,
    low: 72
  };
  const activeSlaTarget = formData.priority ? (slaTargetMap[formData.priority] || 24) : null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (formData.location_type === 'campus' &&
        ((campuses.length > 0 && !formData.campus_id) || !formData.building || !formData.floor || !formData.room)) {
      setError('Please select a campus and provide a valid Building, Floor, and Room, or choose a non-campus location type.');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const resolvedPriority = formData.priority || 'medium';
      const payload = {
        title: formData.title,
        description: formData.description,
        problem_domain: formData.problem_domain || 'technical',
        location_type: formData.location_type,
        category: formData.category || 'General Campus Facilities & Maintenance',
        priority: resolvedPriority,
        campus_id: formData.location_type === 'campus' ? (formData.campus_id || null) : null,
        building: formData.location_type === 'campus' ? (formData.building || 'Not specified') : 'Not applicable',
        floor: formData.location_type === 'campus' ? (formData.floor || 'Ground Floor') : 'Not applicable',
        room: formData.location_type === 'campus' ? (formData.room || 'Not specified') : 'Not applicable',
        department: formData.department || null,
        affected_users: parseInt(formData.affected_users, 10) || 1,
        visibility: formData.visibility || 'public',
        image_url: formData.image_url || null
      };

      const res = await ticketService.createTicket(payload, true);
      const createdTicket = res.data;
      navigate(`/tickets/${createdTicket.id}`);
    } catch (err) {
      console.error(err);
      setError(err.response?.data?.detail || 'Failed to submit ticket. Please check location details and try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ maxWidth: '850px', margin: '0 auto', paddingBottom: '3rem' }}>
      <div style={{ marginBottom: '1.75rem' }}>
        <h1 style={{ fontSize: '1.75rem', fontWeight: '800', color: 'var(--text-main)', letterSpacing: '-0.025em' }}>
          Report a Campus Issue
        </h1>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem', marginTop: '0.25rem' }}>
          Submit a ticket to campus IT and facilities support. We track resolution targets based on issue severity and location.
        </p>
      </div>

      <div className="card" style={{ padding: '2rem' }}>
        {error && (
          <div role="alert" style={{
            backgroundColor: '#FEE2E2',
            border: '1px solid #FCA5A5',
            color: '#991B1B',
            padding: '1rem',
            borderRadius: '8px',
            marginBottom: '1.5rem',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem'
          }}>
            <AlertTriangle size={18} />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit}>
          {/* Issue Title */}
          <div className="form-group" style={{ marginBottom: '1.25rem' }}>
            <label className="form-label" htmlFor="ticket-title">Issue Title *</label>
            <input
              id="ticket-title"
              type="text"
              name="title"
              className="form-control"
              placeholder="e.g. Wi-Fi router blackout in CSE Lab 101 affecting 30 students"
              value={formData.title}
              onChange={handleChange}
              minLength={5}
              maxLength={150}
              required
            />
          </div>

          {/* Description */}
          <div className="form-group" style={{ marginBottom: '1.25rem' }}>
            <label className="form-label" htmlFor="ticket-desc">Detailed Description *</label>
            <textarea
              id="ticket-desc"
              name="description"
              className="form-control"
              rows={4}
              placeholder="Describe what happened, any error messages shown, and steps you already tried..."
              value={formData.description}
              onChange={handleChange}
              minLength={10}
              maxLength={5000}
              required
            />
          </div>

          {/* Location Scope */}
          <div className="grid-2" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1.25rem', marginBottom: '1.25rem' }}>
            <div className="form-group">
              <label className="form-label" htmlFor="location-type">Where does this problem apply? *</label>
              <select id="location-type" name="location_type" className="form-control" value={formData.location_type} onChange={handleChange} required>
                <option value="campus">At a campus location</option>
                <option value="remote">Online / remote</option>
                <option value="not_applicable">No specific location</option>
              </select>
            </div>

            {/* Category Dropdown (Extensive Options, Subcategory Removed) */}
            <div className="form-group">
              <label className="form-label">Category *</label>
              <select
                name="category"
                className="form-control"
                value={formData.category}
                onChange={handleChange}
                required
              >
                <option value="">Select an issue category</option>
                {allCategories.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {formData.location_type === 'campus' && (
            <>
              {/* Campus selection if multiple exist */}
              {campuses.length > 0 && (
                <div className="form-group" style={{ maxWidth: '420px', marginBottom: '1.25rem' }}>
                  <label className="form-label" htmlFor="ticket-campus">Campus *</label>
                  <select id="ticket-campus" name="campus_id" className="form-control" value={formData.campus_id} onChange={e => setFormData(prev => ({ ...prev, campus_id: e.target.value, building: '', floor: '', room: '' }))} required={formData.location_type === 'campus'}>
                    <option value="">Select campus</option>
                    {campuses.map(campus => <option key={campus.id} value={campus.id}>{campus.name}</option>)}
                  </select>
                </div>
              )}

              {/* Location Details: Building, Floor, Room Dropdowns */}
              <div className="grid-3" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '1.25rem', marginBottom: '1.25rem' }}>
                {/* Campus Building */}
                <div className="form-group">
                  <label className="form-label">Campus Building *</label>
                  <select
                    name="building"
                    className="form-control"
                    value={formData.building}
                    onChange={handleChange}
                    required={formData.location_type === 'campus'}
                  >
                    <option value="">Select Building</option>
                    {allBuildings.map((b) => (
                      <option key={b} value={b}>
                        {b}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Floor */}
                <div className="form-group">
                  <label className="form-label">Floor *</label>
                  <select
                    name="floor"
                    className="form-control"
                    value={formData.floor}
                    onChange={handleChange}
                    required={formData.location_type === 'campus'}
                  >
                    <option value="">Select Floor</option>
                    {allFloors.map((flr) => (
                      <option key={flr} value={flr}>
                        {flr}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Room / Location */}
                <div className="form-group">
                  <label className="form-label">Room / Classroom / Lab *</label>
                  <select
                    name="room"
                    className="form-control"
                    value={formData.room}
                    onChange={handleChange}
                    required={formData.location_type === 'campus'}
                  >
                    <option value="">Select Room / Location</option>
                    {allRooms.configured?.length > 0 && (
                      <optgroup label="Campus Configured Rooms">
                        {allRooms.configured.map((rm) => (
                          <option key={rm.value} value={rm.value}>
                            {rm.label}
                          </option>
                        ))}
                      </optgroup>
                    )}
                    {allRooms.additional?.length > 0 && (
                      <optgroup label={allRooms.configured?.length > 0 ? "Other Rooms & Facilities" : "Campus Rooms & Facilities"}>
                        {allRooms.additional.map((rm) => (
                          <option key={rm} value={rm}>
                            {rm}
                          </option>
                        ))}
                      </optgroup>
                    )}
                  </select>
                </div>
              </div>
            </>
          )}

          {/* Department, Affected Users, Priority Level */}
          <div className="grid-3" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '1.25rem', marginBottom: '1.25rem' }}>
            <div className="form-group">
              <label className="form-label">Department</label>
              <input
                type="text"
                name="department"
                className="form-control"
                placeholder="e.g. Computer Science"
                value={formData.department}
                onChange={handleChange}
              />
            </div>

            <div className="form-group">
              <label className="form-label">Number of Affected Users</label>
              <input
                type="number"
                name="affected_users"
                className="form-control"
                value={formData.affected_users}
                onChange={handleChange}
                min={1}
                max={5000}
              />
            </div>

            {/* Priority Level: Just heading and level, nothing else */}
            <div className="form-group">
              <label className="form-label">Priority Level</label>
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  minHeight: '44px',
                  padding: '0.5rem 0.85rem',
                  backgroundColor: 'var(--bg-main)',
                  border: '1px solid var(--border-color)',
                  borderRadius: '6px'
                }}
              >
                {formData.priority ? (
                  <PriorityBadge priority={formData.priority} />
                ) : (
                  <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                    Not set
                  </span>
                )}
              </div>
            </div>
          </div>

          {/* Visibility Classification (Public vs Private) */}
          <div className="form-group" style={{ marginTop: '1.5rem', marginBottom: '1.5rem' }}>
            <label className="form-label" style={{ fontSize: '0.95rem', fontWeight: '700' }}>
              Complaint Visibility *
            </label>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '1rem', marginTop: '0.5rem' }}>
              <label
                style={{
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: '0.75rem',
                  padding: '1rem',
                  borderRadius: '8px',
                  border: formData.visibility === 'public' ? '2px solid var(--brand-blue)' : '1px solid var(--border-color)',
                  backgroundColor: formData.visibility === 'public' ? 'var(--brand-blue-light, #EFF6FF)' : 'var(--bg-main)',
                  cursor: 'pointer',
                  transition: 'all 0.15s ease'
                }}
              >
                <input
                  type="radio"
                  name="visibility"
                  value="public"
                  checked={formData.visibility === 'public'}
                  onChange={handleChange}
                  style={{ marginTop: '0.2rem' }}
                />
                <div>
                  <strong style={{ display: 'inline-flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.9rem', color: 'var(--text-main)', marginBottom: '0.2rem' }}>
                    <Globe size={15} color="#2563EB" /> Public Complaint
                  </strong>
                  <span style={{ fontSize: '0.775rem', color: 'var(--text-muted)', lineHeight: '1.4' }}>
                    Visible on the Public Complaint Board. Other students and faculty can upvote if they face the same problem.
                  </span>
                </div>
              </label>

              <label
                style={{
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: '0.75rem',
                  padding: '1rem',
                  borderRadius: '8px',
                  border: formData.visibility === 'private' ? '2px solid var(--primary-navy)' : '1px solid var(--border-color)',
                  backgroundColor: formData.visibility === 'private' ? 'var(--brand-blue-light, #EFF6FF)' : 'var(--bg-main)',
                  cursor: 'pointer',
                  transition: 'all 0.15s ease'
                }}
              >
                <input
                  type="radio"
                  name="visibility"
                  value="private"
                  checked={formData.visibility === 'private'}
                  onChange={handleChange}
                  style={{ marginTop: '0.2rem' }}
                />
                <div>
                  <strong style={{ display: 'inline-flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.9rem', color: 'var(--text-main)', marginBottom: '0.2rem' }}>
                    <Lock size={15} color="#475569" /> Private Complaint
                  </strong>
                  <span style={{ fontSize: '0.775rem', color: 'var(--text-muted)', lineHeight: '1.4' }}>
                    Confidential. Only visible to College Administrators and the technician assigned to resolve it.
                  </span>
                </div>
              </label>
            </div>
          </div>

          {/* Picture Upload (Optional) */}
          <div className="form-group" style={{ marginBottom: '1.5rem' }}>
            <label className="form-label" style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
              <ImageIcon size={15} color="var(--brand-blue)" />
              <span>Attach Picture of Issue (Optional)</span>
            </label>
            <input
              type="file"
              accept="image/*"
              className="form-control"
              onChange={handleImageFileChange}
              style={{ padding: '0.45rem', fontSize: '0.85rem' }}
            />
            {imagePreview && (
              <div style={{ marginTop: '0.75rem', position: 'relative', display: 'inline-block' }}>
                <img
                  src={imagePreview}
                  alt="Issue attachment preview"
                  style={{ maxHeight: '160px', borderRadius: '8px', border: '1px solid var(--border-color)', objectFit: 'cover' }}
                />
                <button
                  type="button"
                  onClick={() => { setImagePreview(null); setFormData(p => ({ ...p, image_url: null })); }}
                  style={{
                    position: 'absolute',
                    top: '4px',
                    right: '4px',
                    background: 'rgba(0,0,0,0.6)',
                    color: '#fff',
                    border: 'none',
                    borderRadius: '50%',
                    width: '24px',
                    height: '24px',
                    cursor: 'pointer'
                  }}
                  title="Remove image"
                >
                  ×
                </button>
              </div>
            )}
            <small style={{ color: 'var(--text-muted)', fontSize: '0.75rem', display: 'block', marginTop: '0.3rem' }}>
              Upload a clear photo of the broken equipment, error screen, or physical damage (PNG, JPG up to 5MB).
            </small>
          </div>

          {/* SLA Target Information Panel: Changes based on determined priority */}
          <div style={{ marginTop: '1.5rem', marginBottom: '2rem' }}>
            <label className="form-label" style={{ marginBottom: '0.5rem' }}>Governing SLA Policy</label>
            {activeSlaTarget ? (
              <SLAIndicator
                isOverdue={false}
                timeRemainingMinutes={activeSlaTarget * 60}
                targetHours={activeSlaTarget}
              />
            ) : (
              <div
                style={{
                  padding: '1rem',
                  borderRadius: '8px',
                  border: '1px dashed var(--border-color)',
                  backgroundColor: 'var(--bg-main)',
                  color: 'var(--text-muted)',
                  fontSize: '0.85rem'
                }}
              >
                Resolution SLA target time will be calculated once priority level is determined.
              </div>
            )}
          </div>

          {/* Form Actions */}
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '1rem', paddingTop: '1rem', borderTop: '1px solid var(--border-color)' }}>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => navigate('/dashboard')}
              disabled={loading}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="btn btn-primary"
              disabled={loading}
              style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}
            >
              {loading ? (
                <span>Submitting Issue...</span>
              ) : (
                <>
                  <PlusCircle size={18} />
                  <span>Submit Ticket</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
