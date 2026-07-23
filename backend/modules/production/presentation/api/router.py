from fastapi import APIRouter

from modules.production.presentation.api.notifications import router as notifications_router
from modules.production.presentation.api.production_job import router as production_job_router
from modules.production.presentation.api.stages import router as stages_router
from modules.production.presentation.api.work_orders import router as work_orders_router

# work_orders_router carries a catch-all `GET /{work_order_id}` (and the
# module-root "" list/create routes, which FastAPI's include_router()
# refuses to re-mount under a fresh empty-prefix wrapper). stages_router
# (`/stages`), notifications_router (`/notifications`), and
# production_job_router (`/{work_order_id}/job` etc.) must all be matched
# *before* that catch-all -- a request to `/stages` or `/notifications`
# structurally also matches the single-segment `/{work_order_id}` pattern,
# and Starlette resolves ambiguous routes in registration order. Splicing
# the route lists directly (rather than calling .include_router(), which
# appends to the end) puts the more specific routes first.
production_router_main = APIRouter()
production_router_main.routes.extend(stages_router.routes)
production_router_main.routes.extend(notifications_router.routes)
production_router_main.routes.extend(production_job_router.routes)
production_router_main.routes.extend(work_orders_router.routes)
