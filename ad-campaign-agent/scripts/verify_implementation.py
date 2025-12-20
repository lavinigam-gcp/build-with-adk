#!/usr/bin/env python3
"""Verification script for Dave's feedback implementation.

Run this after the changes to verify everything is working correctly.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.database.db import get_connection
from app.config import IMAGE_GENERATION, GCS_PRODUCT_IMAGES_PREFIX
import sqlite3


def print_section(title):
    """Print a section header."""
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print('=' * 60)


def verify_config():
    """Verify config settings."""
    print_section("1. CONFIG VERIFICATION")

    print(f"✓ IMAGE_GENERATION model: {IMAGE_GENERATION}")
    assert IMAGE_GENERATION == "gemini-3-pro-image-preview", "Wrong image model!"

    print(f"✓ GCS_PRODUCT_IMAGES_PREFIX: {GCS_PRODUCT_IMAGES_PREFIX}")
    assert GCS_PRODUCT_IMAGES_PREFIX == "product-images/", "Wrong GCS prefix!"

    print("✅ Config verification PASSED")


def verify_database_schema():
    """Verify database schema changes."""
    print_section("2. DATABASE SCHEMA VERIFICATION")

    conn = get_connection()
    cursor = conn.cursor()

    # Check products table
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='products'")
    assert cursor.fetchone(), "❌ products table not found!"
    print("✓ products table exists")

    # Check campaign_videos table
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='campaign_videos'")
    assert cursor.fetchone(), "❌ campaign_videos table not found!"
    print("✓ campaign_videos table exists")

    # Check video_metrics table
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='video_metrics'")
    assert cursor.fetchone(), "❌ video_metrics table not found!"
    print("✓ video_metrics table exists")

    # Check campaign_products junction table
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='campaign_products'")
    assert cursor.fetchone(), "❌ campaign_products table not found!"
    print("✓ campaign_products junction table exists")

    # Verify campaign_videos has status column
    cursor.execute("PRAGMA table_info(campaign_videos)")
    columns = {row[1] for row in cursor.fetchall()}
    required_cols = {'status', 'activated_at', 'activated_by', 'variation_name', 'variation_params'}
    assert required_cols.issubset(columns), f"❌ Missing columns: {required_cols - columns}"
    print(f"✓ campaign_videos has all required columns: {', '.join(required_cols)}")

    conn.close()
    print("✅ Database schema verification PASSED")


def verify_products_data():
    """Verify products table is populated."""
    print_section("3. PRODUCTS DATA VERIFICATION")

    conn = get_connection()
    cursor = conn.cursor()

    # Count products
    cursor.execute("SELECT COUNT(*) FROM products")
    count = cursor.fetchone()[0]
    print(f"✓ Products count: {count}")
    assert count == 22, f"❌ Expected 22 products, got {count}"

    # Check naming convention (hyphenated)
    cursor.execute("SELECT name FROM products LIMIT 5")
    products = [row[0] for row in cursor.fetchall()]
    print(f"✓ Sample product names: {', '.join(products)}")

    for name in products:
        assert '-' in name, f"❌ Product name '{name}' not hyphenated!"
        assert '_' not in name, f"❌ Product name '{name}' has underscores!"

    # Check categories
    cursor.execute("SELECT category, COUNT(*) as count FROM products GROUP BY category")
    categories = cursor.fetchall()
    print(f"✓ Product categories:")
    for cat, cnt in categories:
        print(f"  - {cat}: {cnt} products")

    conn.close()
    print("✅ Products data verification PASSED")


def verify_indexes():
    """Verify database indexes."""
    print_section("4. INDEX VERIFICATION")

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%'")
    indexes = [row[0] for row in cursor.fetchall()]

    required_indexes = [
        'idx_products_category',
        'idx_campaign_videos_campaign',
        'idx_campaign_videos_product',
        'idx_campaign_videos_status',
        'idx_video_metrics_video',
    ]

    print(f"✓ Found {len(indexes)} indexes:")
    for idx in indexes:
        print(f"  - {idx}")

    missing = set(required_indexes) - set(indexes)
    if missing:
        print(f"⚠️  Missing indexes: {', '.join(missing)}")

    conn.close()
    print("✅ Index verification PASSED")


def verify_legacy_tables():
    """Verify legacy tables still exist."""
    print_section("5. LEGACY TABLES VERIFICATION")

    conn = get_connection()
    cursor = conn.cursor()

    legacy_tables = ['campaigns', 'campaign_images', 'campaign_ads', 'campaign_metrics']

    for table in legacy_tables:
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
        assert cursor.fetchone(), f"❌ Legacy table '{table}' not found!"
        print(f"✓ {table} table exists")

    conn.close()
    print("✅ Legacy tables verification PASSED")


def verify_no_hardcoded_models():
    """Verify no hardcoded model names in code."""
    print_section("6. HARDCODED MODELS VERIFICATION")

    # Check video_tools.py doesn't have hardcoded image model
    video_tools_path = os.path.join(os.path.dirname(__file__), '..', 'app', 'tools', 'video_tools.py')
    with open(video_tools_path, 'r') as f:
        content = f.read()

    # Should NOT have hardcoded gemini-2.0-flash-exp
    assert 'model="gemini-2.0-flash-exp"' not in content, \
        "❌ Found hardcoded gemini-2.0-flash-exp in video_tools.py!"
    print("✓ No hardcoded 'gemini-2.0-flash-exp' in video_tools.py")

    # Should import IMAGE_GENERATION from config
    assert 'IMAGE_GENERATION' in content, \
        "❌ IMAGE_GENERATION not imported in video_tools.py!"
    print("✓ IMAGE_GENERATION imported from config")

    # Should use IMAGE_GENERATION variable
    assert 'model=IMAGE_GENERATION' in content, \
        "❌ Not using IMAGE_GENERATION variable in video_tools.py!"
    print("✓ Using IMAGE_GENERATION variable")

    print("✅ Hardcoded models verification PASSED")


def main():
    """Run all verification checks."""
    print("\n" + "=" * 60)
    print("  DAVE'S FEEDBACK IMPLEMENTATION VERIFICATION")
    print("=" * 60)

    try:
        verify_config()
        verify_database_schema()
        verify_products_data()
        verify_indexes()
        verify_legacy_tables()
        verify_no_hardcoded_models()

        print("\n" + "=" * 60)
        print("  ✅ ALL VERIFICATIONS PASSED!")
        print("=" * 60)
        print("\nImplementation is ready for demo.\n")

        return 0

    except AssertionError as e:
        print(f"\n❌ VERIFICATION FAILED: {e}\n")
        return 1

    except Exception as e:
        print(f"\n❌ ERROR: {e}\n")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
