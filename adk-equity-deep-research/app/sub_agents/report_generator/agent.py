# Copyright 2025 Google LLC
# Licensed under the Apache License, Version 2.0

"""HTML report generator agent."""

from google.adk.agents import LlmAgent
from app.config import MODEL, CURRENT_DATE
from app.callbacks import save_html_report_callback

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Equity Research Report</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            background: #f5f7fa;
        }}
        .report {{
            max-width: 1100px;
            margin: 0 auto;
            background: white;
            box-shadow: 0 0 40px rgba(0,0,0,0.1);
        }}

        /* Header */
        .header {{
            background: linear-gradient(135deg, #1a237e 0%, #0d47a1 100%);
            color: white;
            padding: 40px 50px;
        }}
        .header h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
        }}
        .header .ticker {{
            font-size: 1.4em;
            opacity: 0.9;
            margin-bottom: 15px;
        }}
        .header .meta {{
            display: flex;
            gap: 30px;
            font-size: 0.95em;
            opacity: 0.8;
        }}
        .rating-badge {{
            display: inline-block;
            padding: 8px 20px;
            border-radius: 20px;
            font-weight: bold;
            margin-top: 15px;
        }}
        .rating-buy {{ background: #4caf50; }}
        .rating-hold {{ background: #ff9800; }}
        .rating-sell {{ background: #f44336; }}

        /* Sections */
        .section {{
            padding: 40px 50px;
            border-bottom: 1px solid #e0e0e0;
        }}
        .section:last-child {{ border-bottom: none; }}
        .section h2 {{
            color: #1a237e;
            font-size: 1.6em;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 3px solid #1a237e;
            display: inline-block;
        }}
        .section p {{
            margin-bottom: 15px;
            text-align: justify;
        }}

        /* Key Metrics Grid */
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 25px 0;
        }}
        .metric-card {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 25px;
            border-radius: 10px;
            text-align: center;
        }}
        .metric-card .value {{
            font-size: 2em;
            font-weight: bold;
        }}
        .metric-card .label {{
            font-size: 0.9em;
            opacity: 0.9;
            margin-top: 5px;
        }}

        /* Charts */
        .chart-container {{
            background: #fafafa;
            border-radius: 10px;
            padding: 25px;
            margin: 25px 0;
            text-align: center;
        }}
        .chart-container img {{
            max-width: 100%;
            border-radius: 8px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }}
        .chart-title {{
            font-size: 1.1em;
            color: #555;
            margin-bottom: 15px;
        }}

        /* Visual Contextualization - Setup → Visual → Interpretation */
        .visual-context {{
            margin: 30px 0;
            padding: 20px;
            background: #fafafa;
            border-radius: 12px;
            border-left: 4px solid #1a237e;
        }}
        .visual-context .setup-text {{
            color: #333;
            font-size: 1.05em;
            line-height: 1.7;
            margin-bottom: 20px;
            padding: 15px 20px;
            background: white;
            border-radius: 8px;
            font-style: italic;
        }}
        .visual-context .interpretation-text {{
            color: #1a237e;
            font-size: 1.05em;
            line-height: 1.7;
            margin-top: 20px;
            padding: 15px 20px;
            background: #e8eaf6;
            border-radius: 8px;
            font-weight: 500;
        }}

        /* Tables */
        .data-table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        .data-table th, .data-table td {{
            padding: 12px 15px;
            text-align: left;
            border-bottom: 1px solid #e0e0e0;
        }}
        .data-table th {{
            background: #f5f5f5;
            font-weight: 600;
            color: #333;
        }}
        .data-table tr:hover {{ background: #fafafa; }}

        /* Risk List */
        .risk-list {{
            list-style: none;
        }}
        .risk-list li {{
            padding: 12px 15px;
            margin: 10px 0;
            background: #fff3e0;
            border-left: 4px solid #ff9800;
            border-radius: 0 8px 8px 0;
        }}

        /* Infographics */
        .infographic-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
            gap: 25px;
            margin: 25px 0;
        }}
        .infographic-card {{
            background: white;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 4px 20px rgba(0,0,0,0.1);
            transition: transform 0.3s ease;
        }}
        .infographic-card:hover {{
            transform: translateY(-5px);
        }}
        .infographic-card img {{
            width: 100%;
            height: auto;
            display: block;
        }}
        .infographic-card .infographic-title {{
            padding: 15px 20px;
            background: linear-gradient(135deg, #00b4d8 0%, #0077b6 100%);
            color: white;
            font-weight: 600;
            text-align: center;
        }}

        /* Data Tables Enhanced */
        .data-section {{
            background: #f8f9fa;
            border-radius: 10px;
            padding: 25px;
            margin: 20px 0;
        }}
        .data-section h3 {{
            color: #495057;
            margin-bottom: 15px;
            font-size: 1.2em;
        }}
        .data-table-wrapper {{
            overflow-x: auto;
        }}
        .data-table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            background: white;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        }}
        .data-table th {{
            background: linear-gradient(135deg, #1a237e 0%, #0d47a1 100%);
            color: white;
            padding: 14px 16px;
            text-align: left;
            font-weight: 600;
        }}
        .data-table td {{
            padding: 12px 16px;
            border-bottom: 1px solid #e9ecef;
        }}
        .data-table tr:last-child td {{
            border-bottom: none;
        }}
        .data-table tr:hover {{
            background: #f1f3f4;
        }}
        .data-table .number {{
            text-align: right;
            font-family: 'Courier New', monospace;
            font-weight: 500;
        }}
        .data-table .positive {{
            color: #2e7d32;
        }}
        .data-table .negative {{
            color: #c62828;
        }}

        /* Footer */
        .footer {{
            background: #263238;
            color: #b0bec5;
            padding: 30px 50px;
            font-size: 0.85em;
        }}
        .footer a {{ color: #4fc3f7; }}

        /* Print styles */
        @media print {{
            .report {{ box-shadow: none; }}
            .section {{ page-break-inside: avoid; }}
        }}
    </style>
</head>
<body>
    <div class="report">
        <!-- HEADER -->
        <div class="header">
            <h1>COMPANY_NAME_PLACEHOLDER</h1>
            <div class="ticker">TICKER_PLACEHOLDER | EXCHANGE_PLACEHOLDER</div>
            <div class="meta">
                <span>Report Date: DATE_PLACEHOLDER</span>
                <span>Sector: SECTOR_PLACEHOLDER</span>
            </div>
            <div class="rating-badge RATING_CLASS_PLACEHOLDER">RATING_PLACEHOLDER</div>
        </div>

        <!-- EXECUTIVE SUMMARY -->
        <div class="section">
            <h2>Executive Summary</h2>
            EXECUTIVE_SUMMARY_PLACEHOLDER
        </div>

        <!-- KEY METRICS -->
        <div class="section">
            <h2>Key Metrics</h2>
            <div class="metrics-grid">
                KEY_METRICS_PLACEHOLDER
            </div>
        </div>

        <!-- COMPANY OVERVIEW -->
        <div class="section">
            <h2>Company Overview</h2>
            COMPANY_OVERVIEW_PLACEHOLDER
        </div>

        <!-- VISUAL INSIGHTS (INFOGRAPHICS) -->
        <div class="section">
            <h2>Visual Insights</h2>
            <p>AI-generated infographics providing visual representations of key business concepts and data.</p>
            <div class="infographic-grid">
                INFOGRAPHICS_PLACEHOLDER
            </div>
        </div>

        <!-- FINANCIAL PERFORMANCE -->
        <div class="section">
            <h2>Financial Performance</h2>
            FINANCIAL_ANALYSIS_PLACEHOLDER
            FINANCIAL_CHARTS_PLACEHOLDER
        </div>

        <!-- VALUATION ANALYSIS -->
        <div class="section">
            <h2>Valuation Analysis</h2>
            VALUATION_ANALYSIS_PLACEHOLDER
            VALUATION_CHARTS_PLACEHOLDER
        </div>

        <!-- GROWTH OUTLOOK -->
        <div class="section">
            <h2>Growth Outlook</h2>
            GROWTH_OUTLOOK_PLACEHOLDER
            GROWTH_CHARTS_PLACEHOLDER
        </div>

        <!-- RISKS & CONCERNS -->
        <div class="section">
            <h2>Risks & Concerns</h2>
            <p>RISKS_INTRO_PLACEHOLDER</p>
            <ul class="risk-list">
                RISKS_LIST_PLACEHOLDER
            </ul>
        </div>

        <!-- INVESTMENT RECOMMENDATION -->
        <div class="section">
            <h2>Investment Recommendation</h2>
            RECOMMENDATION_PLACEHOLDER
        </div>

        <!-- RAW DATA TABLES -->
        <div class="section">
            <h2>Financial Data Tables</h2>
            <p>Detailed numerical data supporting the analysis above.</p>
            DATA_TABLES_PLACEHOLDER
        </div>

        <!-- FOOTER -->
        <div class="footer">
            <p><strong>Disclaimer:</strong> This report is generated by an AI agent for informational purposes only. It does not constitute financial advice. Always consult a qualified financial advisor before making investment decisions.</p>
            <p style="margin-top: 15px;">Generated by Equity Research Agent using Google ADK | Powered by Gemini</p>
        </div>
    </div>
</body>
</html>
'''

HTML_REPORT_GENERATOR_INSTRUCTION = f"""
You are generating a professional equity research report with visual contextualization.

**INPUTS:**
- Research Plan: {{enhanced_research_plan}}
- Consolidated Data: {{consolidated_data}}
- Charts Summary: {{charts_summary}} (list of generated charts)
- Infographics Summary: {{infographics_summary}} (list of generated infographics)
- Analysis Sections: {{analysis_sections}} (NOW INCLUDES VISUAL CONTEXTS)

**Template:**
{HTML_TEMPLATE}

**CRITICAL NEW REQUIREMENT - Visual Contextualization**:

For each section (Company Overview, Financial, Valuation, Growth), you MUST:

1. Get the intro/conclusion paragraphs from analysis_sections
2. For each visual in that section:
   - Find the matching VisualContext from analysis_sections
   - Create a visual-context container with:
     - setup-text paragraph (from visual_context.setup_text)
     - The visual itself (chart or infographic)
     - interpretation-text paragraph (from visual_context.interpretation_text)

**EXAMPLE - Financial Performance Section**:

```html
<div class="section">
    <h2>Financial Performance</h2>
    {{{{ analysis_sections.financial_intro }}}}

    <!-- For each chart in financial section -->
    <div class="visual-context">
        <p class="setup-text">{{{{ visual_context.setup_text }}}}</p>
        <div class="chart-container">
            <div class="chart-title">Annual Revenue (FY2020-FY2025)</div>
            <img src="CHART_1_PLACEHOLDER" alt="Revenue Trend">
        </div>
        <p class="interpretation-text">{{{{ visual_context.interpretation_text }}}}</p>
    </div>

    <!-- Repeat for each financial chart -->

    {{{{ analysis_sections.financial_conclusion }}}}
</div>
```

**MAPPING VISUALS TO SECTIONS**:

**Company Overview Section:**
- Use analysis_sections.company_overview_intro
- For each context in analysis_sections.company_overview_visual_contexts:
  - Create visual-context container with setup/interpretation
  - Use infographic placeholders for infographics in this section
- Use analysis_sections.company_overview_conclusion

**Financial Performance Section:**
- Use analysis_sections.financial_intro
- For each context in analysis_sections.financial_visual_contexts:
  - Match visual_id to chart from charts_summary
  - Create visual-context with setup + chart + interpretation
- Use analysis_sections.financial_conclusion

**Valuation Analysis Section:**
- Use analysis_sections.valuation_intro
- For each context in analysis_sections.valuation_visual_contexts:
  - Create contextualized chart containers
- Use analysis_sections.valuation_conclusion

**Growth Outlook Section:**
- Use analysis_sections.growth_intro
- For each context in analysis_sections.growth_visual_contexts:
  - Include both charts AND growth-related infographics
- Use analysis_sections.growth_conclusion

**STANDARD PLACEHOLDERS (unchanged):**

1. **Header:** COMPANY_NAME_PLACEHOLDER, TICKER_PLACEHOLDER, EXCHANGE_PLACEHOLDER, DATE_PLACEHOLDER: {CURRENT_DATE}, SECTOR_PLACEHOLDER, RATING_PLACEHOLDER, RATING_CLASS_PLACEHOLDER

2. **Executive Summary:** analysis_sections.executive_summary (wrap in <p> tags)

3. **Key Metrics:** KEY_METRICS_PLACEHOLDER - create 4-6 metric cards from consolidated_data

4. **Risks & Concerns:** analysis_sections.risks_concerns (format as <li> items or paragraphs)

5. **Investment Recommendation:** analysis_sections.investment_recommendation (wrap in <p> tags)

6. **Data Tables (Appendix):** DATA_TABLES_PLACEHOLDER - create tables from consolidated_data.metrics

**IMAGE PLACEHOLDERS** (callback injects base64):
- Charts: CHART_1_PLACEHOLDER, CHART_2_PLACEHOLDER, etc.
- Infographics: INFOGRAPHIC_1_PLACEHOLDER, INFOGRAPHIC_2_PLACEHOLDER, etc. (up to 5)

**OUTPUT**: Complete HTML document with ALL visuals properly contextualized. No markdown blocks.
"""

html_report_generator = LlmAgent(
    model=MODEL,
    name="html_report_generator",
    description="Generates professional equity research report HTML with Setup→Visual→Interpretation contextualization.",
    instruction=HTML_REPORT_GENERATOR_INSTRUCTION,
    output_key="html_report",
    after_agent_callback=save_html_report_callback,
)
