from sqlalchemy import func
from sqlalchemy.orm import Session
from clv_platform.database.models import Transaction

def generate_recommendations(customer_id: str, tier: str, db: Session) -> str:
    """
    Generates actionable business recommendations based on the customer's CLV tier
    and historical transaction descriptions.
    """
    # Query customer's top 3 items to personalize the recommendation details
    top_items = (
        db.query(Transaction.description)
        .filter(Transaction.customer_id == customer_id)
        .group_by(Transaction.description)
        .order_by(func.count(Transaction.description).desc())
        .limit(3)
        .all()
    )
    
    item_list = [item[0] for item in top_items if item[0]]
    items_str = ", ".join(item_list[:2]) if item_list else "recent purchases"
    
    if tier == "Platinum":
        return (
            "⭐ Platinum Tier Retention Campaign:\n"
            f"- Assign dedicated VIP account manager (Priority Tier 1 Support).\n"
            "- Exclusive invitations to annual brand events and private product showcases.\n"
            f"- Send high-value custom reward matching their preference for: {items_str}.\n"
            "- Direct 25% loyal VIP discount valid for the next 180 days."
        )
    elif tier == "Gold":
        return (
            "🥇 Gold Tier Growth Plan:\n"
            f"- Send invitation to the exclusive Gold Loyalty Club.\n"
            f"- Recommend early-access collections related to: {items_str}.\n"
            "- Send email offering free shipping + 15% discount on their next 3 orders.\n"
            "- Target with monthly cohort feedback surveys."
        )
    elif tier == "Silver":
        return (
            "🥈 Silver Tier Cross-Selling Drive:\n"
            f"- Deliver targeted recommendations of matching complements for: {items_str}.\n"
            "- Offer a bundle discount (Buy 2, Get 1 50% Off) on complementary products.\n"
            "- Send seasonal trend newsletters with social proof reviews."
        )
    else:  # Bronze
        return (
            "🥉 Bronze Tier Nurturing Campaign:\n"
            "- Send a welcome discount code (10% off next purchase).\n"
            "- Enroll in standard email nurturing campaign introducing top-selling brand lines.\n"
            "- Re-engage via retargeting ads if inactive for more than 45 days.\n"
            "- Offer entry-level loyalty rewards to stimulate repeat purchases."
        )
