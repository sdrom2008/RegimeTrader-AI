# AI-Powered Regime Trading Engine: Project Documentation

## 1. Executive Summary

The AI-Powered Regime Trading Engine is a sophisticated, automated trading system designed to navigate the complexities of the cryptocurrency markets. Its core innovation is an AI model that accurately identifies the prevailing market regime (Trend or Range) and dynamically adjusts its strategy, ensuring that trend-following logic is only applied in suitable market conditions. This AI-driven approach, combined with bi-directional trading capabilities and a multi-layered risk management framework, creates a robust and intelligent trading solution.

The project successfully evolved from a concept to a fully functional, backtestable trading engine, achieving a 94.25% accuracy in its regime predictions during testing.

## 2. Core Features

*   **AI-Powered Regime Detection**: At its heart, the system uses a trained RandomForestClassifier model (`regime_model.pkl`) to predict whether the market is in a "Trend" or "Range" state with high accuracy.
*   **Dynamic Strategy Switching**: The engine only activates its trend-following entry logic when the AI confirms a "Trend" regime, effectively filtering out unprofitable trades during choppy, range-bound periods.
*   **Bi-Directional Trading**: The system is capable of executing both LONG and SHORT positions, allowing it to capitalize on both uptrends and downtrends.
*   **Multi-Layered Risk Management**:
    *   **Macro-Economic Filter**: Integrates real-time news sentiment analysis to veto trades that go against the broader market mood (e.g., blocks LONGs during negative news).
    *   **Smart Money Monitor**: Analyzes Binance's Long/Short ratio data to avoid trading against large, informed market participants.
    *   **Per-Trade Risk Control**: Employs an ATR-based trailing stop-loss and a fixed fractional position sizing model (5% of capital at risk per trade) for every position.
*   **Automated & Scalable**: The engine is built to run autonomously, scanning the top 40 USDT pairs on Binance to identify opportunities.

## 3. System Architecture & Data Flow

1.  **Data Ingestion**: The system fetches real-time 1-hour OHLCV data from Binance.
2.  **Macro Filters**: It first analyzes global news sentiment and smart money positioning to establish macro-level biases (e.g., `global_long_veto`).
3.  **Feature Engineering**: For each symbol, it calculates a suite of 16 technical indicators (features) identical to those used in model training.
4.  **AI Regime Prediction**: The latest set of features is fed into the loaded AI model (`regime_model.pkl`) to get a real-time prediction: `Trend` (1) or `Range` (0).
5.  **Decision Logic**:
    *   If `Range` is predicted, the system logs the result and takes no action.
    *   If `Trend` is predicted, the system proceeds to the next step.
6.  **Trade Execution Logic**: A secondary, rule-based analyzer (`MarketStateAnalyzer`) identifies the specific trend direction (Uptrend/Downtrend) to trigger a LONG or SHORT trade, subject to macro vetoes.
7.  **Portfolio Management**: The system manages open positions with trailing stop-losses and tracks overall PnL.

## 4. Key Components & Technologies

*   **Core Engine**: `paper_trader.py` - The main execution script that integrates all components.
*   **AI Model**: `regime_model.pkl` - The serialized, trained scikit-learn model file.
*   **Data Pipeline**:
    *   `fetch_historical_data.py`: Script to download historical data for training.
    *   `generate_features.py`: Script to perform feature engineering on the raw data.
    *   `train_regime_model.py`: Script to label data and train the AI model.
*   **Dependencies**: `requirements.txt` - Contains all necessary Python libraries.
*   **Technology Stack**:
    *   **Language**: Python 3.12
    *   **Libraries**: `pandas`, `ccxt`, `scikit-learn`, `pandas_ta`, `numpy`

## 5. The AI Brain: Model Details

*   **Algorithm**: `RandomForestClassifier` from scikit-learn.
*   **Training Data**: 2 years of BTC/USDT 1-hour data from Binance (~19,000 samples).
*   **Labeling Strategy**: A forward-looking approach where a "Trend" is defined as a future 24-hour price movement exceeding 3x the current ATR.
*   **Performance**:
    *   **Overall Accuracy**: **94.25%**
    *   **Trend Recall**: **99%** (Successfully identifies 99% of all actual trends).
    *   **Trend Precision**: **94%** (When it predicts a trend, it's correct 94% of the time).

## 6. Getting Started / Deployment

1.  **Setup Environment**: Create a Python virtual environment and install all dependencies using `pip install -r requirements.txt`.
2.  **Configuration**: Place necessary API keys (e.g., `GEMINI_API_KEY`) in a `.env` file if using LLM-based sentiment.
3.  **Run**: Execute the main engine with `python paper_trader.py`. The system will run one cycle of scanning and position management. For continuous operation, this script should be scheduled via a cron job or a similar task scheduler.
