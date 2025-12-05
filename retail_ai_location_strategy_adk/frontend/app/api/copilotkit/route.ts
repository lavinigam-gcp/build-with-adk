/**
 * CopilotKit API Route - Proxies requests to the backend AG-UI agent
 *
 * Uses LangGraphHttpAgent which (despite its name) is the generic HTTP agent
 * for connecting to any AG-UI compatible backend, including ag-ui-adk.
 */
import {
  CopilotRuntime,
  ExperimentalEmptyAdapter,
  copilotRuntimeNextJSAppRouterEndpoint,
  LangGraphHttpAgent,
} from "@copilotkit/runtime";
import { NextRequest } from "next/server";

// Use empty adapter since we're proxying to a remote AG-UI backend
const serviceAdapter = new ExperimentalEmptyAdapter();

// Use LangGraphHttpAgent with agents configuration for AG-UI protocol compatibility
// The agent name must match the app_name in the backend ADKAgent configuration
const runtime = new CopilotRuntime({
  agents: {
    retail_location_strategy: new LangGraphHttpAgent({
      url: process.env.REMOTE_ACTION_URL || "http://localhost:8000",
    }),
  },
});

export const POST = async (req: NextRequest) => {
  const { handleRequest } = copilotRuntimeNextJSAppRouterEndpoint({
    runtime,
    serviceAdapter,
    endpoint: "/api/copilotkit",
  });

  return handleRequest(req);
};
