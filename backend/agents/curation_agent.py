class CurationAgent:
    """
    Assigns editorial styling and palettes based on the news category.
    """
    PALETTES = {
        "Technology": {
            "bg": "#F0F7FF", 
            "accent": "#1565C0", 
            "text": "#0D47A1",
            "border": "#BBDEFB"
        },
        "Judiciary/Legal Tech": {
            "bg": "#F5F5F5", 
            "accent": "#455A64", 
            "text": "#263238",
            "border": "#CFD8DC"
        },
        "Business": {
            "bg": "#F1F8E9", 
            "accent": "#2E7D32", 
            "text": "#1B5E20",
            "border": "#DCEDC8"
        },
        "General": {
            "bg": "#FFF8E1", 
            "accent": "#FF8F00", 
            "text": "#5D4037",
            "border": "#FFECB3"
        }
    }

    def curate(self, news_list):
        for item in news_list:
            category = item.get("category", "General")
            # Map specific categories if they differ slightly from keys
            if "Tech" in category and "Legal" not in category:
                key = "Technology"
            elif "Legal" in category or "Judiciary" in category:
                key = "Judiciary/Legal Tech"
            elif "Business" in category:
                key = "Business"
            else:
                key = "General"
                
            item["palette"] = self.PALETTES.get(key, self.PALETTES["General"])
        return news_list
