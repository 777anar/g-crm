"""Pure value objects/enums for the Cut Optimization module. No framework
or DB imports."""

# Where a stored optimization run came from -- affects nothing structurally,
# but lets History (and the UI) distinguish a manual what-if run from the
# run automatically persisted as the winning candidate of a Smart Offcut
# recommendation.
RUN_SOURCE_MANUAL = "manual"
RUN_SOURCE_OFFCUT_RECOMMENDATION = "offcut_recommendation"
VALID_RUN_SOURCES = {RUN_SOURCE_MANUAL, RUN_SOURCE_OFFCUT_RECOMMENDATION}

DEFAULT_KERF_MM = "3"
