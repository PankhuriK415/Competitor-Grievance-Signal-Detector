# Competitor Grievance Signal Detector

A locally runnable, production-quality, serverless-compatible pipeline to detect negative sentiment and pain points about hiring-tech competitors (HackerRank, HireVue, Codility, Greenhouse, Lever). It extracts structured lead-outreach signals with explainable scoring, syncing results to both structured JSON and an SQLite database.

---

## Setup and Run

### Prerequisites
* Python 3.8 or higher.
* Python standard libraries (no external packages are required to run the pipeline).

### Installation
Clone the repository and verify your setup. You can install development dependencies (like `pytest` for the test suite) from the `requirements.txt` file:

```bash
# Clone the repository
git clone https://github.com/PankhuriK415/Competitor-Grievance-Signal-Detector.git
cd Competitor-Grievance-Signal-Detector

# (Optional) Install testing packages
pip install -r requirements.txt
```

### Running the CLI
Run the main ingestion and detection handler pipeline via the command line interface:

```bash
# Run the pipeline with default options (Ingest all mock sources, threshold 40)
python handler.py

# Ingest only Reddit documents
python handler.py --source reddit

# Ingest and filter out signals scoring below 75 (High confidence leads)
python handler.py --threshold 75

# Run with live unauthenticated HTTP fetching (Reddit JSON / Blog RSS feeds)
python handler.py --live --source reddit
```

### Running Unit Tests
Execute the comprehensive unit test suite using Python's built-in `unittest` module:

```bash
python -m unittest discover -s tests
```

---

## Data Ingestion Approach

To deliver a **reliable, production-grade integration experience** under public network constraints, this system utilizes a modular, dual-mode architecture:

1. **Connector Layer**: Implements modular connectors (`fetch_reddit`, `fetch_g2_reviews`, `fetch_trustpilot`, `fetch_public_blog_comments`).
2. **Dual-Ingestion Strategy**:
   * **Live Mode (`--live`)**: Performs unauthenticated requests to public RSS feeds and Reddit endpoints using Python's native `urllib.request`. Enforces custom user-agents, 5.0s connection timeouts, and exponential backoff retry logic.
   * **Simulator Mode (Default)**: Fallback logic that reads from a cached, high-fidelity mock dataset. This bypasses Cloudflare security mechanisms deployed by review platforms like G2 and Trustpilot which instantly block automated scraper requests (throwing `403 Forbidden` errors).
3. **Parsing & Normalization**: Standardizes fields to a target `IngestedDocument` schema, hashes content using MD5 fingerprints to reject cross-posted duplicates, and uses NLP regex heuristics (e.g. `Our company, [Company] uses...`) to extract reviewer organization names from the text.

---

## Scoring Logic

The scoring engine calculates lead confidence on a 100-point scale based on five deterministic, explainable dimensions.

$$\text{Score} = \text{Competitor Confidence} (25) + \text{Complaint Strength} (25) + \text{Distance Score} (20) + \text{Source Quality} (15) + \text{Recency} (15)$$

### Score Breakdown Details

1. **Competitor Confidence (Max 25)**:
   * Case-insensitive exact match of competitor or alias = `25`
   * Fuzzy typo match with Edit Distance 1 = `18`
   * Fuzzy typo match with Edit Distance 2 = `12`
   * Other typo matches = `8`
2. **Complaint Strength (Max 25)**:
   * Base score for matches = `15`
   * Extreme dissatisfaction keywords (e.g., `broken`, `failed`, `unfair`, `horrible`, `overpriced`) = `20`
   * Exclamation emphasis (`!`) = `+3`
   * Capitalized word emphasis (e.g. `REALLY slow`) = `+2`
3. **Distance Score (Max 20)**:
   * Competitor and complaint within 3 tokens = `20`
   * Competitor and complaint within 8 tokens = `15`
   * Competitor and complaint within 15 tokens = `10`
   * Adjacent sentences (Proximity sentence window of 1) = `12`
   * Competitor and complaint > 15 tokens (same sentence) = `5`
4. **Source Quality (Max 15)**:
   * High-intent review platforms (G2, Trustpilot) = `15`
   * Professional forums (Reddit r/recruiting) = `12`
   * Industry blogs = `10`
   * Other feeds = `8`
5. **Recency (Max 15)**:
   * Post age <= 7 days = `15`
   * Post age <= 30 days = `12`
   * Post age <= 90 days = `8`
   * Older posts = `4`

### Actionable Thresholds:
* **80 - 100**: **Strong Signal** (Immediate outbound campaign target).
* **60 - 79**: **Moderate Signal** (Warm nurturing or research target).
* **40 - 59**: **Weak Signal** (Monitored or discarded).
* **< 40**: **Discarded** (Ignored).

---

## Assumptions and Limitations

### Architecture & Design Decisions
* **Pure Python Standard Library**: Run-time modules (scoring, classification, ingestion, database management) utilize only core Python APIs. This guarantees zero dependency load times, serverless architecture compatibility, and eliminates package version conflicts.
* **Proximity Rules vs. AI**: The pipeline implements a sentence-window proximity checker (window size of 1, spanning current sentence and direct neighbors) and negation filters. It avoids heavy LLM or neural networks at runtime, prioritizing millisecond-level speed, explainable score traces, and zero-cost scaling.

### Limitations
* **Public Scrapers and Bot Protection**: Scraping platforms like G2 and Trustpilot without commercial APIs or browser session tokens is blocked by Cloudflare. In production, this detector would ingest data upstream from RSS syndicators, webhook integrations, or data-broker warehouses rather than directly crawling web pages.
* **Keyword Extensibility**: Mentions of complaints are bounded by regular expression lookups. While this provides perfect predictability, it cannot capture sarcasm or highly indirect metaphors without updating the keyword lists in `utils/config.py`.

### AI Usage & Verification Log
* **AI-Generated Components**: The 5-factor scoring coefficients, regex patterns for detecting speech claims, and unit test coverage structures were co-designed with AI suggestions. Look-behind splitting regexes were refactored after compiler checks.
* **Manually Verified Components**:
  * Typos matching constraints (ensuring "Leven" matches "Lever" while "clever" is rejected).
  * Negation analysis verifying "not slow" is discarded while "is overpriced" remains tagged.
  * SQLite database constraints ensuring inserts update on duplicate `(source_url, pain_point)`.
  * Fully executable test suite discovery using native `python -m unittest`.
