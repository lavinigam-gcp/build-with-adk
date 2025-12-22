# Ad Campaign Agent - Demo Guide

A complete walkthrough for demonstrating the Ad Campaign Agent platform.

## Executive Journey

![Executive Journey](assets/executive-journey.jpeg)

## Overview

This demo showcases an **AI-powered in-store retail media platform** built with Google's Agent Development Kit (ADK). The system demonstrates how multi-agent AI can transform retail advertising from creative ideation to performance optimization.

**Key Value Propositions:**

- **10x faster creative production** - Generate video variations in minutes, not weeks
- **Human-in-the-Loop (HITL) control** - AI assists, humans approve
- **Data-driven optimization** - Apply winning formulas across campaigns
- **Geographic intelligence** - Store-level performance with Google Maps integration

## Demo Duration

| Version | Time | Notes |
|---------|------|-------|
| Full Demo | 20-25 min | All 6 acts |
| Core Demo | 15 min | Skip optional scenes |
| Quick Overview | 5 min | Acts 1 + 4 only |

**Audience:** Retail Media Executives, Marketing Leaders, Technical Decision Makers

---

## The Story

> *"You're the Director of Retail Media for a fashion retailer with stores across the US. Holiday season is approaching, and you need to launch personalized video campaigns for each store location - but your creative team is overwhelmed. Let's see how AI agents can help..."*

---

## Pre-Demo Checklist

- [ ] ADK Web UI running (`adk web app` or Cloud Run URL)
- [ ] Product images available in GCS at `product-images/`
- [ ] `GOOGLE_MAPS_API_KEY` set (for static maps)
- [ ] Test one video generation to warm up models
- [ ] Clear browser cache for artifact viewing

---

## Act 1: Understanding the Platform (2 min)

### Scene 1.1: Meet the Multi-Agent System

**Query:**

```text
What agents are available and what are our current campaigns?
```

**What to Highlight:**

- Coordinator routes to 4 specialized agents
- Product-centric model: Each campaign = 1 product + 1 store
- Pre-loaded with 4 demo campaigns

---

### Scene 1.2: Browse the Product Catalog

**Query:**

```text
Show me all available products with their image links
```

**What to Highlight:**

- 22 products across 5 categories
- Clickable `image_url` links to view products
- Each product ready for video generation

---

## Act 2: Creative Generation with AI (5-6 min)

### Scene 2.1: Explore Variation Options

**Query:**

```text
What variation presets do I have for video generation?
```

**What to Highlight:**

- Diversity presets (model ethnicities)
- Setting presets (studio, beach, urban, cafe, etc.)
- Mood presets (elegant, romantic, bold, playful)
- These enable A/B testing

---

### Scene 2.2: Generate a Video

**Query (Use existing campaign):**

```text
Generate a video for campaign 2 with a European model on a rooftop at sunset, with a sophisticated elegant mood
```

**Query (Create new campaign):**

```text
Create a campaign for the sage-satin-camisole at our Miami Beach store, then generate a video with a Latina model on a beach at golden-hour, romantic serene mood
```

**What to Highlight:**

- **Two-stage pipeline**:
  1. Stage 1: Gemini generates scene image
  2. Stage 2: Veo 3.1 animates into 8-second video
- Video starts in "generated" status (pending review)

**Demo Tip:** While generating (~2-3 min), explain:

> "The AI first creates a scene image showing a model wearing our product, then animates it into a cinematic video."

---

### Scene 2.3: Batch Generate Variations

**Query:**

```text
Generate three video variations for campaign 2:
1. African model in studio with dramatic lighting, bold energy
2. Asian model in cafe setting, warm sophisticated mood
3. European model walking in urban street at day, dynamic energy
```

**What to Highlight:**

- Batch generation for efficiency
- Each variation named descriptively
- All pending review before going live

---

### Variation Parameters Reference

| Category | Options |
|----------|---------|
| Model | asian, european, african, latina, south-asian, middle-eastern, diverse |
| Setting | studio, beach, urban, cafe, rooftop, garden, nature, office, street |
| Mood | elegant, romantic, bold, playful, sophisticated, mysterious, serene |
| Lighting | natural, studio, dramatic, soft, golden, neon, moody |
| Time | golden-hour, sunrise, day, sunset, dusk, night |
| Activity | walking, standing, sitting, dancing, spinning, posing, running |
| Camera | orbit, pan, dolly, static, tracking, crane, handheld |

---

## Act 3: Human-in-the-Loop Review (4-5 min)

### Scene 3.1: The Review Table

**Query:**

```text
Show me the video review table with public links
```

**What to Highlight:**

- Card-based format with full details
- **Clickable WATCH VIDEO links** for preview
- Emphasize: "Nothing goes live without human approval"

---

### Scene 3.2: Batch Activation

**Query:**

```text
Activate videos 5 and 7
```

**What to Highlight:**

- Batch activation with `activate_batch([5, 7])`
- Status changes to "activated"
- **30 days of metrics generated** on activation
- Metrics only start after human approval

---

### Scene 3.3: Pause and Archive (Optional)

**Query:**

```text
Pause video 6 temporarily
Archive video 8
```

**What to Highlight:**

- Full lifecycle control: generated -> activated -> paused -> archived
- Paused videos preserve metrics history

---

## Act 4: Analytics & Optimization (4-5 min)

### Scene 4.1: Campaign Metrics

**Query:**

```text
Get metrics for campaign 2 over the last 30 days
```

**What to Highlight:**

- **In-store retail media metrics** (not digital):
  - Impressions: Ad displays on in-store screens
  - Dwell Time: Seconds shoppers viewed the ad
  - Circulation: Foot traffic past display
  - **RPI (Revenue Per Impression)**: Primary KPI
- Weekend patterns visible (40% higher)

---

### Scene 4.2: Generate Charts

**Query:**

```text
Generate a trendline chart showing revenue per impression for campaign 2 over 30 days
```

**Alternative Queries:**

```text
Create a bar chart of weekly impressions for campaign 3
Generate a comparison KPI card for campaign 1
Create an infographic visualization of campaign 2 performance
```

**What to Highlight:**

- AI-generated charts using Gemini
- Anti-hallucination: Uses ONLY real data
- Saved as artifact for download

---

### Scene 4.3: Compare Campaigns

**Query:**

```text
Compare all four campaigns side by side
```

**What to Highlight:**

- Side-by-side metrics comparison
- Rankings by RPI and total revenue
- Identifies winner with explanation

---

## Act 5: Geographic Intelligence (3-4 min)

### Scene 5.1: Campaign Map

**Query:**

```text
Show me all campaign locations with Google Maps links
```

**What to Highlight:**

- Clickable Google Maps URLs for each store
- Performance metrics per location

---

### Scene 5.2: Generate Map Visualization

**Query:**

```text
Generate a performance map showing all campaigns on a US map in infographic style
```

**What to Highlight:**

- AI-generated infographic using Gemini
- Revenue bubbles sized by performance
- Regional summary panel

---

### Scene 5.3: Regional Comparison

**Query:**

```text
Generate a regional comparison map showing West Coast vs East Coast RPI
```

---

## Act 6: Apply Winning Formula (2 min)

### Scene 6.1: Scale Success

**Query:**

```text
Apply the winning formula from video 5 to campaign 3
```

**What to Highlight:**

- Extracts winning characteristics: mood, setting, lighting, camera
- Applies to different product at different location
- New video generated with proven approach

---

## Closing: Value Summary

**Key Points:**

1. **Multi-Agent Collaboration** - 4 specialized agents working together
2. **Product-Centric Campaigns** - Clear attribution per product per store
3. **Creative at Scale** - Multiple video variations with AI
4. **Human Control** - HITL review and approval
5. **In-Store Analytics** - Retail-appropriate metrics
6. **Geographic Intelligence** - Google Maps integration
7. **Data-Driven Optimization** - Apply winning formulas

---

## Quick Reference: Demo Queries

### Campaign Management

```text
List all campaigns
Show me campaign 2 details
Create a campaign for the sage-satin-camisole at our Miami Beach store
What campaigns are in draft status?
```

### Product Browsing

```text
Show me all available products with their image links
List products in the dress category
Show me outerwear products with URLs
```

### Video Generation

```text
What variation presets are available?
Generate a video for campaign 2 with a European model on a rooftop at sunset
Generate 3 variations for campaign 3 with different settings
```

### HITL Review

```text
Show me the video review table with public links
Activate videos 5 and 7
Pause video 6
What's the status of video 5?
```

### Analytics

```text
Get metrics for campaign 2 over the last 30 days
Top 5 videos by RPI
Compare campaigns 1, 2, 3, 4
Generate a trendline chart for campaign 1
```

### Maps

```text
Show me all campaign locations with Google Maps links
Generate a performance map showing all campaigns
Generate a regional comparison map
```

### Optimization

```text
Apply winning formula from video 5 to campaign 3
Get video properties for video 5
```

---

## Campaign Reference (Pre-loaded)

| ID | Product | Store | City |
|----|---------|-------|------|
| 1 | Blue Floral Maxi Dress | Westfield Century City | Los Angeles, CA |
| 2 | Elegant Black Cocktail Dress | Bloomingdale's 59th Street | New York, NY |
| 3 | Black High Waist Trousers | Water Tower Place | Chicago, IL |
| 4 | Emerald Satin Slip Dress | The Grove | Los Angeles, CA |

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "No metrics" for campaign | Videos must be activated first |
| Video generation slow | Normal - Veo 3.1 takes 2-3 minutes |
| Chart not showing data | Check that campaign has activated videos |
| Static map API error | Set `GOOGLE_MAPS_API_KEY` or use AI-generated map |
| Video links show gs:// URLs | Add "with public links" to query |

---

## Models Used

| Purpose | Model |
|---------|-------|
| All Agents | `gemini-2.5-pro` |
| Scene Images | `gemini-2.5-flash-image` |
| Video Animation | `veo-3.1-generate-preview` |
| Charts/Maps | `gemini-2.5-flash-image` |

---

## Environment Variables

| Variable | Purpose | Required |
|----------|---------|----------|
| `GOOGLE_CLOUD_PROJECT` | GCP project | Yes |
| `GCS_BUCKET` | Cloud Storage bucket | Yes |
| `GOOGLE_MAPS_API_KEY` | Static Maps API | Optional |
