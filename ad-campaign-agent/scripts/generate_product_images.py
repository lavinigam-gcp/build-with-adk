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

"""Product Image Generator for Fashion Catalog.

Generates high-quality product images for women's fashion articles using
Gemini 3 Pro Image Preview. Images are optimized for e-commerce catalogs
with clean white backgrounds and no models.

Usage:
    # Generate from JSON file
    python -m scripts.generate_product_images --input products.json

    # Generate single product
    python -m scripts.generate_product_images --product '{
        "name": "floral-summer-dress",
        "category": "dress",
        "style": "midi wrap dress",
        "color": "pink and white floral",
        "fabric": "flowing chiffon",
        "details": "v-neck, flutter sleeves, tiered skirt"
    }'

    # Generate from preset categories
    python -m scripts.generate_product_images --preset dresses --count 5

Output:
    Images are saved to scripts/products/ with descriptive filenames.
"""

import argparse
import asyncio
import json
import os
import sys
import time
from datetime import datetime
from typing import Optional

from google import genai
from google.genai import types
from PIL import Image

# Output directory
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "products")

# Model configuration
MODEL = "gemini-3-pro-image-preview"
ASPECT_RATIO = "9:16"  # Vertical for product catalogs
RESOLUTION = "2K"  # High quality

# Rate limiting (Gemini has ~10 images/minute limit)
RATE_LIMIT_DELAY = 8  # seconds between generations


def build_catalog_prompt(product: dict) -> str:
    """Build an optimized prompt for catalog-quality product images.

    Creates a detailed prompt that produces clean, professional product
    photography suitable for e-commerce websites and catalogs.

    Args:
        product: Dictionary with product attributes

    Returns:
        Optimized prompt string for Gemini 3 Pro Image
    """
    # Extract product attributes
    name = product.get("name", "fashion-item")
    category = product.get("category", "clothing")
    style = product.get("style", "")
    color = product.get("color", "")
    fabric = product.get("fabric", "")
    details = product.get("details", "")
    pattern = product.get("pattern", "")
    occasion = product.get("occasion", "")

    # Build the core garment description
    garment_parts = []
    if color:
        garment_parts.append(color)
    if fabric:
        garment_parts.append(fabric)
    if style:
        garment_parts.append(style)
    elif category:
        garment_parts.append(category)

    garment_description = " ".join(garment_parts) if garment_parts else f"women's {category}"

    # Build detail description
    detail_parts = []
    if pattern:
        detail_parts.append(f"featuring {pattern} pattern")
    if details:
        detail_parts.append(f"with {details}")
    if occasion:
        detail_parts.append(f"perfect for {occasion}")

    detail_description = ", ".join(detail_parts)

    # Construct the optimized prompt for catalog photography
    prompt = f"""Professional e-commerce product photography of a {garment_description}.

PRODUCT DETAILS:
{detail_description}

PHOTOGRAPHY REQUIREMENTS:
- Pure white seamless background (#FFFFFF)
- Product displayed flat-lay or on invisible mannequin (ghost mannequin style)
- NO human model, NO visible mannequin, NO hangers
- Product centered in frame with proper margins
- Soft, even studio lighting with subtle shadows for depth
- Crisp focus on fabric texture and construction details
- High-end fashion catalog aesthetic
- Clean, minimalist composition

STYLE:
- Luxury fashion e-commerce photography
- Professional retouching quality
- True-to-life color representation
- Visible stitching and fabric detail
- Magazine-quality product shot

The garment should appear as if floating on the white background, showing its natural drape and silhouette. Focus on capturing the quality and craftsmanship of the piece."""

    return prompt


def generate_filename(product: dict, output_dir: str = OUTPUT_DIR) -> str:
    """Generate a descriptive filename for the product image.

    Follows the product naming convention from Dave's feedback:
    - Use hyphens (retailer standard)
    - Format: product-name.png (clean, catalog-ready)
    - If file exists, append sequence number: product-name-2.png

    Args:
        product: Dictionary with product attributes
        output_dir: Directory to check for existing files

    Returns:
        Filename string (without extension)
    """
    name = product.get("name", "product")

    # Clean the name for filesystem (hyphens only, no underscores)
    clean_name = name.lower().replace(" ", "-").replace("_", "-")

    # Remove any characters that aren't alphanumeric or hyphens
    clean_name = "".join(c for c in clean_name if c.isalnum() or c == "-")

    # Remove double hyphens
    while "--" in clean_name:
        clean_name = clean_name.replace("--", "-")

    # Strip leading/trailing hyphens
    clean_name = clean_name.strip("-")

    # Check if file already exists, add sequence number if needed
    base_name = clean_name
    sequence = 1
    while os.path.exists(os.path.join(output_dir, f"{clean_name}.png")):
        sequence += 1
        clean_name = f"{base_name}-{sequence}"

    return clean_name


async def generate_product_image(
    product: dict,
    output_dir: str = OUTPUT_DIR,
    save_prompt: bool = True
) -> dict:
    """Generate a single product image using Gemini 3 Pro Image.

    Args:
        product: Dictionary with product attributes
        output_dir: Directory to save the image
        save_prompt: Whether to save the prompt alongside the image

    Returns:
        Dictionary with generation results
    """
    os.makedirs(output_dir, exist_ok=True)

    product_name = product.get("name", "unnamed-product")
    print(f"\n{'='*60}")
    print(f"Generating: {product_name}")
    print(f"{'='*60}")

    # Build the optimized prompt
    prompt = build_catalog_prompt(product)
    print(f"\nPrompt preview:\n{prompt[:200]}...")

    try:
        print(f"\nCalling {MODEL} with {ASPECT_RATIO} @ {RESOLUTION}...")
        client = genai.Client()

        response = client.models.generate_content(
            model=MODEL,
            contents=[prompt],
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE"],
                image_config=types.ImageConfig(
                    aspect_ratio=ASPECT_RATIO,
                    image_size=RESOLUTION,
                )
            )
        )

        # Extract image from response
        generated_image = None
        for part in response.parts:
            if part.inline_data:
                generated_image = part.as_image()
                break

        if generated_image is None:
            return {
                "status": "error",
                "product": product_name,
                "message": "No image generated. Try adjusting the prompt."
            }

        # Save the image
        filename = generate_filename(product, output_dir)
        image_path = os.path.join(output_dir, f"{filename}.png")
        generated_image.save(image_path)
        print(f"Saved: {image_path}")

        # Save the prompt for reference
        if save_prompt:
            prompt_path = os.path.join(output_dir, f"{filename}.txt")
            with open(prompt_path, "w") as f:
                f.write(f"Product: {json.dumps(product, indent=2)}\n\n")
                f.write(f"Generated Prompt:\n{prompt}\n")
            print(f"Prompt saved: {prompt_path}")

        return {
            "status": "success",
            "product": product_name,
            "image_path": image_path,
            "filename": f"{filename}.png",
            "prompt_used": prompt
        }

    except Exception as e:
        import traceback
        print(f"ERROR: {str(e)}")
        print(traceback.format_exc())
        return {
            "status": "error",
            "product": product_name,
            "message": str(e)
        }


async def generate_batch(
    products: list[dict],
    output_dir: str = OUTPUT_DIR
) -> list[dict]:
    """Generate images for multiple products with rate limiting.

    Args:
        products: List of product dictionaries
        output_dir: Directory to save images

    Returns:
        List of generation results
    """
    results = []
    total = len(products)

    print(f"\n{'#'*60}")
    print(f"# BATCH GENERATION: {total} products")
    print(f"# Output: {output_dir}")
    print(f"# Rate limit: {RATE_LIMIT_DELAY}s between generations")
    print(f"{'#'*60}")

    for i, product in enumerate(products, 1):
        print(f"\n[{i}/{total}] Processing...")

        result = await generate_product_image(product, output_dir)
        results.append(result)

        if result["status"] == "success":
            print(f"  SUCCESS: {result['filename']}")
        else:
            print(f"  FAILED: {result['message']}")

        # Rate limiting between generations
        if i < total:
            print(f"  Waiting {RATE_LIMIT_DELAY}s for rate limit...")
            await asyncio.sleep(RATE_LIMIT_DELAY)

    # Summary
    success = sum(1 for r in results if r["status"] == "success")
    failed = total - success

    print(f"\n{'='*60}")
    print("BATCH COMPLETE")
    print(f"{'='*60}")
    print(f"  Total: {total}")
    print(f"  Success: {success}")
    print(f"  Failed: {failed}")
    print(f"  Output: {output_dir}")

    return results


# Preset product definitions for common fashion categories
PRESET_PRODUCTS = {
    "dresses": [
        {
            "name": "floral-midi-wrap-dress",
            "category": "dress",
            "style": "midi wrap dress",
            "color": "pink and white",
            "fabric": "flowing chiffon",
            "pattern": "delicate floral print",
            "details": "v-neck, flutter sleeves, self-tie waist, tiered skirt",
            "occasion": "summer events and brunch"
        },
        {
            "name": "elegant-black-cocktail-dress",
            "category": "dress",
            "style": "fitted cocktail dress",
            "color": "classic black",
            "fabric": "stretch crepe",
            "details": "square neckline, cap sleeves, back zipper, knee-length",
            "occasion": "evening events and parties"
        },
        {
            "name": "blue-floral-maxi-dress",
            "category": "dress",
            "style": "tiered maxi dress",
            "color": "blue and yellow floral on white",
            "fabric": "lightweight cotton",
            "pattern": "botanical floral print",
            "details": "smocked bodice, spaghetti straps, three-tier skirt",
            "occasion": "vacation and resort wear"
        },
        {
            "name": "emerald-satin-slip-dress",
            "category": "dress",
            "style": "bias-cut slip dress",
            "color": "rich emerald green",
            "fabric": "luxurious satin",
            "details": "cowl neckline, adjustable straps, midi length, subtle sheen",
            "occasion": "formal dinners and date nights"
        },
        {
            "name": "rust-boho-peasant-dress",
            "category": "dress",
            "style": "bohemian peasant dress",
            "color": "warm rust orange",
            "fabric": "textured cotton gauze",
            "pattern": "subtle embroidered details",
            "details": "square neckline, balloon sleeves, smocked waist, midi length",
            "occasion": "festivals and casual outings"
        },
    ],
    "tops": [
        {
            "name": "white-classic-button-blouse",
            "category": "top",
            "style": "tailored button-down blouse",
            "color": "crisp white",
            "fabric": "cotton poplin",
            "details": "pointed collar, French cuffs, slightly relaxed fit",
            "occasion": "office and professional settings"
        },
        {
            "name": "sage-satin-camisole",
            "category": "top",
            "style": "drapey camisole",
            "color": "soft sage green",
            "fabric": "silky satin",
            "details": "cowl neckline, adjustable straps, relaxed fit",
            "occasion": "evening wear layering"
        },
        {
            "name": "navy-striped-breton-top",
            "category": "top",
            "style": "classic Breton striped top",
            "color": "navy and white stripes",
            "fabric": "soft cotton jersey",
            "pattern": "horizontal stripes",
            "details": "boat neckline, three-quarter sleeves, relaxed fit",
            "occasion": "casual everyday wear"
        },
        {
            "name": "blush-ruffle-peplum-blouse",
            "category": "top",
            "style": "feminine peplum blouse",
            "color": "blush pink",
            "fabric": "crepe de chine",
            "details": "ruffled v-neck, short sleeves, flared peplum hem",
            "occasion": "romantic dinners and special occasions"
        },
        {
            "name": "ivory-lace-crochet-top",
            "category": "top",
            "style": "bohemian crochet top",
            "color": "ivory cream",
            "fabric": "cotton crochet lace",
            "pattern": "intricate floral crochet",
            "details": "scalloped edges, short sleeves, relaxed fit",
            "occasion": "beach cover-up and summer festivals"
        },
    ],
    "pants": [
        {
            "name": "black-high-waist-trousers",
            "category": "pants",
            "style": "tailored wide-leg trousers",
            "color": "classic black",
            "fabric": "wool blend suiting",
            "details": "high waist, pleated front, wide straight leg, side pockets",
            "occasion": "office and professional wear"
        },
        {
            "name": "cream-linen-palazzo-pants",
            "category": "pants",
            "style": "flowing palazzo pants",
            "color": "natural cream",
            "fabric": "lightweight linen",
            "details": "elastic waist, ultra-wide leg, relaxed drape",
            "occasion": "resort and summer casual"
        },
        {
            "name": "olive-cargo-joggers",
            "category": "pants",
            "style": "modern cargo joggers",
            "color": "olive green",
            "fabric": "soft twill cotton",
            "details": "elastic waist, side cargo pockets, tapered ankle, drawstring hem",
            "occasion": "casual weekend wear"
        },
        {
            "name": "camel-pleated-culottes",
            "category": "pants",
            "style": "cropped pleated culottes",
            "color": "warm camel",
            "fabric": "flowy crepe",
            "details": "high waist, front pleats, wide cropped leg, back zip",
            "occasion": "smart casual and brunch"
        },
        {
            "name": "indigo-straight-leg-jeans",
            "category": "pants",
            "style": "classic straight-leg jeans",
            "color": "medium indigo wash",
            "fabric": "premium stretch denim",
            "details": "high waist, five-pocket styling, straight leg, subtle fading",
            "occasion": "everyday casual wear"
        },
    ],
    "outerwear": [
        {
            "name": "camel-wool-overcoat",
            "category": "outerwear",
            "style": "classic wool overcoat",
            "color": "camel tan",
            "fabric": "wool-cashmere blend",
            "details": "notched lapels, double-breasted, knee-length, side pockets",
            "occasion": "fall and winter professional wear"
        },
        {
            "name": "black-leather-moto-jacket",
            "category": "outerwear",
            "style": "motorcycle jacket",
            "color": "black",
            "fabric": "genuine leather",
            "details": "asymmetric zip, notched lapels, zip pockets, belted waist",
            "occasion": "edgy casual and evening looks"
        },
        {
            "name": "dusty-rose-blazer",
            "category": "outerwear",
            "style": "tailored single-button blazer",
            "color": "dusty rose pink",
            "fabric": "stretch suiting",
            "details": "notched lapels, single button, flap pockets, fitted silhouette",
            "occasion": "office and smart casual"
        },
    ],
    "skirts": [
        {
            "name": "black-pleated-midi-skirt",
            "category": "skirt",
            "style": "accordion pleated midi skirt",
            "color": "black",
            "fabric": "flowy chiffon",
            "details": "elastic waist, all-around pleats, midi length, lined",
            "occasion": "office to evening transition"
        },
        {
            "name": "denim-a-line-mini-skirt",
            "category": "skirt",
            "style": "classic A-line mini skirt",
            "color": "light blue wash",
            "fabric": "cotton denim",
            "details": "high waist, front button closure, side pockets, frayed hem",
            "occasion": "casual summer outings"
        },
        {
            "name": "leopard-print-pencil-skirt",
            "category": "skirt",
            "style": "fitted pencil skirt",
            "color": "brown and black leopard print",
            "fabric": "stretch ponte",
            "pattern": "classic leopard print",
            "details": "high waist, back zip, back vent, knee-length",
            "occasion": "bold office looks and nights out"
        },
    ],
}


def load_products_from_json(filepath: str) -> list[dict]:
    """Load product definitions from a JSON file.

    Args:
        filepath: Path to JSON file

    Returns:
        List of product dictionaries
    """
    with open(filepath, "r") as f:
        data = json.load(f)

    # Handle both array and object with "products" key
    if isinstance(data, list):
        return data
    elif isinstance(data, dict) and "products" in data:
        return data["products"]
    else:
        return [data]  # Single product


def main():
    """Main entry point for the product image generator."""
    parser = argparse.ArgumentParser(
        description="Generate catalog-quality product images for women's fashion",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate from JSON file
  python -m scripts.generate_product_images --input products.json

  # Generate single product from JSON string
  python -m scripts.generate_product_images --product '{"name": "red-maxi-dress", "category": "dress", "color": "crimson red"}'

  # Generate preset dresses
  python -m scripts.generate_product_images --preset dresses

  # Generate 3 random tops
  python -m scripts.generate_product_images --preset tops --count 3

  # List available presets
  python -m scripts.generate_product_images --list-presets
        """
    )

    parser.add_argument(
        "--input", "-i",
        type=str,
        help="Path to JSON file with product definitions"
    )

    parser.add_argument(
        "--product", "-p",
        type=str,
        help="Single product definition as JSON string"
    )

    parser.add_argument(
        "--preset",
        type=str,
        choices=list(PRESET_PRODUCTS.keys()),
        help="Use preset product definitions (dresses, tops, pants, outerwear, skirts)"
    )

    parser.add_argument(
        "--count", "-c",
        type=int,
        default=None,
        help="Number of products to generate from preset (default: all)"
    )

    parser.add_argument(
        "--output", "-o",
        type=str,
        default=OUTPUT_DIR,
        help=f"Output directory (default: {OUTPUT_DIR})"
    )

    parser.add_argument(
        "--list-presets",
        action="store_true",
        help="List all available preset products"
    )

    args = parser.parse_args()

    # List presets (no API key needed)
    if args.list_presets:
        print("\nAvailable Preset Products:")
        print("="*60)
        for category, products in PRESET_PRODUCTS.items():
            print(f"\n{category.upper()} ({len(products)} items):")
            for p in products:
                print(f"  - {p['name']}: {p.get('color', '')} {p.get('style', '')}")
        print()
        return

    # Check for API key (only when generating)
    if not os.environ.get("GOOGLE_API_KEY") and not os.environ.get("GOOGLE_GENAI_USE_VERTEXAI"):
        print("ERROR: GOOGLE_API_KEY environment variable is not set.")
        print("Please set it before running this script:")
        print("  export GOOGLE_API_KEY='your-api-key'")
        print("\nOr use Vertex AI:")
        print("  export GOOGLE_GENAI_USE_VERTEXAI=True")
        print("  export GOOGLE_CLOUD_PROJECT='your-project'")
        sys.exit(1)

    # Determine products to generate
    products = []

    if args.input:
        if not os.path.exists(args.input):
            print(f"ERROR: Input file not found: {args.input}")
            sys.exit(1)
        products = load_products_from_json(args.input)
        print(f"Loaded {len(products)} products from {args.input}")

    elif args.product:
        try:
            product = json.loads(args.product)
            products = [product]
            print(f"Using single product: {product.get('name', 'unnamed')}")
        except json.JSONDecodeError as e:
            print(f"ERROR: Invalid JSON in --product: {e}")
            sys.exit(1)

    elif args.preset:
        preset_products = PRESET_PRODUCTS.get(args.preset, [])
        if args.count:
            products = preset_products[:args.count]
        else:
            products = preset_products
        print(f"Using {len(products)} products from '{args.preset}' preset")

    else:
        parser.print_help()
        print("\nERROR: Please specify --input, --product, or --preset")
        sys.exit(1)

    if not products:
        print("ERROR: No products to generate")
        sys.exit(1)

    # Run generation
    print(f"\nStarting generation of {len(products)} product image(s)...")
    print(f"Model: {MODEL}")
    print(f"Aspect Ratio: {ASPECT_RATIO}")
    print(f"Resolution: {RESOLUTION}")
    print(f"Output: {args.output}")

    results = asyncio.run(generate_batch(products, args.output))

    # Exit with error code if any failed
    if any(r["status"] == "error" for r in results):
        sys.exit(1)


if __name__ == "__main__":
    main()
