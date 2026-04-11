import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { vscDarkPlus } from "react-syntax-highlighter/dist/esm/styles/prism";

type Props = {
  content: string;
};

function normalizeReadableMarkdown(raw: string): string {
  const text = String(raw ?? "").replace(/\r\n/g, "\n").trim();
  if (!text) return "";
  // Keep code blocks untouched to avoid breaking fenced markdown.
  if (text.includes("```")) return text;

  // Only apply heuristics to one-line outputs, which are the primary readability issue.
  if (!text.includes("\n")) {
    return text
      .replace(/([:：])\s*(\d+\.\s*)/g, "$1\n$2")
      .replace(/([；;。！？])\s*(\d+\.\s*)/g, "$1\n$2")
      .replace(/\s+(必要条件包括[:：])/g, "\n$1")
      .trim();
  }

  return text;
}

export function MarkdownRenderer({ content }: Props) {
  const normalizedContent = normalizeReadableMarkdown(content);

  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={{
        table(props) {
          const { children, ...rest } = props;
          return (
            <div className="markdown-table-wrap">
              <table {...rest}>{children}</table>
            </div>
          );
        },
        code(props) {
          const { children, className, ref: _ref, ...rest } = props;
          const match = /language-(\w+)/.exec(className || "");
          const codeText = String(children ?? "").replace(/\n$/, "");

          if (match) {
            return (
              <div className="markdown-codeblock">
                <SyntaxHighlighter
                  {...rest}
                  PreTag="div"
                  language={match[1]}
                  style={vscDarkPlus}
                  customStyle={{
                    margin: 0,
                    background: "transparent",
                    padding: "14px 16px",
                    fontSize: "13px",
                    lineHeight: "1.55",
                  }}
                >
                  {codeText}
                </SyntaxHighlighter>
              </div>
            );
          }

          return (
            <code {...rest} className={className}>
              {children}
            </code>
          );
        },
      }}
    >
      {normalizedContent}
    </ReactMarkdown>
  );
}
