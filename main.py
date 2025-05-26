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
    """Process CIM with multi-agent architecture and write to Supabase"""
    try:
        from orchestrator.cim_orchestrator import CIMOrchestrator
        from orchestrator.supabase import supabase
        import tempfile
        import os

        if 'file' not in request.files:
            return jsonify({"error": "No file provided"}), 400

        file = request.files['file']
        deal_id = request.form.get('deal_id', 'unknown')

        if file.filename == '':
            return jsonify({"error": "No file selected"}), 400

        # Save file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            file_path = tmp_file.name
            file.save(file_path)

        # Run multi-agent orchestrator
        orchestrator = CIMOrchestrator()
        result = orchestrator.run_all(file_path=file_path, deal_id=deal_id)

        # Remove file after use
        os.remove(file_path)

        # Collect inserts
        inserted = {
            "deal_metrics": [],
            "ai_outputs": [],
            "cim_analysis": [],
            "agent_logs": []
        }

        # Write deal_metrics
        metrics = result["results"]["financial"].get("output", [])
        if isinstance(metrics, list):
            for m in metrics:
                if isinstance(m, dict):
                    m["deal_id"] = deal_id
                    inserted["deal_metrics"].append(m)
                else:
                    print(f"❌ Invalid metric format: {m}")
                    inserted["agent_logs"].append({
                        "deal_id": deal_id,
                        "agent_name": "financial_agent",
                        "input_payload": "CIM text (omitted for brevity)",
                        "output_payload": str(m),
                        "status": "failed",
                        "error_message": "Invalid metric format - expected dictionary"
                    })
        else:
            print(f"❌ Financial metrics is not a list: {metrics}")
            inserted["agent_logs"].append({
                "deal_id": deal_id,
                "agent_name": "financial_agent",
                "input_payload": "CIM text (omitted for brevity)",
                "output_payload": str(metrics),
                "status": "failed",
                "error_message": "Invalid metrics format - expected list"
            })
            if "errors" not in result:
                result["errors"] = []
            result["errors"].append("Financial agent returned invalid output format")

        if inserted["deal_metrics"]:
            supabase.table("deal_metrics").insert(inserted["deal_metrics"]).execute()

        # Write ai_outputs (risks + consistency)
        for key in ["risk", "consistency"]:
            output = result["results"][key].get("output", {})
            if isinstance(output, dict) and "items" in output:
                for item in output["items"]:
                    if isinstance(item, dict):
                        inserted["ai_outputs"].append({
                            "deal_id": deal_id,
                            "agent_type": f"{key}_agent",
                            "output_type": output.get("output_type", f"{key}_summary"),
                            "output_json": item
                        })
                    else:
                        print(f"❌ Invalid {key} item format: {item}")
                        inserted["agent_logs"].append({
                            "deal_id": deal_id,
                            "agent_name": f"{key}_agent",
                            "input_payload": "CIM text (omitted for brevity)",
                            "output_payload": str(item),
                            "status": "failed",
                            "error_message": f"Invalid {key} item format - expected dictionary"
                        })
            else:
                print(f"❌ Invalid {key} output format: {output}")
                inserted["agent_logs"].append({
                    "deal_id": deal_id,
                    "agent_name": f"{key}_agent",
                    "input_payload": "CIM text (omitted for brevity)",
                    "output_payload": str(output),
                    "status": "failed",
                    "error_message": f"Invalid {key} output format - expected dict with items"
                })
                if "errors" not in result:
                    result["errors"] = []
                result["errors"].append(f"{key.title()} agent returned invalid output format")

        if inserted["ai_outputs"]:
            supabase.table("ai_outputs").insert(inserted["ai_outputs"]).execute()

        # Write cim_analysis (memo block)
        memo_output = result["results"]["memo"].get("output", {})
        if isinstance(memo_output, dict):
            memo_output["deal_id"] = deal_id
            inserted["cim_analysis"].append(memo_output)
            if inserted["cim_analysis"]:
                supabase.table("cim_analysis").insert(inserted["cim_analysis"]).execute()
        else:
            print(f"❌ Memo output is not a dictionary: {memo_output}")
            if "errors" not in result:
                result["errors"] = []
            result["errors"].append("Memo agent returned invalid output format")
            inserted["agent_logs"].append({
                "deal_id": deal_id,
                "agent_name": "memo_agent",
                "input_payload": "CIM text (omitted for brevity)",
                "output_payload": str(memo_output),
                "status": "failed",
                "error_message": "Invalid memo format - expected dictionary"
            })

        # Write agent_logs
        for agent_name, logs in result.get("logs", {}).items():
            inserted["agent_logs"].append({
                "deal_id": deal_id,
                "agent_name": agent_name,
                "input_payload": "CIM text (omitted for brevity)",
                "output_payload": result["results"].get(agent_name, {}).get("output"),
                "status": "success" if result["results"].get(agent_name, {}).get("success") else "failed",
                "error_message": result["results"].get(agent_name, {}).get("error", None)
            })
        if inserted["agent_logs"]:
            supabase.table("agent_logs").insert(inserted["agent_logs"]).execute()

        return jsonify({
            "success": True,
            "deal_id": deal_id,
            "message": "CIM processed and stored",
            "status": result.get("status", "complete"),
            "errors": result.get("errors", []),
            "written": {k: len(v) for k, v in inserted.items()}
        })

    except Exception as e:
        traceback.print_exc()
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

if __name__ == '__main__':
    print("🚀 DealMate Agent Server Starting...")
    
    # Load Whisper model
    whisper_loaded = load_whisper_model()
    
    if not whisper_loaded:
        print("⚠️  Whisper model failed to load, audio transcription won't work")
    
    print("✅ Server ready!")
    app.run(host='0.0.0.0', port=8000, debug=False)