"""
AccountStateMiddleware — enforces account state on every authenticated request.

Checks:
- Account is active (not deactivated).
- Account is not suspended.
- Email verification status where required.

Stubs out cleanly until the User model is built in the next phase.
"""
import logging

logger = logging.getLogger(__name__)


class AccountStateMiddleware:
    """
    Redirect or block requests from deactivated/suspended accounts.
    Full implementation added in Phase 3 (accounts build).
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Phase 3 will add: check request.user.is_active, suspension status, etc.
        response = self.get_response(request)
        return response
