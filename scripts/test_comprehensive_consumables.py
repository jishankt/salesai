import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.stdout.reconfigure(encoding='utf-8')
from services.pre_router import resolve_conversational_subject
from tools.handlers import get_printer_consumables

test_suite = [
    # 1. Citizen Dye-Sub Photo Printers
    ('Citizen CX-02W', 'i want ink for citizen cx-02w', ['CX2W 812', 'Citizen Pen']),
    ('Citizen CX-02', 'give me consumables for CX-02', ['CX2.4x6', 'CX2.6X8', 'Citizen Pen']),
    ('Citizen CZ-01', 'supplies for CZ-01 printer', ['CZ-MS46', 'Citizen Pen']),
    
    # 2. Epson Large Format Fine Art Printers
    ('Epson SC-P900', 'i want inks for SC-P900', ['C13T47A100', 'C13T47A200', 'C13T47A300', 'C12C935711']),
    ('Epson SC-P20000', 'what inks does SC-P20000 use', ['C13T800100', 'C13T800200', 'C13T619300']),
    ('Epson SC-P9500', 'inks for SC-P9500', ['C13T44Q140', 'C13T44Q240']),
    ('Epson SC-P9000', 'consumables for SC-P9000', ['C13T54X100', 'C13T55K100', 'C13T699700']),
    
    # 3. Epson Dye-Sub & Technical Printers
    ('Epson SC-F100', 'list all the inks for F100', ['C13T49N100', 'C13T49N200', 'C13S210125']),
    ('Epson SC-F500', 'ink for sc-f500', ['C13T49N100']),
    
    # 4. Epson WorkForce Office Series
    ('Epson WF-C5890', 'i want inks for WF-C5890', ['C13T11C140', 'C13T11D140', 'C13T11E140', 'C12C938211']),
    ('Epson WF-C879R', 'inks for WF-C879R', ['C13T05B140', 'C13T05A100', 'C13T671400']),
    ('Epson WF-C21000', 'ink cartridges for WF-C21000', ['C13T02Y100', 'C13T02Y200'])
]

passed = 0
failed = 0

print("===============================================================")
print("RUNNING COMPREHENSIVE SUITE: EXACT PRINTER CONSUMABLES & ROUTING")
print("===============================================================\n")

for model_name, user_query, expected_skus in test_suite:
    resolved = resolve_conversational_subject('test_session', user_query)
    raw_res = get_printer_consumables(user_query)
    
    has_header = '💧' in raw_res and 'Compatible Consumables' in raw_res
    has_all_expected = all(sku in raw_res for sku in expected_skus)
    
    if has_header and has_all_expected:
        print(f"✅ PASS: {model_name:20} | Query: '{user_query}'")
        passed += 1
    else:
        print(f"❌ FAIL: {model_name:20} | Query: '{user_query}'")
        print(f"   Resolved: {resolved}")
        print(f"   Header ok: {has_header}, Expected SKUs in res: {has_all_expected}")
        failed += 1

print("\n---------------------------------------------------------------")
print(f"TOTAL: {len(test_suite)} | PASSED: {passed} | FAILED: {failed}")
print("===============================================================")
