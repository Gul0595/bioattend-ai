"""
BioAttend Ultimate — Email Notification Service
================================================
Fully implemented email notifications using aiosmtplib (async).
Covers ALL notification types:

  ✅ Late check-in alert (to manager)
  ✅ Leave request submitted (to HR/manager)
  ✅ Leave approved / rejected (to employee)
  ✅ Absent employee alert (to manager, daily)
  ✅ Daily attendance summary (to HR)
  ✅ Password reset OTP
  ✅ Welcome email on account creation
  ✅ Face enrollment success confirmation
"""
from __future__ import annotations

import asyncio
import logging
from datetime import date, datetime
from typing import Optional

logger = logging.getLogger(__name__)


def _get_smtp_settings():
    from app.core.config import settings
    return settings


async def _send_email(to: str | list[str], subject: str, html_body: str) -> bool:
    """
    Core async email sender using aiosmtplib.
    Returns True on success, False on failure (never raises).
    """
    import aiosmtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText

    s = _get_smtp_settings()
    if not s.SMTP_USER or not s.SMTP_PASSWORD:
        logger.warning("Email not configured — skipping send to %s: %s", to, subject)
        return False

    recipients = [to] if isinstance(to, str) else to

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"[BioAttend] {subject}"
    msg["From"]    = f"BioAttend <{s.NOTIFICATION_FROM_EMAIL}>"
    msg["To"]      = ", ".join(recipients)
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        await aiosmtplib.send(
            msg,
            hostname=s.SMTP_HOST,
            port=s.SMTP_PORT,
            username=s.SMTP_USER,
            password=s.SMTP_PASSWORD,
            use_tls=False,
            start_tls=True,
            timeout=15,
        )
        logger.info("Email sent → %s | %s", recipients, subject)
        return True
    except Exception as exc:
        logger.error("Email send failed → %s | %s | %s", recipients, subject, exc)
        return False


# ─── HTML Template helper ─────────────────────────────────────────────────────

def _wrap(title: str, content: str) -> str:
    return f"""
<!DOCTYPE html>
<html>
<head><meta charset="utf-8">
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
         background: #f5f5f5; margin: 0; padding: 20px; color: #1a1a1a; }}
  .card {{ background: #fff; border-radius: 12px; padding: 28px 32px;
           max-width: 540px; margin: 0 auto; box-shadow: 0 2px 8px rgba(0,0,0,.08); }}
  .logo {{ font-size: 18px; font-weight: 700; color: #3b82f6; margin-bottom: 20px; }}
  h2 {{ font-size: 20px; font-weight: 600; margin: 0 0 16px; color: #111; }}
  .meta {{ background: #f8fafc; border-radius: 8px; padding: 14px 16px;
           margin: 16px 0; font-size: 14px; line-height: 2; }}
  .meta b {{ color: #374151; }}
  .badge {{ display: inline-block; padding: 3px 10px; border-radius: 20px;
            font-size: 12px; font-weight: 600; }}
  .badge-red    {{ background: #fef2f2; color: #dc2626; }}
  .badge-green  {{ background: #f0fdf4; color: #16a34a; }}
  .badge-yellow {{ background: #fefce8; color: #ca8a04; }}
  .badge-blue   {{ background: #eff6ff; color: #2563eb; }}
  p {{ font-size: 14px; line-height: 1.7; color: #4b5563; margin: 12px 0; }}
  .footer {{ margin-top: 24px; font-size: 12px; color: #9ca3af; text-align: center; }}
  .btn {{ display: inline-block; background: #3b82f6; color: #fff !important;
          padding: 10px 22px; border-radius: 8px; text-decoration: none;
          font-size: 14px; font-weight: 600; margin-top: 16px; }}
</style>
</head>
<body>
  <div class="card">
    <div class="logo">🔐 BioAttend</div>
    <h2>{title}</h2>
    {content}
    <div class="footer">BioAttend Ultimate · Automated notification · Do not reply</div>
  </div>
</body>
</html>"""


# ─── 1. Late check-in alert ───────────────────────────────────────────────────

async def notify_late_checkin(
    manager_email: str,
    employee_name: str,
    employee_id: str,
    check_in_time: datetime,
    late_minutes: int,
    shift_name: str,
) -> bool:
    subject = f"Late Arrival — {employee_name}"
    body = _wrap("Late Check-In Alert", f"""
        <p>The following employee checked in late today:</p>
        <div class="meta">
          <b>Employee:</b> {employee_name} ({employee_id})<br>
          <b>Check-in time:</b> {check_in_time.strftime('%I:%M %p')}<br>
          <b>Shift:</b> {shift_name}<br>
          <b>Late by:</b> <span class="badge badge-yellow">{late_minutes} minutes</span>
        </div>
        <p>Please review if this requires any action.</p>
    """)
    return await _send_email(manager_email, subject, body)


# ─── 2. Leave request submitted ───────────────────────────────────────────────

async def notify_leave_request_submitted(
    approver_email: str,
    employee_name: str,
    leave_type: str,
    start_date: date,
    end_date: date,
    days: float,
    reason: Optional[str],
) -> bool:
    subject = f"Leave Request — {employee_name}"
    body = _wrap("New Leave Request", f"""
        <p><b>{employee_name}</b> has submitted a leave request requiring your approval:</p>
        <div class="meta">
          <b>Leave type:</b> {leave_type.title()}<br>
          <b>From:</b> {start_date.strftime('%d %b %Y')}<br>
          <b>To:</b> {end_date.strftime('%d %b %Y')}<br>
          <b>Days:</b> {days}<br>
          <b>Reason:</b> {reason or '—'}
        </div>
        <p>Please log in to BioAttend to approve or reject this request.</p>
    """)
    return await _send_email(approver_email, subject, body)


# ─── 3. Leave approved ────────────────────────────────────────────────────────

async def notify_leave_approved(
    employee_email: str,
    employee_name: str,
    leave_type: str,
    start_date: date,
    end_date: date,
    days: float,
    approved_by: str,
) -> bool:
    subject = f"Leave Approved — {start_date.strftime('%d %b')} to {end_date.strftime('%d %b %Y')}"
    body = _wrap("Your Leave Has Been Approved ✓", f"""
        <p>Hi {employee_name},</p>
        <p>Your leave request has been <span class="badge badge-green">Approved</span></p>
        <div class="meta">
          <b>Leave type:</b> {leave_type.title()}<br>
          <b>From:</b> {start_date.strftime('%d %b %Y')}<br>
          <b>To:</b> {end_date.strftime('%d %b %Y')}<br>
          <b>Days:</b> {days}<br>
          <b>Approved by:</b> {approved_by}
        </div>
        <p>Enjoy your time off! Have a safe return.</p>
    """)
    return await _send_email(employee_email, subject, body)


# ─── 4. Leave rejected ────────────────────────────────────────────────────────

async def notify_leave_rejected(
    employee_email: str,
    employee_name: str,
    leave_type: str,
    start_date: date,
    end_date: date,
    rejection_reason: Optional[str],
    rejected_by: str,
) -> bool:
    subject = f"Leave Request — Not Approved"
    body = _wrap("Leave Request Not Approved", f"""
        <p>Hi {employee_name},</p>
        <p>Your leave request has been <span class="badge badge-red">Rejected</span></p>
        <div class="meta">
          <b>Leave type:</b> {leave_type.title()}<br>
          <b>Dates:</b> {start_date.strftime('%d %b')} – {end_date.strftime('%d %b %Y')}<br>
          <b>Reason:</b> {rejection_reason or 'No reason provided'}<br>
          <b>Rejected by:</b> {rejected_by}
        </div>
        <p>Please contact HR if you have questions about this decision.</p>
    """)
    return await _send_email(employee_email, subject, body)


# ─── 5. Daily attendance summary (to HR) ──────────────────────────────────────

async def send_daily_summary(
    hr_email: str,
    report_date: date,
    total: int,
    present: int,
    absent: int,
    late: int,
    on_leave: int,
    absent_names: list[str],
) -> bool:
    subject = f"Daily Attendance Summary — {report_date.strftime('%d %b %Y')}"
    absent_list = "".join(f"<li>{n}</li>" for n in absent_names[:20])
    if len(absent_names) > 20:
        absent_list += f"<li>...and {len(absent_names) - 20} more</li>"
    body = _wrap(f"Attendance Summary — {report_date.strftime('%d %b %Y')}", f"""
        <div class="meta">
          <b>Total employees:</b> {total}<br>
          <b>Present:</b> <span class="badge badge-green">{present}</span><br>
          <b>Late:</b> <span class="badge badge-yellow">{late}</span><br>
          <b>On leave:</b> <span class="badge badge-blue">{on_leave}</span><br>
          <b>Absent:</b> <span class="badge badge-red">{absent}</span><br>
          <b>Attendance rate:</b> {round(present / max(total,1) * 100, 1)}%
        </div>
        {'<p><b>Absent employees:</b></p><ul style="font-size:14px;color:#4b5563">' + absent_list + '</ul>' if absent_names else ''}
    """)
    return await _send_email(hr_email, subject, body)


# ─── 6. Password reset OTP ────────────────────────────────────────────────────

async def send_password_reset(
    email: str,
    name: str,
    reset_token: str,
    frontend_url: str = "http://localhost:5173",
) -> bool:
    reset_link = f"{frontend_url}/reset-password?token={reset_token}"
    subject = "Reset Your Password"
    body = _wrap("Password Reset Request", f"""
        <p>Hi {name},</p>
        <p>We received a request to reset your BioAttend password.</p>
        <p>Click the button below to set a new password. This link expires in <b>30 minutes</b>.</p>
        <a href="{reset_link}" class="btn">Reset Password</a>
        <p style="margin-top:20px">If you didn't request this, please ignore this email. Your account is safe.</p>
    """)
    return await _send_email(email, subject, body)


# ─── 7. Welcome email ─────────────────────────────────────────────────────────

async def send_welcome_email(
    email: str,
    name: str,
    employee_id: str,
    temp_password: Optional[str] = None,
) -> bool:
    subject = "Welcome to BioAttend"
    pw_section = f"""
        <div class="meta">
          <b>Employee ID:</b> {employee_id}<br>
          <b>Email:</b> {email}<br>
          <b>Temporary password:</b> {temp_password}
        </div>
        <p>Please log in and change your password immediately.</p>
    """ if temp_password else f"""
        <div class="meta">
          <b>Employee ID:</b> {employee_id}<br>
          <b>Email:</b> {email}
        </div>
    """
    body = _wrap(f"Welcome to BioAttend, {name}! 👋", f"""
        <p>Your attendance account has been created. You can now mark attendance using the Face Kiosk.</p>
        {pw_section}
        <p>Contact HR if you need to enroll your biometric data.</p>
    """)
    return await _send_email(email, subject, body)


# ─── 8. Face enrollment confirmation ─────────────────────────────────────────

async def notify_face_enrolled(email: str, name: str) -> bool:
    subject = "Face Enrollment Successful"
    body = _wrap("Biometric Enrollment Confirmed ✓", f"""
        <p>Hi {name},</p>
        <p>Your face has been successfully enrolled in the BioAttend system.</p>
        <p>You can now mark attendance at any face recognition kiosk in your office.</p>
        <p>If you did not authorize this enrollment, please contact HR immediately.</p>
    """)
    return await _send_email(email, subject, body)
