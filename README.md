# 🚗 Agentic Car Rentals

An intelligent multi-agent system for finding and analyzing car rental options using AI-powered search and recommendations.

## 🌟 Features

- Real-time car rental search and comparison
- Intelligent route optimization
- AI-driven recommendations
- Dynamic price analysis
- Location-specific travel insights

## 🛠️ Tech Stack

- **AI Framework**: CrewAI
- **Language Models**: 
  - Google Gemini Pro
  - Ollama (fallback)
- **Frontend**: Streamlit
- **Web Scraping**: Browserbase
- **Data Integration**: Kayak API

## 🤖 AI Agents

The system uses three specialized agents:

### 1. Cars Agent
- Searches and analyzes rental options
- Compares prices across providers
- Evaluates vehicle options

### 2. Route Agent
- Plans optimal travel routes
- Calculates journey times
- Provides local insights

### 3. Summary Agent
- Creates personalized recommendations
- Generates comprehensive summaries
- Analyzes best value options

## 🚀 Getting Started

1. Clone the repository
```bash
git clone https://github.com/yourusername/agentic-car-rentals
```

2. Install dependencies
```bash
pip install -r requirements.txt
```

3. Set up environment variables in `.env`:
```
BROWSERBASE_API_KEY=your_key
BROWSERBASE_PROJECT_ID= your_project_id
GEMINI_API_KEY=your_key
```

4. Run the application
```bash
streamlit run app.py
```

## 📝 Usage Example

```python
from main import process_rental_request

# Process a rental search
result = process_rental_request(
    "car rental in Miami from June 1st to June 5th"
)
```

## 📄 License

MIT License

## 🙏 Acknowledgments

- CrewAI for the multi-agent framework
- Browserbase for web automation
- Google for Gemini Pro API
