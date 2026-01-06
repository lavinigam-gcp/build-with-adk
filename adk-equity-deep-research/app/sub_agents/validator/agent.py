# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Query validator agent for checking boundaries before processing.

This agent validates user queries against boundary rules:
- Rejects crypto/NFT queries
- Rejects trading advice requests
- Rejects private company queries
- Rejects personal finance questions
- Rejects non-financial queries
- Accepts valid equity research queries for listed companies
"""

from google.adk.agents import LlmAgent
from pydantic import BaseModel, Field

from app.config import MODEL
from app.rules.boundaries_config import (
    UNSUPPORTED_QUERY_TYPES,
    SYSTEM_CAPABILITIES,
)
from app.rules.markets_config import (
    SUPPORTED_MARKETS,
)

# Build rejection keywords list for the prompt
_rejection_categories = "\n".join([
    f"- **{rule['type']}**: {', '.join(str(k) for k in rule.get('keywords', [])[:5])}..."
    for rule in UNSUPPORTED_QUERY_TYPES
])

_supported_markets = ", ".join(SUPPORTED_MARKETS.keys())

QUERY_VALIDATOR_INSTRUCTION = f"""
You are a query validator for an equity research system. Your job is to check if a query should be processed or rejected.

**REJECT queries that match these categories:**
{_rejection_categories}

**ACCEPT queries for listed companies in these markets:**
{_supported_markets}

**Validation Rules:**
1. If query mentions crypto, NFT, blockchain tokens -> REJECT
2. If query asks for buy/sell recommendations or trading signals -> REJECT
3. If query is about private/unlisted companies -> REJECT
4. If query is about personal finance or portfolio advice -> REJECT
5. If query is non-financial (weather, recipes, etc.) -> REJECT
6. If query is about penny stocks or OTC markets -> REJECT
7. If query is about a listed company in a supported market -> ACCEPT

**Your Response:**
- If ACCEPT: Set is_valid=true, rejection_reason=null
- If REJECT: Set is_valid=false, rejection_reason="<specific reason from categories above>"

**Query Types:**
- equity_research: Single company analysis
- comparison: Compare two or more companies
- sector: Sector/industry analysis
- rejected: Query that should be rejected

Always err on the side of accepting ambiguous queries about companies.
"""


class QueryValidationResult(BaseModel):
    """Result of query validation."""

    is_valid: bool = Field(
        description="True if query should be processed, False if rejected"
    )
    rejection_reason: str | None = Field(
        default=None,
        description="Reason for rejection if is_valid=False"
    )
    detected_query_type: str = Field(
        description="Type of query detected: equity_research, comparison, sector, or rejected"
    )


query_validator = LlmAgent(
    model=MODEL,
    name="query_validator",
    description="Validates user queries against boundary rules before processing",
    output_schema=QueryValidationResult,
    output_key="query_validation",
    instruction=QUERY_VALIDATOR_INSTRUCTION,
)
