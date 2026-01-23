# Equity Research Report Agent with Google ADK

A multi-agent AI pipeline for professional-grade equity research reports, built with [Google Agent Development Kit (ADK)](https://google.github.io/adk-docs/) and Gemini.

<table>
  <thead>
    <tr>
      <th colspan="2">Key Features</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>📊</td>
      <td><strong>Professional Reports:</strong> Investment-grade HTML & PDF reports with contextualized charts, data tables, and executive summaries.</td>
    </tr>
    <tr>
      <td>👥</td>
      <td><strong>Human-in-the-Loop:</strong> Interactive planning phase where users review and approve the research plan before execution.</td>
    </tr>
    <tr>
      <td>🌍</td>
      <td><strong>Multi-Market Support:</strong> US, India, China, Japan, Korea, Europe with market-specific metrics (Promoter %, State Ownership, etc.).</td>
    </tr>
    <tr>
      <td>📈</td>
      <td><strong>Dynamic Charts:</strong> 5-10 AI-generated matplotlib charts per report, executed in a secure Python sandbox.</td>
    </tr>
    <tr>
      <td>🎨</td>
      <td><strong>AI Infographics:</strong> 2-5 contextual infographics (business model, competitive landscape) via Gemini native image generation.</td>
    </tr>
    <tr>
      <td>⚡</td>
      <td><strong>Batch Mode:</strong> Experimental ~5-10x speedup for chart generation with single sandbox execution.</td>
    </tr>
    <tr>
      <td>🔒</td>
      <td><strong>Boundary Validation:</strong> Rejects unsupported queries (crypto, trading advice, private companies) with clear guidance.</td>
    </tr>
    <tr>
      <td>🐍</td>
      <td><strong>Code Execution:</strong> Vertex AI Agent Engine Sandbox for secure Python chart generation.</td>
    </tr>
    <tr>
      <td>🏗️</td>
      <td><strong>Production-Ready:</strong> Deploy to <a href="https://cloud.google.com/run">Cloud Run</a> or <a href="https://cloud.google.com/vertex-ai/generative-ai/docs/agent-engine/overview">Vertex AI Agent Engine</a>.</td>
    </tr>
  </tbody>
</table>

<p align="center">
  <img src="assets/hero-image.png" alt="Equity Research Report Agent" width="800">
</p>

## What It Does

Given a company query, this pipeline automatically:

- Validates the query against boundary rules (rejects crypto, trading advice, etc.)
- Presents an interactive research plan with 10-15 metrics for user approval
- Gathers financial, valuation, market, and news data in parallel via web search
- Generates 5-10 professional financial charts using Python sandbox execution
- Creates 2-5 AI-generated contextual infographics with Gemini
- Produces a multi-section HTML report (with optional PDF export)

---

## Getting Started

**Prerequisites:**
- **[Python 3.10+](https://www.python.org/downloads/)**
- **[Google Cloud SDK](https://cloud.google.com/sdk/docs/install)**
- **[ADK CLI](https://google.github.io/adk-docs/get-started/installation/)** (`pip install google-adk`)
- **Google Cloud Project** with Vertex AI API enabled

You have two options:

* A. **[Google Cloud Vertex AI (Recommended)](#a-google-cloud-vertex-ai-recommended)** - Full features with sandbox code execution
* B. **[Google AI Studio](#b-google-ai-studio)** - Quick testing (no chart generation)

---

### A. Google Cloud Vertex AI (Recommended)

Vertex AI is required for the Python sandbox that generates charts.

#### Step 1: Clone Repository
```bash
git clone https://github.com/user/build-with-adk.git
cd build-with-adk/adk-equity-deep-research
```

#### Step 2: Set Environment Variables
Create a `.env` file (see `.env.example` for reference):
```bash
echo "GOOGLE_CLOUD_PROJECT=your-project-id" >> .env
echo "GOOGLE_CLOUD_LOCATION=us-central1" >> .env
echo "GOOGLE_GENAI_USE_VERTEXAI=1" >> .env
echo "SANDBOX_RESOURCE_NAME=projects/.../sandboxes/..." >> .env
```

#### Step 3: Authenticate & Create Sandbox
```bash
gcloud auth application-default login
python manage_sandbox.py create
```

#### Step 4: Install & Run
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

### B. Google AI Studio

For quick testing without chart generation capabilities.

```bash
# Set environment
echo "GOOGLE_GENAI_USE_VERTEXAI=FALSE" >> .env
echo "GOOGLE_API_KEY=YOUR_AI_STUDIO_KEY" >> .env

# Install & Run
pip install -r requirements.txt
adk web app
```

> **Note:** Chart generation requires Vertex AI sandbox. AI Studio mode skips chart generation.

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

## Agent Details

| Attribute | Description |
| :--- | :--- |
| **Interaction Type** | Conversational + Workflow |
| **Complexity** | Advanced |
| **Agent Type** | Multi-Agent (Sequential Pipeline) |
| **Components** | Multi-agent, Function calling, Web search, Code execution, Image generation |
| **Vertical** | Finance / Investment Research |

---

## Model Configuration

| Purpose | Model | Notes |
|---------|-------|-------|
| **Agent Reasoning** | `gemini-3-flash-preview` | Main model for all agents |
| **Image Generation** | `gemini-3-pro-image-preview` | Infographic generation |
| **Code Execution** | Python sandbox | Vertex AI Agent Engine |

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

1. **Query Validator** - Checks boundary rules (crypto, trading advice, etc.)
2. **Query Classifier** - Detects market (US, India, China, etc.) and query type
3. **HITL Planning** - Generates research plan, waits for user approval
4. **Parallel Data Fetchers** - 4 agents gather financial, valuation, market, news data
5. **Data Consolidator** - Merges data into structured format
6. **Chart Generator** - Creates 5-10 matplotlib charts in sandbox
7. **Infographic Planner/Generator** - Plans and generates 2-5 AI infographics
8. **Analysis Writer** - Writes narrative with Setup→Visual→Interpretation pattern
9. **HTML Report Generator** - Produces final report with embedded visuals

---

## Project Structure

```
adk-equity-deep-research/
├── app/
│   ├── agent.py              # Root agent + HITL planning
│   ├── config.py             # Configuration (models, limits)
│   ├── callbacks/            # Agent lifecycle callbacks
│   ├── rules/                # Boundary validation, markets config
│   ├── schemas/              # Pydantic models
│   ├── sub_agents/           # All specialized agents
│   └── tools/                # Custom tools (infographics)
├── .docs/                    # Documentation
├── manage_sandbox.py         # Sandbox lifecycle
├── requirements.txt
└── README.md
```

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

## Learn More

| Goal | Resource |
|------|----------|
| **Architecture deep-dive** | [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) |
| **Implementation details** | [.docs/project_overview.md](.docs/project_overview.md) |
| **Learn ADK fundamentals** | [ADK Documentation](https://google.github.io/adk-docs/) |

---

## Authors

Created by [Lavi Nigam](https://github.com/lavinigam-gcp).

---

## Disclaimer

This agent sample is provided for illustrative purposes only. It serves as a basic example of an agent and a foundational starting point for individuals or teams to develop their own agents.

Users are solely responsible for any further development, testing, security hardening, and deployment of agents based on this sample.

---

## License

Apache 2.0 - See [LICENSE](LICENSE) for details.
