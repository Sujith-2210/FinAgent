#!/usr/bin/env python3
"""
Simple fix: read knowledge.py.backup and restore with correct logic
"""

# Just restore from backup first
import shutil
shutil.copy('/Users/sujith/Documents/FinAgent/New/backend/app/agents/knowledge.py.backup',
            '/Users/sujith/Documents/FinAgent/New/backend/app/agents/knowledge.py')

print("✓ Restored knowledge.py from backup")
