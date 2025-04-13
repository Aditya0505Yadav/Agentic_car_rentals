import sys
import datetime
from crewai import Crew, Task, Agent
from browserbase import browserbase
from kayak import kayak_search
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
import os
import json
from mcp_integration import get_mcp_client, get_car_rentals, get_route_info, get_rental_tips

# Load environment variables
load_dotenv()

# Get API keys
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
BROWSERBASE_API_KEY = os.getenv("BROWSERBASE_API_KEY")

# Initialize the LLM
llm = None
try:
    if GEMINI_API_KEY:
        llm = ChatGoogleGenerativeAI(
            model="gemini-pro",
            google_api_key=GEMINI_API_KEY,
            temperature=0.7
        )
    else:
        from langchain.llms import Ollama
        llm = Ollama(model="llama2")
        print("Using Ollama as fallback LLM")
except Exception as e:
    print(f"Error initializing LLM: {str(e)}")
    print("Continuing without LLM")

# Define tools with better error handling
def enhanced_kayak_search(loc: str, pickup: str, dropoff: str, car_size: str = "Any") -> str:
    """
    Generate a Kayak URL for car rentals with enhanced parameters
    
    Args:
        loc: Location string in format "from-to-destination" or "city name"
        pickup: Pickup date in YYYY-MM-DD format
        dropoff: Return date in YYYY-MM-DD format
        car_size: Car size preference (Any, Economy, Compact, etc.)
    """
    try:
        # Parse location more intelligently
        if "-to-" not in loc.lower():
            # If it's just a city name, assume it's a city search
            clean_location = loc.lower().replace(' ', '-')
            URL = f"https://www.kayak.com/cars/{clean_location}/{pickup}/{dropoff}?sort=price_a"
        else:
            # If it has a "to", it's a route
            clean_location = loc.lower().replace(' ', '-')
            URL = f"https://www.kayak.com/cars/{clean_location}/{pickup}/{dropoff}?sort=price_a"
        
        # Add car size parameter if specified
        if car_size and car_size.lower() != "any":
            URL += f"&carsize={car_size.lower()}"
            
        return URL
    except Exception as e:
        print(f"Error generating Kayak URL: {str(e)}")
        # Fallback to basic URL
        return f"https://www.kayak.com/cars/{pickup}/{dropoff}"

def enhanced_browserbase(url: str):
    """
    Enhanced browsing tool with better error handling and MCP integration
    
    Args:
        url: The URL to load
    """
    if not BROWSERBASE_API_KEY:
        print("BROWSERBASE_API_KEY not set. Using MCP fallback.")
        
        # Extract search parameters from URL to use with MCP
        try:
            from_to = url.split('/cars/')[1].split('/')[0]
            dates = url.split(from_to)[1].split('?')[0]
            pickup_date = dates.split('/')[1]
            return_date = dates.split('/')[2]
            
            # Try to parse from-to locations
            if "-to-" in from_to:
                from_location = from_to.split('-to-')[0].replace('-', ' ')
                to_location = from_to.split('-to-')[1].replace('-', ' ')
            else:
                from_location = from_to.replace('-', ' ')
                to_location = from_location
                
            # Use MCP to get car rental data
            mcp_client = get_mcp_client()
            result = mcp_client.get_car_rentals("", from_location, to_location, 
                                                pickup_date, return_date)
            
            if result:
                return json.dumps({
                    "source": "mcp",
                    "data": result,
                    "route_info": mcp_client.get_route_info(from_location, to_location),
                    "tips": mcp_client.get_rental_tips(from_location, to_location)
                })
        except Exception as e:
            print(f"MCP fallback failed: {str(e)}")
            
        # Return dummy data if all else fails
        return json.dumps({
            "source": "fallback",
            "data": [
                {"company": "Enterprise", "price": "$40/day", "features": "Economy"},
                {"company": "Hertz", "price": "$45/day", "features": "Compact"},
                {"company": "Avis", "price": "$50/day", "features": "Standard"}
            ]
        })
        
    try:
        # Use regular browserbase with the API key
        return browserbase(url)
    except Exception as e:
        print(f"Browserbase error: {str(e)}")
        # Return dummy data as fallback
        return json.dumps({
            "source": "fallback",
            "error": str(e),
            "data": [
                {"company": "Enterprise", "price": "$40/day", "features": "Economy"},
                {"company": "Hertz", "price": "$45/day", "features": "Compact"},
                {"company": "Avis", "price": "$50/day", "features": "Standard"}
            ]
        })

# Define custom tools for additional functionality
def get_rental_recommendations(pickup_location, dropoff_location, dates, preferences=None):
    """
    Get rental recommendations based on location, dates and preferences
    
    Args:
        pickup_location: Location to pick up the rental car
        dropoff_location: Location to drop off the rental car
        dates: String of dates in format "YYYY-MM-DD to YYYY-MM-DD"
        preferences: Dictionary of preferences (car_size, budget, etc.)
    """
    try:
        # Parse dates
        if " to " in dates:
            pickup_date, return_date = dates.split(" to ")
        else:
            # Default to 3-day rental if dates format is incorrect
            pickup_date = datetime.date.today().strftime("%Y-%m-%d")
            return_date = (datetime.date.today() + datetime.timedelta(days=3)).strftime("%Y-%m-%d")
        
        # Parse preferences
        car_size = "Any"
        budget = None
        if preferences:
            if isinstance(preferences, str):
                try:
                    preferences = json.loads(preferences)
                except:
                    preferences = {}
            car_size = preferences.get("car_size", "Any")
            budget = preferences.get("budget")
            
        # Get car rentals via MCP
        mcp_client = get_mcp_client()
        car_options = mcp_client.get_car_rentals("", pickup_location, dropoff_location, 
                                               pickup_date, return_date)
        
        # Filter by budget if provided
        if budget and budget > 0:
            car_options = [opt for opt in car_options if opt.get("price_numeric", 9999) <= budget]
            
        # Get additional information
        route_info = mcp_client.get_route_info(pickup_location, dropoff_location)
        tips = mcp_client.get_rental_tips(pickup_location, dropoff_location)
        
        return json.dumps({
            "car_options": car_options,
            "route_info": route_info,
            "rental_tips": tips
        })
    except Exception as e:
        print(f"Error getting rental recommendations: {str(e)}")
        return json.dumps({
            "error": str(e),
            "car_options": [
                {"company": "Enterprise", "price": "$40/day", "features": "Economy"},
                {"company": "Hertz", "price": "$45/day", "features": "Compact"},
                {"company": "Avis", "price": "$50/day", "features": "Standard"}
            ]
        })

# Create agents with improved tools
cars_agent = Agent(
    role="Car Rentals Expert",
    goal="Search and analyze car rental options using multiple data sources",
    backstory="I am a car rental expert who uses both web data and proprietary databases to find the best rental options for clients.",
    tools=[enhanced_kayak_search, enhanced_browserbase, get_rental_recommendations],
    llm=llm,
    verbose=True,
    allow_delegation=True
)

summarize_agent = Agent(
    role="Summary Expert",
    goal="Provide clear, concise and personalized summaries of car rental options",
    backstory="I specialize in analyzing complex rental information and creating personalized recommendations based on customer preferences.",
    tools=[get_rental_recommendations],
    llm=llm,
    verbose=True,
    allow_delegation=False
)

route_agent = Agent(
    role="Route Planning Expert",
    goal="Provide detailed route information and travel tips for the rental journey",
    backstory="I specialize in route optimization, estimating travel times, and providing local insights for better journey planning.",
    tools=[get_route_info, get_rental_tips],
    llm=llm,
    verbose=True,
    allow_delegation=False
)

# Create tasks with better descriptions
search_task = Task(
    description="""
    Search car rentals according to criteria: {request}. Current year: {current_year}
    
    1. Parse the request to identify pickup location, dropoff location, and dates
    2. Use the enhanced_kayak_search tool to generate a search URL
    3. Use the enhanced_browserbase tool to fetch results from the URL
    4. Analyze the results to find the top 5 rental options based on price and value
    5. Include specific details for each option: company, car type, price, features, and any special offers
    
    If the browserbase tool fails, use the get_rental_recommendations tool as a backup
    to fetch rental options from our proprietary database.
    """,
    agent=cars_agent,
    expected_output="A detailed analysis of the top 5 car rental options with all relevant information"
)

route_analysis_task = Task(
    description="""
    Based on the car rental search information, provide a detailed route analysis:
    
    1. Calculate estimated distance and travel time between pickup and dropoff locations
    2. Identify major highways or routes that will be used
    3. Note any potential traffic issues or construction based on current data
    4. Suggest optimal times of day for travel
    5. Provide information about gas stations and rest stops along the route
    
    Use the get_route_info tool to obtain detailed route information.
    """,
    agent=route_agent,
    expected_output="A comprehensive route analysis with travel time, distance, major routes, and travel tips"
)

summarize_task = Task(
    description="""
    Create a clear, concise summary of the rental options and route information:
    
    1. Highlight the best overall value option
    2. Highlight the most luxury/premium option
    3. Highlight the most economical option
    4. Summarize the route information in a user-friendly way
    5. Provide 3-5 specific tips for this rental journey
    
    Your summary should be personalized to the specific journey from {pickup_location} to {dropoff_location}.
    
    Use the get_rental_tips tool to obtain specific tips for this journey.
    """,
    agent=summarize_agent,
    expected_output="A personalized summary of the best rental options with journey-specific tips"
)

# Create crew with improved configuration
crew = Crew(
    agents=[cars_agent, route_agent, summarize_agent],
    tasks=[search_task, route_analysis_task, summarize_task],
    verbose=True,
    process="sequential",  # Process tasks sequentially to ensure dependencies
    memory=True  # Enable memory to share information between tasks
)

def process_rental_request(request_text, current_year=None):
    """
    Process a car rental request and return comprehensive results
    
    Args:
        request_text: The rental request text (e.g., "car rental in Miami from June 1st to June 5th")
        current_year: Current year (defaults to current year if not provided)
    """
    if not current_year:
        current_year = datetime.date.today().year
        
    # Parse request to extract locations
    pickup_location = "Unknown"
    dropoff_location = "Unknown"
    
    # Simple parsing logic - for production this would be more sophisticated
    if "from" in request_text and "to" in request_text:
        parts = request_text.split("from")[1].split("to")
        if len(parts) >= 2:
            pickup_location = parts[0].strip()
            dropoff_location = parts[1].split()[0].strip()
    elif "in" in request_text:
        pickup_location = request_text.split("in")[1].split()[0].strip()
        dropoff_location = pickup_location
        
    try:
        result = crew.kickoff(
            inputs={
                "request": request_text,
                "current_year": current_year,
                "pickup_location": pickup_location,
                "dropoff_location": dropoff_location
            }
        )
        return result
    except Exception as e:
        error_message = f"An error occurred in the crew process: {str(e)}"
        print(error_message)
        return error_message

if __name__ == "__main__":
    try:
        request = "car rental in Miami from June 1st to June 5th"
        if len(sys.argv) > 1:
            request = sys.argv[1]
            
        result = process_rental_request(
            request,
            current_year=datetime.date.today().year,
        )
        print(result)
    except Exception as e:
        print(f"An error occurred: {str(e)}")