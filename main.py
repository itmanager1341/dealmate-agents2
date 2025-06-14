"""
DealMate AI Agent Server - Main Application

This module provides the main Flask application for the DealMate AI Agent Server,
handling various endpoints for document processing, transcription, and analysis.
"""

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import openai
from openai import OpenAI
import os
import tempfile
import pandas as pd
import PyPDF2
import docx
from datetime import datetime
import json
import traceback
import logging
from orchestrator.cim_orchestrator import CIMOrchestrator
from orchestrator.supabase import supabase
from orchestrator.tools import TOOL_REGISTRY
from typing import Optional
from fastapi import HTTPException

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

@app.route('/', methods=['GET'])
def root():
    """Root endpoint with server information"""
    return jsonify({
        "service": "DealMate AI Agent Server",
        "version": "1.0.0",
        "status": "running",
        "timestamp": datetime.now().isoformat(),
        "endpoints": {
            "health": "/health",
            "transcribe": "/transcribe (POST)",
            "process_excel": "/process-excel (POST)",
            "process_document": "/process-document (POST)",
            "process_cim": "/process-cim (POST)",
            "generate_memo": "/generate-memo (POST)"
        },
        "description": "AI-powered due diligence platform for M&A professionals"
    })

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    openai_status = "configured" if os.getenv('OPENAI_API_KEY') else "missing_key"
    whisper_status = "ready" if 'whisper_transcribe' in TOOL_REGISTRY else "not_loaded"
    
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "openai": openai_status,
            "whisper": whisper_status
        }
    })

@app.route('/transcribe', methods=['POST'])
def transcribe_audio():
    """Transcribe audio files using Whisper"""
    try:
        if 'file' not in request.files:
            return jsonify({"error": "No file provided"}), 400
        
        file = request.files['file']
        deal_id = request.form.get('deal_id', 'unknown')
        
        if file.filename == '':
            return jsonify({"error": "No file selected"}), 400
        
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as tmp_file:
            file.save(tmp_file.name)
            
            try:
                # Use the WhisperTranscribeTool from the toolbox
                result = TOOL_REGISTRY['whisper_transcribe'].run(file_path=tmp_file.name)
                
                return jsonify({
                    "success": True,
                    "deal_id": deal_id,
                    "filename": file.filename,
                    "transcription": result["text"],
                    "segments": result["segments"],
                    "duration": result["duration"],
                    "cost_estimate": result["cost_estimate"]
                })
                
            finally:
                # Clean up temp file
                os.unlink(tmp_file.name)
                
    except Exception as e:
        logger.error(f"Transcription error: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/process-excel', methods=['POST'])
def process_excel():
    """Process Excel files for financial metrics"""
    try:
        if 'file' not in request.files:
            return jsonify({"error": "No file provided"}), 400
        
        file = request.files['file']
        deal_id = request.form.get('deal_id', 'unknown')
        
        # Save and read Excel file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
            file.save(tmp_file.name)
            
            # Read Excel file
            excel_data = pd.read_excel(tmp_file.name, sheet_name=None)  # Read all sheets
            
            # Extract basic financial metrics using AI
            sheets_content = []
            for sheet_name, df in excel_data.items():
                sheets_content.append(f"Sheet: {sheet_name}\n{df.head(10).to_string()}")
            
            excel_summary = "\n\n".join(sheets_content)
            
            # Use OpenAI to extract metrics
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a financial analyst. Extract key financial metrics from this Excel data. Return structured JSON with revenue, EBITDA, growth rates, and other key metrics."},
                    {"role": "user", "content": f"Extract financial metrics from this Excel data:\n\n{excel_summary[:4000]}"}
                ],
                temperature=0.1
            )
            
            # Clean up temp file
            os.unlink(tmp_file.name)
            
            return jsonify({
                "success": True,
                "deal_id": deal_id,
                "filename": file.filename,
                "sheets": list(excel_data.keys()),
                "ai_analysis": response.choices[0].message.content,
                "raw_data_preview": sheets_content[0][:500] if sheets_content else ""
            })
            
    except Exception as e:
        print(f"Excel processing error: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/process-document', methods=['POST'])
def process_document():
    """Process PDF/Word documents for business analysis"""
    try:
        if 'file' not in request.files:
            return jsonify({"error": "No file provided"}), 400
        
        file = request.files['file']
        deal_id = request.form.get('deal_id', 'unknown')
        
        # Extract text based on file type
        text_content = ""
        
        if file.filename.lower().endswith('.pdf'):
            # Process PDF
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                file.save(tmp_file.name)
                
                with open(tmp_file.name, 'rb') as pdf_file:
                    pdf_reader = PyPDF2.PdfReader(pdf_file)
                    for page in pdf_reader.pages:
                        text_content += page.extract_text()
                
                os.unlink(tmp_file.name)
        
        elif file.filename.lower().endswith(('.docx', '.doc')):
            # Process Word document
            with tempfile.NamedTemporaryFile(delete=False, suffix='.docx') as tmp_file:
                file.save(tmp_file.name)
                
                doc = docx.Document(tmp_file.name)
                for paragraph in doc.paragraphs:
                    text_content += paragraph.text + "\n"
                
                os.unlink(tmp_file.name)
        
        # Use OpenAI to analyze document
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an M&A analyst. Analyze this business document and extract key insights including company overview, market position, financial highlights, risks, and opportunities. Return structured analysis."},
                {"role": "user", "content": f"Analyze this business document:\n\n{text_content[:4000]}"}
            ],
            temperature=0.1
        )
        
        return jsonify({
            "success": True,
            "deal_id": deal_id,
            "filename": file.filename,
            "text_length": len(text_content),
            "ai_analysis": response.choices[0].message.content,
            "text_preview": text_content[:500]
        })
        
    except Exception as e:
        print(f"Document processing error: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/process-cim', methods=['POST'])
def process_cim():
    """
    Process a CIM document through all agents and store results in Supabase.
    """
    try:
        # Get file from request
        if 'file' not in request.files:
            logger.error("No file provided in request")
            return jsonify({"error": "No file provided"}), 400
        file = request.files['file']
        if not file:
            logger.error("Empty file provided")
            return jsonify({"error": "Empty file"}), 400

        # Get deal_id from request form data
        deal_id = request.form.get('deal_id')
        if not deal_id:
            logger.error("No deal_id provided in form data")
            return jsonify({"error": "No deal_id provided"}), 400

        # --- User ID Extraction ---
        user_id = None  # Initialize to None

        # 1. Attempt to get user_id from Authorization header (JWT)
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            try:
                # Ensure your global 'supabase' client is configured for auth
                user_response = supabase.auth.get_user(token)
                if user_response.user:
                    user_id = user_response.user.id
                    logger.info(f"Authenticated user_id from header: {user_id}")
                else:
                    logger.warning("Invalid token or user not found via header.")
            except Exception as auth_e:
                logger.error(f"Header auth error: {auth_e}. Token might be invalid or expired.")
        
        # 2. If not found in header, attempt to get user_id from FormData (fallback)
        if not user_id:
            form_user_id = request.form.get('user_id')
            if form_user_id:
                user_id = form_user_id
                logger.info(f"Using user_id from FormData: {user_id}")
            # Optional: Add further validation for form_user_id if necessary

        if not user_id:
            logger.warning("No user_id obtained from header or FormData. Proceeding with user_id=None.")
            # This means the system will try to find a model config for user_id=None.
            # Ensure your Supabase function get_effective_model_config handles this case,
            # potentially falling back to a global default model if no specific config for user_id=None exists.

        logger.info(f"Processing CIM for deal_id: {deal_id}, user_id: {user_id}")

        # Save file temporarily
        tmp_file = tempfile.NamedTemporaryFile(delete=False)
        file.save(tmp_file.name)
        tmp_file.close()

        try:
            # Initialize orchestrator with extracted user_id and deal_id
            logger.info(f"Initializing CIM orchestrator with user_id={user_id}, deal_id={deal_id}")
            orchestrator = CIMOrchestrator(user_id=user_id, deal_id=deal_id)
            
            # Extract text from PDF
            logger.info("Extracting text from PDF")
            document_text = orchestrator.load_pdf_text(tmp_file.name)
            if not document_text.strip():
                logger.error("No text could be extracted from the PDF")
                raise ValueError("No text could be extracted from the PDF")

            # Run all agents - user_id and deal_id are now handled by agent initialization
            logger.info("Running all agents")
            agent_results = orchestrator.run_all_agents(document_text) # Renamed for clarity
            
            # Process results
            # Check if any agent failed
            processing_errors = []
            overall_status_is_error = False
            for agent_name, res in agent_results.items():
                if res.get("status") == "error":
                    overall_status_is_error = True
                    error_detail = f"Agent '{agent_name}' failed: {res.get('error', 'Unknown error')}"
                    processing_errors.append(error_detail)
                    logger.error(error_detail)
            
            if overall_status_is_error:
                logger.error(f"Processing failed due to agent errors: {processing_errors}")
                # Store errors in agent_logs before returning
                for err_msg in processing_errors:
                    try:
                        supabase.table('agent_logs').insert({
                            "deal_id": deal_id, # deal_id is available in this scope
                            "user_id": user_id, # user_id is available in this scope
                            "agent_type": "orchestrator_summary", # Or derive from err_msg if possible
                            "log_type": "error",
                            "message": err_msg
                        }).execute()
                    except Exception as db_err:
                        logger.error(f"Failed to log orchestrator error to DB: {db_err}")
                return jsonify({"error": "Processing failed", "details": processing_errors}), 500

            # Extract results from each agent, now directly from agent_results
            financial_result = agent_results.get("financial", {"status": "not_run", "output": [], "error": "Financial agent did not run or return result"})
            risk_result = agent_results.get("risk", {"status": "not_run", "output": {}, "error": "Risk agent did not run or return result"})
            consistency_result = agent_results.get("consistency", {"status": "not_run", "output": {}, "error": "Consistency agent did not run or return result"})
            memo_result = agent_results.get("memo", {"status": "not_run", "output": {}, "error": "Memo agent did not run or return result"})

            inserted_data_counts = {"deal_metrics": 0, "ai_outputs_risk": 0, "ai_outputs_consistency": 0, "cim_analysis": 0}

            # Store results in Supabase
            if financial_result.get("status") == "success" and financial_result.get("output"):
                logger.info("Storing financial metrics")
                # Ensure output is a list of dicts for batch insert
                metrics_to_insert = financial_result["output"]
                if isinstance(metrics_to_insert, list) and all(isinstance(m, dict) for m in metrics_to_insert):
                    for metric in metrics_to_insert: # Add deal_id to each metric
                        metric['deal_id'] = deal_id
                    db_response = supabase.table('deal_metrics').insert(metrics_to_insert).execute()
                    inserted_data_counts["deal_metrics"] = len(db_response.data) if db_response.data else 0
                else:
                    logger.error(f"Financial agent output is not a list of dicts: {type(metrics_to_insert)}")
            
            # For risk and consistency, they are stored in ai_outputs
            # Risk Agent Output
            if risk_result.get("status") == "success" and risk_result.get("output"):
                logger.info("Storing risk analysis")
                risk_output_to_insert = risk_result["output"]
                if isinstance(risk_output_to_insert, dict):
                    risk_output_to_insert['deal_id'] = deal_id # Add deal_id
                    risk_output_to_insert['agent_type'] = 'risk' # Ensure agent_type is set
                    db_response = supabase.table('ai_outputs').insert(risk_output_to_insert).execute()
                    inserted_data_counts["ai_outputs_risk"] = len(db_response.data) if db_response.data else 0
                else:
                    logger.error(f"Risk agent output is not a dict: {type(risk_output_to_insert)}")

            # Consistency Agent Output
            if consistency_result.get("status") == "success" and consistency_result.get("output"):
                logger.info("Storing consistency analysis")
                consistency_output_to_insert = consistency_result["output"]
                if isinstance(consistency_output_to_insert, dict):
                    consistency_output_to_insert['deal_id'] = deal_id # Add deal_id
                    consistency_output_to_insert['agent_type'] = 'consistency' # Ensure agent_type is set
                    db_response = supabase.table('ai_outputs').insert(consistency_output_to_insert).execute()
                    inserted_data_counts["ai_outputs_consistency"] = len(db_response.data) if db_response.data else 0
                else:
                    logger.error(f"Consistency agent output is not a dict: {type(consistency_output_to_insert)}")
            
            if memo_result.get("status") == "success" and memo_result.get("output"):
                logger.info("Storing investment memo")
                memo_output_to_insert = memo_result["output"]
                if isinstance(memo_output_to_insert, dict):
                    memo_output_to_insert['deal_id'] = deal_id # Add deal_id
                    # Remove 'error' key if present
                    if 'error' in memo_output_to_insert:
                        del memo_output_to_insert['error']
                    db_response = supabase.table('cim_analysis').insert(memo_output_to_insert).execute()
                    inserted_data_counts["cim_analysis"] = len(db_response.data) if db_response.data else 0
                else:
                    logger.error(f"Memo agent output is not a dict: {type(memo_output_to_insert)}")

            # Storing agent execution logs (success or specific errors if any)
            for agent_name, res in agent_results.items():
                log_message = res.get('error') if res.get("status") == "error" else f"Agent {agent_name} completed with status: {res.get('status')}"
                try:
                    supabase.table('agent_logs').insert({
                        "deal_id": deal_id,
                        "user_id": user_id,
                        "agent_type": agent_name,
                        "log_type": "error" if res.get("status") == "error" else "info",
                        "message": log_message
                        # Consider adding "input_payload" and "output_payload" if relevant and available
                    }).execute()
                except Exception as db_log_err:
                    logger.error(f"Failed to log execution for agent {agent_name} to DB: {db_log_err}")

            logger.info("CIM processing completed successfully")
            return jsonify({
                "status": "success",
                "message": "CIM processed successfully",
                "results_summary": {
                    "financial": financial_result.get("status", "not_run"),
                    "risk": risk_result.get("status", "not_run"),
                    "consistency": consistency_result.get("status", "not_run"),
                    "memo": memo_result.get("status", "not_run")
                },
                "inserted_counts": inserted_data_counts
            })

        finally:
            # Clean up temporary file
            os.unlink(tmp_file.name)

    except Exception as e:
        logger.error(f"Error processing CIM: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route('/generate-memo', methods=['POST'])
def generate_memo():
    """Generate investment memo from processed data"""
    try:
        data = request.get_json()
        deal_id = data.get('deal_id')
        sections = data.get('sections', ['executive_summary', 'financial_analysis', 'risks', 'recommendation'])
        
        # This is a simplified version - in a full implementation, 
        # you'd retrieve processed data from a database
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": f"You are an investment professional. Generate a professional investment memo with these sections: {', '.join(sections)}. Use formal business language suitable for an investment committee."},
                {"role": "user", "content": f"Generate an investment memo for deal {deal_id}. Include analysis of the business model, financial performance, market opportunity, risks, and investment recommendation."}
            ],
            temperature=0.1
        )
        
        return jsonify({
            "success": True,
            "deal_id": deal_id,
            "memo": response.choices[0].message.content,
            "sections": sections,
            "generated_at": datetime.now().isoformat()
        })
        
    except Exception as e:
        print(f"Memo generation error: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/chunks/document/<deal_id>', methods=['GET'])
def get_document_chunks(deal_id):
    """
    Get document chunks for a deal with optional filtering.
    """
    try:
        section_type = request.args.get('section_type')
        processed = request.args.get('processed')
        search = request.args.get('search')
        
        query = supabase.table("document_chunks").select("*").eq("deal_id", deal_id)
        
        if section_type:
            query = query.eq("section_type", section_type)
        if processed is not None:
            query = query.eq("processed_by_ai", processed == 'true')
        if search:
            query = query.ilike("chunk_text", f"%{search}%")
            
        result = query.execute()
        return jsonify(result.data)
        
    except Exception as e:
        logger.error(f"Error getting chunks: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/chunks/relationships/<chunk_id>', methods=['GET'])
def get_chunk_relationships(chunk_id):
    """
    Get relationships for a specific chunk.
    """
    try:
        result = supabase.table("chunk_relationships")\
            .select("*")\
            .or_(f"parent_chunk_id.eq.{chunk_id},child_chunk_id.eq.{chunk_id}")\
            .execute()
        return jsonify(result.data)
        
    except Exception as e:
        logger.error(f"Error getting relationships: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/chunks/excel-links/<chunk_id>', methods=['GET'])
def get_excel_links(chunk_id):
    """
    Get Excel links for a specific chunk.
    """
    try:
        result = supabase.table("excel_to_chunk_links")\
            .select("*")\
            .eq("document_chunk_id", chunk_id)\
            .execute()
        return jsonify(result.data)
        
    except Exception as e:
        logger.error(f"Error getting Excel links: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    print("🚀 DealMate Agent Server Starting...")
    print("✅ Server ready!")
    app.run(host='0.0.0.0', port=8000, debug=False)