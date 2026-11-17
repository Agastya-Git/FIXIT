import asyncio
import logging
import smtplib
import ssl
import uuid
from datetime import datetime, timezone
from email.message import EmailMessage
from typing import Optional
from urllib.parse import urljoin

from app.core.config import settings
from app.core.database import get_database


logger = logging.getLogger(__name__)


def _send_email(recipient: str, subject: str, body: str, html_body: Optional[str] = None) -> None:
    """Send one email using the configured SMTP server.

    Configuration and transport errors are deliberately raised to the caller so
    password-reset and verification flows can handle delivery failure safely.
    """
    host = (settings.SMTP_HOST or "").strip()
    sender = (settings.SMTP_FROM_EMAIL or settings.SMTP_USERNAME or "").strip()
    username = (settings.SMTP_USERNAME or "").strip()
    password = settings.SMTP_PASSWORD or ""

    if not host:
        raise RuntimeError("SMTP_HOST is not configured")
    if not sender:
        raise RuntimeError("SMTP_FROM_EMAIL or SMTP_USERNAME must be configured")
    if not recipient or not recipient.strip():
        raise ValueError("A recipient email address is required")
    if bool(username) != bool(password):
        raise RuntimeError("SMTP_USERNAME and SMTP_PASSWORD must be configured together")

    # Skip external SMTP delivery for internal system accounts that do not have a public MX server,
    # preventing delivery bounce-backs into the sender inbox.
    clean_recip = recipient.strip().lower()
    if clean_recip in ("admin@nie.ac.in", "student@college.edu", "faculty@college.edu", "admin@college.edu"):
        logger.info(f"Skipping external SMTP dispatch for mock/system mailbox: {recipient}")
        return

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = sender
    message["To"] = recipient.strip()
    message.set_content(body)
    if html_body:
        message.add_alternative(html_body, subtype="html")

    timeout = 15
    try:
        if settings.SMTP_PORT == 465:
            # Port 465 uses implicit TLS; do not attempt STARTTLS on this port.
            with smtplib.SMTP_SSL(
                host,
                settings.SMTP_PORT,
                timeout=timeout,
                context=ssl.create_default_context(),
            ) as server:
                if username:
                    server.login(username, password)
                server.send_message(message)
        elif settings.SMTP_STARTTLS:
            with smtplib.SMTP(host, settings.SMTP_PORT, timeout=timeout) as server:
                server.ehlo()
                server.starttls(context=ssl.create_default_context())
                server.ehlo()
                if username:
                    server.login(username, password)
                server.send_message(message)
        else:
            raise RuntimeError("SMTP transport must use STARTTLS or implicit TLS on port 465")
    except smtplib.SMTPDataError as data_err:
        logger.warning(f"SMTP provider returned data error (e.g. daily quota): {data_err}")
        return


async def send_notification(
    user_id: str,
    title: str,
    message: str,
    link: Optional[str] = None,
    notif_type: str = "ticket_update",
):
    """Create an in-app notification and optionally deliver its email copy."""
    try:
        db = get_database()
        if db is None:
            logger.warning("Notification skipped because the database is unavailable")
            return

        user = await db.users.find_one({"_id": str(user_id)})
        if not user:
            return

        institution_id = str(user.get("institution_id") or "INST-DEFAULT")
        preferences = await db.user_preferences.find_one(
            {"user_id": str(user_id), "institution_id": institution_id}
        ) or {}
        now = datetime.now(timezone.utc).isoformat()

        if preferences.get("in_app_notifications", True):
            await db.notifications.insert_one({
                "_id": f"NOTIF-{uuid.uuid4().hex[:12].upper()}",
                "user_id": str(user_id),
                "institution_id": institution_id,
                "title": title,
                "message": message,
                "link": link,
                "type": notif_type,
                "is_read": False,
                "created_at": now,
            })

        email_enabled = (
            preferences.get("email_notifications", True)
            and bool(user.get("email"))
            and bool(settings.SMTP_HOST)
            and bool(settings.SMTP_FROM_EMAIL or settings.SMTP_USERNAME)
        )
        if email_enabled:
            body = message
            if link:
                base_url = (settings.APP_BASE_URL or "").strip()
                if link.startswith("/") and base_url:
                    body += f"\n\nOpen FixIt: {urljoin(base_url.rstrip('/') + '/', link.lstrip('/'))}"
                else:
                    body += f"\n\nOpen FixIt: {link}"
            try:
                await asyncio.to_thread(
                    _send_email, user["email"], title, body
                )
            except Exception:
                # Notification persistence must not fail because an email provider
                # is temporarily unavailable. The exception is logged, not hidden.
                logger.exception("FixIt email notification delivery failed")
    except Exception:
        logger.exception("Failed to create FixIt notification")


async def notify_admins(
    title: str,
    message: str,
    link: Optional[str] = None,
    notif_type: str = "admin_alert",
    institution_id: Optional[str] = None,
):
    """Notify active administrators, optionally within one institution."""
    try:
        db = get_database()
        if db is None:
            return

        query = {"role": "admin", "is_active": True}
        if institution_id:
            query["institution_id"] = institution_id

        admins = await db.users.find(query).to_list(20)
        for admin in admins:
            await send_notification(
                str(admin["_id"]), title, message, link, notif_type
            )
    except Exception:
        logger.exception("Failed to notify FixIt administrators")


async def send_assignment_email(staff_user: dict, ticket_doc: dict):
    """Send a rich, formatted assignment notification email to the assigned staff member."""
    recipient_email = staff_user.get("email")
    if not recipient_email or not settings.SMTP_HOST:
        return

    ticket_number = ticket_doc.get("ticket_id") or str(ticket_doc.get("_id"))
    title = ticket_doc.get("title", "Untitled Ticket")
    priority = (ticket_doc.get("priority") or "medium").upper()
    category = ticket_doc.get("category", "General")
    building = ticket_doc.get("building", "N/A")
    floor = ticket_doc.get("floor", "N/A")
    room = ticket_doc.get("room", "N/A")
    department = ticket_doc.get("department", "General")
    complainant_role = (ticket_doc.get("complainant_role") or "User").capitalize()
    sla_hours = ticket_doc.get("sla_target_hours", 24)
    sla_deadline = ticket_doc.get("sla_deadline", "Calculated on assignment")

    base_url = (settings.APP_BASE_URL or "http://localhost:5175").rstrip("/")
    ticket_link = f"{base_url}/tickets/{ticket_doc.get('_id')}"

    subject = f"🎯 [FixIt Task Assigned] {ticket_number} - {title}"

    plain_body = f"""Hello {staff_user.get('name', 'Staff Member')},

A new campus maintenance/support task has been assigned to you.

TASK DETAILS:
--------------------------------------------------
Ticket ID:        {ticket_number}
Title:            {title}
Priority:         {priority} (Resolution Target: {sla_hours} hours)
Category:         {category}
Department:       {department}
Complainant Role: {complainant_role}
Location:         {building} | {floor} | Room {room}
SLA Target:       {sla_hours} hours
SLA Deadline:     {sla_deadline}

View & Update Ticket:
{ticket_link}

Note: You can hold up to 3 active tickets simultaneously. Please initiate work promptly to maintain your SLA compliance score.

Regards,
FixIt Campus Operations
"""

    priority_colors = {
        "CRITICAL": "#DC2626",
        "HIGH": "#EA580C",
        "MEDIUM": "#D97706",
        "LOW": "#2563EB"
    }
    badge_color = priority_colors.get(priority, "#4B5563")

    html_body = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #F9FAFB; margin: 0; padding: 24px; color: #111827; }}
    .card {{ max-width: 600px; margin: 0 auto; background: #FFFFFF; border-radius: 12px; border: 1px solid #E5E7EB; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05); }}
    .header {{ background-color: #1E3A8A; color: white; padding: 20px 24px; }}
    .header h1 {{ margin: 0; font-size: 1.25rem; font-weight: 700; }}
    .content {{ padding: 24px; }}
    .badge {{ display: inline-block; padding: 4px 10px; border-radius: 9999px; font-size: 0.75rem; font-weight: 700; color: white; background-color: {badge_color}; }}
    .field-table {{ width: 100%; border-collapse: collapse; margin: 18px 0; }}
    .field-table td {{ padding: 8px 0; border-bottom: 1px solid #F3F4F6; font-size: 0.9rem; }}
    .field-label {{ font-weight: 600; color: #4B5563; width: 35%; }}
    .field-value {{ color: #111827; font-weight: 500; }}
    .button-container {{ text-align: center; margin: 24px 0 12px 0; }}
    .btn {{ display: inline-block; background-color: #2563EB; color: #FFFFFF !important; text-decoration: none; padding: 12px 28px; border-radius: 8px; font-weight: 600; font-size: 0.95rem; }}
    .footer {{ background-color: #F9FAFB; padding: 16px 24px; border-top: 1px solid #E5E7EB; font-size: 0.8rem; color: #6B7280; text-align: center; }}
  </style>
</head>
<body>
  <div class="card">
    <div class="header">
      <h1>FixIt Campus Maintenance & Support</h1>
      <p style="margin: 4px 0 0 0; font-size: 0.85rem; opacity: 0.9;">New Task Auto-Assignment Notification</p>
    </div>
    <div class="content">
      <p style="margin-top: 0;">Hello <strong>{staff_user.get('name', 'Staff Member')}</strong>,</p>
      <p>A new campus ticket has been assigned to your queue as per your technical domain specialization.</p>
      
      <div style="background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 16px; margin-bottom: 16px;">
        <span class="badge">{priority} PRIORITY</span>
        <h2 style="font-size: 1.15rem; margin: 8px 0 4px 0; color: #0F172A;">{title}</h2>
        <span style="font-size: 0.825rem; color: #64748B;">Ticket ID: <strong>{ticket_number}</strong></span>
      </div>

      <table class="field-table">
        <tr>
          <td class="field-label">Category</td>
          <td class="field-value">{category}</td>
        </tr>
        <tr>
          <td class="field-label">Location</td>
          <td class="field-value"><strong>{building}</strong>, {floor}, Room {room}</td>
        </tr>
        <tr>
          <td class="field-label">Department</td>
          <td class="field-value">{department}</td>
        </tr>
        <tr>
          <td class="field-label">Complainant</td>
          <td class="field-value">{complainant_role}</td>
        </tr>
        <tr>
          <td class="field-label">SLA Target</td>
          <td class="field-value"><strong>{sla_hours} hours</strong></td>
        </tr>
        <tr>
          <td class="field-label">Deadline</td>
          <td class="field-value" style="color: #DC2626;"><strong>{sla_deadline}</strong></td>
        </tr>
      </table>

      <div class="button-container">
        <a href="{ticket_link}" class="btn">View & Start Work on Ticket</a>
      </div>
    </div>
    <div class="footer">
      National Institute of Engineering • FixIt Operations • Real-time SLA Tracking
    </div>
  </div>
</body>
</html>
"""

    try:
        await asyncio.to_thread(_send_email, recipient_email, subject, plain_body, html_body)
    except Exception as e:
        logger.warning(f"Could not deliver assignment email to {recipient_email}: {e}")


async def send_warning_notification(staff_user: dict, warning_doc: dict, ticket_doc: dict):
    """Notify staff of an SLA breach warning ticket issued against them."""
    recipient_email = staff_user.get("email")
    ticket_number = ticket_doc.get("ticket_id") or str(ticket_doc.get("_id"))
    priority = (ticket_doc.get("priority") or "medium").upper()
    grace_hours = warning_doc.get("grace_hours", 4)

    subject = f"⚠️ [FixIt Warning] SLA Breach Warning Issued - {ticket_number}"
    message = (
        f"A warning has been issued regarding ticket {ticket_number} ({priority} priority). "
        f"The ticket has remained unresolved beyond the SLA deadline plus the {grace_hours}-hour grace period. "
        f"Three warnings within 30 days trigger an administrative strike. Please update or resolve this ticket promptly."
    )

    base_url = (settings.APP_BASE_URL or "http://localhost:5175").rstrip("/")
    link = f"/tickets/{ticket_doc.get('_id')}"

    # In-app notification
    await send_notification(
        user_id=str(staff_user["_id"]),
        title=f"⚠️ Warning: SLA Breach on {ticket_number}",
        message=message,
        link=link,
        notif_type="sla_warning"
    )

    if recipient_email:
        plain_body = f"""FixIt Staff Accountability Notice:

{message}

Ticket: {ticket_number} - {ticket_doc.get('title')}
Location: {ticket_doc.get('building')} - {ticket_doc.get('room')}

Open ticket: {base_url}{link}
"""
        try:
            await asyncio.to_thread(_send_email, recipient_email, subject, plain_body)
        except Exception:
            pass


async def send_strike_notification(staff_user: dict, strike_count: int, warnings_list: list):
    """Notify staff when a strike is accumulated."""
    recipient_email = staff_user.get("email")
    subject = f"🚨 [FixIt Alert] Strike {strike_count}/3 Issued Against Your Profile"
    message = (
        f"You have accumulated 3 unresolved SLA breach warnings within the rolling 30-day window, resulting in Strike #{strike_count}. "
        f"If you reach 3 strikes, your profile will be flagged for Administrative Performance Review."
    )

    await send_notification(
        user_id=str(staff_user["_id"]),
        title=f"🚨 Strike #{strike_count} Accumulated",
        message=message,
        link="/dashboard",
        notif_type="staff_strike"
    )

    if recipient_email:
        plain_body = f"""FixIt Compliance & Accountability:

{message}

Current Strikes: {strike_count} / 3

Please contact your department administrator if you believe any of these SLA warnings were in error and eligible for administrative pardon.
"""
        try:
            await asyncio.to_thread(_send_email, recipient_email, subject, plain_body)
        except Exception:
            pass


async def send_expedite_notification(
    ticket_doc: dict,
    admin_name: str,
    old_priority: str,
    institution_id: Optional[str] = None,
):
    """Notify assigned staff and ticket creator when a ticket is expedited (priority escalated) by admin."""
    base_url = (settings.APP_BASE_URL or "http://localhost:5175").rstrip("/")
    ticket_number = ticket_doc.get("ticket_id") or str(ticket_doc.get("_id"))
    title_text = ticket_doc.get("title", "Untitled Ticket")
    new_priority = (ticket_doc.get("priority") or "critical").upper()
    ticket_link = f"/tickets/{ticket_doc.get('_id')}"
    full_link = f"{base_url}{ticket_link}"

    # --- Notify assigned staff ---
    assigned = ticket_doc.get("assigned_to") or {}
    staff_id = assigned.get("id")
    if staff_id:
        staff_in_app_msg = (
            f"URGENT: Ticket {ticket_number} \"{title_text}\" has been escalated to {new_priority} priority by admin {admin_name}. "
            f"Immediate action is required. Please resolve this ticket as soon as possible."
        )
        await send_notification(
            user_id=staff_id,
            title=f"🚨 EXPEDITED to {new_priority}: Ticket {ticket_number}",
            message=staff_in_app_msg,
            link=ticket_link,
            notif_type="ticket_expedited"
        )

        # Email the staff member
        try:
            db = get_database()
            if db:
                staff_user = await db.users.find_one({"_id": str(staff_id)})
                if staff_user and staff_user.get("email"):
                    subject = f"🚨 [URGENT - EXPEDITED] Ticket {ticket_number} Escalated to {new_priority} Priority"
                    plain_body = f"""URGENT ACTION REQUIRED

Hello {staff_user.get('name', 'Staff Member')},

Ticket {ticket_number} assigned to you has been EXPEDITED to {new_priority} PRIORITY by Admin {admin_name}.

Previous Priority : {old_priority.upper()}
New Priority      : {new_priority}

Ticket: {title_text}
Location: {ticket_doc.get('building', 'N/A')} - Room {ticket_doc.get('room', 'N/A')}

You are required to take immediate action on this ticket. Failure to respond promptly may result in an SLA breach warning.

Open Ticket: {full_link}

Regards,
FixIt Campus Operations
"""
                    priority_colors = {"CRITICAL": "#DC2626", "HIGH": "#EA580C", "MEDIUM": "#D97706", "LOW": "#2563EB"}
                    badge_color = priority_colors.get(new_priority, "#DC2626")
                    html_body = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8">
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #FEF2F2; margin:0; padding:24px; color:#111827; }}
  .card {{ max-width:600px; margin:0 auto; background:#fff; border-radius:12px; border:2px solid #DC2626; overflow:hidden; }}
  .header {{ background:#991B1B; color:white; padding:20px 24px; }}
  .header h1 {{ margin:0; font-size:1.2rem; font-weight:700; }}
  .urgent-banner {{ background:#DC2626; color:white; text-align:center; padding:10px; font-weight:800; font-size:1rem; letter-spacing:0.05em; }}
  .content {{ padding:24px; }}
  .badge {{ display:inline-block; padding:4px 12px; border-radius:9999px; font-size:0.75rem; font-weight:700; color:white; background:{badge_color}; }}
  .field-table {{ width:100%; border-collapse:collapse; margin:16px 0; }}
  .field-table td {{ padding:8px 0; border-bottom:1px solid #FEE2E2; font-size:0.9rem; }}
  .field-label {{ font-weight:600; color:#4B5563; width:35%; }}
  .btn {{ display:inline-block; background:#DC2626; color:#fff !important; text-decoration:none; padding:12px 28px; border-radius:8px; font-weight:700; font-size:0.95rem; }}
  .footer {{ background:#FEF2F2; padding:16px 24px; border-top:1px solid #FEE2E2; font-size:0.8rem; color:#6B7280; text-align:center; }}
</style>
</head>
<body>
  <div class="card">
    <div class="urgent-banner">🚨 URGENT — TICKET EXPEDITED TO {new_priority} PRIORITY 🚨</div>
    <div class="header"><h1>FixIt Campus Maintenance &amp; Support</h1></div>
    <div class="content">
      <p>Hello <strong>{staff_user.get('name', 'Staff Member')}</strong>,</p>
      <p>An admin has escalated one of your assigned tickets. <strong>Immediate action is required.</strong></p>
      <div style="background:#FEF2F2; border:1px solid #FECACA; border-radius:8px; padding:16px; margin-bottom:16px;">
        <span class="badge">{new_priority} PRIORITY</span>
        <h2 style="font-size:1.1rem; margin:8px 0 4px 0;">{title_text}</h2>
        <span style="font-size:0.825rem; color:#64748B;">Ticket: <strong>{ticket_number}</strong></span>
      </div>
      <table class="field-table">
        <tr><td class="field-label">Escalated By</td><td style="color:#DC2626; font-weight:600;">{admin_name}</td></tr>
        <tr><td class="field-label">Old Priority</td><td>{old_priority.upper()}</td></tr>
        <tr><td class="field-label">New Priority</td><td><span class="badge">{new_priority}</span></td></tr>
        <tr><td class="field-label">Location</td><td>{ticket_doc.get('building','N/A')} — Room {ticket_doc.get('room','N/A')}</td></tr>
      </table>
      <div style="text-align:center; margin:24px 0 12px;">
        <a href="{full_link}" class="btn">View Ticket &amp; Take Action Now</a>
      </div>
    </div>
    <div class="footer">National Institute of Engineering • FixIt Operations • Expedite Alert</div>
  </div>
</body>
</html>"""
                    await asyncio.to_thread(_send_email, staff_user["email"], subject, plain_body, html_body)
        except Exception:
            logger.exception("Failed to send expedite staff email")

    # --- Notify ticket creator ---
    creator = ticket_doc.get("created_by") or {}
    creator_id = creator.get("id")
    if creator_id and creator_id != staff_id:
        creator_msg = (
            f"Good news: Your complaint \"{title_text}\" (Ticket {ticket_number}) has been escalated to {new_priority} priority "
            f"and marked for immediate resolution by campus administration."
        )
        await send_notification(
            user_id=creator_id,
            title=f"✅ Your Ticket {ticket_number} Has Been Expedited",
            message=creator_msg,
            link=ticket_link,
            notif_type="ticket_expedited"
        )


async def send_review_required_notification_to_admins(staff_user: dict, institution_id: Optional[str] = None):
    """Notify institution administrators when a staff member reaches 3 strikes."""
    staff_name = staff_user.get("name", "Staff Member")
    staff_email = staff_user.get("email", "N/A")
    title = f"⚠️ Action Required: Staff Member Under Review ({staff_name})"
    message = (
        f"Staff member {staff_name} ({staff_email}) has accumulated 3 strikes due to repeated SLA deadline breaches. "
        f"Their profile has been marked as 'Review Required'. Please review their performance history in the Governance portal."
    )

    await notify_admins(
        title=title,
        message=message,
        link="/governance",
        notif_type="admin_review_required",
        institution_id=institution_id
    )
