import numpy as np
from typing import List, Dict

class NarrativeClassifier:
    """
    Classifies text data into crypto narratives and calculates intensity.
    """
    def __init__(self, categories: List[str] = ["AI", "DeFi", "DePIN", "Meme", "Gaming", "RWA"]):
        self.categories = categories

    def classify_post(self, text: str) -> str:
        # In a real app, this would be an LLM call or a trained transformer.
        # For the prototype, we use keyword matching as a baseline.
        text = text.lower()
        if any(kw in text for kw in ["ai", "gpu", "inference", "agent"]):
            return "AI"
        if any(kw in text for kw in ["dex", "yield", "stablecoin", "amm", "perp"]):
            return "DeFi"
        if any(kw in text for kw in ["hardware", "iot", "sensor", "storage", "decentralized infra"]):
            return "DePIN"
        if any(kw in text for kw in ["pepe", "doge", "wif", "bonk", "shib"]):
            return "Meme"
        if any(kw in text for kw in ["nft", "play", "metaverse", "unreal"]):
            return "Gaming"
        if any(kw in text for kw in ["bond", "treasury", "real estate", "tokenized asset"]):
            return "RWA"
        return "Unknown"

    def calculate_intensity(self, posts: List[Dict]) -> Dict[str, float]:
        """
        Calculates intensity based on volume and growth in a time window.
        """
        counts = {cat: 0 for cat in self.categories}
        for post in posts:
            category = self.classify_post(post['text'])
            if category in counts:
                counts[category] += 1
        
        total = sum(counts.values()) or 1
        intensity = {cat: (count / total) * 10 for cat, count in counts.items()}
        return intensity

if __name__ == "__main__":
    mock_posts = [
        {"text": "AI agents on Solana are the next big thing! GPU inference is key."},
        {"text": "Pepe is mooning again, look at that meme volume."},
        {"text": "New DePIN project connecting decentralized sensors for weather data."},
        {"text": "DeFi perps on Drift are growing fast."},
        {"text": "AI and blockchain convergence is the 2026 narrative."},
    ]
    
    classifier = NarrativeClassifier()
    intensity = classifier.calculate_intensity(mock_posts)
    print("--- Narrative Intensity Report ---")
    for cat, score in intensity.items():
        print(f"{cat}: {score:.1f}/10")
