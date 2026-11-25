"""
Authentication and account forms.
"""
from django import forms
from django.contrib.auth import authenticate


class LoginForm(forms.Form):
    """
    Multi-identifier login form.
    Accepts:
    - Institutional username (e.g. GS-DIR-0001, GS-STF-0042, GS-STD-1017)
    - Email address
    - Phone number
    """

    identifier = forms.CharField(
        label="Email, Mobile Number or Username",
        widget=forms.TextInput(
            attrs={
                "class": "w-full px-4 py-3 rounded-xl border border-slate-200 bg-white text-slate-900 placeholder-slate-400 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-600 transition shadow-sm",
                "placeholder": "Enter your email, mobile number or username",
                "autocomplete": "username",
                "autofocus": True,
            }
        ),
    )
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(
            attrs={
                "class": "w-full px-4 py-3 rounded-xl border border-slate-200 bg-white text-slate-900 placeholder-slate-400 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-600 transition shadow-sm",
                "placeholder": "••••••••",
                "autocomplete": "current-password",
                "id": "password-field",
            }
        ),
    )
    remember_me = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(
            attrs={
                "class": "w-4 h-4 rounded text-blue-600 border-slate-300 focus:ring-blue-500/30 transition",
            }
        ),
    )

    def __init__(self, request=None, *args, **kwargs):
        self.request = request
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        identifier = cleaned_data.get("identifier", "").strip()
        password = cleaned_data.get("password")

        if identifier and password:
            user = authenticate(request=self.request, username=identifier, password=password)
            if not user:
                raise forms.ValidationError("Invalid credentials. Please verify your Staff/Student ID and password.")
            if not user.is_active:
                raise forms.ValidationError("This account has been deactivated. Please contact your school administrator.")

            # Deactivated school validation
            # Platform developers and superusers access the SaaS control plane and are not blocked by a single school's status
            if not (user.is_platform_developer or user.is_superuser):
                from accounts.models import SchoolMembership

                current_school = getattr(self.request, "school", None)
                if current_school:
                    # Logging in specifically to this school's portal
                    if not current_school.is_active:
                        raise forms.ValidationError(
                            "This school portal has been deactivated. Please contact support or your school administrator."
                        )
                    membership = SchoolMembership.objects.filter(user=user, school=current_school).first()
                    if not membership:
                        raise forms.ValidationError("You do not have access to this school portal.")
                    if membership.status != "active":
                        raise forms.ValidationError(
                            "Your account in this school has been deactivated. Please contact your school administrator."
                        )
                else:
                    # Global or localhost login without a school preset
                    user_memberships = SchoolMembership.objects.filter(user=user).select_related("school")
                    if not user_memberships.exists():
                        raise forms.ValidationError("No school account associated with these credentials.")

                    active_memberships = user_memberships.filter(status="active", school__is_active=True)
                    if not active_memberships.exists():
                        # Determine exact cause for clear user feedback
                        has_deactivated_school = user_memberships.filter(school__is_active=False).exists()
                        if has_deactivated_school:
                            raise forms.ValidationError(
                                "This school portal has been deactivated. Please contact support or your school administrator."
                            )
                        raise forms.ValidationError(
                            "Your account membership is currently inactive. Please contact your school administrator."
                        )

            self.user_cache = user

        return cleaned_data

    def get_user(self):
        return getattr(self, "user_cache", None)
