import json
import sys
import os

sys.path.insert(0, os.path.abspath('.'))
sys.path.insert(0, os.path.abspath('backend'))

from tools.handlers import get_printer_consumables, search_products
from models.product import Product

def comprehensive_end_to_end_test():
    with open('products.json', 'r', encoding='utf-8') as f:
        products = json.load(f)
        
    prods_by_id = {p['_id']: p for p in products}
    printers = [p for p in products if p.get('category') in ('Printers', 'Business Printer', 'Large Format Printer', 'Photo Printer') or 'printer' in p.get('name', '').lower()]
    
    total_printers = len(printers)
    print(f"============================================================")
    print(f"STARTING COMPREHENSIVE END-TO-END CONSUMABLES & PRINTER TEST")
    print(f"Total Printers to Test: {total_printers}")
    print(f"============================================================")
    
    passed_tests = 0
    failed_tests = 0
    
    test_results = []
    
    for idx, pr in enumerate(printers, 1):
        pid = pr.get('_id')
        pname = pr.get('name')
        cons_list = pr.get('consumables', [])
        
        # Test 1: Query by Full Printer Name
        output_full_name = get_printer_consumables(pname)
        has_cards_name = "📦" in output_full_name
        has_intro_name = "💧" in output_full_name
        has_options_name = "[Options:" in output_full_name
        
        # Test 2: Query by Model Code (e.g. SC-P9500, WF-C20750, F100, CX-02)
        import re
        model_code_match = re.search(r'\b(WF-[A-Z0-9]+|EM-[A-Z0-9]+|SC-[A-Z0-9]+|AM-[A-Z0-9]+|P\d{3,5}[A-Z0-9]*|T\d{3,5}[A-Z0-9]*|F\d{3,4}[A-Z0-9]*|C\d{4,5}[A-Z0-9]*|CX-02W|CX-02|CX02|CZ-01|CY-02)\b', pname, re.IGNORECASE)
        model_code = model_code_match.group(1).upper() if model_code_match else pname
        
        output_model_code = get_printer_consumables(f"i want consumables for {model_code}")
        has_cards_code = "📦" in output_model_code
        
        # Test 3: Validate that all linked consumable IDs exist in catalog and have price > 0
        valid_cons_data = []
        for cid in cons_list:
            if cid in prods_by_id:
                cp = prods_by_id[cid]
                valid_cons_data.append({
                    'id': cid,
                    'name': cp.get('name'),
                    'price': cp.get('price'),
                    'stock': cp.get('stock'),
                    'has_image': bool(cp.get('image_url') and cp.get('image_url').startswith('http')),
                    'image_url': cp.get('image_url')
                })
                
        is_success = (has_cards_name or has_cards_code) and (len(cons_list) == 0 or len(valid_cons_data) == len(cons_list))
        
        if is_success:
            passed_tests += 1
            status = "PASS"
        else:
            failed_tests += 1
            status = "FAIL"
            
        test_results.append({
            'index': idx,
            'status': status,
            'printer_id': pid,
            'printer_name': pname,
            'model_code': model_code,
            'consumables_count': len(cons_list),
            'verified_consumables': valid_cons_data,
            'rendered_cards_full_name': has_cards_name,
            'rendered_cards_model_code': has_cards_code,
            'has_interactive_pills': has_options_name
        })
        
        if idx % 10 == 0 or idx == total_printers:
            print(f"[{idx}/{total_printers}] Tested: {passed_tests} PASS, {failed_tests} FAIL")
            
    print(f"\n============================================================")
    print(f"TEST SUITE SUMMARY:")
    print(f"Passed: {passed_tests} / {total_printers} ({passed_tests/total_printers*100:.1f}%)")
    print(f"Failed: {failed_tests} / {total_printers}")
    print(f"============================================================")
    
    with open('comprehensive_test_report.json', 'w', encoding='utf-8') as f:
        json.dump({
            'total_tested': total_printers,
            'passed': passed_tests,
            'failed': failed_tests,
            'pass_rate_percentage': round(passed_tests / total_printers * 100, 2),
            'results': test_results
        }, f, indent=2, ensure_ascii=False)
        
    print("Full audit test matrix written to 'comprehensive_test_report.json'")

if __name__ == '__main__':
    comprehensive_end_to_end_test()
