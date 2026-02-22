import { useState } from 'react'

export default function QueryForm({ onSubmit, isRunning }) {
  const [url, setUrl] = useState('')
  const [query, setQuery] = useState('')
  const [limit, setLimit] = useState(5)

  const handleSubmit = (e) => {
    e.preventDefault()
    if (!query.trim()) return
    onSubmit({ url: url.trim(), query: query.trim(), limit })
  }

  return (
    <form onSubmit={handleSubmit} className="animate-fade-in">
      <div className="rounded-2xl border border-white/[0.06] bg-[#111827]/80 backdrop-blur-lg p-6 space-y-5">
        <div className="flex items-center gap-2 mb-1">
          <div className="w-2 h-2 rounded-full bg-indigo-500 animate-pulse-slow" />
          <span className="text-sm font-semibold text-slate-300 uppercase tracking-wider">Query Input</span>
        </div>

        {/* Docs URL */}
        <div>
          <label className="block text-xs font-medium text-slate-400 mb-1.5">Documentation URL</label>
          <input
            type="url"
            value={url}
            onChange={e => setUrl(e.target.value)}
            placeholder="https://docs.example.com/"
            disabled={isRunning}
            className="w-full bg-[#0a0e1a] border border-white/[0.08] rounded-xl px-4 py-3 text-sm text-slate-200 placeholder-slate-600 focus:outline-none focus:ring-2 focus:ring-indigo-500/40 focus:border-indigo-500/50 transition-all disabled:opacity-50"
          />
          <p className="text-[10px] text-slate-600 mt-1">Leave empty to query existing ingested docs</p>
        </div>

        {/* Query */}
        <div>
          <label className="block text-xs font-medium text-slate-400 mb-1.5">Your Question</label>
          <textarea
            value={query}
            onChange={e => setQuery(e.target.value)}
            placeholder="How do I authenticate with the API?"
            rows={3}
            required
            disabled={isRunning}
            className="w-full bg-[#0a0e1a] border border-white/[0.08] rounded-xl px-4 py-3 text-sm text-slate-200 placeholder-slate-600 focus:outline-none focus:ring-2 focus:ring-indigo-500/40 focus:border-indigo-500/50 transition-all resize-none disabled:opacity-50"
          />
        </div>

        {/* Limit */}
        <div>
          <label className="block text-xs font-medium text-slate-400 mb-1.5">
            Max Pages to Scrape: <span className="text-indigo-400 font-semibold">{limit}</span>
          </label>
          <input
            type="range"
            min={1}
            max={15}
            value={limit}
            onChange={e => setLimit(Number(e.target.value))}
            disabled={isRunning}
            className="w-full accent-indigo-500 disabled:opacity-50"
          />
          <div className="flex justify-between text-[10px] text-slate-600 mt-0.5">
            <span>1</span><span>15</span>
          </div>
        </div>

        {/* Submit */}
        <button
          type="submit"
          disabled={isRunning || !query.trim()}
          className="w-full py-3 rounded-xl font-semibold text-sm transition-all duration-200
            bg-gradient-to-r from-indigo-600 to-purple-600
            hover:from-indigo-500 hover:to-purple-500
            active:scale-[0.98]
            disabled:opacity-40 disabled:cursor-not-allowed disabled:active:scale-100
            shadow-lg shadow-indigo-500/20 hover:shadow-indigo-500/30
            text-white"
        >
          {isRunning ? (
            <span className="flex items-center justify-center gap-2">
              <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
              Pipeline Running...
            </span>
          ) : 'Run RAG Pipeline'}
        </button>
      </div>
    </form>
  )
}
