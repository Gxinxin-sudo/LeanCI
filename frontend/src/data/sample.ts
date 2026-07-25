export const SAMPLE_LOG = `> dashboard@1.0.0 build
> tsc -b && vite build

src/services/report.ts:42:19
  40 | export async function publishReport(payload: Report) {
  41 |   const body = JSON.stringify(payload)
> 42 |   await uploadReport(process.env.REPORT_BUCKET, body)
     |                     ^^^^^^^^^^^^^^^^^^^^^^^^^

error TS2345: Argument of type 'string | undefined' is not assignable to parameter of type 'string'.
  Type 'undefined' is not assignable to type 'string'.

Found 1 error.
npm error Lifecycle script \`build\` failed with error:
npm error code 2`
