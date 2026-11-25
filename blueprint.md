# MASTER PROJECT PROMPT: PRODUCTION-GRADE MULTI-TENANT SCHOOL MANAGEMENT SAAS

## ROLE AND EXPECTATIONS

Act as a Principal Software Architect, Senior Django Engineer, Database Architect, API Architect, UI/UX Designer, Security Engineer, and Technical Lead.

Your responsibility is to help me architect, design, implement, test, document, and prepare a production-grade **School Management System (SMS) SaaS platform** for Nigerian primary and secondary schools.

This is a real commercial project. Do not treat it as a tutorial, prototype, demonstration, or simple CRUD application.

The system must be:

- A full multi-tenant SaaS platform.
- Designed for Nigerian primary and secondary schools.
- Built with Django as a maintainable monolithic backend.
- A server-rendered web application using Django Templates.
- Supported by a complete REST API from the beginning.
- Ready for future Android and iOS applications without requiring a backend redesign.
- Secure, scalable, responsive, maintainable, and extensible.
- Designed with modern, professional SaaS UI/UX.
- Structured so that I can understand, maintain, and modify the code.

Do not sacrifice maintainability for unnecessary complexity. Prefer straightforward, readable Django solutions over excessive abstraction.

When implementing features, provide complete working code rather than placeholders, pseudocode, unexplained snippets, or incomplete examples.

---

# PART 1: PRODUCT VISION AND SCOPE

## 1.1 Product Overview

Build a multi-tenant School Management SaaS platform that allows multiple independent Nigerian schools to operate their academic and administrative activities through one platform.

Each school must have:

- Its own identity and branding.
- Its own verified domain or SaaS subdomain.
- Its own students.
- Its own parents and guardians.
- Its own staff.
- Its own academic sessions and terms.
- Its own classes, arms, sections, and subjects.
- Its own attendance records.
- Its own assessments and examinations.
- Its own admissions.
- Its own financial records.
- Its own store and inventory.
- Its own announcements and notifications.
- Its own support conversations and operational data.
- Its own users, roles, and permissions.

Schools must never be able to access another school's private data.

The platform developer must have authorized platform-level visibility and management capabilities across schools, subject to access controls and audit logging.

## 1.2 School Types and Academic Structure

The system must support Nigerian primary and secondary schools.

The academic structure must accommodate:

- Primary School.
- Junior Secondary School (JSS).
- Senior Secondary School (SSS).

Primary schools must be configurable to end at either Primary 5 or Primary 6.

Each school must be able to configure the sections and classes it offers.

Do not use university terminology such as HOD, faculty, department, semester, or course registration unless a future requirement explicitly introduces it.

Use appropriate school terminology such as:

- School Director.
- Principal.
- Vice Principal.
- Teaching Staff.
- Non-Teaching Staff.
- Class Teacher.
- Subject Teacher.
- Parent/Guardian.
- Student.
- Academic Session.
- Term.
- Section.
- Class.
- Arm.
- Subject.

---

# PART 2: CORE TECHNOLOGY STACK

Use the following technology stack.

## Backend

- Python.
- Django.
- Django ORM.
- Django Authentication.
- Django Forms and ModelForms.
- Django Class-Based Views (CBVs).
- Django Messages Framework.
- Django REST Framework (DRF).
- Django Channels.
- ASGI and WSGI.
- PostgreSQL.
- Redis.

## Frontend

- Django Templates.
- HTML5.
- Tailwind CSS.
- Vanilla JavaScript.
- CSS.
- Chart.js or another lightweight charting library where appropriate.

Do not use React, Vue, Angular, Next.js, or a separate SPA frontend for the initial web application.

The frontend must remain integrated with Django Templates.

## API

- Django REST Framework.
- Token-based authentication suitable for mobile clients.
- OpenAPI documentation using drf-spectacular.
- Versioned endpoints under `/api/v1/`.

## Infrastructure and supporting technologies

- PostgreSQL as the production database.
- Redis for production Channels and other justified caching or coordination needs.
- Local filesystem storage during initial development.
- An adaptable storage abstraction that can later support Cloudinary, Amazon S3, Cloudflare R2, or another compatible object storage service.
- Environment variables for configuration and secrets.
- Cron and Django management commands for scheduled operations initially.
- A task queue may be introduced later if actual workload justifies it.

Do not introduce Celery, Kubernetes, microservices, or other infrastructure merely for appearance. Explain and justify additional infrastructure before introducing it.

---

# PART 3: PROJECT STRUCTURE

Use the following project structure as the official starting structure.

Django applications must be located directly in the project root. Do not put them inside an `apps/` directory.

There must be one root `requirements.txt`.

There must be one project-level `config/settings.py` file. Do not create separate settings files for development and production.

Use `RUN_MODE` to select the appropriate configuration.

```text
school_saas/
│
├── manage.py
├── requirements.txt
│
├── config/
│   ├── __init__.py
│   ├── asgi.py
│   ├── wsgi.py
│   ├── urls.py
│   ├── routing.py
│   └── settings.py
│
├── accounts/
├── schools/
├── subscriptions/
├── core/
├── media_library/
├── staff/
├── academics/
├── assessments/
├── examinations/
├── learning/
├── admissions/
├── finance/
├── store/
├── communications/
├── support/
│
├── media/
│   ├── public/
│   └── private/
│
├── templates/
│   ├── platform/
│   │   ├── layout.html
│   │   ├── dashboard/
│   │   ├── schools/
│   │   ├── subscriptions/
│   │   └── support/
│   │
│   └── schools/
│       ├── default/
│       │   ├── layout.html
│       │   ├── dashboards/
│       │   ├── components/
│       │   ├── accounts/
│       │   ├── dashboard/
│       │   ├── admissions/
│       │   ├── academics/
│       │   ├── finance/
│       │   ├── support/
│       │   └── errors/
│       │
│       ├── green-school/
│       └── blue-school/
│
├── static/
│   ├── platform/
│   │   ├── css/
│   │   ├── js/
│   │   ├── images/
│   │   └── icons/
│   │
│   └── schools/
│       ├── default/
│       │   ├── css/
│       │   ├── js/
│       │   ├── images/
│       │   └── icons/
│       │
│       ├── green-school/
│       └── blue-school/
│
├── docs/
│   ├── architecture/
│   ├── database/
│   ├── api/
│   ├── security/
│   └── deployment/
│
├── tests/
│
├── .env.example
├── .gitignore
└── README.md
```

The `media/` directory is the single storage root with two subdirectories:

- `media/public/` — publicly accessible uploaded files (e.g. school logos, product images, profile pictures served over the web).
- `media/private/` — sensitive documents requiring permission-checked access (e.g. admission documents, private student records, financial attachments).

Do not create a separate top-level `private_media/` directory. Keep the storage hierarchy clean by nesting both under `media/`.

The Django application responsible for media management must be named `media_library`, not `media`.

## 3.1 Application organization

Every Django application should use a consistent, understandable structure where appropriate.

For example:

```text
academics/
├── migrations/
├── models.py
├── forms.py
├── views.py
├── selectors.py
├── services.py
├── serializers.py
├── permissions.py
├── urls.py
├── api_urls.py
├── admin.py
├── signals.py
├── tests/
└── apps.py
```

Do not create unnecessary files in every application if they serve no purpose.

Use:

- `models.py` for data models.
- `forms.py` for Django forms.
- `views.py` for server-rendered views.
- `serializers.py` for DRF serializers.
- `services.py` for business operations and state-changing workflows.
- `selectors.py` for complex read queries.
- `permissions.py` for application and API permissions.
- `api_urls.py` for API routing where appropriate.
- `tests/` for application tests.

Keep business rules out of templates, JavaScript, serializers, and view functions wherever possible.

## 3.2 Requirements file

Maintain one root `requirements.txt`.

Organize dependencies with comments by category.

Pin compatible versions and avoid unnecessary dependencies.

## 3.3 Single settings file

Use:

```python
BASE_DIR = Path(__file__).resolve().parent.parent
```

Use the environment variable:

```env
RUN_MODE=development
```

or:

```env
RUN_MODE=production
```

The settings file must validate the selected mode and reject unsupported values.

Development mode:

- May use SQLite when PostgreSQL is not available locally.
- May use an in-memory Channels layer.
- May use local media storage.
- May enable Django debug tools where appropriate.
- Must remain safe enough for development.

Production mode:

- Must require PostgreSQL.
- Must require the configured Redis service for production Channels.
- Must require a secure secret key.
- Must disable debug mode.
- Must require explicit allowed hosts.
- Must configure HTTPS and secure cookies.
- Must use secure file storage and private media handling.
- Must not silently fall back to insecure defaults.

Use `.env.example` to document all required environment variables without exposing real secrets.

Use:

```python
TIME_ZONE = "Africa/Lagos"
USE_TZ = True
```

---

# PART 4: MULTI-TENANT SAAS ARCHITECTURE

## 4.1 Tenancy strategy

Implement a shared-database, shared-schema multi-tenant architecture using PostgreSQL.

All schools share the same database tables.

Every tenant-owned record must be associated with its school through an explicit tenant relationship.

The `School` model is the central tenant registry.

Do not create a separate database or schema for every school.

## 4.2 Tenant identification

Support:

1. SaaS subdomains:

   `green.yoursaas.com`

2. Custom school domains:

   `sms.greenschool.com`

3. A platform domain for platform-level operations.

A school's domain must be verified and active before it can resolve to that tenant.

Create a `SchoolDomain` model with suitable fields, including:

- School.
- Domain.
- Domain type.
- Is primary.
- Is verified.
- Is active.
- Created timestamp.

Enforce appropriate uniqueness and constraints, including one active primary domain per school.

## 4.3 Tenant resolution middleware

Implement tenant resolution middleware.

The middleware must:

1. Read the request hostname.
2. Normalize and validate the hostname.
3. Find the corresponding verified and active `SchoolDomain`.
4. Resolve the associated school.
5. Attach the tenant to `request.school`.
6. Reject unknown or inactive school domains appropriately.
7. Prevent users from accessing a tenant through an unverified domain.

Platform routes must be distinguishable from school routes.

The same URL paths should work for different schools because the hostname determines the tenant.

For example:

```text
green.yoursaas.com/dashboard/
blue.yoursaas.com/dashboard/
```

Both can use the same path while resolving to different schools.

## 4.4 Tenant isolation

Tenant isolation is a critical security requirement.

Every tenant-owned model must include a school relationship, directly or through a clearly documented ownership relationship.

Enforce tenant isolation through:

- Querysets.
- Managers where appropriate.
- Services.
- Selectors.
- Forms.
- Serializers.
- API permissions.
- File access.
- WebSocket consumers.
- Background jobs.
- Scheduled commands.
- Reporting queries.

Never trust a `school_id` supplied by the frontend.

Derive tenant context from the verified request and authorized membership.

Every create, update, delete, list, retrieve, export, and download operation must respect tenant boundaries.

Add tenant-scoped unique constraints and indexes where appropriate.

Write automated tests proving that a user from School A cannot access, modify, enumerate, or download School B's records, even by changing object IDs or API request parameters.

PostgreSQL Row-Level Security may be considered as an additional defense-in-depth mechanism, but it must not replace application-level tenant enforcement.

If implemented, document transaction and connection-pooling implications carefully.

## 4.5 School websites and admissions routing

A school may host its public website separately from the SaaS platform.

For example:

```text
www.greenschool.com
```

The school's Apply Now button can redirect applicants to:

```text
apply.greenschool.com/admissions/apply/
```

or:

```text
green.yoursaas.com/admissions/apply/
```

The verified hostname identifies the school.

Do not rely on a frontend-supplied school ID to determine the tenant.

Document how schools configure their admissions links, verify their domains, and test the redirect.

A normal HTTP redirect does not require CORS.

Only configure CORS when browser-based cross-origin API requests genuinely require it, and restrict it to approved origins.

---

# PART 5: USER ACCOUNTS, ROLES AND PERMISSIONS

## 5.1 Custom user model

Create a custom user model inside `accounts`.

Set:

```python
AUTH_USER_MODEL = "accounts.User"
```

Use a suitable login identifier and implement secure account management.

Support:

- Login.
- Logout.
- Registration where permitted.
- Password reset.
- Password change.
- Profile management.
- Account activation and deactivation.
- Session management.
- User status.
- Email and phone verification where required.

### 5.1.1 Username as universal user identifier (Staff ID / Student ID)

Every user in the system must have a unique `username`. The username serves as the human-readable identifier across the entire platform.

For school staff and students, the username is also their **institutional ID**. Use a structured prefix scheme to make IDs self-describing and distinguishable at a glance:

```text
Format:   <SCHOOL_CODE>-<ROLE_PREFIX>-<SEQUENCE>

Examples:
  GS-STF-0042   →  Staff member #42 at Green School
  GS-STD-1017   →  Student #1017 at Green School
  BS-STF-0003   →  Staff member #3 at Blue School
```

**Prefix definitions:**

| Segment | Description | Example |
|---|---|---|
| `SCHOOL_CODE` | 2–4 character uppercase code unique to the school | `GS`, `BSC`, `KING` |
| `STF` | Teaching or non-teaching staff | `GS-STF-0001` |
| `STD` | Student | `GS-STD-0001` |
| `DIR` | School Director | `GS-DIR-0001` |

**Rules:**

- The school code must be assigned at school creation and must be unique across the platform.
- The sequence number must be zero-padded to at least 4 digits and must be school-scoped.
- Username generation must be performed by a service function in `accounts/services.py`, not in a view or model `save()`.
- Usernames must be validated against the platform's format rules before being saved.
- A user who belongs to two schools will have one `username` on the `User` model but separate `SchoolMembership` records, one per school. The username is derived from the school where the user was first registered. The user's ID in a second school is their membership record's local reference, not a second username.
- Username changes must be restricted to authorized platform-level operations and must be audited.
- The Django `username` field must enforce uniqueness at the database level.

### 5.1.2 Multi-school membership

A single user (staff member or student) may belong to more than one school at the same time.

A `User` record is shared across schools. The `SchoolMembership` model (see Section 5.3) records the user's role, status, and permissions at each school independently.

This means:

- A teacher at Green School and also at Blue School has one `User` account but two `SchoolMembership` records.
- A student who transfers to a second school may have memberships at both schools, with the original school showing historical enrollment.
- Role and permissions at School A have no bearing on role and permissions at School B unless explicitly granted.
- Tenant isolation is enforced per membership: a user logged in to Green School's subdomain sees only Green School's data, even if they also have a membership at Blue School.

The login flow must identify which school tenant the user is accessing (from the verified hostname) and load the appropriate `SchoolMembership` for that tenant. Do not automatically grant access to all schools a user belongs to through a single session.

A user switching schools must authenticate through that school's verified domain.

## 5.2 Separate platform and school roles

The platform-level role must be separate from school-level membership roles.

### Platform Developer

The Platform Developer is responsible for managing the SaaS platform.

The Platform Developer must have authorized access to:

- All registered schools.
- School records.
- Students.
- Parents and guardians.
- Staff.
- Platform subscriptions.
- Platform operations.
- Platform-wide support.
- School notifications.
- Platform analytics.

The Platform Developer can send notifications to schools or school directors.

Cross-school access must be logged and auditable.

Do not automatically give every support or intern account unrestricted access.

### School Director

The School Director is the highest school-level authority.

The Director can manage their own school, subject to platform subscription and platform restrictions.

The Director must never become a Django superuser simply because of their school role.

### Other school roles

Support:

- Principal.
- Vice Principal.
- Teaching Staff.
- Non-Teaching Staff.
- Parent/Guardian.
- Student.
- Admissions-related applicant accounts where appropriate.

## 5.3 Role assignment architecture

Use a proper role and permission assignment system.

Do not use boolean role fields such as:

```python
is_parent = True
is_teacher = True
is_director = True
```

A user may have multiple memberships in different schools.

A user may be a parent in one school and have a different role in another school.

Both roles must be seeded automatically when a school is created (see Section 8.7.1 for class seeding; the same seed-on-create pattern applies here). The platform must ensure that a newly created school always has the full set of available roles configured before the School Director logs in for the first time.

Use a structure similar to:

```text
User
  └── SchoolMembership
        ├── School
        ├── User
        ├── Role
        ├── Status
        └── Assigned Permissions
```

Use Django permissions and groups where appropriate, supplemented by tenant-scoped membership permissions.

Permissions must be enforced on the server, not merely by hiding navigation links.

### Role and class seeding on school creation

When the Platform Developer creates a new school, the following must be seeded atomically within the same database transaction:

1. **Standard roles** — All supported school roles (Director, Principal, Vice Principal, Teaching Staff, Non-Teaching Staff, Parent/Guardian, Student) must exist in the school's role catalogue before any users are added.
2. **Standard classes** — The full Nigerian class list (Primary 1–6, JSS 1–3, SSS 1–3) must be created with `is_active = True`. The school can deactivate individual classes it does not offer (see Section 8.7.1).

This ensures no school is ever in a partially configured state after creation.

## 5.4 Role access rules

- Platform Developer: authorized cross-school platform access.
- Director: full school-level authority within their own school.
- Principal: academic and operational management within their school.
- Vice Principal: delegated school management and staff/student operations.
- Teaching Staff: assigned classes, subjects, students, attendance, assessments, and learning materials.
- Non-Teaching Staff: only assigned administrative functions.
- Parent: only linked children and authorized school information.
- Student: only their own records and permitted learning activities.

A parent must not access another parent's child records.

A student must not access another student's results or profile.

A teacher must not access classes or subjects outside their authorized assignments unless granted additional permissions.

---

# PART 6: SCHOOL CONFIGURATION AND APPVARIABLE

## 6.1 School registry

Use a proper `School` model as the tenant registry.

The registry must contain information needed for tenant identification, domain resolution, subscription status, and operational state.

Do not use a rigid `SchoolProfile` as the only source of school configuration.

## 6.2 AppVariable model

Use a centralized key-value configuration system named `AppVariable`.

The model should contain:

- `school`: optional FK to School, null for platform-level settings.
- `var_name`: unique within the appropriate scope.
- `var_value`.
- `description`.
- `isreadonly`.
- `lastupdated`.

Use appropriate verbose names:

- System Setting.
- System Settings.

Implement a helper similar to:

```python
get_setting(name, default="")
```

It must distinguish platform-level settings from school-level settings.

Implement caching and cache invalidation when settings change.

Enforce read-only settings.

Do not store passwords, secret keys, API secrets, or payment secrets as ordinary plaintext AppVariable values.

Use environment variables or an appropriate secrets-management mechanism for sensitive credentials.

## 6.3 Example school settings

Support configuration keys such as:

```text
SCHOOL_NAME
SCHOOL_MOTTO
SCHOOL_LOGO
PRIMARY_COLOR
SECONDARY_COLOR
OFFICIAL_EMAIL
SCHOOL_PHONE
SCHOOL_ADDRESS
CONTACT_PERSON1
ADMISSION_EMAIL
CURRENT_SESSION
CURRENT_TERM
```

Platform settings may include:

```text
PLATFORM_NAME
PLATFORM_EMAIL
PLATFORM_SUPPORT_EMAIL
PLATFORM_LOGO
```

Validate setting types and allowed values.

Do not allow a school administrator to inject arbitrary executable JavaScript or unsafe CSS through settings.

---

# PART 7: SCHOOL TEMPLATE AND BRANDING ARCHITECTURE

The system must support a shared default school design with optional custom school templates.

## 7.1 Platform templates

Platform-level pages must use:

```text
templates/platform/
```

Examples:

- Platform dashboard.
- School management.
- Subscription management.
- Platform support.
- Platform settings.

Platform static assets must use:

```text
static/platform/
```

## 7.2 Default school template

All schools should initially use:

```text
templates/schools/default/
```

and:

```text
static/schools/default/
```

The default template must support dynamic branding.

## 7.3 Optional custom templates

Some schools may require a custom visual identity.

Support approved template folders such as:

```text
templates/schools/green-school/
templates/schools/blue-school/
```

These should be exceptions, not the default approach.

Do not generate a complete custom template folder for every school.

## 7.4 Template selection

Create a safe template-selection service.

It should:

1. Determine the current school.
2. Read its approved template key.
3. Validate the key against an allowlist.
4. Check whether the approved custom template exists.
5. Use the custom template when valid and enabled.
6. Otherwise use the default school template.
7. Always use platform templates for platform-level pages.

Never use arbitrary database values directly as filesystem paths.

## 7.5 Dynamic theming

Use CSS custom properties for school branding.

Example:

```css
:root {
    --primary-color: #2563eb;
    --secondary-color: #f59e0b;

    --bg-body: #f8fafc;
    --bg-surface: #ffffff;

    --text-primary: #0f172a;
    --text-secondary: #64748b;

    --border-color: #e2e8f0;

    --success-color: #16a34a;
    --warning-color: #d97706;
    --danger-color: #dc2626;

    --radius-sm: 8px;
    --radius-md: 12px;
    --radius-lg: 16px;

    --shadow-card: 0 4px 20px -2px rgba(0, 0, 0, 0.05);
}
```

The actual values must be injected from validated school theme settings.

All school components must use these variables instead of hardcoding a school's branding throughout the templates.

Uploaded logos and images must use the media storage system, not source static folders.

---

# PART 8: DJANGO APPLICATIONS AND MODULE RESPONSIBILITIES

Implement the following applications.

## 8.1 accounts

Responsible for:

- Custom user model.
- Authentication.
- Password reset and change.
- User profiles.
- School memberships.
- Roles and permissions.
- Parent/guardian relationships.
- Student account links.
- Account activation and deactivation.
- Login and security history where appropriate.

## 8.2 schools

Responsible for:

- School tenant registry.
- School domains.
- Domain verification state.
- Tenant configuration.
- School operational status.
- School onboarding.
- School-specific settings.
- Tenant resolution support.

## 8.3 subscriptions

Responsible for:

- SaaS subscription plans.
- School subscriptions.
- Trial periods.
- Subscription status.
- Billing periods.
- Renewals.
- Expiry.
- Payment records.
- Feature entitlements.
- Usage limits.
- Grace periods.
- Subscription enforcement.

A school subscription must control access to applicable platform features.

Do not allow expired or suspended subscriptions to bypass restrictions through direct URLs or API calls.

## 8.4 core

Responsible for:

- Shared utilities.
- Common abstract models.
- Constants.
- Shared exceptions.
- Common helpers.
- Context processors.
- Common permission utilities where genuinely reusable.

Do not turn `core` into a dumping ground.

## 8.5 media_library

Responsible for:

- Media albums.
- Media assets.
- Media categories.
- File metadata.
- Upload and organization.
- Storage abstraction.
- Authorized media retrieval.

Retain:

- `MediaAlbum`.
- `MediaAsset`.
- `MediaCategory` where needed.

Do not implement a CMS.

The media library must support future Cloudinary or object-storage integration.

School-specific media must be tenant-scoped.

Sensitive documents must not be exposed through public URLs.

Profile pictures may support direct uploads where appropriate.

## 8.6 staff

Responsible for:

- Staff records.
- Employment information.
- Staff positions.
- Staff status.
- Staff attendance.
- Staff-related administrative records.
- Authorized staff management.

## 8.7 academics

Responsible for:

- Academic sessions.
- Terms.
- School sections.
- Classes.
- Class arms.
- Subjects.
- Students.
- Student enrollment.
- Student class assignments.
- Teaching assignments.
- Student attendance.
- Student promotion.
- Academic history.

The academic structure must support:

```text
TeachingAssignment
    ↓
AcademicSession
    ↓
Section
    ↓
Class
    ↓
Subject
```

Class and subject assignments must be session-aware rather than permanently fixed.

### 8.7.1 Class seeding on school creation

When the Platform Developer creates a new school and assigns a School Director, the system must automatically seed the school's class catalogue with the full set of standard Nigerian school classes.

The seeded classes must cover:

```text
Section: Primary
  Primary 1
  Primary 2
  Primary 3
  Primary 4
  Primary 5
  Primary 6

Section: Junior Secondary School (JSS)
  JSS 1
  JSS 2
  JSS 3

Section: Senior Secondary School (SSS)
  SSS 1
  SSS 2
  SSS 3
```

Each seeded class must be created with `is_active = True` by default.

A school that does not offer a particular class (e.g. a primary school that ends at Primary 5, or a school that is purely secondary) must be able to deactivate individual classes through its school administration interface. Deactivating a class hides it from academic operations, enrollment, attendance, and all related workflows for that school only. It must not affect any other school's configuration.

Reactivating a class must restore it to full operation for that school.

Seeding must be idempotent: running the seed operation more than once for the same school must not create duplicate class records.

Implement the seeding logic as a reusable service function in `academics/services.py` so it can be called from:

1. The school creation workflow in `schools/services.py`.
2. A Django management command for manual recovery if needed.
3. The school onboarding process.

Do not hardcode class data in views or migrations. Use a clearly defined constant or fixture in `academics/constants.py` or `core/constants.py`.

Roles are seeded similarly (see Section 5.3). Both class and role seeding must be triggered atomically as part of the school creation transaction so a school is never left in a partially initialized state.

## 8.8 assessments

Responsible for:

- Continuous assessments.
- Test configuration.
- Question banks.
- Question categories.
- Question images.
- Online assessments.
- Objective questions.
- Essay questions.
- Student submissions.
- Auto-marking.
- Manual marking queues.
- Assessment results.

## 8.9 examinations

Responsible for:

- Formal examinations.
- Examination schedules.
- Examination papers.
- Examination scores.
- Result calculations.
- Grade configuration.
- Result approval.
- Result publication.
- Result scheduling.
- Report cards.
- Student academic performance history.

## 8.10 learning

Responsible for:

- Lesson notes.
- Learning materials.
- Study resources.
- Assignments.
- Student submissions.
- Teacher feedback.
- Learning activities.

## 8.11 admissions

Responsible for:

- Public admission applications.
- Applicant information.
- Application requirements.
- Document submissions.
- Application review.
- Application status.
- Admission decisions.
- Admission letters.
- Application fee tracking.
- Applicant-to-student conversion.

Admission applications must automatically belong to the tenant resolved from the verified school domain.

## 8.12 finance

Responsible for:

- Fee categories.
- Fee structures.
- Student invoices.
- Payment records.
- Payment initiation.
- Payment verification.
- Receipts.
- Outstanding balances.
- Payment history.
- Financial reports.
- Payment reconciliation.

Integrate Paystack with school-specific configuration.

Payment verification must happen on the server.

Never trust a successful payment response from the browser alone.

## 8.13 store

Responsible for:

- Products.
- Product categories.
- Product images.
- Inventory.
- Stock adjustments.
- Orders.
- Purchases.
- Sales records.
- Stock reports.

When a purchase is completed, inventory quantity must be updated safely.

Stock adjustments must also update the actual inventory quantity and maintain an auditable history.

Prevent overselling through appropriate database transactions and validation.

## 8.14 communications

Responsible for school announcements and notifications.

Communications must support:

- Principal-to-staff announcements.
- Director-to-staff announcements.
- General school notifications.
- Targeted staff notifications.
- Email notifications.
- SMS notifications.
- In-app notifications.

The sender selects the target audience and message type.

The backend determines recipients using school membership and permission rules.

Do not implement direct parent or student communication as part of this communications module.

Do not introduce regional or country-based notification targeting.

## 8.15 support

Responsible for:

- Support tickets.
- Anonymous support sessions.
- Authenticated support.
- Live chat.
- Chat messages.
- Chat history.
- Support assignments.
- Escalation.
- AI support assistance.
- Payment complaints.
- Support status and history.

A visitor must be able to start a support conversation without creating an account.

If the visitor logs in later, link the anonymous conversation to their authenticated user safely.

The system must support real-time messaging through Django Channels and WebSockets.

The AI assistant may answer:

- Public questions about admission availability.
- Public questions about school information and policies.
- General platform questions.
- Authenticated questions about store products.
- Authenticated questions about payment records.

Authenticated AI queries must use tenant-scoped services and permission checks.

The AI must never bypass application permissions or access another school's data.

---

# PART 9: ATTENDANCE MANAGEMENT

## 9.1 Student attendance

Teachers must be able to mark attendance for students in their assigned classes.

The attendance system must support:

- Academic session.
- Term.
- Date.
- Class.
- Class arm.
- Student.
- Attendance status.
- Marked by.
- Timestamp.
- Remarks where appropriate.

Students must only be able to view their attendance records.

Students must not be able to mark or edit their own attendance.

Parents may view the attendance of their linked children if authorized.

## 9.2 Staff attendance

The Principal or Vice Principal must be able to mark staff attendance.

Staff attendance must include:

- Date.
- Staff member.
- Attendance status.
- Marked by.
- Timestamp.
- Remarks.

Enforce permission checks for marking and modifying attendance.

Prevent unauthorized changes to finalized attendance records.

---

# PART 10: ASSESSMENTS AND EXAMINATIONS

## 10.1 Assessment weighting

Use the default result weighting:

```text
TET = 30%
EXAM = 70%
```

The weighting should be configurable by an authorized school administrator.

Do not assume every school must use the same weighting forever.

## 10.2 Score validation

Validate all scores against the maximum possible score.

Do not accept scores outside valid ranges.

Do not automatically convert a missing score into zero.

A missing component must be represented as:

```text
Pending
```

not zero.

The system must distinguish:

- Not submitted.
- Pending marking.
- Marked.
- Approved.
- Published.

## 10.3 Default grading

Use the following default grading structure:

| Score | Grade |
|---|---|
| 70–100 | A |
| 60–69 | B |
| 50–59 | C |
| 40–49 | D |
| 0–39 | E |

The grading configuration should be school-configurable where authorized.

## 10.4 Result approval and publication

The Principal must review results before current-term results can be published or scheduled for publication.

Examination approval and result publication must be separate processes.

A result must not become publicly visible merely because scores have been entered.

Implement a clear result workflow:

1. Teachers enter or submit scores.
2. System validates calculations.
3. Results are prepared.
4. Principal reviews.
5. Principal approves or returns for correction.
6. Authorized user publishes or schedules publication.
7. Students and parents view results according to permissions.

Record approvals, changes, and publication history.

## 10.5 Online assessments

Support online assessments with:

- Objective questions.
- Multiple-choice questions.
- True/false questions.
- Other suitable objective formats.
- Essay questions.
- Manual marking.
- Auto-marking.
- Submission tracking.
- Attempt limits.
- Time limits.
- Assessment availability windows.

Objective questions should be automatically marked.

Essay questions should enter a manual marking queue.

Do not require teachers to re-enter scores for questions already marked automatically by the platform.

## 10.6 Question bank and images

Implement a reusable question bank.

Questions must support one or multiple images.

This is important for subjects such as:

- Physics.
- Chemistry.
- Basic Technology.
- Mathematics.
- Biology.

Use an appropriate model such as `QuestionImage` to support multiple images per question.

Provide an assessment builder and preview interface.

---

# PART 11: FINANCE AND PAYMENTS

Implement a complete school finance module.

Support:

- Fee categories.
- Class-based fees.
- Session-based fees.
- Term-based fees.
- Student invoices.
- Payment initiation.
- Paystack payment verification.
- Payment receipts.
- Outstanding balances.
- Partial payments where allowed.
- Payment history.
- Financial reports.

Each school's payment configuration must be tenant-specific.

Payment references must be unique and verifiable.

Verify transactions with the payment provider from the backend.

Use database transactions and idempotent processing to prevent duplicate payment records.

Never expose private payment credentials to frontend JavaScript or public API responses.

Provide clear payment statuses, such as:

- Pending.
- Successful.
- Failed.
- Cancelled.
- Refunded where supported.

---

# PART 12: STORE AND INVENTORY

The store must support school products and purchases.

Include:

- Product management.
- Product categories.
- Product images.
- Stock quantities.
- Stock adjustments.
- Orders.
- Purchase records.
- Inventory reports.

Important business rule:

When a completed purchase reduces available stock, the corresponding inventory quantity must be updated.

An inventory adjustment must also update the current stock quantity.

Maintain a stock movement history with:

- Product.
- School.
- Previous quantity.
- Quantity changed.
- New quantity.
- Adjustment reason.
- User.
- Timestamp.

Use database transactions to avoid inconsistent stock updates.

---

# PART 13: MEDIA AND FILE MANAGEMENT

Build a reusable media library.

Support:

- Media albums.
- Media categories.
- Media assets.
- Uploads.
- Metadata.
- File size and type validation.
- Image previews.
- Authorized downloads.
- School-specific media organization.

Separate public and private storage.

Use:

```text
media/public/
media/private/
```

Both reside under the single `media/` root directory at the project level.

`media/public/` serves files that may be delivered directly by the web server (school logos, general school images, product images).

`media/private/` stores files that must only be served after a permission check (admission documents, private student records, financial attachments, confidential reports). Never configure the web server to serve `media/private/` without an application-level authorization gate.

Do not expose sensitive files using guessable public URLs.

Create a storage service or abstraction so local storage can later be replaced with Cloudinary, S3, R2, or another compatible storage provider.

Validate file extensions, MIME types, file sizes, and access permissions.

---

# PART 14: COMMUNICATIONS AND NOTIFICATIONS

Build a school notification system.

The Director or Principal should be able to create announcements for authorized staff audiences.

The sender should select:

- Target audience.
- Message type.
- Message content.
- Delivery schedule where supported.

Supported delivery types:

- In-app.
- Email.
- SMS.

The backend must resolve recipients using the current tenant's membership and permissions.

Do not allow a user to submit arbitrary recipient user IDs and bypass audience rules.

Do not implement direct parent/student communication in this module.

Create delivery records and statuses where appropriate.

Support notification preferences and delivery failure handling.

Platform-level notifications must be separate from school-level notifications.

---

# PART 15: LIVE SUPPORT AND REAL-TIME MESSAGING

Use Django Channels for real-time support.

Implement:

- Anonymous chat sessions.
- Authenticated chat sessions.
- Chat history.
- Message delivery.
- Support assignment.
- Agent availability/status where needed.
- Conversation closure.
- Conversation reopening.
- Escalation.
- Tenant-aware authorization.

Use Redis as the production Channels layer.

An in-memory channel layer may be used for local development only.

WebSocket connections must validate:

- Authentication where required.
- Tenant context.
- Conversation ownership.
- Agent permissions.
- Conversation membership.

Do not assume that a user who knows a conversation ID is allowed to access it.

Use database-backed messages as the durable source of truth.

Redis must not become the permanent store for chat history.

---

# PART 16: COMPLETE REST API ARCHITECTURE

This is a mandatory core requirement.

The REST API must be designed and implemented from the beginning, not added as an afterthought.

The system must have complete API coverage for all functional modules so that future Android and iOS applications can consume the same backend.

A mobile application must not require a backend redesign.

## 16.1 API base path

Use:

```text
/api/v1/
```

Organize endpoints by application and resource.

Examples:

```text
/api/v1/auth/
/api/v1/users/
/api/v1/schools/
/api/v1/memberships/
/api/v1/students/
/api/v1/parents/
/api/v1/staff/
/api/v1/academics/
/api/v1/attendance/
/api/v1/assessments/
/api/v1/examinations/
/api/v1/results/
/api/v1/learning/
/api/v1/admissions/
/api/v1/finance/
/api/v1/payments/
/api/v1/store/
/api/v1/inventory/
/api/v1/communications/
/api/v1/notifications/
/api/v1/support/
/api/v1/chat/
/api/v1/media/
/api/v1/subscriptions/
```

The final endpoint design should follow actual resource boundaries and avoid redundant endpoints.

## 16.2 Authentication API

Implement endpoints for:

- Registration where allowed.
- Login.
- Logout.
- Access token refresh.
- Token revocation.
- Password reset request.
- Password reset confirmation.
- Password change.
- Email verification.
- Phone verification where required.
- Current user profile.
- Profile update.
- Active device/session management where appropriate.

Use an access-token and refresh-token approach suitable for mobile clients.

Define token expiration, rotation, revocation, and secure storage expectations.

Do not rely exclusively on browser session cookies for mobile authentication.

Browser authentication must remain secure and compatible with Django's session and CSRF protections.

## 16.3 Complete module API coverage

Implement all necessary API operations for every functional module.

The API must support relevant:

- List.
- Retrieve.
- Create.
- Update.
- Delete where permitted.
- Archive.
- Search.
- Filtering.
- Sorting.
- Pagination.
- Status transitions.
- Approvals.
- Rejections.
- Publishing.
- Scheduling.
- File uploads.
- Protected downloads.
- Reports.
- History.
- Export operations where appropriate.

Do not expose unrestricted CRUD merely because a model exists.

Each endpoint must represent a valid business operation.

## 16.4 API module requirements

Provide API coverage for:

### Accounts and authentication

- Login and token management.
- User profiles.
- Memberships.
- Role information.
- Password management.
- Account status.

### Schools and subscriptions

- School information.
- Verified domain information where appropriate.
- Authorized school configuration.
- Subscription plans.
- Subscription status.
- Feature entitlements.
- Usage information.

### Academics

- Academic sessions.
- Terms.
- Sections.
- Classes.
- Arms.
- Subjects.
- Students.
- Enrollment.
- Class assignments.
- Teaching assignments.
- Promotions.

### Attendance

- Attendance lists.
- Attendance marking.
- Attendance updates where authorized.
- Student attendance history.
- Staff attendance.
- Attendance summaries.

### Assessments

- Question banks.
- Questions.
- Question images.
- Assessment creation.
- Assessment publication.
- Student assessment access.
- Submissions.
- Auto-marking results.
- Manual marking.
- Marking status.

### Examinations and results

- Examination schedules.
- Examination records.
- Score submission.
- Result calculation.
- Result review.
- Approval.
- Publication.
- Scheduled publication.
- Report cards.
- Student result history.

### Learning

- Lesson notes.
- Learning materials.
- Assignments.
- Submissions.
- Feedback.

### Admissions

- Public applications.
- Applicant details.
- Document submission.
- Application status.
- Application review.
- Admission decisions.
- Admission letters.
- Applicant conversion.

### Finance and payments

- Fee structures.
- Invoices.
- Payment initiation.
- Payment verification.
- Payment history.
- Receipts.
- Outstanding balances.
- Financial reports.

### Store and inventory

- Product lists.
- Product details.
- Inventory.
- Orders.
- Purchases.
- Stock adjustments.
- Stock history.
- Reports.

### Communications

- Announcements.
- Authorized notification creation.
- Notification history.
- Notification preferences.
- Delivery statuses.

### Support

- Support tickets.
- Anonymous chat creation.
- Authenticated chat.
- Message history.
- Message submission.
- Conversation status.
- Assignment.
- Escalation.

### Media

- Album management.
- Asset management.
- Uploads.
- Protected downloads.
- Authorized file metadata.

## 16.5 API permissions

Every API endpoint must enforce:

- Authentication.
- Tenant isolation.
- Role permissions.
- Object-level permissions.
- Subscription restrictions.
- Business workflow restrictions.

A user must never be able to bypass a permission by calling an API directly.

Never trust a school ID supplied in the request body or query parameters as the source of tenant identity.

## 16.6 Shared business logic

Django Template views and API views must use the same services and selectors.

For example:

```text
Django Template View ──┐
                       ├── Service Layer ─── Database
DRF API View ──────────┘
```

Do not implement one set of business rules for the web application and a separate set for the mobile API.

## 16.7 API documentation

Use drf-spectacular.

Provide:

- OpenAPI schema.
- Swagger UI.
- ReDoc where useful.
- Authentication documentation.
- Request examples.
- Response examples.
- Error examples.
- Role and permission descriptions.
- Tenant behavior.
- Pagination and filtering documentation.

## 16.8 API endpoint matrix

Before or during implementation, maintain a documented endpoint matrix.

For every endpoint document:

| Field | Description |
|---|---|
| Module | Owning application |
| Endpoint | Full API path |
| Method | HTTP method |
| Purpose | Business operation |
| Roles | Authorized roles |
| Permission | Required permission |
| Tenant scope | How school scope is resolved |
| Request | Expected input |
| Response | Expected output |
| Validation | Business validation |
| Errors | Expected error responses |
| Tests | Required automated tests |

Do not leave important modules with placeholder API endpoints.

## 16.9 API consistency

Implement consistent:

- Response formats.
- Validation errors.
- Authentication errors.
- Permission errors.
- Not-found errors.
- Pagination.
- Filtering.
- Sorting.
- Rate limiting.
- Throttling.
- Audit logging.

Use HTTP status codes correctly.

Do not expose internal exception messages, stack traces, database details, or sensitive fields.

## 16.10 API versioning

Use explicit API versioning.

Define a compatibility policy so future mobile application releases do not break when backend changes are introduced.

Document deprecation procedures.

---

# PART 17: USER INTERFACE AND EXPERIENCE DESIGN

The user interface is as important as the backend architecture.

Do not create a generic, outdated school dashboard.

Design a polished, modern SaaS experience suitable for a professional commercial product.

## 17.1 Design principles

The interface must be:

- Modern.
- Professional.
- Clean.
- Consistent.
- Responsive.
- Accessible.
- Easy to navigate.
- Suitable for Nigerian schools.
- Optimized for desktop, tablet, and mobile.

Avoid:

- Cluttered dashboards.
- Excessive gradients.
- Unnecessary animations.
- Inconsistent spacing.
- Random colors.
- Oversized components.
- Unstyled tables.
- Generic Django admin appearance.

## 17.2 Design system

Create reusable design tokens for:

- Primary and secondary colors.
- Backgrounds.
- Surface colors.
- Text colors.
- Borders.
- Typography.
- Spacing.
- Border radius.
- Shadows.
- Buttons.
- Form fields.
- Badges.
- Alerts.
- Tables.
- Cards.

Support light and dark themes where appropriate.

The platform interface must have its own identity.

School interfaces must use dynamic school branding.

## 17.3 Separate dashboard experiences

Design a distinct dashboard for:

1. Platform Developer.
2. School Director.
3. Principal.
4. Vice Principal.
5. Teaching Staff.
6. Non-Teaching Staff.
7. Parent/Guardian.
8. Student.
9. Admissions applicant where applicable.

Each dashboard must show only information and actions relevant to that user's role.

## 17.4 Dashboard content

Examples of useful dashboard elements include:

### Platform Developer

- Total schools.
- Active schools.
- Suspended schools.
- Subscription overview.
- Platform revenue where applicable.
- Platform support requests.
- Recent platform activity.
- School onboarding activity.

### School Director

- Total students.
- Total staff.
- Total parents/guardians.
- School attendance overview.
- Financial overview.
- Admission overview.
- School activity.
- Important notifications.

### Principal

- Student statistics.
- Staff statistics.
- Academic activity.
- Attendance summaries.
- Examination and result status.
- Pending approvals.
- Recent school activities.

### Vice Principal

- Student attendance.
- Staff attendance.
- Class and academic operations.
- Pending administrative actions.
- Relevant school reports.

### Teaching Staff

- Assigned classes.
- Assigned subjects.
- Attendance marking.
- Assessment activities.
- Examination score entry.
- Lesson notes.
- Student submissions.

### Non-Teaching Staff

- Assigned operational functions.
- Relevant administrative tasks.
- Authorized records and reports.

### Parent/Guardian

- Linked children.
- Attendance.
- Results.
- Fees and payment history.
- School announcements.
- Authorized learning information.

### Student

- Personal academic information.
- Attendance status.
- Results.
- Assignments.
- Learning materials.
- Online assessments.
- School announcements.

## 17.5 Reusable UI components

Create reusable template components for:

- Sidebar.
- Top navigation.
- Breadcrumbs.
- Dashboard cards.
- Charts.
- Tables.
- Pagination.
- Search and filter bars.
- Forms.
- Modals.
- Confirmation dialogs.
- Alerts.
- Toast messages.
- Empty states.
- Loading states.
- Error states.
- Profile menus.
- Notification menus.

Use Django template inheritance and includes.

## 17.6 Responsive behavior

Desktop:

- Full sidebar.
- Top navigation.
- Multi-column dashboards.
- Spacious data tables.

Tablet:

- Collapsible sidebar.
- Adaptive grids.
- Responsive tables.

Mobile:

- Mobile navigation.
- Touch-friendly controls.
- Responsive cards.
- Readable forms.
- Mobile-friendly tables or card-based data views.
- No horizontal overflow.

## 17.7 Accessibility

Follow practical accessibility standards.

Include:

- Semantic HTML.
- Keyboard navigation.
- Visible focus states.
- Accessible form labels.
- Appropriate contrast.
- Clear validation messages.
- Screen-reader-friendly controls.
- Status indicators that do not rely only on color.

## 17.8 Charts and tables

Use charts only when they help users understand information.

Use tables for structured operational records.

Implement:

- Search.
- Filtering.
- Sorting.
- Pagination.
- Empty states.
- Loading states.
- Error states.
- Export actions where authorized.

Avoid loading thousands of records into the browser.

Use server-side pagination for large datasets.

---

# PART 18: URL AND NAVIGATION ARCHITECTURE

Use clean, readable URLs.

Examples:

```text
/dashboard/

/admissions/
/admissions/apply/

/academics/students/
/academics/classes/
/academics/subjects/
/academics/attendance/

/staff/
/staff/attendance/

/assessments/
/examinations/
/results/

/finance/
/finance/payments/
/finance/receipts/

/store/
/store/products/
/store/inventory/

/communications/
/notifications/

/support/
/support/chat/

/api/v1/
```

The same school paths should work across tenants because tenant identity comes from the verified hostname.

Do not unnecessarily expose internal database identifiers in URLs where a suitable public identifier or slug is more appropriate.

Use namespaced URL configurations and clear route naming.

---

# PART 19: DATABASE ARCHITECTURE AND DATA INTEGRITY

Design the database carefully before implementing dependent features.

Requirements:

- Use appropriate relational models.
- Use foreign keys correctly.
- Add tenant-aware unique constraints.
- Add indexes for frequently filtered fields.
- Use database transactions for important workflows.
- Use appropriate deletion behavior.
- Avoid unnecessary duplicate data.
- Avoid circular model dependencies.
- Use decimal fields for financial amounts.
- Use appropriate date and datetime fields.
- Maintain audit history for sensitive operations.

Use Django migrations properly.

Do not disable constraints to make migrations succeed.

Do not delete production data or reset migrations casually.

For important business operations, use `transaction.atomic()` and database-level constraints where necessary.

Consider concurrent requests when handling:

- Payments.
- Inventory.
- Attendance finalization.
- Result publication.
- Subscription changes.
- Admission conversion.

Document major model relationships and important constraints.

---

# PART 20: SECURITY ARCHITECTURE

Security is a core product requirement.

Implement:

## Authentication and account security

- Secure password hashing.
- Password reset protections.
- Account activation.
- Login throttling.
- Session security.
- Token expiration and revocation.
- Secure cookie settings.
- Appropriate CSRF protection.

## Authorization

- Role-based permissions.
- Object-level permissions.
- Tenant isolation.
- Subscription entitlements.
- Explicit access to sensitive records.

## Web security

- CSRF protection.
- XSS prevention.
- Secure template escaping.
- SQL injection prevention through ORM and safe queries.
- Secure headers.
- HTTPS enforcement in production.
- Host validation.
- Secure CORS configuration.

## File security

- File type validation.
- File size limits.
- Safe filenames.
- Private document storage.
- Permission-checked downloads.
- Protection against path traversal.
- No direct public access to confidential records.

## Payment security

- Server-side payment verification.
- Unique transaction references.
- Idempotent processing.
- Secure webhook verification.
- No frontend exposure of secret credentials.

## Tenant security

- Verified host-based tenant resolution.
- Tenant-scoped querysets.
- Tenant-scoped serializers.
- Tenant-scoped file access.
- Tenant-aware WebSocket authorization.
- Cross-tenant access tests.

## Audit logging

Record important actions such as:

- User and role changes.
- School settings changes.
- Sensitive student record access where appropriate.
- Score modifications.
- Result approvals.
- Result publication.
- Financial operations.
- Payment verification.
- Inventory adjustments.
- Platform cross-school access.
- Subscription changes.

Audit logs must be protected against unauthorized modification.

---

# PART 21: TESTING STRATEGY

Testing must be part of development, not an afterthought.

Use Django's testing tools and DRF's API testing tools.

Create tests for:

## Models

- Valid model creation.
- Required fields.
- Constraints.
- Tenant relationships.
- Model methods.
- Business validation.

## Views and services

- Correct workflow behavior.
- Form validation.
- Service-layer operations.
- Authorization.
- State transitions.

## API

- Authentication.
- Token refresh and revocation.
- Permissions.
- Tenant isolation.
- Validation.
- Pagination.
- Filtering.
- File access.
- Error responses.
- Critical workflows.

## Multi-tenancy

Explicitly test that:

- School A cannot list School B's students.
- School A cannot retrieve School B's student by ID.
- School A cannot update School B's records.
- School A cannot delete School B's records.
- School A cannot download School B's private files.
- A teacher cannot access unassigned classes.
- A parent cannot access unlinked children.
- A student cannot access another student's records.
- An unauthorized platform user cannot perform unrestricted cross-school operations.

## Business workflows

Test:

- Admissions application and conversion.
- Student enrollment.
- Attendance marking.
- Assessment submission.
- Objective auto-marking.
- Manual essay marking.
- Result calculation.
- Principal approval.
- Result publication.
- Payment verification.
- Duplicate payment prevention.
- Inventory deduction.
- Stock adjustments.
- Subscription expiration.
- Support conversation ownership.
- Anonymous chat linking.

## WebSockets

Test:

- Authenticated connection.
- Anonymous connection where allowed.
- Tenant isolation.
- Conversation access.
- Unauthorized connection rejection.
- Message delivery.
- Conversation closure.

Use test data and factories where appropriate.

Do not claim a feature is complete merely because the page loads.

---

# PART 22: PERFORMANCE AND SCALABILITY

Use sensible performance practices.

Implement:

- Database indexes.
- `select_related()`.
- `prefetch_related()`.
- Efficient selectors.
- Pagination.
- Caching for suitable data.
- Cache invalidation.
- Query optimization.
- Static asset optimization.
- Appropriate upload limits.
- Background processing only where justified.

Redis may support:

- Channels.
- Caching.
- Temporary coordination.

PostgreSQL remains the source of truth.

Avoid premature optimization and unnecessary infrastructure.

---

# PART 23: DEPLOYMENT ARCHITECTURE

Prepare the project for production deployment.

The deployment documentation must cover:

- Django application server.
- ASGI server.
- WSGI server where needed.
- PostgreSQL.
- Redis.
- Static files.
- Public media.
- Private media.- Environment variables.
- HTTPS.
- Domain configuration.
- Database backups.
- Media backups.
- Logging.
- Monitoring.
- Error reporting.
- Database migrations.
- Scheduled management commands.

Document how the system can be deployed on a suitable VPS or managed hosting environment.

Do not assume that a development server is suitable for production.

## 23.1 Development setup

Provide a clear local setup guide.

Include:

- Python environment creation.
- Dependency installation.
- Environment configuration.
- Database configuration.
- Migrations.
- Superuser creation.
- Development server startup.
- Redis setup for local Channels testing where applicable.

SQLite may be used for initial development when PostgreSQL is unavailable, but production must use PostgreSQL.

Do not write application code that silently depends on SQLite-only behavior.

## 23.2 Production settings

Production configuration must enforce:

- `DEBUG=False`.
- Explicit `ALLOWED_HOSTS`.
- HTTPS.
- Secure cookies.
- CSRF trusted origins.
- Secure secret management.
- PostgreSQL.
- Redis.
- Appropriate storage configuration.

Provide backup and restore instructions.

---

# PART 24: DOCUMENTATION

Maintain documentation throughout development.

Create:

```text
docs/
├── architecture/
├── database/
├── api/
├── security/
└── deployment/
```

Document:

- System architecture.
- Project structure.
- App responsibilities.
- Tenant resolution.
- Tenant isolation.
- User roles.
- Permission rules.
- Database relationships.
- API endpoints.
- Authentication.
- Payment workflows.
- Result workflows.
- WebSocket architecture.
- Storage architecture.
- Deployment.
- Backups.
- Testing.

Keep the README updated with installation and startup instructions.

---

# PART 25: DEVELOPMENT METHODOLOGY

Do not attempt to generate the entire project in one uncontrolled response.

Work in clearly defined phases.

Before implementing a phase:

1. Review the existing project structure.
2. Review existing models and dependencies.
3. Identify affected applications.
4. Explain the implementation plan.
5. Identify migration implications.
6. Identify security and tenant-isolation requirements.
7. Implement the phase.
8. Provide complete code for the files being created or changed.
9. Explain where each file belongs.
10. Provide commands to run.
11. Provide relevant tests.
12. Confirm what is completed and what remains.

Do not silently overwrite existing work.

If an existing implementation needs modification, explain why and provide the complete revised file where practical.

Do not create duplicate models, duplicate services, duplicate settings, or competing implementations.

Do not assume a feature exists just because a URL or template has been created.

When a requirement is ambiguous, identify the ambiguity and propose a reasonable default. Ask only when a decision materially affects the architecture or business behavior.

## Phase 1: Architecture and planning

- Confirm requirements.
- Finalize app responsibilities.
- Design the database.
- Define tenancy.
- Define roles and permissions.
- Define the API structure.
- Define UI/UX architecture.
- Produce architecture documentation.

## Phase 2: Project foundation

- Create project structure.
- Configure the single settings file.
- Configure environment variables.
- Configure database.
- Configure ASGI and WSGI.
- Configure static and media files.
- Configure Redis and Channels.
- Configure logging.
- Configure shared base components.

## Phase 3: Multi-tenancy and identity

- Custom user model with structured username/ID prefix scheme.
- School registry.
- School domains.
- Tenant middleware.
- School memberships (supporting multi-school users).
- Roles and permissions.
- Role seeding service.
- AppVariable.
- Tenant security tests.
- Multi-school membership isolation tests.

## Phase 4: Platform management

- Platform dashboard.
- School registration.
- School management.
- Domain management.
- Subscription plans.
- Subscription enforcement.
- Platform notifications.

## Phase 5: School interface and configuration

- Default school layout.
- Dynamic branding.
- Theme selection.
- Sidebar and navigation.
- Role-based dashboards.
- Shared UI components.

## Phase 6: Core school operations

- Staff (with username/ID prefix generation service).
- Academic sessions.
- Terms.
- Sections.
- Classes (with class seeding service invoked on school creation).
- Class activation/deactivation per school.
- Arms.
- Subjects.
- Students (with username/ID prefix generation service).
- Enrollment.
- Parent relationships.
- Teaching assignments.

## Phase 7: Attendance and learning

- Student attendance.
- Staff attendance.
- Learning materials.
- Lesson notes.
- Assignments.
- Submissions.

## Phase 8: Assessments and examinations

- Question bank.
- Question images.
- Assessment builder.
- Online assessments.
- Auto-marking.
- Manual marking.
- Examination management.
- Result calculation.
- Approval and publication.
- Report cards.

## Phase 9: Admissions

- Public application forms.
- Document uploads.
- Application review.
- Admission decisions.
- Admission letters.
- Applicant conversion.

## Phase 10: Finance and store

- Fees.
- Invoices.
- Payments.
- Paystack integration.
- Receipts.
- Financial reporting.
- Products.
- Inventory.
- Orders.
- Stock management.

## Phase 11: Communications and support

- Announcements.
- Notifications.
- Email and SMS delivery.
- Support tickets.
- Anonymous chat.
- Authenticated live chat.
- AI support.

## Phase 12: Complete API implementation

Build and test complete API coverage across all modules.

The API must not be postponed until the web application is finished. Implement each module's API alongside its business functionality.

## Phase 13: Testing and hardening

- Full test suite.
- Tenant isolation review.
- Permission review.
- Security review.
- Performance review.
- API documentation review.
- Workflow testing.

## Phase 14: Production preparation

- Deployment configuration.
- Backups.
- Monitoring.
- Logging.
- Documentation.
- Final acceptance testing.

---

# PART 26: NON-NEGOTIABLE DEVELOPMENT RULES

1. Use Django as a monolith.
2. Use Django Templates for the web interface.
3. Use Tailwind CSS and Vanilla JavaScript.
4. Do not introduce React or another SPA framework.
5. Use PostgreSQL in production.
6. Use a shared-database, shared-schema multi-tenant architecture.
7. Every tenant-owned record must be securely scoped to its school.
8. Use a custom Django user model.
9. Use role and permission assignments instead of boolean role flags.
10. The School Director is not a Django superuser.
11. Platform-level access must be authorized and audited.
12. Use one root `requirements.txt`.
13. Use one `config/settings.py`.
14. Use `RUN_MODE` for development and production configuration.
15. Keep Django applications at the project root.
16. Use `media_library` as the media Django app.
17. Keep CMS functionality out of scope.
18. Retain the media library.
19. Use `AppVariable` for configurable school settings.
20. Use default school templates with optional approved custom templates.
21. Use validated dynamic CSS variables for school branding.
22. Never use arbitrary database values as template filesystem paths.
23. Use Django Channels for live support.
24. Use Redis for production Channels.
25. Keep PostgreSQL as the durable data source.
26. Use services for business operations.
27. Use selectors for complex reads.
28. Share business logic between Django views and API views.
29. Build the complete REST API from the beginning.
30. Do not leave API modules as placeholders.
31. Implement mobile-ready authentication.
32. Document APIs using OpenAPI.
33. Enforce permissions on both web and API requests.
34. Never trust client-supplied tenant IDs.
35. Protect sensitive documents.
36. Verify payments on the backend.
37. Use database transactions for critical financial and inventory operations.
38. Require Principal review before result publication.
39. Missing assessment components must remain Pending, not zero.
40. Students cannot mark their own attendance.
41. Communications must follow the specified school and platform boundaries.
42. Do not implement direct parent/student messaging in the communications module.
43. Do not introduce unnecessary apps or infrastructure.
44. Write readable, maintainable code.
45. Provide tests for important business rules and security boundaries.
46. Keep architecture and API documentation updated.
47. Do not claim a feature is complete until its implementation and tests support that claim.
48. Store public uploads under `media/public/` and private uploads under `media/private/`. Do not create a separate top-level `private_media/` directory.
49. Seed standard roles and all 12 Nigerian school classes atomically when a new school is created. A school must never be left in a partially configured state.
50. School classes default to active. Schools deactivate classes they do not offer. Class deactivation is school-scoped and must not affect other schools.
51. Use a structured prefix username scheme (`SCHOOL_CODE-ROLE_PREFIX-SEQUENCE`) as the institutional ID for staff and students. Username generation must be performed by a service function and audited.
52. A user may belong to more than one school. Each school membership is independent. Tenant isolation is enforced per membership per session. A user does not gain cross-school access simply by having membership at multiple schools.

---

# PART 27: DEFINITION OF DONE

The system is not considered complete merely because its pages render.

A module is complete only when it has:

- Appropriate database models.
- Database constraints and migrations.
- Business logic.
- Tenant isolation.
- Role and permission enforcement.
- Django Template interface.
- Complete relevant API endpoints.
- Input validation.
- Error handling.
- Automated tests.
- Documentation.

The overall system is ready for production preparation when:

1. Multiple schools can register and operate independently.
2. Verified school domains resolve to the correct tenant.
3. Cross-tenant data access is prevented and tested.
4. Each school can configure its identity and branding.
5. Approved custom school templates can be selected safely.
6. All required user roles have correct dashboards and permissions.
7. School academic operations work end to end.
8. Attendance works with the specified permissions.
9. Assessments and examinations follow the defined approval workflow.
10. Admissions applications are tenant-aware.
11. Finance and payment verification work securely.
12. Store purchases and inventory updates remain consistent.
13. Communications follow the defined audience rules.
14. Anonymous and authenticated support conversations work.
15. WebSocket authorization enforces tenant boundaries.
16. Every functional module has complete documented API coverage.
17. Mobile clients can consume the APIs without requiring backend redesign.
18. Sensitive documents are protected.
19. Automated tests cover critical workflows and security.
20. Production deployment, backup, and recovery procedures are documented.
21. Standard Nigerian school classes are automatically seeded when a school is created.
22. Each school can independently deactivate classes it does not offer without affecting other schools.
23. Staff and student usernames conform to the structured prefix scheme and serve as institutional IDs.
24. A user with memberships at two schools can only access one school at a time through that school's verified domain.

---

# FINAL INSTRUCTION TO THE AI DEVELOPMENT ASSISTANT

Treat this document as the authoritative product specification.

Your first task is to produce a comprehensive technical architecture and implementation blueprint before writing application code.

The blueprint must include:

1. System architecture.
2. Multi-tenancy architecture.
3. Project structure.
4. Django application responsibilities.
5. Database model and relationship plan.
6. User, role, and permission architecture.
7. Tenant resolution and domain routing.
8. AppVariable configuration design.
9. Template selection and dynamic branding architecture.
10. UI/UX design system and dashboard plan.
11. Complete API architecture and endpoint matrix.
12. Authentication and authorization strategy.
13. WebSocket and live-support architecture.
14. File and media storage architecture.
15. Payment and inventory transaction design.
16. Security architecture.
17. Testing strategy.
18. Deployment architecture.
19. Development phases and dependencies.

For database design, identify the main models, their relationships, ownership, tenant scope, important constraints, and indexes before generating migrations.

For API design, show the endpoints, HTTP methods, permissions, tenant behavior, and expected operations for every functional module.

For UI/UX, describe the layouts, navigation, dashboards, reusable components, responsive behavior, and theme system.

Identify architectural risks, possible bottlenecks, and important decisions before implementation.

Do not skip requirements because the project is large. Break the work into manageable phases while preserving the complete product scope.

Do not generate the entire codebase in a single response. Complete the architecture blueprint first, obtain confirmation of major architectural decisions, and then implement the project phase by phase.

When implementing code, provide complete, correctly located files and explain how they connect to the rest of the project.

Always prioritize correctness, security, maintainability, tenant isolation, complete API coverage, and a professional user experience.

**The goal is to build a commercially viable, production-grade, multi-tenant Nigerian School Management SaaS platform with a complete web application and a fully mobile-ready API—not a basic school CRUD system.**continue