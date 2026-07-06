from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class AIDashboardOut(BaseModel):
    lead_score_distribution: Dict[str, int]
    avg_win_probability: Optional[float]
    pipeline_health: Dict[str, Any]
    at_risk_customers: List[Dict[str, Any]]
    follow_up_recommendations: List[Dict[str, Any]]
    daily_recommendations: List[Dict[str, Any]]
    recent_activity: List[Dict[str, Any]]
    usage_stats: Dict[str, Any]
