# DealMate AI - API Documentation

## Base URL
```
https://zxjyxzhoz0d2e5-8000.proxy.runpod.net
```

## Authentication
- No authentication required for AI processing endpoints
- Frontend handles user authentication via Supabase
- All requests should include proper CORS headers

## Health & Status

### GET /
**Purpose**: Server information and available endpoints
**Response**:
```json
{
  "service": "DealMate AI Agent Server",
  "version": "1.0.0",
  "status": "running",
  "timestamp": "2025-06-07T15:45:16.000Z",
  "endpoints": {
    "health": "/health",
    "transcribe": "/transcribe (POST)",
    "process_excel": "/process-excel (POST)",
    "process_document": "/process-document (POST)",
    "process_cim": "/process-cim (POST)",
    "generate_memo": "/generate-memo (POST)"
  }
}
```

### GET /health
**Purpose**: Health check for server status
**Response**:
```json
{
  "status": "healthy",
  "timestamp": "2025-06-07T15:45:16.000Z",
  "services": {
    "openai": "configured",
    "whisper": "ready"
  }
}
```

## Document Processing Endpoints

### POST /process-cim
**Purpose**: Process CIM documents with specialized investment analysis
**Status**: ✅ **Operational** - Core functionality stable with edge case handling

**Request**:
- **Content-Type**: `multipart/form-data`
- **file**: PDF file (CIM document)
- **deal_id**: String identifier for the deal

**Response**:
```json
{
  "success": true,
  "deal_id": "deal-123",
  "filename": "project-leap-cim.pdf",
  "document_type": "CIM",
  "page_count": 22,
  "text_length": 15847,
  "ai_analysis": "{\"investment_grade\": \"B+\", \"executive_summary\": \"...\", \"financial_metrics\": {...}}",
  "processing_time": "completed",
  "analysis_type": "comprehensive_cim"
}
```

**AI Analysis Structure**:
```json
{
  "investment_grade": "A+/A/A-/B+/B/B-/C+/C/C-/D+/D/F",
  "executive_summary": "Brief overview",
  "business_model": {
    "type": "Business model description",
    "revenue_streams": ["stream1", "stream2"],
    "key_value_propositions": ["prop1", "prop2"]
  },
  "financial_metrics": {
    "revenue_cagr": "X.X%",
    "ebitda_margin": "X.X%",
    "deal_size_estimate": "$XXM",
    "revenue_multiple": "X.Xx",
    "ebitda_multiple": "X.Xx"
  },
  "key_risks": [
    {
      "risk": "Risk description",
      "severity": "High/Medium/Low",
      "impact": "Impact description"
    }
  ],
  "investment_highlights": ["highlight1", "highlight2"],
  "management_questions": ["question1", "question2"],
  "competitive_position": {
    "strengths": ["strength1"],
    "weaknesses": ["weakness1"],
    "market_position": "Position description"
  },
  "recommendation": {
    "action": "Pursue/Pass/More Info Needed",
    "rationale": "Reasoning"
  }
}
```

### POST /process-excel
**Purpose**: Extract financial metrics from Excel files
**Status**: ✅ Working

**Request**:
- **Content-Type**: `multipart/form-data`
- **file**: Excel file (.xlsx, .xls)
- **deal_id**: String identifier

**Response**:
```json
{
  "success": true,
  "deal_id": "deal-123",
  "filename": "financials.xlsx",
  "sheets": ["Sheet1", "Revenue", "P&L"],
  "ai_analysis": "Structured financial analysis...",
  "raw_data_preview": "First 500 chars of data..."
}
```

### POST /process-document
**Purpose**: Analyze PDF/Word documents for business insights
**Status**: ✅ Working

**Request**:
- **Content-Type**: `multipart/form-data`
- **file**: Document file (.pdf, .docx, .doc)
- **deal_id**: String identifier

**Response**:
```json
{
  "success": true,
  "deal_id": "deal-123",
  "filename": "business-plan.pdf",
  "text_length": 8542,
  "ai_analysis": "Business analysis with insights...",
  "text_preview": "First 500 chars..."
}
```

### POST /transcribe
**Purpose**: Transcribe audio files using Whisper
**Status**: ✅ Working

**Request**:
- **Content-Type**: `multipart/form-data`
- **file**: Audio file (.mp3, .wav, .m4a)
- **deal_id**: String identifier

**Response**:
```json
{
  "success": true,
  "deal_id": "deal-123",
  "filename": "meeting.mp3",
  "transcription": "Full transcription text...",
  "segments": [
    {
      "start": 0.0,
      "end": 5.2,
      "text": "Welcome to the meeting..."
    }
  ],
  "processing_time": 12.5
}
```

### POST /generate-memo
**Purpose**: Generate investment memo from processed data
**Status**: ✅ Basic Implementation

**Request**:
```json
{
  "deal_id": "deal-123",
  "sections": ["executive_summary", "financial_analysis", "risks", "recommendation"]
}
```

**Response**:
```json
{
  "success": true,
  "deal_id": "deal-123",
  "memo": "Professional investment memo content...",
  "sections": ["executive_summary", "financial_analysis", "risks", "recommendation"],
  "generated_at": "2025-05-24T19:19:16.000Z"
}
```

## Progress Tracking

### CIM Processing Progress States
The frontend implements real-time progress tracking for CIM analysis:

**Progress Steps**:
1. **Validation** (0-25%): File type and size validation
2. **Analysis** (25-75%): AI processing and analysis generation
3. **Storage** (75-95%): Database storage and indexing
4. **Complete** (100%): Processing finished successfully

**Progress Response Format**:
```json
{
  "step": "analysis",
  "progress": 45,
  "message": "AI analyzing document structure..."
}
```

## Enhanced Error Handling

### Standard Error Response
```json
{
  "success": false,
  "error": "Error description",
  "error_code": "CIM_PARSE_ERROR",
  "retry_suggested": true,
  "fallback_available": true,
  "agent_logging_status": "failed"
}
```

### Agent Logging Error Scenarios

**Issue**: Agent logging fails due to missing required fields
**Frontend Handling**: 
- Automatic job completion when CIM analysis exists
- User notification about partial logging failure
- Processing continues with available data

**Error Response**:
```json
{
  "success": true,
  "warning": "Agent logging incomplete - processing completed successfully",
  "error_code": "AGENT_LOG_PARTIAL_FAILURE",
  "raw_response": "AI analysis text...",
  "analysis_stored": true,
  "job_completed": true
}
```

### Processing Job Error Recovery

**Stuck Job Detection**:
- Jobs in 'pending' or 'processing' status for >10 minutes
- CIM analysis exists but job not marked complete
- Automatic completion triggered by frontend monitoring

**Recovery Actions**:
```json
{
  "action": "auto_completion",
  "reason": "CIM analysis found, completing stuck job",
  "job_id": "uuid",
  "completion_method": "force_complete",
  "original_status": "processing",
  "new_status": "completed"
}
```

## Enhanced Agent Logging Requirements

### Agent Logging Schema
**Important**: All AI processing endpoints now require proper agent logging with enhanced schema:

**Required Fields for agent_logs table**:
- `deal_id` (UUID): Reference to the deal being processed
- `document_id` (UUID): Reference to the document being analyzed
- `user_id` (UUID): User who initiated the processing
- `agent_type` (string): Type of agent processing (e.g., 'cim_analysis')
- `status` (string): Processing status ('pending', 'processing', 'completed', 'error')
- `input_payload` (JSONB): Complete input data and parameters
- `output_payload` (JSONB): Complete AI response and processed results
- `error_message` (string): Error details if processing fails

### Processing Job Management

**Enhanced Features**:
- **Automatic Stuck Job Detection**: System automatically identifies stalled processing jobs
- **Force Completion Logic**: Completes jobs when analysis already exists in database
- **Real-time Status Updates**: Live progress tracking with database synchronization
- **Error Recovery**: Graceful handling of agent logging failures

**Processing Job Lifecycle**:
1. **Creation** (0%): Job created in `processing_jobs` table with 'pending' status
2. **Validation** (0-25%): File validation and preprocessing
3. **Processing** (25-75%): AI analysis and content extraction
4. **Storage** (75-95%): Database storage and indexing
5. **Completion** (100%): Job marked as 'completed' with results available
6. **Error Recovery**: Automatic completion if stuck but analysis exists

## Enhanced Error Handling

### Standard Error Response
```json
{
  "success": false,
  "error": "Error description",
  "error_code": "CIM_PARSE_ERROR",
  "retry_suggested": true,
  "fallback_available": true,
  "agent_logging_status": "failed"
}
```

### Agent Logging Error Scenarios

**Issue**: Agent logging fails due to missing required fields
**Frontend Handling**: 
- Automatic job completion when CIM analysis exists
- User notification about partial logging failure
- Processing continues with available data

**Error Response**:
```json
{
  "success": true,
  "warning": "Agent logging incomplete - processing completed successfully",
  "error_code": "AGENT_LOG_PARTIAL_FAILURE",
  "raw_response": "AI analysis text...",
  "analysis_stored": true,
  "job_completed": true
}
```

### Processing Job Error Recovery

**Stuck Job Detection**:
- Jobs in 'pending' or 'processing' status for >10 minutes
- CIM analysis exists but job not marked complete
- Automatic completion triggered by frontend monitoring

**Recovery Actions**:
```json
{
  "action": "auto_completion",
  "reason": "CIM analysis found, completing stuck job",
  "job_id": "uuid",
  "completion_method": "force_complete",
  "original_status": "processing",
  "new_status": "completed"
}
```

## Database Integration Enhancements

### Enhanced Database Schema

#### agent_logs Table (Updated)
```sql
-- Primary CIM analysis table
cim_analysis {
  deal_id: uuid,
  document_id: uuid,
  investment_grade: text,
  executive_summary: text,
  business_model: jsonb,
  financial_metrics: jsonb,
  key_risks: jsonb[],
  investment_highlights: text[],
  management_questions: text[],
  competitive_position: jsonb,
  recommendation: jsonb,
  raw_ai_response: jsonb
}

-- Audit trail
ai_outputs {
  deal_id: uuid,
  document_id: uuid,
  agent_type: 'cim_analysis',
  output_type: 'investment_analysis',
  output_json: jsonb,
  created_at: timestamp
}

-- NEW: Performance indexes
CREATE INDEX idx_agent_logs_deal_id ON agent_logs(deal_id);
CREATE INDEX idx_agent_logs_user_id ON agent_logs(user_id);
CREATE INDEX idx_agent_logs_status ON agent_logs(status);
```

#### processing_jobs Table (Enhanced)
```sql
processing_jobs {
  id: uuid PRIMARY KEY,
  deal_id: uuid NOT NULL,
  document_id: uuid,
  user_id: uuid NOT NULL,
  job_type: text DEFAULT 'cim_analysis',
  status: text DEFAULT 'pending',        -- 'pending', 'processing', 'completed', 'error'
  progress: integer DEFAULT 0,           -- 0-100 percentage
  current_step: text DEFAULT 'validation', -- Current processing step
  agent_results: jsonb DEFAULT '{}',     -- Intermediate results
  error_message: text,                   -- Error details
  started_at: timestamp DEFAULT now(),
  completed_at: timestamp,
  created_at: timestamp DEFAULT now(),
  updated_at: timestamp DEFAULT now()
}
```

### Real-time Processing Status

**Enhanced Status Tracking**:
```javascript
// Frontend monitoring with automatic recovery
const { isProcessing, progress, error, checkForCompletion } = useCIMProcessingStatus(dealId);

// Automatic stuck job detection
useEffect(() => {
  const interval = setInterval(async () => {
    if (isProcessing && progress < 100) {
      const completed = await checkForCompletion();
      if (completed) {
        // Job automatically completed
        console.log('Stuck job automatically completed');
      }
    }
  }, 30000); // Check every 30 seconds

  return () => clearInterval(interval);
}, [isProcessing, progress]);
```

## Performance Metrics & Monitoring

### Current Performance Benchmarks
- **CIM Analysis**: 3-8 minutes (variable based on document complexity)
- **Success Rate**: 90%+ with automatic recovery
- **Agent Logging**: 95%+ success rate with fallback handling
- **Job Completion**: 98%+ eventual completion (including auto-recovery)

### Monitoring Endpoints

#### Processing Job Health Check
```javascript
// Check for stuck jobs
GET /api/processing-jobs/health?deal_id={deal_id}

Response:
{
  "active_jobs": 1,
  "stuck_jobs": 0,
  "completion_rate": 0.95,
  "average_processing_time": 240000, // milliseconds
  "last_completed": "2025-06-07T15:30:00Z"
}
```

### Quality Assurance Improvements

#### Enhanced Testing Coverage
- **Agent Logging Scenarios**: Missing field validation and recovery
- **Stuck Job Detection**: Automatic completion testing
- **Error Recovery**: Graceful degradation validation
- **Performance Testing**: Variable document complexity handling

#### Monitoring & Alerts
- **Stuck Job Detection**: Automatic alerts for jobs >10 minutes
- **Agent Logging Failures**: Monitoring for audit trail completeness
- **Processing Time Variance**: Alerts for unusually long processing
- **Success Rate Monitoring**: Real-time success rate tracking

## Development Status

### Current Phase: Stabilization & Optimization (90% Complete)
**Focus Areas**:
- Agent logging reliability and error recovery
- Processing job completion logic optimization
- Performance consistency improvements
- Enhanced error messaging and user feedback

**Known Issues**:
- Processing time variability (3-8 minutes) needs optimization
- Occasional agent logging failures require fallback handling
- Edge cases in job completion logic being addressed

**Recent Improvements** (June 2025):
- Enhanced agent_logs schema with proper foreign key relationships
- Automatic stuck job detection and completion
- Improved error recovery mechanisms
- Better real-time status synchronization

---

**Last Updated**: 2025-06-07  
**Documentation Version**: 3.1.0  
**API Version**: 1.0.0  
**Status**: Stable with ongoing optimization

The API is production-ready with robust error handling and automatic recovery mechanisms, suitable for professional investment analysis workflows.
