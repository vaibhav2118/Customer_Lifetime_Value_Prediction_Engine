import logging
import requests
import json
from sqlalchemy.orm import Session
from clv_platform.database.models import WebhookSubscription, WebhookDelivery

log = logging.getLogger(__name__)

def trigger_webhook_event(db_session_factory, tenant_id: int, event_type: str, payload: dict):
    """
    Finds active webhook subscriptions for the tenant and dispatches the payload.
    Uses database session factory to create a thread-safe db session when running inside background tasks.
    """
    db = db_session_factory()
    try:
        subscriptions = (
            db.query(WebhookSubscription)
            .filter(
                WebhookSubscription.tenant_id == tenant_id,
                WebhookSubscription.event_type == event_type,
                WebhookSubscription.is_active == True
            )
            .all()
        )
        
        if not subscriptions:
            return

        for sub in subscriptions:
            try:
                headers = {
                    "Content-Type": "application/json",
                    "X-CLV-Signature": sub.secret,
                    "X-CLV-Event": event_type
                }
                
                # Make HTTP POST request
                resp = requests.post(
                    sub.target_url, 
                    data=json.dumps(payload), 
                    headers=headers, 
                    timeout=15
                )
                
                # Log delivery
                delivery = WebhookDelivery(
                    subscription_id=sub.id,
                    payload=payload,
                    status_code=resp.status_code,
                    response_body=resp.text[:1000] # Cap size
                )
                db.add(delivery)
                
            except Exception as e:
                log.error("Failed to deliver webhook sub ID %d: %s", sub.id, e)
                delivery = WebhookDelivery(
                    subscription_id=sub.id,
                    payload=payload,
                    status_code=500,
                    response_body=str(e)[:1000]
                )
                db.add(delivery)
        
        db.commit()
    except Exception as e:
        log.error("Webhook trigger failed: %s", e)
    finally:
        db.close()
