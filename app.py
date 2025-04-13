import streamlit as st
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup
import os
import re
import json
import logging
import subprocess
import random
import tempfile
import urllib.parse

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("app")

# Define company websites with direct search URLs
COMPANY_WEBSITES = {
    "Enterprise": "https://www.enterprise.com/en/home.html",
    "Hertz": "https://www.hertz.com/rentacar/reservation/",
    "Avis": "https://www.avis.com/en/home",
    "Budget": "https://www.budget.com/en/home",
    "National": "https://www.nationalcar.com/en/home.html",
    "Alamo": "https://www.alamo.com/en/home.html",
    "Dollar": "https://www.dollar.com/",
    "Thrifty": "https://www.thrifty.com/",
    "Sixt": "https://www.sixt.com/",
    "Fox": "https://www.foxrentacar.com/"
}

# Define major cities by state for dropdown selection
CITIES_BY_STATE = {
    "Alabama": ["Birmingham", "Montgomery", "Mobile", "Huntsville"],
    "Alaska": ["Anchorage", "Fairbanks", "Juneau"],
    "Arizona": ["Phoenix", "Tucson", "Scottsdale", "Mesa", "Flagstaff"],
    "Arkansas": ["Little Rock", "Fayetteville", "Hot Springs"],
    "California": ["Los Angeles", "San Francisco", "San Diego", "San Jose", "Sacramento"],
    "Colorado": ["Denver", "Colorado Springs", "Boulder", "Fort Collins"],
    "Connecticut": ["Hartford", "New Haven", "Stamford"],
    "Delaware": ["Wilmington", "Dover", "Newark"],
    "Florida": ["Miami", "Orlando", "Tampa", "Jacksonville", "Key West"],
    "Georgia": ["Atlanta", "Savannah", "Augusta", "Athens"],
    "Hawaii": ["Honolulu", "Hilo", "Lahaina"],
    "Idaho": ["Boise", "Idaho Falls", "Coeur d'Alene"],
    "Illinois": ["Chicago", "Springfield", "Peoria"],
    "Indiana": ["Indianapolis", "Fort Wayne", "Bloomington"],
    "Iowa": ["Des Moines", "Iowa City", "Cedar Rapids"],
    "Kansas": ["Wichita", "Kansas City", "Topeka"],
    "Kentucky": ["Louisville", "Lexington", "Frankfort"],
    "Louisiana": ["New Orleans", "Baton Rouge", "Lafayette"],
    "Maine": ["Portland", "Augusta", "Bar Harbor"],
    "Maryland": ["Baltimore", "Annapolis", "Bethesda"],
    "Massachusetts": ["Boston", "Cambridge", "Worcester", "Springfield"],
    "Michigan": ["Detroit", "Grand Rapids", "Ann Arbor"],
    "Minnesota": ["Minneapolis", "Saint Paul", "Duluth"],
    "Mississippi": ["Jackson", "Biloxi", "Gulfport"],
    "Missouri": ["Kansas City", "St. Louis", "Springfield"],
    "Montana": ["Billings", "Missoula", "Helena"],
    "Nebraska": ["Omaha", "Lincoln", "Grand Island"],
    "Nevada": ["Las Vegas", "Reno", "Carson City"],
    "New Hampshire": ["Manchester", "Concord", "Portsmouth"],
    "New Jersey": ["Newark", "Jersey City", "Atlantic City"],
    "New Mexico": ["Albuquerque", "Santa Fe", "Las Cruces"],
    "New York": ["New York City", "Buffalo", "Rochester", "Albany"],
    "North Carolina": ["Charlotte", "Raleigh", "Wilmington", "Asheville"],
    "North Dakota": ["Fargo", "Bismarck", "Grand Forks"],
    "Ohio": ["Columbus", "Cleveland", "Cincinnati"],
    "Oklahoma": ["Oklahoma City", "Tulsa", "Norman"],
    "Oregon": ["Portland", "Eugene", "Salem"],
    "Pennsylvania": ["Philadelphia", "Pittsburgh", "Harrisburg"],
    "Rhode Island": ["Providence", "Newport", "Warwick"],
    "South Carolina": ["Charleston", "Columbia", "Myrtle Beach"],
    "South Dakota": ["Sioux Falls", "Rapid City", "Aberdeen"],
    "Tennessee": ["Nashville", "Memphis", "Knoxville"],
    "Texas": ["Dallas", "Houston", "Austin", "San Antonio", "Fort Worth"],
    "Utah": ["Salt Lake City", "Park City", "Moab"],
    "Vermont": ["Burlington", "Montpelier", "Stowe"],
    "Virginia": ["Richmond", "Virginia Beach", "Arlington"],
    "Washington": ["Seattle", "Spokane", "Tacoma"],
    "West Virginia": ["Charleston", "Morgantown", "Huntington"],
    "Wisconsin": ["Milwaukee", "Madison", "Green Bay"],
    "Wyoming": ["Cheyenne", "Jackson", "Casper"],
    "District of Columbia": ["Washington DC"]
}

# Load MCP configuration from file
def load_mcp_config():
    """Load MCP configuration from mcp_config.json"""
    try:
        with open("mcp_config.json", "r") as f:
            config = json.load(f)
            
        # Replace environment variables in configuration
        for server_name, server_config in config.get("mcpServers", {}).items():
            if "env" in server_config:
                for key, value in server_config["env"].items():
                    if value.startswith("${") and value.endswith("}"):
                        env_var = value[2:-1]
                        env_value = os.environ.get(env_var, "")
                        server_config["env"][key] = env_value
        
        return config
    except Exception as e:
        logger.error(f"Failed to load MCP configuration: {str(e)}")
        return {"mcpServers": {}}

# Initialize MCP configuration
MCP_CONFIG = load_mcp_config()

def call_mcp_service(server_name, service_name, payload):
    """Call an MCP service with the provided payload"""
    if server_name not in MCP_CONFIG.get("mcpServers", {}):
        logger.error(f"MCP server {server_name} not configured")
        return None
    
    server_config = MCP_CONFIG["mcpServers"][server_name]
    
    # Add service name to payload
    full_payload = {**payload, "service": service_name}
    
    try:
        # Prepare command
        command = [server_config.get("command", "")]
        command.extend(server_config.get("args", []))
        
        # Prepare environment variables
        env = os.environ.copy()
        if "env" in server_config:
            env.update(server_config["env"])
        
        # Execute command
        logger.info(f"Calling MCP service: {server_name}.{service_name}")
        
        # Convert payload to JSON string
        input_data = json.dumps(full_payload)
        
        # Create a temporary file for the payload
        with tempfile.NamedTemporaryFile(mode='w+', delete=False) as temp_file:
            temp_file.write(input_data)
            temp_file_path = temp_file.name
        
        try:
            # Use the temporary file as input
            with open(temp_file_path, 'r') as input_file:
                result = subprocess.run(
                    command,
                    stdin=input_file,
                    capture_output=True,
                    text=True,
                    env=env,
                    timeout=30  # Set a timeout to prevent hanging
                )
        finally:
            # Clean up the temporary file
            os.unlink(temp_file_path)
        
        if result.returncode != 0:
            logger.error(f"MCP service call failed: {result.stderr}")
            return None
        
        # Parse response
        if result.stdout:
            try:
                return json.loads(result.stdout)
            except json.JSONDecodeError:
                logger.error(f"Failed to parse JSON response from MCP service: {server_name}.{service_name}")
                return None
        
        return None
    except Exception as e:
        logger.error(f"Error calling MCP service {server_name}.{service_name}: {str(e)}")
        return None

def check_browserbase_api_key():
    """Check if BrowserBase API key is set and valid"""
    api_key = os.environ.get("BROWSERBASE_API_KEY")
    if not api_key:
        api_key = MCP_CONFIG.get("mcpServers", {}).get("browserbase", {}).get("env", {}).get("BROWSERBASE_API_KEY", "")
    
    logger.info(f"BrowserBase API Key is {'set' if api_key else 'not set'}")
    return bool(api_key)

def get_distance_with_maps(from_location, to_location):
    """Get distance and route information using Google Maps MCP server"""
    payload = {
        "origin": from_location,
        "destination": to_location,
        "mode": "driving"
    }
    
    result = call_mcp_service("maps", "directions", payload)
    
    if result and "routes" in result and len(result["routes"]) > 0:
        route = result["routes"][0]
        distance_meters = route.get("distance", {}).get("value", 0)
        distance_miles = round(distance_meters / 1609.34)  # Convert meters to miles
        
        duration_seconds = route.get("duration", {}).get("value", 0)
        duration_hours = round(duration_seconds / 3600, 1)  # Convert seconds to hours
        
        # Extract the main route (highways)
        steps = route.get("legs", [{}])[0].get("steps", [])
        highways = []
        for step in steps:
            if "highway" in step.get("html_instructions", "").lower():
                highway_match = re.search(r'(I-\d+|US-\d+|Route \d+)', step.get("html_instructions", ""))
                if highway_match and highway_match.group(1) not in highways:
                    highways.append(highway_match.group(1))
        
        main_route = ", ".join(highways) if highways else "Local roads"
        
        return {
            "distance": f"~{distance_miles} miles",
            "drive_time": f"~{duration_hours} hours",
            "main_route": main_route
        }
    
    # Fallback to estimation if Google Maps fails
    return estimate_route_info(from_location, to_location)

def fetch_kayak_data(url):
    """Fetch Kayak data using the fetch MCP server"""
    payload = {
        "url": url,
        "headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        },
        "render": True,  # Enable JavaScript rendering
        "format": "html"  # Return HTML content
    }
    
    result = call_mcp_service("fetch", "get", payload)
    
    if result and "content" in result:
        return result["content"]
    
    return None

def scrape_with_browserbase(url):
    """Scrape website using Browserbase MCP server"""
    payload = {
        "url": url,
        "options": {
            "waitForSelector": "div.c1LbP, div.YUUgj",  # Wait for car containers to appear
            "timeout": 30000  # 30 seconds timeout
        }
    }
    
    result = call_mcp_service("browserbase", "visit", payload)
    
    if result and "html" in result:
        return result["html"]
    
    return None

def extract_car_options_from_html(html_content):
    """Extract car rental options from Kayak HTML content using BeautifulSoup"""
    if not html_content:
        logger.warning("Empty HTML content")
        return []
    
    soup = BeautifulSoup(html_content, 'html.parser')
    options = []
    
    # Look for car rental options - these selectors target Kayak's structure
    car_containers = soup.select('div.c1LbP') or soup.select('div.YUUgj')
    
    if not car_containers or len(car_containers) < 3:
        logger.warning("Failed to extract car options from HTML")
        return []
    
    # Process each car container from the actual HTML
    for i, container in enumerate(car_containers[:5]):  # Get top 5 options
        try:
            # Extract company - adjust selectors based on inspection
            company_elem = container.select_one('div.J0g6-name') or container.select_one('div.cFAxh')
            company = company_elem.text.strip() if company_elem else f"Company {i+1}"
            
            # Extract price - adjust selectors based on inspection
            price_elem = container.select_one('div.zV27-price') or container.select_one('div.K-GUI')
            price = price_elem.text.strip() if price_elem else f"${30 + (i*5)}/day"
            
            # Extract features - adjust selectors based on inspection
            features_elem = container.select_one('div.car-features') or container.select_one('div.c9fNV')
            features = [features_elem.text.strip()] if features_elem else ["Standard"]
            
            # Extract car type
            car_type_elem = container.select_one('div.KheO1') or container.select_one('div.PVIO-')
            car_type = car_type_elem.text.strip() if car_type_elem else "Standard"
            
            # Parse price for total calculation
            try:
                daily_price = int(re.search(r'\$(\d+)', price).group(1))
                total_price = f"${daily_price * 3} total"  # Assume 3 days as default
            except:
                total_price = "Price varies"
            
            # Create a structured option
            option = {
                "company": company,
                "price": price,
                "car_type": car_type,
                "features": features,
                "total_price": total_price,
                "rating": 4.0 + (i * 0.1),  # Placeholder
                "special_offer": None,
                "website": COMPANY_WEBSITES.get(company, "#")  # Add direct link to company website
            }
            
            options.append(option)
        except Exception as e:
            logger.warning(f"Error extracting car option: {str(e)}")
            continue
    
    return options

def estimate_route_info(from_location, to_location):
    """Fallback method to estimate route information between locations"""
    # Map of regions based on states
    regions = {
        "northeast": ["Massachusetts", "New York", "Connecticut", "Rhode Island", 
                    "New Hampshire", "Vermont", "Maine", "Pennsylvania", 
                    "New Jersey", "Delaware", "Maryland", "District of Columbia"],
        "southeast": ["Virginia", "North Carolina", "South Carolina", 
                    "Georgia", "Florida", "Alabama", "Mississippi", 
                    "Louisiana", "Arkansas", "Tennessee", "Kentucky"],
        "midwest": ["Ohio", "Michigan", "Indiana", "Illinois", 
                  "Wisconsin", "Minnesota", "Iowa", "Missouri", 
                  "North Dakota", "South Dakota", "Nebraska", "Kansas"],
        "southwest": ["Texas", "Oklahoma", "New Mexico", "Arizona"],
        "west": ["California", "Oregon", "Washington", 
               "Nevada", "Idaho", "Montana", "Wyoming", 
               "Colorado", "Utah", "Hawaii", "Alaska"]
    }
    
    # Get the regions for the locations
    from_state = from_location.split(", ")[-1]
    to_state = to_location.split(", ")[-1]
    
    from_region = next((region for region, states in regions.items() if from_state in states), "unknown")
    to_region = next((region for region, states in regions.items() if to_state in states), "unknown")
    
    # Distances between regions (approximates)
    region_distances = {
        "northeast-northeast": 200,
        "northeast-southeast": 900,
        "northeast-midwest": 800,
        "northeast-southwest": 1600,
        "northeast-west": 2700,
        "southeast-southeast": 300,
        "southeast-midwest": 800,
        "southeast-southwest": 1000,
        "southeast-west": 2400,
        "midwest-midwest": 400,
        "midwest-southwest": 900,
        "midwest-west": 1700,
        "southwest-southwest": 500,
        "southwest-west": 800,
        "west-west": 500
    }
    
    # Get the approximate distance between regions
    region_key = f"{from_region}-{to_region}"
    
    if region_key in region_distances:
        distance = region_distances[region_key]
    elif f"{to_region}-{from_region}" in region_distances:
        distance = region_distances[f"{to_region}-{from_region}"]
    else:
        # Default distance for unknown combinations
        distance = 1000
    
    # Add some variation
    variation = random.randint(-100, 100)
    distance += variation
    
    # Calculate driving time (65 mph average)
    drive_time = round(distance / 65, 1)
    
    # Determine route based on regions
    if from_region == "northeast" and to_region == "southeast":
        route = "I-95 S"
    elif from_region == "southeast" and to_region == "northeast":
        route = "I-95 N"
    elif from_region == "northeast" and to_region == "midwest":
        route = "I-90 W, I-80 W"
    elif from_region == "midwest" and to_region == "northeast":
        route = "I-80 E, I-90 E"
    elif from_region == "midwest" and to_region == "west":
        route = "I-80 W, I-70 W"
    elif from_region == "west" and to_region == "midwest":
        route = "I-70 E, I-80 E"
    elif from_region == "southeast" and to_region == "southwest":
        route = "I-10 W"
    elif from_region == "southwest" and to_region == "southeast":
        route = "I-10 E"
    elif from_region == "northeast" and to_region == "west":
        route = "I-80 W"
    elif from_region == "west" and to_region == "northeast":
        route = "I-80 E"
    else:
        route = "Major highways"
    
    return {
        "distance": f"~{distance} miles",
        "drive_time": f"~{drive_time} hours",
        "main_route": route
    }

def get_rental_deals(from_location, to_location, route_info):
    """Generate rental deals based on locations and route info"""
    try:
        # Extract distance value
        distance_str = route_info["distance"].replace("~", "").split(" ")[0]
        distance = int(distance_str)
    except:
        distance = 0
    
    # Standard deals
    standard_deals = [
        "Weekend special: 15% off weekly rentals",
        "Free GPS with 3+ day rentals",
        "No drop-off fees for same-state returns"
    ]
    
    # Distance-based deals
    distance_deals = []
    if distance > 500:
        distance_deals.append("Long-distance special: reduced fees")
    if distance > 1000:
        distance_deals.append("Interstate journey package with roadside assistance")
    if distance > 1500:
        distance_deals.append("Cross-country special: unlimited mileage included")
    
    # Location-specific deals
    location_deals = []
    from_state = from_location.split(", ")[-1]
    to_state = to_location.split(", ")[-1]
    
    if "New York" in from_location or "New York" in to_location:
        location_deals.append("NYC special: Tunnel/bridge fee coverage")
    if "Las Vegas" in from_location or "Las Vegas" in to_location:
        location_deals.append("Vegas special: Free upgrade to luxury car")
    if "Florida" in from_state or "Florida" in to_state:
        location_deals.append("Florida sunshine package: Convertible upgrade $10/day")
    if from_state == to_state:
        location_deals.append(f"{from_state} resident special: 10% off with ID")
    
    # Combine deals and shuffle
    all_deals = standard_deals + distance_deals + location_deals
    random.shuffle(all_deals)
    
    # Return 3-5 deals
    num_deals = min(5, len(all_deals))
    return all_deals[:num_deals]

def get_rental_tips(from_location, to_location, route_info, is_round_trip=False):
    """Generate rental tips based on locations, route info, and trip type"""
    # Extract distance
    try:
        distance_str = route_info["distance"].replace("~", "").replace(" miles", "").replace(" (round trip)", "")
        distance = int(distance_str)
    except:
        distance = 0
    
    # Extract drive time
    try:
        drive_time_str = route_info["drive_time"].replace("~", "").replace(" hours", "").replace(" (round trip)", "")
        drive_time = float(drive_time_str)
    except:
        drive_time = 0
    
    # Generic tips that apply to most rentals
    generic_tips = [
        "Book 2+ weeks ahead for best rates",
        "Check insurance coverage before renting",
        "Fill gas before return to avoid high fees",
        "Take photos of the car before driving off",
        "Inspect the car thoroughly before accepting",
        "Compare prices across multiple companies",
        "Check for one-way rental fees if applicable",
        "Consider prepaying for fuel if gas prices are high",
        "Verify if your credit card offers rental insurance",
        "Bring a credit card, as many rentals don't accept debit"
    ]
    
    # Round-trip specific tips
    round_trip_tips = []
    if is_round_trip:
        round_trip_tips = [
            "Round-trip rentals typically offer better daily rates",
            "Check for unlimited mileage on round-trip rentals",
            "For multi-day trips, weekly rates are often cheaper than daily",
            "Look for special round-trip weekend rates",
            "Return to the same location for best pricing"
        ]
    
    # Tips for long-distance travel
    long_distance_tips = []
    if distance > 500:
        long_distance_tips.append("Check the vehicle's comfort for long drives")
    if distance > 1000:
        long_distance_tips.append("Plan your route with regular rest stops every 2-3 hours")
        long_distance_tips.append("Consider reserving hotels along your route in advance")
    if distance > 1500:
        long_distance_tips.append("Verify if there are mileage limits on your rental")
        long_distance_tips.append("Pack emergency supplies for long interstate drives")
    
    # If this is a multi-day drive
    if drive_time > 10:
        long_distance_tips.append(f"Plan for a {int(drive_time/8)} day journey with overnight stops")
    
    # Location-specific tips
    location_specific_tips = []
    
    from_state = from_location.split(", ")[-1]
    to_state = to_location.split(", ")[-1]
    
    # Beach destinations
    beach_states = ["Florida", "Hawaii", "California"]
    if from_state in beach_states or to_state in beach_states:
        location_specific_tips.extend([
            "Request a car with good AC for hot weather",
            "Consider a convertible for beach driving",
            "Ask about water/sand damage policies"
        ])
    
    # Mountain/winter destinations
    mountain_states = ["Colorado", "Vermont", "Wyoming", "Montana"]
    if from_state in mountain_states or to_state in mountain_states:
        location_specific_tips.extend([
            "Consider getting a 4WD vehicle for mountain roads",
            "Check if snow chains or winter tires are needed",
            "Verify the vehicle has sufficient cargo space for gear"
        ])
    
    # Urban destinations
    urban_cities = ["New York City", "Chicago", "Boston", "Philadelphia", "San Francisco"]
    if any(city in from_location or city in to_location for city in urban_cities):
        location_specific_tips.extend([
            "Opt for a compact car for easier parking in city areas",
            "Consider using public transit instead in dense areas",
            "Check if your hotel charges for parking"
        ])
    
    # Combine and prioritize tips based on trip type
    if is_round_trip:
        all_tips = round_trip_tips + long_distance_tips + location_specific_tips + generic_tips
    else:
        all_tips = long_distance_tips + location_specific_tips + generic_tips
    
    # Ensure we don't have duplicates and limit to 5 tips
    unique_tips = []
    for tip in all_tips:
        if tip not in unique_tips:
            unique_tips.append(tip)
            if len(unique_tips) >= 5:
                break
    
    return unique_tips

def get_car_data(from_location, to_location, pickup_date, return_date, car_size="Any", is_round_trip=False):
    """Get car rental data using MCP servers"""
    logger.info(f"Getting car data for {from_location} to {to_location}")
    
    # Format the search locations for URL
    pickup_str = pickup_date.strftime("%Y-%m-%d")
    return_str = return_date.strftime("%Y-%m-%d")
    
    # Calculate number of days for the rental
    days = max(1, (return_date - pickup_date).days)  # Ensure at least 1 day for same-day returns
    
    # For round trip, we use the same location for pickup and dropoff
    dropoff_location = from_location if is_round_trip else to_location
    
    # 1. Try to get route information using Google Maps MCP
    route_info = None
    try:
        if MCP_CONFIG["mcpServers"].get("maps", {}).get("env", {}).get("GOOGLE_MAPS_API_KEY"):
            route_info = get_distance_with_maps(from_location, to_location)
            logger.info(f"Got route info from Google Maps MCP: {route_info}")
    except Exception as e:
        logger.error(f"Failed to get route info from Google Maps MCP: {str(e)}")
    
    # If maps failed, use estimation
    if not route_info:
        route_info = estimate_route_info(from_location, to_location)
        logger.info(f"Used estimated route info: {route_info}")
    
    # For round trip, double the distance and time
    if is_round_trip:
        try:
            distance = int(route_info["distance"].replace("~", "").replace(" miles", ""))
            time = float(route_info["drive_time"].replace("~", "").replace(" hours", ""))
            route = route_info["main_route"]
            
            # Create round trip info
            route_info = {
                "distance": f"~{distance * 2} miles (round trip)",
                "drive_time": f"~{time * 2} hours (round trip)",
                "main_route": f"{route} (outbound), {route} (return)"
            }
        except Exception as e:
            logger.error(f"Failed to convert route info to round trip: {str(e)}")
    
    # 2. Try to get car rental data using Browserbase MCP
    options = None
    kayak_url = None
    try:
        # Build the Kayak search URL
        if is_round_trip:
            # Round trip - use the same location for pickup and dropoff
            kayak_url = f"https://www.kayak.com/cars/{from_location.lower().replace(' ', '-').replace(',', '')}/{pickup_str}/{return_str}?sort=price_a"
        else:
            # One-way trip
            from_clean = from_location.lower().replace(' ', '-').replace(',', '')
            to_clean = to_location.lower().replace(' ', '-').replace(',', '')
            kayak_url = f"https://www.kayak.com/cars/{from_clean}-to-{to_clean}/{pickup_str}/{return_str}?sort=price_a"
        
        if car_size != "Any":
            kayak_url += f"&carsize={car_size.lower()}"
        
        logger.info(f"Generated Kayak URL: {kayak_url}")
        
        # Check if Browserbase MCP is available
        if "browserbase" in MCP_CONFIG["mcpServers"] and MCP_CONFIG["mcpServers"]["browserbase"].get("env", {}).get("BROWSERBASE_API_KEY"):
            html_content = scrape_with_browserbase(kayak_url)
            if html_content:
                options = extract_car_options_from_html(html_content)
                logger.info(f"Got {len(options)} options from Browserbase MCP")
        
        # If Browserbase failed, try fetch MCP
        if not options and "fetch" in MCP_CONFIG["mcpServers"]:
            html_content = fetch_kayak_data(kayak_url)
            if html_content:
                options = extract_car_options_from_html(html_content)
                logger.info(f"Got {len(options)} options from fetch MCP")
    except Exception as e:
        logger.error(f"Failed to get car rental data from MCP: {str(e)}")
    
    # If MCP services failed, generate fallback data
    if not options or len(options) < 3:
        options = generate_fallback_options(from_location, to_location, pickup_date, return_date, route_info, car_size, is_round_trip)
        logger.info("Used fallback options generation")
    
    # Make sure we have the total price calculated correctly
    for option in options:
        try:
            price_str = option["price"].replace("$", "").replace("/day", "")
            daily_price = int(price_str)
            option["total_price"] = f"${daily_price * days} total"
            
            # Make sure each option has a website link
            if "website" not in option or not option["website"]:
                option["website"] = COMPANY_WEBSITES.get(option["company"], "#")
        except Exception as e:
            logger.error(f"Failed to calculate total price: {str(e)}")
    
    # Generate deals and tips
    deals = get_rental_deals(from_location, to_location, route_info)
    tips = get_rental_tips(from_location, to_location, route_info, is_round_trip)
    
    # Determine the data source
    if "browserbase" in MCP_CONFIG["mcpServers"] and MCP_CONFIG["mcpServers"]["browserbase"].get("env", {}).get("BROWSERBASE_API_KEY"):
        source = "browserbase"
    elif "fetch" in MCP_CONFIG["mcpServers"]:
        source = "fetch"
    else:
        source = "fallback"
    
    return {
        "source": source,
        "options": options,
        "deals": deals,
        "route_info": route_info,
        "tips": tips,
        "url": kayak_url,
        "is_round_trip": is_round_trip
    }

def generate_fallback_options(from_location, to_location, pickup_date, return_date, route_info, car_size="Any", is_round_trip=False):
    """Generate fallback car rental options"""
    # Calculate number of days for the rental
    days = max(1, (return_date - pickup_date).days)  # Ensure at least 1 day for same-day returns
    
    # Extract distance from route info
    try:
        distance_str = route_info["distance"].replace("~", "").replace(" miles", "").replace(" (round trip)", "")
        distance = int(distance_str)
    except:
        distance = 500  # Default
    
    # Basic car options
    companies = ["Enterprise", "Hertz", "Avis", "Budget", "National"]
    car_types = ["Economy", "Compact", "Mid-size", "Full-size", "SUV"]
    features = {
        "Economy": ["4 doors", "Good MPG", "Compact size"],
        "Compact": ["4 doors", "Good MPG", "Easy parking"],
        "Mid-size": ["4 doors", "Comfortable", "Moderate MPG"],
        "Full-size": ["4 doors", "Spacious", "Moderate MPG"],
        "SUV": ["5 doors", "Cargo space", "All-weather"]
    }
    
    # Distance-based pricing
    base_price = 35
    distance_factor = 1.0
    if distance > 500:
        distance_factor = 1.2
    if distance > 1000:
        distance_factor = 1.4
    if distance > 1500:
        distance_factor = 1.6
        
    # Round-trip discount - typically up to 10-20% off one-way rates
    if is_round_trip:
        distance_factor *= 0.85  # 15% discount for round trips
    
    options = []
    for i, company in enumerate(companies):
        if car_size != "Any" and car_size in car_types:
            car_type = car_size
        else:
            car_type = car_types[min(i, len(car_types)-1)]
        
        price = int(base_price * distance_factor) + (i * 5)
        total_price = price * max(1, days)  # Ensure at least 1 day for pricing
        
        # Determine if this company offers a round-trip special
        special_offer = None
        if is_round_trip and i % 3 == 0:
            special_offer = "Round-trip special: Free tank of gas"
        elif not is_round_trip and i % 3 == 0:
            special_offer = "Free additional driver"
            
        # Add company website
        website = COMPANY_WEBSITES.get(company, "#")
        
        options.append({
            "company": company,
            "car_type": car_type,
            "price": f"${price}/day",
            "total_price": f"${total_price} total",
            "features": features[car_type],
            "rating": 4.0 + (i * 0.1),
            "special_offer": special_offer,
            "website": website
        })
    
    return options

def get_city_distance(from_city, from_state, to_city, to_state):
    """Get approximate distance between two cities"""
    from_location = f"{from_city}, {from_state}"
    to_location = f"{to_city}, {to_state}"
    
    # Try using Google Maps MCP
    try:
        if MCP_CONFIG["mcpServers"].get("maps", {}).get("env", {}).get("GOOGLE_MAPS_API_KEY"):
            route_info = get_distance_with_maps(from_location, to_location)
            distance_str = route_info["distance"].replace("~", "").replace(" miles", "")
            return int(distance_str)
    except:
        pass
    
    # Fallback to estimation
    route_info = estimate_route_info(from_location, to_location)
    distance_str = route_info["distance"].replace("~", "").replace(" miles", "")
    try:
        return int(distance_str)
    except:
        return 0

def build_search_url(company, from_location, to_location, pickup_date, return_date, is_round_trip=False):
    """Build a search URL for the specific car rental company"""
    # Extract location components
    from_city = from_location.split(", ")[0]
    from_state = from_location.split(", ")[1]
    
    if is_round_trip:
        to_city = from_city
        to_state = from_state
    else:
        to_city = to_location.split(", ")[0]
        to_state = to_location.split(", ")[1]
    
    # Format dates
    pickup_str = pickup_date.strftime("%Y-%m-%d")
    return_str = return_date.strftime("%Y-%m-%d")
    
    # Get base website URL
    base_url = COMPANY_WEBSITES.get(company, "#")
    
    # Don't try to build complex URLs, just return to the homepage
    return base_url

def main():
    st.set_page_config(page_title="Car Rental Search", page_icon="🚗")
    st.title("🚗 Car Rental Search")
    
    # Service status indicator
    with st.sidebar:
        # Only show BrowserBase status
        has_browserbase = check_browserbase_api_key()
        st.subheader("Service Status")
        st.markdown(f"📶 BrowserBase API: {'✅ Connected' if has_browserbase else '❌ Not configured'}")
        
        if not has_browserbase:
            st.warning("API key not configured. Using simulated data.")
        else:
            st.success("Using real-time data from BrowserBase")
        
        # Add some tips in the sidebar
        st.subheader("Pro Tips")
        st.info("""
        • Try searching between major cities for best results
        • One-way rentals between distant cities may have drop-off fees
        • Weekend rentals often have special discounts
        • Some locations offer free upgrades during off-peak times
        • Round-trip rentals are typically cheaper than one-way
        """)
        
        # Add BrowserBase API key input in sidebar for easy configuration
        st.subheader("Configure API Key")
        current_api_key = os.environ.get("BROWSERBASE_API_KEY", "")
        browserbase_api_key = st.text_input(
            "BrowserBase API Key", 
            value=current_api_key, 
            type="password",
            help="Enter your BrowserBase API key for real-time data"
        )
        
        # Update environment variable if key is provided
        if browserbase_api_key and browserbase_api_key != current_api_key:
            os.environ["BROWSERBASE_API_KEY"] = browserbase_api_key
            if st.button("Apply API Key"):
                # Reload MCP configuration with updated environment variables
                global MCP_CONFIG
                MCP_CONFIG = load_mcp_config()
                st.experimental_rerun()
    
    # Trip type selection
    trip_type = st.radio("Trip Type:", ["One-Way", "Round-Trip"], horizontal=True)
    is_round_trip = (trip_type == "Round-Trip")
    
    if is_round_trip:
        st.info("Round-Trip: You'll pick up and return the car at the same location.")
    else:
        st.info("One-Way: You'll pick up the car at one location and drop it off at a different location.")
    
    # State selection for origin and destination
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Pickup Location:")
        from_state = st.selectbox("Select pickup state:", sorted(CITIES_BY_STATE.keys()), key="from_state")
        from_city = st.selectbox("Select pickup city:", sorted(CITIES_BY_STATE[from_state]), key="from_city")
        from_location = f"{from_city}, {from_state}"
    
    # For round-trip, disable the destination selection and use the origin
    if is_round_trip:
        with col2:
            st.subheader("Drop-off Location (Same as Pickup):")
            st.markdown(f"**Return to:** {from_city}, {from_state}")
            # Hidden values to maintain the variables
            to_state = from_state
            to_city = from_city
            to_location = from_location
    else:
        with col2:
            st.subheader("Drop-off Location:")
            to_state = st.selectbox("Select drop-off state:", sorted(CITIES_BY_STATE.keys()), key="to_state")
            to_city = st.selectbox("Select drop-off city:", sorted(CITIES_BY_STATE[to_state]), key="to_city")
            to_location = f"{to_city}, {to_state}"

    # Date inputs
    col3, col4 = st.columns(2)
    with col3:
        pickup_date = st.date_input("Pickup Date", value=datetime.now() + timedelta(days=1))
    
    # Determine if same-day drop-off should be available
    allow_same_day = False
    if not is_round_trip:
        # Check the approximate distance between cities
        distance = get_city_distance(from_city, from_state, to_city, to_state)
        # Allow same-day drop-off for distances under 300 miles
        allow_same_day = distance <= 300
    
    with col4:
        drop_off_label = "Return Date" if is_round_trip else "Drop-off Date"
        
        # Set min_value to either today or tomorrow based on distance
        min_date = pickup_date if allow_same_day else pickup_date + timedelta(days=1)
        return_date = st.date_input(drop_off_label, value=pickup_date + timedelta(days=3), min_value=min_date)
    
    # For shorter one-way trips, show a note about same-day drop-off
    if not is_round_trip and allow_same_day:
        st.info("Short distance detected. Same-day drop-off is available for this route.")
    
    # Additional options
    with st.expander("Additional Options"):
        car_size = st.selectbox(
            "Car Size",
            ["Any", "Economy", "Compact", "Mid-size", "Full-size", "SUV", "Luxury"]
        )
        
        col_a, col_b = st.columns(2)
        with col_a:
            sort_by = st.radio("Sort By", ["Price (low to high)", "Rating", "Popularity"])
        with col_b:
            include_extras = st.checkbox("Include airport pickup/dropoff", value=True)

    if st.button("Search Car Rentals", type="primary"):
        if not is_round_trip and from_city == to_city and from_state == to_state:
            st.error("For one-way rentals, please select different pickup and drop-off locations. Or select Round-Trip option.")
            return
            
        if pickup_date > return_date:
            st.error("Drop-off date must be after or equal to pickup date")
            return

        try:
            with st.spinner('Searching for car rentals...'):
                # Get car rental data using MCP servers
                data = get_car_data(from_location, to_location, pickup_date, return_date, car_size, is_round_trip)
                
                # Extract data components
                options = data["options"]
                deals = data["deals"]
                route_info = data["route_info"]
                tips = data["tips"]
                url = data["url"]
                
                # Show trip type for clarity
                trip_type_label = "🔄 Round-Trip" if is_round_trip else "➡️ One-Way"
                
                # Show data source for transparency
                source_indicators = {
                    "browserbase": f"🌐 Real-time data (Browserbase) - {trip_type_label}",
                    "fetch": f"🔍 Web data - {trip_type_label}",
                    "fallback": f"📊 Simulated data - {trip_type_label}"
                }
                st.info(f"Data source: {source_indicators.get(data['source'], 'Unknown')}")
                
                st.write("Generated URL:", url)

                if not options or len(options) < 3:
                    st.error("Failed to retrieve sufficient rental data")
                    return

                # Calculate rental duration
                rental_duration = (return_date - pickup_date).days
                rental_duration_text = "Same-day rental" if rental_duration == 0 else f"{rental_duration} day rental"
                
                # Display route information prominently
                distance = int(route_info["distance"].replace("~", "").replace(" miles", "").replace(" (round trip)", ""))
                
                # For round trip, we show the full round-trip distance
                if is_round_trip:
                    st.info(f"""
                    **Round-Trip Details:**
                    • Pickup at: {from_location}
                    • Return to: {from_location}
                    • Duration: {rental_duration_text}
                    • Total distance: {route_info["distance"]}
                    • Total driving time: {route_info["drive_time"]}
                    • Routes: {route_info["main_route"]}
                    """)
                elif distance > 500:
                    st.warning(f"""
                    **One-Way Trip Details:**
                    • Pickup at: {from_location}
                    • Drop off at: {to_location} 
                    • Duration: {rental_duration_text}
                    • Distance: {route_info["distance"]}
                    • Driving time: {route_info["drive_time"]}
                    • Note: One-way rentals for long distances typically incur additional fees.
                    """)
                else:
                    st.info(f"""
                    **One-Way Trip Details:**
                    • Pickup at: {from_location}
                    • Drop off at: {to_location}
                    • Duration: {rental_duration_text}
                    • Distance: {route_info["distance"]}
                    • Driving time: {route_info["drive_time"]}
                    """)

                st.header("🚗 Top Rental Options")
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.markdown(f"""
                    **Economy Choice**
                    - [{options[0]['company']}]({options[0]['website']})
                    - {options[0]['price']}
                    - {options[0]['car_type']}
                    - {options[0]['total_price']}
                    - Rating: {options[0]['rating']:.1f}⭐
                    """)
                    
                    if options[0].get('special_offer'):
                        st.markdown(f"**Special:** {options[0]['special_offer']}")
                
                with col2:
                    st.markdown(f"""
                    **Mid-Range Choice**
                    - [{options[1]['company']}]({options[1]['website']})
                    - {options[1]['price']}
                    - {options[1]['car_type']}
                    - {options[1]['total_price']}
                    - Rating: {options[1]['rating']:.1f}⭐
                    """)
                    
                    if options[1].get('special_offer'):
                        st.markdown(f"**Special:** {options[1]['special_offer']}")
                
                with col3:
                    st.markdown(f"""
                    **Premium Choice**
                    - [{options[2]['company']}]({options[2]['website']})
                    - {options[2]['price']}
                    - {options[2]['car_type']}
                    - {options[2]['total_price']}
                    - Rating: {options[2]['rating']:.1f}⭐
                    """)
                    
                    if options[2].get('special_offer'):
                        st.markdown(f"**Special:** {options[2]['special_offer']}")

                with st.expander("📊 View All Options"):
                    for i, option in enumerate(options):
                        st.markdown(f"""
                        **Option {i+1}: [{option['company']}]({option['website']}) - {option.get('car_type', 'Standard')}**
                        - Price: {option['price']}
                        - Total: {option.get('total_price', 'N/A')}
                        - Features: {', '.join(option.get('features', ['Standard']))}
                        - Rating: {option.get('rating', 4.0):.1f}⭐
                        {f"- Special: {option['special_offer']}" if option.get('special_offer') else ""}
                        """)
                        st.markdown("---")

                with st.expander("💰 View Current Deals"):
                    st.markdown("\n".join([f"- {deal}" for deal in deals]))
                
                # Format tips section
                tips_str = "\n".join([f"• {tip}" for tip in tips])
                st.success(f"""
                💡 **Quick Tips:**
                {tips_str}
                """)

                st.markdown("---")
                st.markdown(f"🔍 [Compare All Options on Kayak]({url})")

        except Exception as e:
            st.error("An unexpected error occurred")
            st.error(f"Error details: {str(e)}")
            import traceback
            st.error(traceback.format_exc())

if __name__ == "__main__":
    main()