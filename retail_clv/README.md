# 🏆 CLV Prediction Engine

> **Production-grade Customer Lifetime Value prediction** using the UCI Online Retail II dataset.
> Combines probabilistic BG/NBD + Gamma-Gamma models with XGBoost ML, K-Means segmentation, MLflow experiment tracking, and a FastAPI scoring service.

---

## 📁 Project Structure

```
retail_clv/
├── data/
│   ├── raw/                    # Downloaded XLSX (~45 MB)
│   └── processed/              # Cleaned parquet files
├── pipelines/
│   ├── ingest.py               # Data download + cleaning
│   ├── features.py             # RFM + extended feature engineering
│   ├── train_bg_nbd.py         # BG/NBD + Gamma-Gamma probabilistic CLV
│   ├── train_xgboost.py        # XGBoost CLV regression + MLflow tracking
│   ├── segment.py              # K-Means segmentation → Bronze/Silver/Gold/Platinum
│   └── run_pipeline.py         # End-to-end orchestrator
├── models/                     # Serialised model artifacts (.pkl)
├── outputs/
│   ├── clv_scores.csv          # Final deliverable
│   └── reports/                # EDA + segment charts
├── notebooks/
│   └── 01_eda.ipynb            # Exploratory analysis
├── api/
│   ├── main.py                 # FastAPI app
│   ├── schemas.py              # Pydantic request/response models
│   └── predictor.py            # Model inference logic
└── requirements.txt
```

---

## ⚙️ Setup

### 1. Create the virtual environment (already created inside `retail_clv/`)

```bash
# The venv lives at retail_clv/.venv — activate it:

# Windows (PowerShell)
retail_clv\.venv\Scripts\Activate.ps1

# Windows (CMD)
retail_clv\.venv\Scripts\activate.bat

# macOS / Linux
source retail_clv/.venv/bin/activate
```

### 2. Install dependencies

```bash
# With the venv active:
pip install -r retail_clv/requirements.txt

# Or directly via the venv pip (no activation needed):
retail_clv\.venv\Scripts\pip install -r retail_clv\requirements.txt
```

> **Python 3.10 or 3.11** is recommended. The `lifetimes` library may not support 3.12+.

---

## 🚀 Running the Pipeline

### Full pipeline (downloads data automatically)

```bash
# From the retail_clv/ directory
python pipelines/run_pipeline.py
```

### Skip re-download if data already present

```bash
python pipelines/run_pipeline.py --skip-download
```

### Resume from a specific phase

```bash
python pipelines/run_pipeline.py --start-from features
python pipelines/run_pipeline.py --start-from segment
```

### Run individual phases

```bash
python pipelines/ingest.py               # Phase 1: Download + clean
python pipelines/features.py             # Phase 2: RFM features
python pipelines/train_bg_nbd.py         # Phase 3: BG/NBD + Gamma-Gamma
python pipelines/train_xgboost.py        # Phase 4: XGBoost + MLflow
python pipelines/segment.py              # Phase 5: Segmentation + output
```

---

## 📊 MLflow Experiment Tracking

After running `train_xgboost.py`, launch the MLflow UI:

```bash
mlflow ui
```

Open **http://localhost:5000** in your browser to view:
- Cross-validation RMSE, MAE, R² metrics
- Feature importance chart
- Logged model artifact

---

## 🌐 FastAPI Scoring Service

### Start the API server

```bash
# From the retail_clv/ parent directory
uvicorn api.main:app --reload --port 8000
```

Open **http://localhost:8000/docs** for the interactive Swagger UI.

### Health check

```bash
curl http://localhost:8000/health
```

```json
{
  "status": "ok",
  "models_loaded": {
    "bg_nbd": true,
    "gamma_gamma": true,
    "xgb": true,
    "xgb_scaler": true,
    "kmeans": true,
    "clv_scaler": true
  },
  "version": "1.0.0"
}
```

### Score a single customer

```bash
curl -X POST http://localhost:8000/score \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "12345",
    "transactions": [
      {"invoice_date": "2024-01-15", "quantity": 3, "unit_price": 12.50},
      {"invoice_date": "2024-03-22", "quantity": 1, "unit_price": 45.00},
      {"invoice_date": "2024-05-10", "quantity": 5, "unit_price": 8.99}
    ]
  }'
```

**Response:**

```json
{
  "customer_id": "12345",
  "predicted_clv_6months": 182.50,
  "clv_tier": "Gold",
  "churn_risk_score": 0.23,
  "expected_purchases_6m": 4.1,
  "model_used": "bg_nbd_gamma_gamma + xgboost",
  "message": null
}
```

### Batch scoring (up to 500 customers)

```bash
curl -X POST http://localhost:8000/score/batch \
  -H "Content-Type: application/json" \
  -d '[
    {
      "customer_id": "A1",
      "transactions": [{"invoice_date": "2024-02-01", "quantity": 2, "unit_price": 25.0}]
    },
    {
      "customer_id": "A2",
      "transactions": [
        {"invoice_date": "2024-01-10", "quantity": 5, "unit_price": 99.0},
        {"invoice_date": "2024-04-15", "quantity": 2, "unit_price": 55.0}
      ]
    }
  ]'
```

---

## 📄 Output: `outputs/clv_scores.csv`

| Column | Description |
|---|---|
| `customer_id` | Unique customer identifier |
| `predicted_clv_6months` | Predicted revenue over the next 180 days (£) |
| `clv_tier` | Customer segment: Bronze / Silver / Gold / Platinum |
| `churn_risk_score` | Churn probability [0, 1] — from BG/NBD P(alive) |
| `expected_purchases_6m` | Predicted number of purchases in next 6 months |
| `prob_alive` | Probability customer is still active |
| `clv_bg_nbd` | Raw BG/NBD model CLV estimate |
| `clv_xgb` | Raw XGBoost model CLV estimate |

---

## 🧠 Business Interpretation

### CLV Tiers

| Tier | Typical CLV Range | Recommended Action |
|---|---|---|
| 🥉 **Bronze** | < £50 / 6 months | Win-back email campaigns, low-cost promotions |
| 🥈 **Silver** | £50–£150 | Loyalty programme enrolment, cross-sell |
| 🥇 **Gold** | £150–£400 | Priority customer service, early access |
| 💎 **Platinum** | > £400 | VIP concierge, retention spend justified |

### Churn Risk Score

| Score | Interpretation |
|---|---|
| 0.0 – 0.3 | Low risk — customer likely to return |
| 0.3 – 0.6 | Medium risk — targeted retention recommended |
| 0.6 – 1.0 | High risk — urgent win-back action needed |

### Model Architecture

```
Historical Transactions
        │
        ▼
  ┌─────────────┐
  │  RFM Engine │  → Recency, Frequency, Monetary, T, AOV…
  └─────────────┘
        │
        ├──────────────────────────────────────┐
        ▼                                      ▼
 ┌─────────────────┐                  ┌──────────────────┐
 │ BG/NBD Model    │                  │  XGBoost Model   │
 │ + Gamma-Gamma   │                  │  (supervised)    │
 └────────┬────────┘                  └────────┬─────────┘
          │  60%                               │  40%
          └──────────┬─────────────────────────┘
                     ▼
            Ensemble CLV Score
                     │
                     ▼
            K-Means Clustering
                     │
           ┌─────────┴─────────┐
           ▼                   ▼
    CLV Tier + Churn Risk  →  outputs/clv_scores.csv
```

---

## 📈 EDA Notebook

Launch the EDA notebook (requires pipeline to have run at least Phase 1 and 2):

```bash
cd notebooks
jupyter notebook 01_eda.ipynb
```

Charts generated in `outputs/reports/`:
- `revenue_distribution.png` — Invoice revenue histogram
- `cohort_analysis.png` — Monthly customer retention heatmap
- `rfm_heatmap.png` — RFM segment value heatmap
- `country_revenue.png` — Top 15 countries by revenue
- `monthly_revenue.png` — Revenue time series
- `clv_segment_report.png` — Tier distribution + CLV box plots
- `clv_vs_churn_risk.png` — CLV vs churn scatter by tier
- `xgb_feature_importance.png` — XGBoost feature importance

---

## 🔧 Tech Stack

| Component | Library |
|---|---|
| Data processing | pandas ≥ 2.0, numpy, openpyxl |
| Probabilistic CLV | lifetimes ≥ 0.11 |
| ML CLV | xgboost ≥ 2.0, scikit-learn ≥ 1.3 |
| Experiment tracking | mlflow ≥ 2.9 |
| API | fastapi ≥ 0.104, uvicorn, pydantic v2 |
| Visualisation | matplotlib ≥ 3.8, seaborn ≥ 0.13 |
| Serialisation | joblib |

---

## ❓ Troubleshooting

**`lifetimes` install fails:**
```bash
pip install lifetimes --no-build-isolation
```

**UCI download times out:**
Download manually from https://archive.ics.uci.edu/dataset/502/online+retail+ii and place `online_retail_II.xlsx` in `data/raw/`, then run with `--skip-download`.

**MLflow experiment not showing:**
```bash
mlflow ui --backend-store-uri ./mlruns
```

---

## 📜 License

This project uses the Online Retail II dataset from UCI ML Repository, licensed under CC BY 4.0.
