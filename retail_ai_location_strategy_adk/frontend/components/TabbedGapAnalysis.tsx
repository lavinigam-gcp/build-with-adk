"use client";

import { useState } from "react";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneLight } from "react-syntax-highlighter/dist/esm/styles/prism";
import { ScrollableMarkdown } from "./ScrollableMarkdown";
import { parseCodeBlocks, extractPythonCode } from "@/lib/parseCodeBlocks";

interface TabbedGapAnalysisProps {
  content: string;
}

type TabType = "results" | "code";

/**
 * Multi-tab interface for gap analysis showing both results and code.
 * - Results Tab: Rendered markdown output
 * - Code Tab: Syntax highlighted Python code
 */
export function TabbedGapAnalysis({ content }: TabbedGapAnalysisProps) {
  const [activeTab, setActiveTab] = useState<TabType>("results");

  if (!content) {
    return <p className="text-gray-500 text-sm italic">Analyzing market gaps...</p>;
  }

  const { textContent, codeBlocks } = parseCodeBlocks(content);
  const pythonCode = extractPythonCode(content);
  const hasCode = codeBlocks.length > 0;

  return (
    <div className="space-y-2">
      {/* Tab Navigation */}
      <div className="flex gap-1 border-b border-gray-200">
        <TabButton
          active={activeTab === "results"}
          onClick={() => setActiveTab("results")}
        >
          Results
        </TabButton>
        {hasCode && (
          <TabButton
            active={activeTab === "code"}
            onClick={() => setActiveTab("code")}
          >
            Code
          </TabButton>
        )}
      </div>

      {/* Tab Content */}
      <div className="pt-2">
        {activeTab === "results" && (
          <ScrollableMarkdown content={textContent || content} maxHeight="16rem" />
        )}

        {activeTab === "code" && hasCode && (
          <div
            className="overflow-y-auto rounded-lg"
            style={{ maxHeight: "16rem" }}
          >
            <SyntaxHighlighter
              language="python"
              style={oneLight}
              customStyle={{
                margin: 0,
                padding: "1rem",
                fontSize: "0.75rem",
                borderRadius: "0.5rem",
                backgroundColor: "#f8f9fa",
              }}
              showLineNumbers
              wrapLines
            >
              {pythonCode}
            </SyntaxHighlighter>
          </div>
        )}
      </div>
    </div>
  );
}

function TabButton({
  children,
  active,
  onClick,
}: {
  children: React.ReactNode;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={`px-3 py-1.5 text-sm font-medium rounded-t-lg transition-colors ${
        active
          ? "bg-white text-blue-600 border-b-2 border-blue-600"
          : "text-gray-500 hover:text-gray-700 hover:bg-gray-50"
      }`}
    >
      {children}
    </button>
  );
}
