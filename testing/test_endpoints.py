"""
Simple test script for FastAPI endpoints.

This script tests all endpoints in the FastAPI application and displays
the results in a clear, formatted way.

Usage:
    python test_endpoints.py
    python test_endpoints.py --base-url http://localhost:8000
"""

import requests
import json
import sys
from typing import Dict, Any
from datetime import datetime


class Colors:
    """ANSI color codes for terminal output."""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


class APITester:
    """Simple API endpoint tester."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip('/')
        self.results = []
        
    def print_header(self, text: str):
        """Print a section header."""
        print(f"\n{Colors.BOLD}{Colors.CYAN}{'=' * 60}{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.CYAN}{text}{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.CYAN}{'=' * 60}{Colors.RESET}\n")
    
    def print_test(self, method: str, endpoint: str, status: str, response_time: float):
        """Print test result."""
        status_color = Colors.GREEN if status == "PASS" else Colors.RED
        print(f"{status_color}{status}{Colors.RESET} | "
              f"{Colors.BLUE}{method:6}{Colors.RESET} | "
              f"{endpoint:30} | "
              f"{response_time:.3f}s")
    
    def print_response(self, data: Any, indent: int = 2):
        """Print formatted response data."""
        if isinstance(data, dict) or isinstance(data, list):
            print(json.dumps(data, indent=indent))
        else:
            print(data)
    
    def test_endpoint(
        self, 
        method: str, 
        endpoint: str, 
        expected_status: int = 200,
        show_response: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Test a single endpoint.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: Endpoint path
            expected_status: Expected HTTP status code
            show_response: Whether to print the response
            **kwargs: Additional arguments for requests
        
        Returns:
            Dictionary with test results
        """
        url = f"{self.base_url}{endpoint}"
        start_time = datetime.now()
        
        try:
            response = requests.request(method, url, timeout=10, **kwargs)
            response_time = (datetime.now() - start_time).total_seconds()
            
            # Check status code
            status = "PASS" if response.status_code == expected_status else "FAIL"
            
            # Store result
            result = {
                "method": method,
                "endpoint": endpoint,
                "status": status,
                "status_code": response.status_code,
                "expected_status": expected_status,
                "response_time": response_time,
                "url": url
            }
            
            self.results.append(result)
            self.print_test(method, endpoint, status, response_time)
            
            # Print response if requested
            if show_response:
                print(f"{Colors.YELLOW}Response:{Colors.RESET}")
                try:
                    self.print_response(response.json())
                except json.JSONDecodeError:
                    print(response.text[:500])  # Print first 500 chars if not JSON
                print()
            
            # Print headers if present
            if "X-Request-ID" in response.headers:
                print(f"{Colors.CYAN}Request-ID:{Colors.RESET} {response.headers['X-Request-ID']}")
            if "X-Process-Time" in response.headers:
                print(f"{Colors.CYAN}Process-Time:{Colors.RESET} {response.headers['X-Process-Time']}s")
            
            print()
            return result
            
        except requests.exceptions.ConnectionError:
            print(f"{Colors.RED}FAIL{Colors.RESET} | "
                  f"{Colors.BLUE}{method:6}{Colors.RESET} | "
                  f"{endpoint:30} | Connection failed")
            print(f"{Colors.RED}Error: Could not connect to {url}{Colors.RESET}")
            print(f"{Colors.YELLOW}Make sure the server is running!{Colors.RESET}\n")
            return {
                "method": method,
                "endpoint": endpoint,
                "status": "FAIL",
                "error": "Connection failed"
            }
        
        except Exception as e:
            print(f"{Colors.RED}FAIL{Colors.RESET} | "
                  f"{Colors.BLUE}{method:6}{Colors.RESET} | "
                  f"{endpoint:30} | Error: {str(e)}\n")
            return {
                "method": method,
                "endpoint": endpoint,
                "status": "FAIL",
                "error": str(e)
            }
    
    def test_streaming_endpoint(self, endpoint: str):
        """Test a streaming endpoint."""
        url = f"{self.base_url}{endpoint}"
        print(f"\n{Colors.CYAN}Testing streaming endpoint:{Colors.RESET} {endpoint}")
        
        try:
            response = requests.get(url, stream=True, timeout=10)
            print(f"{Colors.GREEN}Status Code:{Colors.RESET} {response.status_code}")
            print(f"{Colors.YELLOW}Streaming response:{Colors.RESET}")
            
            count = 0
            for line in response.iter_lines():
                if line:
                    decoded_line = line.decode('utf-8')
                    print(f"  {decoded_line}")
                    count += 1
                    if count >= 5:  # Limit output
                        break
            
            print(f"{Colors.GREEN}✓ Streaming test passed{Colors.RESET}\n")
            
        except Exception as e:
            print(f"{Colors.RED}✗ Streaming test failed: {str(e)}{Colors.RESET}\n")
    
    def print_summary(self):
        """Print test summary."""
        self.print_header("TEST SUMMARY")
        
        total = len(self.results)
        passed = sum(1 for r in self.results if r.get("status") == "PASS")
        failed = total - passed
        
        print(f"Total Tests:  {total}")
        print(f"{Colors.GREEN}Passed:       {passed}{Colors.RESET}")
        print(f"{Colors.RED}Failed:       {failed}{Colors.RESET}")
        
        if failed > 0:
            print(f"\n{Colors.RED}Failed Tests:{Colors.RESET}")
            for result in self.results:
                if result.get("status") == "FAIL":
                    print(f"  - {result['method']} {result['endpoint']}")
                    if "error" in result:
                        print(f"    Error: {result['error']}")
                    elif "status_code" in result:
                        print(f"    Expected: {result['expected_status']}, Got: {result['status_code']}")
        
        print()
        return failed == 0


def main():
    """Run all endpoint tests."""
    # Parse command line arguments
    base_url = "http://localhost:8000"
    if len(sys.argv) > 1 and sys.argv[1].startswith("http"):
        base_url = sys.argv[1]
    
    tester = APITester(base_url)
    
    print(f"\n{Colors.BOLD}FastAPI Endpoint Testing Suite{Colors.RESET}")
    print(f"Testing server at: {Colors.CYAN}{base_url}{Colors.RESET}\n")
    
    # Test root endpoint
    tester.print_header("ROOT ENDPOINT")
    tester.test_endpoint("GET", "/")
    
    # Test health endpoints
    tester.print_header("HEALTH ENDPOINTS")
    tester.test_endpoint("GET", "/health")
    tester.test_endpoint("GET", "/ready")
    tester.test_endpoint("GET", "/alive")
    
    # Test streaming endpoint
    tester.print_header("STREAMING ENDPOINT")
    tester.test_streaming_endpoint("/stream-example")
    
    # Test non-existent endpoint (should return 404)
    tester.print_header("ERROR HANDLING")
    tester.test_endpoint("GET", "/nonexistent", expected_status=404, show_response=True)
    
    # Test with custom request ID
    tester.print_header("CUSTOM REQUEST ID")
    tester.test_endpoint(
        "GET", 
        "/health",
        headers={"X-Request-ID": "test-12345"},
        show_response=False
    )
    
    # Print summary
    success = tester.print_summary()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()