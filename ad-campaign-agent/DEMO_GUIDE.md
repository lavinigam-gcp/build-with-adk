# Ad Campaign Agent - Demo Query Journeys

This document contains complete user journeys for demonstrating the Ad Campaign Agent. Each journey is a multi-step conversation that showcases different capabilities from basic to advanced.

## Pre-loaded Demo Data Reference

Before running demos, note the pre-loaded data:

| Campaign | ID | Location | Category | Status |
|----------|-----|----------|----------|--------|
| Summer Blooms 2025 | 1 | Los Angeles, CA | Summer | Active |
| Evening Elegance Collection | 2 | New York, NY | Formal | Active |
| Urban Professional | 3 | Chicago, IL | Professional | Active |
| Fall Essentials | 4 | Seattle, WA | Essentials | Draft |

**Available Seed Images:** `dress_summer_dress_004.jpg`, `dress_formal_dress_002.jpg`, `dress_formal_dress_003.jpg`, `top_blouse_002.jpg`, `top_blouse_003.jpg`, `top_blouse_004.jpg`, `top_sweater_003.jpg`

---

## Journey 1: Quick Campaign Overview (Basic - 3 steps)

**Persona:** Executive wanting a quick status update
**Duration:** ~2 minutes
**Agents Used:** Campaign Agent, Analytics Agent

### Step 1: Get the big picture
```
Query: "Show me all our active ad campaigns"
```
**Expected Response:**
- List of 3 active campaigns (Summer Blooms, Evening Elegance, Urban Professional)
- Each showing: name, location, category, status
- Note about 1 draft campaign (Fall Essentials)

### Step 2: Check overall performance
```
Query: "How are they performing? Which one is doing best?"
```
**Expected Response:**
- Comparison of all 3 active campaigns
- Metrics: impressions, revenue, engagement rate
- Clear winner identified (likely Summer Blooms or Evening Elegance based on mock data)
- Revenue ranking

### Step 3: Get quick insights
```
Query: "Why is [top performer] doing so well? Give me the key insights."
```
**Expected Response:**
- Performance trend (improving/stable/declining)
- Key characteristics of top-performing ads (mood, setting, style)
- Actionable recommendations
- Best performing day highlighted

---

## Journey 2: New Campaign Creation to Video Ad (End-to-End - 6 steps)

**Persona:** Campaign Manager launching a new campaign
**Duration:** ~10 minutes (includes video generation wait)
**Agents Used:** Campaign Agent, Media Agent

### Step 1: Create new campaign
```
Query: "I want to create a new campaign called 'Holiday Sparkle' for our Miami stores.
It's for our holiday party dress collection."
```
**Expected Response:**
- New campaign created with ID (likely 5)
- Confirmation: name, category (formal), location (Miami, FL), status (draft)

### Step 2: Browse available images
```
Query: "What seed images do we have available for this campaign?"
```
**Expected Response:**
- List of 7+ available images in selected/ folder
- Each with filename and brief description
- Suggestions for formal/party wear images

### Step 3: Add a seed image
```
Query: "Add the formal red dress image to my Holiday Sparkle campaign"
```
**Expected Response:**
- Image added: dress_formal_dress_002.jpg
- Image analyzed automatically
- Metadata extracted: garment type, colors, mood, setting

### Step 4: Review image analysis
```
Query: "Tell me more about this image - what did the AI detect?"
```
**Expected Response:**
- Detailed metadata breakdown:
  - Model description
  - Clothing description (red floral fitted gown)
  - Setting description
  - Mood (elegant, sophisticated)
  - Key features
  - Suggested video prompt elements

### Step 5: Generate video ad
```
Query: "Generate a video ad for this campaign using this image. Make it 6 seconds."
```
**Expected Response:**
- Video generation started (wait 2-5 minutes)
- Prompt used shown (auto-generated from metadata)
- Video saved to generated/ folder
- Saved as ADK artifact (viewable in UI)
- Mock metrics auto-generated (90 days)

### Step 6: Activate campaign
```
Query: "The video looks great! Activate this campaign."
```
**Expected Response:**
- Campaign status updated from 'draft' to 'active'
- Confirmation of activation
- Summary of campaign assets (1 image, 1 video ad)

---

## Journey 3: Performance Analysis & Optimization (Intermediate - 5 steps)

**Persona:** Marketing Analyst optimizing campaign performance
**Duration:** ~5 minutes
**Agents Used:** Analytics Agent, Media Agent

### Step 1: Compare all campaigns
```
Query: "Compare the performance of all our campaigns side by side"
```
**Expected Response:**
- Table/comparison of all campaigns
- Metrics per campaign: impressions, views, clicks, revenue
- Engagement rates compared
- Rankings by revenue and engagement
- Best performer highlighted

### Step 2: Find top performing ads
```
Query: "What are our top 5 best performing video ads by revenue?"
```
**Expected Response:**
- Ranked list of top 5 ads
- For each ad:
  - Campaign name and location
  - Total revenue generated
  - Key characteristics (mood, setting, garment)
  - Source image used
- Common traits among top performers identified

### Step 3: Deep dive on winner
```
Query: "Give me detailed insights on the #1 performing ad. What makes it work?"
```
**Expected Response:**
- Full ad details
- Image metadata breakdown
- Prompt that was used
- Performance metrics over time
- AI analysis of success factors:
  - Mood resonates with audience
  - Setting matches brand
  - Camera style creates engagement
- Specific recommendations

### Step 4: Apply winning formula
```
Query: "Apply the winning formula from our top ad to the Urban Professional campaign in Chicago"
```
**Expected Response:**
- Winning characteristics extracted:
  - Mood, setting, camera style from top performer
- New video generated for Urban Professional
- Same successful elements, different product
- Video saved as artifact
- Comparison of applied formula

### Step 5: Verify improvement potential
```
Query: "Show me metrics for Urban Professional before and after. Create a comparison chart."
```
**Expected Response:**
- Metrics visualization generated
- Chart showing campaign performance
- Note: New video just created, metrics will accumulate
- Projection based on winning formula success rate

---

## Journey 4: Geographic Strategy & Visualization (Intermediate - 6 steps)

**Persona:** Director of Retail Media Networks
**Duration:** ~5 minutes
**Agents Used:** Campaign Agent, Analytics Agent

### Step 1: Get geographic overview
```
Query: "Show me where all our campaigns are located"
```
**Expected Response:**
- List of 4 campaigns with locations:
  - Los Angeles, CA
  - New York, NY
  - Chicago, IL
  - Seattle, WA
- Coordinates for each (geocoded)
- Map visualization URL

### Step 2: Generate performance map
```
Query: "Create a map visualization showing campaign performance by location"
```
**Expected Response:**
- Map image generated (saved as artifact)
- US map with campaign markers
- Bubble sizes representing revenue
- Color coding by status
- Legend and summary stats

### Step 3: Regional comparison
```
Query: "How does the West Coast compare to East Coast in terms of performance?"
```
**Expected Response:**
- Regional breakdown:
  - West Coast (LA, Seattle): combined metrics
  - East Coast (NYC): metrics
  - Midwest (Chicago): metrics
- Revenue per region
- Engagement differences
- Style preferences by region

### Step 4: Explore local market
```
Query: "What fashion stores are near our LA campaign location? Any competitors?"
```
**Expected Response:**
- Nearby stores search results
- List of fashion retailers within 5km
- Store names, ratings, addresses
- Competitive landscape insight

### Step 5: Get demographics
```
Query: "What are the demographics and fashion preferences in Los Angeles?"
```
**Expected Response:**
- LA demographic data:
  - Population: ~3.9M
  - Median age: 35
  - Median income: $65K
  - Fashion market index: 92/100
- Style preferences: casual, athleisure, bohemian
- Market insight summary

### Step 6: Create market opportunity map
```
Query: "Generate a market opportunity visualization showing where we should expand"
```
**Expected Response:**
- Market opportunity map generated
- Current locations marked
- Opportunity scores by market
- Expansion recommendations
- Underserved regions highlighted

---

## Journey 5: Creative Iteration & A/B Testing (Advanced - 7 steps)

**Persona:** Creative Director testing ad variations
**Duration:** ~15 minutes (includes multiple video generations)
**Agents Used:** Media Agent, Analytics Agent

### Step 1: Review existing ads
```
Query: "Show me all video ads for the Summer Blooms campaign"
```
**Expected Response:**
- List of ads for campaign 1
- Each ad showing:
  - Video filename
  - Duration
  - Prompt used
  - Source image
  - Status
  - Creation date

### Step 2: Analyze top performer
```
Query: "Which of these ads is performing best and what's its style?"
```
**Expected Response:**
- Top performing ad identified
- Revenue and engagement metrics
- Style analysis:
  - Mood (e.g., "dreamy, romantic")
  - Setting (e.g., "outdoor field")
  - Camera style (e.g., "slowly pans")
  - Key feature highlighted

### Step 3: Create setting variation
```
Query: "Generate a variation of the top ad but change the setting to something more urban"
```
**Expected Response:**
- Video variation generated
- Variation type: setting
- New setting applied (e.g., "luxurious urban rooftop")
- Original elements preserved
- Video saved as artifact

### Step 4: Create mood variation
```
Query: "Now create another variation with a more energetic, vibrant mood"
```
**Expected Response:**
- Second variation generated
- Variation type: mood
- New mood: "energetic, vibrant, youthful"
- Same product/setting as original
- Video saved as artifact

### Step 5: Create camera style variation
```
Query: "One more - try a dramatic low angle camera sweep"
```
**Expected Response:**
- Third variation generated
- Variation type: angle
- New camera: "dramatically sweeps from low angle upward"
- Cinematic effect applied
- Video saved as artifact

### Step 6: Compare all versions
```
Query: "Show me all the variations we just created and their prompts"
```
**Expected Response:**
- List of all Summer Blooms ads
- Original vs. 3 new variations
- Side-by-side prompt comparison
- Highlighted differences in each

### Step 7: Predict performance
```
Query: "Based on our historical data, which variation do you think will perform best?"
```
**Expected Response:**
- AI analysis of variations
- Comparison to past top performers
- Prediction based on:
  - Similar mood/setting success rates
  - Engagement patterns
  - Audience preferences
- Recommendation for A/B test priority

---

## Journey 6: Full Executive Demo (Comprehensive - 10 steps)

**Persona:** Demonstrating full platform capabilities to stakeholders
**Duration:** ~20 minutes
**Agents Used:** All three agents

### Step 1: Introduction
```
Query: "Give me an overview of our ad campaign management system and what campaigns we're running"
```
**Expected Response:**
- System overview (multi-agent architecture)
- 4 campaigns listed with status
- Quick metrics summary
- Capabilities overview

### Step 2: Deep dive on top performer
```
Query: "Tell me about our best performing campaign in detail"
```
**Expected Response:**
- Top campaign identified
- Full details: name, location, category
- Total revenue, impressions, engagement
- Number of ads and images
- Performance trend

### Step 3: View the creative
```
Query: "Show me the images and videos for this campaign"
```
**Expected Response:**
- List of seed images with descriptions
- List of video ads with details
- Prompts used for generation
- Artifacts available in UI

### Step 4: Live video generation
```
Query: "Generate a new video ad for this campaign using a different image. Use the blouse image."
```
**Expected Response:**
- New video generation initiated
- Different seed image selected
- Auto-generated prompt from image analysis
- Video created and saved (wait 2-5 mins)
- Artifact viewable

### Step 5: Instant metrics
```
Query: "Now show me the performance metrics with a trend chart"
```
**Expected Response:**
- Campaign metrics summary
- 30-day performance data
- Trend visualization generated
- Chart saved as artifact
- Trend analysis (up/down/stable)

### Step 6: AI insights
```
Query: "What insights can you give me about what's working and what's not?"
```
**Expected Response:**
- AI-generated insights:
  - Success factors identified
  - Underperforming elements
  - Recommendations for improvement
  - Best/worst performing days
- Actionable suggestions

### Step 7: Cross-campaign comparison
```
Query: "Compare this to our other campaigns. Create an infographic."
```
**Expected Response:**
- Multi-campaign comparison
- Metrics table
- Infographic visualization generated
- Key differences highlighted
- Winner identified

### Step 8: Scale success
```
Query: "Take what's working from our top campaign and apply it to the Fall Essentials campaign in Seattle"
```
**Expected Response:**
- Fall Essentials identified (draft status)
- Winning formula extracted
- Applied characteristics listed
- New video generated
- Campaign optionally activated

### Step 9: Geographic visualization
```
Query: "Show me all our campaigns on a map with their performance"
```
**Expected Response:**
- Map visualization generated
- All 4+ campaigns plotted
- Revenue bubbles
- Regional performance summary
- Expansion opportunities

### Step 10: Summary and recommendations
```
Query: "Summarize what we should focus on next and any recommendations"
```
**Expected Response:**
- Executive summary:
  - Top performing: [campaign name]
  - Key success factors
  - Underperforming areas
- Recommendations:
  - Apply winning formula to X
  - Expand to Y region
  - Test Z variation type
- Next steps

---

## Journey 7: Image-First Creative Workflow (Advanced - 6 steps)

**Persona:** Creative team starting from scratch
**Duration:** ~12 minutes
**Agents Used:** Media Agent, Campaign Agent

### Step 1: Generate new seed image
```
Query: "Generate a new fashion image for a winter coat campaign.
I want a model in a stylish wool peacoat, outdoor snowy city setting, elegant and sophisticated mood."
```
**Expected Response:**
- AI image generation initiated
- Prompt processed
- Image created with Gemini 3 Pro Image
- Saved to selected/ folder
- Saved as artifact
- Auto-analyzed for metadata

### Step 2: Review generated image
```
Query: "Describe the image you just created in detail"
```
**Expected Response:**
- Full image analysis:
  - Model description
  - Clothing details (wool peacoat, colors)
  - Setting (snowy city street)
  - Mood (elegant, sophisticated)
  - Suggested video elements
- Metadata stored

### Step 3: Create campaign for it
```
Query: "Create a new campaign called 'Winter Elegance' for Boston and add this image to it"
```
**Expected Response:**
- New campaign created (Boston, MA)
- Category: essentials/winter
- Status: draft
- Generated image added to campaign
- Ready for video generation

### Step 4: Generate video
```
Query: "Generate an 8-second cinematic video ad from this image"
```
**Expected Response:**
- Video generation started
- Prompt auto-generated from image metadata
- 8-second duration set
- Veo 3.1 processing
- Video saved and artifact created
- Mock metrics generated

### Step 5: Generate a second image variation
```
Query: "Generate another image with the same coat but in an indoor luxury hotel lobby setting"
```
**Expected Response:**
- Second image generated
- Same style coat
- New setting: luxury hotel lobby
- Contrasting mood
- Added to same campaign
- Analyzed and stored

### Step 6: Create second video for A/B test
```
Query: "Create a video from this new image too so we can A/B test the settings"
```
**Expected Response:**
- Second video generated
- Different prompt (hotel lobby setting)
- Same campaign, two creative directions
- Both videos available as artifacts
- Ready for performance comparison

---

## Journey 8: Property-Controlled Video Generation (Advanced - 5 steps)

**Persona:** Creative Director fine-tuning video style
**Duration:** ~12 minutes
**Agents Used:** Media Agent, Analytics Agent

### Step 1: View existing video properties
```
Query: "Show me the video properties for ad 21"
```
**Expected Response:**
- Full video properties breakdown:
  - Mood: romantic/warm/playful/etc.
  - Energy level: calm/moderate/dynamic
  - Visual style: cinematic/editorial/commercial
  - Color temperature: warm/neutral/cool
  - Camera movement: orbit/pan/static
  - Dominant colors: ["pink", "white", "green"]
  - Setting type: outdoor/studio/urban
  - Lighting style: natural/studio/dramatic

### Step 2: Generate video with specific properties
```
Query: "Generate a quirky, high-energy video with warm colors for campaign 1"
```
**Expected Response:**
- Video generation started with property overrides
- Properties applied: mood=quirky, energy_level=high_energy, color_temperature=warm
- Templated prompt built from properties
- Video generated and analyzed
- Extracted properties shown for verification

### Step 3: Try different property combinations
```
Query: "Generate a serene, calm video with cool colors and dramatic lighting for campaign 3"
```
**Expected Response:**
- Video generated with:
  - mood: serene
  - energy_level: calm
  - color_temperature: cool
  - lighting_style: dramatic
- Auto-analysis confirms properties match request
- Saved as artifact

### Step 4: Compare properties across ads
```
Query: "Show the video properties for all ads in campaign 1 and compare them"
```
**Expected Response:**
- List of all campaign 1 ads with properties
- Side-by-side comparison:
  - Mood distribution
  - Energy level patterns
  - Color temperature trends
- Insights on which combinations perform best

### Step 5: Apply properties from top performer
```
Query: "Apply the video properties from our top performer to campaign 4"
```
**Expected Response:**
- Top performer identified with its video_properties
- Properties extracted: mood, visual_style, energy_level, color_temperature, lighting_style
- New video generated for campaign 4 using these properties
- Winning formula applied with precision control

---

## Quick Reference: Single-Purpose Queries

For quick demos of specific features:

### Campaign Management
```
"List all campaigns"
"Create a campaign called X for Y location"
"Update campaign X to active status"
"What campaigns are in draft status?"
```

### Media Generation
```
"List available seed images"
"Add [image_name] to campaign [X]"
"Analyze the image for campaign [X]"
"Generate a video ad for campaign [X]"
"Generate an 8-second video with custom prompt: [prompt]"
"Create a setting variation of ad [X]"
```

### Property-Controlled Video Generation
```
"Generate a quirky, high-energy video with warm colors for campaign [X]"
"Generate a video for campaign [X] with mood serene and energy level calm"
"Create a bold, cinematic video with dramatic lighting for campaign [X]"
"Generate a playful video with cool color temperature for campaign [X]"
```

### Video Properties
```
"Get video properties for ad [X]"
"Show video properties for all ads in campaign [X]"
"What are the properties of our top performing videos?"
"Compare video properties across our best ads"
```

### Analytics
```
"Get metrics for campaign [X]"
"What are the top 5 ads by revenue?"
"Compare campaigns [X] and [Y]"
"Give me insights for campaign [X]"
"Generate a trendline chart for campaign [X]"
"Create a bar chart of weekly revenue"
```

### Location Features
```
"Get all campaign locations"
"Search for fashion stores near [city]"
"What are the demographics for [city]?"
"Generate a performance map"
"Show regional comparison"
```

### Advanced
```
"Apply the winning formula from the top ad to campaign [X]"
"Generate 3 variations of ad [X] with different moods"
"What characteristics do our top performers share?"
"Create a market opportunity visualization"
```

---

## Demo Tips

1. **Wait for video generation**: Veo 3.1 takes 2-5 minutes. Use this time to explain the process or show other features.

2. **Check artifacts**: After generating videos/images/charts, remind viewers they can see them in the ADK Web UI artifacts panel.

3. **Use natural language**: The agent understands context. You don't need exact command syntax.

4. **Build on previous responses**: Reference "the top performer" or "that campaign" - the agent maintains context.

5. **Show the handoff**: Point out when the coordinator delegates to specialized agents.

6. **Highlight the data**: All mock metrics are realistic with 90 days of history per campaign.

7. **Video properties are auto-extracted**: Every video is automatically analyzed after generation to extract mood, energy, style, and 25+ other properties. Show this by asking "Get video properties for ad X" after generating.

8. **Property-controlled generation**: Demonstrate fine-grained control by requesting specific mood (quirky, warm, bold), energy (calm, dynamic), colors (warm, cool), and lighting (dramatic, natural). The system builds templated prompts from these properties.
