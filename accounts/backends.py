"""
Custom authentication backend.

Allows login with:
- Institutional username / Staff ID / Student ID
- Email address
- Phone number (normalized to match local 080... and international +234...)
"""
import re
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.db.models import Q

User = get_user_model()


class MultiIdentifierBackend(ModelBackend):
    """
    Authenticate against username, email, or phone number.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        if not username or not password:
            return None

        identifier = username.strip()

        # Build lookup variants for phone numbers
        phone_lookups = [identifier]
        clean_digits = re.sub(r"[^\d+]", "", identifier)
        if clean_digits.startswith("+234") and len(clean_digits) == 14:
            phone_lookups.append("0" + clean_digits[4:])
            phone_lookups.append(clean_digits[1:])
        elif clean_digits.startswith("234") and len(clean_digits) == 13:
            phone_lookups.append("0" + clean_digits[3:])
            phone_lookups.append("+" + clean_digits)
        elif clean_digits.startswith("0") and len(clean_digits) == 11:
            phone_lookups.append("+234" + clean_digits[1:])
            phone_lookups.append("234" + clean_digits[1:])

        # Match username, email, or any phone variant
        lookup = (
            Q(username__iexact=identifier)
            | Q(email__iexact=identifier)
            | Q(phone_number__in=phone_lookups)
        )

        try:
            users = User.objects.filter(lookup)
            for user in users:
                if user.check_password(password) and self.user_can_authenticate(user):
                    return user
        except Exception:
            return None

        return None
