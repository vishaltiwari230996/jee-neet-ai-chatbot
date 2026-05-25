"use client";

/**
 * Tiny structured renderer for the assistant's reply.
 *
 * The system prompt (`packages/orchestrator/.../prompts.py`) asks the model
 * to use a fixed set of `## Header` sections plus paragraphs and lists.
 * That's a narrow enough shape that a 60-line renderer beats pulling in a
 * full markdown library — and it keeps the visual style locked down
 * (no surprise tables, no images, no raw HTML injection).
 *
 * Supports:
 *   - `# / ## / ### Heading`     (section title card)
 *   - `- bullet` / `* bullet`    (unordered list)
 *   - `1. ordered` / `2. ordered`(ordered list)
 *   - Markdown tables            (styled comparison grids)
 *   - `>` blockquotes            (callouts)
 *   - `---` horizontal rules     (quiet section breaks)
 *   - `**bold**`                 (inline emphasis)
 *   - `*italic*` / `_italic_`    (inline emphasis)
 *   - `` `code` ``               (inline code)
 *   - blank line                 (paragraph break)
 *
 * Anything else flows as plain text. Newlines mid-paragraph are preserved.
 */

import { type ReactNode } from "react";

interface Props {
  text: string;
  /** Show a blinking caret at the end while text is still streaming. */
  streaming?: boolean;
}

type Block =
  | { kind: "heading"; level: 1 | 2 | 3; text: string }
  | { kind: "paragraph"; lines: string[] }
  | { kind: "list"; ordered: boolean; items: string[] }
  | { kind: "table"; headers: string[]; rows: string[][] }
  | { kind: "quote"; lines: string[] }
  | { kind: "rule" };

export function StructuredAnswer({ text, streaming = false }: Props) {
  const blocks = parseBlocks(text);

  return (
    <div className="space-y-4 text-[15px] leading-7 text-[var(--color-fg)]">
      {blocks.map((block, idx) => (
        <Block
          key={idx}
          block={block}
          showCaret={streaming && idx === blocks.length - 1}
        />
      ))}
      {blocks.length === 0 && streaming ? <Caret /> : null}
    </div>
  );
}

function Block({ block, showCaret }: { block: Block; showCaret: boolean }) {
  if (block.kind === "heading") {
    const Tag = block.level === 1 ? "h1" : block.level === 2 ? "h2" : "h3";
    const className =
      block.level === 1
        ? "mt-2 text-xl font-semibold tracking-tight text-[var(--color-fg)]"
        : block.level === 2
          ? "mt-2 text-[13px] font-semibold uppercase tracking-wider text-[var(--color-brand)]"
          : "mt-1 text-sm font-medium text-[var(--color-fg)]";
    return (
      <Tag className={className}>
        {block.text}
        {showCaret ? <Caret /> : null}
      </Tag>
    );
  }

  if (block.kind === "table") {
    return (
      <div className="overflow-hidden rounded-xl border border-[var(--color-border)] bg-[var(--color-bg)]">
        <div className="overflow-x-auto">
          <table className="min-w-full border-collapse text-left text-sm">
            <thead className="bg-[var(--color-bg-elevated)] text-[12px] uppercase tracking-wider text-[var(--color-fg-muted)]">
              <tr>
                {block.headers.map((header, i) => (
                  <th
                    key={`${header}-${i}`}
                    className="border-b border-[var(--color-border)] px-3 py-2 font-semibold"
                  >
                    {renderInline(header)}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {block.rows.map((row, rowIdx) => (
                <tr
                  key={rowIdx}
                  className="border-b border-[var(--color-border)] last:border-0"
                >
                  {row.map((cell, cellIdx) => (
                    <td
                      key={`${rowIdx}-${cellIdx}`}
                      className="px-3 py-2 align-top text-[var(--color-fg)]"
                    >
                      {renderInline(cell)}
                      {showCaret &&
                      rowIdx === block.rows.length - 1 &&
                      cellIdx === row.length - 1 ? (
                        <Caret />
                      ) : null}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    );
  }

  if (block.kind === "quote") {
    return (
      <blockquote className="rounded-xl border-l-4 border-[var(--color-brand)] bg-[var(--color-bg)] px-4 py-3 text-sm text-[var(--color-fg-muted)]">
        {block.lines.map((line, i) => (
          <span key={i}>
            {i > 0 ? <br /> : null}
            {renderInline(line)}
          </span>
        ))}
        {showCaret ? <Caret /> : null}
      </blockquote>
    );
  }

  if (block.kind === "rule") {
    return <hr className="border-0 border-t border-[var(--color-border)]" />;
  }

  if (block.kind === "list") {
    const Tag = block.ordered ? "ol" : "ul";
    return (
      <Tag
        className={
          block.ordered
            ? "list-decimal space-y-1 pl-5 marker:text-[var(--color-fg-muted)]"
            : "list-disc space-y-1 pl-5 marker:text-[var(--color-fg-muted)]"
        }
      >
        {block.items.map((item, i) => (
          <li key={i}>
            {renderInline(item)}
            {showCaret && i === block.items.length - 1 ? <Caret /> : null}
          </li>
        ))}
      </Tag>
    );
  }

  return (
    <p className="whitespace-pre-wrap">
      {block.lines.map((line, i) => (
        <span key={i}>
          {i > 0 ? <br /> : null}
          {renderInline(line)}
        </span>
      ))}
      {showCaret ? <Caret /> : null}
    </p>
  );
}

function Caret() {
  return (
    <span className="ml-0.5 inline-block h-4 w-[2px] -translate-y-px animate-pulse bg-[var(--color-brand)] align-middle" />
  );
}

function parseBlocks(text: string): Block[] {
  const lines = text.split("\n");
  const blocks: Block[] = [];
  let i = 0;

  while (i < lines.length) {
    const line = lines[i] ?? "";

    if (line.trim() === "") {
      i += 1;
      continue;
    }

    const heading = /^(#{1,3})\s+(.*)$/.exec(line);
    if (heading) {
      blocks.push({
        kind: "heading",
        level: (heading[1]?.length ?? 2) as 1 | 2 | 3,
        text: (heading[2] ?? "").trim(),
      });
      i += 1;
      continue;
    }

    if (/^\s*-{3,}\s*$/.test(line)) {
      blocks.push({ kind: "rule" });
      i += 1;
      continue;
    }

    if (isTableStart(lines, i)) {
      const parsed = parseTable(lines, i);
      blocks.push(parsed.block);
      i = parsed.nextIndex;
      continue;
    }

    if (/^\s*>\s?/.test(line)) {
      const quote: string[] = [];
      while (i < lines.length) {
        const current = lines[i] ?? "";
        if (!/^\s*>\s?/.test(current)) break;
        quote.push(current.replace(/^\s*>\s?/, ""));
        i += 1;
      }
      blocks.push({ kind: "quote", lines: quote });
      continue;
    }

    if (/^\s*[-*]\s+/.test(line)) {
      const items: string[] = [];
      while (i < lines.length) {
        const current = lines[i] ?? "";
        if (!/^\s*[-*]\s+/.test(current)) break;
        items.push(current.replace(/^\s*[-*]\s+/, ""));
        i += 1;
      }
      blocks.push({ kind: "list", ordered: false, items });
      continue;
    }

    if (/^\s*\d+\.\s+/.test(line)) {
      const items: string[] = [];
      while (i < lines.length) {
        const current = lines[i] ?? "";
        if (!/^\s*\d+\.\s+/.test(current)) break;
        items.push(current.replace(/^\s*\d+\.\s+/, ""));
        i += 1;
      }
      blocks.push({ kind: "list", ordered: true, items });
      continue;
    }

    const para: string[] = [];
    while (i < lines.length) {
      const current = lines[i] ?? "";
      if (
        current.trim() === "" ||
        /^#{1,3}\s+/.test(current) ||
        /^\s*-{3,}\s*$/.test(current) ||
        isTableStart(lines, i) ||
        /^\s*>\s?/.test(current) ||
        /^\s*[-*]\s+/.test(current) ||
        /^\s*\d+\.\s+/.test(current)
      ) {
        break;
      }
      para.push(current);
      i += 1;
    }
    blocks.push({ kind: "paragraph", lines: para });
  }

  return blocks;
}

function isTableStart(lines: string[], index: number): boolean {
  const header = lines[index] ?? "";
  const separator = lines[index + 1] ?? "";
  return isTableRow(header) && isTableSeparator(separator);
}

function isTableRow(line: string): boolean {
  const trimmed = line.trim();
  return trimmed.startsWith("|") && trimmed.endsWith("|") && trimmed.includes("|");
}

function isTableSeparator(line: string): boolean {
  if (!isTableRow(line)) return false;
  return splitTableRow(line).every((cell) => /^:?-{3,}:?$/.test(cell.trim()));
}

function parseTable(
  lines: string[],
  startIndex: number,
): { block: Extract<Block, { kind: "table" }>; nextIndex: number } {
  const headers = splitTableRow(lines[startIndex] ?? "");
  let i = startIndex + 2; // skip separator row
  const rows: string[][] = [];

  while (i < lines.length && isTableRow(lines[i] ?? "")) {
    rows.push(padRow(splitTableRow(lines[i] ?? ""), headers.length));
    i += 1;
  }

  return {
    block: {
      kind: "table",
      headers,
      rows,
    },
    nextIndex: i,
  };
}

function splitTableRow(line: string): string[] {
  return line
    .trim()
    .replace(/^\|/, "")
    .replace(/\|$/, "")
    .split("|")
    .map((cell) => cell.trim());
}

function padRow(row: string[], length: number): string[] {
  if (row.length >= length) return row.slice(0, length);
  return [...row, ...Array.from({ length: length - row.length }, () => "")];
}

/**
 * Inline parser: bold, italic, code. Walks the string once so partial
 * tokens that haven't finished streaming render as plain text (no
 * jarring re-flows mid-token).
 */
function renderInline(text: string): ReactNode {
  const out: ReactNode[] = [];
  let buf = "";
  let i = 0;

  const flush = () => {
    if (buf) {
      out.push(buf);
      buf = "";
    }
  };

  while (i < text.length) {
    const char = text[i] ?? "";
    if (text.startsWith("**", i)) {
      const close = text.indexOf("**", i + 2);
      if (close !== -1) {
        flush();
        out.push(
          <strong key={out.length} className="font-semibold">
            {text.slice(i + 2, close)}
          </strong>,
        );
        i = close + 2;
        continue;
      }
    }
    if (char === "`") {
      const close = text.indexOf("`", i + 1);
      if (close !== -1) {
        flush();
        out.push(
          <code
            key={out.length}
            className="rounded-md bg-[var(--color-bg)] px-1.5 py-0.5 font-mono text-[13px]"
          >
            {text.slice(i + 1, close)}
          </code>,
        );
        i = close + 1;
        continue;
      }
    }
    if ((char === "*" || char === "_") && text[i + 1] !== char) {
      const marker = char;
      const close = text.indexOf(marker, i + 1);
      if (close !== -1 && text[close + 1] !== marker) {
        flush();
        out.push(
          <em key={out.length} className="italic">
            {text.slice(i + 1, close)}
          </em>,
        );
        i = close + 1;
        continue;
      }
    }
    buf += char;
    i += 1;
  }
  flush();

  return out;
}
