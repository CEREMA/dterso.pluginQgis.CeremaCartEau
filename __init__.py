# -*- coding: utf-8 -*-
"""
/***************************************************************************
__init__
                                 A QGIS plugin
 Cart'Eau Plugin Cerema
                             -------------------
        begin                : 2015-10-06
        modification         : 2018-07-09
        copyright            : (C) 2018 by Christelle Bosc & Christophe Bez
                                                           & Gilles Fouvet
        email                : Christelle.Bosc@cerema.fr
        git sha              : $Format:%H$
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
 This script initializes the plugin, making it known to QGIS.
"""


# noinspection PyPep8Naming
def classFactory(iface):  # pylint: disable=invalid-name
    """Load CeremaCartEau class from file main.py

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from main import CeremaCartEau
    return CeremaCartEau(iface)
