from typing import Dict, List

class TopicNormalizerAgent:
    def normalize(self, extracted_data: Dict) -> Dict:
        """
        Refines extracted data into search queries and filters.
        """
        if "error" in extracted_data:
            return extracted_data

        topics = extracted_data.get("topics", [])
        entities = extracted_data.get("entities", [])
        sector = extracted_data.get("sector", "General")
        
        # Create optimized search queries
        queries = []
        
        # Combine top topic + entity for precise search
        if topics and entities:
            queries.append(f"{topics[0]} {entities[0]} news")
            
        # General topic search
        if topics:
            for t in topics[:2]:
                queries.append(f"{t} news")
                
        # Fallback if empty (shouldn't happen with Gemini)
        if not queries:
            queries.append(f"{sector} news")

        return {
            "search_queries": queries,
            "primary_category": sector,
            "keywords": topics + entities
        }
