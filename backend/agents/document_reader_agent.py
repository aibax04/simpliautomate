import google.generativeai as genai
import pypdf
import docx
import io
from typing import List, Dict

class DocumentReaderAgent:
    def __init__(self):
        # Using 2.0 Flash for efficient long-context parsing
        self.model = genai.GenerativeModel('models/gemini-2.0-flash-exp')

    async def parse_document(self, file_content: bytes, filename: str) -> Dict:
        """
        Reads a document and extracts structured themes.
        """
        text = self._extract_text(file_content, filename)
        
        if not text:
            return {"error": "Could not extract text from file"}
            
        return await self._analyze_text(text)

    def _extract_text(self, content: bytes, filename: str) -> str:
        text = ""
        try:
            if filename.lower().endswith('.pdf'):
                pdf_reader = pypdf.PdfReader(io.BytesIO(content))
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
            elif filename.lower().endswith('.docx'):
                doc = docx.Document(io.BytesIO(content))
                for para in doc.paragraphs:
                    text += para.text + "\n"
            elif filename.lower().endswith('.txt'):
                text = content.decode('utf-8')
        except Exception as e:
            print(f"Error reading file {filename}: {e}")
            return ""
            
        return text

    async def _analyze_text(self, text: str) -> Dict:
        prompt = f"""
        Analyze the following document text and extract key metadata for news finding.
        
        DOCUMENT TEXT (Truncated to first 20k chars):
        {text[:20000]}
        
        EXTRACT THE FOLLOWING:
        1. Key Topics: Main subjects (e.g. "AI Regulation", "Crypto Markets").
        2. Entities: Important companies, people, or courts mentioned.
        3. Jurisdiction: If legal/policy, which country/region?
        4. Sector Relevance: Is this Tech, Legal, or Business?
        
        Return ONLY valid JSON:
        {{
            "topics": ["string"],
            "entities": ["string"],
            "jurisdiction": "string",
            "sector": "string"
        }}
        """
        
        try:
            response = await self.model.generate_content_async(prompt)
            # Basic cleanup
            text_res = response.text.strip()
            if "```json" in text_res:
                text_res = text_res.split("```json")[1].split("```")[0].strip()
            elif "```" in text_res:
                text_res = text_res.split("```")[1].split("```")[0].strip()
            
            import json
            return json.loads(text_res)
        except Exception as e:
            print(f"Error parsing document with Gemini: {e}")
            return {"error": str(e)}
