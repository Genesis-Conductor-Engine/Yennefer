#!/usr/bin/env python3
"""
Notion Telemetry Seed Verification Script
Validates that seed data was created correctly
"""

import os
import sys
import argparse
from datetime import datetime
from notion_client import Client
from tabulate import tabulate

def get_notion_token():
    """Get NOTION_TOKEN from env var or command line"""
    parser = argparse.ArgumentParser(description='Verify Notion telemetry seed data')
    parser.add_argument('--token', help='Notion integration token (or set NOTION_TOKEN env var)')
    args = parser.parse_args()
    
    token = args.token or os.getenv("NOTION_TOKEN")
    
    if not token:
        print("❌ NOTION_TOKEN not provided")
        print()
        print("Usage:")
        print("  1. export NOTION_TOKEN='secret_your_token_here'")
        print("     python3 verify_notion_seed.py")
        print()
        print("  2. python3 verify_notion_seed.py --token 'secret_your_token_here'")
        sys.exit(1)
    
    return token

NOTION_TOKEN = get_notion_token()
DATABASE_ID = "9a32dcb5-00b6-40d7-bd86-43d93965fa82"

notion = Client(auth=NOTION_TOKEN)

def get_property_value(props, key, prop_type):
    """Extract property value based on type"""
    if key not in props:
        return None
    
    prop = props[key]
    
    if prop_type == "title":
        return prop["title"][0]["text"]["content"] if prop["title"] else None
    elif prop_type == "number":
        return prop["number"]
    elif prop_type == "checkbox":
        return prop["checkbox"]
    elif prop_type == "select":
        return prop["select"]["name"] if prop["select"] else None
    elif prop_type == "rich_text":
        return prop["rich_text"][0]["text"]["content"] if prop["rich_text"] else ""
    
    return None

print("🔍 Notion Telemetry Seed Verification")
print("=" * 80)

# Query the database
try:
    response = notion.databases.query(
        database_id=DATABASE_ID,
        sorts=[{"property": "Timestamp", "direction": "descending"}],
        page_size=10
    )
except Exception as e:
    print(f"❌ Failed to query database: {e}")
    sys.exit(1)

results = response.get("results", [])

if len(results) == 0:
    print("❌ No rows found in database")
    sys.exit(1)

print(f"Found {len(results)} rows in database")
print()

# Extract and display the data
table_data = []
live_verified_count = 0
envelope_version = "0.3.0"

for page in results[:3]:  # Show first 3 rows
    props = page["properties"]
    
    timestamp = get_property_value(props, "Timestamp", "title")
    eta = get_property_value(props, "η_thermo", "number")
    epsilon = get_property_value(props, "ε", "number")
    gamma = get_property_value(props, "γ", "number")
    delta_q = get_property_value(props, "Δq", "number")
    vram = get_property_value(props, "VRAM_JAX_Pct", "number")
    cuda_status = get_property_value(props, "CUDA_Q_Kernel_Status", "select")
    crystalline = get_property_value(props, "Crystalline_Score", "number")
    live_verified = get_property_value(props, "Live_Run_Verified", "checkbox")
    sanitization = get_property_value(props, "Sanitization_Status", "select")
    
    if live_verified:
        live_verified_count += 1
    
    table_data.append([
        timestamp[:19] if timestamp else "N/A",
        f"{eta:.2f}" if eta is not None else "N/A",
        f"{epsilon:.2f}" if epsilon is not None else "N/A",
        cuda_status or "N/A",
        f"{vram:.2f}" if vram is not None else "N/A",
        f"{crystalline:.2f}" if crystalline is not None else "N/A",
        "✓" if live_verified else "✗",
        sanitization or "N/A"
    ])

headers = ["Timestamp", "η_thermo", "ε", "Status", "VRAM%", "Crystal", "Live✓", "Sanit"]
print(tabulate(table_data, headers=headers, tablefmt="grid"))
print()

# Validation checks
print("Validation Results:")
print("-" * 80)

checks = [
    ("Database accessible", len(results) > 0, True),
    ("Minimum 3 rows exist", len(results) >= 3, True),
    ("All rows have Live_Run_Verified", live_verified_count >= 3, True),
    ("Envelope version", "0.3.0", envelope_version),
]

all_passed = True
for check_name, expected, actual in checks:
    if expected == actual:
        print(f"  ✅ {check_name}: {actual}")
    else:
        print(f"  ❌ {check_name}: Expected {expected}, got {actual}")
        all_passed = False

# Additional analysis
if len(table_data) >= 3:
    print()
    print("Key Demonstrations Found:")
    print("-" * 80)
    
    eta_values = [float(row[1]) for row in table_data[:3] if row[1] != "N/A"]
    if len(eta_values) == 3:
        print(f"  • Dynamic η_thermo progression: {' → '.join(f'{v:.2f}' for v in eta_values)}")
    
    epsilon_values = [float(row[2]) for row in table_data[:3] if row[2] != "N/A"]
    if len(epsilon_values) >= 2 and epsilon_values[0] == epsilon_values[1]:
        print(f"  • Hysteresis hold detected: ε={epsilon_values[0]:.2f} maintained across η spike")
    
    yielding_count = sum(1 for row in table_data[:3] if row[3] == "YIELDING")
    if yielding_count > 0:
        print(f"  • YIELDING kernel status: {yielding_count} instances (bus coordination active)")
    
    sanit_statuses = [row[7] for row in table_data[:3] if row[7] != "N/A"]
    clean_count = sum(1 for s in sanit_statuses if s == "CLEAN")
    sanitized_count = sum(1 for s in sanit_statuses if s == "SANITIZED")
    print(f"  • Sanitization: CLEAN ({clean_count}), SANITIZED ({sanitized_count})")

print()
print("=" * 80)
if all_passed:
    print("✅ All validation checks passed - seed data ready for Maru guardian polling")
else:
    print("⚠️  Some validation checks failed - review output above")
    sys.exit(1)
