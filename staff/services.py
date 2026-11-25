"""
Staff services.

Covers staff onboarding helpers and daily staff attendance management.
"""
from django.db import transaction
from django.utils import timezone
from staff.models import (
    StaffProfile,
    StaffAttendance,
    STAFF_ATTENDANCE_PRESENT,
)
from accounts.models import User


@transaction.atomic
def record_staff_attendance(
    *,
    school,
    date,
    marked_by: User = None,
    attendance_records: list[dict],
) -> int:
    """
    Bulk records or updates daily staff attendance.
    attendance_records is a list of dicts:
    [
        {
            "staff_id": "...", 
            "status": "present"|"absent"|"late"|"excused"|"on_leave",
            "time_in": "07:45" (optional),
            "time_out": "16:00" (optional),
            "remarks": "..."
        },
        ...
    ]
    Returns count of records saved.
    """
    count = 0
    for record in attendance_records:
        staff_id = record.get("staff_id")
        status = record.get("status", STAFF_ATTENDANCE_PRESENT)
        time_in = record.get("time_in") or None
        time_out = record.get("time_out") or None
        remarks = record.get("remarks", "").strip()

        staff_profile = StaffProfile.objects.filter(id=staff_id, school=school).first()
        if not staff_profile:
            continue

        defaults = {
            "status": status,
            "marked_by": marked_by,
            "remarks": remarks,
        }
        if time_in:
            defaults["time_in"] = time_in
        if time_out:
            defaults["time_out"] = time_out

        StaffAttendance.objects.update_or_create(
            school=school,
            staff=staff_profile,
            date=date,
            defaults=defaults,
        )
        count += 1

    return count
