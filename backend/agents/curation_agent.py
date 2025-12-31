class CurationAgent:
    """
    Assigns editorial styling and palettes based on the news category.
    Optimized for a wide range of specialized AI domains.
    """
    PALETTES = {
        "Healthcare/Medical": {
            "bg": "#F0FAF9", # soft green/teal
            "accent": "#00796B", 
            "text": "#004D40",
            "border": "#B2DFDB"
        },
        "Finance/FinTech": {
            "bg": "#1A252F", # deep blue 
            "accent": "#D4AF37", # muted gold
            "text": "#FFFFFF",
            "border": "#2C3E50"
        },
        "Legal/Judiciary/Civic": {
            "bg": "#F5F5F7", # neutral greys
            "accent": "#2C3E50", # navy
            "text": "#1D1D1F",
            "border": "#D2D2D7"
        },
        "Tech/Industrial/IoT": {
            "bg": "#E8F4FD", # light blue
            "accent": "#1565C0", 
            "text": "#0D47A1",
            "border": "#BBDEFB"
        },
        "Business/HR/Marketing": {
            "bg": "#F9F1FE", # very light purple
            "accent": "#8E24AA", 
            "text": "#4A148C",
            "border": "#E1BEE7"
        },
        "General": {
            "bg": "#FFFFFF", 
            "accent": "#636E72", 
            "text": "#2D3436",
            "border": "#DFE6E9"
        }
    }

    def curate(self, news_list):
        for item in news_list:
            domain = item.get("domain", "General").lower()
            
            # Complex mapping logic for new categories
            if any(k in domain for k in ["healthcare", "medical", "healthtech"]):
                key = "Healthcare/Medical"
            elif any(k in domain for k in ["finance", "fintech"]):
                key = "Finance/FinTech"
            elif any(k in domain for k in ["judiciary", "legal", "civic"]):
                key = "Legal/Judiciary/Civic"
            elif any(k in domain for k in ["tech", "industrial", "iot", "llmops", "nlp"]):
                key = "Tech/Industrial/IoT"
            elif any(k in domain for k in ["business", "hr", "marketing", "edtech", "consumer"]):
                key = "Business/HR/Marketing"
            else:
                key = "General"
                
            item["palette"] = self.PALETTES.get(key, self.PALETTES["General"])
        return news_list
