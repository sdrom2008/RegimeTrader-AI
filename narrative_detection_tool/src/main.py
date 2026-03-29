import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from classifier import NarrativeClassifier
from idea_generator import IdeaGenerator

def main():
    """
    Main loop for Narrative Detection & Idea Generation Tool.
    """
    # 1. Aggregator (Simulated for Prototype)
    mock_posts = [
        {"text": "AI agents on Solana are the next big thing! GPU inference is key."},
        {"text": "Pepe is mooning again, look at that meme volume."},
        {"text": "New DePIN project connecting decentralized sensors for weather data."},
        {"text": "DeFi perps on Drift are growing fast."},
        {"text": "AI and blockchain convergence is the 2026 narrative."},
        {"text": "Build anything on Solana with AI agents! GPU protocols are surging."},
    ]

    # 2. Classifier: Detect Narrative & Intensity
    classifier = NarrativeClassifier()
    intensity = classifier.calculate_intensity(mock_posts)

    # 3. Idea Generator: Propose Work
    gen = IdeaGenerator()
    ideas = gen.generate(intensity)

    print("--- Narrative Intelligence (2026-03-10) ---")
    print("Market Intensity Summary:")
    for cat, score in intensity.items():
        if score > 0:
            print(f"  {cat}: {score:.1f}/10")
    
    print("\n--- Proposed Opportunities ---")
    for idea in ideas:
        print(f"  - {idea}")

if __name__ == "__main__":
    main()
