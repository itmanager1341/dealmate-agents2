# Updated main.py with CIM processing - compatible with existing structure
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import whisper
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
from typing import Optional
from fastapi import HTTPException

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# Global variables for models
whisper_model = None

def load_whisper_model():
    """Load Whisper model on startup"""
    global whisper_model
    try:
        print("⚡ Pre-loading Whisper model...")
        whisper_model = whisper.load_model("base")
        print("✅ Whisper model loaded successfully!")
        return True
    except Exception as e:
        print(f"❌ Failed to load Whisper model: {e}")
        return False

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
    whisper_status = "ready" if whisper_model else "not_loaded"
    
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
            
            # Transcribe using Whisper
            if whisper_model:
                result = whisper_model.transcribe(tmp_file.name)
                
                # Clean up temp file
                os.unlink(tmp_file.name)
                
                return jsonify({
                    "success": True,
                    "deal_id": deal_id,
                    "filename": file.filename,
                    "transcription": result["text"],
                    "segments": result.get("segments", []),
                    "processing_time": result.get("processing_time", 0)
                })
            else:
                return jsonify({"error": "Whisper model not loaded"}), 500
                
    except Exception as e:
        print(f"Transcription error: {e}")
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

        # Get deal_id from request
        deal_id = request.form.get('deal_id')
        if not deal_id:
            logger.error("No deal_id provided")
            return jsonify({"error": "No deal_id provided"}), 400

        logger.info(f"Processing CIM for deal_id: {deal_id}")

        # Save file temporarily
        tmp_file = tempfile.NamedTemporaryFile(delete=False)
        file.save(tmp_file.name)
        tmp_file.close()

        try:
            # Initialize orchestrator
            logger.info("Initializing CIM orchestrator")
            orchestrator = CIMOrchestrator()
            
            # Extract text from PDF
            logger.info("Extracting text from PDF")
            document_text = orchestrator.load_pdf_text(tmp_file.name)
            if not document_text.strip():
                raise ValueError("No text could be extracted from the PDF")

            # Run all agents
            logger.info("Running all agents")
            result = orchestrator.run_all_agents(document_text, deal_id)
            
            # Process results
            if result["status"] == "error":
                logger.error(f"Processing failed: {result['errors']}")
                return jsonify({"error": "Processing failed", "details": result["errors"]}), 500

            # Extract results from each agent
            financial_result = result["results"]["financial"]
            risk_result = result["results"]["risk"]
            consistency_result = result["results"]["consistency"]
            memo_result = result["results"]["memo"]

            # Store results in Supabase
            if financial_result["status"] == "success" and financial_result["output"]:
                logger.info("Storing financial metrics")
                supabase.table('deal_metrics').insert(financial_result["output"]).execute()
            
            if risk_result["status"] == "success" and risk_result["output"]:
                logger.info("Storing risk analysis")
                supabase.table('ai_outputs').insert(risk_result["output"]).execute()
            
            if consistency_result["status"] == "success" and consistency_result["output"]:
                logger.info("Storing consistency analysis")
                supabase.table('ai_outputs').insert(consistency_result["output"]).execute()
            
            if memo_result["status"] == "success" and memo_result["output"]:
                logger.info("Storing investment memo")
                supabase.table('cim_analysis').insert(memo_result["output"]).execute()

            # Store any errors in agent_logs
            if result["errors"]:
                logger.warning(f"Storing {len(result['errors'])} errors in agent_logs")
                for error in result["errors"]:
                    supabase.table('agent_logs').insert({
                        "deal_id": deal_id,
                        "agent_type": "orchestrator",
                        "log_type": "error",
                        "message": error
                    }).execute()

            logger.info("CIM processing completed successfully")
            return jsonify({
                "status": "success",
                "message": "CIM processed successfully",
                "results": {
                    "financial": financial_result["status"],
                    "risk": risk_result["status"],
                    "consistency": consistency_result["status"],
                    "memo": memo_result["status"]
                }
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

@app.get("/api/chunks/document/{deal_id}")
async def get_document_chunks(
    deal_id: str,
    section_type: Optional[str] = None,
    processed: Optional[bool] = None,
    search: Optional[str] = None
):
    """
    Get document chunks for a deal with optional filtering.
    """
    try:
        query = supabase.table("document_chunks").select("*").eq("deal_id", deal_id)
        
        if section_type:
            query = query.eq("section_type", section_type)
        if processed is not None:
            query = query.eq("processed_by_ai", processed)
        if search:
            query = query.ilike("chunk_text", f"%{search}%")
            
        result = await query.execute()
        return result.data
        
    except Exception as e:
        logger.error(f"Error getting chunks: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/chunks/relationships/{chunk_id}")
async def get_chunk_relationships(chunk_id: str):
    """
    Get relationships for a specific chunk.
    """
    try:
        result = await supabase.table("chunk_relationships")\
            .select("*")\
            .or_(f"parent_chunk_id.eq.{chunk_id},child_chunk_id.eq.{chunk_id}")\
            .execute()
        return result.data
        
    except Exception as e:
        logger.error(f"Error getting relationships: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/chunks/excel-links/{chunk_id}")
async def get_excel_links(chunk_id: str):
    """
    Get Excel links for a specific chunk.
    """
    try:
        result = await supabase.table("excel_to_chunk_links")\
            .select("*")\
            .eq("document_chunk_id", chunk_id)\
            .execute()
        return result.data
        
    except Exception as e:
        logger.error(f"Error getting Excel links: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == '__main__':
    print("🚀 DealMate Agent Server Starting...")
    
    # Load Whisper model
    whisper_loaded = load_whisper_model()
    
    if not whisper_loaded:
        print("⚠️  Whisper model failed to load, audio transcription won't work")
    
    print("✅ Server ready!")
    app.run(host='0.0.0.0', port=8000, debug=False)