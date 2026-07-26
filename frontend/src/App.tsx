import { useEffect, useRef, useState } from 'react'

import { BenchmarkPage } from './components/BenchmarkPage'
import { ResultsPanel } from './components/ResultsPanel'
import { TokenPanel } from './components/TokenPanel'
import { analyzeLog, getHealth, getSample, getSampleCapture } from './lib/api'
import {
  FILE_ACCEPT,
  MAX_FILE_BYTES,
  MAX_LOG_BYTES,
  MAX_LOG_CHARACTERS,
  MAX_TOTAL_FILE_BYTES,
  MAX_UPLOAD_FILES,
  formatBytes,
  readTextFiles,
  utf8Bytes,
  validateSubmission,
} from './lib/input'
import type { AnalysisResult, HealthResponse, UploadedTextFile } from './types/api'

export { MAX_LOG_CHARACTERS }

type AnalysisState =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'success'; data: AnalysisResult }
  | { status: 'error'; message: string }

type HealthState =
  | { status: 'checking' }
  | { status: 'ready'; data: HealthResponse }
  | { status: 'unreachable'; message: string }

const SAMPLE_CARDS = [
  {
    id: 'python-pytest',
    kicker: 'pytest',
    title: 'Python pytest failure',
    description: '823 tests pass before one retry-cap assertion exposes a precedence bug.',
  },
  {
    id: 'typescript-build',
    kicker: 'tsc --strict',
    title: 'TypeScript build failure',
    description: 'A required deployment region receives string | undefined.',
  },
  {
    id: 'docker-build',
    kicker: 'buildkit',
    title: 'Docker build failure',
    description: 'An ignore rule silently removes package manifests from the build context.',
  },
  {
    id: 'dependency-resolution',
    kicker: 'npm ERESOLVE',
    title: 'Dependency resolution failure',
    description: 'A React 19 tree conflicts with a package that requires React 18.',
  },
  {
    id: 'github-actions-environment',
    kicker: 'actions env',
    title: 'GitHub Actions environment failure',
    description: 'An unset repository variable reaches a fail-fast environment check.',
  },
] as const

function BrandMark() {
  return (
    <span className="brand-mark" aria-hidden="true">
      <i />
      <i />
      <i />
    </span>
  )
}

function HealthStrip({
  health,
  onRefresh,
}: {
  health: HealthState
  onRefresh: () => void
}) {
  const ready = health.status === 'ready'
  const healthy = ready && health.data.status === 'ok'
  const message =
    health.status === 'checking'
      ? 'Checking FastAPI → Paritok → hosted GPU'
      : health.status === 'unreachable'
        ? health.message
        : health.data.message

  return (
    <section className="route-strip" aria-label="Formal analysis route status">
      <div className="route-strip-main">
        <span className={`status-light ${healthy ? 'status-light-ok' : ''}`} aria-hidden="true" />
        <div>
          <p className="eyebrow">Formal route status</p>
          <p className="route-message">{message}</p>
        </div>
      </div>
      <dl>
        <div>
          <dt>FastAPI</dt>
          <dd>{ready ? 'Online' : health.status === 'checking' ? 'Checking' : 'Offline'}</dd>
        </div>
        <div>
          <dt>Paritok</dt>
          <dd>{ready && health.data.paritok_connected ? 'Connected' : 'Unavailable'}</dd>
        </div>
        <div>
          <dt>Hosted GPU</dt>
          <dd>{ready && health.data.hosted_gpu_available ? 'Ready' : 'Unavailable'}</dd>
        </div>
        <div>
          <dt>Model</dt>
          <dd>{ready ? health.data.model : 'deepseek-v4-flash'}</dd>
        </div>
      </dl>
      <button type="button" className="text-action" onClick={onRefresh}>Refresh</button>
    </section>
  )
}

function SampleRail({
  activeId,
  disabled,
  loadingId,
  onLoad,
}: {
  activeId: string | null
  disabled: boolean
  loadingId: string | null
  onLoad: (sampleId: string) => void
}) {
  return (
    <section className="sample-rail" aria-labelledby="sample-title">
      <div className="sample-intro">
        <p className="eyebrow">Start with a known answer</p>
        <h2 id="sample-title">One-click samples</h2>
        <p>Bundled locally. No repository clone and no code execution.</p>
      </div>
      <div className="sample-cards">
        {SAMPLE_CARDS.map((sample) => {
          const active = sample.id === activeId
          const loading = sample.id === loadingId
          return (
            <button
              className={`sample-card ${active ? 'sample-card-active' : ''}`}
              type="button"
              key={sample.id}
              disabled={disabled || loadingId !== null}
              onClick={() => onLoad(sample.id)}
            >
              <span>{sample.kicker}</span>
              <strong>{loading ? 'Loading sample…' : sample.title}</strong>
              <small>{sample.description}</small>
              <b>{active ? 'Loaded ✓' : 'Load sample →'}</b>
            </button>
          )
        })}
      </div>
    </section>
  )
}

function UploadedFiles({
  disabled,
  files,
  onRemove,
}: {
  disabled: boolean
  files: UploadedTextFile[]
  onRemove: (index: number) => void
}) {
  const total = files.reduce((sum, file) => sum + utf8Bytes(file.content), 0)
  return (
    <div className="upload-area">
      <div className="upload-heading">
        <div>
          <p className="eyebrow">Related files · optional</p>
          <h3>Text context</h3>
        </div>
        <span>{files.length}/{MAX_UPLOAD_FILES} files · {formatBytes(total)}/{formatBytes(MAX_TOTAL_FILE_BYTES)}</span>
      </div>
      {files.length > 0 ? (
        <ul className="upload-list">
          {files.map((file, index) => (
            <li key={`${file.name}-${index}`}>
              <span>
                <strong>{file.name}</strong>
                <small>{formatBytes(utf8Bytes(file.content))} · UTF-8 text</small>
              </span>
              <button
                type="button"
                disabled={disabled}
                onClick={() => onRemove(index)}
                aria-label={`Remove ${file.name}`}
              >
                Remove
              </button>
            </li>
          ))}
        </ul>
      ) : (
        <p className="upload-empty">Add up to five source, config, log, or documentation files.</p>
      )}
    </div>
  )
}

export function App() {
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [logText, setLogText] = useState('')
  const [files, setFiles] = useState<UploadedTextFile[]>([])
  const [activeSampleId, setActiveSampleId] = useState<string | null>(null)
  const [sampleLoadingId, setSampleLoadingId] = useState<string | null>(null)
  const [analysisState, setAnalysisState] = useState<AnalysisState>({ status: 'idle' })
  const [healthState, setHealthState] = useState<HealthState>({ status: 'checking' })
  const [inputMessage, setInputMessage] = useState('')
  const captureMode = new URLSearchParams(window.location.search).has('capture')
  const benchmarkMode = new URLSearchParams(window.location.search).get('view') === 'benchmark'

  const refreshHealth = async () => {
    setHealthState({ status: 'checking' })
    try {
      setHealthState({ status: 'ready', data: await getHealth() })
    } catch (error) {
      setHealthState({
        status: 'unreachable',
        message: error instanceof Error ? error.message : 'LeanCI API is unreachable.',
      })
    }
  }

  useEffect(() => {
    if (benchmarkMode) return
    let active = true
    void getHealth()
      .then((data) => {
        if (active) setHealthState({ status: 'ready', data })
      })
      .catch((error: unknown) => {
        if (active) {
          setHealthState({
            status: 'unreachable',
            message: error instanceof Error ? error.message : 'LeanCI API is unreachable.',
          })
        }
      })
    return () => {
      active = false
    }
  }, [benchmarkMode])

  useEffect(() => {
    if (benchmarkMode) return
    const captureId = new URLSearchParams(window.location.search).get('capture')
    if (!captureId || !SAMPLE_CARDS.some((sample) => sample.id === captureId)) return

    let active = true
    void Promise.all([getSample(captureId), getSampleCapture(captureId)])
      .then(([sample, capture]) => {
        if (!active) return
        setLogText(sample.log_text)
        setFiles(sample.files)
        setActiveSampleId(sample.id)
        setAnalysisState({ status: 'success', data: capture.analysis_result })
        setInputMessage(
          `Saved real run captured ${new Date(capture.captured_at).toLocaleString()}. Re-run Analyze failure for fresh stats.`,
        )
      })
      .catch((error: unknown) => {
        if (!active) return
        setAnalysisState({
          status: 'error',
          message: error instanceof Error ? error.message : 'The saved capture could not be loaded.',
        })
      })
    return () => {
      active = false
    }
  }, [benchmarkMode])

  const handleLoadSample = async (sampleId: string) => {
    setSampleLoadingId(sampleId)
    setInputMessage('')
    try {
      const sample = await getSample(sampleId)
      setLogText(sample.log_text)
      setFiles(sample.files)
      setActiveSampleId(sample.id)
      setAnalysisState({ status: 'idle' })
      setInputMessage(
        `${sample.title} loaded: ${formatBytes(sample.log_bytes)} log + ${sample.file_count} related files.`,
      )
    } catch (error) {
      setAnalysisState({
        status: 'error',
        message: error instanceof Error ? error.message : 'The sample could not be loaded.',
      })
    } finally {
      setSampleLoadingId(null)
    }
  }

  const handleFileSelection = async (selected: FileList | null) => {
    if (!selected?.length) return
    try {
      setFiles(await readTextFiles(selected, files))
      setInputMessage(`${selected.length} text file${selected.length === 1 ? '' : 's'} added.`)
      setActiveSampleId(null)
      if (analysisState.status !== 'loading') setAnalysisState({ status: 'idle' })
    } catch (error) {
      setInputMessage(error instanceof Error ? error.message : 'The files could not be added.')
    } finally {
      if (fileInputRef.current) fileInputRef.current.value = ''
    }
  }

  const handleAnalyze = async () => {
    try {
      validateSubmission(logText, files)
    } catch (error) {
      setAnalysisState({
        status: 'error',
        message: error instanceof Error ? error.message : 'The input is invalid.',
      })
      return
    }

    setAnalysisState({ status: 'loading' })
    try {
      const result = await analyzeLog(logText, files)
      setAnalysisState({ status: 'success', data: result })
      void refreshHealth()
    } catch (error) {
      setAnalysisState({
        status: 'error',
        message: error instanceof Error ? error.message : 'The analysis request failed.',
      })
    }
  }

  const clearInput = () => {
    setLogText('')
    setFiles([])
    setActiveSampleId(null)
    setInputMessage('')
    setAnalysisState({ status: 'idle' })
  }

  const logBytes = utf8Bytes(logText)
  const activeResult = analysisState.status === 'success' ? analysisState.data : undefined
  const analysisLoading = analysisState.status === 'loading'

  if (benchmarkMode) {
    return (
      <div className="app-shell">
        <header className="topbar">
          <a className="brand" href="/" aria-label="LeanCI home">
            <BrandMark />
            <span><strong>LeanCI</strong><small>Benchmark ledger</small></span>
          </a>
          <nav className="topbar-nav" aria-label="Primary navigation">
            <a href="/">Workbench</a>
            <a href="/?view=benchmark" aria-current="page">Benchmark</a>
          </nav>
          <span className="security-note">Fixed artifact · No paid action in browser</span>
        </header>
        <main id="top">
          <BenchmarkPage />
        </main>
        <footer>
          <span>LeanCI · Phase 05 benchmark</span>
          <span>Baseline uncompressed ↔ Paritok verified compression</span>
        </footer>
      </div>
    )
  }

  return (
    <div className={`app-shell ${captureMode ? 'capture-mode' : ''}`}>
      <header className="topbar">
        <a className="brand" href="#top" aria-label="LeanCI home">
          <BrandMark />
          <span><strong>LeanCI</strong><small>Failure workbench</small></span>
        </a>
        <nav className="topbar-nav" aria-label="Primary navigation">
          <a href="/" aria-current="page">Workbench</a>
          <a href="/?view=benchmark">Benchmark</a>
        </nav>
        <span className="security-note">No code execution · Uploads not stored by LeanCI</span>
      </header>

      <main id="top">
        <section className="hero">
          <div className="hero-copy">
            <p className="eyebrow">Long CI logs, reduced before analysis</p>
            <h1>
              Keep the failure.
              <span>Cut the noise.</span>
            </h1>
            <p className="hero-lede">
              LeanCI compresses massive CI context through Paritok, asks DeepSeek for a
              strict diagnosis, and proves every Token number with this request’s real
              stats delta.
            </p>
            <div className="hero-promises">
              <span>01 · Fixed production route</span>
              <span>02 · Inspectable evidence</span>
              <span>03 · Review-only patches</span>
            </div>
          </div>
          <div className="hero-instrument" aria-label="LeanCI analysis path">
            <div className="instrument-readout">
              <span>INPUT</span>
              <strong>5k+ tokens</strong>
              <small>safe, repeatable samples</small>
            </div>
            <div className="instrument-path">
              <span>FastAPI</span><i>→</i><span>Paritok GPU</span><i>→</i><span>DeepSeek</span>
            </div>
            <div className="instrument-rule">
              <span />
              <span />
              <span />
              <span />
              <span />
            </div>
            <p>Token metrics appear only after /stats proof.</p>
          </div>
        </section>

        <HealthStrip health={healthState} onRefresh={() => void refreshHealth()} />
        <SampleRail
          activeId={activeSampleId}
          disabled={analysisLoading}
          loadingId={sampleLoadingId}
          onLoad={(sampleId) => void handleLoadSample(sampleId)}
        />

        {captureMode && (
          <section className="capture-banner" aria-label="Saved real run status">
            <div>
              <p className="eyebrow">Saved real Paritok run</p>
              <h2>{activeSampleId ?? 'Loading capture…'}</h2>
            </div>
            <p>Strict stats delta and ground-truth file match loaded from this workspace.</p>
          </section>
        )}

        <section className="workbench" aria-label="LeanCI analysis workbench">
          <aside className="input-column">
            <div className="input-panel">
              <div className="panel-heading">
                <div>
                  <p className="eyebrow">Untrusted input · text only</p>
                  <h2>CI failure log</h2>
                </div>
                {(logText || files.length > 0) && (
                  <button
                    type="button"
                    className="text-action text-action-danger"
                    disabled={analysisLoading}
                    onClick={clearInput}
                  >
                    Clear all
                  </button>
                )}
              </div>
              <label className="sr-only" htmlFor="ci-log">Paste CI failure log</label>
              <textarea
                id="ci-log"
                maxLength={MAX_LOG_CHARACTERS}
                placeholder="$ Paste the complete failing CI log, or load a sample above…"
                spellCheck={false}
                disabled={analysisLoading}
                value={logText}
                onChange={(event) => {
                  setLogText(event.target.value)
                  setActiveSampleId(null)
                  setInputMessage('')
                  if (analysisState.status !== 'loading') setAnalysisState({ status: 'idle' })
                }}
              />
              <div className="input-meter">
                <span className={logBytes > MAX_LOG_BYTES ? 'limit-exceeded' : ''}>
                  {formatBytes(logBytes)} / {formatBytes(MAX_LOG_BYTES)}
                </span>
                <span>{logText.length.toLocaleString('en-US')} characters</span>
              </div>

              <UploadedFiles
                disabled={analysisLoading}
                files={files}
                onRemove={(index) => {
                  setFiles((current) => current.filter((_, itemIndex) => itemIndex !== index))
                  setActiveSampleId(null)
                }}
              />

              <div className="file-controls">
                <label
                  className="secondary-action"
                  htmlFor="related-files"
                  aria-disabled={analysisLoading}
                >
                  Add text files
                </label>
                <input
                  ref={fileInputRef}
                  id="related-files"
                  type="file"
                  accept={FILE_ACCEPT}
                  disabled={analysisLoading}
                  multiple
                  onChange={(event) => void handleFileSelection(event.target.files)}
                />
                <p>
                  {MAX_UPLOAD_FILES} files max · {formatBytes(MAX_FILE_BYTES)} each ·{' '}
                  {formatBytes(MAX_TOTAL_FILE_BYTES)} total · archives and executables blocked
                </p>
              </div>

              <p className="input-message" aria-live="polite">{inputMessage}</p>
              <button
                className="primary-action"
                type="button"
                disabled={analysisLoading}
                onClick={() => void handleAnalyze()}
              >
                {analysisState.status === 'loading' ? (
                  <><span className="loading-mark loading-mark-dark" aria-hidden="true" />Analyzing through Paritok…</>
                ) : (
                  <>Analyze failure <span aria-hidden="true">↗</span></>
                )}
              </button>
              <div className="privacy-notice">
                <strong>Privacy &amp; control</strong>
                <p>
                  LeanCI does not permanently store pasted logs or uploaded files. It
                  processes them in memory and sends them through Paritok and DeepSeek for
                  analysis, so do not include secrets. Provider retention policies still
                  apply.
                </p>
                <p>
                  Suggestions, patches, and commands are inert text for human review.
                  LeanCI never runs or applies them.
                </p>
              </div>
            </div>

            <TokenPanel
              stats={activeResult?.compression_stats}
              analysisTimeMs={activeResult?.analysis_time_ms}
              loading={analysisState.status === 'loading'}
            />
          </aside>

          <ResultsPanel state={analysisState} onRetry={() => void handleAnalyze()} />
        </section>
      </main>

      <footer>
        <span>LeanCI · Phase 05 benchmark-ready MVP</span>
        <span>FastAPI → local Paritok Proxy → hosted GPU → DeepSeek</span>
      </footer>
    </div>
  )
}
