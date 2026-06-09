import logging
from sqlalchemy.orm import Session
from sqlalchemy import text
from clv_platform.database.models import CustomerClvPrediction, CustomerSegment

log = logging.getLogger(__name__)

def calculate_customer_health_score(
    predicted_clv: float, 
    churn_risk: float, 
    recency: float, 
    frequency: float
) -> dict:
    """
    Computes a customer health score from 0 to 100 based on metrics.
    Formula:
      - Churn Risk Weight (40%): (1 - churn_risk) * 40
      - Frequency Weight (20%): min(frequency / 10.0, 1.0) * 20
      - Recency Weight (20%): max(0, (365 - recency) / 365.0) * 20
      - Monetary/CLV Weight (20%): min(predicted_clv / 500.0, 1.0) * 20
    """
    # Normalize inputs
    churn_component = (1.0 - min(max(churn_risk, 0.0), 1.0)) * 40.0
    freq_component = min(max(frequency, 0.0) / 15.0, 1.0) * 20.0
    rec_component = max(0.0, (365.0 - min(max(recency, 0.0), 365.0)) / 365.0) * 20.0
    clv_component = min(max(predicted_clv, 0.0) / 600.0, 1.0) * 20.0

    score = round(churn_component + freq_component + rec_component + clv_component, 1)
    
    if score >= 80:
        label = "Excellent"
        color = "#38A169" # Green
    elif score >= 60:
        label = "Good"
        color = "#3182CE" # Blue
    elif score >= 40:
        label = "Fair"
        color = "#DD6B20" # Orange
    else:
        label = "Poor"
        color = "#E53E3E" # Red

    return {
        "health_score": score,
        "label": label,
        "color": color,
        "components": {
            "retention_reliability": round(churn_component, 1),
            "purchase_frequency": round(freq_component, 1),
            "recency_activity": round(rec_component, 1),
            "clv_value_index": round(clv_component, 1)
        }
    }

def get_tenant_health_distribution(db: Session, tenant_id: int = None) -> dict:
    """
    Query database predictions and segments to build health distributions.
    """
    query = """
        SELECT p.customer_id, p.predicted_clv_6months, p.churn_risk_score, s.recency, s.frequency
        FROM customer_clv_predictions p
        JOIN customer_segments s ON p.customer_id = s.customer_id
        WHERE 1=1
    """
    params = {}
    if tenant_id is not None:
        query += " AND p.tenant_id = :tenant_id"
        params["tenant_id"] = tenant_id

    result = db.execute(text(query), params).fetchall()
    
    distribution = {"Excellent": 0, "Good": 0, "Fair": 0, "Poor": 0}
    total_score = 0.0
    count = 0
    
    for row in result:
        # row: (customer_id, clv, churn, recency, frequency)
        health = calculate_customer_health_score(
            predicted_clv=float(row[1] or 0.0),
            churn_risk=float(row[2] or 0.5),
            recency=float(row[3] or 180.0),
            frequency=float(row[4] or 1.0)
        )
        distribution[health["label"]] += 1
        total_score += health["health_score"]
        count += 1
        
    avg_score = round(total_score / count, 1) if count > 0 else 0.0
    return {
        "average_health_score": avg_score,
        "counts": distribution,
        "total_evaluated": count
    }
