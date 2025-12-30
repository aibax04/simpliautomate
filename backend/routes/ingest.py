from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from pydantic import BaseModel
from typing import Optional
from backend.agents.document_reader_agent import DocumentReaderAgent
from backend.agents.url_reader_agent import URLReaderAgent
from backend.agents.topic_normalizer_agent import TopicNormalizerAgent
from backend.agents.news_suggestion_agent import LiveNewsSuggestionAgent

router = APIRouter()

class IngestRequest(BaseModel):
    url: Optional[str] = None

@router.post("/ingest-source")
async def ingest_source(
    file: Optional[UploadFile] = File(None),
    url_data: Optional[str] = Form(None) # Accepting raw string from form if needed, or JSON
):
    """
    Ingests a document or URL, extracts themes, and returns suggested news.
    """
    
    # Initialize Agents
    doc_agent = DocumentReaderAgent()
    url_agent = URLReaderAgent()
    normalizer = TopicNormalizerAgent()
    suggestion_agent = LiveNewsSuggestionAgent()
    
    extracted_data = {}
    
    # 1. Parsing
    if file:
        print(f"Processing file: {file.filename}")
        content = await file.read()
        extracted_data = await doc_agent.parse_document(content, file.filename)
    elif url_data:
        print(f"Processing URL: {url_data}")
        # Handle if it came as a JSON string field or direct string
        import json
        try:
            # Check if it's a JSON string
            if url_data.strip().startswith('{'):
                data = json.loads(url_data)
                target_url = data.get('url')
            else:
                target_url = url_data
        except:
            target_url = url_data
            
        extracted_data = await url_agent.parse_url(target_url)
    else:
        # Check raw body if not form data? 
        # For simplicity, we assume frontend sends multipart/form-data for file 
        # and JSON or Form for URL. 
        # But if the user sends JSON body for URL, FastAPI handles it if we define a Pydantic model.
        # However, mixing File and Body is tricky. 
        # We'll stick to Form fields or File.
        raise HTTPException(status_code=400, detail="No valid source provided")

    if "error" in extracted_data:
        raise HTTPException(status_code=422, detail=extracted_data["error"])

    # 2. Normalization
    normalized = normalizer.normalize(extracted_data)
    
    # 3. Suggestion
    suggestions = await suggestion_agent.suggest_news(normalized)
    
    return suggestions
