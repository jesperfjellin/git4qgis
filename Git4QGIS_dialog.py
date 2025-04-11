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
from qgis.PyQt.QtWidgets import QDialog, QVBoxLayout, QLabel, QLineEdit, QCheckBox, QDialogButtonBox

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
        
        # GitHub Token
        self.layout.addWidget(QLabel("GitHub Token (optional):"))
        self.txtGithubToken = QLineEdit()
        self.txtGithubToken.setPlaceholderText("Personal access token for private repositories")
        self.txtGithubToken.setEchoMode(QLineEdit.Password)
        self.layout.addWidget(self.txtGithubToken)
        
        # Button box
        self.buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        self.layout.addWidget(self.buttonBox)
        
        self.setLayout(self.layout)