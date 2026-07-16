# risk-service anomaly-detection model

`model.pkl` (joblib-dumped `xgboost.XGBClassifier`) and `metrics.json` in
this directory are **committed to git** (see the repo root `.gitignore` --
only `*.pkl.tmp` is excluded) rather than trained at container-build time.

## What it predicts

Given a vendor's latest `risk_score_history` row plus the VRS delta versus
its previous row, the model predicts the probability that this vendor's
risk trajectory is anomalous (`services/anomaly/model.py`'s
`ANOMALY_THRESHOLD = 0.7` decides the boolean cutoff). "Anomalous" in the
training data means either a sharp VRS increase (risk got much worse
quickly, >15 points) or a compounding-risk pattern (poor vulnerability
exposure *and* poor external posture at once).

## Training data

Trained on **~800 synthetic samples** (a scoped-down placeholder for the
blueprint's 10,000-sample target), generated deterministically
(`SEED = 42`) using the exact same VRS weighting formula as
`services/vrs_calculator.py`, so the synthetic distribution is a reasonable
stand-in for real vendor trajectories. See `services/anomaly/train.py` for
the full generation + labeling logic.

## Retraining

```bash
make train-anomaly-model
# or directly:
docker compose run --rm risk-service python -m app.services.anomaly.train
```

This overwrites `model.pkl` and `metrics.json` in place. Commit the updated
files if you intend the change to ship.

## Fail-soft behavior

If `model.pkl` is missing (e.g. a fresh checkout before the first training
run), `services/anomaly/model.py` logs a warning and anomaly evaluation is
skipped (VRS computation itself is unaffected) -- consistent with this
project's "external/optional dependency down should degrade, not crash"
posture.
