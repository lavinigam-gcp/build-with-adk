"use client";

import { useState } from "react";

interface ArtifactViewerProps {
  htmlReport?: string;
  infographic?: string;
}

/**
 * ArtifactViewer provides a tabbed interface to view the generated
 * HTML executive report and infographic image.
 */
export function ArtifactViewer({ htmlReport, infographic }: ArtifactViewerProps) {
  const [activeTab, setActiveTab] = useState<"report" | "infographic">("report");

  if (!htmlReport && !infographic) return null;

  return (
    <div className="bg-white rounded-xl shadow-sm border overflow-hidden">
      {/* Tab header */}
      <div className="flex border-b">
        {htmlReport && (
          <button
            onClick={() => setActiveTab("report")}
            className={`flex-1 px-4 py-3 text-sm font-medium transition-colors ${
              activeTab === "report"
                ? "bg-blue-50 text-blue-700 border-b-2 border-blue-500"
                : "text-gray-500 hover:text-gray-700 hover:bg-gray-50"
            }`}
          >
            <span className="mr-2">📄</span>
            Executive Report
          </button>
        )}
        {infographic && (
          <button
            onClick={() => setActiveTab("infographic")}
            className={`flex-1 px-4 py-3 text-sm font-medium transition-colors ${
              activeTab === "infographic"
                ? "bg-blue-50 text-blue-700 border-b-2 border-blue-500"
                : "text-gray-500 hover:text-gray-700 hover:bg-gray-50"
            }`}
          >
            <span className="mr-2">🎨</span>
            Infographic
          </button>
        )}
      </div>

      {/* Tab content */}
      <div className="p-4">
        {activeTab === "report" && htmlReport && (
          <div className="space-y-4">
            <div className="flex justify-end">
              <button
                onClick={() => {
                  const blob = new Blob([htmlReport], { type: "text/html" });
                  const url = URL.createObjectURL(blob);
                  const a = document.createElement("a");
                  a.href = url;
                  a.download = "executive_report.html";
                  a.click();
                  URL.revokeObjectURL(url);
                }}
                className="px-3 py-1.5 text-sm bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
              >
                Download HTML
              </button>
            </div>
            <iframe
              srcDoc={htmlReport}
              className="w-full h-[600px] border rounded-lg"
              title="Executive Report"
              sandbox="allow-same-origin"
            />
          </div>
        )}

        {activeTab === "infographic" && infographic && (
          <div className="space-y-4">
            <div className="flex justify-end">
              <a
                href={infographic}
                download="infographic.png"
                className="px-3 py-1.5 text-sm bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
              >
                Download Image
              </a>
            </div>
            <img
              src={infographic}
              alt="Location Strategy Infographic"
              className="w-full rounded-lg shadow-sm"
            />
          </div>
        )}
      </div>
    </div>
  );
}
