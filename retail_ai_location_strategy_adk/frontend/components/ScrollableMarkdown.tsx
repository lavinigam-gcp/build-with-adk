"use client";

import ReactMarkdown from "react-markdown";

interface ScrollableMarkdownProps {
  content: string;
  maxHeight?: string;
}

/**
 * Renders markdown content in a scrollable container with fixed max-height.
 * Shows a gradient fade at the bottom to indicate more content is available.
 */
export function ScrollableMarkdown({
  content,
  maxHeight = "12rem",
}: ScrollableMarkdownProps) {
  if (!content) {
    return <p className="text-gray-500 text-sm italic">Loading...</p>;
  }

  return (
    <div className="relative">
      <div
        className="overflow-y-auto pr-2 scrollbar-thin scrollbar-thumb-gray-300 scrollbar-track-gray-100"
        style={{ maxHeight }}
      >
        <div className="prose prose-sm prose-gray max-w-none">
          <ReactMarkdown
            components={{
              // Style headings
              h1: ({ children }) => (
                <h1 className="text-lg font-bold text-gray-900 mt-0 mb-2">
                  {children}
                </h1>
              ),
              h2: ({ children }) => (
                <h2 className="text-base font-semibold text-gray-800 mt-3 mb-2">
                  {children}
                </h2>
              ),
              h3: ({ children }) => (
                <h3 className="text-sm font-semibold text-gray-800 mt-2 mb-1">
                  {children}
                </h3>
              ),
              // Style paragraphs
              p: ({ children }) => (
                <p className="text-sm text-gray-600 mb-2 leading-relaxed">
                  {children}
                </p>
              ),
              // Style lists
              ul: ({ children }) => (
                <ul className="list-disc list-inside text-sm text-gray-600 mb-2 space-y-1">
                  {children}
                </ul>
              ),
              ol: ({ children }) => (
                <ol className="list-decimal list-inside text-sm text-gray-600 mb-2 space-y-1">
                  {children}
                </ol>
              ),
              li: ({ children }) => (
                <li className="text-sm text-gray-600">{children}</li>
              ),
              // Style bold and emphasis
              strong: ({ children }) => (
                <strong className="font-semibold text-gray-800">{children}</strong>
              ),
              em: ({ children }) => (
                <em className="italic text-gray-700">{children}</em>
              ),
              // Style inline code
              code: ({ children }) => (
                <code className="px-1 py-0.5 bg-gray-100 text-gray-800 text-xs rounded font-mono">
                  {children}
                </code>
              ),
              // Style code blocks
              pre: ({ children }) => (
                <pre className="p-3 bg-gray-50 rounded-lg overflow-x-auto text-xs my-2">
                  {children}
                </pre>
              ),
            }}
          >
            {content}
          </ReactMarkdown>
        </div>
      </div>
      {/* Gradient fade to indicate more content */}
      <div className="absolute bottom-0 left-0 right-0 h-4 bg-gradient-to-t from-white to-transparent pointer-events-none" />
    </div>
  );
}
