# LeanCI Demo Video Script — 2:50 target

Keep the final exported video below 3:00. Use the saved real Python capture for the result sequence;
do not trigger a paid rerun while recording unless you have separately approved the cost.

## 0:00–0:15 — Problem and value

**Picture:** GitHub README title, Built with Paritok/DeepSeek badges, then the LeanCI home screen.

**Voice:** “CI logs can contain tens of thousands of noisy lines around one useful clue. LeanCI
compresses that evidence with Paritok, then asks DeepSeek for a strict, reviewable diagnosis.”

## 0:15–0:35 — Long CI log and one-click Sample

**Picture:** Open the Sample picker, choose Python pytest, and scroll the loaded 69.5 KiB log enough
to show its length and repetition. Show the two related files.

**Voice:** “I can paste a log and add a few text files, or load a fixed Sample with one click. LeanCI
does not clone or run the repository; all inputs are treated as untrusted evidence.”

## 0:35–0:55 — Analysis path

**Picture:** Show the healthy formal route status and click `Analyze failure`, or cut directly to the
saved `?capture=python-pytest` state after briefly showing the loading UI.

**Voice:** “Formal analysis cannot bypass Paritok. FastAPI checks the local Proxy, hosted GPU, and
stats, then sends the request through Paritok to `deepseek-v4-flash`. Missing proof fails closed.”

## 0:55–1:30 — Root cause, evidence, and patch

**Picture:** Hold on Summary and Root Cause, highlight the retry precedence finding, then Evidence,
Relevant Files, Recommended Changes, and Patch. Briefly show Copy Patch.

**Voice:** “The diagnosis identifies an operator-precedence bug in the retry backoff. The result is
not just a summary: it points to log evidence and files, proposes the correction, emits a Git diff,
and lists verification commands. LeanCI never executes any of them.”

## 1:30–1:52 — Token proof

**Picture:** Show `Original 23,906`, `Compressed 332`, `Saved 23,574`, and `98.61%`. Also show the
model and verified stats indicator.

**Voice:** “For this saved real request, Paritok reported 23,906 original Tokens and 332 compressed
Tokens: 23,574 saved, or 98.61%. These are the before-and-after Paritok stats delta for this request,
not a character estimate or model-generated number.”

## 1:52–2:18 — Benchmark, including the negative result

**Picture:** Open `?view=benchmark`. Show the summary and two compressed rows, then the three
`skipped_low_yield` rows and quality comparison.

**Voice:** “The controlled five-case benchmark keeps every row. Two requests compressed, averaging
85.53% Token savings across those two rows only. Three were normal low-yield skips. Quality averaged
73 for Baseline and 54 for Paritok, a negative 19-point change, so we do not claim universal quality
preservation.”

## 2:18–2:36 — Architecture

**Picture:** Show the README Mermaid architecture diagram.

**Voice:** “The fixed path is React to FastAPI, through a loopback Paritok Proxy and hosted GPU, then
DeepSeek V4 Flash. A request-count check and stats delta must pass before Token metrics appear.”

## 2:36–2:50 — Repository and close

**Picture:** Show the public GitHub repository, `examples/`, `benchmarks/report.md`, `SECURITY.md`,
Dockerfile, and Apache-2.0 license indicator.

**Voice:** “LeanCI is public under Apache 2.0 with reproducible Samples, benchmark artifacts, security
documentation, and Docker setup. It makes AI CI debugging measurable—and honest about the tradeoffs.”
