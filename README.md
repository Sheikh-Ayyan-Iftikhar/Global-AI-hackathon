# 🛡️ FreshGuard AI
### Stale-Answer Detector for AI Applications

**Detect outdated AI-generated answers. Verify claims against trusted knowledge sources. Improve AI reliability.**

FreshGuard AI is a lightweight, AI reliability monitoring MVP designed to identify outdated, contradictory, and potentially unreliable information in AI-generated answers.

It analyzes factual claims, retrieves relevant evidence from knowledge sources, compares numerical values and software versions, and generates explainable freshness assessments.

Built as a single-file Python application for rapid prototyping and hackathon demonstrations, FreshGuard AI works without paid APIs, external AI services, or databases.

---

## ✨ Key Features

### 1. Answer Analyzer
- Analyze AI-generated answers against knowledge sources.
- Extract individual factual claims.
- Classify claims into meaningful categories.
- Identify time-sensitive information.
- Retrieve relevant supporting evidence.
- Detect numerical and version contradictions.
- Generate explainable analysis reports.

### 2. Knowledge Source Management
Supports multiple knowledge source formats:

- PDF documents
- DOCX documents
- TXT documents
- Website URLs

Additional capabilities:
- Automatic text extraction.
- Text normalization and chunking.
- SHA-256 content hashing.
- In-memory source indexing.
- Source metadata management.
- Source preview and reprocessing.
- Source removal.

### 3. Hybrid Staleness Detection Engine

FreshGuard uses deterministic, rule-based detection combined with lightweight information retrieval.

Detection capabilities include:

- Price and numerical comparisons.
- Currency-aware value extraction.
- Software version comparisons.
- Date extraction and comparison.
- Temporal sensitivity analysis.
- Keyword-based contradiction signals.
- Evidence relevance scoring.

### 4. Freshness Scoring

The application calculates a freshness score using three primary factors:

**Freshness Score Formula**

Freshness Score =

100 − (0.35 × Temporal Risk + 0.40 × Contradiction Severity + 0.25 × Evidence Age Risk)

All scoring inputs are normalized between 0 and 100.

| Score | Classification |
|---|---|
| 80–100 | FRESH |
| 60–79 | REVIEW |
| 30–59 | POTENTIALLY STALE |
| 0–29 | HIGH STALE RISK |

Additional detection statuses:

- **STALE:** Evidence contradicts an answer.
- **UNVERIFIED:** Insufficient supporting evidence.
- **CONFLICT:** Retrieved sources contain conflicting information.

Missing evidence is not automatically treated as proof of stale information.

### 5. Evidence Retrieval

FreshGuard implements lightweight in-memory evidence retrieval.

Retrieval priority:

1. TF-IDF vectorization using Scikit-learn.
2. Token-overlap similarity fallback.

Relevant evidence is displayed alongside the original claim, including its source name and retrieval relevance score.

No external vector database is required.

### 6. Knowledge Update Simulation

A dedicated hackathon demonstration feature.

Simulate changes between old and updated knowledge sources.

Workflow:

OLD SOURCE → NEW SOURCE → CHANGE DETECTION → CLAIM REVALIDATION → STALE ALERT

The simulation:
- Compares SHA-256 content hashes.
- Identifies changed source content.
- Scans previously analyzed answers.
- Identifies affected price and API version claims.
- Displays potential stale-answer alerts.

### 7. Analytics Dashboard

- Total answers analyzed.
- Fresh answers.
- Stale and conflicting answers.
- Unverified answers.
- Average freshness score.
- Freshness distribution.
- Detection trends.
- Claim category distribution.

All dashboard metrics are calculated from actual application session data.

---

## 🖥️ Application Dashboard

FreshGuard AI features a modern dark-themed dashboard with a premium blue and violet visual identity.

Main sections:

| Section | Description |
|---|---|
| Overview | Application metrics and recent detections |
| Answer Analyzer | Analyze AI-generated answers |
| Knowledge Sources | Upload and manage source documents |
| Demo Lab | Execute hackathon demonstration scenarios |
| Knowledge Update | Simulate source changes |
| Detection History | Review previous analyses |
| Analytics | Visualize detection statistics |
| Settings | Configure scoring thresholds |

---

## 🧠 Detection Examples

### Scenario 1: Stale Answer

**Question:**

What is the current Premium plan price?

**AI-generated answer:**

Our Premium plan costs $99 per month.

**Latest knowledge source:**

Premium Plan: $149/month.

**Expected outcome:** STALE

The system identifies a numerical contradiction between the generated answer and retrieved evidence.

### Scenario 2: Fresh Answer

**AI-generated answer:**

Our Premium plan costs $149 per month.

**Knowledge source:**

Premium Plan: $149/month.

**Expected outcome:** FRESH, provided the evidence and freshness score satisfy the configured thresholds.

### Scenario 3: Unverified Answer

**AI-generated answer:**

Our Premium plan includes unlimited AI requests.

**Knowledge sources:**

No relevant supporting evidence.

**Expected outcome:** UNVERIFIED

The system does not automatically assume that unsupported claims are false.

### Scenario 4: Outdated Software Version

**AI-generated answer:**

The latest API version is v2.

**Latest documentation:**

Current API version is v3.

**Expected outcome:** STALE

The version comparison identifies the older version referenced in the answer.

### Scenario 5: Conflicting Knowledge

Two active knowledge sources contain different Premium plan prices.

**Expected behavior:** Identify inconsistent evidence and flag the result for further investigation.

---

## 🏗️ Architecture

FreshGuard AI uses a lightweight, single-file architecture.

```text
freshguard-ai/
│
├── freshguard_ai.py
│
└── README.md
```

The Python application internally separates its responsibilities into logical modules:

```text
FRESHGUARD AI
│
├── Streamlit Dashboard
│   ├── Overview
│   ├── Answer Analyzer
│   ├── Knowledge Sources
│   ├── Demo Lab
│   ├── Knowledge Update
│   └── Analytics
│
├── Detection Engine
│   ├── Claim Extraction
│   ├── Claim Classification
│   ├── Temporal Analysis
│   ├── Evidence Retrieval
│   ├── Contradiction Detection
│   ├── Freshness Scoring
│   └── Explanation Generation
│
├── Document Ingestion
│   ├── PDF Parser
│   ├── DOCX Parser
│   ├── TXT Parser
│   ├── Website Parser
│   └── Text Chunking
│
└── In-Memory Storage
    ├── Knowledge Sources
    ├── Extracted Claims
    ├── Analysis History
    └── Analytics
```

All functionality is implemented within `freshguard_ai.py` for easy execution and hackathon deployment.

---

## ⚙️ Technology Stack

| Technology | Purpose |
|---|---|
| Python 3.12 | Core application |
| Streamlit | Interactive dashboard |
| Scikit-learn | TF-IDF evidence retrieval |
| PyMuPDF | PDF text extraction |
| python-docx | DOCX document extraction |
| BeautifulSoup | Website content extraction |
| HTTPX | Website ingestion |
| Pandas | Analytics data processing |
| Plotly | Interactive visualizations |
| Regex | Claim, date, number and version extraction |
| SHA-256 | Source content hashing |

---

## 🚀 Installation and Setup

### Prerequisites

- Windows 10/11, Linux, or macOS
- Python 3.12
- pip package manager
- Internet connection for installing dependencies and website ingestion

### Step 1: Clone the Repository

```bash
git clone https://github.com/Sheikh-Ayyan-Iftikhar/freshguard-ai.git

cd freshguard-ai
```

Replace `YOUR_USERNAME` with your GitHub username.

### Step 2: Create a Virtual Environment

**Windows PowerShell:**

```powershell
py -3.12 -m venv .venv

.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks script execution:

```powershell
Set-ExecutionPolicy -Scope Process Bypass

.\.venv\Scripts\Activate.ps1
```

### Step 3: Install Dependencies

```bash
pip install streamlit pandas scikit-learn pymupdf python-docx beautifulsoup4 httpx plotly
```

### Step 4: Run FreshGuard AI

```bash
streamlit run freshguard_ai.py
```

### Step 5: Open the Application

```text
http://localhost:8501
```

That's it! FreshGuard AI is ready to use.

---

## 🎯 Hackathon Demonstration Guide

For the best demonstration experience:

**Step 1 — Launch the Application**

Start FreshGuard AI and open the dashboard.

**Step 2 — Load Demo Data**

Navigate to Demo Lab and click:

`Load / reset demo knowledge`

This loads sample pricing, company policy, product documentation, and API documentation.

**Step 3 — Demonstrate Stale Detection**

Execute the stale pricing scenario.

Show the difference:

```text
AI ANSWER             CURRENT SOURCE

$99/month      →     $149/month

       STALE DETECTED
```

**Step 4 — Demonstrate Fresh Detection**

Run the fresh pricing scenario using $149/month.

**Step 5 — Demonstrate Unverified Claims**

Analyze the unlimited AI requests claim.

**Step 6 — Demonstrate Version Detection**

Compare API v2 with the documented API v3.

**Step 7 — Demonstrate Knowledge Updates**

Navigate to Knowledge Update and run the simulation.

Show how changes in source content can affect previously analyzed answers.

**Step 8 — Explore Analytics**

Show the detection history and analytics dashboard.

---

## 📊 Evaluation and Reliability

FreshGuard AI is designed to make AI answer validation explainable.

Each analysis can expose:

- Original factual claim.
- Claim category.
- Temporal sensitivity.
- Freshness score.
- Detection status.
- Retrieved evidence.
- Source references.
- Contradiction explanation.
- Recommended corrective action.

**Important:** No benchmark precision, recall, F1 score, or false-positive rate is claimed in this MVP. A formally evaluated test dataset and automated evaluation suite have not yet been implemented.

---

## 🔒 Data Privacy and Storage

FreshGuard AI follows a database-free architecture.

- No PostgreSQL.
- No MySQL.
- No MongoDB.
- No SQLite.
- No Redis.
- No vector database.
- No mandatory cloud infrastructure.
- No authentication or registration.

Application data is maintained in Streamlit session state.

**Important:** Uploaded documents and analysis history are temporary. They are not guaranteed to persist across sessions or application restarts.

---

## ⚠️ Current MVP Limitations

This is a hackathon MVP, not an enterprise-grade production monitoring platform.

Current limitations include:

1. Claim extraction is primarily deterministic and sentence-based.
2. Semantic retrieval uses TF-IDF rather than transformer embeddings.
3. Contradiction detection relies on numerical, version, date, and keyword-based heuristics.
4. Source age is a weak freshness signal and does not establish whether information is correct.
5. Website ingestion is intended for accessible public pages, not authenticated websites.
6. The knowledge update simulator currently demonstrates source changes using predefined sample content.
7. Data is temporary and session-based.
8. The optional LLM environment configuration is reserved for future integration; external LLM calls are not currently implemented.
9. Automated benchmark evaluation and REST API endpoints are not included in this single-file edition.

---

## 🔮 Future Improvements

Potential future development:

- OpenAI-compatible LLM integration.
- Sentence Transformers for semantic retrieval.
- Claim-level revalidation when knowledge sources change.
- Automated stale-answer monitoring.
- Real-time AI response interception.
- REST API integration for external AI applications.
- Automated regression testing.
- Measured precision, recall, and F1 evaluation.
- Persistent source version management.
- Advanced semantic contradiction detection.
- Production deployment architecture.

---

## 💡 Why FreshGuard AI?

AI systems can generate convincing answers using outdated information.

A response may be grammatically correct and sound confident while containing an obsolete price, deprecated software version, outdated policy, or incorrect specification.

FreshGuard AI addresses this reliability problem by introducing an explainable verification layer between AI-generated answers and trusted knowledge sources.

**The goal is simple: Don't just generate answers. Verify that they are still correct.**

---

## 🏆 Project Information

**Project:** FreshGuard AI  
**Category:** Artificial Intelligence / AI Reliability  
**Type:** Hackathon MVP  
**Primary Language:** Python  
**Interface:** Streamlit  
**Architecture:** Single-file, database-free application  
**Deployment:** Local development

---

### Built for a more reliable AI ecosystem. 🛡️

**FreshGuard AI — Detect Staleness. Verify Evidence. Trust Better.**
