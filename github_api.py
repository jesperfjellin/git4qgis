# -*- coding: utf-8 -*-
"""
GitHub API integration for Git4QGIS
"""

import os
import json
import base64
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

class GitHubAPI:
    """Class to handle GitHub API operations"""
    
    def __init__(self, token=None):
        """Initialize the GitHub API handler
        
        Args:
            token (str): GitHub personal access token (optional)
        """
        self.api_url = "https://api.github.com"
        self.token = token
        
    def set_token(self, token):
        """Set the GitHub personal access token
        
        Args:
            token (str): GitHub personal access token
        """
        self.token = token
        
    def _make_request(self, endpoint, method="GET", data=None):
        """Make a request to the GitHub API
        
        Args:
            endpoint (str): API endpoint (e.g., "/repos/username/repo/contents")
            method (str): HTTP method (GET, POST, etc.)
            data (dict): Data to send with the request (for POST, PUT, etc.)
            
        Returns:
            dict: JSON response from the API
        """
        url = f"{self.api_url}{endpoint}"
        headers = {
            "Accept": "application/vnd.github.v3+json"
        }
        
        if self.token:
            headers["Authorization"] = f"token {self.token}"
            
        if data:
            data = json.dumps(data).encode("utf-8")
            
        request = Request(url, headers=headers, method=method, data=data)
        
        try:
            with urlopen(request) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as e:
            error_message = e.read().decode("utf-8")
            try:
                error_data = json.loads(error_message)
                error_message = error_data.get("message", error_message)
            except:
                pass
            raise Exception(f"GitHub API error: {error_message}")
        except URLError as e:
            raise Exception(f"Network error: {e.reason}")
            
    def get_repository(self, owner, repo):
        """Get repository information
        
        Args:
            owner (str): Repository owner username
            repo (str): Repository name
            
        Returns:
            dict: Repository information
        """
        return self._make_request(f"/repos/{owner}/{repo}")
        
    def get_contents(self, owner, repo, path, ref=None):
        """Get repository contents
        
        Args:
            owner (str): Repository owner username
            repo (str): Repository name
            path (str): Path to the file or directory
            ref (str): Git reference (branch, tag, or commit SHA)
            
        Returns:
            dict or list: File or directory contents
        """
        endpoint = f"/repos/{owner}/{repo}/contents/{path}"
        if ref:
            endpoint += f"?ref={ref}"
        return self._make_request(endpoint)
        
    def get_file_content(self, owner, repo, path, ref=None):
        """Get file content as string
        
        Args:
            owner (str): Repository owner username
            repo (str): Repository name
            path (str): Path to the file
            ref (str): Git reference (branch, tag, or commit SHA)
            
        Returns:
            str: File content as string
        """
        contents = self.get_contents(owner, repo, path, ref)
        if "content" in contents:
            return base64.b64decode(contents["content"]).decode("utf-8")
        raise Exception(f"Not a file: {path}")
        
    def get_commits(self, owner, repo, path=None, since=None):
        """Get commits for a repository or file
        
        Args:
            owner (str): Repository owner username
            repo (str): Repository name
            path (str): Path to the file (optional)
            since (str): ISO 8601 timestamp (optional)
            
        Returns:
            list: Commits information
        """
        endpoint = f"/repos/{owner}/{repo}/commits"
        params = []
        
        if path:
            params.append(f"path={path}")
        if since:
            params.append(f"since={since}")
            
        if params:
            endpoint += "?" + "&".join(params)
            
        return self._make_request(endpoint)
        
    def parse_github_url(self, url):
        """Parse a GitHub URL to extract owner and repository name
        
        Args:
            url (str): GitHub repository URL
            
        Returns:
            tuple: (owner, repo)
        """
        # Remove .git extension if present
        if url.endswith(".git"):
            url = url[:-4]
            
        # Handle various GitHub URL formats
        if "github.com" in url:
            parts = url.split("github.com/")
            if len(parts) > 1:
                parts = parts[1].split("/")
                if len(parts) >= 2:
                    return parts[0], parts[1]
                    
        return None, None