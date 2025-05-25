from flask import Flask, request, jsonify
from flask_cors import CORS
import openai
import whisper
import pandas as pd
import PyPDF2
from docx import Document
import json
import logging
import traceback
import tempfile
import os
from datetime import datetime
import fitz  # PyMuPDF for better PDF processing

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Load OpenAI API key from environment
openai.api_key = os.getenv('OPENAI_API_KEY')
if not openai.api_key:
    logger.warning("OpenAI API key not found in environment variables")

print("🚀 DealMate Agent Server Starting...")

# Pre-load Whisper model for faster transcription
print("⚡ Pre-loading Whisper model...")
try:
    whisper_model = whisper.load_model("base")
    print("✅ Whisper model loaded successfully!")
except Exception as e:
    print(f"❌ Failed to load Whisper model: {e}")
    whisper_model = None

@app.route('/')
def root():
    """Root endpoint with API documentation"""
    return jsonify({
        "service": "DealMate AI Agent Server",
        "version": "1.0.0",
        "status": "running",
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

@app.route('/health')
def health_check():
    """Health check endpoint"""
    try:
        # Check OpenAI API
        openai_status = "configured" if openai.api_key else "not_configured"
        
        # Check Whisper model
        whisper_status = "ready" if whisper_model else "not_loaded"
        
        return jsonify({
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "services": {
                "openai": openai_status,
                "whisper": whisper_status
            }
        })
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            "status": "unhealthy",
            "error": str(e)
        }), 500

@app.route('/transcribe', methods=['POST'])
def transcribe_audio():
    """Transcribe audio files using Whisper"""
    try:
        if 'file' not in request.files:
            return jsonify({"error": "No file provided"}), 400
        
        file = request.files['file']
        deal_id = request.form.get('deal_id', 'unknown')
        
        if not whisper_model:
            return jsonify({"error": "Whisper model not available"}), 500
        
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix='.audio') as temp_file:
            file.save(temp_file.name)
            
            try:
                # Transcribe audio
                logger.info(f"Transcribing audio file for deal {deal_id}")
                result = whisper_model.transcribe(temp_file.name)
                
                return jsonify({
                    "success": True,
                    "transcript": result["text"],
                    "segments": result.get("segments", []),
                    "language": result.get("language", "unknown"),
                    "deal_id": deal_id,
                    "processing_time": "completed"
                })
                
            finally:
                # Clean up temporary file
                os.unlink(temp_file.name)
                
    except Exception as e:
        logger.error(f"Audio transcription failed: {e}")
        logger.error(traceback.format_exc())
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/process-excel', methods=['POST'])
def process_excel():
    """Process Excel files for financial metrics extraction"""
    try:
        if 'file' not in request.files:
            return jsonify({"error": "No file provided"}), 400
        
        file = request.files['file']
        deal_id = request.form.get('deal_id', 'unknown')
        
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as temp_file:
            file.save(temp_file.name)
            
            try:
                # Read Excel file
                logger.info(f"Processing Excel file for deal {deal_id}")
                excel_data = pd.read_excel(temp_file.name, sheet_name=None, nrows=50)
                
                # Process each sheet
                sheets_data = {}
                for sheet_name, df in excel_data.items():
                    # Convert to JSON-serializable format
                    sheets_data[sheet_name] = {
                        "columns": df.columns.tolist(),
                        "data": df.fillna("").to_dict('records')[:20],  # Limit rows
                        "shape": df.shape
                    }
                
                # Prepare data for AI analysis
                data_summary = ""
                for sheet_name, sheet_info in sheets_data.items():
                    data_summary += f"\nSheet: {sheet_name}\n"
                    data_summary += f"Columns: {', '.join(sheet_info['columns'])}\n"
                    data_summary += f"Rows: {sheet_info['shape'][0]}\n"
                    
                    # Add sample data
                    if sheet_info['data']:
                        data_summary += "Sample data:\n"
                        for i, row in enumerate(sheet_info['data'][:5]):
                            data_summary += f"Row {i+1}: {str(row)}\n"
                
                # AI Analysis
                ai_analysis = None
                if openai.api_key:
                    try:
                        prompt = f"""
                        Analyze this Excel financial data and extract key metrics:
                        
                        {data_summary}
                        
                        Please provide a JSON response with:
                        {{
                            "financial_metrics": {{
                                "revenue": {{"monthly": [], "annual": null}},
                                "expenses": {{"monthly": [], "annual": null}},
                                "profit": {{"monthly": [], "annual": null}},
                                "growth_rate": {{"monthly": [], "annual": null}}
                            }},
                            "key_insights": [],
                            "data_quality": "high/medium/low",
                            "recommendations": []
                        }}
                        
                        Extract actual numbers where possible and calculate growth rates.
                        """
                        
                        response = openai.ChatCompletion.create(
                            model="gpt-3.5-turbo",
                            messages=[{"role": "user", "content": prompt}],
                            max_tokens=1500,
                            temperature=0.3
                        )
                        
                        ai_analysis = response.choices[0].message.content
                        logger.info("OpenAI processing completed")
                        
                    except Exception as ai_error:
                        logger.error(f"OpenAI processing failed: {ai_error}")
                        ai_analysis = f"AI analysis failed: {str(ai_error)}"
                
                return jsonify({
                    "success": True,
                    "deal_id": deal_id,
                    "sheets": list(sheets_data.keys()),
                    "raw_data_preview": sheets_data,
                    "ai_analysis": ai_analysis,
                    "processing_time": "completed"
                })
                
            finally:
                # Clean up temporary file
                os.unlink(temp_file.name)
                
    except Exception as e:
        logger.error(f"Excel processing failed: {e}")
        logger.error(traceback.format_exc())
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/process-document', methods=['POST'])
def process_document():
    """Process PDF/DOCX documents for business analysis"""
    try:
        if 'file' not in request.files:
            return jsonify({"error": "No file provided"}), 400
        
        file = request.files['file']
        deal_id = request.form.get('deal_id', 'unknown')
        filename = file.filename.lower()
        
        # Extract text based on file type
        extracted_text = ""
        
        if filename.endswith('.pdf'):
            # Use PyMuPDF for better PDF processing
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
                file.save(temp_file.name)
                try:
                    doc = fitz.open(temp_file.name)
                    for page in doc:
                        extracted_text += page.get_text()
                    doc.close()
                finally:
                    os.unlink(temp_file.name)
                    
        elif filename.endswith(('.docx', '.doc')):
            with tempfile.NamedTemporaryFile(delete=False, suffix='.docx') as temp_file:
                file.save(temp_file.name)
                try:
                    doc = Document(temp_file.name)
                    for paragraph in doc.paragraphs:
                        extracted_text += paragraph.text + "\n"
                finally:
                    os.unlink(temp_file.name)
        
        # Limit text length for API
        if len(extracted_text) > 15000:
            extracted_text = extracted_text[:15000] + "..."
        
        # AI Analysis
        ai_analysis = None
        if openai.api_key and extracted_text:
            try:
                prompt = f"""
                Analyze this business document and provide key insights:
                
                Document Text:
                {extracted_text}
                
                Please provide analysis covering:
                1. Business model and revenue streams
                2. Market position and competitive advantages
                3. Financial performance indicators
                4. Key risks and concerns
                5. Growth opportunities
                6. Management team assessment (if mentioned)
                
                Format as structured JSON with clear sections.
                """
                
                response = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=2000,
                    temperature=0.3
                )
                
                ai_analysis = response.choices[0].message.content
                logger.info("Document analysis completed")
                
            except Exception as ai_error:
                logger.error(f"Document AI analysis failed: {ai_error}")
                ai_analysis = f"AI analysis failed: {str(ai_error)}"
        
        return jsonify({
            "success": True,
            "deal_id": deal_id,
            "text_length": len(extracted_text),
            "extracted_text": extracted_text[:2000] + "..." if len(extracted_text) > 2000 else extracted_text,
            "ai_analysis": ai_analysis,
            "processing_time": "completed"
        })
        
    except Exception as e:
        logger.error(f"Document processing failed: {e}")
        logger.error(traceback.format_exc())
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/process-cim', methods=['POST'])
def process_cim():
    """Process CIM (Confidential Information Memorandum) documents with specialized analysis"""
    try:
        if 'file' not in request.files:
            return jsonify({"error": "No file provided"}), 400
        
        file = request.files['file']
        deal_id = request.form.get('deal_id', 'unknown')
        
        # Extract text from CIM PDF
        extracted_text = ""
        page_count = 0
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
            file.save(temp_file.name)
            try:
                doc = fitz.open(temp_file.name)
                page_count = len(doc)
                
                # Extract text from all pages for comprehensive analysis
                for page in doc:
                    extracted_text += page.get_text()
                doc.close()
            finally:
                os.unlink(temp_file.name)
        
        # Limit text for API but keep more for CIM analysis
        if len(extracted_text) > 25000:
            extracted_text = extracted_text[:25000] + "..."
        
        # Specialized CIM Analysis
        ai_analysis = None
        if openai.api_key and extracted_text:
            try:
                cim_prompt = f"""
                Analyze this Confidential Information Memorandum (CIM) and provide comprehensive investment analysis:
                
                CIM Document Text:
                {extracted_text}
                
                Please provide a detailed JSON analysis with these sections:
                {{
                    "investment_grade": "A+/A/A-/B+/B/B-/C+/C/C-/D+/D/F",
                    "executive_summary": "Brief overview of the investment opportunity",
                    "business_model": {{
                        "type": "Description of business model",
                        "revenue_streams": [],
                        "key_value_propositions": []
                    }},
                    "financial_metrics": {{
                        "revenue_cagr": "X.X%",
                        "ebitda_margin": "X.X%",
                        "deal_size_estimate": "$XXM",
                        "historical_performance": {{}}
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
                        "Critical questions to ask management"
                    ],
                    "competitive_position": {{
                        "strengths": [],
                        "weaknesses": [],
                        "market_position": "Description"
                    }},
                    "recommendation": {{
                        "action": "Pursue/Pass/More Info Needed",
                        "rationale": "Explanation of recommendation"
                    }}
                }}
                
                Focus on:
                - Extracting actual financial numbers where available
                - Identifying red flags and risk factors
                - Assessing market position and competitive advantages
                - Evaluating management team and governance
                - Analyzing growth prospects and scalability
                """
                
                response = openai.ChatCompletion.create(
                    model="gpt-4",  # Use GPT-4 for more sophisticated CIM analysis
                    messages=[{"role": "user", "content": cim_prompt}],
                    max_tokens=3000,
                    temperature=0.2  # Lower temperature for more consistent analysis
                )
                
                ai_analysis = response.choices[0].message.content
                logger.info("CIM analysis completed")
                
            except Exception as ai_error:
                logger.error(f"CIM AI analysis failed: {ai_error}")
                # Fallback to GPT-3.5 if GPT-4 fails
                try:
                    response = openai.ChatCompletion.create(
                        model="gpt-3.5-turbo",
                        messages=[{"role": "user", "content": cim_prompt}],
                        max_tokens=2500,
                        temperature=0.2
                    )
                    ai_analysis = response.choices[0].message.content
                    logger.info("CIM analysis completed with GPT-3.5 fallback")
                except Exception as fallback_error:
                    logger.error(f"CIM fallback analysis failed: {fallback_error}")
                    ai_analysis = f"AI analysis failed: {str(ai_error)}"
        
        return jsonify({
            "success": True,
            "deal_id": deal_id,
            "document_type": "CIM",
            "page_count": page_count,
            "text_length": len(extracted_text),
            "ai_analysis": ai_analysis,
            "processing_time": "completed",
            "analysis_type": "comprehensive_cim"
        })
        
    except Exception as e:
        logger.error(f"CIM processing failed: {e}")
        logger.error(traceback.format_exc())
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/generate-memo', methods=['POST'])
def generate_memo():
    """Generate investment memo from processed deal data"""
    try:
        data = request.get_json()
        deal_id = data.get('deal_id')
        sections = data.get('sections', ['executive_summary', 'financial_analysis', 'risks', 'recommendation'])
        
        if not deal_id:
            return jsonify({"error": "Deal ID is required"}), 400
        
        # This would typically fetch processed data from your database
        # For now, return a template structure
        
        memo_prompt = f"""
        Generate an investment memo for deal {deal_id} with the following sections: {', '.join(sections)}
        
        The memo should be professional and suitable for investment committee review.
        Include specific financial metrics, risk assessments, and clear recommendations.
        """
        
        ai_memo = None
        if openai.api_key:
            try:
                response = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": memo_prompt}],
                    max_tokens=2000,
                    temperature=0.3
                )
                
                ai_memo = response.choices[0].message.content
                logger.info("Investment memo generated")
                
            except Exception as ai_error:
                logger.error(f"Memo generation failed: {ai_error}")
                ai_memo = f"Memo generation failed: {str(ai_error)}"
        
        return jsonify({
            "success": True,
            "deal_id": deal_id,
            "memo": ai_memo,
            "sections": sections,
            "generated_at": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Memo generation failed: {e}")
        logger.error(traceback.format_exc())
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    print("✅ Server ready!")
    app.run(host='0.0.0.0', port=8000, debug=False)