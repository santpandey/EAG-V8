from mcp.server.fastmcp import FastMCP, Context
import httpx
from bs4 import BeautifulSoup
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
import urllib.parse
import sys
import traceback
import asyncio
from datetime import datetime, timedelta
import time
from fake_useragent import UserAgent
import re
import os
from googleapiclient.errors import HttpError
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from email.message import EmailMessage
from email.mime.text import MIMEText  # Import MIMEText
from email.mime.multipart import MIMEMultipart # Import MIMEMultipart
import base64
from google.auth.transport.requests import Request
import os.path
import logging

# Create a module-level logger
logger = logging.getLogger(__name__)

# Configure basic logging
logging.basicConfig(
    level=logging.INFO,
    format='[DUCKDUCKGO] %(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # Console output
        logging.FileHandler('duckduckgo_search.log', encoding='utf-8', mode='a')  # File logging
    ]
)

# Ensure the logger uses the configured logging level
logger.setLevel(logging.INFO)


@dataclass
class SearchResult:
    title: str
    link: str
    snippet: str
    current_point_standing: int


class RateLimiter:
    def __init__(self, requests_per_minute: int = 30):
        self.requests_per_minute = requests_per_minute
        self.requests = []

    async def acquire(self):
        now = datetime.now()
        # Remove requests older than 1 minute
        self.requests = [
            req for req in self.requests if now - req < timedelta(minutes=1)
        ]

        if len(self.requests) >= self.requests_per_minute:
            # Wait until we can make another request
            wait_time = 60 - (now - self.requests[0]).total_seconds()
            if wait_time > 0:
                await asyncio.sleep(wait_time)

        self.requests.append(now)


class DuckDuckGoSearcher:
    BASE_URL = "https://html.duckduckgo.com/html"
    ua = UserAgent()
    HEADERS = {
        #"Host": "html.duckduckgo.com",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Referer": "https://html.duckduckgo.com/",
        #"Content-Type": "application/x-www-form-urlencoded",
        #"Origin": "https://html.duckduckgo.com",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        #"Sec-Fetch-Dest": "document",
        #"Sec-Fetch-Mode": "navigate",
        #"Sec-Fetch-Site": "same-origin",
        #"Sec-Fetch-User": "?1",
        #"Priority": "u=0, i",
        #"TE": "trailers",
    }

    def __init__(self):
        self.rate_limiter = RateLimiter()

    def format_results_for_llm(self, results: List[SearchResult]) -> str:
        """Format results in a natural language style that's easier for LLMs to process"""
        if not results:
            #add results in the return string
            return "No results were found for your search query. This could be due to DuckDuckGo's bot detection or the query returned no matches. Please try rephrasing your search or try again in a few minutes."

        output = []
        output.append(f"Found {len(results)} search results:\n")

        for result in results:
            output.append(f"{result.current_point_standing}. {result.title}")
            output.append(f"   URL: {result.link}")
            output.append(f"   Summary: {result.snippet}")
            output.append("")  # Empty line between results

        return "\n".join(output)

    async def search(
        self, query: str, ctx: Context = None, max_results: int = 10
    ) -> List[SearchResult]:
        # Create list of SearchResult with static data
        # Extensive type and value checking with detailed tracing
        logger.debug(f"Search method called with: query={query}, type={type(query)}, ctx={ctx}, max_results={max_results}")
        if not isinstance(query, str):
            logger.warning(f"Non-string query detected. Attempting conversion. Original type: {type(query)}")
            query = str(query)
        # Attempt to convert query to string
        try:
            # If query is not a string, attempt conversion
            if not isinstance(query, str):
                logger.warning(f"Non-string query detected. Attempting conversion. Original type: {type(query)}")
                query = str(query)
        
        
            if not query or len(query.strip()) == 0:
                logger.error(f"Invalid search query: {query}")
                return []

            # Apply rate limiting
            await self.rate_limiter.acquire()

            # Create form data for POST request
            # Ensure query is a string before encoding
            if not isinstance(query, str):
                logger.error(f"Invalid query type before encoding. Got {type(query)}: {query}")
                return []
            
            data = {
                'q': query,
                'b': '',
                'kl': ''
            }

            logger.info(f"Searching with query: {query}")
            logger.info(f"POST request data: {data}")
            logger.info(f"POST request headers: {self.HEADERS}")
            #logger.info(f"POST request timeout: {30.0}")
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.BASE_URL, data=data, headers=self.HEADERS, timeout=30.0
                )
                response.raise_for_status()

            logger.info(f"HTTP Response: {response.text}")
            # Parse HTML response
            soup = BeautifulSoup(response.text, "html.parser")
            if not soup:
                logger.error("Failed to parse HTML response")
                return []

            results = []
            for result in soup.select(".result"):
                title_elem = result.select_one(".result__title")
                if not title_elem:
                    continue

                link_elem = title_elem.find("a")
                if not link_elem:
                    continue

                title = link_elem.get_text(strip=True)
                link = link_elem.get("href", "")

            # Skip ad results
                if "y.js" in link:
                    continue

            # Clean up DuckDuckGo redirect URLs
                if link.startswith("//duckduckgo.com/l/?uddg="):
                    link = urllib.parse.unquote(link.split("uddg=")[1].split("&")[0])

                snippet_elem = result.select_one(".result__snippet")
                snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""

                results.append(
                    SearchResult(
                        title=title,
                        link=link,
                        snippet=snippet,
                        current_point_standing=len(results) + 1,
                    )
                )

                if len(results) >= max_results:
                    break

            logger.info(f"Successfully found {len(results)} results")
            return results

        except httpx.TimeoutException:
            logger.error("Search request timed out")
            return []
        except httpx.HTTPError as e:
            logger.error(f"Search error: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error during search: {type(e)} {str(e)}")
            logger.error(f"Error details: type={type(e)}, query={query}, max_results={max_results}")
        traceback.print_exc(file=sys.stderr)
        return []


class WebContentFetcher:
    def __init__(self):
        self.rate_limiter = RateLimiter(requests_per_minute=20)

    async def fetch_and_parse(self, url: str, ctx: Context) -> str:
        """Fetch and parse content from a webpage"""
        try:
            await self.rate_limiter.acquire()

            await ctx.info(f"Fetching content from: {url}")

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                    },
                    follow_redirects=True,
                    timeout=30.0,
                )
                response.raise_for_status()

            # Parse the HTML
            soup = BeautifulSoup(response.text, "html.parser")

            # Remove script and style elements
            for element in soup(["script", "style", "nav", "header", "footer"]):
                element.decompose()

            # Get the text content
            text = soup.get_text()

            # Clean up the text
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = " ".join(chunk for chunk in chunks if chunk)

            # Remove extra whitespace
            text = re.sub(r"\s+", " ", text).strip()

            # Truncate if too long
            if len(text) > 8000:
                text = text[:8000] + "... [content truncated]"

            await ctx.info(
                f"Successfully fetched and parsed content ({len(text)} characters)"
            )
            return text

        except httpx.TimeoutException:
            await ctx.error(f"Request timed out for URL: {url}")
            return "Error: The request timed out while trying to fetch the webpage."
        except httpx.HTTPError as e:
            await ctx.error(f"HTTP error occurred while fetching {url}: {str(e)}")
            return f"Error: Could not access the webpage ({str(e)})"
        except Exception as e:
            await ctx.error(f"Error fetching content from {url}: {str(e)}")
            return f"Error: An unexpected error occurred while fetching the webpage ({str(e)})"


# Initialize FastMCP server
mcp = FastMCP("ddg-search")
searcher = DuckDuckGoSearcher()
fetcher = WebContentFetcher()


@mcp.tool()
async def search(query, ctx: Context, max_results: int = 10) -> str:
    """
    Search DuckDuckGo and return formatted results.

    Args:
        query: The search query string
        max_results: Maximum number of results to return (default: 10)
        ctx: MCP context for logging
    """
    # Robust type handling for query
    if query is None:
        logger.error("Search query is None")
        return "No search query provided"
    
    # Convert query to string
    try:
        query = str(query).strip()
    except Exception as conv_err:
        logger.error(f"Failed to convert query to string: {type(conv_err)} {conv_err}")
        return f"Invalid query type: {type(query)}"
    
    if not query:
        logger.error("Search query is empty")
        return "Empty search query"
    
    try:
        results = await searcher.search(query, ctx, max_results)
        return searcher.format_results_for_llm(results)
    except Exception as e:
        logger.error(f"Search error: {type(e)} {str(e)}")
        traceback.print_exc(file=sys.stderr)
        return f"An error occurred while searching: {str(e)}"


@mcp.tool()
async def fetch_content(url: str, ctx: Context) -> str:
    """
    Fetch and parse content from a webpage URL.

    Args:
        url: The webpage URL to fetch content from
        ctx: MCP context for logging
    """
    return await fetcher.fetch_and_parse(url, ctx)

@mcp.tool()
def send_email(text: str):
    """Creates spreadsheet in Google Drive and Sends Email to Gmail with the supplied text string"""
    scope = ["https://www.googleapis.com/auth/gmail.modify","https://www.googleapis.com/auth/spreadsheets"]
    creds = None
    #D:\EAG-V4\app
    path = os.path.join("D:","EAG-V4","app","gmail.json")
    path = r"D:\EAG-V4\app\gmail.json"
    token_path= r"D:\EAG-V4\app\token.json"
    print("path ", path)
    logger.info("text is ", text)
    try:
        if os.path.exists(token_path):
            creds = Credentials.from_authorized_user_file(token_path, scope)
        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    path, scope
                )
                creds = flow.run_local_server(port=0)
            # Save the credentials for the next run
            with open("token.json", "w") as token:
                token.write(creds.to_json())

        service = build("sheets", "v4", credentials=creds)
        spreadsheet = {"properties": {"title": "F1 Ranking Sheet for EAG"}}
        spreadsheet = (
            service.spreadsheets()
            .create(body=spreadsheet, fields="spreadsheetId")
            .execute()
        )
        print(f"Spreadsheet ID: {spreadsheet['spreadsheetId']}")
        spreadsheet_id = spreadsheet["spreadsheetId"]
        # Transform string to list of lists
        if isinstance(text, str):
            # Split the string by newline and remove any empty lines
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            values = [[line] for line in lines]
        elif isinstance(text, list):
            # If it's already a list, ensure it's a 2D list
            values = [line] if not isinstance(text[0], list) else text
        else:
            values = [[str(text)]]
        
        logger.info(f"Prepared values for Google Sheets: {values}")
        
        body = {
            "values": values
        }
        sheet_range='Sheet1'
        result = service.spreadsheets().values().update(spreadsheetId=spreadsheet_id,
                                                        range=sheet_range,
                                                        valueInputOption='RAW',
                                                        body=body).execute()
        print(f"Updated {result.get('updatedCells')} cells")
        # Construct the Google Sheets URL.
        spreadsheet_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}"
        sheet_body = f"Please find the F1 Ranking Sheet for EAG here: {spreadsheet_url}"
        service = build("gmail","v1", credentials=creds)
        
        # Create a multipart message
        message = MIMEMultipart()
        message["To"] = "eagsantosh@gmail.com"
        message["From"] = "eagsantosh@gmail.com"
        message["Subject"] = "F1 Ranking Sheet"
        
        # Attach the main content
        main_body = MIMEText(text, 'plain')
        message.attach(main_body)
        
        # Attach the spreadsheet link
        sheet_link = MIMEText(sheet_body, 'plain')
        message.attach(sheet_link)
        
        # Encode the message
        encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        create_message = {"raw": encoded_message}
        send_message = (
            service.users()
            .messages()
            .send(userId="me", body=create_message)
            .execute()
        )
        print(f'Message Id: {send_message["id"]}')
        
        
    except (HttpError, Exception) as e:
        print(f"Error sending email: {e}")
        send_message = e
    return send_message



if __name__ == "__main__":
    print("mcp_server_3.py starting")
    if len(sys.argv) > 1 and sys.argv[1] == "dev":
            mcp.run()  # Run without transport for dev server
    else:
        mcp.run(transport="stdio")  # Run with stdio for direct execution
        print("\nShutting down...")