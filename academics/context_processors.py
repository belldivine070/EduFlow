"""
Academics context processor.

Injects the current academic session and term into every template render
so that the topbar and other components can display live period info
without each view having to pass it manually.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def academic_period(request):
    """
    Return the current AcademicSession and Term for the active school.

    Returns empty dict (None values) when:
    - There is no active school on the request (platform-level pages)
    - The school has no session/term marked as current yet

    Templates should always use the |default filter:
        {{ current_session.name|default:"No Session" }}
        {{ current_term.display_name|default:"No Term" }}
    """
    school = getattr(request, "school", None)
    if not school:
        return {
            "current_session": None,
            "current_term": None,
        }

    # Lazy import keeps startup clean and avoids circular imports
    from academics.models import AcademicSession, Term  # noqa: PLC0415

    current_session = (
        AcademicSession.objects.filter(school=school, is_current=True)
        .select_related("school")
        .first()
    )

    # Only look for a current term if we have a current session
    current_term = (
        Term.objects.filter(school=school, is_current=True)
        .select_related("session", "school")
        .first()
        if current_session
        else None
    )

    return {
        "current_session": current_session,
        "current_term": current_term,
    }
