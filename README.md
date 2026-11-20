# FreshGuard AI — Stale-Answer Detector for AI Applications

<p align="center">
  <strong>Detect outdated, potentially incorrect, and conflicting AI answers before they reach users.</strong>
</p>

<p align="center">
  An AI reliability and knowledge freshness monitoring system built to help AI applications identify answers that may no longer reflect the latest available information.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Project-Hackathon%20MVP-blueviolet" alt="Hackathon MVP">
  <img src="https://img.shields.io/badge/Python-3.12-blue" alt="Python">
  <img src="https://img.shields.io/badge/Status-Active-success" alt="Status">
  <img src="https://img.shields.io/badge/License-MIT-green" alt="License">
</p>

---

## Overview

AI applications can generate answers that sound confident but rely on outdated documentation, old pricing information, deprecated API versions, or previously valid company policies.

This creates a serious reliability problem: an answer can be factually correct based on historical information while being incorrect today.

**FreshGuard AI** is designed to address this problem.

It analyzes AI-generated answers against available knowledge sources and identifies potential freshness risks, outdated claims, unsupported information, and possible contradictions.

Instead of treating every generated answer as equally reliable, FreshGuard AI provides a structured assessment that helps developers understand whether an answer should be trusted, reviewed, or investigated.

### The Problem

Consider an AI customer-support assistant that responds:

> "Our Premium subscription costs $99 per month."

However, the company's latest pricing documentation states that the Premium subscription now costs $149 per month.

A traditional AI application may still return the outdated price because its underlying knowledge has not been updated.

FreshGuard AI aims to identify this discrepancy before the answer is delivered to the end user.

### The Solution

FreshGuard AI introduces a knowledge-aware answer validation workflow:

1. Collect relevant knowledge sources.
2. Extract and organize available information.
3. Analyze an AI-generated answer.
4. Retrieve supporting knowledge.
5. Evaluate temporal and factual consistency.
6. Calculate a freshness score.
7. Highlight potential risks and supporting evidence.

---

## Key Features

### 1. AI Answer Freshness Analysis

Analyze generated answers and identify potentially outdated information.

- Sentence-level claim analysis.
- Temporal risk identification.
- Potentially outdated claims.
- Unsupported information detection.
- Evidence-based answer assessment.
- Structured analysis results.

### 2. Knowledge Source Management

Provide reference knowledge that can be used to evaluate generated answers.

Supported source types depend on the ingestion implementation:

- PDF documents
- DOCX documents
- TXT files
- Web URLs

### 3. Knowledge Retrieval

Retrieve relevant information from available knowledge sources to compare against the generated answer.

The system is designed around:

- Text normalization.
- Content processing.
- Document chunking.
- Similarity-based retrieval.
- Supporting evidence extraction.

### 4. Contradiction Detection

Identify potential differences between answer claims and retrieved knowledge.

Examples include:

- Outdated subscription pricing.
- Deprecated API versions.
- Changed company policies.
- Different numeric values.
- Conflicting reference information.

### 5. Freshness Scoring

FreshGuard AI uses a weighted scoring approach to estimate answer freshness.

The scoring model considers:

- Temporal risk.
- Contradiction severity.
- Evidence age risk.

The conceptual formula is:

\[
FreshnessScore = 100 - (0.35T + 0.40C + 0.25A)
\]

Where:

- \(T\) = Temporal risk
- \(C\) = Contradiction severity
- \(A\) = Evidence age risk

The result is a score between 0 and 100.

**Important:** This is a heuristic assessment, not a mathematically guaranteed probability that an answer is correct.

### 6. Knowledge Update Simulation

Simulate changes in reference knowledge and inspect whether previously analyzed answers may be affected.

Example:

- Previous Premium price: $99/month.
- Updated Premium price: $149/month.
- Previously analyzed answers can be reviewed for potentially outdated information.

### 7. Detection History

Keep track of analyzed answers during the application session.

Review previous results and investigate answers that may require attention.

### 8. Analytics Dashboard

Present an overview of answer analysis and detection activity through visual summaries and charts, where supported by the application.

---

## Application Modules

The project is organized into separate Python modules.

```text
freshguard/
│
├── main.py
│   └── Main application entry point
│
├── engine.py
│   └── Freshness analysis and detection logic
│
├── storage.py
│   └── Data storage and management
│
├── static/
│   └── Static frontend assets
│
├── .venv/
│   └── Python virtual environment
│
├── .gitignore
│
└── README.md
```

### Module Responsibilities

| Module | Responsibility |
|---|---|
| `main.py` | Application interface and workflow |
| `engine.py` | Claim analysis, retrieval, scoring, and detection |
| `storage.py` | Knowledge and application data management |
| `static/` | Frontend styling and static resources |

---

## Technology Stack

| Technology | Purpose |
|---|---|
| Python | Core application development |
| Streamlit / application UI | User interface, if used by the current implementation |
| Scikit-learn | Text similarity and retrieval, if enabled |
| Pandas | Data processing |
| PyMuPDF | PDF document processing |
| python-docx | DOCX document processing |
| BeautifulSoup | Web content extraction |
| HTTPX | HTTP requests |
| Plotly | Interactive analytics visualizations, if enabled |

The actual runtime dependencies are defined by the project's installed packages and implementation.

---

## Installation and Setup

### Prerequisites

- Windows 10/11, Linux, or macOS.
- Python 3.10 or newer.
- Git.
- pip.

### 1. Clone the Repository

```bash
git clone https://github.com/YOUR_USERNAME/freshguard.git
```

```bash
cd freshguard
```

Replace `YOUR_USERNAME` with your GitHub username.

### 2. Create a Virtual Environment

**Windows PowerShell:**

```powershell
py -3.12 -m venv .venv
```

### 3. Activate the Environment

```powershell
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks script execution, run:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

Then activate the environment again.

### 4. Install Dependencies

Install the dependencies required by the project.

If a `requirements.txt` file is available:

```powershell
pip install -r requirements.txt
```

Otherwise, install the packages required by the current implementation:

```powershell
pip install streamlit pandas scikit-learn pymupdf python-docx beautifulsoup4 httpx plotly
```

### 5. Run the Application

If the project uses Streamlit:

```powershell
streamlit run main.py
```

Otherwise, use the entry-point command specified by the application's implementation.

---

## How to Use FreshGuard AI

### Step 1 — Launch the Application

Start FreshGuard AI using the appropriate application command.

### Step 2 — Add Knowledge Sources

Upload supported reference documents or provide a URL if URL ingestion is enabled.

These sources act as the reference knowledge for answer evaluation.

### Step 3 — Submit an AI-Generated Answer

Provide the answer that you want to inspect.

Example:

```text
Our Premium subscription costs $99 per month
and includes unlimited API requests.
```

### Step 4 — Analyze the Answer

Run the freshness analysis.

The system evaluates available evidence and identifies potential inconsistencies.

### Step 5 — Review the Results

Inspect:

- Freshness score.
- Detection status.
- Potentially outdated claims.
- Contradiction indicators.
- Supporting knowledge.
- Recommended review actions.

### Step 6 — Simulate a Knowledge Update

Update or simulate a change in reference information and investigate whether previously analyzed answers may now be outdated.

---

## Example Detection Scenarios

The following scenarios illustrate the types of problems FreshGuard AI is designed to investigate. They are illustrative examples, not benchmark results.

| Scenario | Answer | Reference Knowledge | Expected Investigation |
|---|---|---|---|
| Outdated Pricing | Premium costs $99 | Premium costs $149 | Potentially stale |
| Current Pricing | Premium costs $149 | Premium costs $149 | Supported by evidence |
| Deprecated API | API v2 is current | API v3 is current | Version inconsistency |
| Unsupported Claim | Unlimited requests included | 5,000 requests included | Unsupported or contradictory claim |
| Knowledge Conflict | Premium costs $149 | Another source says $199 | Conflicting evidence |

---

## Freshness Status Interpretation

The following score bands describe the intended interpretation of the freshness score. Additional detection statuses may be produced by the engine.

| Score | Status | Interpretation |
|---|---|---|
| 80–100 | FRESH | Stronger freshness indicators |
| 60–79 | REVIEW | Manual review recommended |
| 30–59 | POTENTIALLY STALE | Significant freshness concerns |
| 0–29 | HIGH STALE RISK | High priority for investigation |

Other possible detection outcomes include:

- **UNVERIFIED:** Available evidence is insufficient to verify a claim.
- **STALE:** A claim appears inconsistent with newer knowledge.
- **CONFLICT:** Available reference sources disagree.

A high freshness score does not guarantee factual correctness. Likewise, a low score does not automatically prove that an answer is false.

---

## Architecture

```text
          AI-Generated Answer
                   |
                   v
          Answer Submission
                   |
                   v
          Claim Extraction
                   |
                   v
          Temporal Analysis
                   |
                   v
          Knowledge Retrieval
                   |
                   v
        Evidence Comparison
                   |
                   v
       Contradiction Assessment
                   |
                   v
          Freshness Scoring
                   |
                   v
          Detection Results
                   |
          +--------+--------+
          |                 |
          v                 v
     Risk Analysis     Evidence Review
          |                 |
          +--------+--------+
                   |
                   v
          Developer Review
```

---

## Design Principles

FreshGuard AI is developed around several core principles:

**1. Knowledge-Aware Validation**

Answers should be evaluated against available reference knowledge rather than relying solely on their generated wording.

**2. Explainable Results**

The system should help developers understand why an answer was flagged, rather than simply returning a score.

**3. Lightweight Architecture**

The MVP focuses on a straightforward Python-based implementation without requiring a complex enterprise infrastructure.

**4. Practical Demonstration**

The project includes demonstration scenarios that illustrate common freshness and consistency problems.

**5. Human Review**

Automated detection is intended to support human decision-making, not replace it.

---

## Current MVP Scope

FreshGuard AI is an evolving hackathon MVP.

Current implementation capabilities depend on the code available in the repository.

The project is designed to focus on:

- Knowledge ingestion.
- Answer analysis.
- Retrieval-based evidence comparison.
- Heuristic freshness assessment.
- Potential contradiction detection.
- Knowledge update simulation.
- Detection history and analytics.

### Current Limitations

- Detection relies on heuristics and available reference information.
- Similarity-based retrieval does not guarantee semantic understanding.
- Numeric and version comparisons may require additional validation.
- Conflicting sources may require human investigation.
- A freshness score should not be interpreted as a calibrated confidence probability.
- General-purpose automatic knowledge monitoring is outside the scope of the basic MVP.
- External LLM integration should not be considered active unless explicitly implemented and configured.

---

## Future Roadmap

Potential improvements include:

- [ ] Advanced semantic claim extraction.
- [ ] More robust temporal reasoning.
- [ ] Improved contradiction detection.
- [ ] Source reliability and authority scoring.
- [ ] Automatic knowledge change monitoring.
- [ ] LLM-powered claim verification.
- [ ] REST API integration.
- [ ] Integration with LangChain and other AI application frameworks.
- [ ] Integration with RAG pipelines.
- [ ] Persistent knowledge storage.
- [ ] Automated evaluation and benchmark datasets.
- [ ] Production-ready deployment and monitoring.

---

## Security and Data Handling

The MVP should be treated as a development and demonstration environment.

Before production deployment, consider implementing:

- Secure document handling.
- URL ingestion restrictions.
- Input validation.
- Authentication and authorization.
- Sensitive information protection.
- Secure API key management.
- Persistent storage security.
- Logging and monitoring.

Do not upload confidential documents or production secrets into an environment that has not been reviewed for security.

---

## Contributing

Contributions, suggestions, and technical feedback are welcome.

To contribute:

1. Fork the repository.
2. Create a feature branch.
3. Implement your changes.
4. Test the application.
5. Submit a pull request.

```bash
git checkout -b feature/your-feature
git add .
git commit -m "Add: your feature"
git push origin feature/your-feature
```

---

## License

This project is intended to be released under the MIT License.

Add a `LICENSE` file to the repository before claiming that the project has been formally distributed under that license.

---

## Project Information

**Project:** FreshGuard AI  
**Category:** AI Reliability / AI Infrastructure / Developer Tools  
**Type:** Hackathon MVP  
**Primary Language:** Python  
**Focus:** Detecting stale, unsupported, and potentially conflicting AI-generated answers.

---

<p align="center">
  <strong>FreshGuard AI</strong>
  <br>
  Making AI answers more reliable, one claim at a time.
</p>
