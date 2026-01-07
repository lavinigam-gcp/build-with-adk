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

"""Infographic summary callback for creating lightweight summaries."""


async def create_infographics_summary_callback(callback_context):
    """Create infographics_summary without base64 data for later agents.

    This runs as after_agent_callback on infographic_generator, ensuring the summary
    exists in session state before analysis_writer tries to use it in its instruction template.
    """
    try:
        print("\n" + "="*80)
        print("CREATE INFOGRAPHICS SUMMARY CALLBACK - START")
        print("="*80)

        state = callback_context.state

        print(f"📋 Agent: {callback_context.agent_name}")
        print(f"🔑 Invocation ID: {callback_context.invocation_id}")

        infographics_generated = state.get("infographics_generated", [])
        print(f"🔍 DEBUG: infographics_generated type: {type(infographics_generated)}")
        print(f"🔍 DEBUG: infographics_generated length: {len(infographics_generated) if isinstance(infographics_generated, list) else 'N/A'}")

        print(f"📊 Found {len(infographics_generated)} generated infographics in state")

        # Calculate total base64 size for debugging
        total_base64_size = 0
        for infographic in infographics_generated:
            base64_data = infographic.get("base64_data", "")
            total_base64_size += len(base64_data)

        print(f"⚠️  Total base64 data size: {total_base64_size:,} chars (~{total_base64_size / (1024*1024):.2f} MB)")
        print(f"   This would exceed LLM context - creating summary without base64...")

        infographics_summary = []
        for infographic in infographics_generated:
            summary_item = {
                "infographic_id": infographic.get("infographic_id"),
                "title": infographic.get("title"),
                "infographic_type": infographic.get("infographic_type"),
                "filename": infographic.get("filename"),
            }
            infographics_summary.append(summary_item)
            print(f"   - Infographic {summary_item['infographic_id']}: {summary_item['title']} ({summary_item['filename']})")

        state["infographics_summary"] = infographics_summary

        # Debug: Check size of all state variables that will be passed to analysis_writer
        print(f"\n📏 STATE SIZE CHECK (for analysis_writer):")
        print(f"   enhanced_research_plan: {len(str(state.get('enhanced_research_plan', '')))} chars")
        print(f"   consolidated_data: {len(str(state.get('consolidated_data', '')))} chars")
        print(f"   charts_summary: {len(str(state.get('charts_summary', '')))} chars")
        print(f"   infographics_summary: {len(str(infographics_summary))} chars")

        total_state_size = (
            len(str(state.get('enhanced_research_plan', ''))) +
            len(str(state.get('consolidated_data', ''))) +
            len(str(state.get('charts_summary', ''))) +
            len(str(infographics_summary))
        )
        print(f"   TOTAL (without base64): {total_state_size:,} chars (~{total_state_size / (1024*1024):.2f} MB)")

        if total_state_size > 500_000:  # ~500KB
            print(f"   ⚠️  WARNING: State size is large - may cause LLM errors")

        print(f"\n✅ Created infographics_summary with {len(infographics_summary)} items (no base64)")
        print("="*80 + "\n")

    except Exception as e:
        print(f"\n✗ ERROR in create_infographics_summary_callback: {str(e)}")
        import traceback
        traceback.print_exc()
        print("="*80 + "\n")
        # Create empty summary to prevent downstream errors
        callback_context.state["infographics_summary"] = []
