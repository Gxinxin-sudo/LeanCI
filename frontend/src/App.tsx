import { useState } from 'react'

import { ResultsPanel } from './components/ResultsPanel'
import { TokenPanel } from './components/TokenPanel'
import { SAMPLE_LOG } from './data/sample'
import { analyzeLog } from './lib/api'
import type { AnalysisResult } from './types/api'

export const MAX_LOG_CHARACTERS = 120_000

type AnalysisState =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'success'; data: AnalysisResult }
  | { status: 'error'; message: string }

function SignalTrack() {
  const stages = ['Ingest', 'Triage', 'Evidence']

  return (
    <div className="signal-track" aria-label="Analysis stages">
      {stages.map((stage, index) => (
        <div className="signal-stage" key={stage}>
          <span className={`signal-node ${index === 0 ? 'signal-node-active' : ''}`} aria-hidden="true" />
          <span className="font-mono text-[0.62rem] uppercase tracking-[0.2em] text-muted">
            {stage}
          </span>
        </div>
      ))}
    </div>
  )
}

function BrandMark() {
  return (
    <div className="grid h-9 w-9 place-items-center border border-line-bright bg-panel" aria-hidden="true">
      <svg className="h-5 w-5 text-signal" viewBox="0 0 24 24" fill="none">
        <path d="M5 5v14h14" stroke="currentColor" strokeWidth="1.5" />
        <path d="m8 15 3-4 3 2 4-6" stroke="currentColor" strokeWidth="1.5" />
      </svg>
    </div>
  )
}

export function App() {
  const [logText, setLogText] = useState('')
  const [analysisState, setAnalysisState] = useState<AnalysisState>({ status: 'idle' })

  const handleAnalyze = async () => {
    if (!logText.trim()) {
      setAnalysisState({
        status: 'error',
        message: 'Paste a CI log or load the sample before starting analysis.',
      })
      return
    }

    setAnalysisState({ status: 'loading' })
    try {
      const result = await analyzeLog(logText)
      setAnalysisState({ status: 'success', data: result })
    } catch (error) {
      setAnalysisState({
        status: 'error',
        message: error instanceof Error ? error.message : 'The analysis request failed.',
      })
    }
  }

  const activeStats =
    analysisState.status === 'success' ? analysisState.data.compression_stats : undefined

  return (
    <div className="min-h-screen bg-ink text-fog">
      <header className="border-b border-line bg-ink/95">
        <div className="mx-auto flex max-w-[96rem] items-center justify-between px-5 py-4 lg:px-8">
          <div className="flex items-center gap-3">
            <BrandMark />
            <div>
              <p className="font-display text-lg font-semibold tracking-tight text-white">LeanCI</p>
              <p className="font-mono text-[0.58rem] uppercase tracking-[0.2em] text-muted">
                Failure workbench
              </p>
            </div>
          </div>
          <div className="hidden items-center gap-3 sm:flex">
            <span className="status-dot status-dot-offline" aria-hidden="true" />
            <span className="font-mono text-[0.62rem] uppercase tracking-[0.18em] text-muted">
              Phase 01 / Mock
            </span>
          </div>
        </div>
      </header>

      <div className="border-b border-fault/30 bg-fault/8">
        <div className="mx-auto flex max-w-[96rem] items-center gap-3 px-5 py-3 lg:px-8">
          <span className="h-2 w-2 shrink-0 bg-fault" aria-hidden="true" />
          <p className="font-mono text-[0.68rem] uppercase tracking-[0.12em] text-fault-soft">
            Demo data — Paritok not connected
          </p>
        </div>
      </div>

      <main className="mx-auto max-w-[96rem] px-5 py-8 lg:px-8 lg:py-10">
        <section className="grid gap-8 border-b border-line pb-8 lg:grid-cols-[minmax(0,1fr)_minmax(28rem,0.72fr)] lg:items-end">
          <div>
            <p className="font-mono text-[0.65rem] uppercase tracking-[0.24em] text-signal">
              CI failure / structured triage
            </p>
            <h1 className="mt-4 max-w-4xl font-display text-4xl font-semibold leading-[1.04] tracking-[-0.03em] text-white sm:text-5xl lg:text-6xl">
              Find the line that broke the build.
              <span className="block text-muted">Keep every claim inspectable.</span>
            </h1>
            <p className="mt-5 max-w-2xl text-sm leading-7 text-muted sm:text-base">
              Paste a failure log and exercise the complete response contract locally. This stage
              returns deterministic demo evidence and never contacts an external model.
            </p>
          </div>
          <SignalTrack />
        </section>

        <div className="mt-8 grid gap-6 xl:grid-cols-[minmax(22rem,0.72fr)_minmax(0,1.28fr)]">
          <aside className="space-y-4 xl:sticky xl:top-6 xl:self-start">
            <section className="border border-line bg-panel" aria-labelledby="log-input-title">
              <div className="flex items-start justify-between gap-4 border-b border-line px-5 py-4">
                <div>
                  <p className="font-mono text-[0.62rem] uppercase tracking-[0.2em] text-muted">
                    Input / untrusted text
                  </p>
                  <h2 id="log-input-title" className="mt-1 font-display text-lg font-semibold text-white">
                    CI failure log
                  </h2>
                </div>
                <button
                  className="border border-line-bright px-3 py-2 font-mono text-[0.62rem] uppercase tracking-[0.14em] text-fog transition-colors hover:border-signal hover:text-signal focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-signal"
                  type="button"
                  onClick={() => {
                    setLogText(SAMPLE_LOG)
                    setAnalysisState({ status: 'idle' })
                  }}
                >
                  Load sample
                </button>
              </div>

              <div className="p-5">
                <label className="sr-only" htmlFor="ci-log">
                  Paste CI failure log
                </label>
                <textarea
                  id="ci-log"
                  className="min-h-80 w-full resize-y border border-line bg-terminal p-4 font-mono text-xs leading-6 text-fog caret-signal outline-none transition-colors placeholder:text-muted/60 focus:border-signal"
                  maxLength={MAX_LOG_CHARACTERS}
                  placeholder="$ paste failing CI output here…"
                  spellCheck={false}
                  value={logText}
                  onChange={(event) => {
                    setLogText(event.target.value)
                    if (analysisState.status !== 'loading') {
                      setAnalysisState({ status: 'idle' })
                    }
                  }}
                />
                <div className="mt-3 flex items-center justify-between gap-4">
                  <p className="text-[0.68rem] leading-5 text-muted">
                    Text only. Commands are displayed, never executed.
                  </p>
                  <p className="shrink-0 font-mono text-[0.65rem] text-muted">
                    {logText.length.toLocaleString('en-US')} /{' '}
                    {MAX_LOG_CHARACTERS.toLocaleString('en-US')}
                  </p>
                </div>

                <div className="mt-5 flex gap-3">
                  <button
                    className="flex flex-1 items-center justify-center gap-2 border border-signal bg-signal px-4 py-3 font-mono text-xs font-bold uppercase tracking-[0.12em] text-ink transition-colors hover:bg-signal-bright disabled:cursor-wait disabled:border-muted disabled:bg-muted focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-signal"
                    type="button"
                    disabled={analysisState.status === 'loading'}
                    onClick={() => void handleAnalyze()}
                  >
                    {analysisState.status === 'loading' ? (
                      <>
                        <span className="loading-mark loading-mark-dark" aria-hidden="true" />
                        Analyzing failure…
                      </>
                    ) : (
                      <>
                        Analyze failure
                        <span aria-hidden="true">→</span>
                      </>
                    )}
                  </button>
                  {logText.length > 0 && (
                    <button
                      className="border border-line-bright px-4 py-3 font-mono text-[0.65rem] uppercase tracking-[0.12em] text-muted hover:border-fault hover:text-fault focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-fault"
                      type="button"
                      onClick={() => {
                        setLogText('')
                        setAnalysisState({ status: 'idle' })
                      }}
                    >
                      Clear
                    </button>
                  )}
                </div>
              </div>
            </section>

            <TokenPanel
              stats={activeStats}
              loading={analysisState.status === 'loading'}
            />
          </aside>

          <ResultsPanel state={analysisState} />
        </div>
      </main>

      <footer className="mx-auto flex max-w-[96rem] flex-col gap-2 border-t border-line px-5 py-6 text-xs text-muted sm:flex-row sm:items-center sm:justify-between lg:px-8">
        <p>LeanCI phase-one local skeleton</p>
        <p className="font-mono text-[0.62rem] uppercase tracking-[0.16em]">
          No Paritok · No DeepSeek · No command execution
        </p>
      </footer>
    </div>
  )
}
