"""
Schools services.

Complete school creation workflow:
- Creates School record
- Creates primary SchoolDomain (subdomain or custom)
- Seeds all standard Nigerian classes (Primary 1-6, JSS 1-3, SSS 1-3)
- Creates School Director user with institutional username (e.g. GS-DIR-0001)
- Assigns Director membership
- Initializes standard school AppVariables

All operations execute atomically in a single transaction.
"""
from django.db import transaction
from django.utils.text import slugify
from schools.models import School, SchoolDomain, AppVariable
from academics.services import seed_school_classes
from accounts.services import create_school_user
from core.constants import (
    ROLE_DIRECTOR,
    DEFAULT_TET_WEIGHT,
    DEFAULT_EXAM_WEIGHT,
)


@transaction.atomic
def register_school_with_director(
    *,
    school_name: str,
    school_code: str,
    primary_domain: str,
    director_first_name: str,
    director_last_name: str,
    director_email: str,
    director_password: str = None,
    director_phone: str = None,
    motto: str = "",
    student_id_prefix: str = "",
    is_domain_verified: bool = True,
) -> tuple[School, SchoolDomain, object, object]:
    """
    Onboard a brand new school on the SaaS platform.

    Atomic guarantees:
    1. School record created with normalized uppercase code & student ID prefix
    2. Primary domain registered (verified and active)
    3. Default Nigerian classes (Primary 1-6, JSS 1-3, SSS 1-3) seeded and active
    4. School Director user created with unique random staff ID
    5. Director SchoolMembership assigned
    6. Default AppVariables (TET, Exam weights, branding) initialized
    """
    code = school_code.strip().upper()
    slug = slugify(school_name)
    prefix = student_id_prefix.strip().upper() if student_id_prefix else f"{code}-STD-"

    # 1. Create School
    school = School.objects.create(
        name=school_name.strip(),
        code=code,
        slug=slug,
        motto=motto.strip(),
        student_id_prefix=prefix,
        is_active=True,
    )

    # 2. Create primary domain
    domain_record = SchoolDomain.objects.create(
        school=school,
        domain=primary_domain.strip().lower(),
        domain_type=SchoolDomain.DOMAIN_SUBDOMAIN if "." in primary_domain else SchoolDomain.DOMAIN_CUSTOM,
        is_primary=True,
        is_verified=is_domain_verified,
        is_active=True,
    )

    # 3. Seed classes and default subjects
    seed_school_classes(school)
    from academics.services import seed_default_school_subjects
    seed_default_school_subjects(school)

    # 4. Create School Director user + membership
    director_user, director_membership = create_school_user(
        school=school,
        role=ROLE_DIRECTOR,
        first_name=director_first_name.strip(),
        last_name=director_last_name.strip(),
        email=director_email.strip().lower(),
        phone_number=director_phone,
        password=director_password,
    )

    # 5. Initialize standard AppVariables
    default_vars = [
        ("SCHOOL_NAME", school.name, "Official school name"),
        ("SCHOOL_MOTTO", school.motto, "School motto"),
        ("TET_WEIGHT", str(DEFAULT_TET_WEIGHT), "Continuous assessment weight (default 30%)"),
        ("EXAM_WEIGHT", str(DEFAULT_EXAM_WEIGHT), "Examination weight (default 70%)"),
        ("PRIMARY_COLOR", "#2563eb", "Primary theme color"),
        ("SECONDARY_COLOR", "#f59e0b", "Secondary theme color"),
        ("SCHOOL_TEMPLATE", "default", "Selected theme template folder"),
    ]

    for var_name, var_value, desc in default_vars:
        AppVariable.objects.create(
            school=school,
            var_name=var_name,
            var_value=var_value,
            description=desc,
        )

    # 6. Automatically scaffold isolated static assets & templates
    scaffold_school_assets(school)

    return school, domain_record, director_user, director_membership


def scaffold_school_assets(school) -> None:
    """
    Ensure every school has its own completely isolated static and template folder.
    Guarantees no school shares static or template files, allowing independent customization.
    """
    import os
    import shutil
    from django.conf import settings

    slug = school.slug if hasattr(school, "slug") else str(school)

    # 1. Define Palettes
    PALETTES = {
        "acumen": {
            "name": "Espresso & Amber Bronze",
            "brand": {
                "50": "#fdf8f4",
                "100": "#faeee4",
                "200": "#f3d8c3",
                "500": "#8a4f26",
                "600": "#5c3317",
                "700": "#46250f",
            },
            "accent": {
                "50": "#fffbeb",
                "500": "#c27828",
                "600": "#9a5b19",
            },
            "primary_hex": "#5c3317",
            "accent_hex": "#c27828",
        },
        "blale-international-school": {
            "name": "Royal Navy & Crimson",
            "brand": {
                "50": "#f0f7ff",
                "100": "#e0effe",
                "200": "#b9ddfd",
                "500": "#2563eb",
                "600": "#1e3a8a",
                "700": "#172554",
            },
            "accent": {
                "50": "#fff1f2",
                "500": "#f43f5e",
                "600": "#e11d48",
            },
            "primary_hex": "#1e3a8a",
            "accent_hex": "#e11d48",
        },
        "heritage-school": {
            "name": "Forest Emerald & Gold",
            "brand": {
                "50": "#f0fdf4",
                "100": "#dcfce7",
                "200": "#bbf7d0",
                "500": "#10b981",
                "600": "#065f46",
                "700": "#064e3b",
            },
            "accent": {
                "50": "#fefce8",
                "500": "#eab308",
                "600": "#d97706",
            },
            "primary_hex": "#065f46",
            "accent_hex": "#d97706",
        },
    }

    # Fallback default palette
    default_palette = {
        "name": "Sapphire Blue & Amber",
        "brand": {
            "50": "#eff6ff",
            "100": "#dbeafe",
            "200": "#bfdbfe",
            "500": "#3b82f6",
            "600": "#2563eb",
            "700": "#1d4ed8",
        },
        "accent": {
            "50": "#fffbeb",
            "500": "#f59e0b",
            "600": "#d97706",
        },
        "primary_hex": "#2563eb",
        "accent_hex": "#f59e0b",
    }

    palette = PALETTES.get(slug, default_palette)

    # 2. Template Scaffold
    templates_base = settings.BASE_DIR / "templates" / "schools"
    default_template_dir = templates_base / "default"
    school_template_dir = templates_base / slug

    if not school_template_dir.exists() and default_template_dir.exists():
        shutil.copytree(default_template_dir, school_template_dir)

    # 3. Static Assets Scaffold
    static_base = settings.BASE_DIR / "static" / "schools"
    default_static_dir = static_base / "default"
    school_static_dir = static_base / slug

    if not school_static_dir.exists() and default_static_dir.exists():
        shutil.copytree(default_static_dir, school_static_dir)

    # 4. Generate school-specific tailwind.config.js
    js_dir = school_static_dir / "js"
    js_dir.mkdir(parents=True, exist_ok=True)
    tailwind_file = js_dir / "tailwind.config.js"

    brand_obj = ",\n                    ".join([f"'{k}': '{v}'" for k, v in palette["brand"].items()])
    accent_obj = ",\n                    ".join([f"'{k}': '{v}'" for k, v in palette["accent"].items()])

    tailwind_content = f"""/**
 * Tailwind CSS configuration for {palette['name']} Theme.
 * School slug: {slug}
 * Location: static/schools/{slug}/js/tailwind.config.js
 */
tailwind.config = {{
    darkMode: 'class',
    theme: {{
        extend: {{
            fontFamily: {{
                sans: ['"Plus Jakarta Sans"', 'system-ui', '-apple-system', 'sans-serif'],
                mono: ['"JetBrains Mono"', 'monospace'],
            }},
            colors: {{
                brand: {{
                    {brand_obj}
                }},
                accent: {{
                    {accent_obj}
                }}
            }},
            boxShadow: {{
                soft: '0 4px 20px -2px rgba(15, 23, 42, 0.06)',
                hover: '0 12px 30px -4px rgba(15, 23, 42, 0.12)',
                glow: '0 0 25px -5px {palette["primary_hex"]}55',
            }},
            keyframes: {{
                fadeIn: {{
                    '0%': {{ opacity: '0', transform: 'translateY(6px)' }},
                    '100%': {{ opacity: '1', transform: 'translateY(0)' }},
                }},
                slideInRight: {{
                    '0%': {{ opacity: '0', transform: 'translateX(24px)' }},
                    '100%': {{ opacity: '1', transform: 'translateX(0)' }},
                }}
            }},
            animation: {{
                'fade-in': 'fadeIn 0.25s cubic-bezier(0.16, 1, 0.3, 1) forwards',
                'slide-in': 'slideInRight 0.3s cubic-bezier(0.16, 1, 0.3, 1) forwards',
            }}
        }}
    }}
}};
"""
    tailwind_file.write_text(tailwind_content, encoding="utf-8")

    # 5. Generate school-specific theme.css
    css_dir = school_static_dir / "css"
    css_dir.mkdir(parents=True, exist_ok=True)
    theme_css_file = css_dir / "theme.css"

    css_content = f"""/**
 * School Theme Stylesheet
 * School: {slug}
 * Palette: {palette['name']}
 * Location: static/schools/{slug}/css/theme.css
 */
:root {{
    --color-brand-50: {palette['brand']['50']};
    --color-brand-100: {palette['brand']['100']};
    --color-brand-200: {palette['brand']['200']};
    --color-brand-500: {palette['brand']['500']};
    --color-brand-600: {palette['brand']['600']};
    --color-brand-700: {palette['brand']['700']};

    --color-accent-50: {palette['accent']['50']};
    --color-accent-500: {palette['accent']['500']};
    --color-accent-600: {palette['accent']['600']};

    --color-primary: {palette['primary_hex']};
    --color-accent: {palette['accent_hex']};
}}

/* Custom scrollbars matching tenant brand */
::-webkit-scrollbar {{
    width: 6px;
    height: 6px;
}}

::-webkit-scrollbar-track {{
    background: #f1f5f9;
}}

::-webkit-scrollbar-thumb {{
    background: {palette['brand']['500']};
    border-radius: 9999px;
}}

::-webkit-scrollbar-thumb:hover {{
    background: {palette['brand']['600']};
}}
"""
    theme_css_file.write_text(css_content, encoding="utf-8")


def resolve_school_template(school, relative_path: str) -> str:
    """
    Safely resolve a template path for a school tenant.
    Checks if templates/schools/<school.slug>/<relative_path> exists.
    If yes, returns 'schools/<school.slug>/<relative_path>'.
    Otherwise, returns 'schools/default/<relative_path>'.
    """
    from django.conf import settings
    if school and getattr(school, "slug", None):
        custom_path = settings.BASE_DIR / "templates" / "schools" / school.slug / relative_path
        if custom_path.exists():
            return f"schools/{school.slug}/{relative_path}"
    return f"schools/default/{relative_path}"
