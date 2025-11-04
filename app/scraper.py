"""
Scraper module using Playwright for JS-rendered quiz pages.
"""
import asyncio
import logging
import re
from typing import Dict, Any, Optional, List
from playwright.async_api import async_playwright, Page, Browser
from urllib.parse import urljoin, urlparse

from app.config import PLAYWRIGHT_TIMEOUT
from app.utils import find_file_links, extract_json_from_text, find_base64_strings, try_decode_base64

logger = logging.getLogger(__name__)


class QuizScraper:
    """Handles scraping of JS-rendered quiz pages using Playwright."""
    
    def __init__(self, timeout: int = PLAYWRIGHT_TIMEOUT):
        self.timeout = timeout
        self.browser: Optional[Browser] = None
        self.playwright = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=True)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
    
    async def scrape_quiz_page(self, url: str) -> Dict[str, Any]:
        """
        Scrape a quiz page and extract relevant information.
        
        Args:
            url: URL of the quiz page
            
        Returns:
            Dictionary containing:
            - html_content: Full HTML content
            - text_content: Visible text content
            - file_links: List of downloadable file links
            - submission_url: URL for submitting answers (if found)
            - question: Question text (if found)
            - instructions: Instructions text (if found)
            - base64_data: Any decoded base64 data found
            - json_data: Any JSON data found
        """
        if not self.browser:
            raise RuntimeError("Browser not initialized. Use async context manager.")
        
        page = await self.browser.new_page()
        result = {
            "html_content": "",
            "text_content": "",
            "file_links": [],
            "submission_url": None,
            "question": None,
            "instructions": None,
            "base64_data": None,
            "json_data": None,
            "url": url
        }
        
        try:
            logger.info(f"Loading page: {url}")
            await page.goto(url, wait_until="networkidle", timeout=self.timeout)
            
            # Wait a bit for any dynamic content
            await asyncio.sleep(2)
            
            # Get HTML content
            result["html_content"] = await page.content()
            
            # Get visible text content
            try:
                result["text_content"] = await page.inner_text("body")
            except Exception as e:
                logger.warning(f"Could not extract text content: {e}")
                result["text_content"] = result["html_content"]
            
            # Find file links
            result["file_links"] = find_file_links(result["html_content"], url)
            logger.info(f"Found {len(result['file_links'])} file links")
            
            # Look for submission URL in various places
            result["submission_url"] = await self._find_submission_url(page, result["html_content"], url)
            
            # Extract question and instructions
            result["question"] = await self._extract_question(page, result["text_content"])
            result["instructions"] = await self._extract_instructions(page, result["text_content"])
            
            # Look for base64 encoded data
            base64_strings = find_base64_strings(result["text_content"])
            for b64 in base64_strings:
                decoded = try_decode_base64(b64)
                if decoded:
                    result["base64_data"] = decoded
                    # Check if decoded data contains JSON
                    json_data = extract_json_from_text(decoded)
                    if json_data:
                        result["json_data"] = json_data
                    break
            
            # Look for JSON in page (data attributes, script tags, etc.)
            if not result["json_data"]:
                json_data = extract_json_from_text(result["html_content"])
                if json_data:
                    result["json_data"] = json_data
            
            logger.info(f"Scraped page successfully. Found question: {result['question'] is not None}")
            
        except Exception as e:
            logger.error(f"Error scraping page {url}: {e}")
            raise
        finally:
            await page.close()
        
        return result
    
    async def _find_submission_url(self, page: Page, html_content: str, base_url: str) -> Optional[str]:
        """Find the submission URL from the page."""
        # Look for common submission URL patterns
        patterns = [
            r'submit[_-]?url["\']?\s*[:=]\s*["\']([^"\']+)["\']',
            r'action=["\']([^"\']*(?:submit|answer|post)[^"\']*)["\']',
            r'api[_-]?url["\']?\s*[:=]\s*["\']([^"\']+)["\']',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, html_content, flags=re.IGNORECASE)
            for match in matches:
                if match.startswith(("http://", "https://")):
                    return match
                else:
                    return urljoin(base_url, match)
        
        # Check for form action
        try:
            form_action = await page.get_attribute("form", "action")
            if form_action:
                return urljoin(base_url, form_action)
        except Exception:
            pass
        
        # Check data attributes
        try:
            submit_elem = await page.query_selector("[data-submit-url], [data-submission-url]")
            if submit_elem:
                url = await submit_elem.get_attribute("data-submit-url") or \
                      await submit_elem.get_attribute("data-submission-url")
                if url:
                    return urljoin(base_url, url)
        except Exception:
            pass
        
        return None
    
    async def _extract_question(self, page: Page, text_content: str) -> Optional[str]:
        """Extract question text from the page."""
        # Look for common question patterns
        question_patterns = [
            r'(?:question|task|problem|what|calculate|find)[:.\s]+(.{20,500})',
            r'<h[1-3][^>]*>(.*?)</h[1-3]>',
        ]
        
        for pattern in question_patterns:
            matches = re.findall(pattern, text_content, flags=re.IGNORECASE | re.DOTALL)
            if matches:
                # Clean HTML tags from the first match
                question = re.sub(r'<[^>]+>', '', matches[0]).strip()
                if len(question) > 10:  # Valid question should be meaningful
                    return question[:1000]  # Limit length
        
        # Try to find question in specific elements
        try:
            question_elem = await page.query_selector("h1, h2, .question, #question, [class*='question']")
            if question_elem:
                question_text = await question_elem.inner_text()
                if question_text and len(question_text) > 10:
                    return question_text[:1000]
        except Exception:
            pass
        
        return None
    
    async def _extract_instructions(self, page: Page, text_content: str) -> Optional[str]:
        """Extract instructions text from the page."""
        # Look for instruction patterns
        instruction_patterns = [
            r'(?:instruction|note|hint|guideline)[s]?[:.\s]+(.{20,500})',
            r'<p[^>]*class="[^"]*instruction[^"]*"[^>]*>(.*?)</p>',
        ]
        
        for pattern in instruction_patterns:
            matches = re.findall(pattern, text_content, flags=re.IGNORECASE | re.DOTALL)
            if matches:
                instructions = re.sub(r'<[^>]+>', '', matches[0]).strip()
                if len(instructions) > 10:
                    return instructions[:1000]
        
        return None

