/**
 * MarkdownContent Component
 * 
 * Safely renders Markdown content with ATLAS-styled formatting.
 * Supports GitHub-flavored Markdown including tables.
 * 
 * Used for rendering Gemini AI responses that contain:
 * - Headings
 * - Bold/italic text
 * - Lists (bullet and numbered)
 * - Tables (budget breakdowns, itineraries)
 * - Horizontal rules
 * - Paragraphs
 * - Blockquotes
 * - Links
 */

import ReactMarkdown from 'react-markdown';
import type { Components } from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { cn } from '../utils/format';

interface MarkdownContentProps {
  children: string;
  className?: string;
}

export function MarkdownContent({ children, className }: MarkdownContentProps) {
  return (
    <div className={cn('prose prose-sm max-w-none', className)}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          // Headings
          h1: ({ children }) => (
            <h1 className="mt-6 mb-4 text-xl font-bold text-ink leading-tight">
              {children}
            </h1>
          ),
          h2: ({ children }) => (
            <h2 className="mt-5 mb-3 text-lg font-bold text-ink leading-tight">
              {children}
            </h2>
          ),
          h3: ({ children }) => (
            <h3 className="mt-4 mb-2 text-base font-bold text-ink leading-tight">
              {children}
            </h3>
          ),
          h4: ({ children }) => (
            <h4 className="mt-3 mb-2 text-sm font-bold text-ink">
              {children}
            </h4>
          ),
          h5: ({ children }) => (
            <h5 className="mt-2 mb-1 text-sm font-semibold text-ink">
              {children}
            </h5>
          ),
          h6: ({ children }) => (
            <h6 className="mt-2 mb-1 text-xs font-semibold text-muted">
              {children}
            </h6>
          ),

          // Paragraphs
          p: ({ children }) => (
            <p className="my-3 text-[14px] leading-relaxed text-ink">
              {children}
            </p>
          ),

          // Lists
          ul: ({ children }) => (
            <ul className="my-3 ml-5 space-y-1.5 text-[14px] leading-relaxed text-ink list-disc list-outside">
              {children}
            </ul>
          ),
          ol: ({ children }) => (
            <ol className="my-3 ml-5 space-y-1.5 text-[14px] leading-relaxed text-ink list-decimal list-outside">
              {children}
            </ol>
          ),
          li: ({ children }) => (
            <li className="ml-2">
              {children}
            </li>
          ),

          // Code
          code: ({ children, className }) => (
            <code className={cn('rounded bg-subtle px-1.5 py-0.5 font-mono text-[13px] text-brand', className)}>
              {children}
            </code>
          ),
          pre: ({ children }) => (
            <pre className="bg-subtle p-3 rounded overflow-x-auto my-3 text-[13px] font-mono">
              {children}
            </pre>
          ),

          // Blockquote
          blockquote: ({ children }) => (
            <blockquote className="border-l-4 border-brand/30 pl-4 py-2 my-3 italic text-muted bg-brand/5 rounded-r">
              {children}
            </blockquote>
          ),

          // Horizontal rule
          hr: () => (
            <hr className="my-4 border-t border-line" />
          ),

          // Links
          a: ({ href, children }) => (
            <a
              href={href}
              target="_blank"
              rel="noopener noreferrer"
              className="text-brand underline hover:text-brand/80 transition-colors"
            >
              {children}
            </a>
          ),

          // Tables
          table: ({ children }) => (
            <div className="my-4 overflow-x-auto rounded-lg border border-line">
              <table className="w-full text-[13px] leading-relaxed">
                {children}
              </table>
            </div>
          ),
          thead: ({ children }) => (
            <thead className="bg-brand/5 border-b border-line">
              {children}
            </thead>
          ),
          tbody: ({ children }) => (
            <tbody className="divide-y divide-line">
              {children}
            </tbody>
          ),
          tr: ({ children }) => (
            <tr className="divide-x divide-line">
              {children}
            </tr>
          ),
          th: ({ children }) => (
            <th className="px-4 py-3 text-left font-semibold text-ink bg-brand/5">
              {children}
            </th>
          ),
          td: ({ children }) => (
            <td className="px-4 py-3 text-ink">
              {children}
            </td>
          ),

          // Strong (bold)
          strong: ({ children }) => (
            <strong className="font-bold text-ink">
              {children}
            </strong>
          ),

          // Emphasis (italic)
          em: ({ children }) => (
            <em className="italic text-ink">
              {children}
            </em>
          ),
        } satisfies Components}
      >
        {children}
      </ReactMarkdown>
    </div>
  );
}
