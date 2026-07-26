import { existsSync, mkdirSync, unlinkSync, writeFileSync } from 'node:fs'
import { resolve } from 'node:path'

const CDP_BASE = 'http://127.0.0.1:9223'
const APP_ORIGIN = 'http://127.0.0.1:15173'
const RUNTIME_ROOT = resolve('artifacts/runtime/browser-smoke')
const DOWNLOAD_ROOT = resolve(RUNTIME_ROOT, 'downloads')
const COMMAND_TIMEOUT_MS = 15_000

mkdirSync(DOWNLOAD_ROOT, { recursive: true })

function withTimeout(promise, label, timeoutMs = COMMAND_TIMEOUT_MS) {
  return new Promise((resolvePromise, reject) => {
    const timer = setTimeout(
      () => reject(new Error(`${label} exceeded ${timeoutMs} ms`)),
      timeoutMs,
    )
    promise.then(
      (value) => {
        clearTimeout(timer)
        resolvePromise(value)
      },
      (error) => {
        clearTimeout(timer)
        reject(error)
      },
    )
  })
}

async function openTarget(url) {
  const response = await withTimeout(
    fetch(`${CDP_BASE}/json/new?${encodeURIComponent(url)}`, { method: 'PUT' }),
    'create browser target',
  )
  if (!response.ok) {
    throw new Error(`CDP target creation returned HTTP ${response.status}`)
  }
  return response.json()
}

async function connect(webSocketDebuggerUrl) {
  const socket = new WebSocket(webSocketDebuggerUrl)
  await withTimeout(
    new Promise((resolvePromise, reject) => {
      socket.addEventListener('open', resolvePromise, { once: true })
      socket.addEventListener(
        'error',
        () => reject(new Error('CDP WebSocket connection failed')),
        { once: true },
      )
    }),
    'CDP WebSocket connection',
  )

  let sequence = 0
  const pending = new Map()
  const eventWaiters = new Map()
  const listeners = new Map()

  socket.addEventListener('message', (event) => {
    const message = JSON.parse(String(event.data))
    if (typeof message.id === 'number') {
      const waiter = pending.get(message.id)
      if (!waiter) return
      pending.delete(message.id)
      if (message.error) {
        waiter.reject(new Error(`${message.error.code}: ${message.error.message}`))
      } else {
        waiter.resolve(message.result)
      }
      return
    }
    if (!message.method) return
    for (const listener of listeners.get(message.method) ?? []) {
      listener(message.params ?? {})
    }
    const waiters = eventWaiters.get(message.method)
    if (!waiters?.length) return
    const waiter = waiters.shift()
    waiter.resolve(message.params ?? {})
  })

  function send(method, params = {}) {
    const id = ++sequence
    return withTimeout(
      new Promise((resolvePromise, reject) => {
        pending.set(id, { resolve: resolvePromise, reject })
        socket.send(JSON.stringify({ id, method, params }))
      }),
      method,
    )
  }

  function waitForEvent(method) {
    return withTimeout(
      new Promise((resolvePromise, reject) => {
        const waiters = eventWaiters.get(method) ?? []
        waiters.push({ resolve: resolvePromise, reject })
        eventWaiters.set(method, waiters)
      }),
      method,
    )
  }

  function on(method, listener) {
    const registered = listeners.get(method) ?? []
    registered.push(listener)
    listeners.set(method, registered)
  }

  return { close: () => socket.close(), on, send, waitForEvent }
}

async function evaluate(client, expression) {
  const result = await client.send('Runtime.evaluate', {
    expression,
    awaitPromise: true,
    returnByValue: true,
  })
  if (result.exceptionDetails) {
    throw new Error('Browser evaluation raised an exception')
  }
  return result.result?.value
}

async function waitForText(client, text, timeoutMs = 10_000) {
  const deadline = Date.now() + timeoutMs
  while (Date.now() < deadline) {
    const found = await evaluate(
      client,
      `document.body?.textContent.includes(${JSON.stringify(text)}) ?? false`,
    )
    if (found) return
    await new Promise((resolvePromise) => setTimeout(resolvePromise, 100))
  }
  throw new Error(`Page never displayed required text: ${text}`)
}

async function auditPage({
  name,
  path,
  width,
  height,
  requiredText,
  exerciseActions = false,
}) {
  const target = await openTarget(`${APP_ORIGIN}${path}`)
  const client = await connect(target.webSocketDebuggerUrl)
  try {
  const consoleErrors = []
  const pageExceptions = []
  const logErrors = []
  const networkFailures = []

  client.on('Runtime.consoleAPICalled', (event) => {
    if (event.type === 'error' || event.type === 'assert') {
      consoleErrors.push(event.type)
    }
  })
  client.on('Runtime.exceptionThrown', () => pageExceptions.push('exception'))
  client.on('Log.entryAdded', (event) => {
    if (event.entry?.level === 'error') {
      logErrors.push({
        source: event.entry.source ?? 'unknown',
        text: event.entry.text ?? 'unknown',
        url: event.entry.url ?? null,
      })
    }
  })
  client.on('Network.loadingFailed', (event) => {
    if (!event.canceled) networkFailures.push(event.errorText ?? 'unknown')
  })

  await Promise.all([
    client.send('Page.enable'),
    client.send('Runtime.enable'),
    client.send('Log.enable'),
    client.send('Network.enable'),
    client.send('Emulation.setDeviceMetricsOverride', {
      width,
      height,
      deviceScaleFactor: 1,
      mobile: width <= 500,
    }),
  ])
  const loaded = client.waitForEvent('Page.loadEventFired')
  await client.send('Page.navigate', { url: `${APP_ORIGIN}${path}` })
  await loaded
  await waitForText(client, requiredText)
  await new Promise((resolvePromise) => setTimeout(resolvePromise, 500))

  let copyStatus = null
  let downloadSucceeded = null
  if (exerciseActions) {
    await client.send('Browser.grantPermissions', {
      origin: APP_ORIGIN,
      permissions: ['clipboardReadWrite', 'clipboardSanitizedWrite'],
    })
    copyStatus = await evaluate(
      client,
      `(() => {
        const button = [...document.querySelectorAll('button')]
          .find((item) => item.textContent?.trim() === 'Copy Patch')
        button?.click()
        return true
      })()`,
    )
    await waitForText(client, 'Patch copied')

    await client.send('Page.setDownloadBehavior', {
      behavior: 'allow',
      downloadPath: DOWNLOAD_ROOT,
    })
    const reportPath = resolve(DOWNLOAD_ROOT, 'leanci-report.md')
    if (existsSync(reportPath)) {
      unlinkSync(reportPath)
    }
    await evaluate(
      client,
      `(() => {
        const button = [...document.querySelectorAll('button')]
          .find((item) => item.textContent?.trim() === 'Download Report')
        button?.click()
        return true
      })()`,
    )
    const deadline = Date.now() + 5_000
    while (Date.now() < deadline && !existsSync(reportPath)) {
      await new Promise((resolvePromise) => setTimeout(resolvePromise, 100))
    }
    downloadSucceeded = existsSync(reportPath)
  }

  const metrics = await evaluate(
    client,
    `(() => {
      const root = document.querySelector('#root')
      const body = document.body
      const documentElement = document.documentElement
      return {
        rootChildren: root?.children.length ?? 0,
        bodyTextLength: body?.innerText.length ?? 0,
        viewportWidth: window.innerWidth,
        documentWidth: Math.max(
          body?.scrollWidth ?? 0,
          documentElement?.scrollWidth ?? 0
        ),
        horizontalOverflow: Math.max(
          body?.scrollWidth ?? 0,
          documentElement?.scrollWidth ?? 0
        ) - window.innerWidth,
        h1: document.querySelector('h1')?.innerText ?? '',
        sampleButtons: [...document.querySelectorAll('button')]
          .filter((button) => button.textContent?.includes('Load sample')).length,
        hasPrivacyNotice: body?.innerText.includes(
          'does not permanently store pasted logs or uploaded files'
        ) ?? false,
        hasCopyPatch: [...document.querySelectorAll('button')]
          .some((button) => button.textContent?.trim() === 'Copy Patch'),
        hasDownloadReport: [...document.querySelectorAll('button')]
          .some((button) => button.textContent?.trim() === 'Download Report'),
      }
    })()`,
  )
  const screenshot = await client.send('Page.captureScreenshot', {
    format: 'png',
    fromSurface: true,
  })
  const screenshotPath = resolve(RUNTIME_ROOT, `${name}.png`)
  writeFileSync(screenshotPath, Buffer.from(screenshot.data, 'base64'))
  return {
    name,
    path,
    metrics,
    consoleErrors,
    pageExceptions,
    logErrors,
    networkFailures,
    copyStatus,
    downloadSucceeded,
    screenshotPath,
  }
  } finally {
    client.close()
  }
}

function passes(result) {
  const noRuntimeErrors =
    result.consoleErrors.length === 0 &&
    result.pageExceptions.length === 0 &&
    result.logErrors.length === 0 &&
    result.networkFailures.length === 0
  const rendered =
    result.metrics.rootChildren > 0 &&
    result.metrics.bodyTextLength > 100 &&
    result.metrics.horizontalOverflow <= 1
  const actions =
    result.copyStatus === null ||
    (result.copyStatus === true && result.downloadSucceeded === true)
  return noRuntimeErrors && rendered && actions
}

try {
  await withTimeout(fetch(`${CDP_BASE}/json/version`), 'CDP health')
  const results = [
    await auditPage({
      name: 'home-desktop',
      path: '/',
      width: 1440,
      height: 900,
      requiredText: 'One-click samples',
    }),
    await auditPage({
      name: 'home-mobile',
      path: '/',
      width: 390,
      height: 844,
      requiredText: 'One-click samples',
    }),
    await auditPage({
      name: 'capture-desktop',
      path: '/?capture=python-pytest',
      width: 1440,
      height: 900,
      requiredText: 'Tokens Saved',
      exerciseActions: true,
    }),
    await auditPage({
      name: 'benchmark-desktop',
      path: '/?view=benchmark',
      width: 1440,
      height: 900,
      requiredText: 'Every row stays.',
    }),
  ]
  const productChecks = {
    firstOpenExplainsProduct:
      results[0].metrics.h1.includes('Keep the failure') &&
      results[0].metrics.h1.includes('Cut the noise'),
    samplesAreObvious: results[0].metrics.sampleButtons === 5,
    privacyNoticeVisible: results[0].metrics.hasPrivacyNotice,
    mobileHasNoHorizontalOverflow: results[1].metrics.horizontalOverflow <= 1,
    captureHasCopyPatch: results[2].metrics.hasCopyPatch,
    captureHasDownloadReport: results[2].metrics.hasDownloadReport,
    reportDownloadCompleted: results[2].downloadSucceeded === true,
    noBlankPages: results.every((result) => result.metrics.rootChildren > 0),
    noConsoleOrNetworkErrors: results.every((result) => passes(result)),
  }
  const passed = Object.values(productChecks).every(Boolean)
  console.log(
    JSON.stringify(
      {
        status: passed ? 'passed' : 'failed',
        productChecks,
        results,
      },
      null,
      2,
    ),
  )
  process.exitCode = passed ? 0 : 1
} catch (error) {
  console.log(
    JSON.stringify({
      status: 'error',
      message: error instanceof Error ? error.message : 'Browser smoke failed',
    }),
  )
  process.exitCode = 2
}
