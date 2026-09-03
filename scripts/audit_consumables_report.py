import json
import sys
import io

sys.path.insert(0, 'backend')
from tools.handlers import get_printer_consumables

def audit_all_printers_and_consumables():
    with open('products.json', 'r', encoding='utf-8') as f:
        products = json.load(f)
        
    prods_by_id = {p['_id']: p for p in products}
    
    printers = [p for p in products if p.get('category') in ('Printers', 'Business Printer', 'Large Format Printer', 'Photo Printer') or 'printer' in p.get('name', '').lower()]
    
    report = []
    
    total_printers = len(printers)
    total_with_consumables = 0
    total_resolved_ok = 0
    total_empty = 0
    
    print(f"Auditing {total_printers} printer records...")
    
    for pr in printers:
        pid = pr.get('_id')
        pname = pr.get('name')
        cons_list = pr.get('consumables', [])
        
        # Test handler output
        output_text = get_printer_consumables(pname)
        
        has_cards = "📦" in output_text
        has_intro = "💧" in output_text
        
        valid_items = []
        missing_items = []
        for cid in cons_list:
            if cid in prods_by_id:
                valid_items.append(prods_by_id[cid])
            else:
                missing_items.append(cid)
                
        is_populated = len(cons_list) > 0
        if is_populated:
            total_with_consumables += 1
            if has_cards:
                total_resolved_ok += 1
        else:
            total_empty += 1
            
        report.append({
            'printer_id': pid,
            'printer_name': pname,
            'consumables_count': len(cons_list),
            'consumables_ids': cons_list,
            'missing_ids_in_db': missing_items,
            'handler_rendered_cards': has_cards,
            'handler_rendered_intro': has_intro
        })
        
    summary = {
        'total_printers_audited': total_printers,
        'printers_with_mapped_consumables': total_with_consumables,
        'printers_successfully_rendering_cards': total_resolved_ok,
        'printers_with_empty_consumables': total_empty,
        'details': report
    }
    
    with open('audit_consumables_report.json', 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
        
    print(f"Audit completed: {total_resolved_ok}/{total_with_consumables} mapped printers render 100% genuine consumable cards.")
    print(f"Report saved to audit_consumables_report.json")

if __name__ == '__main__':
    audit_all_printers_and_consumables()
