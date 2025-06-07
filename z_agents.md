# DealMate Multi-Agent System — Architecture & Agent Spec

_Last updated: 2025-06-07_

## 🎯 Project Purpose

DealMate is a platform for AI-powered M&A due diligence. The system processes unstructured documents — particularly Confidential Information Memoranda (CIMs) — into structured insights, KPIs, and investment recommendations.

The backend in this repo (`dealmate-agents2`) orchestrates **multi-agent AI processing** with enhanced model management, transforming uploaded CIM PDFs into normalized Supabase records with comprehensive audit trails.

---

## 🧠 Architecture Overview

### System Components
- `cim_orchestrator.py`: Core router with enhanced model configuration and agent orchestration
- `base_agent.py`: Enhanced base class with model management, usage tracking, and tool support
- `agents/`: Task-specific AI agents with standardized interfaces and validation
- `tools/`: Shared tool registry for agent operations

### Enhanced Model Management
- **Model Configuration**: User/deal-specific model settings with performance tracking
- **Usage Monitoring**: Detailed token usage, processing time, and cost tracking
- **Performance Analytics**: Success rates and processing time metrics
- **Cost Optimization**: Automatic model selection based on use case and performance

### Supabase Integration
Agents write output to these tables:
- `cim_analysis`: Structured investment analysis with grading
- `deal_metrics`: Extracted KPIs and financial metrics
- `ai_outputs`: Risk analysis, quotes, and summary chunks
- `agent_logs`: Enhanced audit trail with model usage
- `model_usage_logs`: Detailed model performance tracking
- `model_configurations`: User/deal-specific model settings

Each agent is stateless and logs its operation with comprehensive metadata.

---

## 🧩 Current Agents

| Agent Name         | File                    | Output Targets      | Purpose |
|--------------------|-------------------------|----------------------|---------|
| `FinancialAgent`   | `agents/financial_agent.py` | `deal_metrics`        | Extracts KPIs like revenue, EBITDA, margins, CAGR |
| `RiskAgent`        | `agents/risk_agent.py`      | `ai_outputs`          | Extracts red flags and risk categories |
| `MemoAgent`        | `agents/memo_agent.py`      | `cim_analysis`        | Generates structured investment memo content |
| `ConsistencyAgent` | `agents/consistency_agent.py` | `ai_outputs`          | Cross-checks narrative vs financials |
| `QuoteAgent`       | `agents/quote_agent.py`      | `ai_outputs`          | Extracts and analyzes key statements |
| `ChartAgent`       | `agents/chart_agent.py`      | `ai_outputs`          | Extracts and analyzes charts/tables |

---

## 📄 Enhanced Workflow: Orchestration Logic

1. PDF file is uploaded (via Lovable)
2. Model configuration is loaded based on user/deal settings
3. `cim_orchestrator.py`:
   - Loads full text using PyPDF2
   - Splits text for agent-specific sections
   - Initializes agents with model configuration
   - Runs each agent's `execute()` function
   - Tracks model usage and performance
   - Collects output, logs results, writes to Supabase

All agent results are regenerable, traced by `agent_logs` and `model_usage_logs`.

---

## 🤖 Enhanced Model Management

### Model Configuration
```typescript
interface ModelConfig {
  model_id: string;
  use_case: string;
  is_testing_mode: boolean;
  user_id?: string;
  deal_id?: string;
}
```

### Model Usage Tracking
```typescript
interface ModelUsage {
  model_id: string;
  use_case: string;
  input_tokens: number;
  output_tokens: number;
  processing_time_ms: number;
  cost_usd: number;
  success: boolean;
  error_message?: string;
}
```

### Model Selection Logic
1. Check user-specific configuration
2. Check deal-specific configuration
3. Use default model for use case
4. Fall back to GPT-3.5-turbo if needed

---

## 📥 Enhanced Supabase Output Structure

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
```

### `ai_outputs`
```json
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
```

### `cim_analysis`
```json
{
  "deal_id": "uuid",
  "investment_grade": "B+",
  "executive_summary": "...",
  "business_model": { ... },
  "recommendation": { "action": "Pursue", "rationale": "..." }
}
```

### `model_usage_logs`
```json
{
  "deal_id": "uuid",
  "model_id": "uuid",
  "use_case": "cim_analysis",
  "input_tokens": 1500,
  "output_tokens": 500,
  "processing_time_ms": 2500,
  "cost_usd": 0.02,
  "success": true
}
```

---

## 🔧 Agent Implementation Details

### Base Agent Features
- Model configuration management
- Usage tracking and logging
- Tool registry integration
- Error handling and recovery
- Output validation
- Chunk processing

### Agent Validation
Each agent implements:
- Input validation
- Output type checking
- Error recovery
- Usage tracking
- Performance monitoring

### Tool Integration
Agents can use shared tools from the registry:
- Text processing
- Data extraction
- Validation
- Error handling

---

## 🚀 Future Enhancements

### Planned Agents
- `TableAgent`: Enhanced table extraction and analysis
- `ImageAgent`: Image and diagram analysis
- `ValidationAgent`: Cross-agent validation

### Model Improvements
- Custom model fine-tuning
- Performance optimization
- Cost reduction strategies
- Enhanced error recovery

### Tool Enhancements
- More specialized tools
- Better error handling
- Performance optimization
- Enhanced validation

---

## 📊 Performance Metrics

### Current Benchmarks
- Processing Time: 3-8 minutes per CIM
- Success Rate: 90%+ with automatic recovery
- Model Usage: Tracked per agent and operation
- Cost Efficiency: Optimized model selection

### Monitoring
- Real-time performance tracking
- Cost monitoring
- Success rate analysis
- Error rate tracking

---

## 🔐 Security & Compliance

### Data Protection
- Encrypted model configurations
- Secure usage logging
- Access control
- Audit trails

### Compliance
- Usage tracking
- Cost allocation
- Performance monitoring
- Error logging

---

## 🛠️ Development Guidelines

### Adding New Agents
1. Extend `BaseAgent`
2. Implement required methods
3. Add validation
4. Update documentation
5. Add tests

### Model Configuration
1. Define use case
2. Set performance metrics
3. Configure fallbacks
4. Add monitoring

### Tool Development
1. Define interface
2. Add validation
3. Implement error handling
4. Add tests

---

_Last Updated: 2025-06-07_  
_Version: 3.1.0_  
_Status: Development - Stabilization Phase_

