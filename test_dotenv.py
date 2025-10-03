#!/usr/bin/env python3
"""Quick test to verify .env loading"""

import os

from dotenv import load_dotenv

print("=== Testing dotenv loading ===")
load_dotenv()

vars_to_check = [
    "USE_SEMANTIC_CACHE",
    "SEMANTIC_CACHE_THRESHOLD",
    "SEMANTIC_CACHE_SIZE",
    "SEMANTIC_CACHE_TTL",
]

for var in vars_to_check:
    value = os.getenv(var)
    status = "✅" if value else "❌"
    print(f"{status} {var} = {value}")

print(f"\nCache would be enabled: {os.getenv('USE_SEMANTIC_CACHE', 'true').lower() == 'true'}")
