from typing import List, Dict

class IdeaGenerator:
    """
    Generates trading setups or product ideas based on market intensity.
    """
    def __init__(self, templates: Dict[str, str] = None):
        self.templates = templates or {
            "AI": "Build a specialized Agentic SDK or bridge for decentralized AI inference protocols.",
            "DeFi": "Implement a Cross-DEX arbitrage strategy or a multi-chain liquidity aggregator.",
            "DePIN": "Design a reward distribution mechanism for small-scale hardware participants.",
            "Meme": "Create a sentiment-based launchpad or a volatility-hedging derivative.",
            "Gaming": "Develop an interoperable asset bridge for cross-game NFT mobility.",
            "RWA": "Construct a synthetic yield product tied to tokenized real estate or treasury bonds."
        }

    def generate(self, intensity: Dict[str, float]) -> List[str]:
        # Sort narratives by intensity
        sorted_narratives = sorted(intensity.items(), key=lambda x: x[1], reverse=True)
        
        ideas = []
        for cat, score in sorted_narratives[:2]: # Top 2
            if score > 3.0: # Minimum intensity threshold
                idea = self.templates.get(cat, "Generic product improvement.")
                ideas.append(f"Narrative: {cat} (Intensity: {score:.1f}/10) -> Idea: {idea}")
        
        return ideas

if __name__ == "__main__":
    intensity = {"AI": 8.5, "Meme": 4.2, "DeFi": 2.1}
    gen = IdeaGenerator()
    ideas = gen.generate(intensity)
    print("--- Narrative-Driven Ideas ---")
    for idea in ideas:
        print(idea)
