import os
import re
import requests
import base64
from datetime import datetime
from typing import List, Dict, Tuple
import time

class GitHubEnvScraper:
    def __init__(self, token: str = None):
        """
        Initialize the scraper with optional GitHub token for higher rate limits
        
        Args:
            token: GitHub personal access token (optional but recommended)
        """
        self.token = token
        self.headers = {}
        if token:
            self.headers['Authorization'] = f'token {token}'
        self.base_url = 'https://api.github.com'
        self.results = []
        
    def search_repos(self, query: str, max_repos: int = 10) -> List[Dict]:
        """
        Search for repositories based on query
        
        Args:
            query: Search query for repositories
            max_repos: Maximum number of repositories to search
            
        Returns:
            List of repository information
        """
        repos = []
        url = f'{self.base_url}/search/repositories'
        params = {
            'q': query,
            'sort': 'stars',
            'order': 'desc',
            'per_page': min(max_repos, 100)
        }
        
        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            data = response.json()
            
            for repo in data.get('items', [])[:max_repos]:
                repos.append({
                    'name': repo['full_name'],
                    'url': repo['html_url'],
                    'stars': repo['stargazers_count']
                })
                
        except requests.exceptions.RequestException as e:
            print(f"Error searching repositories: {e}")
            
        return repos
    
    def find_env_files(self, repo_name: str) -> List[Dict]:
        """
        Find all .env files in a repository
        
        Args:
            repo_name: Full repository name (owner/repo)
            
        Returns:
            List of .env file information
        """
        env_files = []
        url = f'{self.base_url}/search/code'
        params = {
            'q': f'filename:.env repo:{repo_name}',
            'per_page': 100
        }
        
        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            data = response.json()
            
            for file in data.get('items', []):
                env_files.append({
                    'path': file['path'],
                    'url': file['url'],
                    'html_url': file['html_url']
                })
                
        except requests.exceptions.RequestException as e:
            print(f"Error finding .env files in {repo_name}: {e}")
            
        return env_files
    
    def get_file_content(self, file_url: str) -> str:
        """
        Get the content of a file from GitHub
        
        Args:
            file_url: API URL of the file
            
        Returns:
            File content as string
        """
        try:
            response = requests.get(file_url, headers=self.headers)
            response.raise_for_status()
            data = response.json()
            
            # Decode base64 content
            content = base64.b64decode(data['content']).decode('utf-8')
            return content
            
        except requests.exceptions.RequestException as e:
            print(f"Error getting file content: {e}")
            return ""
    
    def apply_regex_patterns(self, content: str, patterns: List[str]) -> List[Tuple[str, str]]:
        """
        Apply regex patterns to content and extract matches
        
        Args:
            content: File content
            patterns: List of regex patterns to match
            
        Returns:
            List of (pattern, match) tuples
        """
        matches = []
        
        for pattern in patterns:
            try:
                regex = re.compile(pattern, re.MULTILINE | re.IGNORECASE)
                found_matches = regex.findall(content)
                
                for match in found_matches:
                    matches.append((pattern, match))
                    
            except re.error as e:
                print(f"Invalid regex pattern '{pattern}': {e}")
                
        return matches
    
    def scrape(self, repos: List[str], patterns: List[str], search_query: str = None, max_repos: int = 10):
        """
        Main scraping function
        
        Args:
            repos: List of specific repository names to search (owner/repo format)
            patterns: List of regex patterns to match in .env files
            search_query: Optional query to search for additional repositories
            max_repos: Maximum number of repositories to search when using search_query
        """
        all_repos = repos.copy()
        
        # Add repositories from search if query provided
        if search_query:
            print(f"Searching for repositories matching '{search_query}'...")
            search_results = self.search_repos(search_query, max_repos)
            all_repos.extend([repo['name'] for repo in search_results])
        
        # Remove duplicates
        all_repos = list(set(all_repos))
        
        print(f"Scanning {len(all_repos)} repositories...")
        
        for repo_name in all_repos:
            print(f"\nScanning repository: {repo_name}")
            
            # Find .env files
            env_files = self.find_env_files(repo_name)
            
            if not env_files:
                print(f"  No .env files found")
                continue
                
            print(f"  Found {len(env_files)} .env file(s)")
            
            for env_file in env_files:
                print(f"  Checking: {env_file['path']}")
                
                # Get file content
                content = self.get_file_content(env_file['url'])
                
                if content:
                    # Apply regex patterns
                    matches = self.apply_regex_patterns(content, patterns)
                    
                    if matches:
                        self.results.append({
                            'repo': repo_name,
                            'file_path': env_file['path'],
                            'file_url': env_file['html_url'],
                            'matches': matches
                        })
                        print(f"    Found {len(matches)} matches!")
                
                # Rate limiting
                time.sleep(0.5)
    
    def save_results(self, output_file: str = 'github_env_matches.txt'):
        """
        Save results to a text file
        
        Args:
            output_file: Output filename
        """
        with open(output_file, 'w') as f:
            f.write(f"GitHub .env File Scan Results\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 80 + "\n\n")
            
            if not self.results:
                f.write("No matches found.\n")
                return
            
            for result in self.results:
                f.write(f"Repository: {result['repo']}\n")
                f.write(f"File: {result['file_path']}\n")
                f.write(f"URL: {result['file_url']}\n")
                f.write("-" * 40 + "\n")
                
                for pattern, match in result['matches']:
                    f.write(f"Pattern: {pattern}\n")
                    f.write(f"Match: {match}\n")
                    f.write("\n")
                
                f.write("=" * 80 + "\n\n")
        
        print(f"\nResults saved to {output_file}")


# Example usage
if __name__ == "__main__":
    # Initialize scraper (optionally with GitHub token)
    # Get a token from: https://github.com/settings/tokens
    # scraper = GitHubEnvScraper(token="your_github_token_here")
    scraper = GitHubEnvScraper()
    
    # Define repositories to search
    # Format: "owner/repository"
    specific_repos = [
        # "facebook/react",
        # "vuejs/vue",
        # "angular/angular"
    ]
    
    # Define regex patterns to search for
    # These patterns will search for common sensitive data patterns
    regex_patterns = [
        # API Keys
        r'(?:api[_-]?key|apikey)\s*=\s*["\']?([a-zA-Z0-9_\-]+)["\']?',
        
        # AWS Keys
        r'(?:aws[_-]?access[_-]?key[_-]?id|aws[_-]?key)\s*=\s*["\']?([A-Z0-9]{20})["\']?',
        r'(?:aws[_-]?secret[_-]?access[_-]?key|aws[_-]?secret)\s*=\s*["\']?([a-zA-Z0-9/+=]{40})["\']?',
        
        # Database URLs
        r'(?:database[_-]?url|db[_-]?url|mongo[_-]?uri)\s*=\s*["\']?([^\s"\']+)["\']?',
        
        # JWT Secrets
        r'(?:jwt[_-]?secret|secret[_-]?key)\s*=\s*["\']?([a-zA-Z0-9_\-]+)["\']?',
        
        # Generic Secrets
        r'(?:secret|password|passwd|pwd)\s*=\s*["\']?([^\s"\']+)["\']?',
        
        # OAuth Tokens
        r'(?:oauth[_-]?token|access[_-]?token|bearer[_-]?token)\s*=\s*["\']?([a-zA-Z0-9_\-]+)["\']?',
        
        # Private Keys (careful with this one)
        r'(?:private[_-]?key|priv[_-]?key)\s*=\s*["\']?([^\s"\']+)["\']?',
        
        # Email credentials
        r'(?:email[_-]?password|smtp[_-]?password)\s*=\s*["\']?([^\s"\']+)["\']?',
        
        # Stripe/Payment Keys
        r'(?:stripe[_-]?key|stripe[_-]?secret)\s*=\s*["\']?(sk_[a-zA-Z0-9]+)["\']?',
        
        # Custom pattern example - adjust as needed
        # r'YOUR_CUSTOM_PATTERN_HERE'
    ]
    
    # You can also search for repositories dynamically
    # search_query = "language:javascript stars:>1000"
    search_query = None  # Set to None to only search specific_repos
    
    # Run the scraper
    scraper.scrape(
        repos=specific_repos,
        patterns=regex_patterns,
        search_query=search_query,
        max_repos=5  # Limit search results when using search_query
    )
    
    # Save results to file
    scraper.save_results('github_env_matches.txt')