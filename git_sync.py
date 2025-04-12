# -*- coding: utf-8 -*-
"""
Git synchronization for Git4QGIS
"""

import os
import subprocess
import tempfile
import shutil
from datetime import datetime
import logging
import base64

logger = logging.getLogger('Git4QGIS')

class GitSync:
    """Class to handle Git synchronization operations"""
    
    def __init__(self):
        """Initialize the Git synchronization handler"""
        self.temp_dir = None
        self.git_path = self._find_git_executable()
        logger.info(f"Initialized GitSync with git_path: {self.git_path}")
        
    def _execute_git_command(self, command, cwd=None, env=None):
        """Execute a Git command
        
        Args:
            command (list): Git command as a list of arguments
            cwd (str): Working directory
            env (dict): Environment variables
            
        Returns:
            str: Command output
        """
        try:
            # If command starts with 'git' and we have a specific git path, use it
            if command[0] == 'git' and self.git_path != 'git':
                command[0] = self.git_path
            
            logger.info(f"Executing git command: {' '.join(command)}")
            
            # Set up environment variables including system ones
            execution_env = os.environ.copy()
            if env:
                execution_env.update(env)
            
            result = subprocess.run(
                command,
                cwd=cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True,
                env=execution_env
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            logger.error(f"Git command failed: {e.stderr}")
            raise Exception(f"Git command failed: {e.stderr}")
        except Exception as e:
            logger.error(f"Exception during Git command: {str(e)}")
            raise
        
    def is_git_installed(self):
        """Check if Git is installed"""
        logger.info(f"Checking if Git is installed using path: {self.git_path}")
        
        # If we found Git in a specific location, use that
        if self.git_path != 'git' and os.path.exists(self.git_path):
            logger.info(f"Git found at: {self.git_path}")
            return True
        
        # Otherwise try running git command
        try:
            version = self._execute_git_command(['git', '--version'])
            logger.info(f"Git is installed: {version}")
            return True
        except Exception as e:
            logger.error(f"Git check failed: {str(e)}")
            # Second chance - try with explicit path
            try:
                # Hardcode the path you confirmed exists
                hardcoded_path = r'C:\Program Files\Git\bin\git.exe'
                if os.path.exists(hardcoded_path):
                    self.git_path = hardcoded_path
                    logger.info(f"Using hardcoded Git path: {hardcoded_path}")
                    version = self._execute_git_command([hardcoded_path, '--version'])
                    logger.info(f"Git is installed (hardcoded path): {version}")
                    return True
            except Exception as e2:
                logger.error(f"Git check with hardcoded path failed: {str(e2)}")
            return False
        
    def _find_git_executable(self):
        """Find the Git executable path"""
        logger.info("Searching for Git executable")
        
        # Try common Git installation paths on Windows
        common_paths = [
            r'C:\Program Files\Git\bin\git.exe',     # Common path
            r'C:\Program Files\Git\cmd\git.exe',      # Alternative location
            r'C:\Program Files (x86)\Git\bin\git.exe',
            r'C:\Program Files (x86)\Git\cmd\git.exe',
            os.path.expanduser(r'~\AppData\Local\Programs\Git\bin\git.exe'),
        ]
        
        # Check if each path exists
        for path in common_paths:
            logger.info(f"Checking for Git at: {path}")
            if os.path.exists(path):
                logger.info(f"Found Git at: {path}")
                return path
        
        # If not found in common locations, return default
        logger.warning("Git not found in common locations, defaulting to 'git'")
        return 'git'
        
    def clone_repository(self, url, branch='main', username=None, token=None):
        """Clone a Git repository to a temporary directory
        
        Args:
            url (str): Repository URL
            branch (str): Branch to clone
            username (str): GitHub username for authentication
            token (str): GitHub token or password for authentication
        """
        print(f"Attempting to clone: {url} (branch: {branch})")
        
        if self.temp_dir:
            print(f"Cleaning up existing temp dir: {self.temp_dir}")
            self.cleanup()
            
        self.temp_dir = tempfile.mkdtemp()
        print(f"Created temp directory: {self.temp_dir}")
        
        try:
            # If authentication provided, modify the URL
            if username and token:
                # Parse the URL to insert credentials
                if url.startswith('https://'):
                    auth_url = url.replace('https://', f'https://{username}:{token}@')
                    # Log that we're using authentication (but don't log the full URL with token)
                    logger.info(f"Using authenticated URL for {url}")
                else:
                    auth_url = url
                    logger.warning(f"Authentication provided but URL doesn't use HTTPS: {url}")
            else:
                auth_url = url
                
            # Full git command for debugging (don't log auth_url to avoid exposing credentials)
            git_cmd = ['git', 'clone', '--depth', '1', '--branch', branch, auth_url, self.temp_dir]
            print(f"Running Git command: git clone --depth 1 --branch {branch} [REPO_URL] {self.temp_dir}")
            
            # Set up environment variables for git credential helper if needed
            env = None
            if username and token and 'github.com' in url:
                # Set git credential helper environment variables
                credential = f"username={username}\npassword={token}\n"
                credential_b64 = base64.b64encode(credential.encode('utf-8')).decode('utf-8')
                env = {
                    'GIT_ASKPASS': 'echo',
                    'GIT_TERMINAL_PROMPT': '0',
                    'GCM_CREDENTIAL': credential_b64
                }
            
            # Execute with authentication
            self._execute_git_command(git_cmd, env=env)
            print(f"Clone successful to: {self.temp_dir}")
            return self.temp_dir
        except Exception as e:
            print(f"Clone failed: {str(e)}")
            raise
    
    def _find_plugin_directory(self, temp_dir, plugin_name):
        """Find the appropriate directory for a plugin in the repository
        
        Args:
            temp_dir (str): Path to the temporary directory containing the cloned repo
            plugin_name (str): Name of the plugin to find
            
        Returns:
            str: Path to the plugin directory within the repo (or root if single plugin)
        """
        # First check if metadata.txt exists in the root (single plugin repo)
        root_metadata_path = os.path.join(temp_dir, 'metadata.txt')
        if os.path.exists(root_metadata_path):
            logger.info(f"Found metadata.txt in root - treating as single plugin repository")
            return temp_dir
            
        # If not, check for subdirectories containing metadata.txt
        logger.info(f"No metadata.txt in root - looking for plugins in subdirectories")
        plugin_dirs = []
        
        for item in os.listdir(temp_dir):
            item_path = os.path.join(temp_dir, item)
            metadata_path = os.path.join(item_path, 'metadata.txt')
            
            if os.path.isdir(item_path) and os.path.exists(metadata_path):
                logger.info(f"Found plugin in subdirectory: {item}")
                plugin_dirs.append(item)
                
                # If the directory name exactly matches the plugin name, return it immediately
                if item == plugin_name:
                    logger.info(f"Exact match found for plugin: {plugin_name}")
                    return item_path
        
        # If we have plugin directories but no exact match, log what we found
        if plugin_dirs:
            logger.info(f"Found {len(plugin_dirs)} plugins in repository: {', '.join(plugin_dirs)}")
            logger.warning(f"No subdirectory matching plugin name '{plugin_name}' exactly")
            
            # Try to find a case-insensitive match
            for item in plugin_dirs:
                if item.lower() == plugin_name.lower():
                    logger.info(f"Found case-insensitive match: {item}")
                    return os.path.join(temp_dir, item)
        
        # Default to the repo root if we can't find a match
        logger.warning(f"No matching plugin directory found for '{plugin_name}' - using repository root")
        return temp_dir
        
    def get_remote_version(self, repo_url, plugin_path, username=None, token=None):
        """Check if a plugin has updates available
        
        Args:
            repo_url (str): Repository URL
            plugin_path (str): Path to the local plugin directory
            username (str): GitHub username for authentication
            token (str): GitHub token or password for authentication
            
        Returns:
            str: Remote version if found, None otherwise
        """
        # Get the plugin name from the path
        plugin_name = os.path.basename(plugin_path)
        logger.info(f"Getting remote version for plugin: {plugin_name}")
        
        # Clone the repository with authentication if provided
        temp_dir = self.clone_repository(repo_url, username=username, token=token)
        
        # Check if this is a single-plugin or multi-plugin repository
        root_metadata_path = os.path.join(temp_dir, 'metadata.txt')
        
        if os.path.exists(root_metadata_path):
            # Single plugin in repo root
            logger.info(f"Found metadata.txt in repository root - single plugin repository")
            metadata_path = root_metadata_path
        else:
            # Look for plugin in subdirectories
            logger.info(f"No metadata.txt in root - looking for plugin in subdirectories")
            
            # Check for subdirectory matching plugin name
            subdir_metadata_path = os.path.join(temp_dir, plugin_name, 'metadata.txt')
            if os.path.exists(subdir_metadata_path):
                logger.info(f"Found matching subdirectory for {plugin_name}")
                metadata_path = subdir_metadata_path
            else:
                logger.warning(f"No matching subdirectory for {plugin_name} - plugin may not exist in repo")
                return None
        
        logger.info(f"Looking for metadata at: {metadata_path}")
        
        # Read remote version from metadata.txt
        if os.path.exists(metadata_path):
            with open(metadata_path, 'r') as f:
                for line in f:
                    if line.startswith('version='):
                        remote_version = line.strip().split('=')[1]
                        logger.info(f"Found remote version: {remote_version}")
                        return remote_version
        else:
            logger.warning(f"Metadata file not found at: {metadata_path}")
        
        return None
        
    def update_plugin(self, repo_url, plugin_path, username=None, token=None):
        """Update a plugin from a Git repository
        
        Args:
            repo_url (str): Repository URL
            plugin_path (str): Path to the local plugin directory
            username (str): GitHub username for authentication
            token (str): GitHub token or password for authentication
        """
        try:
            # Get the plugin name from the path
            plugin_name = os.path.basename(plugin_path)
            logger.info(f"Starting update of plugin: {plugin_name} at {plugin_path}")
            logger.info(f"From repo: {repo_url}")
            
            # Clone the repository with authentication
            temp_dir = self.clone_repository(repo_url, username=username, token=token)
            logger.info(f"Cloned to temp dir: {temp_dir}")
            
            # Check if this is a single-plugin or multi-plugin repository
            root_metadata_path = os.path.join(temp_dir, 'metadata.txt')
            
            if os.path.exists(root_metadata_path):
                # Single plugin in repo root - use entire repo content
                logger.info(f"Found metadata.txt in repository root - using entire repository")
                source_dir = temp_dir
            else:
                # Look for plugin in subdirectories
                logger.info(f"No metadata.txt in root - looking for plugin in subdirectories")
                
                # Check for subdirectory matching plugin name
                subdir_path = os.path.join(temp_dir, plugin_name)
                if os.path.exists(os.path.join(subdir_path, 'metadata.txt')):
                    logger.info(f"Found matching subdirectory for {plugin_name}")
                    source_dir = subdir_path
                else:
                    # If explicit match not found, raise exception
                    logger.error(f"No matching subdirectory for {plugin_name} in repository")
                    raise Exception(f"Plugin {plugin_name} not found in repository structure")
            
            logger.info(f"Using source directory: {source_dir}")
            
            # IMPORTANT: Remove the old plugin directory first
            logger.info(f"Removing old plugin at: {plugin_path}")
            self._safe_remove_directory(plugin_path)
            
            # Create the plugin directory again
            os.makedirs(plugin_path, exist_ok=True)
            
            # Copy files from the source directory to the plugin directory
            logger.info(f"Copying new plugin files from {source_dir} to {plugin_path}")
            files_copied = 0
            for item in os.listdir(source_dir):
                if item == '.git':
                    continue
                    
                source = os.path.join(source_dir, item)
                dest = os.path.join(plugin_path, item)
                
                if os.path.isdir(source):
                    shutil.copytree(source, dest)
                    files_copied += len(os.listdir(source))
                else:
                    shutil.copy2(source, dest)
                    files_copied += 1
                
            logger.info(f"Copied {files_copied} files to {plugin_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error during update: {str(e)}")
            raise Exception(f"Failed to update plugin: {str(e)}")
            
        finally:
            self.cleanup()
            
    def _safe_remove_directory(self, directory_path):
        """Safely remove a directory with special handling for .git directories"""
        if not os.path.exists(directory_path):
            return
            
        try:
            # First try: Standard removal
            shutil.rmtree(directory_path)
        except PermissionError as e:
            logger.warning(f"Permission error removing {directory_path}, trying alternative methods")
            
            try:
                # Windows-specific approach for locked files
                import subprocess
                import time
                
                # Special handling for .git directory
                git_dir = os.path.join(directory_path, '.git')
                if os.path.exists(git_dir):
                    logger.info(f"Found .git directory, using special removal for: {git_dir}")
                    
                    # Try to make files writable first
                    for root, dirs, files in os.walk(git_dir, topdown=False):
                        for name in files:
                            try:
                                file_path = os.path.join(root, name)
                                # Make file writable
                                os.chmod(file_path, 0o777)
                            except:
                                pass
                
                # Wait a moment to let any file handles close
                time.sleep(2)
                
                # Force removal using Windows command
                cmd = f'rmdir /s /q {directory_path}'
                logger.info(f"Executing: {cmd}")
                result = subprocess.run(['cmd', '/c', 'rmdir', '/s', '/q', directory_path], 
                                        shell=False, 
                                        capture_output=True,
                                        text=True)
                
                if result.returncode != 0:
                    logger.warning(f"Command failed: {result.stderr}")
                    
                # Check if it worked
                if os.path.exists(directory_path):
                    logger.warning(f"Directory still exists after forced removal: {directory_path}")
                    # As a last resort, try to rename the directory
                    random_suffix = datetime.now().strftime('%Y%m%d%H%M%S')
                    renamed_path = f"{directory_path}_old_{random_suffix}"
                    logger.info(f"Attempting to rename to: {renamed_path}")
                    os.rename(directory_path, renamed_path)
                    
                    # The directory has been renamed, so we can proceed
                    logger.info(f"Successfully renamed problematic directory")
                else:
                    logger.info(f"Successfully removed directory")
                    
            except Exception as inner_e:
                logger.error(f"Failed to remove directory using all methods: {str(inner_e)}")
                raise inner_e
            
    def cleanup(self):
        """Clean up temporary files"""
        if self.temp_dir and os.path.exists(self.temp_dir):
            logger.info(f"Cleaning up temporary directory: {self.temp_dir}")
            try:
                # Use our safe directory removal method
                self._safe_remove_directory(self.temp_dir)
            except Exception as e:
                logger.error(f"Error during cleanup: {str(e)}")
            
            # Clear the temp_dir reference
            self.temp_dir = None