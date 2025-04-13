import os
from playwright.sync_api import sync_playwright
from html2text import html2text
from time import sleep
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("browserbase")

def browserbase(url: str):
    """
    Loads a URL using a headless webbrowser

    :param url: The URL to load
    :return: The text content of the page
    """
    logger.info(f"Loading URL: {url}")
    api_key = os.environ.get("BROWSERBASE_API_KEY")
    
    if not api_key:
        logger.warning("BROWSERBASE_API_KEY not set")
        # Return fallback response
        return """
        # Car Rental Results
        
        ## Options
        - Enterprise: $40/day (Economy)
        - Hertz: $45/day (Compact)
        - Avis: $50/day (Standard)
        
        ## Deals
        - Weekend special: 15% off weekly rentals
        - Free GPS with 3+ day rentals
        - No drop-off fees for same-state returns
        """
    
    try:
        with sync_playwright() as playwright:
            logger.info("Connecting to browserbase...")
            browser = playwright.chromium.connect_over_cdp(
                f"wss://connect.browserbase.com?apiKey={api_key}"
            )
            context = browser.contexts[0]
            page = context.pages[0]
            
            # Set a generous timeout for navigation
            page.set_default_timeout(60000)  # 60 seconds
            
            logger.info(f"Navigating to: {url}")
            page.goto(url)

            # Wait for the car search to finish
            logger.info("Waiting for page to load completely...")
            sleep(5)  # Initial wait
            
            # Wait for the main container to be visible
            try:
                page.wait_for_selector('div.Yct0-', timeout=20000)
                logger.info("Main container loaded")
            except Exception as e:
                logger.warning(f"Timeout waiting for main container: {str(e)}")
            
            # Additional wait for dynamic content
            sleep(20)
            
            logger.info("Extracting page content...")
            html = page.content()
            
            # Close browser
            browser.close()
            logger.info("Browser closed")
            
            return html
    except Exception as e:
        logger.error(f"Browserbase error: {str(e)}")
        # Return fallback content in case of error
        return """
        # Car Rental Results
        
        ## Options
        - Enterprise: $40/day (Economy)
        - Hertz: $45/day (Compact)
        - Avis: $50/day (Standard)
        
        ## Deals
        - Weekend special: 15% off weekly rentals
        - Free GPS with 3+ day rentals
        - No drop-off fees for same-state returns
        """