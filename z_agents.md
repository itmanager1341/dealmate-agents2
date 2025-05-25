# DealMate Multi-Agent System — Architecture & Agent Spec

_Last updated: 2025-05-25_

## 🎯 Project Purpose

DealMate is a platform for AI-powered M&A due diligence. The system processes unstructured documents — particularly Confidential Information Memoranda (CIMs) — into structured insights, KPIs, and investment recommendations.

The backend in this repo (`dealmate-agents2`) orchestrates **multi-agent AI processing**, transforming uploaded CIM PDFs into normalized Supabase records.

---

## 🧠 Architecture Overview

### System Components
- `cim_orchestrator.py`: Core router; receives a PDF, extracts text, dispatches to agents
- `base_agent.py`: Abstract base class for all agents
- `agents/`: Contains task-specific AI agents

### Supabase Integration
Agents write output to these tables:
- `cim_analysis`: Block-level CIM output
- `deal_metrics`: Structured KPIs from financials
- `ai_outputs`: Risk, quotes, summary chunks
- `agent_logs`: Raw input/output + status for each run

Each agent is stateless and logs its operation to `agent_logs`.

---

## 🧩 Current Agents

| Agent Name         | File                    | Output Targets      | Purpose |
|--------------------|-------------------------|----------------------|---------|
| `FinancialAgent`   | `agents/financial_agent.py` | `deal_metrics`        | Extracts KPIs like revenue, EBITDA, margins, CAGR |
| `RiskAgent`        | `agents/risk_agent.py`      | `ai_outputs`          | Extracts red flags and risk categories |
| `MemoAgent`        | `agents/memo_agent.py`      | `cim_analysis`        | Generates structured investment memo content |
| `ConsistencyAgent` | `agents/consistency_agent.py` | `ai_outputs`          | Cross-checks narrative vs financials |

---

## 📄 Workflow: Orchestration Logic

1. PDF file is uploaded (via Lovable)
2. `cim_orchestrator.py`:
   - Loads full text using PyPDF2
   - Splits text for agent-specific sections (if applicable)
   - Runs each agent's `execute()` function
   - Collects output, logs results, writes to Supabase

All agent results are regenerable, traced by `agent_logs`.

---

## 🤖 Model Usage

| Agent            | Model         |
|------------------|---------------|
| All current agents | `gpt-4o` (default) |
| Fallback option  | `gpt-3.5-turbo-1106` |

Text length is chunked as needed to stay within token limits.

---

## 📥 Supabase Output Structure

### `deal_metrics`
```json
{
  "deal_id": "uuid",
  "metric_name": "EBITDA Margin",
  "metric_value": 56.2,
  "metric_unit": "%",
  "source_chunk_id": "uuid (optional)",
  "pinned": true
}

ai_outputs
{
  "deal_id": "uuid",
  "agent_type": "risk_agent",
  "output_type": "risk_summary",
  "output_text": "Key risks include regulatory constraints...",
  "output_json": {
    "risks": [
      {"risk": "Regulation", "severity": "Medium", "impact": "Could affect operations"}
    ]
  }
}

cim_analysis
{
  "deal_id": "uuid",
  "investment_grade": "B+",
  "executive_summary": "...",
  "business_model": { ... },
  "recommendation": { "action": "Pursue", "rationale": "..." }
}

Future Enhancements
Add chart_agent for table/graph extraction using OCR

Add quote_agent to extract investor testimonials and CEO statements

Supabase Edge Function run-agent.ts to asynchronously trigger agents per file

Prompt Patterns
Each agent uses structured GPT-4o prompts in this format:
messages = [
  {"role": "system", "content": "You are a financial analyst. Extract KPIs..."},
  {"role": "user", "content": extracted_text}
]
Prompts vary per agent and are modular in logic.

Developer Note
This agent framework is designed to scale:

Modular agents (plug-and-play logic)

Unified orchestrator

Database-backed retry + trace logs

Future support for agent chaining and validation cross-checks

