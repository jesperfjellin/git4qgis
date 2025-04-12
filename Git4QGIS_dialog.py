# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Git4QGISDialog
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

import os

from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import QDialog, QVBoxLayout, QLabel, QLineEdit, QCheckBox, QDialogButtonBox, QGroupBox, QPushButton, QHBoxLayout, QFileDialog

class Git4QGISDialog(QDialog):
    def __init__(self, parent=None):
        """Constructor."""
        super(Git4QGISDialog, self).__init__(parent)
        
        # Create the dialog manually since we don't have a .ui file yet
        self.setWindowTitle("Git4QGIS Settings")
        self.resize(400, 300)
        
        self.layout = QVBoxLayout()
        
        # Run on startup checkbox
        self.cbRunOnStartup = QCheckBox("Run on QGIS startup")
        self.layout.addWidget(self.cbRunOnStartup)
        
        # Organization prefix
        self.layout.addWidget(QLabel("Organization Prefix:"))
        self.txtOrgPrefix = QLineEdit()
        self.txtOrgPrefix.setPlaceholderText("e.g., MyOrganization_")
        self.layout.addWidget(self.txtOrgPrefix)
        
        # GitHub Repository
        self.layout.addWidget(QLabel("GitHub Repository URL:"))
        self.txtGithubRepo = QLineEdit()
        self.txtGithubRepo.setPlaceholderText("e.g., https://github.com/yourusername/repo")
        self.layout.addWidget(self.txtGithubRepo)
        
        # Check for updates now
        self.cbCheckNow = QCheckBox("Check for updates now")
        self.layout.addWidget(self.cbCheckNow)
        
        # GitHub Authentication Group
        authGroup = QGroupBox("GitHub Authentication (for private repositories)")
        authLayout = QVBoxLayout()
        
        # GitHub Username
        authLayout.addWidget(QLabel("GitHub Username:"))
        self.txtGithubUsername = QLineEdit()
        self.txtGithubUsername.setPlaceholderText("Your GitHub username")
        authLayout.addWidget(self.txtGithubUsername)
        
        # Replace the existing GitHub Token section with:
        tokenLabel = QLabel("Fine-grained Personal Access Token:")
        authLayout.addWidget(tokenLabel)
        self.txtGithubToken = QLineEdit()
        self.txtGithubToken.setPlaceholderText("PAT for private repositories")
        self.txtGithubToken.setEchoMode(QLineEdit.Password)
        authLayout.addWidget(self.txtGithubToken)
        
        # Add token help text
        tokenHelp = QLabel(
            "Create a token at: github.com/settings/tokens?type=beta\n"
            "Required permissions: Contents (read-only)"
        )
        tokenHelp.setWordWrap(True)
        authLayout.addWidget(tokenHelp)
        
        authGroup.setLayout(authLayout)
        self.layout.addWidget(authGroup)
        
        # Git Executable Path
        self.layout.addWidget(QLabel("Git Executable Path:"))
        self.txtGitPath = QLineEdit()
        self.txtGitPath.setPlaceholderText(r"C:\Program Files\Git\bin\git.exe")
        browse_button = QPushButton("Browse...")
        browse_button.clicked.connect(self.browse_git_executable)
        browse_layout = QHBoxLayout()
        browse_layout.addWidget(self.txtGitPath)
        browse_layout.addWidget(browse_button)
        self.layout.addLayout(browse_layout)
        
        # Plugin Directory Path
        self.layout.addWidget(QLabel("QGIS Plugin Directory:"))
        self.txtPluginDir = QLineEdit()
        self.txtPluginDir.setPlaceholderText(r"C:\OSGeo4W\apps\qgis\python\plugins")
        plugin_browse_button = QPushButton("Browse...")
        plugin_browse_button.clicked.connect(self.browse_plugin_directory)
        plugin_browse_layout = QHBoxLayout()
        plugin_browse_layout.addWidget(self.txtPluginDir)
        plugin_browse_layout.addWidget(plugin_browse_button)
        self.layout.addLayout(plugin_browse_layout)
        
        # Button box
        self.buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        self.layout.addWidget(self.buttonBox)
        
        self.setLayout(self.layout)

    def browse_git_executable(self):
        """Open file dialog to select git executable"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            "Select Git Executable", 
            "", 
            "Executable Files (*.exe);;All Files (*)"
        )
        if file_path:
            self.txtGitPath.setText(file_path)

    def browse_plugin_directory(self):
        """Open directory dialog to select plugin directory"""
        dir_path = QFileDialog.getExistingDirectory(
            self,
            "Select QGIS Plugin Directory",
            self.txtPluginDir.text() or r"C:\OSGeo4W\apps\qgis\python\plugins"
        )
        if dir_path:
            self.txtPluginDir.setText(dir_path)