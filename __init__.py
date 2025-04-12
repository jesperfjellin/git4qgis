# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Git4QGIS
                                 A QGIS plugin
 Automatically sync QGIS plugins with GitHub repositories
                             -------------------
        begin                : 2025
        copyright            : (C) 2025
        email                : jesperfjellin@gmail.com
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


def classFactory(iface):
    """Load the Git4QGIS plugin class.
    
    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    from .Git4QGIS import Git4QGISPlugin
    return Git4QGISPlugin(iface)
