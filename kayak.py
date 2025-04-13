import re
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("kayak")

def kayak_search(from_location: str, to_location: str, pickup: str, dropoff: str) -> str:
    """
    Generates a Kayak URL for car rentals between two locations and dates.
    
    Args:
        from_location: Origin location (city, state)
        to_location: Destination location (city, state)
        pickup: Pickup date in YYYY-MM-DD format
        dropoff: Return date in YYYY-MM-DD format
    
    Returns:
        A properly formatted Kayak search URL
    """
    logger.info(f"Generating Kayak URL for: {from_location} to {to_location}, {pickup} to {dropoff}")
    
    # Clean and standardize the location strings
    from_clean = sanitize_location(from_location)
    to_clean = sanitize_location(to_location)
    location = f"{from_clean}-to-{to_clean}"
    
    # Check if dates are valid
    if not is_valid_date_format(pickup) or not is_valid_date_format(dropoff):
        logger.warning("Invalid date format. Using current dates.")
        # Default to a simple URL if dates are invalid
        URL = f"https://www.kayak.com/cars/{location}"
    else:
        # Build the URL with dates
        URL = f"https://www.kayak.com/cars/{location}/{pickup}/{dropoff}?sort=price_a"
    
    logger.info(f"Generated URL: {URL}")
    return URL

def sanitize_location(loc: str) -> str:
    """
    Sanitize and format location string for Kayak URL.
    
    Args:
        loc: Location string that could be in various formats
    
    Returns:
        Properly formatted location string for Kayak URL
    """
    # Remove special characters except for spaces, letters, numbers, and hyphens
    cleaned = re.sub(r'[^\w\s-]', '', loc)
    
    # Convert to lowercase and replace spaces with hyphens
    cleaned = cleaned.lower().replace(' ', '-').replace(',', '')
    
    # Remove any trailing or leading hyphens
    cleaned = cleaned.strip('-')
    
    # Ensure the string is not empty
    if not cleaned:
        cleaned = "united-states"
    
    return cleaned

def is_valid_date_format(date_str: str) -> bool:
    """
    Check if the date string is in YYYY-MM-DD format.
    
    Args:
        date_str: Date string to validate
    
    Returns:
        True if the format is valid, False otherwise
    """
    pattern = r'^\d{4}-\d{2}-\d{2}$'
    return bool(re.match(pattern, date_str))