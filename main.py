from flask import Flask, request, jsonify
import whisper
import pandas as pd
import os
import requests
import json
from datetime import datetime
from openai import OpenAI
from PyPDF2 import PdfReader
from docx import Document
import tempfile
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# Initialize Whisper model (will download on first use)
whisper_model = None

def load_whisper():
    global whisper_model
    if whisper_model is None:
        print("Loading Whisper model...")
        whisper_model = whisper.load_model("base")
        print("Whisper model loaded!")
    return whisper_model

def download_file(url):
    """Download a file from URL and return temporary file path"""
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        # Create temporary file
        suffix = '.' + url.split('.')[-1] if '.' in url else '.tmp'
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        temp_file.write(response.content)
        temp_file.close()
        
        return temp_file.name
    except Exception as e:
        raise Exception(f"Failed to download file: {str(e)}")

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "whisper": "ready" if whisper_model else "not_loaded",
            "openai": "configured" if os.getenv('OPENAI_API_KEY') else "missing_key"
        }
    })

@app.route('/transcribe', methods=['POST'])
def transcribe_audio():
    """Transcribe audio file using Whisper"""
    try:
        data = request.get_json()
        file_url = data.get('file_url')
        deal_id = data.get('deal_id', 'unknown')
        
        if not file_url:
            return jsonify({"error": "file_url is required"}), 400
        
        print(f"[TRANSCRIBE] Starting transcription for deal {deal_id}")
        
        # Download audio file
        temp_path = download_file(file_url)
        
        try:
            # Load Whisper model and transcribe
            model = load_whisper()
            result = model.transcribe(temp_path)
            
            # Clean up
            os.unlink(temp_path)
            
            response_data = {
                "success": True,
                "agent_type": "transcriber",
                "deal_id": deal_id,
                "transcript": result["text"],
                "language": result.get("language", "unknown"),
                "segments": result.get("segments", [])[:10],  # Limit segments for response size
                "processed_at": datetime.now().isoformat()
            }
            
            print(f"[TRANSCRIBE] Completed for deal {deal_id}")
            return jsonify(response_data)
            
        except Exception as e:
            # Clean up on error
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            raise e
            
    except Exception as e:
        print(f"[TRANSCRIBE] Error: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/process-excel', methods=['POST'])
def process_excel():
    """Process Excel file and extract financial metrics"""
    try:
        data = request.get_json()
        file_url = data.get('file_url')
        deal_id = data.get('deal_id', 'unknown')
        
        if not file_url:
            return jsonify({"error": "file_url is required"}), 400
        
        print(f"[EXCEL] Processing Excel for deal {deal_id}")
        
        # Download Excel file
        temp_path = download_file(file_url)
        
        try:
            # Read all sheets
            excel_data = pd.read_excel(temp_path, sheet_name=None)
            
            # Process each sheet
            processed_sheets = {}
            financial_metrics = {}
            
            for sheet_name, df in excel_data.items():
                # Basic sheet info
                processed_sheets[sheet_name] = {
                    "rows": len(df),
                    "columns": len(df.columns),
                    "column_names": df.columns.tolist()[:10]  # Limit for response size
                }
                
                # Convert sheet to text for AI analysis
                sheet_preview = df.head(20).to_string()  # First 20 rows only
                
                # AI analysis prompt
                prompt = f"""
                Analyze this Excel sheet and extract financial metrics. Return only valid JSON.
                
                Sheet: {sheet_name}
                Data preview:
                {sheet_preview}
                
                Extract metrics like:
                {{"revenue": null, "ebitda": null, "cash_flow": null, "growth_rate": null, "margins": null}}
                
                Only include metrics you can clearly identify. Use null for missing data.
                """
                
                try:
                    response = client.chat.completions.create(
                        model="gpt-4",
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0.1,
                        max_tokens=500
                    )
                    
                    # Parse response
                    ai_response = response.choices[0].message.content.strip()
                    # Clean up response (remove markdown formatting if present)
                    if ai_response.startswith('```json'):
                        ai_response = ai_response.replace('```json', '').replace('```', '').strip()
                    
                    metrics = json.loads(ai_response)
                    financial_metrics[sheet_name] = metrics
                    
                except Exception as ai_error:
                    print(f"[EXCEL] AI processing error for {sheet_name}: {ai_error}")
                    financial_metrics[sheet_name] = {"error": "Could not process with AI"}
            
            # Clean up
            os.unlink(temp_path)
            
            response_data = {
                "success": True,
                "agent_type": "excel_processor",
                "deal_id": deal_id,
                "sheets_found": list(processed_sheets.keys()),
                "sheet_details": processed_sheets,
                "financial_metrics": financial_metrics,
                "processed_at": datetime.now().isoformat()
            }
            
            print(f"[EXCEL] Completed for deal {deal_id}")
            return jsonify(response_data)
            
        except Exception as e:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            raise e
            
    except Exception as e:
        print(f"[EXCEL] Error: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/process-document', methods=['POST'])
def process_document():
    """Process PDF or Word document"""
    try:
        data = request.get_json()
        file_url = data.get('file_url')
        deal_id = data.get('deal_id', 'unknown')
        
        if not file_url:
            return jsonify({"error": "file_url is required"}), 400
        
        print(f"[DOCUMENT] Processing document for deal {deal_id}")
        
        # Download document
        temp_path = download_file(file_url)
        
        try:
            # Extract text based on file type
            file_extension = file_url.lower().split('.')[-1]
            text_content = ""
            
            if file_extension == 'pdf':
                reader = PdfReader(temp_path)
                for page in reader.pages:
                    text_content += page.extract_text() + "\n"
                    
            elif file_extension in ['docx', 'doc']:
                doc = Document(temp_path)
                for paragraph in doc.paragraphs:
                    text_content += paragraph.text + "\n"
            else:
                raise Exception(f"Unsupported file type: {file_extension}")
            
            # Clean up
            os.unlink(temp_path)
            
            # AI analysis
            prompt = f"""
            Analyze this business document for investment purposes. Return only valid JSON.
            
            Document content (first 3000 chars):
            {text_content[:3000]}
            
            Extract:
            {{
                "business_model": "brief description",
                "market_position": "market position summary",
                "financial_highlights": "key financial points",
                "growth_drivers": "growth factors",
                "risk_factors": "potential risks",
                "investment_thesis": "why invest"
            }}
            """
            
            try:
                response = client.chat.completions.create(
                    model="gpt-4",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.2,
                    max_tokens=1000
                )
                
                ai_response = response.choices[0].message.content.strip()
                if ai_response.startswith('```json'):
                    ai_response = ai_response.replace('```json', '').replace('```', '').strip()
                
                analysis = json.loads(ai_response)
                
            except Exception as ai_error:
                print(f"[DOCUMENT] AI analysis error: {ai_error}")
                analysis = {"error": "Could not analyze document"}
            
            response_data = {
                "success": True,
                "agent_type": "document_processor", 
                "deal_id": deal_id,
                "document_type": file_extension,
                "text_length": len(text_content),
                "analysis": analysis,
                "processed_at": datetime.now().isoformat()
            }
            
            print(f"[DOCUMENT] Completed for deal {deal_id}")
            return jsonify(response_data)
            
        except Exception as e:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            raise e
            
    except Exception as e:
        print(f"[DOCUMENT] Error: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/generate-memo', methods=['POST'])
def generate_memo():
    """Generate investment memo from deal data"""
    try:
        data = request.get_json()
        deal_data = data.get('deal_data', {})
        deal_id = data.get('deal_id', 'unknown')
        
        print(f"[MEMO] Generating memo for deal {deal_id}")
        
        # Create comprehensive prompt
        prompt = f"""
        Generate a professional investment committee memo based on this deal analysis.
        Return only valid JSON with the structure below.
        
        Deal Data:
        {json.dumps(deal_data, indent=2)[:2000]}
        
        Create memo with these sections:
        {{
            "executive_summary": "2-3 sentence overview",
            "business_overview": "business model and market position", 
            "financial_highlights": "key financial metrics and trends",
            "investment_drivers": "reasons to invest",
            "risk_factors": "key risks and concerns",
            "recommendation": "invest/pass with brief rationale"
        }}
        
        Write professionally but concisely for senior stakeholders.
        """
        
        try:
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=1500
            )
            
            ai_response = response.choices[0].message.content.strip()
            if ai_response.startswith('```json'):
                ai_response = ai_response.replace('```json', '').replace('```', '').strip()
            
            memo_content = json.loads(ai_response)
            
        except Exception as ai_error:
            print(f"[MEMO] Generation error: {ai_error}")
            memo_content = {"error": "Could not generate memo"}
        
        response_data = {
            "success": True,
            "agent_type": "memo_drafter",
            "deal_id": deal_id,
            "memo": memo_content,
            "generated_at": datetime.now().isoformat()
        }
        
        print(f"[MEMO] Completed for deal {deal_id}")
        return jsonify(response_data)
        
    except Exception as e:
        print(f"[MEMO] Error: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == '__main__':
    print("🚀 DealMate Agent Server Starting...")
    print("📋 Available Endpoints:")
    print("   GET  /health          - Health check")
    print("   POST /transcribe      - Audio → Text")  
    print("   POST /process-excel   - Excel → Metrics")
    print("   POST /process-document - PDF/Word → Analysis")
    print("   POST /generate-memo   - Data → Investment Memo")
    print("\n⚡ Pre-loading Whisper model...")
    
    # Pre-load Whisper to avoid first-request delay
    load_whisper()
    
    print("✅ Server ready!")
    app.run(host='0.0.0.0', port=8000, debug=False)