from typing import List
from src.models import ProductMatchedItem, RelatedProductItem

def format_whatsapp_response(matched: List[ProductMatchedItem], related: List[RelatedProductItem]) -> str:
    if not matched:
        return "I could not find an exact match in our Kepler Tech catalog. Could you share the specific printer model, brand, or supplies you are looking for?"

    top = matched[0]
    lines = []
    
    # Header with icon
    if "printer" in top.category.lower():
        lines.append(f"🖨️ *Recommended Product*")
    elif "ink" in top.category.lower():
        lines.append(f"💧 *Product Details*")
    elif "media" in top.category.lower() or "paper" in top.category.lower() or "canvas" in top.category.lower():
        lines.append(f"📜 *Recommended Media*")
    else:
        lines.append(f"📦 *Product Recommendation*")

    lines.append(f"*{top.name}*")
    if top.sku:
        lines.append(f"SKU: `{top.sku}`")
    lines.append("")
    
    # Grounded description
    if top.smart_description:
        lines.append(top.smart_description)
        lines.append("")

    # Specifications bullets
    if top.specifications:
        lines.append("*Key Specifications:*")
        for k, v in top.specifications.items():
            k_fmt = k.replace("_", " ").title()
            if isinstance(v, list):
                v_fmt = ", ".join(v[:5])
            else:
                v_fmt = str(v)
            lines.append(f"• {k_fmt}: {v_fmt}")
        lines.append("")

    # Price if present
    if top.price > 0:
        lines.append(f"💰 *Price:* {top.currency} {top.price:,.2f}")
        lines.append("")

    # Related / Compatible Products
    if related:
        lines.append("*Compatible & Related Supplies:*")
        for rel in related[:3]:
            rel_type = f" ({rel.relationship_type.title()})" if rel.relationship_type else ""
            lines.append(f"• {rel.name}{rel_type}")
        lines.append("")

    # Direct Website Link
    lines.append("🔗 *View on Kepler Tech LLC:*")
    lines.append(f"{top.website_url}")

    return "\n".join(lines)
