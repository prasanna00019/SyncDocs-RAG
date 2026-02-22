import { useEffect, useRef } from 'react'

const LOG_COLORS = {
  system: 'text-indigo-400',
  info: 'text-slate-400',
  success: 'text-emerald-400',
  error: 'text-red-400',
  url: 'text-sky-400',
}

export default function LogStream({ logs }) {
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [logs])

  return (
    <div className="animate-fade-in">
      <div className="rounded-2xl border border-white/[0.06] bg-[#111827]/80 backdrop-blur-lg overflow-hidden">
        {/* Terminal header */}
        <div className="flex items-center gap-2 px-5 py-3 border-b border-white/[0.04] bg-[#0d1117]/60">
          <div className="flex gap-1.5">
            <div className="w-2.5 h-2.5 rounded-full bg-red-500/70" />
            <div className="w-2.5 h-2.5 rounded-full bg-amber-500/70" />
            <div className="w-2.5 h-2.5 rounded-full bg-emerald-500/70" />
          </div>
          <span className="text-[10px] text-slate-600 ml-2 font-mono">pipeline.log</span>
          <div className="flex-1" />
          <span className="text-[10px] text-slate-600 font-mono">{logs.length} entries</span>
        </div>

        {/* Log body */}
        <div className="h-[420px] overflow-y-auto p-4 font-mono text-xs leading-relaxed">
          {logs.length === 0 ? (
            <div className="flex items-center justify-center h-full text-slate-700">
              <p>Logs will appear here when you run the pipeline...</p>
            </div>
          ) : (
            logs.map((log, i) => (
              <div key={i} className="flex gap-3 py-0.5 animate-fade-in">
                <span className="text-slate-700 select-none shrink-0">{log.ts}</span>
                <span className={LOG_COLORS[log.type] || 'text-slate-400'}>
                  {log.message}
                </span>
              </div>
            ))
          )}
          <div ref={bottomRef} />
        </div>
      </div>
    </div>
  )
}
