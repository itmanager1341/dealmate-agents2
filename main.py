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
    """Process CIM (Confidential Information Memorandum) documents with specialized analysis"""
    try:
        if 'file' not in request.files:
            return jsonify({"error": "No file provided"}), 400
        
        file = request.files['file']
        deal_id = request.form.get('deal_id', 'unknown')
        
        # Extract text from CIM PDF using PyPDF2 (consistent with existing code)
        text_content = ""
        page_count = 0
        
        if file.filename.lower().endswith('.pdf'):
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                file.save(tmp_file.name)
                
                with open(tmp_file.name, 'rb') as pdf_file:
                    pdf_reader = PyPDF2.PdfReader(pdf_file)
                    page_count = len(pdf_reader.pages)
                    
                    # Extract text from all pages for comprehensive CIM analysis
                    for page in pdf_reader.pages:
                        text_content += page.extract_text()
                
                os.unlink(tmp_file.name)
        else:
            return jsonify({"error": "CIM processing only supports PDF files"}), 400
        
        # Limit text for API but keep more for CIM analysis
        analysis_text = text_content[:20000] if len(text_content) > 20000 else text_content
        
        # Specialized CIM Analysis using OpenAI
        cim_prompt = f"""
        Analyze this Confidential Information Memorandum (CIM) and provide comprehensive investment analysis.
        
        CIM Document Text:
        {analysis_text}
        
        Please provide a detailed JSON analysis with these sections:
        {{
            "investment_grade": "A+/A/A-/B+/B/B-/C+/C/C-/D+/D/F",
            "executive_summary": "Brief overview of the investment opportunity",
            "business_model": {{
                "type": "Description of business model",
                "revenue_streams": ["stream1", "stream2"],
                "key_value_propositions": ["prop1", "prop2"]
            }},
            "financial_metrics": {{
                "revenue_cagr": "X.X%",
                "ebitda_margin": "X.X%",
                "deal_size_estimate": "$XXM",
                "revenue_multiple": "X.Xx",
                "ebitda_multiple": "X.Xx"
            }},
            "key_risks": [
                {{
                    "risk": "Risk description",
                    "severity": "High/Medium/Low",
                    "impact": "Description of potential impact"
                }}
            ],
            "investment_highlights": [
                "Key positive points for investment"
            ],
            "management_questions": [
                "Critical questions to ask management in due diligence"
            ],
            "competitive_position": {{
                "strengths": ["strength1", "strength2"],
                "weaknesses": ["weakness1", "weakness2"],
                "market_position": "Description"
            }},
            "recommendation": {{
                "action": "Pursue/Pass/More Info Needed",
                "rationale": "Explanation of recommendation"
            }}
        }}
        
        Focus on extracting actual financial numbers, identifying red flags, assessing market position, and providing investment-grade analysis.
        """
        
        try:
            # Use GPT-4 for sophisticated CIM analysis if available, otherwise GPT-3.5-turbo
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a senior M&A analyst with 15+ years of experience reviewing CIMs. Provide institutional-quality investment analysis."},
                    {"role": "user", "content": cim_prompt}
                ],
                temperature=0.2,
                max_tokens=3000
            )
            
            ai_analysis = response.choices[0].message.content
            print("✅ CIM analysis completed with GPT-4")
            
        except Exception as gpt4_error:
            print(f"GPT-4 failed, falling back to GPT-3.5-turbo: {gpt4_error}")
            # Fallback to GPT-3.5-turbo
            try:
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "You are a senior M&A analyst. Provide institutional-quality investment analysis of this CIM."},
                        {"role": "user", "content": cim_prompt}
                    ],
                    temperature=0.2,
                    max_tokens=2500
                )
                ai_analysis = response.choices[0].message.content
                print("✅ CIM analysis completed with GPT-3.5-turbo fallback")
                
            except Exception as fallback_error:
                print(f"Both GPT-4 and GPT-3.5-turbo failed: {fallback_error}")
                ai_analysis = f"AI analysis failed: {str(gpt4_error)}"
        
        return jsonify({
            "success": True,
            "deal_id": deal_id,
            "filename": file.filename,
            "document_type": "CIM",
            "page_count": page_count,
            "text_length": len(text_content),
            "ai_analysis": ai_analysis,
            "processing_time": "completed",
            "analysis_type": "comprehensive_cim"
        })
        
    except Exception as e:
        print(f"CIM processing error: {e}")
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