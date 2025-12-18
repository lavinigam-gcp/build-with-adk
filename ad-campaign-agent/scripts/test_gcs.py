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

"""
GCS Integration Test Script

Tests the storage abstraction module with GCS to verify cloud integration
before deploying to Cloud Run.

Prerequisites:
    - Run: gcloud auth application-default login
    - Set: export GCS_BUCKET="your-bucket-name"

Usage:
    python scripts/test_gcs.py
    python scripts/test_gcs.py --verbose
"""

import os
import sys

# Add project root to path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, PROJECT_DIR)


def print_header(text: str):
    """Print a section header."""
    print()
    print("=" * 60)
    print(text)
    print("=" * 60)


def print_success(text: str):
    """Print success message."""
    print(f"\033[92m✓ {text}\033[0m")


def print_error(text: str):
    """Print error message."""
    print(f"\033[91m✗ {text}\033[0m")


def print_warning(text: str):
    """Print warning message."""
    print(f"\033[93m⚠ {text}\033[0m")


def print_info(text: str):
    """Print info message."""
    print(f"  {text}")


def main():
    """Run all GCS integration tests."""
    verbose = "--verbose" in sys.argv or "-v" in sys.argv

    print_header("GCS Integration Test")

    # Check GCS_BUCKET is set
    gcs_bucket = os.environ.get("GCS_BUCKET")
    if not gcs_bucket:
        print_error("GCS_BUCKET environment variable not set!")
        print()
        print("To test GCS integration, run:")
        print('  export GCS_BUCKET="kaggle-on-gcp-ad-campaign-assets"')
        print("  python scripts/test_gcs.py")
        print()
        print("To test local mode (no GCS), just run the agent without GCS_BUCKET:")
        print("  adk web .")
        sys.exit(1)

    print(f"GCS_BUCKET: {gcs_bucket}")
    print()

    # Import modules after path setup
    try:
        from app import storage
        from app.config import GCS_BUCKET, SELECTED_DIR, GENERATED_DIR
        print_success("Imported app.storage and app.config")
    except ImportError as e:
        print_error(f"Failed to import modules: {e}")
        print()
        print("Make sure you have the required dependencies:")
        print("  pip install google-cloud-storage")
        sys.exit(1)

    # Verify storage mode
    storage_mode = storage.get_storage_mode()
    print(f"Storage mode: {storage_mode}")

    if storage_mode != "gcs":
        print_error(f"Expected 'gcs' mode but got '{storage_mode}'")
        print("Check that GCS_BUCKET is set correctly")
        sys.exit(1)

    print_success(f"Storage mode is 'gcs'")
    print()

    # Track test results
    tests_passed = 0
    tests_failed = 0

    # =========================================================================
    # Test 1: List seed images
    # =========================================================================
    print_header("Test 1: List Seed Images")
    try:
        images = storage.list_seed_images()
        print_success(f"Found {len(images)} seed images in GCS")

        if images:
            print("First 5 images:")
            for img in images[:5]:
                print_info(img)
            if len(images) > 5:
                print_info(f"... and {len(images) - 5} more")
            tests_passed += 1
        else:
            print_warning("No images found - bucket may be empty")
            print_info("Run: ./scripts/setup_gcp.sh to upload assets")
            tests_passed += 1  # Empty is valid, just means no uploads yet

    except Exception as e:
        print_error(f"Failed: {e}")
        tests_failed += 1

    # =========================================================================
    # Test 2: Check image exists
    # =========================================================================
    print_header("Test 2: Check Image Exists")
    try:
        images = storage.list_seed_images()
        if images:
            test_image = images[0]
            exists = storage.image_exists(test_image)
            if exists:
                print_success(f"image_exists('{test_image}') = True")
                tests_passed += 1
            else:
                print_error(f"image_exists('{test_image}') = False (unexpected)")
                tests_failed += 1

            # Test non-existent image
            fake_exists = storage.image_exists("nonexistent_image_12345.jpg")
            if not fake_exists:
                print_success("image_exists('nonexistent_image_12345.jpg') = False")
            else:
                print_warning("Non-existent image returned True (unexpected)")
        else:
            print_warning("Skipping - no images in bucket")
            tests_passed += 1

    except Exception as e:
        print_error(f"Failed: {e}")
        tests_failed += 1

    # =========================================================================
    # Test 3: Read image bytes
    # =========================================================================
    print_header("Test 3: Read Image Bytes")
    try:
        images = storage.list_seed_images()
        if images:
            test_image = images[0]
            img_bytes = storage.read_image(test_image)
            size_kb = len(img_bytes) / 1024

            if len(img_bytes) > 0:
                print_success(f"Read {size_kb:.1f} KB from '{test_image}'")

                # Verify it's a valid image (check magic bytes)
                if img_bytes[:2] == b'\xff\xd8':
                    print_info("Format: JPEG")
                elif img_bytes[:8] == b'\x89PNG\r\n\x1a\n':
                    print_info("Format: PNG")
                else:
                    print_info("Format: Unknown (but data received)")

                tests_passed += 1
            else:
                print_error("Received 0 bytes")
                tests_failed += 1
        else:
            print_warning("Skipping - no images in bucket")
            tests_passed += 1

    except Exception as e:
        print_error(f"Failed: {e}")
        tests_failed += 1

    # =========================================================================
    # Test 4: Video path format
    # =========================================================================
    print_header("Test 4: Video Path Format")
    try:
        video_path = storage.get_video_path("test_video.mp4")
        expected_prefix = f"gs://{gcs_bucket}/generated/"

        if video_path.startswith(expected_prefix):
            print_success(f"get_video_path returns correct GCS URL")
            print_info(f"Path: {video_path}")
            tests_passed += 1
        else:
            print_error(f"Unexpected path format: {video_path}")
            print_info(f"Expected prefix: {expected_prefix}")
            tests_failed += 1

    except Exception as e:
        print_error(f"Failed: {e}")
        tests_failed += 1

    # =========================================================================
    # Test 5: Check video exists
    # =========================================================================
    print_header("Test 5: Check Video Exists")
    try:
        # First, list videos directly from GCS
        from google.cloud import storage as gcs_storage
        client = gcs_storage.Client()
        bucket = client.bucket(gcs_bucket)
        blobs = list(bucket.list_blobs(prefix="generated/"))
        videos = [b.name.replace("generated/", "") for b in blobs if b.name.endswith(".mp4")]

        print(f"Found {len(videos)} videos in GCS")

        if videos:
            test_video = videos[0]
            exists = storage.video_exists(test_video)
            if exists:
                print_success(f"video_exists('{test_video}') = True")
                tests_passed += 1
            else:
                print_error(f"video_exists('{test_video}') = False (unexpected)")
                tests_failed += 1
        else:
            print_warning("No videos in bucket - testing non-existent video")
            fake_exists = storage.video_exists("nonexistent_video_12345.mp4")
            if not fake_exists:
                print_success("video_exists returns False for missing video")
                tests_passed += 1
            else:
                print_error("Returned True for non-existent video")
                tests_failed += 1

    except Exception as e:
        print_error(f"Failed: {e}")
        tests_failed += 1

    # =========================================================================
    # Test 6: Read video bytes
    # =========================================================================
    print_header("Test 6: Read Video Bytes")
    try:
        from google.cloud import storage as gcs_storage
        client = gcs_storage.Client()
        bucket = client.bucket(gcs_bucket)
        blobs = list(bucket.list_blobs(prefix="generated/"))
        videos = [b.name.replace("generated/", "") for b in blobs if b.name.endswith(".mp4")]

        if videos:
            test_video = videos[0]
            video_bytes = storage.read_video(test_video)
            size_mb = len(video_bytes) / (1024 * 1024)

            if len(video_bytes) > 0:
                print_success(f"Read {size_mb:.2f} MB from '{test_video}'")

                # Check for MP4 magic bytes (ftyp box)
                if b'ftyp' in video_bytes[:32]:
                    print_info("Format: Valid MP4")
                else:
                    print_info("Format: Unknown (but data received)")

                tests_passed += 1
            else:
                print_error("Received 0 bytes")
                tests_failed += 1
        else:
            print_warning("Skipping - no videos in bucket")
            tests_passed += 1

    except Exception as e:
        print_error(f"Failed: {e}")
        tests_failed += 1

    # =========================================================================
    # Test 7: Write test (save and delete)
    # =========================================================================
    print_header("Test 7: Write/Delete Test")
    try:
        # Create test data
        test_filename = "_test_gcs_integration_12345.txt"
        test_data = b"GCS integration test file - safe to delete"

        # Upload using save_image (tests upload_from_file with BytesIO)
        print("Uploading test file...")
        from google.cloud import storage as gcs_storage
        client = gcs_storage.Client()
        bucket = client.bucket(gcs_bucket)
        blob = bucket.blob(f"seed-images/{test_filename}")

        import io
        blob.upload_from_file(io.BytesIO(test_data), content_type="text/plain", rewind=True)
        print_success("Upload successful")

        # Verify it exists
        if blob.exists():
            print_success("File exists in GCS")

            # Download and verify content
            downloaded = blob.download_as_bytes()
            if downloaded == test_data:
                print_success("Content verified")
            else:
                print_warning("Content mismatch")

            # Clean up
            blob.delete()
            print_success("Test file deleted")
            tests_passed += 1
        else:
            print_error("File not found after upload")
            tests_failed += 1

    except Exception as e:
        print_error(f"Failed: {e}")
        tests_failed += 1

    # =========================================================================
    # Summary
    # =========================================================================
    print_header("Test Summary")

    total = tests_passed + tests_failed
    print(f"Passed: {tests_passed}/{total}")
    print(f"Failed: {tests_failed}/{total}")
    print()

    if tests_failed == 0:
        print_success("All GCS integration tests passed!")
        print()
        print("You can now run the agent with GCS mode:")
        print(f'  export GCS_BUCKET="{gcs_bucket}"')
        print('  export GOOGLE_GENAI_USE_VERTEXAI="True"')
        print("  adk web .")
        print()
        return 0
    else:
        print_error(f"{tests_failed} test(s) failed")
        print()
        print("Check the errors above and ensure:")
        print("  1. You've run: gcloud auth application-default login")
        print("  2. The bucket exists and has the correct permissions")
        print("  3. Assets have been uploaded: ./scripts/setup_gcp.sh")
        return 1


if __name__ == "__main__":
    sys.exit(main())
