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


# =============================================================================
# Video Review Tools (Table View with Preview Links)
# =============================================================================

def get_video_review_table(
    campaign_id: int = None,
    status: str = None,
    limit: int = 20
) -> dict:
    """Get a formatted review table with video preview links.

    Returns a table view optimized for human review with:
    - Video ID (for activation commands like "activate 1, 4, 7")
    - Status indicator (pending, live, paused, archived)
    - Product and campaign/store info
    - View link (public GCS URL - click to preview in browser)
    - Thumbnail link (if available)
    - Variation name

    Args:
        campaign_id: Optional filter by campaign
        status: Optional filter (generated, activated, paused, archived)
        limit: Maximum videos to return (default 20)

    Returns:
        Dict with:
        - table: Markdown-formatted table string for display
        - videos: List of video details with URLs
        - summary: Status counts and action guidance
    """
    from .. import storage

    with get_db_cursor() as cursor:
        # Build query with filters - include full product and campaign details
        query = '''
            SELECT cv.*,
                   c.name as campaign_name, c.store_name, c.city, c.state, c.category as campaign_category,
                   p.name as product_name, p.category as product_category,
                   p.color as product_color, p.style as product_style,
                   p.fabric as product_fabric, p.image_filename as product_image
            FROM campaign_videos cv
            JOIN campaigns c ON cv.campaign_id = c.id
            LEFT JOIN products p ON cv.product_id = p.id
        '''
        conditions = []
        params = []

        if campaign_id:
            conditions.append("cv.campaign_id = ?")
            params.append(campaign_id)
        if status:
            conditions.append("cv.status = ?")
            params.append(status)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY cv.created_at DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)
        rows = cursor.fetchall()

        # Build table and video list
        videos = []
        status_counts = {"generated": 0, "activated": 0, "paused": 0, "archived": 0}

        for row in rows:
            # Get public URLs for viewing
            video_url = storage.get_video_public_url(row["video_filename"]) if row["video_filename"] else None
            # Product image URL (not thumbnail)
            product_image_url = storage.get_public_url(f"product-images/{row['product_image']}") if row["product_image"] else None

            # Map status to display text
            status_display = {
                "generated": "pending",
                "activated": "live",
                "paused": "paused",
                "archived": "archived"
            }.get(row["status"], row["status"])

            # Count by status
            if row["status"] in status_counts:
                status_counts[row["status"]] += 1

            # Parse variation params if available
            variation_params = None
            if row["variation_params"]:
                try:
                    variation_params = json.loads(row["variation_params"])
                except json.JSONDecodeError:
                    pass

            videos.append({
                "id": row["id"],
                "status": row["status"],
                "status_display": status_display,
                # Product info
                "product_name": row["product_name"],
                "product_category": row["product_category"],
                "product_color": row["product_color"],
                "product_style": row["product_style"],
                "product_fabric": row["product_fabric"],
                "product_image_url": product_image_url,
                # Campaign/location info
                "campaign_name": row["campaign_name"],
                "store_name": row["store_name"],
                "city": row["city"],
                "state": row["state"],
                # Video generation info
                "variation_name": row["variation_name"],
                "variation_params": variation_params,
                "video_url": video_url,
                "duration_seconds": row["duration_seconds"],
                "pipeline_type": row["pipeline_type"],
                "generation_time_seconds": row["generation_time_seconds"],
                "created_at": row["created_at"]
            })

        # Build card-based format with bullet points for proper ADK web rendering
        table_lines = []

        for v in videos:
            vid_id = v['id']
            status_icon = "🟡" if v['status'] == 'generated' else "🟢" if v['status'] == 'activated' else "⏸️" if v['status'] == 'paused' else "📦"
            status_text = v['status_display'].upper()

            # Video header
            table_lines.append(f"## {status_icon} Video #{vid_id} — {status_text}")
            table_lines.append("")

            # Product section
            table_lines.append("**📦 Product Details**")
            table_lines.append(f"- Name: {v['product_name'] or 'N/A'}")
            table_lines.append(f"- Category: {v['product_category'] or 'N/A'} | Color: {v['product_color'] or 'N/A'}")
            table_lines.append(f"- Style: {v['product_style'] or 'N/A'} | Fabric: {v['product_fabric'] or 'N/A'}")
            if v["product_image_url"]:
                table_lines.append(f"- [🖼️ View Product Image]({v['product_image_url']})")
            table_lines.append("")

            # Location section
            table_lines.append("**📍 Location**")
            table_lines.append(f"- Store: {v['store_name'] or 'N/A'}")
            table_lines.append(f"- Location: {v['city'] or 'N/A'}, {v['state'] or 'N/A'}")
            table_lines.append("")

            # Video generation section
            table_lines.append("**🎬 Video Info**")
            table_lines.append(f"- Variation: {v['variation_name'] or 'default'}")
            if v['variation_params']:
                vp = v['variation_params']
                table_lines.append(f"- Model: {vp.get('model_ethnicity', 'N/A')} | Setting: {vp.get('setting', 'N/A')} | Mood: {vp.get('mood', 'N/A')}")
            table_lines.append(f"- Duration: {v['duration_seconds']}s | Pipeline: {v['pipeline_type'] or 'N/A'}")
            if v['generation_time_seconds']:
                table_lines.append(f"- Generation time: {v['generation_time_seconds']}s")
            table_lines.append(f"- Created: {v['created_at'] or 'N/A'}")
            table_lines.append("")

            # Watch link - prominent
            if v["video_url"]:
                table_lines.append(f"**👉 [▶️ WATCH VIDEO]({v['video_url']})**")
                table_lines.append("")

            table_lines.append("---")
            table_lines.append("")

        table = "\n".join(table_lines)

        # Build summary
        pending = status_counts["generated"]
        live = status_counts["activated"]
        total = len(videos)

        summary = f"**Summary:** {pending} pending activation, {live} live, {total} total shown"
        if pending > 0:
            summary += f"\n\nTo activate videos, say: \"activate {', '.join(str(v['id']) for v in videos[:3] if v['status'] == 'generated')}\" (or any IDs)"

        return {
            "status": "success",
            "table": table,
            "videos": videos,
            "summary": summary,
            "counts": status_counts,
            "filter": {"campaign_id": campaign_id, "status": status},
            "message": "Click View links to preview videos in browser. Use activate_batch([id1, id2, ...]) to activate."
        }


def get_video_details(video_id: int) -> dict:
    """Get detailed preview information for a single video.

    Returns full information for reviewing a specific video including:
    - Video public URL (viewable link)
    - Thumbnail public URL
    - Full variation parameters (model, setting, mood, etc.)
    - Scene and video prompts used
    - Generation metadata (duration, pipeline type, generation time)
    - Product details (name, category, color, style)
    - Campaign info (store, location)
    - Metrics summary (if activated)

    Args:
        video_id: The video ID to get details for

    Returns:
        Dict with comprehensive video information
    """
    from .. import storage

    with get_db_cursor() as cursor:
        cursor.execute('''
            SELECT cv.*,
                   c.name as campaign_name, c.store_name, c.city, c.state,
                   p.name as product_name, p.category as product_category,
                   p.color as product_color, p.style as product_style,
                   p.fabric as product_fabric
            FROM campaign_videos cv
            JOIN campaigns c ON cv.campaign_id = c.id
            LEFT JOIN products p ON cv.product_id = p.id
            WHERE cv.id = ?
        ''', (video_id,))

        row = cursor.fetchone()
        if not row:
            return {
                "status": "error",
                "message": f"Video {video_id} not found"
            }

        # Get public URLs
        video_url = storage.get_video_public_url(row["video_filename"]) if row["video_filename"] else None
        thumbnail_url = None
        if row["thumbnail_path"]:
            # Handle both full paths and filenames
            thumb_filename = row["thumbnail_path"].split("/")[-1] if "/" in row["thumbnail_path"] else row["thumbnail_path"]
            thumbnail_url = storage.get_thumbnail_public_url(thumb_filename)

        # Parse variation parameters
        variation_params = None
        if row["variation_params"]:
            try:
                variation_params = json.loads(row["variation_params"])
            except json.JSONDecodeError:
                pass

        # Get metrics summary if activated
        metrics_summary = None
        if row["status"] == "activated":
            cursor.execute('''
                SELECT
                    COUNT(*) as days,
                    SUM(impressions) as total_impressions,
                    AVG(dwell_time_seconds) as avg_dwell,
                    SUM(revenue) as total_revenue
                FROM video_metrics
                WHERE video_id = ?
            ''', (video_id,))
            m = cursor.fetchone()
            if m and m["days"] > 0:
                metrics_summary = {
                    "days_tracked": m["days"],
                    "total_impressions": int(m["total_impressions"]),
                    "avg_dwell_seconds": round(m["avg_dwell"], 1),
                    "total_revenue": round(m["total_revenue"], 2),
                    "rpi": round(m["total_revenue"] / m["total_impressions"], 4) if m["total_impressions"] > 0 else 0
                }

        return {
            "status": "success",
            "video": {
                "id": row["id"],
                "video_filename": row["video_filename"],
                "video_url": video_url,
                "thumbnail_url": thumbnail_url,
                "video_status": row["status"],
                "duration_seconds": row["duration_seconds"],
                "aspect_ratio": row["aspect_ratio"],
                "pipeline_type": row["pipeline_type"],
                "generation_time_seconds": row["generation_time_seconds"],
                "created_at": row["created_at"],
                "activated_at": row["activated_at"],
                "activated_by": row["activated_by"]
            },
            "variation": {
                "name": row["variation_name"],
                "params": variation_params
            },
            "prompts": {
                "scene_prompt": row["scene_prompt"],
                "video_prompt": row["video_prompt"]
            },
            "product": {
                "id": row["product_id"],
                "name": row["product_name"],
                "category": row["product_category"],
                "color": row["product_color"],
                "style": row["product_style"],
                "fabric": row["product_fabric"]
            },
            "campaign": {
                "id": row["campaign_id"],
                "name": row["campaign_name"],
                "store": row["store_name"],
                "location": f"{row['city']}, {row['state']}"
            },
            "metrics": metrics_summary,
            "actions": {
                "view": f"Click video_url to preview: {video_url}",
                "activate": f"activate_video({video_id})" if row["status"] == "generated" else None,
                "pause": f"pause_video({video_id})" if row["status"] == "activated" else None,
                "archive": f"archive_video({video_id})" if row["status"] != "archived" else None
            }
        }
