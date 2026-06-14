/* eslint-disable @typescript-eslint/no-unused-vars */
import ReactMarkdown from "react-markdown";

type MarkdownProps = {
  content: string;
};

/**
 * 通用 Markdown 渲染组件，使用 Tailwind CSS 自定义各种 HTML 标签的样式以匹配全局 UI
 */
export function Markdown({ content }: MarkdownProps) {
  return (
    <ReactMarkdown
      components={{
        // 段落样式
        p: ({ node: _, ...props }) => (
          <p className="mb-2 last:mb-0 leading-relaxed break-words text-[13.5px]" {...props} />
        ),
        // 标题样式
        h1: ({ node: _, ...props }) => (
          <h1 className="text-lg font-bold mt-4 mb-2 first:mt-0 font-display text-slate-900 dark:text-slate-100" {...props} />
        ),
        h2: ({ node: _, ...props }) => (
          <h2 className="text-base font-bold mt-3 mb-2 first:mt-0 font-display text-slate-900 dark:text-slate-100" {...props} />
        ),
        h3: ({ node: _, ...props }) => (
          <h3 className="text-sm font-bold mt-2.5 mb-1.5 first:mt-0 font-display text-slate-900 dark:text-slate-100" {...props} />
        ),
        // 列表样式
        ul: ({ node: _, ...props }) => (
          <ul className="list-disc pl-5 mb-2 space-y-1 text-[13px]" {...props} />
        ),
        ol: ({ node: _, ...props }) => (
          <ol className="list-decimal pl-5 mb-2 space-y-1 text-[13px]" {...props} />
        ),
        li: ({ node: _, ...props }) => <li className="mb-0.5" {...props} />,
        // 行内代码与代码块样式
        code: ({ node: _, className, children, ...props }) => {
          const isInline = !className; // react-markdown 中 inline 代码没有 className
          
          if (isInline) {
            return (
              <code
                className="bg-slate-100 dark:bg-slate-800 text-pink-600 dark:text-pink-400 px-1.5 py-0.5 rounded font-mono text-xs font-semibold"
                {...props}
              >
                {children}
              </code>
            );
          }
          
          return (
            <pre className="bg-slate-950 text-slate-100 p-4 rounded-xl font-mono text-xs my-3 overflow-x-auto border border-slate-800 shadow-inner">
              <code className={className} {...props}>
                {children}
              </code>
            </pre>
          );
        },
        // 链接样式
        a: ({ node: _, ...props }) => (
          <a
            className="text-brand-600 dark:text-brand-400 underline hover:text-brand-700 dark:hover:text-brand-300 transition-colors font-medium"
            target="_blank"
            rel="noopener noreferrer"
            {...props}
          />
        ),
        // 引用块样式
        blockquote: ({ node: _, ...props }) => (
          <blockquote
            className="border-l-4 border-slate-300 dark:border-slate-700 pl-4 py-1 my-3 text-slate-500 dark:text-slate-400 italic bg-slate-50/50 dark:bg-slate-950/20 rounded-r"
            {...props}
          />
        ),
        // 表格样式
        table: ({ node: _, ...props }) => (
          <div className="overflow-x-auto my-3 border border-slate-200 dark:border-slate-800 rounded-lg">
            <table className="min-w-full divide-y divide-slate-200 dark:divide-slate-800 text-xs" {...props} />
          </div>
        ),
        thead: ({ node: _, ...props }) => <thead className="bg-slate-50 dark:bg-slate-900" {...props} />,
        tbody: ({ node: _, ...props }) => <tbody className="divide-y divide-slate-200 dark:divide-slate-800" {...props} />,
        tr: ({ node: _, ...props }) => <tr {...props} />,
        th: ({ node: _, ...props }) => (
          <th className="px-4 py-2 text-left font-semibold text-slate-700 dark:text-slate-300" {...props} />
        ),
        td: ({ node: _, ...props }) => <td className="px-4 py-2 text-slate-600 dark:text-slate-400 font-mono" {...props} />,
      }}
    >
      {content}
    </ReactMarkdown>
  );
}
