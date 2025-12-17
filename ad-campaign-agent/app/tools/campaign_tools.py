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

"""Campaign management tools for CRUD operations."""

import json
from typing import Optional
from ..database.db import get_db_cursor


def create_campaign(
    name: str,
    description: str,
    category: str,
    city: str,
    state: str
) -> dict:
    """Create a new ad campaign with US location targeting.

    Args:
        name: Campaign name (e.g., "Summer Blooms 2025")
        description: Campaign description
        category: Category - one of: summer, formal, professional, essentials
        city: US city for targeting (e.g., "Los Angeles")
        state: US state abbreviation (e.g., "CA")

    Returns:
        Dictionary with campaign details or error message
    """
    # Validate category
    valid_categories = ["summer", "formal", "professional", "essentials"]
    if category not in valid_categories:
        return {
            "status": "error",
            "message": f"Invalid category. Must be one of: {', '.join(valid_categories)}"
        }

    with get_db_cursor() as cursor:
        cursor.execute('''
            INSERT INTO campaigns (name, description, category, city, state, status)
            VALUES (?, ?, ?, ?, ?, 'draft')
        ''', (name, description, category, city, state))

        campaign_id = cursor.lastrowid

        cursor.execute('SELECT * FROM campaigns WHERE id = ?', (campaign_id,))
        row = cursor.fetchone()

        return {
            "status": "success",
            "message": f"Campaign '{name}' created successfully",
            "campaign": {
                "id": row["id"],
                "name": row["name"],
                "description": row["description"],
                "category": row["category"],
                "city": row["city"],
                "state": row["state"],
                "status": row["status"],
                "created_at": row["created_at"]
            }
        }


def list_campaigns(status: Optional[str] = None) -> dict:
    """List all campaigns, optionally filtered by status.

    Args:
        status: Optional filter - one of: draft, active, paused, completed

    Returns:
        Dictionary with list of campaigns and counts
    """
    with get_db_cursor() as cursor:
        if status:
            cursor.execute('''
                SELECT c.*,
                       COUNT(DISTINCT ci.id) as image_count,
                       COUNT(DISTINCT ca.id) as ad_count
                FROM campaigns c
                LEFT JOIN campaign_images ci ON c.id = ci.campaign_id
                LEFT JOIN campaign_ads ca ON c.id = ca.campaign_id
                WHERE c.status = ?
                GROUP BY c.id
                ORDER BY c.created_at DESC
            ''', (status,))
        else:
            cursor.execute('''
                SELECT c.*,
                       COUNT(DISTINCT ci.id) as image_count,
                       COUNT(DISTINCT ca.id) as ad_count
                FROM campaigns c
                LEFT JOIN campaign_images ci ON c.id = ci.campaign_id
                LEFT JOIN campaign_ads ca ON c.id = ca.campaign_id
                GROUP BY c.id
                ORDER BY c.created_at DESC
            ''')

        rows = cursor.fetchall()

        campaigns = []
        for row in rows:
            campaigns.append({
                "id": row["id"],
                "name": row["name"],
                "description": row["description"],
                "category": row["category"],
                "location": f"{row['city']}, {row['state']}",
                "status": row["status"],
                "image_count": row["image_count"],
                "ad_count": row["ad_count"],
                "created_at": row["created_at"]
            })

        return {
            "status": "success",
            "total_count": len(campaigns),
            "filter": status if status else "all",
            "campaigns": campaigns
        }


def get_campaign(campaign_id: int) -> dict:
    """Get detailed campaign info including images, ads, and metrics summary.

    Args:
        campaign_id: The ID of the campaign to retrieve

    Returns:
        Dictionary with full campaign details including related data
    """
    with get_db_cursor() as cursor:
        # Get campaign
        cursor.execute('SELECT * FROM campaigns WHERE id = ?', (campaign_id,))
        campaign = cursor.fetchone()

        if not campaign:
            return {
                "status": "error",
                "message": f"Campaign with ID {campaign_id} not found"
            }

        # Get images
        cursor.execute('''
            SELECT id, image_path, image_type, metadata, created_at
            FROM campaign_images
            WHERE campaign_id = ?
        ''', (campaign_id,))
        images = []
        for row in cursor.fetchall():
            images.append({
                "id": row["id"],
                "image_path": row["image_path"],
                "image_type": row["image_type"],
                "metadata": json.loads(row["metadata"]) if row["metadata"] else None,
                "created_at": row["created_at"]
            })

        # Get ads
        cursor.execute('''
            SELECT id, video_path, prompt_used, duration_seconds, status, created_at
            FROM campaign_ads
            WHERE campaign_id = ?
        ''', (campaign_id,))
        ads = []
        for row in cursor.fetchall():
            ads.append({
                "id": row["id"],
                "video_path": row["video_path"],
                "prompt_used": row["prompt_used"],
                "duration_seconds": row["duration_seconds"],
                "status": row["status"],
                "created_at": row["created_at"]
            })

        # Get metrics summary (last 30 days) - In-store retail media metrics
        cursor.execute('''
            SELECT
                SUM(impressions) as total_impressions,
                AVG(dwell_time) as avg_dwell_time,
                SUM(circulation) as total_circulation,
                SUM(revenue) as total_revenue
            FROM campaign_metrics
            WHERE campaign_id = ?
            AND date >= date('now', '-30 days')
        ''', (campaign_id,))
        metrics_row = cursor.fetchone()

        metrics_summary = None
        if metrics_row and metrics_row["total_impressions"]:
            total_impressions = int(metrics_row["total_impressions"])
            total_revenue = round(metrics_row["total_revenue"], 2)
            # Compute RPI (revenue per impression) - the primary KPI
            rpi = round(total_revenue / total_impressions, 4) if total_impressions > 0 else 0

            metrics_summary = {
                "period": "last_30_days",
                "total_impressions": total_impressions,
                "average_dwell_time": round(metrics_row["avg_dwell_time"], 1),
                "total_circulation": int(metrics_row["total_circulation"]),
                "total_revenue": total_revenue,
                "revenue_per_impression": rpi,
                "revenue_per_1000_impressions": round(rpi * 1000, 2)
            }

        return {
            "status": "success",
            "campaign": {
                "id": campaign["id"],
                "name": campaign["name"],
                "description": campaign["description"],
                "category": campaign["category"],
                "city": campaign["city"],
                "state": campaign["state"],
                "status": campaign["status"],
                "created_at": campaign["created_at"],
                "updated_at": campaign["updated_at"]
            },
            "images": images,
            "ads": ads,
            "metrics_summary": metrics_summary
        }


def update_campaign(
    campaign_id: int,
    name: Optional[str] = None,
    description: Optional[str] = None,
    status: Optional[str] = None
) -> dict:
    """Update campaign properties.

    Args:
        campaign_id: The ID of the campaign to update
        name: New campaign name (optional)
        description: New description (optional)
        status: New status - one of: draft, active, paused, completed (optional)

    Returns:
        Dictionary with updated campaign details or error message
    """
    # Validate status if provided
    if status:
        valid_statuses = ["draft", "active", "paused", "completed"]
        if status not in valid_statuses:
            return {
                "status": "error",
                "message": f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
            }

    with get_db_cursor() as cursor:
        # Check if campaign exists
        cursor.execute('SELECT * FROM campaigns WHERE id = ?', (campaign_id,))
        if not cursor.fetchone():
            return {
                "status": "error",
                "message": f"Campaign with ID {campaign_id} not found"
            }

        # Build update query dynamically
        updates = []
        params = []

        if name:
            updates.append("name = ?")
            params.append(name)
        if description:
            updates.append("description = ?")
            params.append(description)
        if status:
            updates.append("status = ?")
            params.append(status)

        if not updates:
            return {
                "status": "error",
                "message": "No fields to update provided"
            }

        updates.append("updated_at = CURRENT_TIMESTAMP")
        params.append(campaign_id)

        query = f"UPDATE campaigns SET {', '.join(updates)} WHERE id = ?"
        cursor.execute(query, params)

        # Get updated campaign
        cursor.execute('SELECT * FROM campaigns WHERE id = ?', (campaign_id,))
        row = cursor.fetchone()

        return {
            "status": "success",
            "message": "Campaign updated successfully",
            "campaign": {
                "id": row["id"],
                "name": row["name"],
                "description": row["description"],
                "category": row["category"],
                "city": row["city"],
                "state": row["state"],
                "status": row["status"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"]
            }
        }
