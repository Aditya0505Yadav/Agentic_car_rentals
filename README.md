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
cd agentic-car-rentals
```

2. Set up Python virtual environment

For Windows:
```bash
python -m venv venv
.\venv\Scripts\activate
```

For macOS/Linux:
```bash
python3 -m venv venv
source venv/bin/activate
```

3. Install dependencies
```bash
pip install -r requirements.txt
```

4. Set up environment variables in `.env`:
```
BROWSERBASE_API_KEY=your_key
GEMINI_API_KEY=your_key
```

5. Run the application
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

## 💻 Development Setup

### Prerequisites
- Python 3.8 or higher
- pip (Python package installer)
- virtualenv or venv

### Virtual Environment Management

Activate the virtual environment:

Windows:
```bash
.\venv\Scripts\activate
```

macOS/Linux:
```bash
source venv/bin/activate
```

Deactivate when done:
```bash
deactivate
```

### Installing New Dependencies
```bash
pip install package_name
pip freeze > requirements.txt
```


## 🙏 Acknowledgments

- CrewAI for the multi-agent framework
- Browserbase for web automation
- Google for Gemini Pro API
