class CurationAgent:
    """
    Assigns editorial styling and palettes based on the news category.
    Optimized for Legal AI, Healthcare AI, and Business AI.
    """
    PALETTES = {
        "Legal AI": {
            "bg": "#F5F5F7", 
            "accent": "#4A4A4A", 
            "text": "#1D1D1F",
            "border": "#D2D2D7"
        },
        "Healthcare AI": {
            "bg": "#F0FAF9", 
            "accent": "#00796B", 
            "text": "#004D40",
            "border": "#B2DFDB"
        },
        "Business AI": {
            "bg": "#F8F9FA", 
            "accent": "#2C3E50", 
            "text": "#1A252F",
            "border": "#E9ECEF"
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
            # Updated to use 'domain' as per new NewsFetchAgent schema
            domain = item.get("domain", "General")
            
            # Match strict domain categories
            if "Legal AI" in domain:
                key = "Legal AI"
            elif "Healthcare AI" in domain:
                key = "Healthcare AI"
            elif "Business AI" in domain:
                key = "Business AI"
            else:
                key = "General"
                
            item["palette"] = self.PALETTES.get(key, self.PALETTES["General"])
        return news_list
