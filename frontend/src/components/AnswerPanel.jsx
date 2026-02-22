import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

export default function AnswerPanel({ answer }) {
  if (!answer) return null

  return (
    <div className="animate-slide-up">
      <div className="rounded-2xl border border-indigo-500/20 bg-gradient-to-b from-indigo-500/[0.04] to-[#111827]/80 backdrop-blur-lg p-6">
        <div className="flex items-center gap-2 mb-4">
          <div className="w-2 h-2 rounded-full bg-indigo-500 animate-pulse-slow" />
          <span className="text-sm font-semibold text-slate-300 uppercase tracking-wider">Generated Answer</span>
        </div>

        <div className="markdown-body">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {answer}
          </ReactMarkdown>
        </div>
      </div>
    </div>
  )
}
