"""
Example usage of the LLM Quiz Solver API.
"""
import requests
import json

# Configuration
API_URL = "http://localhost:8000"
EMAIL = "your-email@example.com"
SECRET = "super-secret-string-change-me"  # Change this to match your .env
QUIZ_URL = "https://example.com/quiz-123"  # Replace with actual quiz URL


def solve_quiz():
    """Example: Solve a quiz."""
    print(f"Solving quiz: {QUIZ_URL}")
    
    response = requests.post(
        f"{API_URL}/solve",
        json={
            "email": EMAIL,
            "secret": SECRET,
            "url": QUIZ_URL
        },
        timeout=200  # 3+ minutes for quiz solving
    )
    
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    return response.json()


def check_health():
    """Example: Check API health."""
    response = requests.get(f"{API_URL}/health")
    print(f"Health Check: {response.json()}")
    return response.json()


if __name__ == "__main__":
    print("=== LLM Quiz Solver API Example ===\n")
    
    # Check health
    print("1. Checking API health...")
    check_health()
    print()
    
    # Solve quiz
    print("2. Solving quiz...")
    try:
        result = solve_quiz()
        if result.get("success"):
            print("\n✅ Quiz solved successfully!")
        else:
            print("\n❌ Quiz solving failed")
    except requests.exceptions.RequestException as e:
        print(f"\n❌ Error: {e}")
        print("Make sure the server is running: python run.py")

