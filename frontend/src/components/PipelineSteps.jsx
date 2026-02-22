const STEPS_CONFIG = [
  { key: 'init',     label: 'Initialize',      icon: '⚡' },
  { key: 'map',      label: 'Map Links',        icon: '🗺️' },
  { key: 'filter',   label: 'Filter URLs',      icon: '🔍' },
  { key: 'scrape',   label: 'Scrape Pages',     icon: '📄' },
  { key: 'ingest',   label: 'Chunk & Embed',    icon: '🧩' },
  { key: 'generate', label: 'Generate Answer',  icon: '✨' },
]

export default function PipelineSteps({ steps, pipelineData }) {
  if (Object.keys(steps).length === 0) return null

  return (
    <div className="animate-slide-up">
      <div className="rounded-2xl border border-white/[0.06] bg-[#111827]/80 backdrop-blur-lg p-6">
        <div className="flex items-center gap-2 mb-4">
          <div className="w-2 h-2 rounded-full bg-emerald-500" />
          <span className="text-sm font-semibold text-slate-300 uppercase tracking-wider">Pipeline Progress</span>
        </div>

        <div className="space-y-1">
          {STEPS_CONFIG.map(({ key, label, icon }) => {
            const status = steps[key]
            if (!status) return (
              <StepRow key={key} icon={icon} label={label} status="pending" />
            )
            return (
              <StepRow
                key={key}
                icon={icon}
                label={label}
                status={status}
                detail={getDetail(key, pipelineData[key])}
              />
            )
          })}
        </div>
      </div>
    </div>
  )
}

function StepRow({ icon, label, status, detail }) {
  const statusColors = {
    pending: 'text-slate-600',
    running: 'text-amber-400',
    done: 'text-emerald-400',
  }

  return (
    <div className={`flex items-center gap-3 py-2 px-3 rounded-lg transition-all duration-300
      ${status === 'running' ? 'bg-amber-500/[0.06]' : ''}
      ${status === 'done' ? 'bg-emerald-500/[0.04]' : ''}
    `}>
      <span className="text-base w-6 text-center">{icon}</span>
      <span className={`text-sm font-medium flex-1 ${status === 'pending' ? 'text-slate-600' : 'text-slate-300'}`}>
        {label}
      </span>
      {status === 'running' && (
        <svg className="animate-spin h-3.5 w-3.5 text-amber-400" viewBox="0 0 24 24">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
        </svg>
      )}
      {status === 'done' && (
        <svg className="h-3.5 w-3.5 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
        </svg>
      )}
      {detail && <span className="text-[10px] text-slate-500 ml-1">{detail}</span>}
    </div>
  )
}

function getDetail(key, data) {
  if (!data) return null
  switch (key) {
    case 'map': return data.total_links ? `${data.total_links} links` : null
    case 'filter': return data.count ? `${data.count} selected` : null
    case 'scrape': return data.scraped_count ? `${data.scraped_count} pages` : null
    default: return null
  }
}
