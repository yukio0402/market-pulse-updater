# Market Pulse Updater

Public execution shell for guarded updates of four private market dashboards:
the company and family Fable5 editions plus the company and family classic
editions.
This repository contains no dashboard source, market snapshot, credentials, or
private repository identifiers.

## Schedule

GitHub Actions runs at 06:23, 07:23, 15:38, and 18:57 JST. A manual run can set
`force=1` to force a full market-data fetch.

`TODAY'S BRIEF / MARKET WIRE` retains its existing schedule: static Nikkei and
theme feeds run at 06:17 and 15:47 JST, while the live `/api/news` feed keeps
its independent 15-minute Cloudflare cache.

The classic company dashboard runs at 08:00 and 15:45 JST. The classic family
dashboard runs at 05:30, 07:00, 08:47, 16:17, and 17:37 JST.

## Safeguards

- The company snapshot is fetched and validated before either repository moves.
- Duplicate dates, unsorted rows, stale series, internal gaps, non-positive
  prices, and isolated scale anomalies fail the run.
- Recent weekend bond observations are removed before validation so sovereign
  yields retain business-day daily cadence without synthetic Saturday/Sunday
  points.
- Weekend or future-dated final rows, future bond observations, and any recent
  weekend bond observations that remain after normalization fail the run,
  including forced refreshes.
- Generated files are committed as one atomic snapshot.
- Only an explicit generated-file allowlist can be committed.
- The family snapshot is byte-copied from the validated company snapshot.
- Both Cloudflare deployments must expose the same date, row count, and SHA-256
  market hash before the run succeeds.
- Optional context feeds retain their last valid JSON on failure.
- DFL files and DFL build steps are intentionally excluded.
- Classic snapshots use the same validated data generator and are independently
  checked against their public Cloudflare health endpoint after each push.

## Required secrets

- `COMPANY_REPOSITORY`
- `FAMILY_REPOSITORY`
- `COMPANY_DEPLOY_KEY`
- `FAMILY_DEPLOY_KEY`
- `COMPANY_HEALTH_URL`
- `FAMILY_HEALTH_URL`
- `COMPANY_BASIC_USER`
- `COMPANY_BASIC_PASSWORD`
- `FAMILY_BASIC_USER`
- `FAMILY_BASIC_PASSWORD`
- `CLASSIC_COMPANY_REPOSITORY`
- `CLASSIC_FAMILY_REPOSITORY`
- `CLASSIC_COMPANY_DEPLOY_KEY`
- `CLASSIC_FAMILY_DEPLOY_KEY`

The deploy keys are independent and write-enabled only for their corresponding
private repository.
