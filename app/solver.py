"""
Quiz solving logic: processes quiz data, computes answers, and submits them.
"""
import asyncio
import logging
import time
import re
import os
from typing import Dict, Any, Optional
import httpx

from app.config import (
    QUIZ_TIMEOUT, REQUEST_TIMEOUT, MAX_RETRIES, RETRY_DELAY,
    SECRET, EMAIL
)
from app.scraper import QuizScraper
from app.utils import (
    download_file, analyze_data_file, create_temp_file,
    extract_text_from_pdf, parse_csv_and_sum, sum_values_in_text,
    extract_json_from_text, try_decode_base64, find_base64_strings
)

logger = logging.getLogger(__name__)


class QuizSolver:
    """Main solver class that orchestrates quiz solving."""
    
    def __init__(self, email: str, secret: str):
        self.email = email
        self.secret = secret
        self.start_time = None
    
    async def solve_quiz_chain(self, initial_url: str) -> Dict[str, Any]:
        """
        Solve a quiz chain, automatically progressing to next quiz if available.
        
        Args:
            initial_url: Starting quiz URL
            
        Returns:
            Dictionary with results from all quizzes solved
        """
        self.start_time = time.time()
        results = {
            "quizzes_solved": [],
            "total_quizzes": 0,
            "success": False,
            "final_message": None,
            "errors": []
        }
        
        current_url = initial_url
        quiz_number = 1
        
        async with QuizScraper() as scraper:
            while current_url and (time.time() - self.start_time) < QUIZ_TIMEOUT:
                try:
                    logger.info(f"Solving quiz #{quiz_number}: {current_url}")
                    
                    # Scrape the quiz page
                    page_data = await scraper.scrape_quiz_page(current_url)
                    
                    # Solve the quiz
                    answer = await self._compute_answer(page_data)
                    
                    if answer is None:
                        error_msg = "Could not compute answer"
                        logger.error(error_msg)
                        results["errors"].append({"quiz": quiz_number, "error": error_msg})
                        break
                    
                    # Submit the answer
                    submission_result = await self._submit_answer(
                        page_data.get("submission_url") or current_url,
                        current_url,
                        answer
                    )
                    
                    quiz_result = {
                        "quiz_number": quiz_number,
                        "url": current_url,
                        "answer": answer,
                        "submission_result": submission_result
                    }
                    
                    results["quizzes_solved"].append(quiz_result)
                    results["total_quizzes"] = quiz_number
                    
                    # Check if there's a next quiz
                    if isinstance(submission_result, dict):
                        if submission_result.get("correct") is True:
                            next_url = submission_result.get("url")
                            if next_url and next_url != current_url:
                                logger.info(f"Moving to next quiz: {next_url}")
                                current_url = next_url
                                quiz_number += 1
                                continue
                            else:
                                results["success"] = True
                                results["final_message"] = "All quizzes completed successfully"
                                break
                        else:
                            # Wrong answer, try again with retry logic
                            if quiz_result.get("retry_count", 0) < MAX_RETRIES:
                                logger.warning(f"Wrong answer, retrying... (attempt {quiz_result.get('retry_count', 0) + 1})")
                                await asyncio.sleep(RETRY_DELAY)
                                quiz_result["retry_count"] = quiz_result.get("retry_count", 0) + 1
                                # Re-compute answer with different strategy
                                answer = await self._compute_answer(page_data, retry=True)
                                if answer:
                                    submission_result = await self._submit_answer(
                                        page_data.get("submission_url") or current_url,
                                        current_url,
                                        answer
                                    )
                                    quiz_result["answer"] = answer
                                    quiz_result["submission_result"] = submission_result
                                    continue
                            else:
                                results["errors"].append({
                                    "quiz": quiz_number,
                                    "error": "Max retries reached, wrong answer"
                                })
                                break
                    else:
                        # Submission failed or returned unexpected format
                        break
                
                except Exception as e:
                    error_msg = f"Error solving quiz #{quiz_number}: {str(e)}"
                    logger.error(error_msg)
                    results["errors"].append({"quiz": quiz_number, "error": error_msg})
                    break
        
        if (time.time() - self.start_time) >= QUIZ_TIMEOUT:
            results["final_message"] = "Timeout reached (3 minutes)"
        
        return results
    
    async def _compute_answer(self, page_data: Dict[str, Any], retry: bool = False) -> Optional[Any]:
        """
        Compute the answer to the quiz based on page data.
        
        Args:
            page_data: Scraped page data from QuizScraper
            retry: Whether this is a retry attempt (use different strategy)
            
        Returns:
            Computed answer (number, string, dict, etc.)
        """
        logger.info("Computing answer...")
        
        # Strategy 1: Check if answer is directly in JSON data
        if page_data.get("json_data"):
            json_data = page_data["json_data"]
            if "answer" in json_data:
                logger.info("Answer found in JSON data")
                return json_data["answer"]
            if "solution" in json_data:
                return json_data["solution"]
        
        # Strategy 2: Check base64 decoded data
        if page_data.get("base64_data"):
            decoded = page_data["base64_data"]
            json_data = extract_json_from_text(decoded)
            if json_data and "answer" in json_data:
                logger.info("Answer found in base64 decoded data")
                return json_data["answer"]
            
            # Try to extract numbers from decoded text
            numbers = sum_values_in_text(decoded, "value")
            if numbers is not None:
                logger.info(f"Computed sum from base64 text: {numbers}")
                return numbers
        
        # Strategy 3: Download and analyze files
        question = page_data.get("question") or page_data.get("text_content", "")
        file_links = page_data.get("file_links", [])
        
        if file_links:
            logger.info(f"Analyzing {len(file_links)} file(s)...")
            for file_url, file_ext in file_links:
                try:
                    temp_file = create_temp_file(f".{file_ext}")
                    download_file(file_url, temp_file, timeout=REQUEST_TIMEOUT)
                    
                    answer = analyze_data_file(temp_file, question)
                    if answer is not None:
                        logger.info(f"Answer computed from file {file_url}: {answer}")
                        # Clean up temp file
                        try:
                            os.remove(temp_file)
                        except Exception:
                            pass
                        return answer
                    
                    # Clean up temp file
                    try:
                        os.remove(temp_file)
                    except Exception:
                        pass
                except Exception as e:
                    logger.warning(f"Failed to analyze file {file_url}: {e}")
                    continue
        
        # Strategy 4: Analyze page text directly
        text_content = page_data.get("text_content", "")
        if text_content:
            # Look for "sum of" questions
            sum_match = re.search(
                r"sum\s+of\s+(?:the\s+)?['\"]?([A-Za-z0-9_\s-]+)['\"]?\s*(?:column|values?)?",
                text_content,
                flags=re.IGNORECASE
            )
            if sum_match:
                column_name = sum_match.group(1).strip()
                # Try to find table in HTML
                html_content = page_data.get("html_content", "")
                table_matches = re.findall(r"<table[^>]*>.*?</table>", html_content, flags=re.IGNORECASE | re.DOTALL)
                for table_html in table_matches:
                    try:
                        import pandas as pd
                        df_list = pd.read_html(table_html)
                        if df_list:
                            df = df_list[0]
                            if column_name in df.columns:
                                result = float(df[column_name].sum())
                                logger.info(f"Computed sum from inline table: {result}")
                                return result
                            # Fallback to numeric columns
                            numeric_cols = df.select_dtypes(include=["number"]).columns
                            if len(numeric_cols) > 0:
                                result = float(df[numeric_cols[0]].sum())
                                logger.info(f"Computed sum from inline table (fallback): {result}")
                                return result
                    except Exception as e:
                        logger.debug(f"Failed to parse table: {e}")
                        continue
            
            # Fallback: sum all numbers in text
            if not retry:  # Only do this on first attempt
                numbers = sum_values_in_text(text_content)
                if numbers is not None and numbers != 0:
                    logger.info(f"Computed sum from page text: {numbers}")
                    return numbers
        
        # Strategy 5 (retry): Try different heuristics
        if retry:
            # Try extracting from different patterns
            text_content = page_data.get("text_content", "")
            # Look for answer patterns
            answer_patterns = [
                r'answer["\']?\s*[:=]\s*["\']?([^"\'\n]+)["\']?',
                r'solution["\']?\s*[:=]\s*["\']?([^"\'\n]+)["\']?',
                r'result["\']?\s*[:=]\s*["\']?([^"\'\n]+)["\']?',
            ]
            for pattern in answer_patterns:
                matches = re.findall(pattern, text_content, flags=re.IGNORECASE)
                if matches:
                    try:
                        # Try to convert to number
                        answer = float(matches[0])
                        return answer
                    except ValueError:
                        return matches[0]
        
        logger.warning("Could not compute answer using any strategy")
        return None
    
    async def _submit_answer(
        self,
        submission_url: str,
        original_url: str,
        answer: Any
    ) -> Dict[str, Any]:
        """
        Submit answer to the quiz endpoint.
        
        Args:
            submission_url: URL to submit answer to
            original_url: Original quiz URL
            answer: Computed answer
            
        Returns:
            Response from submission endpoint
        """
        payload = {
            "email": self.email,
            "secret": self.secret,
            "url": original_url,
            "answer": answer
        }
        
        logger.info(f"Submitting answer to {submission_url}: {answer}")
        
        for attempt in range(MAX_RETRIES):
            try:
                async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
                    response = await client.post(submission_url, json=payload)
                    
                    if response.status_code in (200, 201, 202):
                        try:
                            result = response.json()
                            logger.info(f"Submission successful: {result}")
                            return result
                        except Exception:
                            return {
                                "status_code": response.status_code,
                                "text": response.text[:500]
                            }
                    else:
                        logger.warning(
                            f"Submission failed with status {response.status_code}: {response.text[:200]}"
                        )
                        if attempt < MAX_RETRIES - 1:
                            await asyncio.sleep(RETRY_DELAY * (attempt + 1))
                        else:
                            return {
                                "status_code": response.status_code,
                                "text": response.text[:500],
                                "error": "Submission failed"
                            }
            
            except Exception as e:
                logger.error(f"Error submitting answer (attempt {attempt + 1}): {e}")
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(RETRY_DELAY * (attempt + 1))
                else:
                    return {"error": str(e)}
        
        return {"error": "Max retries exceeded"}

