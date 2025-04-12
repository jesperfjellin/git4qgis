# -*- coding: utf-8 -*-
"""
Plugin scanner for Git4QGIS
"""

import os
import configparser
from qgis.core import QgsApplication
import logging

logger = logging.getLogger('Git4QGIS')

class PluginScanner:
    """Class to scan for QGIS plugins matching an organization prefix"""
    
    def __init__(self, org_prefix, custom_plugin_dir=None):
        """Initialize the plugin scanner
        
        Args:
            org_prefix (str): Organization prefix to match plugins against
            custom_plugin_dir (str): Optional custom plugin directory
        """
        self.org_prefix = org_prefix
        
        # Get all possible plugin directories
        self.plugin_dirs = []
        
        # User plugins directory
        user_plugin_dir = os.path.join(QgsApplication.qgisSettingsDirPath(), 'python', 'plugins')
        if os.path.exists(user_plugin_dir):
            self.plugin_dirs.append(user_plugin_dir)
        
        # System plugins directory
        system_plugin_dir = os.path.join(QgsApplication.prefixPath(), 'python', 'plugins')
        if os.path.exists(system_plugin_dir):
            self.plugin_dirs.append(system_plugin_dir)
        
        # Add custom plugin directory if provided
        if custom_plugin_dir and os.path.exists(custom_plugin_dir):
            if custom_plugin_dir not in self.plugin_dirs:
                self.plugin_dirs.append(custom_plugin_dir)
        else:
            # Use default OSGeo directory as a fallback
            default_plugin_dir = r'C:\OSGeo4W\apps\qgis\python\plugins'
            if os.path.exists(default_plugin_dir) and default_plugin_dir not in self.plugin_dirs:
                self.plugin_dirs.append(default_plugin_dir)
        
    def set_prefix(self, prefix):
        """Set the organization prefix
        
        Args:
            prefix (str): Organization prefix
        """
        self.org_prefix = prefix
        
    def get_matching_plugins(self):
        """Get plugins matching the organization prefix"""
        if not self.org_prefix:
            logger.warning("No organization prefix specified")
            return []
        
        matching_plugins = []
        seen_plugin_paths = set()  # Use a set to track unique paths
        
        logger.info(f"Scanning for plugins with prefix: '{self.org_prefix}'")
        logger.info(f"Plugin directories to scan: {self.plugin_dirs}")
        
        # Loop through all plugin directories
        for plugin_dir in self.plugin_dirs:
            if not os.path.exists(plugin_dir):
                logger.warning(f"Plugin directory doesn't exist: {plugin_dir}")
                continue
            
            logger.info(f"Scanning directory: {plugin_dir}")
            
            # Loop through plugin directories
            for plugin_name in os.listdir(plugin_dir):
                logger.debug(f"Found plugin: {plugin_name}")
                if plugin_name.startswith(self.org_prefix):
                    plugin_path = os.path.normpath(os.path.join(plugin_dir, plugin_name))
                    
                    # Skip if we've already seen this normalized path
                    if plugin_path in seen_plugin_paths:
                        logger.debug(f"Skipping duplicate plugin path: {plugin_path}")
                        continue
                    
                    seen_plugin_paths.add(plugin_path)
                    logger.info(f"Found matching plugin: {plugin_name} at {plugin_path}")
                    
                    # Verify it's a directory and has a metadata.txt file
                    metadata_path = os.path.join(plugin_path, 'metadata.txt')
                    if os.path.isdir(plugin_path) and os.path.exists(metadata_path):
                        logger.info(f"Plugin {plugin_name} has valid metadata")
                        matching_plugins.append({
                            'name': plugin_name,
                            'path': plugin_path,
                            'metadata': self._read_metadata(plugin_path)
                        })
                    else:
                        logger.warning(f"Plugin {plugin_name} is missing metadata or not a directory")
                        
        logger.info(f"Found {len(matching_plugins)} unique matching plugins")
        return matching_plugins
        
    def _read_metadata(self, plugin_path):
        """Read plugin metadata
        
        Args:
            plugin_path (str): Path to the plugin directory
            
        Returns:
            dict: Plugin metadata
        """
        metadata_path = os.path.join(plugin_path, 'metadata.txt')
        metadata = {}
        
        if os.path.exists(metadata_path):
            config = configparser.ConfigParser()
            config.read(metadata_path)
            
            if 'general' in config:
                for key, value in config['general'].items():
                    metadata[key] = value
                    
        return metadata
        
    def get_plugin_version(self, plugin_name):
        """Get the version of a plugin
        
        Args:
            plugin_name (str): Name of the plugin
            
        Returns:
            str: Plugin version or None if not found
        """
        plugin_path = os.path.join(self.plugin_dir, plugin_name)
        metadata = self._read_metadata(plugin_path)
        
        return metadata.get('version')