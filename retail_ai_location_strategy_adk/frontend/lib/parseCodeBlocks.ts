/**
 * Utility to extract code blocks from markdown content.
 * Used primarily for parsing gap_analysis output which contains both code and results.
 */

export interface CodeBlock {
  language: string;
  code: string;
}

export interface ParsedContent {
  codeBlocks: CodeBlock[];
  textContent: string; // content with code blocks removed
}

/**
 * Parses markdown content to extract code blocks and remaining text.
 * Handles fenced code blocks with language specifiers (```python, ```js, etc.)
 */
export function parseCodeBlocks(content: string): ParsedContent {
  if (!content) {
    return { codeBlocks: [], textContent: "" };
  }

  const codeBlocks: CodeBlock[] = [];

  // Regex to match fenced code blocks: ```language\ncode\n```
  const codeBlockRegex = /```(\w*)\n([\s\S]*?)```/g;

  let match;
  while ((match = codeBlockRegex.exec(content)) !== null) {
    codeBlocks.push({
      language: match[1] || "text",
      code: match[2].trim(),
    });
  }

  // Remove code blocks from content to get text-only content
  const textContent = content
    .replace(codeBlockRegex, "")
    .replace(/\n{3,}/g, "\n\n") // Clean up extra newlines
    .trim();

  return { codeBlocks, textContent };
}

/**
 * Extracts just the Python code from content (for gap analysis).
 */
export function extractPythonCode(content: string): string {
  const { codeBlocks } = parseCodeBlocks(content);

  // Find Python code blocks
  const pythonBlocks = codeBlocks.filter(
    (block) => block.language.toLowerCase() === "python"
  );

  if (pythonBlocks.length > 0) {
    return pythonBlocks.map((b) => b.code).join("\n\n");
  }

  // Fallback: return all code blocks
  return codeBlocks.map((b) => b.code).join("\n\n");
}

/**
 * Gets the text content without code blocks.
 */
export function getTextContent(content: string): string {
  const { textContent } = parseCodeBlocks(content);
  return textContent;
}
