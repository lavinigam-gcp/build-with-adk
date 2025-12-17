#!/usr/bin/env python3
# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""One-time migration script for metrics schema change.

Migrates from digital video metrics to in-store retail media metrics:
- Removes: views, clicks, cost_per_impression, engagement_rate
- Adds: dwell_time, circulation
- Keeps: impressions, revenue (for RPI calculation)
- New: revenue_per_impression computed on-the-fly

Run: python -m scripts.migrate_metrics_schema

After successful migration, this script can be deleted.
"""

import os
import random
import shutil
import sqlite3
import sys
from datetime import datetime

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from app.config import DB_PATH


def migrate_metrics_schema():
    """Migrate campaign_metrics from digital video to retail media metrics."""
    print("=" * 60)
    print("Metrics Schema Migration")
    print("Digital Video -> In-Store Retail Media")
    print("=" * 60)
    print()
    print(f"Database: {DB_PATH}")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print()

    # Step 0: Create backup
    backup_path = f"{DB_PATH}.backup_{int(datetime.now().timestamp())}"
    print(f"[Step 0] Creating backup at: {backup_path}")
    shutil.copy2(DB_PATH, backup_path)
    print("  Backup created successfully")
    print()

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Step 1: Check current schema
    print("[Step 1] Checking current schema...")
    cursor.execute("PRAGMA table_info(campaign_metrics)")
    current_columns = {col[1]: col[2] for col in cursor.fetchall()}
    print(f"  Current columns: {list(current_columns.keys())}")

    # Check if migration is needed
    if "dwell_time" in current_columns and "views" not in current_columns:
        print("  Migration already completed. Exiting.")
        conn.close()
        return

    # Step 2: Count existing records
    cursor.execute("SELECT COUNT(*) FROM campaign_metrics")
    count = cursor.fetchone()[0]
    print(f"[Step 2] Found {count} existing metric records to migrate")

    # Step 3: Create new table with correct schema
    print("[Step 3] Creating new table with retail metrics schema...")
    cursor.execute('DROP TABLE IF EXISTS campaign_metrics_new')
    cursor.execute('''
        CREATE TABLE campaign_metrics_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            campaign_id INTEGER NOT NULL,
            ad_id INTEGER,
            date DATE NOT NULL,
            impressions INTEGER DEFAULT 0,
            dwell_time REAL DEFAULT 0.0,
            circulation INTEGER DEFAULT 0,
            revenue REAL DEFAULT 0.0,
            FOREIGN KEY (campaign_id) REFERENCES campaigns(id) ON DELETE CASCADE,
            FOREIGN KEY (ad_id) REFERENCES campaign_ads(id) ON DELETE SET NULL
        )
    ''')
    print("  New table created with columns: id, campaign_id, ad_id, date, impressions, dwell_time, circulation, revenue")

    # Step 4: Migrate data with computed values
    print("[Step 4] Migrating data with new metrics...")

    # Get all existing records
    cursor.execute('''
        SELECT id, campaign_id, ad_id, date, impressions, revenue, engagement_rate
        FROM campaign_metrics
    ''')
    rows = cursor.fetchall()

    migrated = 0
    for row in rows:
        # Compute new metrics from old data
        impressions = row["impressions"] or 0
        revenue = row["revenue"] or 0
        engagement_rate = row["engagement_rate"] or 0

        # dwell_time: estimate from engagement_rate (higher engagement = longer dwell)
        # Base 2-4 seconds + engagement bonus (0-10 seconds based on engagement)
        dwell_time = round(2.0 + (engagement_rate * 0.12) + random.uniform(0, 2), 1)
        dwell_time = min(dwell_time, 15.0)  # Cap at 15 seconds

        # circulation: estimate as 1.5-3x impressions (not everyone sees ad)
        circulation_multiplier = random.uniform(1.5, 3.0)
        circulation = int(impressions * circulation_multiplier)

        cursor.execute('''
            INSERT INTO campaign_metrics_new
                (campaign_id, ad_id, date, impressions, dwell_time, circulation, revenue)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            row["campaign_id"],
            row["ad_id"],
            row["date"],
            impressions,
            dwell_time,
            circulation,
            revenue
        ))
        migrated += 1

    conn.commit()
    print(f"  Migrated {migrated} records")

    # Step 5: Verify migration
    print("[Step 5] Verifying migration...")
    cursor.execute("SELECT COUNT(*) FROM campaign_metrics_new")
    new_count = cursor.fetchone()[0]
    print(f"  Original records: {count}")
    print(f"  Migrated records: {new_count}")

    if new_count != count:
        print("  WARNING: Record count mismatch!")
        print("  Restoring from backup...")
        conn.close()
        shutil.copy2(backup_path, DB_PATH)
        return

    # Step 6: Swap tables
    print("[Step 6] Swapping tables...")
    cursor.execute("DROP TABLE campaign_metrics")
    cursor.execute("ALTER TABLE campaign_metrics_new RENAME TO campaign_metrics")
    print("  Tables swapped successfully")

    # Step 7: Recreate indexes
    print("[Step 7] Recreating indexes...")
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_campaign_metrics_campaign ON campaign_metrics(campaign_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_campaign_metrics_date ON campaign_metrics(date)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_campaign_metrics_ad ON campaign_metrics(ad_id)')
    print("  Indexes created")

    conn.commit()

    # Step 8: Verify final schema
    print("[Step 8] Verifying final schema...")
    cursor.execute("PRAGMA table_info(campaign_metrics)")
    final_columns = [col[1] for col in cursor.fetchall()]
    print(f"  Final columns: {final_columns}")

    # Check expected columns
    expected = {"id", "campaign_id", "ad_id", "date", "impressions", "dwell_time", "circulation", "revenue"}
    actual = set(final_columns)
    if expected == actual:
        print("  Schema verification: PASSED")
    else:
        print(f"  Schema verification: FAILED")
        print(f"  Expected: {expected}")
        print(f"  Actual: {actual}")

    # Step 9: Show sample data
    print("[Step 9] Sample migrated data...")
    cursor.execute('''
        SELECT campaign_id, date, impressions, dwell_time, circulation, revenue,
               ROUND(revenue * 1.0 / NULLIF(impressions, 0), 4) as rpi
        FROM campaign_metrics
        LIMIT 5
    ''')
    samples = cursor.fetchall()
    for sample in samples:
        print(f"  Campaign {sample[0]} ({sample[1]}): "
              f"impressions={sample[2]:,}, dwell={sample[3]:.1f}s, "
              f"circulation={sample[4]:,}, RPI=${sample[6] or 0:.4f}")

    conn.close()

    print()
    print("=" * 60)
    print("Migration Complete!")
    print("=" * 60)
    print()
    print("Changes made:")
    print("  - Removed: views, clicks, cost_per_impression, engagement_rate")
    print("  - Added: dwell_time (seconds), circulation (foot traffic)")
    print("  - Kept: impressions, revenue")
    print("  - RPI (revenue_per_impression) computed on-the-fly")
    print()
    print(f"Backup saved at: {backup_path}")
    print()
    print("Next steps:")
    print("  1. Update code files (db.py, mock_data.py, metrics_tools.py, etc.)")
    print("  2. Test with: adk web .")
    print("  3. Verify metrics queries work correctly")


def main():
    """Entry point for the migration script."""
    print()
    print("This script will migrate campaign_metrics from digital video metrics")
    print("to in-store retail media metrics.")
    print()
    print("Changes:")
    print("  - Remove: views, clicks, cost_per_impression, engagement_rate")
    print("  - Add: dwell_time (seconds), circulation (foot traffic)")
    print("  - Keep: impressions, revenue")
    print("  - New: revenue_per_impression (computed as revenue/impressions)")
    print()

    # Run the migration
    migrate_metrics_schema()


if __name__ == "__main__":
    main()
