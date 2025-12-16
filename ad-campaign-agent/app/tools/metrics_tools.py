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

"""Metrics and analytics tools for campaign performance."""

import json
from typing import List, Optional

from ..database.db import get_db_cursor


def get_campaign_metrics(campaign_id: int, days: int = 30) -> dict:
    """Get performance metrics for a campaign.

    Returns daily and aggregated metrics including impressions, views,
    clicks, revenue, and engagement rates.

    Args:
        campaign_id: The ID of the campaign
        days: Number of days to retrieve (default: 30)

    Returns:
        Dictionary with daily metrics and aggregated totals
    """
    with get_db_cursor() as cursor:
        # Verify campaign exists
        cursor.execute('SELECT id, name, status FROM campaigns WHERE id = ?', (campaign_id,))
        campaign = cursor.fetchone()
        if not campaign:
            return {
                "status": "error",
                "message": f"Campaign with ID {campaign_id} not found"
            }

        # Get daily metrics
        cursor.execute('''
            SELECT
                date,
                SUM(impressions) as impressions,
                SUM(views) as views,
                SUM(clicks) as clicks,
                SUM(revenue) as revenue,
                AVG(cost_per_impression) as cost_per_impression,
                AVG(engagement_rate) as engagement_rate
            FROM campaign_metrics
            WHERE campaign_id = ?
            AND date >= date('now', ?)
            GROUP BY date
            ORDER BY date DESC
        ''', (campaign_id, f'-{days} days'))

        daily_metrics = []
        for row in cursor.fetchall():
            daily_metrics.append({
                "date": row["date"],
                "impressions": int(row["impressions"]),
                "views": int(row["views"]),
                "clicks": int(row["clicks"]),
                "revenue": round(row["revenue"], 2),
                "cost_per_impression": round(row["cost_per_impression"], 4),
                "engagement_rate": round(row["engagement_rate"], 2)
            })

        # Get aggregated totals
        cursor.execute('''
            SELECT
                SUM(impressions) as total_impressions,
                SUM(views) as total_views,
                SUM(clicks) as total_clicks,
                SUM(revenue) as total_revenue,
                AVG(cost_per_impression) as avg_cpi,
                AVG(engagement_rate) as avg_engagement
            FROM campaign_metrics
            WHERE campaign_id = ?
            AND date >= date('now', ?)
        ''', (campaign_id, f'-{days} days'))

        totals = cursor.fetchone()

        summary = None
        if totals and totals["total_impressions"]:
            summary = {
                "total_impressions": int(totals["total_impressions"]),
                "total_views": int(totals["total_views"]),
                "total_clicks": int(totals["total_clicks"]),
                "total_revenue": round(totals["total_revenue"], 2),
                "average_cost_per_impression": round(totals["avg_cpi"], 4),
                "average_engagement_rate": round(totals["avg_engagement"], 2),
                "revenue_per_1000_impressions": round(
                    (totals["total_revenue"] / totals["total_impressions"]) * 1000, 2
                ) if totals["total_impressions"] > 0 else 0
            }

        return {
            "status": "success",
            "campaign": {
                "id": campaign["id"],
                "name": campaign["name"],
                "status": campaign["status"]
            },
            "period": f"last_{days}_days",
            "summary": summary,
            "daily_metrics": daily_metrics
        }


def get_top_performing_ads(metric: str = "revenue", limit: int = 5) -> dict:
    """Get top performing ads across all campaigns.

    Identifies the best ads and their key characteristics for insights.

    Args:
        metric: Metric to rank by - one of: revenue, impressions, engagement_rate, clicks
        limit: Number of top ads to return

    Returns:
        Dictionary with top ads and their characteristics
    """
    valid_metrics = ["revenue", "impressions", "engagement_rate", "clicks"]
    if metric not in valid_metrics:
        return {
            "status": "error",
            "message": f"Invalid metric. Must be one of: {', '.join(valid_metrics)}"
        }

    metric_column_map = {
        "revenue": "SUM(cm.revenue)",
        "impressions": "SUM(cm.impressions)",
        "engagement_rate": "AVG(cm.engagement_rate)",
        "clicks": "SUM(cm.clicks)"
    }

    with get_db_cursor() as cursor:
        cursor.execute(f'''
            SELECT
                ca.id as ad_id,
                c.id as campaign_id,
                c.name as campaign_name,
                c.category,
                c.city,
                c.state,
                ca.prompt_used,
                ci.image_path,
                ci.metadata,
                {metric_column_map[metric]} as metric_value,
                SUM(cm.impressions) as total_impressions,
                SUM(cm.revenue) as total_revenue,
                AVG(cm.cost_per_impression) as avg_cpi
            FROM campaign_ads ca
            JOIN campaigns c ON ca.campaign_id = c.id
            LEFT JOIN campaign_images ci ON ca.image_id = ci.id
            LEFT JOIN campaign_metrics cm ON ca.id = cm.ad_id
            WHERE ca.status = 'completed'
            GROUP BY ca.id
            HAVING metric_value IS NOT NULL
            ORDER BY metric_value DESC
            LIMIT ?
        ''', (limit,))

        top_ads = []
        for row in cursor.fetchall():
            metadata = json.loads(row["metadata"]) if row["metadata"] else {}

            top_ads.append({
                "rank": len(top_ads) + 1,
                "ad_id": row["ad_id"],
                "campaign": {
                    "id": row["campaign_id"],
                    "name": row["campaign_name"],
                    "category": row["category"],
                    "location": f"{row['city']}, {row['state']}"
                },
                "metrics": {
                    f"{metric}": round(row["metric_value"], 2) if row["metric_value"] else 0,
                    "total_impressions": int(row["total_impressions"]) if row["total_impressions"] else 0,
                    "total_revenue": round(row["total_revenue"], 2) if row["total_revenue"] else 0,
                    "cost_per_impression": round(row["avg_cpi"], 4) if row["avg_cpi"] else 0
                },
                "characteristics": {
                    "model": metadata.get("model_description", "Unknown"),
                    "setting": metadata.get("setting_description", "Unknown"),
                    "garment": metadata.get("garment_type", "Unknown"),
                    "mood": metadata.get("mood", "Unknown"),
                    "key_feature": metadata.get("key_feature", "Unknown")
                },
                "source_image": row["image_path"]
            })

        # Extract common characteristics from top performers
        common_traits = {}
        if top_ads:
            for trait in ["garment", "mood", "setting"]:
                values = [ad["characteristics"].get(trait, "") for ad in top_ads if ad["characteristics"].get(trait)]
                if values:
                    from collections import Counter
                    most_common = Counter(values).most_common(1)
                    if most_common:
                        common_traits[trait] = most_common[0][0]

        return {
            "status": "success",
            "ranked_by": metric,
            "top_ads": top_ads,
            "insights": {
                "common_characteristics": common_traits,
                "recommendation": f"Top performers share these traits: {', '.join(common_traits.values())}" if common_traits else "Insufficient data for recommendations"
            }
        }


def get_campaign_insights(campaign_id: int) -> dict:
    """Get AI-generated insights about campaign performance.

    Analyzes campaign data and identifies key patterns and recommendations.

    Args:
        campaign_id: The ID of the campaign

    Returns:
        Dictionary with performance insights and recommendations
    """
    with get_db_cursor() as cursor:
        # Get campaign details
        cursor.execute('SELECT * FROM campaigns WHERE id = ?', (campaign_id,))
        campaign = cursor.fetchone()
        if not campaign:
            return {
                "status": "error",
                "message": f"Campaign with ID {campaign_id} not found"
            }

        # Get performance trend (weekly aggregates)
        cursor.execute('''
            SELECT
                strftime('%Y-W%W', date) as week,
                SUM(impressions) as impressions,
                SUM(revenue) as revenue,
                AVG(engagement_rate) as engagement
            FROM campaign_metrics
            WHERE campaign_id = ?
            GROUP BY week
            ORDER BY week
        ''', (campaign_id,))

        weeks = cursor.fetchall()

        trend = "stable"
        if len(weeks) >= 2:
            first_half_rev = sum(w["revenue"] for w in weeks[:len(weeks)//2])
            second_half_rev = sum(w["revenue"] for w in weeks[len(weeks)//2:])
            if second_half_rev > first_half_rev * 1.1:
                trend = "improving"
            elif second_half_rev < first_half_rev * 0.9:
                trend = "declining"

        # Get best and worst performing days
        cursor.execute('''
            SELECT date, revenue, impressions, engagement_rate
            FROM campaign_metrics
            WHERE campaign_id = ?
            ORDER BY revenue DESC
            LIMIT 1
        ''', (campaign_id,))
        best_day = cursor.fetchone()

        cursor.execute('''
            SELECT date, revenue, impressions, engagement_rate
            FROM campaign_metrics
            WHERE campaign_id = ?
            ORDER BY revenue ASC
            LIMIT 1
        ''', (campaign_id,))
        worst_day = cursor.fetchone()

        # Get ad performance comparison
        cursor.execute('''
            SELECT
                ca.id,
                ci.metadata,
                SUM(cm.revenue) as total_revenue,
                AVG(cm.engagement_rate) as avg_engagement
            FROM campaign_ads ca
            LEFT JOIN campaign_images ci ON ca.image_id = ci.id
            LEFT JOIN campaign_metrics cm ON ca.id = cm.ad_id
            WHERE ca.campaign_id = ?
            GROUP BY ca.id
            ORDER BY total_revenue DESC
        ''', (campaign_id,))

        ad_performances = cursor.fetchall()

        # Generate insights
        insights = []

        if trend == "improving":
            insights.append("Campaign performance is trending upward - consider increasing budget")
        elif trend == "declining":
            insights.append("Campaign performance is declining - review targeting and creative")

        if best_day:
            day_of_week = best_day["date"]  # Could parse to get actual day name
            insights.append(f"Best performing day: {day_of_week} (${best_day['revenue']:.2f} revenue)")

        if ad_performances:
            best_ad = ad_performances[0]
            if best_ad["metadata"]:
                metadata = json.loads(best_ad["metadata"])
                insights.append(f"Top performing creative features: {metadata.get('mood', 'N/A')} mood, {metadata.get('setting_description', 'N/A')}")

        return {
            "status": "success",
            "campaign": {
                "id": campaign["id"],
                "name": campaign["name"],
                "category": campaign["category"],
                "status": campaign["status"]
            },
            "performance_trend": trend,
            "insights": insights,
            "recommendations": [
                "Consider generating variations of top-performing ads",
                "Test different settings and moods based on successful patterns",
                "Review engagement rates by time of week"
            ] if trend != "improving" else [
                "Continue current creative strategy",
                "Consider expanding to new locations",
                "Generate similar creatives for other campaigns"
            ],
            "best_day": {
                "date": best_day["date"],
                "revenue": round(best_day["revenue"], 2),
                "impressions": int(best_day["impressions"])
            } if best_day else None,
            "worst_day": {
                "date": worst_day["date"],
                "revenue": round(worst_day["revenue"], 2),
                "impressions": int(worst_day["impressions"])
            } if worst_day else None
        }


def compare_campaigns(campaign_ids: List[int]) -> dict:
    """Compare performance metrics across multiple campaigns.

    Args:
        campaign_ids: List of campaign IDs to compare

    Returns:
        Dictionary with comparative metrics and rankings
    """
    if not campaign_ids or len(campaign_ids) < 2:
        return {
            "status": "error",
            "message": "Please provide at least 2 campaign IDs to compare"
        }

    with get_db_cursor() as cursor:
        comparisons = []

        for cid in campaign_ids:
            cursor.execute('''
                SELECT
                    c.id,
                    c.name,
                    c.category,
                    c.city,
                    c.state,
                    c.status,
                    COUNT(DISTINCT ca.id) as ad_count,
                    SUM(cm.impressions) as total_impressions,
                    SUM(cm.views) as total_views,
                    SUM(cm.clicks) as total_clicks,
                    SUM(cm.revenue) as total_revenue,
                    AVG(cm.cost_per_impression) as avg_cpi,
                    AVG(cm.engagement_rate) as avg_engagement
                FROM campaigns c
                LEFT JOIN campaign_ads ca ON c.id = ca.campaign_id
                LEFT JOIN campaign_metrics cm ON c.id = cm.campaign_id
                WHERE c.id = ?
                GROUP BY c.id
            ''', (cid,))

            row = cursor.fetchone()
            if row:
                comparisons.append({
                    "campaign_id": row["id"],
                    "name": row["name"],
                    "category": row["category"],
                    "location": f"{row['city']}, {row['state']}",
                    "status": row["status"],
                    "ad_count": row["ad_count"] or 0,
                    "metrics": {
                        "total_impressions": int(row["total_impressions"]) if row["total_impressions"] else 0,
                        "total_views": int(row["total_views"]) if row["total_views"] else 0,
                        "total_clicks": int(row["total_clicks"]) if row["total_clicks"] else 0,
                        "total_revenue": round(row["total_revenue"], 2) if row["total_revenue"] else 0,
                        "cost_per_impression": round(row["avg_cpi"], 4) if row["avg_cpi"] else 0,
                        "engagement_rate": round(row["avg_engagement"], 2) if row["avg_engagement"] else 0
                    }
                })

        if not comparisons:
            return {
                "status": "error",
                "message": "No valid campaigns found for the provided IDs"
            }

        # Rank by revenue
        ranked_by_revenue = sorted(comparisons, key=lambda x: x["metrics"]["total_revenue"], reverse=True)
        for i, c in enumerate(ranked_by_revenue):
            c["revenue_rank"] = i + 1

        # Rank by engagement
        ranked_by_engagement = sorted(comparisons, key=lambda x: x["metrics"]["engagement_rate"], reverse=True)
        for i, c in enumerate(ranked_by_engagement):
            c["engagement_rank"] = i + 1

        # Find best performer
        best = ranked_by_revenue[0]

        return {
            "status": "success",
            "campaigns_compared": len(comparisons),
            "comparisons": comparisons,
            "best_performer": {
                "by_revenue": best["name"],
                "campaign_id": best["campaign_id"],
                "total_revenue": best["metrics"]["total_revenue"]
            },
            "summary": f"Compared {len(comparisons)} campaigns. '{best['name']}' leads with ${best['metrics']['total_revenue']:.2f} revenue."
        }
