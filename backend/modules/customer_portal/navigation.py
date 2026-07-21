# Deliberately empty: this module has no staff-facing screen of its own --
# portal-access management is a widget on the existing CRM Customer detail
# page (frontend/app/(app)/crm/customers/[id]/page.tsx), not a new nav entry.
# The customer-facing side (/portal/...) is a separate, unauthenticated (from
# the staff app's perspective) route tree with its own login, not part of the
# staff AppShell's navigation at all.
CUSTOMER_PORTAL_NAVIGATION = []
