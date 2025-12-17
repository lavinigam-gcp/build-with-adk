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

"""One-time script to backfill video_properties for existing videos.

This script analyzes all existing completed videos that don't have video_properties
and populates the video_properties column using Gemini video analysis.

Run this once after deploying the video properties feature:
    cd ad-campaign-agent
    python -m scripts.backfill_video_properties

After running successfully, this script can be deleted from the repository.
"""

import asyncio
import os
import sys

# Add project root to path for imports
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from app.database.db import get_db_cursor
from app.config import GENERATED_DIR, VIDEO_ANALYSIS_MODEL
from app.tools.video_tools import analyze_video


async def backfill_all_videos():
    """Analyze all existing videos and populate their video_properties."""
    print("=" * 60)
    print("Video Properties Backfill Script")
    print("=" * 60)
    print()
    print(f"Using model: {VIDEO_ANALYSIS_MODEL}")
    print()

    # First, check if any videos need backfilling
    with get_db_cursor() as cursor:
        cursor.execute('''
            SELECT id, video_path, campaign_id, status
            FROM campaign_ads
            WHERE status = 'completed' AND (video_properties IS NULL OR video_properties = '')
        ''')
        ads_to_backfill = cursor.fetchall()

    if not ads_to_backfill:
        print("No videos need backfilling. All completed videos already have properties.")
        return

    print(f"Found {len(ads_to_backfill)} video(s) to backfill")
    print()

    success = 0
    skipped = 0
    failed = 0

    for ad in ads_to_backfill:
        ad_id = ad["id"]
        video_filename = ad["video_path"]
        campaign_id = ad["campaign_id"]

        print(f"[Ad #{ad_id}] Processing: {video_filename}")

        if not video_filename:
            print(f"  SKIP: No video path set")
            skipped += 1
            continue

        video_path = os.path.join(GENERATED_DIR, video_filename)

        if not os.path.exists(video_path):
            print(f"  SKIP: Video file not found at {video_path}")
            skipped += 1
            continue

        try:
            print(f"  Analyzing video with Gemini...")
            properties = await analyze_video(video_path)

            # Save to database
            with get_db_cursor() as cursor:
                cursor.execute(
                    'UPDATE campaign_ads SET video_properties = ? WHERE id = ?',
                    (properties.model_dump_json(), ad_id)
                )

            print(f"  OK: mood={properties.mood}, energy={properties.energy_level}, "
                  f"style={properties.visual_style}")
            success += 1

        except Exception as e:
            print(f"  ERROR: {str(e)}")
            failed += 1

    print()
    print("=" * 60)
    print("Backfill Complete")
    print("=" * 60)
    print(f"  Success: {success}")
    print(f"  Skipped: {skipped}")
    print(f"  Failed:  {failed}")
    print()

    if success > 0:
        print("Video properties have been populated successfully.")
        print("You can now delete this script from the repository.")


def main():
    """Entry point for the backfill script."""
    print()
    print("This script will analyze all existing videos and populate video_properties.")
    print("This may take several minutes depending on the number of videos.")
    print()

    # Check if GOOGLE_API_KEY is set
    if not os.environ.get("GOOGLE_API_KEY"):
        print("ERROR: GOOGLE_API_KEY environment variable is not set.")
        print("Please set it before running this script:")
        print("  export GOOGLE_API_KEY='your-api-key'")
        sys.exit(1)

    # Run the async backfill
    asyncio.run(backfill_all_videos())


if __name__ == "__main__":
    main()
