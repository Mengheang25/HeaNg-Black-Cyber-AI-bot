#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Runtime configuration checker for Render.com deployment
Ensures all necessary configurations are in place before starting the bot
"""

import os
import sys
import sqlite3
from pathlib import Path

def check_environment():
    """Check if all required environment variables are set"""
    print("[CHECK] Verifying environment variables...")
    
    required = ['TELEGRAM_TOKEN', 'OPENROUTER_KEY']
    missing = []
    
    for var in required:
        if not os.getenv(var):
            missing.append(var)
            print(f"[WARNING] Missing: {var}")
        else:
            print(f"[OK] Found: {var}")
    
    if missing:
        print(f"\n[ERROR] Missing environment variables: {', '.join(missing)}")
        return False
    
    return True

def check_database():
    """Check and initialize database if needed"""
    print("\n[CHECK] Verifying database configuration...")
    
    db_path = os.getenv("DATABASE_PATH", "date_user.db")
    enable_history = os.getenv("ENABLE_HISTORY", "true").lower() == "true"
    
    if not enable_history:
        print("[INFO] History disabled, skipping database check")
        return True
    
    # Create directory if needed
    db_dir = os.path.dirname(db_path)
    if db_dir and not os.path.exists(db_dir):
        try:
            os.makedirs(db_dir, exist_ok=True)
            print(f"[OK] Created database directory: {db_dir}")
        except Exception as e:
            print(f"[ERROR] Failed to create database directory: {e}")
            return False
    
    # Check if database exists
    if os.path.exists(db_path):
        print(f"[OK] Database exists: {db_path}")
        try:
            # Verify database is valid
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            conn.close()
            print(f"[OK] Database is valid with {len(tables)} tables")
            return True
        except Exception as e:
            print(f"[ERROR] Database is corrupted: {e}")
            return False
    else:
        print(f"[INFO] Database will be created on first run: {db_path}")
        return True

def check_system_prompt():
    """Check if system prompt file exists"""
    print("\n[CHECK] Verifying system prompt...")
    
    if os.path.exists("system_prompt.b"):
        with open("system_prompt.b", "r", encoding="utf-8") as f:
            prompt = f.read()
        print(f"[OK] System prompt found ({len(prompt)} bytes)")
        return True
    else:
        print("[WARNING] system_prompt.b not found, will use default prompt")
        return True

def check_dependencies():
    """Check if required packages are installed"""
    print("\n[CHECK] Verifying Python dependencies...")
    
    required = [
        'telegram',
        'requests',
        'dotenv'
    ]
    
    missing = []
    for package in required:
        try:
            __import__(package.replace('-', '_'))
            print(f"[OK] {package} installed")
        except ImportError:
            missing.append(package)
            print(f"[WARNING] {package} not installed")
    
    if missing:
        print(f"\n[ERROR] Missing packages: {', '.join(missing)}")
        print("Install with: pip install -r requirements.txt")
        return False
    
    return True

def main():
    """Run all checks"""
    print("=" * 50)
    print("HeaNg[Black-Cyber] Bot - Pre-flight Check")
    print("=" * 50)
    
    checks = [
        ("Dependencies", check_dependencies),
        ("Environment", check_environment),
        ("System Prompt", check_system_prompt),
        ("Database", check_database),
    ]
    
    results = []
    for name, check_func in checks:
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print(f"[ERROR] {name} check failed: {e}")
            results.append((name, False))
    
    # Summary
    print("\n" + "=" * 50)
    print("PRE-FLIGHT CHECK SUMMARY")
    print("=" * 50)
    
    for name, result in results:
        status = "[OK]" if result else "[FAIL]"
        print(f"{status} {name}")
    
    all_passed = all(result for _, result in results)
    
    if all_passed:
        print("\n[OK] All checks passed! Bot is ready to start.")
        return 0
    else:
        print("\n[ERROR] Some checks failed. Fix issues before starting bot.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
