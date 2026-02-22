import { useState, useRef, useCallback } from 'react'
import QueryForm from './components/QueryForm'
import PipelineSteps from './components/PipelineSteps'
import LogStream from './components/LogStream'
import AnswerPanel from './components/AnswerPanel'

const API_URL = 'http://localhost:8000'

function App() {
  const [isRunning, setIsRunning] = useState(false)
  const [logs, setLogs] = useState([])
  const [steps, setSteps] = useState({})
  const [answer, setAnswer] = useState('')
  const [pipelineData, setPipelineData] = useState({})
  const abortRef = useRef(null)

  const addLog = useCallback((message, type = 'info') => {
    const ts = new Date().toLocaleTimeString('en-US', { hour12: false })
    setLogs(prev => [...prev, { ts, message, type }])
  }, [])

  const handleSubmit = useCallback(async ({ url, query, limit }) => {
    // Reset state
    setLogs([])
    setSteps({})
    setAnswer('')
    setPipelineData({})
    setIsRunning(true)

    addLog(`Starting RAG pipeline...`, 'system')
    addLog(`URL: ${url}`, 'info')
    addLog(`Query: ${query}`, 'info')
    addLog(`Limit: ${limit} URLs`, 'info')

    try {
      const response = await fetch(`${API_URL}/api/rag`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url, query, limit }),
      })

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const event = JSON.parse(line.slice(6))
              processEvent(event)
            } catch { /* skip malformed */ }
          }
        }
      }
    } catch (err) {
      addLog(`Connection error: ${err.message}`, 'error')
    } finally {
      setIsRunning(false)
    }
  }, [addLog])

  const processEvent = useCallback((event) => {
    const { step, status, data } = event

    // Update step status
    setSteps(prev => ({ ...prev, [step]: status }))

    // Store step-specific data
    setPipelineData(prev => ({
      ...prev,
      [step]: { ...prev[step], ...data, status },
    }))

    // Log events
    switch (step) {
      case 'init':
        if (status === 'running') addLog('Initializing models...', 'system')
        if (status === 'done') {
          addLog(`Chat model: ${data.chat_model}`, 'success')
          addLog(`Embed model: ${data.embed_model}`, 'success')
        }
        break
      case 'map':
        if (status === 'running') addLog(`Mapping documentation from: ${data.url}`, 'info')
        if (status === 'done') addLog(`Found ${data.total_links} sub-links`, 'success')
        break
      case 'filter':
        if (status === 'running') addLog(`Filtering ${data.total_urls} URLs for relevance...`, 'info')
        if (status === 'done') {
          addLog(`Selected ${data.count} relevant URLs:`, 'success')
          data.selected_urls?.forEach(u => addLog(`  → ${u}`, 'url'))
        }
        break
      case 'scrape':
        if (status === 'running') addLog(`Scraping ${data.urls?.length} pages...`, 'info')
        if (status === 'done') addLog(`Successfully scraped ${data.scraped_count} pages`, 'success')
        break
      case 'ingest':
        if (status === 'running') addLog(`Chunking & embedding ${data.doc_count} documents...`, 'info')
        if (status === 'done') addLog(`Ingested into ChromaDB ✓`, 'success')
        break
      case 'generate':
        if (status === 'running') addLog(`Generating answer with RAG chain...`, 'info')
        if (status === 'done') {
          addLog(`Answer generated ✓`, 'success')
          setAnswer(data.answer)
        }
        break
      case 'complete':
        addLog('Pipeline complete!', 'system')
        break
      case 'error':
        addLog(`Error: ${data.message}`, 'error')
        break
    }
  }, [addLog])

  return (
    <div className="min-h-screen bg-[#0a0e1a]">
      {/* Header */}
      <header className="border-b border-white/5 bg-[#0a0e1a]/80 backdrop-blur-xl sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center">
            <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
            </svg>
          </div>
          <div>
            <h1 className="text-xl font-bold text-white tracking-tight">DocsRAG</h1>
            <p className="text-xs text-slate-500">Live Documentation Intelligence</p>
          </div>
        </div>
      </header>

      {/* Main Layout */}
      <main className="max-w-7xl mx-auto px-6 py-8 grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column — Input + Steps */}
        <div className="lg:col-span-4 space-y-6">
          <QueryForm onSubmit={handleSubmit} isRunning={isRunning} />
          <PipelineSteps steps={steps} pipelineData={pipelineData} />
        </div>

        {/* Right Column — Logs + Answer */}
        <div className="lg:col-span-8 space-y-6">
          <LogStream logs={logs} />
          {answer && <AnswerPanel answer={answer} />}
        </div>
      </main>
    </div>
  )
}

export default App
