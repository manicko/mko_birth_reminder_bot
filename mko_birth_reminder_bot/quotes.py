import aiohttp
from bs4 import BeautifulSoup
import logging
from functools import wraps
from mko_birth_reminder_bot.core import CONFIG

logger = logging.getLogger(__name__)

BANNED_AUTHORS = CONFIG.QUOTES.banned_authors

def filter_authors(banned_authors, max_attempts = 5):
    """decorator to filter banned authors"""
    def decorator(func):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            for _ in range(max_attempts):
                quote, author = await func(self, *args, **kwargs)
                if not quote:
                    continue
                is_banned = False
                for banned in banned_authors:
                    if banned in author:
                        is_banned = True
                        break
                if is_banned:
                    continue
                return " — ".join((quote, author))
            return None
        return wrapper
    return decorator

class QuoteFetcher:
    """A class for fetching random quotes from a website using an aiohttp session."""

    def __init__(self, session = None):
        """Initializes QuoteFetcher without an active session."""
        self.session = session

    async def __aenter__(self):
        """Creates an aiohttp session when entering the async context.

        Returns:
            QuoteFetcher: The instance itself with an open session.
        """
        await self.start_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Closes the aiohttp session when exiting the async context."""
        if self.session:
            await self.close_session()

    async def start_session(self):
        """Starts an aiohttp session if it's not already active."""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()

    async def close_session(self):
        """Closes the aiohttp session if it's open."""
        if self.session and not self.session.closed:
            await self.session.close()

    @filter_authors(banned_authors = BANNED_AUTHORS)
    async def get_random_quote(self):
        """Fetches a random quote from the website.

        Returns:
            str: A string containing the quote and the author, or None if an error occurs.
        """
        url = 'https://ru.citaty.net/tsitaty/sluchainaia-tsitata/'
        try:

            # async with self.session.get(url) as response: - not working with tests
                response = await self.session.get(url)
                if response.status != 200:
                    logger.error(f"HTTP Error {response.status}")
                    return None

                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')

                quote_text = soup.find("h1", attrs={"data-quote-content": True})
                quote_author = soup.find('div', class_='blockquote-origin').find('a')

                quote_text = quote_text.get_text(strip=True) if quote_text else ""
                quote_author = quote_author.get_text(strip=True) if quote_author else "Unknown author"

                if quote_text:
                    return quote_text, quote_author
        except Exception as e:
            logger.error(f"Error while fetching quote: {e}")
            return None

async def main():
    """Main function to test fetching multiple quotes."""
    async with QuoteFetcher() as fetcher:
        for _ in range(5):
            quote = await fetcher.get_random_quote()
            print(quote)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
