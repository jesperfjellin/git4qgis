# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Git4QGIS
                                 A QGIS plugin
 Automatically sync QGIS plugins with GitHub repositories
                              -------------------
        begin                : 2023
        copyright            : (C) 2023
        email                : your.email@example.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

import os.path
import configparser
import logging
import sys
import traceback
import base64
import ctypes
from ctypes import wintypes

from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction, QMessageBox
from qgis.core import Qgis, QgsApplication
from qgis.utils import reloadPlugin, loadPlugin, unloadPlugin, updateAvailablePlugins

# Initialize Qt resources from file resources.py
# from .resources import *
# Import the code for the dialog
from .Git4QGIS_dialog import Git4QGISDialog
from .github_api import GitHubAPI
from .plugin_scanner import PluginScanner
from .git_sync import GitSync

# Load Windows DPAPI functions
crypt32 = ctypes.WinDLL('crypt32.dll')
cryptprotect = crypt32.CryptProtectData
cryptunprotect = crypt32.CryptUnprotectData

# DPAPI data structure
class DATA_BLOB(ctypes.Structure):
    _fields_ = [('cbData', wintypes.DWORD),
                ('pbData', ctypes.POINTER(ctypes.c_char))]

def encrypt_data(data):
    """Encrypt data using Windows DPAPI"""
    if not data:
        return None
        
    data_in = DATA_BLOB()
    data_out = DATA_BLOB()
    
    # Convert string to bytes if necessary
    if isinstance(data, str):
        data = data.encode('utf-8')
    
    # Set up input blob
    buffer = ctypes.create_string_buffer(data)
    data_in.pbData = ctypes.cast(buffer, ctypes.POINTER(ctypes.c_char))
    data_in.cbData = len(data)
    
    # Encrypt
    if cryptprotect(ctypes.byref(data_in), None, None, None, None, 0, ctypes.byref(data_out)):
        encrypted_len = int(data_out.cbData)
        encrypted_buffer = ctypes.string_at(data_out.pbData, encrypted_len)
        # Free the memory
        ctypes.windll.kernel32.LocalFree(data_out.pbData)
        # Convert to base64 for string storage
        return base64.b64encode(encrypted_buffer).decode('utf-8')
    return None

def decrypt_data(encrypted_data):
    """Decrypt data using Windows DPAPI"""
    if not encrypted_data:
        return None
        
    # Decode from base64
    try:
        encrypted_bytes = base64.b64decode(encrypted_data)
    except:
        return None
    
    data_in = DATA_BLOB()
    data_out = DATA_BLOB()
    
    # Set up input blob
    buffer = ctypes.create_string_buffer(encrypted_bytes)
    data_in.pbData = ctypes.cast(buffer, ctypes.POINTER(ctypes.c_char))
    data_in.cbData = len(encrypted_bytes)
    
    # Decrypt
    if cryptunprotect(ctypes.byref(data_in), None, None, None, None, 0, ctypes.byref(data_out)):
        decrypted_len = int(data_out.cbData)
        decrypted_buffer = ctypes.string_at(data_out.pbData, decrypted_len)
        # Free the memory
        ctypes.windll.kernel32.LocalFree(data_out.pbData)
        return decrypted_buffer.decode('utf-8')
    return None

# Create a logger with an absolute path to ensure we can write to it
try:
    log_dir = os.path.join(os.path.expanduser('~'), 'Git4QGIS_logs')
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, 'git4qgis_debug.log')
    
    # Print the log location to help find it
    print(f"Git4QGIS log file: {log_file}")
    
    # Setup file logging
    file_handler = logging.FileHandler(log_file, mode='w')
    file_handler.setLevel(logging.DEBUG)
    
    # Setup console logging too
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    
    # Format for both handlers
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # Create logger and add handlers
    logger = logging.getLogger('Git4QGIS')
    logger.setLevel(logging.DEBUG)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    # Log startup message
    logger.info("Git4QGIS plugin started")
    
except Exception as e:
    # Last resort - print the error
    print(f"Failed to set up logging: {str(e)}")
    traceback.print_exc()

class Git4QGISPlugin:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        try:
            # Save reference to the QGIS interface
            self.iface = iface
            logger.info("Git4QGIS plugin initializing")
            
            # initialize plugin directory
            self.plugin_dir = os.path.dirname(__file__)
            # initialize locale
            locale = QSettings().value('locale/userLocale')[0:2]
            locale_path = os.path.join(
                self.plugin_dir,
                'i18n',
                'Git4QGIS_{}.qm'.format(locale))

            if os.path.exists(locale_path):
                self.translator = QTranslator()
                self.translator.load(locale_path)
                QCoreApplication.installTranslator(self.translator)

            # Declare instance attributes
            self.actions = []
            self.menu = 'Git4QGIS'
            self.toolbar = self.iface.addToolBar('Git4QGIS')
            self.toolbar.setObjectName('Git4QGIS')
            
            # Load settings
            self.settings = QSettings()
            self.run_on_startup = self.settings.value("Git4QGIS/run_on_startup", False, type=bool)
            self.org_prefix = self.settings.value("Git4QGIS/org_prefix", "", type=str)
            self.github_repo = self.settings.value("Git4QGIS/github_repo", "", type=str)
            self.github_token = self.settings.value("Git4QGIS/github_token", "", type=str)
            self.github_username = self.settings.value("Git4QGIS/github_username", "", type=str)
            self.git_path = self.settings.value("Git4QGIS/git_path", r"C:\Program Files\Git\bin\git.exe", type=str)
            self.plugin_dir_path = self.settings.value("Git4QGIS/plugin_dir_path", r"C:\OSGeo4W\apps\qgis\python\plugins", type=str)
            
            # Clean up any leftover backup directories
            git_sync = GitSync()
            
            # Check if we should run on startup
            if self.run_on_startup:
                logger.info("Running on startup enabled, checking for updates")
                self.check_for_updates()
            
        except Exception as e:
            logger.error(f"Error initializing plugin: {str(e)}")
            logger.error(traceback.format_exc())

    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            self.toolbar.addAction(action)

        if add_to_menu:
            self.iface.addPluginToMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = os.path.join(self.plugin_dir, 'icon.png')
        self.add_action(
            icon_path,
            text='Git4QGIS',
            callback=self.run,
            parent=self.iface.mainWindow())

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                'Git4QGIS',
                action)
            self.iface.removeToolBarIcon(action)
        # remove the toolbar
        del self.toolbar

    def run(self):
        """Run method that performs all the real work"""
        # Create the dialog with elements (after translation) and keep reference
        # Only create GUI ONCE in callback
        if not hasattr(self, 'dlg'):
            self.dlg = Git4QGISDialog()
            # Connect the dialog signals
            self.dlg.buttonBox.accepted.connect(self.save_settings)
            
        # Load current settings into dialog
        self.dlg.cbRunOnStartup.setChecked(self.run_on_startup)
        self.dlg.txtOrgPrefix.setText(self.org_prefix)
        self.dlg.txtGithubRepo.setText(self.github_repo)
        self.dlg.txtGithubToken.setText(self.github_token)
        self.dlg.txtGithubUsername.setText(self.github_username)
        self.dlg.txtGitPath.setText(self.git_path)
        self.dlg.txtPluginDir.setText(self.plugin_dir_path)
        
        # show the dialog
        self.dlg.show()
        # Run the dialog event loop
        result = self.dlg.exec_()
        
    def save_settings(self):
        """Save plugin settings"""
        self.run_on_startup = self.dlg.cbRunOnStartup.isChecked()
        self.org_prefix = self.dlg.txtOrgPrefix.text()
        self.github_repo = self.dlg.txtGithubRepo.text()
        self.github_username = self.dlg.txtGithubUsername.text()
        self.git_path = self.dlg.txtGitPath.text()
        self.plugin_dir_path = self.dlg.txtPluginDir.text()
        
        # Encrypt the token before storing
        token = self.dlg.txtGithubToken.text()
        encrypted_token = encrypt_data(token) if token else ""
        
        # Save to QSettings
        self.settings.setValue("Git4QGIS/run_on_startup", self.run_on_startup)
        self.settings.setValue("Git4QGIS/org_prefix", self.org_prefix)
        self.settings.setValue("Git4QGIS/github_repo", self.github_repo)
        self.settings.setValue("Git4QGIS/github_username", self.github_username)
        self.settings.setValue("Git4QGIS/github_token_encrypted", encrypted_token)
        self.settings.setValue("Git4QGIS/git_path", self.git_path)
        self.settings.setValue("Git4QGIS/plugin_dir_path", self.plugin_dir_path)
        
        # Check for updates if requested
        if self.dlg.cbCheckNow.isChecked():
            self.check_for_updates()
    
    def check_for_updates(self):
        """Check for plugin updates from GitHub"""
        try:
            logger.info("Checking for updates")
            
            if not self.org_prefix:
                logger.warning("No organization prefix set")
                self.iface.messageBar().pushMessage(
                    "Git4QGIS", 
                    "No organization prefix set. Please configure in settings.", 
                    level=Qgis.Warning
                )
                return
            
            if not self.github_repo:
                logger.warning("No GitHub repository set")
                self.iface.messageBar().pushMessage(
                    "Git4QGIS", 
                    "No GitHub repository set. Please configure in settings.", 
                    level=Qgis.Warning
                )
                return
            
            # Log settings
            logger.info(f"Settings - Prefix: '{self.org_prefix}', Repo: '{self.github_repo}'")
            
            # Check if git is installed
            logger.info("Checking if Git is installed")
            git_sync = GitSync(custom_git_path=self.git_path)
            logger.info("GitSync initialized")
            
            if not git_sync.is_git_installed():
                logger.error("Git is not installed or not found")
                self.iface.messageBar().pushMessage(
                    "Git4QGIS", 
                    "Git is not installed. Please install Git to use this plugin.", 
                    level=Qgis.Critical
                )
                return
            
            logger.info("Git is installed")
            
            # Initialize GitHub API
            logger.info("Initializing GitHub API")
            encrypted_token = self.settings.value("Git4QGIS/github_token_encrypted", "", type=str)
            token = decrypt_data(encrypted_token) if encrypted_token else ""
            github_api = GitHubAPI(token=token)
            logger.info("GitHub API initialized")
            
            # Initialize Plugin Scanner
            logger.info("Initializing Plugin Scanner")
            scanner = PluginScanner(self.org_prefix, custom_plugin_dir=self.plugin_dir_path)
            logger.info(f"Plugin Scanner initialized with prefix: {self.org_prefix} and custom directory: {self.plugin_dir_path}")
            
            # Find plugins matching the prefix
            logger.info("Searching for matching plugins")
            matching_plugins = scanner.get_matching_plugins()
            logger.info(f"Found {len(matching_plugins)} matching plugins: {[p['name'] for p in matching_plugins]}")
            
            if not matching_plugins:
                logger.warning(f"No plugins found with prefix '{self.org_prefix}'")
                self.iface.messageBar().pushMessage(
                    "Git4QGIS", 
                    f"No plugins found with prefix '{self.org_prefix}'", 
                    level=Qgis.Info
                )
                return
            
            # Parse GitHub repository URL
            owner, repo = github_api.parse_github_url(self.github_repo)
            if not owner or not repo:
                self.iface.messageBar().pushMessage(
                    "Git4QGIS", 
                    "Invalid GitHub repository URL", 
                    level=Qgis.Warning
                )
                return
            
            # Check for updates for each plugin
            updated_plugins = []
            for plugin in matching_plugins:
                plugin_name = plugin['name']
                plugin_path = plugin['path']
                current_version = plugin['metadata'].get('version', '0.0.0')
                
                try:
                    # CHANGE THIS PART
                    # Don't add the plugin name to the repo URL
                    # Just use the GitHub repo URL directly
                    repo_url = self.github_repo
                    
                    # Log what we're doing
                    logger.info(f"Checking repository {repo_url} for updates to plugin {plugin_name} (v{current_version})")
                    
                    # Get remote version
                    remote_version = git_sync.get_remote_version(
                        repo_url, 
                        plugin_path, 
                        username=self.github_username, 
                        token=token
                    )
                    
                    if remote_version:
                        logger.info(f"Remote version: {remote_version}, Local version: {current_version}")
                        
                        if remote_version != current_version:
                            # Update the plugin
                            logger.info(f"Updating {plugin_name} from v{current_version} to v{remote_version}")
                            if git_sync.update_plugin(
                                repo_url, 
                                plugin_path, 
                                username=self.github_username, 
                                token=token
                            ):
                                updated_plugins.append(plugin_name)
                                logger.info(f"Successfully updated {plugin_name}")
                                
                                # Reload the plugin in QGIS
                                try:
                                    logger.info(f"Attempting to reload plugin {plugin_name}")

                                    
                                    # First try to unload the plugin if it's loaded
                                    unloadPlugin(plugin_name)
                                    
                                    # Update the plugins registry
                                    updateAvailablePlugins()
                                    
                                    # Load the updated plugin
                                    loadPlugin(plugin_name)
                                    logger.info(f"Plugin {plugin_name} reloaded successfully")
                                    
                                    # Inform the user
                                    self.iface.messageBar().pushMessage(
                                        "Git4QGIS", 
                                        f"Plugin {plugin_name} updated to version {remote_version} and reloaded", 
                                        level=Qgis.Success,
                                        duration=5
                                    )
                                except Exception as e:
                                    logger.warning(f"Could not automatically reload plugin: {str(e)}")
                                    # Inform the user they may need to restart QGIS
                                    self.iface.messageBar().pushMessage(
                                        "Git4QGIS", 
                                        f"Plugin {plugin_name} updated to version {remote_version}. Please restart QGIS to use the new version.", 
                                        level=Qgis.Warning,
                                        duration=10
                                    )
                        else:
                            logger.info(f"Plugin {plugin_name} is up to date (v{current_version})")
                    else:
                        logger.warning(f"Could not determine remote version for {plugin_name}")
                except Exception as e:
                    logger.error(f"Error updating {plugin_name}: {str(e)}")
                    logger.error(traceback.format_exc())
                    self.iface.messageBar().pushMessage(
                        "Git4QGIS", 
                        f"Error updating {plugin_name}: {str(e)}", 
                        level=Qgis.Warning
                    )
            
            # Report results
            if updated_plugins:
                self.iface.messageBar().pushMessage(
                    "Git4QGIS", 
                    f"Updated {len(updated_plugins)} plugins: {', '.join(updated_plugins)}", 
                    level=Qgis.Success
                )
            else:
                self.iface.messageBar().pushMessage(
                    "Git4QGIS", 
                    "All plugins are up to date", 
                    level=Qgis.Info
                )
            
        except Exception as e:
            logger.error(f"Error in check_for_updates: {str(e)}")
            logger.error(traceback.format_exc())
            self.iface.messageBar().pushMessage(
                "Git4QGIS", 
                f"Error checking for updates: {str(e)}", 
                level=Qgis.Critical
            )