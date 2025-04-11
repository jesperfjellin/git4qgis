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

logger = logging.getLogger('Git4QGIS')

class GitSync:
    """Class to handle Git synchronization operations"""
    
    def __init__(self):
        """Initialize the Git synchronization handler"""
        self.temp_dir = None
        self.git_path = self._find_git_executable()
        logger.info(f"Initialized GitSync with git_path: {self.git_path}")
        
    def _execute_git_command(self, command, cwd=None):
        """Execute a Git command
        
        Args:
            command (list): Git command as a list of arguments
            cwd (str): Working directory
            
        Returns:
            str: Command output
        """
        try:
            # If command starts with 'git' and we have a specific git path, use it
            if command[0] == 'git' and self.git_path != 'git':
                command[0] = self.git_path
            
            logger.info(f"Executing git command: {' '.join(command)}")
            
            result = subprocess.run(
                command,
                cwd=cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True
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
        
    def clone_repository(self, url, branch='main'):
        """Clone a Git repository to a temporary directory"""
        print(f"Attempting to clone: {url} (branch: {branch})")
        
        if self.temp_dir:
            print(f"Cleaning up existing temp dir: {self.temp_dir}")
            self.cleanup()
            
        self.temp_dir = tempfile.mkdtemp()
        print(f"Created temp directory: {self.temp_dir}")
        
        try:
            # Full git command for debugging
            git_cmd = ['git', 'clone', '--depth', '1', '--branch', branch, url, self.temp_dir]
            print(f"Running Git command: {' '.join(git_cmd)}")
            
            self._execute_git_command(git_cmd)
            print(f"Clone successful to: {self.temp_dir}")
            return self.temp_dir
        except Exception as e:
            print(f"Clone failed: {str(e)}")
            raise
        
    def get_remote_version(self, repo_url, plugin_path):
        """Check if a plugin has updates available
        
        Args:
            repo_url (str): Repository URL
            plugin_path (str): Path to the local plugin directory
            
        Returns:
            tuple: (has_updates, remote_version)
        """
        # Clone the repository
        temp_dir = self.clone_repository(repo_url)
        
        # Read remote version from metadata.txt
        metadata_path = os.path.join(temp_dir, 'metadata.txt')
        if os.path.exists(metadata_path):
            with open(metadata_path, 'r') as f:
                for line in f:
                    if line.startswith('version='):
                        remote_version = line.strip().split('=')[1]
                        return remote_version
                        
        return None
        
    def update_plugin(self, repo_url, plugin_path):
        """Update a plugin from a Git repository"""
        try:
            logger.info(f"Starting update of plugin: {plugin_path}")
            logger.info(f"From repo: {repo_url}")
            
            # Clone the repository
            temp_dir = self.clone_repository(repo_url)
            logger.info(f"Cloned to temp dir: {temp_dir}")
            
            # Check if temp_dir actually contains any files
            if not os.path.exists(temp_dir) or not os.listdir(temp_dir):
                raise Exception(f"Temp directory is empty or doesn't exist: {temp_dir}")
            
            # IMPORTANT: Completely remove the old plugin directory first
            logger.info(f"Removing old plugin at: {plugin_path}")
            shutil.rmtree(plugin_path)
            
            # Create the plugin directory again
            os.makedirs(plugin_path, exist_ok=True)
            
            # Copy files from the repository to the plugin directory
            logger.info(f"Copying new plugin files from {temp_dir} to {plugin_path}")
            files_copied = 0
            for item in os.listdir(temp_dir):
                if item == '.git':
                    continue
                    
                source = os.path.join(temp_dir, item)
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
            
    def cleanup(self):
        """Clean up temporary files"""
        if self.temp_dir and os.path.exists(self.temp_dir):
            logger.info(f"Cleaning up temporary directory: {self.temp_dir}")
            try:
                # First try normal removal
                shutil.rmtree(self.temp_dir)
            except PermissionError:
                logger.warning(f"Permission error removing {self.temp_dir}, trying fallback cleanup")
                
                # On Windows, try to use the OS to force remove the directory
                try:
                    import subprocess
                    import time
                    
                    # Wait a moment to let any file handles close
                    time.sleep(1)
                    
                    # Use rmdir /s /q which is more forceful on Windows
                    subprocess.run(['cmd', '/c', f'rmdir /s /q "{self.temp_dir}"'], 
                                  shell=True, check=False)
                    
                    # Check if it worked
                    if not os.path.exists(self.temp_dir):
                        logger.info("Fallback cleanup successful")
                    else:
                        logger.warning(f"Could not remove temp directory {self.temp_dir}")
                except Exception as e:
                    logger.error(f"Fallback cleanup failed: {str(e)}")
                    # Just mark for deletion on exit
                    import tempfile
                    tempfile._TemporaryFileWrapper.__del__(self.temp_dir)
            except Exception as e:
                logger.error(f"Error during cleanup: {str(e)}")
            
            # Clear the temp_dir reference
            self.temp_dir = None