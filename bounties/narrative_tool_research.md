# Solana Narrative Detection Tool - Research & Architecture Plan ($3,500 Bounty)

## 1. Objective
Build an AI Agent capable of tracking early Solana ecosystem signals to output emerging narratives and 3-5 build ideas per narrative.

## 2. Data Sources & APIs
### A. On-Chain Signals (High Priority)
- **Helius Digital Asset Standard (DAS) API**: Track new token mints and NFT collections.
- **Birdeye API**: Real-time volume spikes on DEXs (Jupiter/Raydium).
- **Pump.fun Activity**: Monitoring the "meme-to-utility" funnel.
- **Whale Monitoring**: Tracking 100+ "Smart Money" wallets for rotation patterns.

### B. Developer Signals (Mid Priority)
- **GitHub API**: Search for `language:rust` + `topic:solana` and track repo creation rates.
- **Solana Stack Exchange / Dev Discourse**: Keyword frequency analysis.

### C. Social & Ecosystem Signals (High Priority)
- **Twitter (X) API v2**: Monitor mentions from influential Solana figures.
- **Discord/Telegram Scrapers**: Sentiment analysis on specific community channels.

## 3. Implementation Logic (The Agent's "Brain")
1. **Aggregator**: Pulls data from the above sources every 6 hours.
2. **Clustering Engine**: Uses an LLM to group disparate signals (e.g., "AI agent tokens up" + "3 new Rust AI repos" -> "AI Agent Summer").
3. **Idea Generator**: For each cluster, the agent prompts an LLM with: "Given [Narrative Context], what are 3 underserved product niches?"
4. **Dashboard/Output**: A clean JSON or Markdown report delivered to a Telegram/Discord bot.

## 4. Next Steps
- [ ] Implement a prototype Python script to fetch Birdeye "Trending" data.
- [ ] Connect a basic GitHub scraper for Solana topics.
- [ ] Design the LLM prompt for narrative clustering.
