# Supabase Database Schema

## Tables Overview

### agent_logs
Tracks execution details for each agent run.
| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | uuid | NO | gen_random_uuid() | Primary key |
| agent_name | text | YES | null | Name of the agent |
| input_payload | jsonb | YES | null | Input data for the agent |
| output_payload | jsonb | YES | null | Output data from the agent |
| status | text | YES | null | Execution status |
| error_message | text | YES | null | Error details if any |
| created_at | timestamptz | YES | now() | Creation timestamp |

### ai_outputs
Stores AI agent outputs and analysis results.
| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | uuid | NO | gen_random_uuid() | Primary key |
| deal_id | uuid | YES | null | Reference to deals table |
| document_id | uuid | YES | null | Reference to documents table |
| chunk_id | uuid | YES | null | Reference to document chunks |
| agent_type | text | YES | null | Type of agent (financial, risk, etc.) |
| output_type | text | YES | null | Type of output |
| output_text | text | YES | null | Text output |
| output_json | jsonb | YES | null | Structured JSON output |
| created_by | uuid | YES | null | User who created the output |
| created_at | timestamptz | YES | now() | Creation timestamp |

### chunk_relationships
Maintains context and relationships between document chunks.
| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | uuid | NO | gen_random_uuid() | Primary key |
| parent_chunk_id | uuid | NO | null | Reference to parent chunk |
| child_chunk_id | uuid | NO | null | Reference to child chunk |
| relationship_type | text | NO | null | Type of relationship |
| strength | numeric | YES | 1.0 | Relationship strength |
| created_at | timestamptz | NO | now() | Creation timestamp |

### cim_analysis
Stores comprehensive CIM analysis results.
| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | uuid | NO | gen_random_uuid() | Primary key |
| deal_id | uuid | NO | null | Reference to deals table |
| document_id | uuid | YES | null | Reference to documents table |
| investment_grade | text | NO | null | Investment grade (A+, A, B+, B, C) |
| executive_summary | text | YES | null | Executive summary text |
| business_model | jsonb | YES | null | Business model analysis |
| financial_metrics | jsonb | YES | null | Financial metrics analysis |
| key_risks | jsonb | YES | null | Key risks analysis |
| investment_highlights | ARRAY | YES | null | Array of investment highlights |
| management_questions | ARRAY | YES | null | Array of management questions |
| competitive_position | jsonb | YES | null | Competitive analysis |
| recommendation | jsonb | YES | null | Investment recommendation |
| raw_ai_response | jsonb | YES | null | Raw AI response data |
| created_at | timestamptz | NO | now() | Creation timestamp |
| updated_at | timestamptz | NO | now() | Last update timestamp |

### comparisons
Stores deal comparisons and analysis.
| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | uuid | NO | gen_random_uuid() | Primary key |
| user_id | uuid | YES | null | Reference to users table |
| name | text | YES | null | Comparison name |
| deal_ids | ARRAY | YES | null | Array of deal IDs |
| comparison_json | jsonb | YES | null | Structured comparison data |
| created_at | timestamptz | YES | now() | Creation timestamp |

### deal_metrics
Stores individual deal metrics and KPIs.
| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | uuid | NO | gen_random_uuid() | Primary key |
| deal_id | uuid | YES | null | Reference to deals table |
| metric_name | text | YES | null | Name of the metric |
| metric_value | numeric | YES | null | Value of the metric |
| metric_unit | text | YES | null | Unit of measurement |
| source_chunk_id | uuid | YES | null | Source document chunk |
| pinned | boolean | YES | false | Whether metric is pinned |
| created_at | timestamptz | YES | now() | Creation timestamp |

### deals
Stores deal information and metadata.
| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | uuid | NO | gen_random_uuid() | Primary key |
| user_id | uuid | YES | null | Reference to users table |
| name | text | NO | null | Deal name |
| status | text | YES | 'active' | Deal status |
| industry | text | YES | null | Industry classification |
| company_name | text | YES | null | Company name |
| description | text | YES | null | Deal description |
| created_by | uuid | YES | null | User who created the deal |
| created_at | timestamptz | YES | now() | Creation timestamp |
| updated_at | timestamptz | YES | now() | Last update timestamp |

### document_chunks
Stores document chunks for RAG and processing.
| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | uuid | NO | gen_random_uuid() | Primary key |
| document_id | uuid | NO | null | Reference to documents table |
| deal_id | uuid | NO | null | Reference to deals table |
| chunk_text | text | NO | null | Chunk content |
| chunk_index | integer | NO | null | Chunk sequence number |
| chunk_size | integer | NO | null | Size in tokens/characters |
| start_page | integer | YES | null | Starting page number |
| end_page | integer | YES | null | Ending page number |
| section_type | text | YES | null | Type of section |
| section_title | text | YES | null | Section title |
| metadata | jsonb | YES | '{}' | Additional metadata |
| processed_by_ai | boolean | YES | false | AI processing status |
| ai_output | jsonb | YES | null | AI analysis results |
| confidence_score | numeric | YES | null | Processing confidence |
| created_at | timestamptz | NO | now() | Creation timestamp |
| updated_at | timestamptz | NO | now() | Last update timestamp |

### documents
Stores document metadata and processing status.
| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | uuid | NO | gen_random_uuid() | Primary key |
| deal_id | uuid | YES | null | Reference to deals table |
| file_name | text | YES | null | Original file name |
| file_type | text | YES | null | File type/extension |
| storage_path | text | YES | null | Storage location |
| uploaded_by | uuid | YES | null | User who uploaded |
| uploaded_at | timestamptz | YES | now() | Upload timestamp |
| classified_as | text | YES | null | Document classification |
| is_audio | boolean | YES | false | Whether document is audio |
| name | text | YES | null | Display name |
| file_path | text | YES | null | File system path |
| size | integer | YES | null | File size in bytes |
| processed | boolean | YES | false | Processing status |

### excel_to_chunk_links
Links Excel chunks to document chunks.
| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | uuid | NO | gen_random_uuid() | Primary key |
| xlsx_chunk_id | uuid | NO | null | Reference to xlsx_chunks |
| document_chunk_id | uuid | NO | null | Reference to document_chunks |
| relationship_type | text | NO | null | Type of relationship |
| confidence | numeric | YES | 1.0 | Link confidence score |
| created_at | timestamptz | NO | now() | Creation timestamp |

### transcripts
Stores document transcriptions.
| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | uuid | NO | gen_random_uuid() | Primary key |
| document_id | uuid | YES | null | Reference to documents table |
| content | text | YES | null | Transcript content |
| timestamps | jsonb | YES | null | Timestamp data |
| created_at | timestamptz | YES | now() | Creation timestamp |

### users
Stores user information.
| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | uuid | NO | gen_random_uuid() | Primary key |
| email | text | YES | null | User email |
| full_name | text | YES | null | User's full name |
| created_at | timestamptz | YES | now() | Creation timestamp |

### xlsx_chunks
Stores Excel file chunks and data.
| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | uuid | NO | gen_random_uuid() | Primary key |
| document_id | uuid | YES | null | Reference to documents table |
| sheet_name | text | YES | null | Excel sheet name |
| chunk_label | text | YES | null | Chunk identifier |
| data | jsonb | YES | null | Chunk data |
| created_at | timestamptz | YES | now() | Creation timestamp |
| verified_by_user | boolean | YES | false | User verification status |

### ai_models
Stores AI model configurations and capabilities.
| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | uuid | NO | gen_random_uuid() | Primary key |
| name | text | NO | null | Model name |
| provider | ai_provider | NO | null | Model provider (openai, anthropic, google, local) |
| model_id | text | NO | null | Provider's model identifier |
| use_case | model_use_case | NO | null | Primary use case |
| cost_per_input_token | numeric | NO | 0 | Cost per 1000 input tokens |
| cost_per_output_token | numeric | NO | 0 | Cost per 1000 output tokens |
| max_tokens | integer | YES | 4096 | Maximum tokens per request |
| context_window | integer | YES | 128000 | Maximum context window size |
| supports_vision | boolean | YES | false | Whether model supports vision |
| supports_function_calling | boolean | YES | false | Whether model supports function calling |
| is_active | boolean | YES | true | Whether model is active |
| is_default | boolean | YES | false | Whether model is default for use case |
| performance_score | numeric | YES | 0.00 | Model performance rating (0-10) |
| speed_score | numeric | YES | 0.00 | Model speed rating (0-10) |
| compatible_use_cases | text[] | YES | '{}' | Array of compatible use cases |
| description | text | YES | null | Model description |
| created_at | timestamptz | YES | now() | Creation timestamp |
| updated_at | timestamptz | YES | now() | Last update timestamp |

### model_usage_logs
Tracks detailed model usage and costs.
| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | uuid | NO | gen_random_uuid() | Primary key |
| deal_id | uuid | YES | null | Reference to deals table |
| document_id | uuid | YES | null | Reference to documents table |
| agent_log_id | uuid | YES | null | Reference to agent_logs table |
| model_id | uuid | NO | null | Reference to ai_models table |
| use_case | model_use_case | NO | null | Use case for this usage |
| input_tokens | integer | YES | 0 | Number of input tokens |
| output_tokens | integer | YES | 0 | Number of output tokens |
| total_tokens | integer | YES | 0 | Total tokens used |
| cost_usd | numeric | YES | 0 | Cost in USD |
| processing_time_ms | integer | YES | 0 | Processing time in milliseconds |
| success | boolean | YES | true | Whether request was successful |
| error_message | text | YES | null | Error message if any |
| user_id | uuid | YES | null | Reference to users table |
| created_at | timestamptz | YES | now() | Creation timestamp |

### model_configurations
Stores user and deal-specific model settings.
| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | uuid | NO | gen_random_uuid() | Primary key |
| user_id | uuid | YES | null | Reference to users table |
| deal_id | uuid | YES | null | Reference to deals table |
| use_case | model_use_case | NO | null | Use case for this configuration |
| model_id | uuid | NO | null | Reference to ai_models table |
| is_testing_mode | boolean | YES | false | Whether in testing mode |
| created_at | timestamptz | YES | now() | Creation timestamp |
| updated_at | timestamptz | YES | now() | Last update timestamp |

## Key Relationships

1. **Deals → Documents**
   - One deal can have multiple documents
   - `deals.id` → `documents.deal_id`

2. **Documents → Document Chunks**
   - One document can have multiple chunks
   - `documents.id` → `document_chunks.document_id`

3. **Document Chunks → Relationships**
   - Chunks can have multiple relationships
   - `document_chunks.id` → `chunk_relationships.parent_chunk_id`
   - `document_chunks.id` → `chunk_relationships.child_chunk_id`

4. **Excel Chunks → Document Chunks**
   - Excel chunks can be linked to document chunks
   - `xlsx_chunks.id` → `excel_to_chunk_links.xlsx_chunk_id`
   - `document_chunks.id` → `excel_to_chunk_links.document_chunk_id`

5. **Documents → Analysis**
   - One document can have multiple analyses
   - `documents.id` → `cim_analysis.document_id`

6. **Deals → Metrics**
   - One deal can have multiple metrics
   - `deals.id` → `deal_metrics.deal_id`

7. **Documents → Transcripts**
   - One document can have one transcript
   - `documents.id` → `transcripts.document_id`

8. **Users → Deals**
   - One user can have multiple deals
   - `users.id` → `deals.user_id`

9. **AI Models → Model Configurations**
   - One model can be used in multiple configurations
   - `ai_models.id` → `model_configurations.model_id`

10. **Model Configurations → Users/Deals**
    - Configurations can be user-specific or deal-specific
    - `model_configurations.user_id` → `users.id`
    - `model_configurations.deal_id` → `deals.id`

11. **Model Usage Logs → AI Models**
    - Usage logs reference specific models
    - `model_usage_logs.model_id` → `ai_models.id`

12. **Model Usage Logs → Agent Logs**
    - Usage logs can be linked to agent executions
    - `model_usage_logs.agent_log_id` → `agent_logs.id`

## Important Constraints

1. **Required Fields**:
   - `cim_analysis.investment_grade` (NOT NULL)
   - `deals.name` (NOT NULL)
   - `document_chunks.chunk_text` (NOT NULL)
   - All primary keys (id fields) are NOT NULL
   - `ai_models.name` (NOT NULL)
   - `ai_models.provider` (NOT NULL)
   - `ai_models.model_id` (NOT NULL)
   - `ai_models.use_case` (NOT NULL)
   - `model_configurations.use_case` (NOT NULL)
   - `model_configurations.model_id` (NOT NULL)
   - `model_usage_logs.model_id` (NOT NULL)
   - `model_usage_logs.use_case` (NOT NULL)

2. **Default Values**:
   - `deals.status` defaults to 'active'
   - `deal_metrics.pinned` defaults to false
   - `documents.is_audio` defaults to false
   - `xlsx_chunks.verified_by_user` defaults to false
   - `document_chunks.metadata` defaults to '{}'
   - `document_chunks.processed_by_ai` defaults to false
   - `ai_models.cost_per_input_token` defaults to 0
   - `ai_models.cost_per_output_token` defaults to 0
   - `ai_models.max_tokens` defaults to 4096
   - `ai_models.context_window` defaults to 128000
   - `ai_models.supports_vision` defaults to false
   - `ai_models.supports_function_calling` defaults to false
   - `ai_models.is_active` defaults to true
   - `ai_models.is_default` defaults to false
   - `ai_models.performance_score` defaults to 0.00
   - `ai_models.speed_score` defaults to 0.00
   - `model_usage_logs.input_tokens` defaults to 0
   - `model_usage_logs.output_tokens` defaults to 0
   - `model_usage_logs.total_tokens` defaults to 0
   - `model_usage_logs.cost_usd` defaults to 0
   - `model_usage_logs.processing_time_ms` defaults to 0
   - `model_usage_logs.success` defaults to true
   - `model_configurations.is_testing_mode` defaults to false

3. **Unique Constraints**:
   - `model_configurations` has a unique constraint on (user_id, deal_id, use_case)

4. **Timestamps**:
   - Most tables have `created_at` with default `now()`
   - Some tables have both `created_at` and `updated_at` 