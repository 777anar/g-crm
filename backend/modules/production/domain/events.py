"""Domain events published by the Production module."""

WORK_ORDER_CREATED = "WorkOrderCreated"
WORK_ORDER_STATUS_CHANGED = "WorkOrderStatusChanged"
WORK_ORDER_COMPLETED = "WorkOrderCompleted"
WORK_ORDER_CANCELLED = "WorkOrderCancelled"

# Phase 1: Stone Fabrication Workflow -- configurable stages, priority, and
# operator assignment on top of the existing coarse status lifecycle.
WORK_ORDER_STAGE_CHANGED = "WorkOrderStageChanged"
WORK_ORDER_PRIORITY_CHANGED = "WorkOrderPriorityChanged"
WORK_ORDER_OPERATOR_ASSIGNED = "WorkOrderOperatorAssigned"
PRODUCTION_STAGE_CREATED = "ProductionStageCreated"
