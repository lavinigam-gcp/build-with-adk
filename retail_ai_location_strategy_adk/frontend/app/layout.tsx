import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { CopilotKit } from "@copilotkit/react-core";
import "@copilotkit/react-ui/styles.css";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Retail AI Location Strategy",
  description:
    "AI-powered retail site selection and location intelligence with Google ADK + Gemini 3",
  keywords: ["retail", "location strategy", "AI", "Google ADK", "Gemini"],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <CopilotKit
          runtimeUrl="/api/copilotkit"
          agent="retail_location_strategy"
        >
          {children}
        </CopilotKit>
      </body>
    </html>
  );
}
