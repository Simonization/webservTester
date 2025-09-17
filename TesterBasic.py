#!/usr/bin/env python3
"""
General Tests for 42 Webserv Project
Tests error codes, permissions, file uploads, configuration errors, etc.
"""

import subprocess
import time
import os
import sys
import tempfile
import random
import string
from pathlib import Path

# Colors for output
RED = '\033[91m'
GREEN = '\033[92m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

class WebservGeneralTester:
    def __init__(self, binary_path="./webserv", config_path="config/example.conf"):
        self.binary_path = binary_path
        self.config_path = config_path
        self.server_process = None
        self.test_results = []
        
    def print_test_header(self, test_name):
        print(f"\n{BLUE}{'='*50}{RESET}")
        print(f"{BLUE}Testing: {test_name}{RESET}")
        print(f"{BLUE}{'='*50}{RESET}")
    
    def run_curl(self, command, expected_code=None):
        """Run a curl command and check the response code"""
        try:
            result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=5)
            
            # Extract HTTP status code from curl output
            curl_status_cmd = command + " -o /dev/null -w '%{http_code}'"
            status_result = subprocess.run(curl_status_cmd, shell=True, capture_output=True, text=True, timeout=5)
            status_code = status_result.stdout.strip().replace("'", "")
            
            if expected_code and str(expected_code) == status_code:
                print(f"{GREEN}✓ {command} returned {status_code} as expected{RESET}")
                return True
            elif expected_code:
                print(f"{RED}✗ {command} returned {status_code}, expected {expected_code}{RESET}")
                return False
            else:
                print(f"{YELLOW}→ {command} returned {status_code}{RESET}")
                return True
        except subprocess.TimeoutExpired:
            print(f"{RED}✗ Curl command timed out{RESET}")
            return False
        except Exception as e:
            print(f"{RED}✗ Error running curl: {e}{RESET}")
            return False
    
    def test_error_codes(self):
        """Test 1: Trigger various error codes with curl commands"""
        self.print_test_header("Error Codes with CURL")
        
        tests = [
            # 400 Bad Request
            ("curl -X INVALID http://127.0.0.1:8888/", 400),
            ("curl -H 'Host:' http://127.0.0.1:8888/", 400),
            ("curl --request-target '*' http://127.0.0.1:8888/", 400),
            
            # 403 Forbidden 
            ("curl -X POST http://127.0.0.1:8888/", 403),
            ("curl -X DELETE http://127.0.0.1:8888/index.html", 403),
            
            # 404 Not Found
            ("curl http://127.0.0.1:8888/nonexistent", 404),
            ("curl http://127.0.0.1:8888/no_such_file.html", 404),
            ("curl http://127.0.0.1:8888/uploads/", 404),  # autoindex off by default
            
            # 405 Method Not Allowed
            ("curl -X PUT http://127.0.0.1:8888/", 405),
            ("curl -X PATCH http://127.0.0.1:8888/", 405),
            ("curl -X OPTIONS http://127.0.0.1:8888/", 405),
            
            # 413 Payload Too Large (assuming client_max_body_size is 50000)
            ("curl -X POST -H 'Content-Type: text/plain' --data '" + ("x" * 60000) + "' http://127.0.0.1:8888/methods", 413),
        ]
        
        passed = 0
        for cmd, expected in tests:
            if self.run_curl(cmd, expected):
                passed += 1
        
        print(f"\n{GREEN if passed == len(tests) else YELLOW}Passed {passed}/{len(tests)} error code tests{RESET}")
        return passed == len(tests)
    
    def test_file_uploads(self):
        """Test 2: POST files of different sizes"""
        self.print_test_header("File Uploads - Different Sizes")
        
        # Create temporary files of different sizes
        sizes = [100, 1000, 10000, 49999, 50001]  # Last one should fail if limit is 50000
        test_files = []
        
        for size in sizes:
            fd, path = tempfile.mkstemp(suffix='.txt')
            with os.fdopen(fd, 'w') as f:
                f.write('X' * size)
            test_files.append((path, size))
        
        passed = 0
        for filepath, size in test_files:
            expected = 201 if size <= 50000 else 413
            cmd = f"curl -X POST -H 'Content-Type: text/plain' --data-binary '@{filepath}' http://127.0.0.1:8888/methods"
            
            if self.run_curl(cmd, expected):
                passed += 1
            
            # Clean up
            os.unlink(filepath)
        
        print(f"\n{GREEN if passed == len(test_files) else YELLOW}Passed {passed}/{len(test_files)} file upload tests{RESET}")
        return passed == len(test_files)
    
    def test_permission_errors(self):
        """Test 3: POST to URLs without permissions"""
        self.print_test_header("Permission Tests")
        
        tests = [
            # Locations that don't allow POST
            ("curl -X POST --data 'test' http://127.0.0.1:8888/", 403),
            ("curl -X POST --data 'test' http://127.0.0.1:8888/index.html", 403),
            ("curl -X POST --data 'test' http://127.0.0.1:8888/dashboard", 403),
            ("curl -X POST --data 'test' http://127.0.0.1:8888/autoindex", 403),
            
            # Locations that don't allow DELETE
            ("curl -X DELETE http://127.0.0.1:8888/", 403),
            ("curl -X DELETE http://127.0.0.1:8888/dashboard.html", 403),
            
            # Locations that allow certain methods
            ("curl -X GET http://127.0.0.1:8888/methods", 200),
            ("curl -X POST --data 'test' http://127.0.0.1:8888/methods", 201),
            ("curl -X DELETE http://127.0.0.1:8888/uploads/file.txt", 200),  # if file exists
        ]
        
        passed = 0
        for cmd, expected in tests:
            if self.run_curl(cmd, expected):
                passed += 1
        
        print(f"\n{GREEN if passed == len(tests) else YELLOW}Passed {passed}/{len(tests)} permission tests{RESET}")
        return passed == len(tests)
    
    def test_autoindex(self):
        """Test 4: Autoindex functionality"""
        self.print_test_header("Autoindex Tests")
        
        tests = [
            # Directories without trailing slash and autoindex off should give 404
            ("curl http://127.0.0.1:8888/uploads", 404),
            
            # Directories with autoindex on (based on config)
            ("curl http://127.0.0.1:8888/uploads/", 200),  # autoindex on
            ("curl http://127.0.0.1:8888/uploads/01/", 200),  # autoindex on
            
            # Directories with autoindex off
            ("curl http://127.0.0.1:8888/cgi-bin/", 200),  # has autoindex on in config
        ]
        
        passed = 0
        for cmd, expected in tests:
            if self.run_curl(cmd, expected):
                passed += 1
        
        print(f"\n{GREEN if passed == len(tests) else YELLOW}Passed {passed}/{len(tests)} autoindex tests{RESET}")
        return passed == len(tests)
    
    def create_config_with_duplicate_ports(self):
        """Create a config file with duplicate ports"""
        config = """
server {
    host 127.0.0.1;
    listen 8080;
    server_name server1;
    root ./www/;
    
    location / {
        index index.html;
        allowed_methods GET;
    }
}

server {
    host 127.0.0.1;
    listen 8080;
    server_name server2;
    root ./www/;
    
    location / {
        index index.html;
        allowed_methods GET;
    }
}
"""
        fd, path = tempfile.mkstemp(suffix='.conf')
        with os.fdopen(fd, 'w') as f:
            f.write(config)
        return path
    
    def create_config_with_duplicate_names(self):
        """Create a config file with duplicate server names"""
        config = """
server {
    host 127.0.0.1;
    listen 8080;
    server_name myserver;
    root ./www/;
    
    location / {
        index index.html;
        allowed_methods GET;
    }
}

server {
    host 127.0.0.1;
    listen 8081;
    server_name myserver;
    root ./www/;
    
    location / {
        index index.html;
        allowed_methods GET;
    }
}
"""
        fd, path = tempfile.mkstemp(suffix='.conf')
        with os.fdopen(fd, 'w') as f:
            f.write(config)
        return path
    
    def create_config_with_duplicate_locations(self):
        """Create a config file with duplicate locations"""
        config = """
server {
    host 127.0.0.1;
    listen 8080;
    server_name server1;
    root ./www/;
    
    location /test {
        index index.html;
        allowed_methods GET;
    }
    
    location /test {
        index index.html;
        allowed_methods POST;
    }
}
"""
        fd, path = tempfile.mkstemp(suffix='.conf')
        with os.fdopen(fd, 'w') as f:
            f.write(config)
        return path
    
    def test_config_errors(self):
        """Test 5: Configuration error handling"""
        self.print_test_header("Configuration Error Handling")
        
        test_configs = [
            (self.create_config_with_duplicate_ports(), "duplicate ports"),
            (self.create_config_with_duplicate_names(), "duplicate server names"),
            (self.create_config_with_duplicate_locations(), "duplicate locations"),
        ]
        
        passed = 0
        for config_path, description in test_configs:
            print(f"\nTesting {description}...")
            try:
                # Try to start server with bad config
                result = subprocess.run(
                    [self.binary_path, config_path],
                    capture_output=True,
                    text=True,
                    timeout=2
                )
                
                # Server should exit with error
                if result.returncode != 0:
                    print(f"{GREEN}✓ Server correctly rejected config with {description}{RESET}")
                    passed += 1
                else:
                    print(f"{RED}✗ Server accepted invalid config with {description}{RESET}")
                    # Kill the server if it started
                    subprocess.run(["pkill", "-f", self.binary_path], capture_output=True)
            except subprocess.TimeoutExpired:
                print(f"{RED}✗ Server hung with {description}{RESET}")
                subprocess.run(["pkill", "-f", self.binary_path], capture_output=True)
            except Exception as e:
                print(f"{RED}✗ Error testing {description}: {e}{RESET}")
            finally:
                os.unlink(config_path)
        
        print(f"\n{GREEN if passed == len(test_configs) else YELLOW}Passed {passed}/{len(test_configs)} config error tests{RESET}")
        return passed == len(test_configs)
    
    def test_multiple_servers(self):
        """Test 6: Multiple servers running simultaneously"""
        self.print_test_header("Multiple Servers Test")
        
        # Create config for second server
        config2 = """
server {
    host 127.0.0.1;
    listen 9999;
    server_name second_server;
    root ./www/;
    
    location / {
        index index.html;
        allowed_methods GET;
    }
}
"""
        fd, path2 = tempfile.mkstemp(suffix='.conf')
        with os.fdopen(fd, 'w') as f:
            f.write(config2)
        
        try:
            # Start second server
            server2 = subprocess.Popen([self.binary_path, path2], 
                                      stdout=subprocess.PIPE, 
                                      stderr=subprocess.PIPE)
            time.sleep(2)
            
            # Test both servers
            result1 = self.run_curl("curl http://127.0.0.1:8888/", 200)
            result2 = self.run_curl("curl http://127.0.0.1:9999/", 200)
            
            if result1 and result2:
                print(f"{GREEN}✓ Both servers responding correctly{RESET}")
                passed = True
            else:
                print(f"{RED}✗ One or both servers not responding{RESET}")
                passed = False
            
            # Clean up
            server2.terminate()
            server2.wait(timeout=5)
            
        except Exception as e:
            print(f"{RED}✗ Error testing multiple servers: {e}{RESET}")
            passed = False
        finally:
            os.unlink(path2)
        
        return passed
    
    def test_cgi(self):
        """Test 7: CGI functionality"""
        self.print_test_header("CGI Tests")
        
        tests = [
            # GET requests to CGI
            ("curl http://127.0.0.1:8888/cgi-bin/lotr", 200),
            ("curl http://127.0.0.1:8888/cgi-bin/lotr?action=time", 200),
            ("curl http://127.0.0.1:8888/cgi-bin/star-wars", 200),
            
            # POST requests to CGI
            ("curl -X POST -d 'username=test&message=hello' http://127.0.0.1:8888/cgi-bin/lotr", 200),
            ("curl -X POST -d 'username=test&message=hello' http://127.0.0.1:8888/cgi-bin/star-wars", 200),
        ]
        
        passed = 0
        for cmd, expected in tests:
            if self.run_curl(cmd, expected):
                passed += 1
        
        print(f"\n{GREEN if passed == len(tests) else YELLOW}Passed {passed}/{len(tests)} CGI tests{RESET}")
        return passed == len(tests)
    
    def test_cookies(self):
        """Test 8: Cookie/Session functionality"""
        self.print_test_header("Cookie/Session Tests")
        
        # Test register endpoint sets cookie
        result = subprocess.run(
            "curl -v http://127.0.0.1:8888/register 2>&1 | grep -i 'set-cookie'",
            shell=True,
            capture_output=True,
            text=True
        )
        
        if "set-cookie" in result.stdout.lower():
            print(f"{GREEN}✓ Server sets cookies on /register{RESET}")
            passed = True
        else:
            print(f"{RED}✗ Server doesn't set cookies on /register{RESET}")
            passed = False
        
        return passed
    
    def start_server(self):
        """Start the webserv server"""
        print(f"{YELLOW}Starting webserv with config: {self.config_path}{RESET}")
        self.server_process = subprocess.Popen(
            [self.binary_path, self.config_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        time.sleep(3)  # Give server time to start
        
        # Check if server is running
        if self.server_process.poll() is not None:
            print(f"{RED}✗ Server failed to start{RESET}")
            return False
        
        print(f"{GREEN}✓ Server started successfully{RESET}")
        return True
    
    def stop_server(self):
        """Stop the webserv server"""
        if self.server_process:
            print(f"{YELLOW}Stopping server...{RESET}")
            self.server_process.terminate()
            try:
                self.server_process.wait(timeout=5)
                print(f"{GREEN}✓ Server stopped{RESET}")
            except subprocess.TimeoutExpired:
                self.server_process.kill()
                print(f"{YELLOW}Server killed{RESET}")
            self.server_process = None
    
    def run_all_tests(self):
        """Run all general tests"""
        print(f"\n{BLUE}{'='*60}{RESET}")
        print(f"{BLUE}{'WEBSERV GENERAL TESTS':^60}{RESET}")
        print(f"{BLUE}{'='*60}{RESET}")
        
        # Start server for regular tests
        if not self.start_server():
            print(f"{RED}Failed to start server, aborting tests{RESET}")
            return
        
        test_results = []
        
        # Run tests that require server to be running
        test_results.append(("Error Codes", self.test_error_codes()))
        test_results.append(("File Uploads", self.test_file_uploads()))
        test_results.append(("Permissions", self.test_permission_errors()))
        test_results.append(("Autoindex", self.test_autoindex()))
        test_results.append(("CGI", self.test_cgi()))
        test_results.append(("Cookies", self.test_cookies()))
        
        # Stop server for config tests
        self.stop_server()
        
        # Run config error tests (these should fail to start)
        test_results.append(("Config Errors", self.test_config_errors()))
        
        # Restart server for multiple server test
        if self.start_server():
            test_results.append(("Multiple Servers", self.test_multiple_servers()))
            self.stop_server()
        
        # Print summary
        print(f"\n{BLUE}{'='*60}{RESET}")
        print(f"{BLUE}{'TEST SUMMARY':^60}{RESET}")
        print(f"{BLUE}{'='*60}{RESET}")
        
        passed = sum(1 for _, result in test_results if result)
        total = len(test_results)
        
        for name, result in test_results:
            status = f"{GREEN}PASS{RESET}" if result else f"{RED}FAIL{RESET}"
            print(f"{name:.<40} {status}")
        
        print(f"\n{BLUE}Total: {passed}/{total} tests passed{RESET}")
        
        if passed == total:
            print(f"\n{GREEN}{'🎉 ALL TESTS PASSED! 🎉':^60}{RESET}")
        elif passed >= total * 0.7:
            print(f"\n{YELLOW}{'Most tests passed, check failures above':^60}{RESET}")
        else:
            print(f"\n{RED}{'Multiple tests failed, review implementation':^60}{RESET}")

if __name__ == "__main__":
    # Parse command line arguments
    binary_path = sys.argv[1] if len(sys.argv) > 1 else "./webserv"
    config_path = sys.argv[2] if len(sys.argv) > 2 else "config/example.conf"
    
    # Check if binary exists
    if not os.path.exists(binary_path):
        print(f"{RED}Error: Binary '{binary_path}' not found{RESET}")
        print(f"Usage: {sys.argv[0]} [webserv_binary] [config_file]")
        sys.exit(1)
    
    if not os.path.exists(config_path):
        print(f"{RED}Error: Config file '{config_path}' not found{RESET}")
        print(f"Usage: {sys.argv[0]} [webserv_binary] [config_file]")
        sys.exit(1)
    
    tester = WebservGeneralTester(binary_path, config_path)
    try:
        tester.run_all_tests()
    except KeyboardInterrupt:
        print(f"\n{YELLOW}Tests interrupted by user{RESET}")
        tester.stop_server()
    except Exception as e:
        print(f"\n{RED}Unexpected error: {e}{RESET}")
        tester.stop_server()