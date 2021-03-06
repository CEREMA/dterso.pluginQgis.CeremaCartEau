# -*- coding: utf-8 -*-
"""
/***************************************************************************
 doCartEauDialog
                                 A QGIS plugin
 Cart'Eau  Plugin Cerema
                             -------------------
        begin                : 2015-10-06
        modification         : 2018-07-09
        git sha              : $Format:%H$
        copyright            : (C) 2018 by Christelle Bosc & Gilles Fouvet 
                                                           
        email                : Christelle.Bosc@cerema.fr
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

from PyQt4 import QtGui, uic

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'cartEauDialog.ui'))

class CeremaCartEauDialog(QtGui.QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        """Constructor."""
        super(CeremaCartEauDialog, self).__init__(parent)
        # Set up the user interface from Designer.
        # After setupUI you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)
