#!/usr/bin/env python3
"""Reset database with fresh product-centric campaigns.

Product-Centric Model:
    Each campaign = 1 product + 1 store location
    Example: "Blue Floral Maxi Dress - Westfield Century City"

This script:
1. Cleans up all old data from legacy tables
2. Creates sample product-centric campaigns (1 product per campaign)
3. Keeps new tables (campaign_videos, video_metrics) empty for HITL workflow
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.database.db import get_connection


# Product-centric campaign definitions
# Each campaign = 1 product + 1 store
CAMPAIGNS = [
    {
        "product_name": "blue-floral-maxi-dress",
        "store_name": "Westfield Century City",
        "city": "Los Angeles",
        "state": "California",
    },
    {
        "product_name": "elegant-black-cocktail-dress",
        "store_name": "Bloomingdale's 59th Street",
        "city": "New York",
        "state": "New York",
    },
    {
        "product_name": "black-high-waist-trousers",
        "store_name": "Water Tower Place",
        "city": "Chicago",
        "state": "Illinois",
    },
    {
        "product_name": "emerald-satin-slip-dress",
        "store_name": "The Grove",
        "city": "Los Angeles",
        "state": "California",
    },
]


def cleanup_old_data(conn):
    """Remove all old data from legacy tables."""
    cursor = conn.cursor()

    print("\n=== CLEANING UP OLD DATA ===")

    # Delete in order to respect foreign keys
    tables_to_clean = [
        ("campaign_metrics", "Legacy metrics"),
        ("campaign_ads", "Legacy video ads"),
        ("campaign_images", "Legacy seed images"),
        ("campaign_products", "Campaign-product links (deprecated)"),
        ("video_metrics", "New video metrics"),
        ("campaign_videos", "New campaign videos"),
        ("campaigns", "All campaigns"),
    ]

    for table, desc in tables_to_clean:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        if count > 0:
            cursor.execute(f"DELETE FROM {table}")
            print(f"  Deleted {count} rows from {table} ({desc})")
        else:
            print(f"  {table}: already empty")

    # Reset autoincrement counters
    cursor.execute("DELETE FROM sqlite_sequence WHERE name IN ('campaigns', 'campaign_images', 'campaign_ads', 'campaign_metrics', 'campaign_products', 'campaign_videos', 'video_metrics')")
    print("  Reset autoincrement counters")

    conn.commit()
    print("Done cleaning up old data")


def create_campaigns(conn):
    """Create new product-centric campaigns."""
    cursor = conn.cursor()

    print("\n=== CREATING PRODUCT-CENTRIC CAMPAIGNS ===")

    # Category mapping for products
    category_mapping = {
        "dress": "summer",
        "top": "essentials",
        "pants": "professional",
        "skirt": "formal",
        "outerwear": "essentials"
    }

    for campaign_def in CAMPAIGNS:
        product_name = campaign_def["product_name"]

        # Get product
        cursor.execute("SELECT * FROM products WHERE name = ?", (product_name,))
        product = cursor.fetchone()

        if not product:
            print(f"  Product not found: {product_name}")
            continue

        # Generate campaign name
        product_title = product_name.replace("-", " ").title()
        campaign_name = f"{product_title} - {campaign_def['store_name']}"

        # Get category from product
        product_category = product["category"] if product["category"] else "dress"
        category = category_mapping.get(product_category.lower(), "essentials")

        # Generate description
        description = f"Campaign for {product['style']} in {product['color']} at {campaign_def['store_name']}, {campaign_def['city']}."

        # Insert campaign
        cursor.execute('''
            INSERT INTO campaigns (name, description, product_id, store_name, city, state, category, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'active')
        ''', (
            campaign_name,
            description,
            product["id"],
            campaign_def["store_name"],
            campaign_def["city"],
            campaign_def["state"],
            category
        ))
        campaign_id = cursor.lastrowid

        print(f"\n  Created: {campaign_name}")
        print(f"    Product: {product_name} (ID: {product['id']})")
        print(f"    Store: {campaign_def['store_name']}")
        print(f"    Location: {campaign_def['city']}, {campaign_def['state']}")
        print(f"    Category: {category}")

    conn.commit()
    print("\nDone creating campaigns")


def verify_setup(conn):
    """Verify the final database state."""
    cursor = conn.cursor()

    print("\n=== VERIFICATION ===")

    # Count all tables
    tables = [
        "campaigns",
        "products",
        "campaign_videos",
        "video_metrics"
    ]

    print("\nTable record counts:")
    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        print(f"  {table}: {count}")

    # Show campaign summary
    print("\nCampaign Summary (Product-Centric):")
    cursor.execute('''
        SELECT c.id, c.name, c.store_name, c.city, c.state,
               p.name as product_name, p.category as product_category
        FROM campaigns c
        LEFT JOIN products p ON c.product_id = p.id
        ORDER BY c.id
    ''')
    for row in cursor.fetchall():
        print(f"\n  Campaign {row[0]}: {row[1]}")
        print(f"    Product: {row[5]} ({row[6]})")
        print(f"    Store: {row[2]}")
        print(f"    Location: {row[3]}, {row[4]}")


def main():
    """Run the database reset."""
    print("=" * 60)
    print("  DATABASE RESET - PRODUCT-CENTRIC CAMPAIGNS")
    print("=" * 60)

    conn = get_connection()

    try:
        cleanup_old_data(conn)
        create_campaigns(conn)
        verify_setup(conn)

        print("\n" + "=" * 60)
        print("  DATABASE RESET COMPLETE")
        print("=" * 60)
        print("\nProduct-Centric Model:")
        print("  - Each campaign = 1 product + 1 store location")
        print("  - Use create_campaign(product_id, store_name, city, state)")
        print("  - Generate videos with variations for A/B testing")
        print()
        print("Next steps:")
        print("  1. Use ADK web to create more campaigns via create_campaign()")
        print("  2. Generate videos with generate_video_from_product()")
        print("  3. Use variations for A/B testing")
        print("  4. Activate videos via Review Agent")
        print()

        return 0

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
