# Equity Research Report Agent with Google ADK

A multi-agent AI pipeline for professional-grade equity research reports, built with [Google Agent Development Kit (ADK)](https://google.github.io/adk-docs/) and Gemini on Google Cloud.

> **Google Cloud Required:** This sample requires an active Google Cloud account with Vertex AI APIs enabled. Chart generation uses Agent Engine Sandbox, and all LLM calls go through Gemini on Vertex AI.

<table>
  <thead>
    <tr>
      <th colspan="2">Key Features</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>📊</td>
      <td><strong>Professional Reports:</strong> Investment-grade HTML & PDF reports with charts, infographics, and executive summaries.</td>
    </tr>
    <tr>
      <td>👥</td>
      <td><strong>Human-in-the-Loop Planning:</strong> Users review and approve research plans before execution begins.</td>
    </tr>
    <tr>
      <td>📈</td>
      <td><strong>Structured Data via yfinance:</strong> Financial statements, valuation metrics, and market data from Yahoo Finance with Google Search fallback.</td>
    </tr>
    <tr>
      <td>⚡</td>
      <td><strong>Batch Chart Generation:</strong> ~5-10x faster chart generation with single sandbox execution (all charts at once).</td>
    </tr>
    <tr>
      <td>🎨</td>
      <td><strong>AI Infographics:</strong> 2-5 contextual infographics via Gemini native image generation.</td>
    </tr>
    <tr>
      <td>🌍</td>
      <td><strong>Multi-Market Support:</strong> US, India, China, Japan, Korea, Europe with locale-specific metrics.</td>
    </tr>
    <tr>
      <td>🔒</td>
      <td><strong>Boundary Validation:</strong> Rejects unsupported queries (crypto, trading advice, private companies).</td>
    </tr>
    <tr>
      <td>☁️</td>
      <td><strong>Google Cloud Native:</strong> Vertex AI Gemini + Agent Engine Sandbox for secure code execution.</td>
    </tr>
  </tbody>
</table>

<p align="center">
  <img src="assets/hero-image.png" alt="Equity Research Report Agent" width="800">
</p>

## What It Does

Given a company query, this pipeline automatically:

1. **Validates** the query against boundary rules (rejects crypto, trading advice, etc.)
2. **Presents** an interactive research plan with 10-15 metrics for user approval
3. **Fetches** financial data via yfinance (structured) + Google Search (qualitative)
4. **Generates** 5-10 matplotlib charts in batch mode via Agent Engine Sandbox
5. **Creates** 2-5 AI-generated infographics with Gemini image generation
6. **Produces** a professional HTML report with optional PDF export

---

## Getting Started

### Prerequisites

| Requirement | Description |
|-------------|-------------|
| **Google Cloud Account** | Active account with billing enabled |
| **Vertex AI API** | Must be enabled in your GCP project |
| **Python 3.10+** | [Download](https://www.python.org/downloads/) |
| **Google Cloud SDK** | [Install gcloud CLI](https://cloud.google.com/sdk/docs/install) |
| **ADK CLI** | `pip install google-adk` |

> **Why Google Cloud?** This sample uses Vertex AI Gemini for LLM reasoning, Agent Engine Sandbox for secure Python code execution (charts), and Gemini image generation for infographics. These features require Google Cloud.

### Setup

#### Step 1: Clone Repository
```bash
git clone https://github.com/user/build-with-adk.git
cd build-with-adk/adk-equity-deep-research
```

#### Step 2: Authenticate with Google Cloud
```bash
gcloud auth application-default login
```

#### Step 3: Set Environment Variables
Create a `.env` file (see `.env.example` for reference):
```bash
echo "GOOGLE_CLOUD_PROJECT=your-project-id" >> .env
echo "GOOGLE_CLOUD_LOCATION=us-central1" >> .env
echo "GOOGLE_GENAI_USE_VERTEXAI=1" >> .env
```

#### Step 4: Create Sandbox for Chart Generation
```bash
python manage_sandbox.py create
```

The script will output a `SANDBOX_RESOURCE_NAME`. Copy it and add to your `.env`:
```bash
echo "SANDBOX_RESOURCE_NAME=projects/your-project/locations/.../sandboxes/..." >> .env
```

#### Step 5: Install & Run
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
adk web app
```

#### What You'll See

1. Open `http://localhost:8000` in your browser
2. Select **"app"** from the agent dropdown
3. Try a query: *"Do a fundamental analysis of Apple"*
4. Review the research plan when prompted
5. Approve with: *"Looks good, proceed"*

---

## Cloud Deployment

> **Note:** For production cloud deployment, use the [Agent Starter Pack](https://goo.gle/agent-starter-pack) to generate a deployment-ready project with CI/CD pipelines.

**Prerequisites:**
```bash
gcloud components update
gcloud config set project YOUR_PROJECT_ID
```

### Option 1: Cloud Run

Deploy with the built-in ADK web interface:

```bash
gcloud run deploy equity-research-agent \
  --source . \
  --region us-central1 \
  --allow-unauthenticated
```

### Option 2: Agent Engine

Deploy to Vertex AI Agent Engine for managed sessions:

```bash
# See ADK documentation for Agent Engine deployment
```

---

## Model & Data Configuration

| Component | Technology | Notes |
|-----------|------------|-------|
| **LLM Reasoning** | `gemini-3-flash-preview` | All agent reasoning via Vertex AI |
| **Image Generation** | `gemini-3-pro-image-preview` | Infographic generation |
| **Code Execution** | Agent Engine Sandbox | Secure Python for matplotlib charts |
| **Financial Data** | yfinance (Yahoo Finance) | Structured data: statements, metrics, prices |
| **News & Sentiment** | Google Search | Qualitative context and recent news |

---

## Example Prompts

Try these queries to explore the agent's capabilities:

### US Markets
| Query | What It Does |
|-------|--------------|
| "Analyze Apple stock" | Quick fundamental analysis with key metrics |
| "Do a fundamental analysis of Microsoft" | Comprehensive fundamentals with profitability focus |
| "Equity research on NVIDIA focusing on AI chip revenue" | Sector-specific analysis with custom focus |
| "Comprehensive analysis of Amazon covering AWS, e-commerce, and advertising" | Multi-segment business analysis |
| "Compare Tesla's profitability metrics over the last 5 years" | Time-series focused analysis |

### International Markets
| Query | Market | What It Does |
|-------|--------|--------------|
| "Comprehensive analysis of Reliance Industries" | India | Includes Promoter Holding %, FII/DII flows |
| "Analyze Tata Consultancy Services with focus on margins" | India | IT sector with India-specific metrics |
| "Research Alibaba Group fundamentals" | China | Includes State Ownership %, regulatory context |
| "Equity analysis of Toyota Motor Corporation" | Japan | Includes Keiretsu affiliation metrics |
| "Analyze Samsung Electronics valuation" | Korea | Includes Chaebol structure analysis |
| "Fundamental analysis of ASML Holding" | Europe | Includes ESG scores, EU metrics |

### Advanced Queries
| Query | What It Does |
|-------|--------------|
| "Deep dive into Alphabet's revenue segments and growth drivers" | Multi-segment with growth analysis |
| "Analyze Meta Platforms focusing on Reality Labs losses and AI investments" | Specific segment deep-dive |
| "Comprehensive equity research on JPMorgan Chase covering net interest income, trading revenue, and credit quality" | Financial sector with banking-specific metrics |
| "Research Pfizer's pipeline and patent cliff analysis" | Healthcare with R&D focus |

### HITL Refinement Examples
After the agent presents a research plan, try these refinements:
- "Add gross margin and operating margin"
- "Remove the news sentiment metrics"
- "Focus more on valuation metrics"
- "Add 10-year historical data instead of 5"
- "Include competitor comparison with AMD"

---

## Architecture

<p align="center">
  <img src="assets/architecture-diagram.png" alt="Agent Architecture" width="700">
</p>

The pipeline orchestrates 10+ specialized agents in a sequential flow:

| Stage | Agent | Description |
|-------|-------|-------------|
| 1 | **Query Validator** | Rejects unsupported queries (crypto, trading advice, etc.) |
| 2 | **Query Classifier** | Detects market (US, India, Japan, etc.) and query type |
| 3 | **HITL Planning** | Generates research plan, waits for user approval |
| 4 | **Parallel Data Fetchers** | 4 agents fetch data via **yfinance** + Google Search fallback |
| 5 | **Data Consolidator** | Merges structured data for charting |
| 6 | **Batch Chart Generator** | Creates all charts in single sandbox execution (~5-10x faster) |
| 7 | **Infographic Generator** | Generates 2-5 AI infographics via Gemini |
| 8 | **Analysis Writer** | Writes narrative with Setup→Visual→Interpretation pattern |
| 9 | **HTML Report Generator** | Produces final report with embedded visuals |

### Data Fetcher Pipeline (v2.4)

```
┌─────────────────────────────────────────────────────────────┐
│              ParallelAgent (4 concurrent fetchers)           │
├─────────────┬─────────────┬─────────────┬───────────────────┤
│ Financial   │ Valuation   │ Market      │ News              │
│ (yfinance)  │ (yfinance)  │ (yfinance)  │ (Google Search)   │
│ + fallback  │ + fallback  │ + fallback  │                   │
└─────────────┴─────────────┴─────────────┴───────────────────┘
```

**Why yfinance?** Structured, deterministic financial data from Yahoo Finance. Google Search is used as fallback and for qualitative news/sentiment.

---

## Supported Markets

| Market | Exchanges | Market-Specific Metrics |
|--------|-----------|------------------------|
| **US** | NYSE, NASDAQ | Standard metrics |
| **India** | NSE, BSE | Promoter Holding %, FII/DII Flows |
| **China** | SSE, SZSE, HKEX | State Ownership %, A/H-Share Premium |
| **Japan** | TSE | Keiretsu Affiliation, Cross-Shareholding |
| **Korea** | KRX, KOSDAQ | Chaebol Affiliation, Foreign Ownership |
| **Europe** | LSE, Euronext, XETRA | ESG Score, EU Taxonomy Alignment |

Markets are auto-detected from company names (e.g., "Reliance" → India, "Toyota" → Japan).

---

## HITL Planning Flow

```
User: "Analyze Tesla stock"

Agent: ## Research Plan for Tesla (TSLA)
       | # | Metric | Category | Chart | Priority |
       |---|--------|----------|-------|----------|
       | 1 | Revenue | financial | line | 10 |
       | 2 | Net Income | financial | bar | 9 |
       ...

       **To approve:** Say "looks good" or "proceed"
       **To modify:** Say "add X" or "remove Y"

User: "Add profit margin"

Agent: ## Updated Research Plan (v2)
       [Updated table with Profit Margin added]

User: "Looks good, proceed"

Agent: [Generates full report with charts and infographics]
```

---

## Authors

Created by [Lavi Nigam](https://github.com/lavinigam-gcp).

---

## Disclaimer

This agent sample is provided for illustrative purposes only. It serves as a basic example of an agent and a foundational starting point for individuals or teams to develop their own agents.

**Not Financial Advice:** This tool is a technology demonstration only. The reports, analysis, and data generated by this agent do not constitute investment advice, stock recommendations, or financial guidance of any kind. The outputs should not be used as the basis for any investment decisions. Always consult with a qualified financial advisor before making investment decisions.

Users are solely responsible for any further development, testing, security hardening, and deployment of agents based on this sample.

---

## License

Apache 2.0 - See [LICENSE](LICENSE) for details.
