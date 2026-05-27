# ChatGPT Thread 1: System Design and NLP Strategy

This log records the conceptual discussions and design iterations that shaped the Competitor Grievance Signal Detector.

## Discussion 1: Architecture & Proximity Rules

**User Prompt:**
> "I need to build a high-reliability Python pipeline that scans public posts for negative feedback about recruiting platforms (HireVue, Greenhouse, etc.). It needs to run locally, require no external API keys, and must NOT use deep learning or LLMs at runtime. How should I design the complaint extraction rules so I don't get flooded with false positives like 'HireVue says competitors are expensive'?"

**ChatGPT Suggestion:**
To build a zero-dependency, non-LLM NLP extractor for this, use a layered heuristic pipeline:
1. **Sentence Segmentation:** Instead of running heavy library-based tokenizers, use regex-based sentence splitting that handles common abbreviations (`e.g.`, `i.e.`, `corp.`).
2. **Proximity Analysis:** Rather than checking whole-document co-occurrence (which generates huge false positives), enforce that the competitor mention and the complaint keyword must appear in the *same sentence*.
3. **Syntactic Heuristic Filters:** Write regex filters to look for subject-action patterns. For example, if the sentence matches `[Competitor] (claims|says|argues|states) [Grievance]`, reject the match because the competitor is the speaker making the claim about others, not the victim of the complaint.
4. **Negation Checking:** Look at a prefix window of 3 tokens before the complaint keyword. If negation words (`not`, `never`, `don't`, `isn't`) are present, skip the keyword.

**Decision:** We adopted these recommendation layers verbatim in `signals/classifier.py` and `utils/text_utils.py`.

---

## Discussion 2: Scoring Formula Design

**User Prompt:**
> "How can I map out a 100-point explainable scoring engine for these signals? I need to combine competitor confidence, complaint strength, source quality, recency, and word proximity."

**ChatGPT Suggestion:**
A balanced, 5-factor scoring model works best for sales qualification:
- **Competitor Confidence (25 pts):** Exact match (25), Case-insensitive alias (22), Typo-tolerant match (15).
- **Complaint Strength (25 pts):** Base score (15) + Strong keyword bonus (+5) + Emphasis indicators like caps or exclamations (+3 to +5).
- **Distance Score (20 pts):** Token distance between competitor name and keyword: <=3 tokens (20), <=8 tokens (15), <=15 tokens (10), >15 (5).
- **Source Quality (15 pts):** Intent-rich G2/Trustpilot reviews (15), Community Reddit posts (12), Industry Blogs (10), General feeds (8).
- **Recency Score (15 pts):** Age of content: <=7 days (15), <=30 days (12), <=90 days (8), older (4).

**Decision:** Implemented in `signals/scorer.py` as it guarantees explainability with simple, trace-friendly math.
