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

"""HITL (Human-in-the-Loop) Review and Activation Tools.

This module implements the video activation workflow where:
1. Videos are generated with status='generated'
2. Users review pending videos (thumbnails visible)
3. Selected videos are activated to go live
4. Mock metrics are only generated after activation

Video Lifecycle:
    generated → (HITL Review) → activated → (metrics start)
        ↓                           ↓
      archived                    paused
"""

import json
from datetime import datetime, date, timedelta
from typing import List, Optional
import random

from ..database.db import get_db_cursor


def list_pending_videos(
    campaign_id: int = None,
    limit: int = 10
) -> dict:
    """List videos awaiting activation (status='generated').

    Shows videos that have been generated but not yet pushed live.
    Includes thumbnail paths for visual review.

    Args:
        campaign_id: Optional campaign filter
        limit: Maximum number of videos to return

    Returns:
        Dictionary with list of pending videos
    """
    with get_db_cursor() as cursor:
        if campaign_id:
            cursor.execute('''
                SELECT cv.*, c.name as campaign_name, p.name as product_name
                FROM campaign_videos cv
                JOIN campaigns c ON cv.campaign_id = c.id
                LEFT JOIN products p ON cv.product_id = p.id
                WHERE cv.status = 'generated' AND cv.campaign_id = ?
                ORDER BY cv.created_at DESC
                LIMIT ?
            ''', (campaign_id, limit))
        else:
            cursor.execute('''
                SELECT cv.*, c.name as campaign_name, p.name as product_name
                FROM campaign_videos cv
                JOIN campaigns c ON cv.campaign_id = c.id
                LEFT JOIN products p ON cv.product_id = p.id
                WHERE cv.status = 'generated'
                ORDER BY cv.created_at DESC
                LIMIT ?
            ''', (limit,))

        rows = cursor.fetchall()

        videos = []
        for row in rows:
            variation_params = None
            if row["variation_params"]:
                try:
                    variation_params = json.loads(row["variation_params"])
                except json.JSONDecodeError:
                    pass

            videos.append({
                "id": row["id"],
                "campaign_id": row["campaign_id"],
                "campaign_name": row["campaign_name"],
                "product_id": row["product_id"],
                "product_name": row["product_name"],
                "video_filename": row["video_filename"],
                "thumbnail_path": row["thumbnail_path"],
                "variation_name": row["variation_name"],
                "variation_params": variation_params,
                "duration_seconds": row["duration_seconds"],
                "created_at": row["created_at"],
                "generation_time_seconds": row["generation_time_seconds"]
            })

        return {
            "status": "success",
            "pending_count": len(videos),
            "videos": videos,
            "message": f"Found {len(videos)} videos awaiting activation" + (
                f" for campaign {campaign_id}" if campaign_id else ""
            )
        }


def activate_video(
    video_id: int,
    activated_by: str = "user"
) -> dict:
    """Activate a video to push it live.

    This:
    1. Changes status from 'generated' to 'activated'
    2. Records activation timestamp and user
    3. Generates mock metrics starting from today

    Args:
        video_id: The video ID to activate
        activated_by: Who activated (for audit trail)

    Returns:
        Dictionary with activation result and generated metrics count
    """
    with get_db_cursor() as cursor:
        # Check if video exists and is in 'generated' status
        cursor.execute('''
            SELECT cv.*, c.name as campaign_name, p.name as product_name
            FROM campaign_videos cv
            JOIN campaigns c ON cv.campaign_id = c.id
            LEFT JOIN products p ON cv.product_id = p.id
            WHERE cv.id = ?
        ''', (video_id,))

        video = cursor.fetchone()
        if not video:
            return {
                "status": "error",
                "message": f"Video {video_id} not found"
            }

        if video["status"] == "activated":
            return {
                "status": "error",
                "message": f"Video {video_id} is already activated"
            }

        if video["status"] not in ["generated", "paused"]:
            return {
                "status": "error",
                "message": f"Video {video_id} cannot be activated (status: {video['status']})"
            }

        # Update status to activated
        now = datetime.now().isoformat()
        cursor.execute('''
            UPDATE campaign_videos
            SET status = 'activated', activated_at = ?, activated_by = ?
            WHERE id = ?
        ''', (now, activated_by, video_id))

        # Generate mock metrics for this video
        # Start from today, generate 30 days of data
        metrics_generated = _generate_mock_video_metrics(
            cursor=cursor,
            video_id=video_id,
            start_date=date.today(),
            days=30
        )

        return {
            "status": "success",
            "message": f"Video activated successfully and is now live",
            "video": {
                "id": video_id,
                "video_filename": video["video_filename"],
                "campaign_name": video["campaign_name"],
                "product_name": video["product_name"],
                "variation_name": video["variation_name"],
                "activated_at": now,
                "activated_by": activated_by,
                "metrics_generated": metrics_generated
            }
        }


def activate_batch(
    video_ids: List[int],
    activated_by: str = "user"
) -> dict:
    """Activate multiple videos at once.

    Args:
        video_ids: List of video IDs to activate
        activated_by: Who activated (for audit trail)

    Returns:
        Dictionary with batch activation results
    """
    results = []
    success_count = 0
    error_count = 0

    for video_id in video_ids:
        result = activate_video(video_id, activated_by)
        results.append({
            "video_id": video_id,
            "status": result["status"],
            "message": result.get("message", "")
        })

        if result["status"] == "success":
            success_count += 1
        else:
            error_count += 1

    return {
        "status": "success" if error_count == 0 else "partial",
        "message": f"Activated {success_count} videos" + (
            f", {error_count} failed" if error_count > 0 else ""
        ),
        "success_count": success_count,
        "error_count": error_count,
        "results": results
    }


def pause_video(video_id: int) -> dict:
    """Pause an activated video.

    Stops new metrics from being generated but preserves existing data.

    Args:
        video_id: The video ID to pause

    Returns:
        Dictionary with pause result
    """
    with get_db_cursor() as cursor:
        cursor.execute('''
            SELECT cv.*, c.name as campaign_name
            FROM campaign_videos cv
            JOIN campaigns c ON cv.campaign_id = c.id
            WHERE cv.id = ?
        ''', (video_id,))

        video = cursor.fetchone()
        if not video:
            return {
                "status": "error",
                "message": f"Video {video_id} not found"
            }

        if video["status"] != "activated":
            return {
                "status": "error",
                "message": f"Video {video_id} is not activated (status: {video['status']})"
            }

        cursor.execute('''
            UPDATE campaign_videos
            SET status = 'paused'
            WHERE id = ?
        ''', (video_id,))

        return {
            "status": "success",
            "message": f"Video paused successfully",
            "video": {
                "id": video_id,
                "video_filename": video["video_filename"],
                "campaign_name": video["campaign_name"],
                "new_status": "paused"
            }
        }


def archive_video(
    video_id: int,
    reason: str = None
) -> dict:
    """Archive a video (reject/remove from consideration).

    Archived videos are not shown in pending lists and cannot be activated.

    Args:
        video_id: The video ID to archive
        reason: Optional reason for archiving

    Returns:
        Dictionary with archive result
    """
    with get_db_cursor() as cursor:
        cursor.execute('''
            SELECT cv.*, c.name as campaign_name
            FROM campaign_videos cv
            JOIN campaigns c ON cv.campaign_id = c.id
            WHERE cv.id = ?
        ''', (video_id,))

        video = cursor.fetchone()
        if not video:
            return {
                "status": "error",
                "message": f"Video {video_id} not found"
            }

        if video["status"] == "archived":
            return {
                "status": "error",
                "message": f"Video {video_id} is already archived"
            }

        cursor.execute('''
            UPDATE campaign_videos
            SET status = 'archived'
            WHERE id = ?
        ''', (video_id,))

        return {
            "status": "success",
            "message": f"Video archived" + (f": {reason}" if reason else ""),
            "video": {
                "id": video_id,
                "video_filename": video["video_filename"],
                "campaign_name": video["campaign_name"],
                "previous_status": video["status"],
                "new_status": "archived",
                "reason": reason
            }
        }


def get_video_status(video_id: int) -> dict:
    """Get the current status and details of a video.

    Args:
        video_id: The video ID to check

    Returns:
        Dictionary with video status and details
    """
    with get_db_cursor() as cursor:
        cursor.execute('''
            SELECT cv.*, c.name as campaign_name, p.name as product_name
            FROM campaign_videos cv
            JOIN campaigns c ON cv.campaign_id = c.id
            LEFT JOIN products p ON cv.product_id = p.id
            WHERE cv.id = ?
        ''', (video_id,))

        video = cursor.fetchone()
        if not video:
            return {
                "status": "error",
                "message": f"Video {video_id} not found"
            }

        # Get metrics count if activated
        metrics_count = 0
        if video["status"] == "activated":
            cursor.execute('''
                SELECT COUNT(*) as count FROM video_metrics WHERE video_id = ?
            ''', (video_id,))
            metrics_count = cursor.fetchone()["count"]

        variation_params = None
        if video["variation_params"]:
            try:
                variation_params = json.loads(video["variation_params"])
            except json.JSONDecodeError:
                pass

        return {
            "status": "success",
            "video": {
                "id": video_id,
                "video_filename": video["video_filename"],
                "campaign_id": video["campaign_id"],
                "campaign_name": video["campaign_name"],
                "product_id": video["product_id"],
                "product_name": video["product_name"],
                "variation_name": video["variation_name"],
                "variation_params": variation_params,
                "thumbnail_path": video["thumbnail_path"],
                "pipeline_type": video["pipeline_type"],
                "duration_seconds": video["duration_seconds"],
                "video_status": video["status"],
                "activated_at": video["activated_at"],
                "activated_by": video["activated_by"],
                "created_at": video["created_at"],
                "metrics_count": metrics_count
            }
        }


def get_activation_summary(campaign_id: int = None) -> dict:
    """Get a summary of video statuses across campaigns.

    Args:
        campaign_id: Optional campaign filter

    Returns:
        Dictionary with status counts
    """
    with get_db_cursor() as cursor:
        if campaign_id:
            cursor.execute('''
                SELECT status, COUNT(*) as count
                FROM campaign_videos
                WHERE campaign_id = ?
                GROUP BY status
            ''', (campaign_id,))
        else:
            cursor.execute('''
                SELECT status, COUNT(*) as count
                FROM campaign_videos
                GROUP BY status
            ''')

        rows = cursor.fetchall()

        status_counts = {
            "generating": 0,
            "generated": 0,
            "activated": 0,
            "paused": 0,
            "archived": 0
        }

        for row in rows:
            status_counts[row["status"]] = row["count"]

        total = sum(status_counts.values())

        return {
            "status": "success",
            "campaign_id": campaign_id,
            "total_videos": total,
            "status_counts": status_counts,
            "pending_review": status_counts["generated"],
            "live": status_counts["activated"]
        }


# =============================================================================
# Mock Metrics Generation (only called on activation)
# =============================================================================

def _generate_mock_video_metrics(
    cursor,
    video_id: int,
    start_date: date,
    days: int = 30
) -> int:
    """Generate mock metrics for an activated video.

    Creates realistic in-store retail media metrics:
    - Impressions: 800-2000 per day (with weekly patterns)
    - Dwell time: 3-8 seconds average
    - Circulation: 1500-4000 foot traffic
    - Revenue: Based on impressions and RPI

    Args:
        cursor: Database cursor
        video_id: The video ID to generate metrics for
        start_date: Start date for metrics
        days: Number of days of metrics to generate

    Returns:
        Number of metric records created
    """
    metrics_created = 0

    # Base performance (varies by video for diversity)
    base_impressions = random.randint(800, 1500)
    base_dwell = random.uniform(4.0, 6.5)
    base_rpi = random.uniform(0.08, 0.15)  # Revenue per impression

    for day_offset in range(days):
        metric_date = start_date + timedelta(days=day_offset)

        # Day of week multiplier (weekends higher)
        dow = metric_date.weekday()
        if dow >= 5:  # Weekend
            dow_multiplier = random.uniform(1.3, 1.6)
        elif dow == 0 or dow == 4:  # Monday, Friday
            dow_multiplier = random.uniform(1.0, 1.2)
        else:  # Tue-Thu
            dow_multiplier = random.uniform(0.85, 1.05)

        # Add some random variation
        daily_variation = random.uniform(0.85, 1.15)

        # Calculate metrics
        impressions = int(base_impressions * dow_multiplier * daily_variation)
        dwell_time = round(base_dwell * random.uniform(0.9, 1.1), 2)
        circulation = int(impressions * random.uniform(1.8, 2.5))  # More foot traffic than impressions
        revenue = round(impressions * base_rpi * random.uniform(0.9, 1.1), 2)

        cursor.execute('''
            INSERT OR IGNORE INTO video_metrics
            (video_id, metric_date, impressions, dwell_time_seconds, circulation, revenue)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (video_id, metric_date.isoformat(), impressions, dwell_time, circulation, revenue))

        metrics_created += 1

    return metrics_created


def generate_additional_metrics(
    video_id: int,
    days: int = 7
) -> dict:
    """Generate additional metrics for an already-activated video.

    Use this to extend the metrics period for a live video.

    Args:
        video_id: The video ID
        days: Number of additional days to generate

    Returns:
        Dictionary with generation result
    """
    with get_db_cursor() as cursor:
        # Check video exists and is activated
        cursor.execute('''
            SELECT status FROM campaign_videos WHERE id = ?
        ''', (video_id,))

        video = cursor.fetchone()
        if not video:
            return {
                "status": "error",
                "message": f"Video {video_id} not found"
            }

        if video["status"] != "activated":
            return {
                "status": "error",
                "message": f"Video {video_id} is not activated (metrics only for live videos)"
            }

        # Get the last metric date
        cursor.execute('''
            SELECT MAX(metric_date) as last_date FROM video_metrics WHERE video_id = ?
        ''', (video_id,))

        row = cursor.fetchone()
        if row and row["last_date"]:
            last_date = date.fromisoformat(row["last_date"])
            start_date = last_date + timedelta(days=1)
        else:
            start_date = date.today()

        # Generate new metrics
        metrics_created = _generate_mock_video_metrics(
            cursor=cursor,
            video_id=video_id,
            start_date=start_date,
            days=days
        )

        return {
            "status": "success",
            "message": f"Generated {metrics_created} additional metric days",
            "video_id": video_id,
            "start_date": start_date.isoformat(),
            "days_generated": metrics_created
        }
