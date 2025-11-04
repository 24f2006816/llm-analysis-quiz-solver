"""
Utility functions for file downloads, decoding, data processing, and analysis.
"""
import re
import base64
import json
import tempfile
import os
import httpx
import pandas as pd
import pdfplumber
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


def download_file(url: str, dest_path: str, timeout: int = 60) -> str:
    """
    Download a file from URL to destination path.
    
    Args:
        url: URL to download from
        dest_path: Local file path to save to
        timeout: Request timeout in seconds
        
    Returns:
        Path to downloaded file
    """
    try:
        with httpx.stream("GET", url, follow_redirects=True, timeout=timeout) as response:
            response.raise_for_status()
            with open(dest_path, "wb") as f:
                for chunk in response.iter_bytes():
                    f.write(chunk)
        logger.info(f"Downloaded file from {url} to {dest_path}")
        return dest_path
    except Exception as e:
        logger.error(f"Failed to download {url}: {e}")
        raise


def find_base64_strings(text: str, min_length: int = 120) -> List[str]:
    """
    Find base64-like strings in text.
    
    Args:
        text: Text to search
        min_length: Minimum length of base64 string
        
    Returns:
        List of potential base64 strings
    """
    pattern = rf"[A-Za-z0-9+/=]{{{min_length},}}"
    candidates = re.findall(pattern, text)
    return candidates


def try_decode_base64(b64text: str) -> Optional[str]:
    """
    Attempt to decode a base64 string.
    
    Args:
        b64text: Base64 encoded string
        
    Returns:
        Decoded string or None if decoding fails
    """
    try:
        decoded = base64.b64decode(b64text).decode("utf-8", errors="ignore")
        return decoded
    except Exception:
        return None


def extract_json_from_text(text: str) -> Optional[Dict[str, Any]]:
    """
    Extract JSON object from text.
    
    Args:
        text: Text that may contain JSON
        
    Returns:
        Parsed JSON dict or None
    """
    # Find JSON-like structures
    json_patterns = [
        r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}',  # Nested objects
        r'\[[^\[\]]*(?:\[[^\[\]]*\][^\[\]]*)*\]',  # Arrays
    ]
    
    for pattern in json_patterns:
        matches = re.findall(pattern, text, re.DOTALL)
        for match in matches:
            try:
                return json.loads(match)
            except json.JSONDecodeError:
                continue
    
    # Try to find JSON starting from first {
    json_start = text.find('{')
    if json_start != -1:
        try:
            # Try to extract complete JSON
            remaining = text[json_start:]
            return json.loads(remaining)
        except json.JSONDecodeError:
            pass
    
    return None


def sum_values_in_text(text: str, column_hint: Optional[str] = None) -> Optional[float]:
    """
    Extract and sum numeric values from text.
    
    Args:
        text: Text to analyze
        column_hint: Optional column name hint (e.g., "value")
        
    Returns:
        Sum of values or None if no values found
    """
    if column_hint:
        # Try to find values associated with a specific column
        pattern = rf'"?{column_hint}"?\s*[:=]\s*(-?\d+\.?\d*)'
        vals = re.findall(pattern, text, flags=re.IGNORECASE)
        if vals:
            try:
                return sum(float(v) for v in vals)
            except ValueError:
                pass
    
    # Fallback: find all numbers
    numbers = re.findall(r"(-?\d+\.?\d*)", text)
    if numbers:
        try:
            return sum(float(n) for n in numbers)
        except ValueError:
            pass
    
    return None


def parse_csv_and_sum(file_path: str, column_hint: str = "value") -> Optional[float]:
    """
    Parse CSV/Excel file and sum values from a column.
    
    Args:
        file_path: Path to CSV/Excel file
        column_hint: Column name to sum (default: "value")
        
    Returns:
        Sum of column values or None
    """
    try:
        # Try CSV first
        df = pd.read_csv(file_path)
    except Exception:
        try:
            # Try Excel
            df = pd.read_excel(file_path)
        except Exception as e:
            logger.error(f"Failed to parse {file_path}: {e}")
            return None
    
    if column_hint in df.columns:
        try:
            return float(df[column_hint].sum())
        except Exception as e:
            logger.error(f"Failed to sum column {column_hint}: {e}")
    
    # Fallback: sum first numeric column
    numeric_cols = df.select_dtypes(include=["number"]).columns
    if len(numeric_cols) > 0:
        try:
            return float(df[numeric_cols[0]].sum())
        except Exception as e:
            logger.error(f"Failed to sum numeric column: {e}")
    
    return None


def extract_text_from_pdf(file_path: str) -> str:
    """
    Extract text from PDF file.
    
    Args:
        file_path: Path to PDF file
        
    Returns:
        Extracted text
    """
    text = ""
    try:
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += "\n" + page_text
    except Exception as e:
        logger.error(f"Failed to extract text from PDF {file_path}: {e}")
    
    return text


def find_file_links(html_content: str, base_url: str) -> List[Tuple[str, str]]:
    """
    Find file download links in HTML content.
    
    Args:
        html_content: HTML content to search
        base_url: Base URL for resolving relative links
        
    Returns:
        List of (url, extension) tuples
    """
    file_extensions = r'(csv|xlsx|xls|pdf|png|jpg|jpeg|gif|txt|json)'
    
    # Find href attributes
    href_pattern = rf'href=[\'"]([^\'"]+\.{file_extensions})[\'"]'
    href_matches = re.findall(href_pattern, html_content, flags=re.IGNORECASE)
    
    # Find src attributes
    src_pattern = rf'src=[\'"]([^\'"]+\.{file_extensions})[\'"]'
    src_matches = re.findall(src_pattern, html_content, flags=re.IGNORECASE)
    
    # Find direct URLs in text
    url_pattern = rf'(https?://[^\s<>"\']+\.{file_extensions})'
    url_matches = re.findall(url_pattern, html_content, flags=re.IGNORECASE)
    
    all_links = []
    for match in href_matches + src_matches + url_matches:
        if isinstance(match, tuple):
            url, ext = match
        else:
            url = match
            ext = Path(url).suffix[1:] if Path(url).suffix else ""
        
        # Resolve relative URLs
        if not url.lower().startswith(("http://", "https://")):
            try:
                from urllib.parse import urljoin
                url = urljoin(base_url, url)
            except Exception:
                continue
        
        if url not in [link[0] for link in all_links]:
            all_links.append((url, ext.lower()))
    
    return all_links


def create_temp_file(extension: str = "") -> str:
    """
    Create a temporary file path.
    
    Args:
        extension: File extension (e.g., ".csv", ".pdf")
        
    Returns:
        Path to temporary file
    """
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=extension)
    temp_file.close()
    return temp_file.name


def analyze_data_file(file_path: str, question_hint: Optional[str] = None) -> Optional[Any]:
    """
    Analyze a data file and compute answer based on question hints.
    
    Args:
        file_path: Path to data file
        question_hint: Optional question text to guide analysis
        
    Returns:
        Computed answer or None
    """
    file_ext = Path(file_path).suffix.lower()
    
    # Check for sum operations
    if question_hint:
        sum_match = re.search(r"sum\s+of\s+(?:the\s+)?['\"]?([A-Za-z0-9_\s-]+)['\"]?\s*(?:column|values?)?", 
                             question_hint, flags=re.IGNORECASE)
        if sum_match:
            column_name = sum_match.group(1).strip()
            if file_ext in [".csv", ".xlsx", ".xls"]:
                result = parse_csv_and_sum(file_path, column_name)
                if result is not None:
                    return result
    
    # Default analysis based on file type
    if file_ext in [".csv", ".xlsx", ".xls"]:
        return parse_csv_and_sum(file_path)
    elif file_ext == ".pdf":
        text = extract_text_from_pdf(file_path)
        if question_hint:
            return sum_values_in_text(text, "value")
        return sum_values_in_text(text)
    elif file_ext in [".txt", ".json"]:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        if file_ext == ".json":
            try:
                data = json.loads(content)
                # Try to find numeric values in JSON
                def extract_numbers(obj):
                    if isinstance(obj, (int, float)):
                        return [obj]
                    elif isinstance(obj, dict):
                        return [n for v in obj.values() for n in extract_numbers(v)]
                    elif isinstance(obj, list):
                        return [n for item in obj for n in extract_numbers(item)]
                    return []
                numbers = extract_numbers(data)
                if numbers:
                    return sum(numbers)
            except json.JSONDecodeError:
                pass
        return sum_values_in_text(content)
    
    return None

