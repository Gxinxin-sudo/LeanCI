# Final Submission Checklist

Items marked `[MANUAL]` require the owner to use an account, browser, credential, or publishing UI.

## Repository release

- [ ] Final quality commands pass and their exact counts are recorded.
- [ ] Fresh-install verification passes from a clean dependency environment.
- [ ] Docker production build passes within the project time limit.
- [ ] Markdown local links and required external links pass.
- [ ] Working tree is clean after the final release commit.
- [ ] `v1.0.0` points to the final release commit.
- [ ] `main` and `v1.0.0` are pushed to GitHub.
- [ ] GitHub shows the repository as Public and recognizes Apache-2.0.
- [ ] GitHub About section shows License and, if desired, a Project URL.
- [ ] Secret scan covers the current tree and Git history; no real secret is printed or committed.

## Product evidence

- [x] Formal route is fixed through Paritok; no request-level Mock/Direct/model/URL switch.
- [x] Model is fixed to `deepseek-v4-flash`.
- [x] Token proof is derived from per-request Paritok `/stats` deltas.
- [x] Paritok `estimated_cost_saved_usd` is excluded.
- [x] Three saved real Sample captures exist and match their committed JSON.
- [x] Frozen five-case Benchmark includes all rows and does not invent skipped Token values.
- [ ] `[MANUAL]` Public live Demo is secured and reachable, or use the public repository as the
  Devpost Project URL. Do not expose the current internal Railway deployment.

## Video

- [ ] `[MANUAL]` Record the shots in `RECORDING_SHOT_LIST.md`.
- [ ] `[MANUAL]` Final duration is below 3:00.
- [ ] `[MANUAL]` Video shows long log, one-click Sample, analysis, root cause, evidence, Patch,
  original/compressed/saved Token data, Benchmark, architecture, and GitHub.
- [ ] `[MANUAL]` Video contains no secret/account/private data or copyrighted music.
- [ ] `[MANUAL]` Upload to public YouTube or Vimeo and verify in a signed-out window.

## Devpost fields

- [ ] `[MANUAL]` Join the hackathon and confirm student/eligibility rules.
- [ ] `[MANUAL]` Project name: `LeanCI`.
- [ ] `[MANUAL]` Tagline: `Token-Efficient AI Debugging for Massive CI Logs`.
- [ ] `[MANUAL]` Project URL: public live Demo if safely available; otherwise
  `https://github.com/Gxinxin-sudo/LeanCI`.
- [ ] `[MANUAL]` Repository URL: `https://github.com/Gxinxin-sudo/LeanCI`.
- [ ] `[MANUAL]` Paste the matching sections from `DEVPOST_DESCRIPTION.md`.
- [ ] `[MANUAL]` Paste public video URL.
- [ ] `[MANUAL]` Enter the Paritok account email only in Devpost.
- [ ] `[MANUAL]` Add social URL if published.
- [ ] `[MANUAL]` Add screenshots and sample outputs.
- [ ] `[MANUAL]` Preview every link in a signed-out/private browser.
- [ ] `[MANUAL]` Submit before Aug 5, 2026 at 12:00am PDT; reconfirm the live Devpost page.

## Optional prizes and feedback

- [ ] `[MANUAL]` Publish `SOCIAL_POST.md` with `#BuiltWithParitok`.
- [ ] `[MANUAL]` Convert `PARITOK_FEEDBACK_TEMPLATE.md` into a focused reproducible GitHub issue
  tagged `hackathon-feedback`; do not include keys or private traces.
- [ ] `[MANUAL]` Save the final Devpost project URL and submission confirmation.
