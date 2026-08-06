# postmortem-incident-lab

A self-contained incident lab. You run a small containerized service —
`checkout-api` — together with a Redis dependency, Prometheus, and Grafana.
The service becomes unstable for a **specific, evidence-discoverable reason**.
Your job is to investigate the incident, recover the service, and write a
**blameless postmortem** backed by five screenshots.

> One Grafana panel is **deliberately missing** so you experience what
> "incomplete visibility" feels like during a real incident. Discovering and
> naming that gap is a valid prevention item.

---

## Stack

| Service        | Port  | Role                                   |
| -------------- | ----- | -------------------------------------- |
| checkout-api   | 8080  | The service under investigation        |
| inventory-redis| 6379  | Dependency (inventory store)           |
| prometheus     | 9090  | Metrics scraping                       |
| grafana        | 3000  | Dashboards (login admin / admin)       |

`checkout-api` endpoints:

- `GET /` — health, returns the deployed revision
- `GET /checkout?items=<n>` — place an order
- `GET /metrics` — Prometheus metrics

Key metrics: `checkout_requests_total{status="ok|error|rejected"}`,
`checkout_latency_seconds`, `checkout_app_info{revision}`.

---

## 1. Start the stack

```bash
git clone https://github.com/kalviumcommunity/postmortem-incident-lab.git
cd postmortem-incident-lab

chmod +x scripts/*.sh
docker compose up -d --build      # start checkout-api + redis + prometheus + grafana
docker compose ps
```

Open Grafana at http://localhost:3000 (admin / admin) → dashboard
**"Checkout API — Service Health"**.

## 2. Generate traffic (baseline)

In a second terminal:

```bash
./scripts/load.sh
```

You should see `HTTP 200` responses. This is your healthy baseline — capture it.

## 3. Trigger the incident (a bad deploy)

A new revision ships to production:

```bash
./scripts/deploy.sh v2
```

Keep the load script running and watch what happens:

```bash
docker logs checkout-api | tail
```

The service starts failing. Investigate:

- Read the container logs — what exception repeats, and which revision is it tagged with?
- Compare against the deploy history:

```bash
cat deploy-history.log
```

- Look at Grafana — notice which question you **cannot** answer from the panels
  that exist (hint: there is no error-rate panel).

## 4. Recover (rollback)

Once you have identified the operational root cause, roll back to the last
known-good revision:

```bash
./scripts/rollback.sh          # equivalent to ./scripts/deploy.sh v1
docker logs checkout-api | tail
```

Errors should stop; the load script should return to `HTTP 200`.

## 5. Confirm stable state

Give it a minute, then confirm errors are back to baseline in the logs and in
the Grafana request-rate panel.

---

## What to submit

A single PDF containing **five labelled screenshots in order**, each with a
1–2 line caption, plus a short **blameless** write-up organised into:
**timeline, impact, root cause, recovery actions, prevention.**

1. **Screenshot 1 — Initial incident:** first runtime errors in
   `docker logs checkout-api` and/or the Grafana panel where failure appears.
2. **Screenshot 2 — Escalation:** errors/latency growing as traffic continues.
3. **Screenshot 3 — Root cause:** the evidence pinning the true cause
   (logs + `deploy-history.log`). Caption states the root cause in one sentence.
4. **Screenshot 4 — Recovery:** the rollback command applied and errors falling.
5. **Screenshot 5 — Stable state:** service healthy again, timeline closed.

**Blameless rule (graded):** describe what the *system* did and why — never a
person. Say "the v2 deploy introduced a bad config," not "someone broke it."

---

## Reset

```bash
docker compose down -v
./scripts/deploy.sh v1   # optional: reset .env back to the healthy revision
```
