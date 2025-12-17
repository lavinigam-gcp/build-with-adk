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
import time
from typing import List, Optional

from google import genai
from google.genai import types
from google.adk.tools import ToolContext

from ..database.db import get_db_cursor


def get_campaign_metrics(campaign_id: int, days: int = 30) -> dict:
    """Get performance metrics for a campaign.

    Returns daily and aggregated in-store retail media metrics including
    impressions, dwell time, circulation, and revenue per impression (RPI).

    Args:
        campaign_id: The ID of the campaign
        days: Number of days to retrieve (default: 30)

    Returns:
        Dictionary with daily metrics and aggregated totals
    """
    print(f"[DEBUG get_campaign_metrics] Starting for campaign_id={campaign_id}, days={days}")
    with get_db_cursor() as cursor:
        # Verify campaign exists
        cursor.execute('SELECT id, name, status FROM campaigns WHERE id = ?', (campaign_id,))
        campaign = cursor.fetchone()
        if not campaign:
            return {
                "status": "error",
                "message": f"Campaign with ID {campaign_id} not found"
            }

        # Get daily metrics (in-store retail media)
        cursor.execute('''
            SELECT
                date,
                SUM(impressions) as impressions,
                AVG(dwell_time) as avg_dwell_time,
                SUM(circulation) as circulation,
                SUM(revenue) as revenue
            FROM campaign_metrics
            WHERE campaign_id = ?
            AND date >= date('now', ?)
            GROUP BY date
            ORDER BY date DESC
        ''', (campaign_id, f'-{days} days'))

        daily_metrics = []
        for row in cursor.fetchall():
            impressions = int(row["impressions"])
            revenue = round(row["revenue"], 2)
            # Compute RPI on the fly (THE key metric)
            rpi = round(revenue / impressions, 4) if impressions > 0 else 0

            daily_metrics.append({
                "date": row["date"],
                "impressions": impressions,
                "dwell_time": round(row["avg_dwell_time"], 1),
                "circulation": int(row["circulation"]),
                "revenue_per_impression": rpi
            })

        # Get aggregated totals
        cursor.execute('''
            SELECT
                SUM(impressions) as total_impressions,
                AVG(dwell_time) as avg_dwell_time,
                SUM(circulation) as total_circulation,
                SUM(revenue) as total_revenue
            FROM campaign_metrics
            WHERE campaign_id = ?
            AND date >= date('now', ?)
        ''', (campaign_id, f'-{days} days'))

        totals = cursor.fetchone()

        summary = None
        if totals and totals["total_impressions"]:
            total_impressions = int(totals["total_impressions"])
            total_revenue = round(totals["total_revenue"], 2)
            # RPI is THE key metric for retail media
            rpi = round(total_revenue / total_impressions, 4) if total_impressions > 0 else 0

            summary = {
                "total_impressions": total_impressions,
                "average_dwell_time": round(totals["avg_dwell_time"], 1),
                "total_circulation": int(totals["total_circulation"]),
                "total_revenue": total_revenue,
                "revenue_per_impression": rpi,
                "revenue_per_1000_impressions": round(rpi * 1000, 2)  # CPM equivalent
            }

        print(f"[DEBUG get_campaign_metrics] Found {len(daily_metrics)} daily records")
        print(f"[DEBUG get_campaign_metrics] Summary: {summary}")
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


def get_top_performing_ads(metric: str = "revenue_per_impression", limit: int = 5) -> dict:
    """Get top performing ads across all campaigns.

    Identifies the best ads and their key characteristics for insights.
    Uses in-store retail media metrics.

    Args:
        metric: Metric to rank by - one of: revenue_per_impression, impressions, dwell_time, circulation
        limit: Number of top ads to return

    Returns:
        Dictionary with top ads and their characteristics
    """
    print(f"[DEBUG get_top_performing_ads] Starting with metric={metric}, limit={limit}")
    valid_metrics = ["revenue_per_impression", "impressions", "dwell_time", "circulation"]
    if metric not in valid_metrics:
        return {
            "status": "error",
            "message": f"Invalid metric. Must be one of: {', '.join(valid_metrics)}"
        }

    # RPI must be computed, not a direct column
    metric_column_map = {
        "revenue_per_impression": "SUM(cm.revenue) / NULLIF(SUM(cm.impressions), 0)",
        "impressions": "SUM(cm.impressions)",
        "dwell_time": "AVG(cm.dwell_time)",
        "circulation": "SUM(cm.circulation)"
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
                AVG(cm.dwell_time) as avg_dwell_time,
                SUM(cm.circulation) as total_circulation,
                SUM(cm.revenue) as total_revenue
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
            total_impressions = int(row["total_impressions"]) if row["total_impressions"] else 0
            total_revenue = round(row["total_revenue"], 2) if row["total_revenue"] else 0
            # Compute RPI
            rpi = round(total_revenue / total_impressions, 4) if total_impressions > 0 else 0

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
                    f"{metric}": round(row["metric_value"], 4) if row["metric_value"] else 0,
                    "total_impressions": total_impressions,
                    "average_dwell_time": round(row["avg_dwell_time"], 1) if row["avg_dwell_time"] else 0,
                    "total_circulation": int(row["total_circulation"]) if row["total_circulation"] else 0,
                    "revenue_per_impression": rpi
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

        print(f"[DEBUG get_top_performing_ads] Found {len(top_ads)} top ads")
        print(f"[DEBUG get_top_performing_ads] Common traits: {common_traits}")
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
    Uses in-store retail media metrics.

    Args:
        campaign_id: The ID of the campaign

    Returns:
        Dictionary with performance insights and recommendations
    """
    print(f"[DEBUG get_campaign_insights] Starting for campaign_id={campaign_id}")
    with get_db_cursor() as cursor:
        # Get campaign details
        cursor.execute('SELECT * FROM campaigns WHERE id = ?', (campaign_id,))
        campaign = cursor.fetchone()
        if not campaign:
            return {
                "status": "error",
                "message": f"Campaign with ID {campaign_id} not found"
            }

        # Get performance trend (weekly aggregates) - using RPI as key metric
        cursor.execute('''
            SELECT
                strftime('%Y-W%W', date) as week,
                SUM(impressions) as impressions,
                SUM(revenue) as revenue,
                AVG(dwell_time) as avg_dwell
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

        # Get best and worst performing days by RPI
        cursor.execute('''
            SELECT date, revenue, impressions, dwell_time,
                   revenue * 1.0 / NULLIF(impressions, 0) as rpi
            FROM campaign_metrics
            WHERE campaign_id = ?
            ORDER BY rpi DESC
            LIMIT 1
        ''', (campaign_id,))
        best_day = cursor.fetchone()

        cursor.execute('''
            SELECT date, revenue, impressions, dwell_time,
                   revenue * 1.0 / NULLIF(impressions, 0) as rpi
            FROM campaign_metrics
            WHERE campaign_id = ?
            ORDER BY rpi ASC
            LIMIT 1
        ''', (campaign_id,))
        worst_day = cursor.fetchone()

        # Get ad performance comparison
        cursor.execute('''
            SELECT
                ca.id,
                ci.metadata,
                SUM(cm.revenue) as total_revenue,
                SUM(cm.impressions) as total_impressions,
                AVG(cm.dwell_time) as avg_dwell
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
            insights.append("Campaign RPI is trending upward - consider increasing budget")
        elif trend == "declining":
            insights.append("Campaign RPI is declining - review creative and placement")

        if best_day:
            rpi = round(best_day["rpi"], 4) if best_day["rpi"] else 0
            insights.append(f"Best performing day: {best_day['date']} (RPI: ${rpi:.4f}, Dwell: {best_day['dwell_time']:.1f}s)")

        if ad_performances:
            best_ad = ad_performances[0]
            if best_ad["total_impressions"] and best_ad["total_impressions"] > 0:
                ad_rpi = round(best_ad["total_revenue"] / best_ad["total_impressions"], 4)
                if best_ad["metadata"]:
                    metadata = json.loads(best_ad["metadata"])
                    insights.append(f"Top performer (RPI: ${ad_rpi:.4f}): {metadata.get('mood', 'N/A')} mood, avg dwell {best_ad['avg_dwell']:.1f}s")

        print(f"[DEBUG get_campaign_insights] Trend: {trend}, Insights: {len(insights)} items")
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
                "Review dwell time patterns by time of week"
            ] if trend != "improving" else [
                "Continue current creative strategy",
                "Consider expanding to new locations",
                "Generate similar creatives for other campaigns"
            ],
            "best_day": {
                "date": best_day["date"],
                "revenue_per_impression": round(best_day["rpi"], 4) if best_day["rpi"] else 0,
                "impressions": int(best_day["impressions"]),
                "dwell_time": round(best_day["dwell_time"], 1)
            } if best_day else None,
            "worst_day": {
                "date": worst_day["date"],
                "revenue_per_impression": round(worst_day["rpi"], 4) if worst_day["rpi"] else 0,
                "impressions": int(worst_day["impressions"]),
                "dwell_time": round(worst_day["dwell_time"], 1)
            } if worst_day else None
        }


def compare_campaigns(campaign_ids: List[int]) -> dict:
    """Compare performance metrics across multiple campaigns.

    Compares in-store retail media metrics including impressions, dwell time,
    circulation, and revenue per impression (RPI).

    Args:
        campaign_ids: List of campaign IDs to compare

    Returns:
        Dictionary with comparative metrics and rankings
    """
    print(f"[DEBUG compare_campaigns] Starting with campaign_ids={campaign_ids}")
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
                    AVG(cm.dwell_time) as avg_dwell_time,
                    SUM(cm.circulation) as total_circulation,
                    SUM(cm.revenue) as total_revenue
                FROM campaigns c
                LEFT JOIN campaign_ads ca ON c.id = ca.campaign_id
                LEFT JOIN campaign_metrics cm ON c.id = cm.campaign_id
                WHERE c.id = ?
                GROUP BY c.id
            ''', (cid,))

            row = cursor.fetchone()
            if row:
                total_impressions = int(row["total_impressions"]) if row["total_impressions"] else 0
                total_revenue = round(row["total_revenue"], 2) if row["total_revenue"] else 0
                # Compute RPI on the fly
                rpi = round(total_revenue / total_impressions, 4) if total_impressions > 0 else 0

                comparisons.append({
                    "campaign_id": row["id"],
                    "name": row["name"],
                    "category": row["category"],
                    "location": f"{row['city']}, {row['state']}",
                    "status": row["status"],
                    "ad_count": row["ad_count"] or 0,
                    "metrics": {
                        "total_impressions": total_impressions,
                        "average_dwell_time": round(row["avg_dwell_time"], 1) if row["avg_dwell_time"] else 0,
                        "total_circulation": int(row["total_circulation"]) if row["total_circulation"] else 0,
                        "total_revenue": total_revenue,
                        "revenue_per_impression": rpi,
                        "revenue_per_1000_impressions": round(rpi * 1000, 2)
                    }
                })

        if not comparisons:
            return {
                "status": "error",
                "message": "No valid campaigns found for the provided IDs"
            }

        # Rank by RPI (the primary KPI for retail media)
        ranked_by_rpi = sorted(comparisons, key=lambda x: x["metrics"]["revenue_per_impression"], reverse=True)
        for i, c in enumerate(ranked_by_rpi):
            c["rpi_rank"] = i + 1

        # Rank by dwell time (engagement indicator)
        ranked_by_dwell = sorted(comparisons, key=lambda x: x["metrics"]["average_dwell_time"], reverse=True)
        for i, c in enumerate(ranked_by_dwell):
            c["dwell_time_rank"] = i + 1

        # Find best performer by RPI
        best = ranked_by_rpi[0]

        print(f"[DEBUG compare_campaigns] Compared {len(comparisons)} campaigns")
        print(f"[DEBUG compare_campaigns] Best performer: {best['name']}")
        return {
            "status": "success",
            "campaigns_compared": len(comparisons),
            "comparisons": comparisons,
            "best_performer": {
                "by_rpi": best["name"],
                "campaign_id": best["campaign_id"],
                "revenue_per_impression": best["metrics"]["revenue_per_impression"],
                "total_revenue": best["metrics"]["total_revenue"]
            },
            "summary": f"Compared {len(comparisons)} campaigns. '{best['name']}' leads with RPI of ${best['metrics']['revenue_per_impression']:.4f} (${best['metrics']['total_revenue']:.2f} total revenue)."
        }


async def generate_metrics_visualization(
    campaign_id: int,
    chart_type: str = "trendline",
    metric: str = "revenue",
    days: int = 30,
    tool_context: ToolContext = None
) -> dict:
    """Generate a visual chart/infographic from campaign metrics using Gemini 3 Pro Image.

    Creates professional data visualizations as images using AI image generation.
    The generated chart is saved as an ADK artifact for viewing in the web UI.

    Args:
        campaign_id: The campaign to visualize metrics for
        chart_type: Type of visualization - one of: trendline, bar_chart, comparison, infographic
        metric: Which metric to visualize - one of: revenue_per_impression, impressions, dwell_time, circulation
        days: Number of days of data to include (default: 30)
        tool_context: ADK ToolContext for artifact storage

    Returns:
        Dictionary with visualization details and artifact info
    """
    print(f"[DEBUG generate_metrics_visualization] Starting for campaign_id={campaign_id}")
    print(f"[DEBUG generate_metrics_visualization] chart_type={chart_type}, metric={metric}, days={days}")

    valid_chart_types = ["trendline", "bar_chart", "comparison", "infographic"]
    valid_metrics = ["revenue_per_impression", "impressions", "dwell_time", "circulation"]

    if chart_type not in valid_chart_types:
        return {
            "status": "error",
            "message": f"Invalid chart_type. Must be one of: {', '.join(valid_chart_types)}"
        }

    if metric not in valid_metrics:
        return {
            "status": "error",
            "message": f"Invalid metric. Must be one of: {', '.join(valid_metrics)}"
        }

    # Get campaign metrics data
    print(f"[DEBUG VIZ] Step 1: Fetching metrics from database...")
    metrics_result = get_campaign_metrics(campaign_id, days)
    if metrics_result["status"] == "error":
        return metrics_result

    campaign_name = metrics_result["campaign"]["name"]
    summary = metrics_result["summary"]
    daily_metrics = metrics_result["daily_metrics"]

    print(f"[DEBUG VIZ] Step 2: Data received from DB:")
    print(f"[DEBUG VIZ]   - Campaign: {campaign_name}")
    print(f"[DEBUG VIZ]   - Total daily records: {len(daily_metrics)}")
    print(f"[DEBUG VIZ]   - Summary totals: impressions={summary['total_impressions']:,}, revenue=${summary['total_revenue']:,.2f}")

    # Show first 3 and last 3 daily records as sample
    if daily_metrics:
        print(f"[DEBUG VIZ]   - Sample daily data (first 3 records):")
        for i, day in enumerate(daily_metrics[:3]):
            print(f"[DEBUG VIZ]     [{i}] date={day['date']}, {metric}={day.get(metric, 'N/A')}")
        if len(daily_metrics) > 6:
            print(f"[DEBUG VIZ]     ... ({len(daily_metrics) - 6} more records) ...")
        if len(daily_metrics) > 3:
            print(f"[DEBUG VIZ]   - Sample daily data (last 3 records):")
            for i, day in enumerate(daily_metrics[-3:]):
                print(f"[DEBUG VIZ]     [{len(daily_metrics)-3+i}] date={day['date']}, {metric}={day.get(metric, 'N/A')}")

    if not daily_metrics:
        return {
            "status": "error",
            "message": f"No metrics data available for campaign {campaign_id}"
        }

    # Extract data points for the visualization
    print(f"[DEBUG VIZ] Step 3: Extracting '{metric}' values from daily_metrics...")
    data_points = []
    for day in daily_metrics[:min(days, len(daily_metrics))]:
        data_points.append({
            "date": day["date"],
            "value": day.get(metric, 0)
        })

    # Reverse to show oldest to newest
    data_points = list(reversed(data_points))

    print(f"[DEBUG VIZ]   - Extracted {len(data_points)} data points (oldest to newest)")
    print(f"[DEBUG VIZ]   - First point: date={data_points[0]['date']}, value={data_points[0]['value']}")
    print(f"[DEBUG VIZ]   - Last point: date={data_points[-1]['date']}, value={data_points[-1]['value']}")

    # Calculate statistics for the prompt
    values = [d["value"] for d in data_points]
    min_val = min(values) if values else 0
    max_val = max(values) if values else 0
    avg_val = sum(values) / len(values) if values else 0
    total_val = sum(values)

    print(f"[DEBUG VIZ] Step 4: Calculated statistics:")
    print(f"[DEBUG VIZ]   - Min: {min_val}")
    print(f"[DEBUG VIZ]   - Max: {max_val}")
    print(f"[DEBUG VIZ]   - Avg: {avg_val:.2f}")
    print(f"[DEBUG VIZ]   - Sum: {total_val}")

    # Determine trend
    if len(values) >= 2:
        first_half = sum(values[:len(values)//2]) / (len(values)//2)
        second_half = sum(values[len(values)//2:]) / (len(values) - len(values)//2)
        print(f"[DEBUG VIZ]   - First half avg: {first_half:.2f}")
        print(f"[DEBUG VIZ]   - Second half avg: {second_half:.2f}")
        if second_half > first_half * 1.05:
            trend = "upward trending"
        elif second_half < first_half * 0.95:
            trend = "downward trending"
        else:
            trend = "stable"
    else:
        trend = "stable"

    print(f"[DEBUG VIZ]   - Trend: {trend}")

    # Format metric name for display
    metric_display = metric.replace("_", " ").title()
    if metric == "revenue_per_impression":
        metric_display = "Revenue Per Impression (RPI)"
        value_format = f"${min_val:.4f} to ${max_val:.4f}"
    elif metric == "dwell_time":
        metric_display = "Dwell Time (seconds)"
        value_format = f"{min_val:.1f}s to {max_val:.1f}s"
    elif metric == "circulation":
        metric_display = "Circulation (foot traffic)"
        value_format = f"{int(min_val):,} to {int(max_val):,}"
    else:
        value_format = f"{int(min_val):,} to {int(max_val):,}"

    print(f"[DEBUG VIZ]   - Display format: {metric_display}, range: {value_format}")

    # Build the visualization prompt based on chart type
    print(f"[DEBUG VIZ] Step 5: Building prompt for chart_type='{chart_type}'...")

    if chart_type == "trendline":
        visualization_prompt = f"""Create a professional, clean line chart infographic showing:

CHART SPECIFICATIONS:
- Title: "{campaign_name} - {metric_display} Trend"
- Chart Type: Line chart with smooth curve
- X-Axis: Time period ({len(data_points)} days)
- Y-Axis: {metric_display}
- Data Range: {value_format}
- Trend: {trend}

STYLE:
- Modern, minimalist business dashboard style
- Dark blue or teal line on white/light gray background
- Gradient fill under the line
- Clean sans-serif font (like Roboto or Inter)
- Subtle grid lines
- Rounded corners on the chart container
- Small data point markers

KEY STATISTICS TO SHOW:
- Average: {avg_val:.2f}
- Peak: {max_val:.2f}
- Trend arrow indicating {trend}

Make it look like a professional analytics dashboard widget. High quality, crisp, suitable for business presentation."""

    elif chart_type == "bar_chart":
        # Get weekly aggregates for bar chart
        print(f"[DEBUG VIZ]   - Aggregating data into weekly buckets...")
        weekly_data = []
        week_size = 7
        for i in range(0, len(data_points), week_size):
            week_slice = data_points[i:i+week_size]
            if week_slice:
                week_total = sum(d["value"] for d in week_slice)
                weekly_data.append({"week": f"Week {len(weekly_data)+1}", "value": week_total})
                print(f"[DEBUG VIZ]     Week {len(weekly_data)}: {len(week_slice)} days, total={week_total:.2f}")

        visualization_prompt = f"""Create a professional bar chart infographic showing:

CHART SPECIFICATIONS:
- Title: "{campaign_name} - Weekly {metric_display}"
- Chart Type: Vertical bar chart
- Number of bars: {len(weekly_data)} weeks
- Y-Axis: {metric_display}
- Data Range: {value_format}

STYLE:
- Modern gradient bars (blue to purple or teal to blue)
- White/light gray background
- Each bar slightly rounded at top
- Clean sans-serif typography
- Value labels above each bar
- Subtle drop shadows for depth

WEEKLY VALUES:
{json.dumps(weekly_data, indent=2)}

Make it look like a polished business analytics chart. Professional, clean, high resolution."""

    elif chart_type == "comparison":
        # Create a comparison with multiple metrics (in-store retail media)
        print(f"[DEBUG VIZ]   - Comparison chart using summary metrics:")
        print(f"[DEBUG VIZ]     RPI: ${summary['revenue_per_impression']:.4f}")
        print(f"[DEBUG VIZ]     Impressions: {summary['total_impressions']:,}")
        print(f"[DEBUG VIZ]     Dwell Time: {summary['average_dwell_time']:.1f}s")
        print(f"[DEBUG VIZ]     Circulation: {summary['total_circulation']:,}")
        visualization_prompt = f"""Create a professional multi-metric comparison infographic for:

CAMPAIGN: "{campaign_name}"
TIME PERIOD: Last {days} days
CONTEXT: In-Store Retail Media Network

KEY METRICS TO DISPLAY:
- Revenue Per Impression (RPI): ${summary['revenue_per_impression']:.4f} (PRIMARY KPI)
- Total Impressions: {summary['total_impressions']:,}
- Average Dwell Time: {summary['average_dwell_time']:.1f} seconds
- Total Circulation: {summary['total_circulation']:,} (foot traffic)

STYLE:
- Modern dashboard card layout
- 4 metric boxes in a 2x2 grid
- Each box with:
  - Large number as the value
  - Metric name below
  - Trend indicator (arrow up/down)
  - Color coded (green for good, blue for neutral)
- RPI box should be prominently highlighted as primary KPI
- Clean white background with subtle shadows
- Campaign name as header
- Professional retail analytics style

Make it look like a KPI dashboard summary card. High quality, suitable for executive reporting."""

    else:  # infographic
        print(f"[DEBUG VIZ]   - Infographic using all data:")
        print(f"[DEBUG VIZ]     Primary metric: {metric_display}")
        print(f"[DEBUG VIZ]     RPI: ${summary['revenue_per_impression']:.4f}")
        print(f"[DEBUG VIZ]     Impressions: {summary['total_impressions']:,}")
        print(f"[DEBUG VIZ]     Dwell Time: {summary['average_dwell_time']:.1f}s")
        visualization_prompt = f"""Create a comprehensive visual infographic for:

CAMPAIGN: "{campaign_name}"
ANALYSIS PERIOD: Last {days} days
CONTEXT: In-Store Retail Media Network

DATA TO VISUALIZE:
- Primary Metric: {metric_display}
- Trend: {trend}
- Range: {value_format}
- Average: {avg_val:.2f}

PERFORMANCE SUMMARY (RETAIL MEDIA):
- Revenue Per Impression (RPI): ${summary['revenue_per_impression']:.4f} (PRIMARY KPI)
- Total Impressions: {summary['total_impressions']:,}
- Average Dwell Time: {summary['average_dwell_time']:.1f} seconds
- Total Circulation: {summary['total_circulation']:,} (foot traffic)

INFOGRAPHIC STYLE:
- Magazine-quality data visualization
- Combination of mini charts, icons, and numbers
- Color palette: Professional blues, teals, and accents
- Clean typography hierarchy
- Visual flow from top to bottom
- Include trend arrows and percentage indicators
- Modern flat design with subtle gradients
- RPI prominently featured as the key success metric

Create a visually stunning, information-rich infographic suitable for a marketing presentation or report cover."""

    print(f"[DEBUG VIZ] Step 6: Complete prompt being sent to Gemini 3 Pro Image:")
    print(f"[DEBUG VIZ] {'='*60}")
    print(visualization_prompt)
    print(f"[DEBUG VIZ] {'='*60}")
    print(f"[DEBUG VIZ] Prompt length: {len(visualization_prompt)} characters")

    try:
        print("[DEBUG VIZ] Step 7: Calling Gemini 3 Pro Image API...")
        client = genai.Client()

        # Generate visualization using Gemini 3 Pro Image
        response = client.models.generate_content(
            model="gemini-3-pro-image-preview",
            contents=[visualization_prompt],
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE"],
                image_config=types.ImageConfig(
                    aspect_ratio="16:9",  # Wide format for charts
                )
            )
        )
        print(f"[DEBUG VIZ]   - Response received, parts count: {len(response.parts) if response.parts else 0}")

        # Extract image from response
        generated_image = None
        for i, part in enumerate(response.parts):
            has_inline = hasattr(part, 'inline_data') and part.inline_data is not None
            print(f"[DEBUG VIZ]   - Part {i}: has inline_data={has_inline}")
            if part.inline_data:
                generated_image = part
                print(f"[DEBUG VIZ]   - Image found in part {i}, size: {len(part.inline_data.data)} bytes")
                break

        if generated_image is None:
            print("[DEBUG VIZ]   - ERROR: No image found in response")
            return {
                "status": "error",
                "message": "Failed to generate visualization. Try a different chart type or metric."
            }

        # Save as ADK artifact (not locally)
        timestamp = int(time.time())
        filename = f"chart_{campaign_id}_{chart_type}_{metric}_{timestamp}.png"

        print(f"[DEBUG VIZ] Step 8: Saving artifact...")
        if tool_context:
            print(f"[DEBUG VIZ]   - Filename: {filename}")
            # Get the image bytes from inline_data
            image_bytes = generated_image.inline_data.data
            image_artifact = types.Part.from_bytes(data=image_bytes, mime_type="image/png")
            version = await tool_context.save_artifact(filename=filename, artifact=image_artifact)
            print(f"[DEBUG VIZ]   - Artifact saved successfully, version: {version}")
            artifact_saved = True
        else:
            print("[DEBUG VIZ]   - WARNING: No tool_context, artifact not saved")
            artifact_saved = False
            version = None

        print(f"[DEBUG VIZ] Step 9: SUCCESS - Visualization complete!")
        print(f"[DEBUG VIZ]   - Data points used: {len(data_points)}")
        print(f"[DEBUG VIZ]   - Statistics: min={min_val}, max={max_val}, avg={avg_val:.2f}")
        print(f"[DEBUG VIZ]   - Trend: {trend}")

        return {
            "status": "success",
            "message": f"Generated {chart_type} visualization for {campaign_name}",
            "visualization": {
                "campaign_id": campaign_id,
                "campaign_name": campaign_name,
                "chart_type": chart_type,
                "metric": metric,
                "days": days,
                "filename": filename,
                "artifact_saved": artifact_saved,
                "artifact_version": version,
                "data_summary": {
                    "data_points": len(data_points),
                    "min": min_val,
                    "max": max_val,
                    "average": round(avg_val, 2),
                    "trend": trend
                }
            }
        }

    except Exception as e:
        import traceback
        print(f"[DEBUG VIZ] EXCEPTION: {str(e)}")
        print(f"[DEBUG VIZ] Traceback: {traceback.format_exc()}")
        return {
            "status": "error",
            "message": f"Failed to generate visualization: {str(e)}"
        }
