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

"""SQLite database setup and connection management."""

import sqlite3
from contextlib import contextmanager
from ..config import DB_PATH


def get_connection() -> sqlite3.Connection:
    """Get a database connection with row factory enabled."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def get_db_cursor():
    """Context manager for database operations."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        yield cursor
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def init_database() -> None:
    """Initialize the database schema.

    Creates tables for:
    - campaigns: Campaign metadata and location targeting
    - campaign_images: Seed images associated with campaigns
    - campaign_ads: Generated video ads
    - campaign_metrics: Daily performance metrics (mock data)
    """
    conn = get_connection()
    cursor = conn.cursor()

    # Create campaigns table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS campaigns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            category TEXT CHECK(category IN ('summer', 'formal', 'professional', 'essentials')),
            city TEXT NOT NULL,
            state TEXT NOT NULL,
            status TEXT DEFAULT 'draft' CHECK(status IN ('draft', 'active', 'paused', 'completed')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Create campaign_images table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS campaign_images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            campaign_id INTEGER NOT NULL,
            image_path TEXT NOT NULL,
            image_type TEXT DEFAULT 'seed' CHECK(image_type IN ('seed', 'reference')),
            metadata TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (campaign_id) REFERENCES campaigns(id) ON DELETE CASCADE
        )
    ''')

    # Create campaign_ads table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS campaign_ads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            campaign_id INTEGER NOT NULL,
            image_id INTEGER,
            video_path TEXT NOT NULL,
            prompt_used TEXT,
            duration_seconds INTEGER DEFAULT 5,
            status TEXT DEFAULT 'completed' CHECK(status IN ('pending', 'generating', 'completed', 'failed')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (campaign_id) REFERENCES campaigns(id) ON DELETE CASCADE,
            FOREIGN KEY (image_id) REFERENCES campaign_images(id) ON DELETE SET NULL
        )
    ''')

    # Create campaign_metrics table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS campaign_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            campaign_id INTEGER NOT NULL,
            ad_id INTEGER,
            date DATE NOT NULL,
            impressions INTEGER DEFAULT 0,
            views INTEGER DEFAULT 0,
            clicks INTEGER DEFAULT 0,
            revenue REAL DEFAULT 0.0,
            cost_per_impression REAL DEFAULT 0.0,
            engagement_rate REAL DEFAULT 0.0,
            FOREIGN KEY (campaign_id) REFERENCES campaigns(id) ON DELETE CASCADE,
            FOREIGN KEY (ad_id) REFERENCES campaign_ads(id) ON DELETE SET NULL
        )
    ''')

    # Create indexes for faster queries
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_campaigns_status ON campaigns(status)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_campaign_images_campaign ON campaign_images(campaign_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_campaign_ads_campaign ON campaign_ads(campaign_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_campaign_metrics_campaign ON campaign_metrics(campaign_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_campaign_metrics_date ON campaign_metrics(date)')

    conn.commit()
    conn.close()


def reset_database() -> None:
    """Drop all tables and reinitialize the database."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('DROP TABLE IF EXISTS campaign_metrics')
    cursor.execute('DROP TABLE IF EXISTS campaign_ads')
    cursor.execute('DROP TABLE IF EXISTS campaign_images')
    cursor.execute('DROP TABLE IF EXISTS campaigns')

    conn.commit()
    conn.close()

    init_database()
