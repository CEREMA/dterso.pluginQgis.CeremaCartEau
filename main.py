# -*- coding: utf-8 -*-
"""
/***************************************************************************
 main
                                 A QGIS plugin
 Cart'Eau. Plugin Cerema.
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

from PyQt4.QtCore import QSettings, QTranslator, qVersion, QCoreApplication
from PyQt4.QtGui import QAction, QIcon, QFileDialog, QMessageBox, QMenu, QImage, QPixmap, QLabel
from qgis.core import *
import os
import os.path
import platform
# Initialize Qt resources from file resources.py
import resources
# Import the code for the dialog
from doCartEauDialog import CeremaCartEauDialog
from doConfigurationDialog import CeremaConfigurationDialog
from doAssemblyDialog import CeremaAssemblyDialog
from tools import *
from treatment import *

#########################################################################
# CLASS CeremaCartEau                                                   #
#########################################################################
class CeremaCartEau:
    ### QGIS Plugin Implementation. ###

    #########################################################################
    # FONCTION __init__()                                                   #
    #########################################################################
    def __init__(self, iface):
        # Constructor.
        #
        # param iface: An interface instance that will be passed to this class
        #    which provides the hook by which you can manipulate the QGIS
        #    application at run time.
        # type iface: QgsInterface

        CHANNEL_LIST = ("Bande 1", "Bande 2", "Bande 3", "Bande 4", "Bande 5", "Bande 6", "Bande 7", "Bande 8", "Bande 9", "Bande 10", "Bande 11", "Bande 12", "Bande 13")
        
        # Save reference to the QGIS interface
        self.iface = iface
        # Initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # Initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'CeremaCartEau_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

        # Create the dialog (after translation) and keep reference
        self.dlg = CeremaCartEauDialog()
        self.conf = CeremaConfigurationDialog()
        self.assb = CeremaAssemblyDialog()

        self.testRasterValMinValMax = True
        
        self.fromActiveLayerRaster = True
        self.fromActiveLayerVector = True
        self.fromActiveLayerAssembled = True
        self.layersName = {}
        self.dir_dest = ""
        self.dir_raster_src = ""

        self.seuilMin = -1.0
        self.seuilMax = +1.0
        self.seuil = 0.0
        self.seuilStr = ''
        self.dlg.seuil.setText(str(self.seuil))

        # Liaison signaux / slots
        self.dlg.btInitScript.clicked.connect(self.initScript)
        self.dlg.btConfiguration.clicked.connect(self.btConfigurationClicked)
        self.dlg.btAbout.clicked.connect(self.btAboutClicked)
        self.dlg.btInfo.clicked.connect(self.btInfoClicked)
        self.conf.buttonBox.accepted.connect(self.closeConfClicked)
        self.conf.buttonBox.rejected.connect(self.cancelConfClicked)
        self.assb.buttonBox.accepted.connect(self.closeAssemblyClicked)
        self.assb.buttonBox.rejected.connect(self.cancelAssemblyClicked)
        self.dlg.btSeuiller.clicked.connect(self.seuillerClicked)
        self.dlg.btValider.clicked.connect(self.validerSeuillageClicked)
        self.dlg.btFilter.clicked.connect(self.filtrerClicked)
        self.dlg.btVectoriser.clicked.connect(self.vectoriserClicked)
        self.dlg.seuilSlider.valueChanged.connect(lambda: self.updateSeuil(self.dlg.seuilSlider.value() / 10000.0))
        self.dlg.seuil.textChanged.connect(lambda: self.updateSlider(self.dlg.seuil.text()))
        self.dlg.delta.textChanged.connect(self.onDeltaChange)
        self.dlg.seuilTamiser.textChanged.connect(self.onSeuilTamiserChange)
        self.dlg.seuilCMR.textChanged.connect(self.onSeuilCMRChange)
        self.dlg.rbComputeNdvi.toggled.connect(self.onrbcomputeNdviChange)
        self.dlg.rbComputeNdwi2.toggled.connect(self.onrbcomputeNdwi2Change)
        self.dlg.rbComputeNone.toggled.connect(self.onrbcomputeNoneChange)
        self.dlg.rbDespeckLee.toggled.connect(self.onrbDespeckLeeChange)
        self.dlg.rbDespeckGamma.toggled.connect(self.onrbDespeckGammaChange)
        self.dlg.rbDespeckNone.toggled.connect(self.onrbDespeckNoneChange)
        self.dlg.rbSeuil.toggled.connect(self.onrbSeuilChange)

        self.dlg.btClose.clicked.connect(self.quit)
        self.dlg.clayer_raster.currentIndexChanged.connect(lambda: self.updateRasterPath(self.dlg.clayer_raster.currentText()))
        self.assb.clayer_vector.currentIndexChanged.connect(lambda: self.updateVectorPath(self.assb.clayer_vector.currentText()))
        self.assb.clayer_assembled.currentIndexChanged.connect(lambda: self.updateAssembledPath(self.assb.clayer_assembled.currentText()))

        self.dlg.btReload_raster.clicked.connect(self.reloadComboLayersRaster)
        self.dlg.btDir_raster.clicked.connect(self.btDirRasterClicked)
        self.dlg.btDel_raster.clicked.connect(self.btDelRasterClicked)

        self.assb.btReload_vector.clicked.connect(self.reloadComboLayersVector)
        self.assb.btDir_vector.clicked.connect(self.btDirVectorClicked)
        self.assb.btDel_vector.clicked.connect(self.btDelVectorClicked)
        self.assb.btDel_dir_src.clicked.connect(self.btDelDirSrcClicked)
        self.assb.btDir_dir_src.clicked.connect(self.btDirDirSrcClicked)
        self.assb.btDel_assembled.clicked.connect(self.btDelAssembledClicked)
        self.assb.btReload_assembled.clicked.connect(self.reloadComboLayersAssembled)
        self.assb.btDir_assembled.clicked.connect(self.btDirAssembledClicked)

        self.dlg.btAssembler.clicked.connect(self.btAssemblerClicked)
        self.dlg.btDel_dir_dest.clicked.connect(self.btDelDirDestClicked)
        self.dlg.btDir_dir_dest.clicked.connect(self.btDirDirDestClicked)

        # Configuration DiaolgBox
        self.conf.rbQGIS.toggled.connect(self.onrbQGISChange)
        self.conf.rbOTB.toggled.connect(self.onrbOTBChange)
        self.conf.rbOptique.toggled.connect(self.onrbOptiqueChange)
        self.conf.rbRadar.toggled.connect(self.onrbRadarChange)
        self.conf.channelOrderDic = {"Red":1, "Green":2, "Blue":3, "NIR":4}

        for i in range(len(CHANNEL_LIST)): self.conf.cbRed.addItem(CHANNEL_LIST[i])
        self.conf.cbRed.currentIndexChanged.connect(lambda: self.updateConfBand(self.conf.cbRed.currentText(),1))
        self.conf.cbRed.setCurrentIndex(0)
        for i in range(len(CHANNEL_LIST)): self.conf.cbGreen.addItem(CHANNEL_LIST[i])
        self.conf.cbGreen.currentIndexChanged.connect(lambda: self.updateConfBand(self.conf.cbGreen.currentText(),2))
        self.conf.cbGreen.setCurrentIndex(1)
        for i in range(len(CHANNEL_LIST)): self.conf.cbBlue.addItem(CHANNEL_LIST[i])
        self.conf.cbBlue.currentIndexChanged.connect(lambda: self.updateConfBand(self.conf.cbBlue.currentText(),3))
        self.conf.cbBlue.setCurrentIndex(2)
        for i in range(len(CHANNEL_LIST)): self.conf.cbNIR.addItem(CHANNEL_LIST[i])
        self.conf.cbNIR.currentIndexChanged.connect(lambda: self.updateConfBand(self.conf.cbNIR.currentText(),4))
        self.conf.cbNIR.setCurrentIndex(3)

        # Init Configuration
        self.conf.rbQGIS.setChecked(True)
        self.conf.rbOTB.setChecked(False)
        self.conf.rbOptique.setChecked(True)
        self.conf.rbRadar.setChecked(False)

        self.dlg.spinBoxRadius.setSingleStep(1)
        self.dlg.spinBoxRadius.setValue(1)
        self.dlg.spinBoxRadius.setMinimum(-1000)
        self.dlg.spinBoxRadius.setMaximum(+1000)
        self.dlg.doubleSpinBoxLooks.setSingleStep(0.1)
        self.dlg.doubleSpinBoxLooks.setValue(1.0)
        self.dlg.doubleSpinBoxLooks.setMinimum(-1000)
        self.dlg.doubleSpinBoxLooks.setMaximum(+1000)
        self.dlg.seuil.setReadOnly(False)

        # Declare instance attributes
        self.actions = []

        # We are going to let the user set this up in a future iteration
        self.toolBarName = self.tr(u'&Cerema Zones Immergées')
        self.menu = QMenu(self.toolBarName)
        self.menuBar = self.iface.mainWindow().menuBar()
        self.toolbar = self.iface.addToolBar(self.toolBarName)
        self.toolbar.setObjectName(self.toolBarName)

        self.home = os.path.expanduser("~")
        return

    #########################################################################
    # FONCTION tr()     noinspection PyMethodMayBeStatic                    #
    #########################################################################
    def tr(self, message):
        # Get the translation for a string using Qt translation API.
        #
        # We implement this ourselves since we do not inherit QObject.
        #
        # param message: String for translation.
        # type message: str, QString
        #
        # returns: Translated version of message.
        # rtype: QString

        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('CeremaCartEau', message)

    #########################################################################
    # FONCTION add_action()                                                 #
    #########################################################################
    def add_action(
        self,
        icon_path,
        text,
        name,
        callback,
        enabled_flag = True,
        add_to_menu = True,
        add_to_toolbar = True,
        status_tip = None,
        whats_this = None,
        parent = None):

        # Add a toolbar icon to the toolbar.
        #
        # param icon_path: Path to the icon for this action. Can be a resource
        #    path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        # type icon_path: str
        #
        # param text: Text that should be shown in menu items for this action.
        # type text: str
        #
        # param name: Name that should be shown in menu items for this action.
        # type text: str
        #
        # param callback: Function to be called when the action is triggered.
        # type callback: function
        #
        # param enabled_flag: A flag indicating if the action should be enabled
        #    by default. Defaults to True.
        # type enabled_flag: bool
        #
        # param add_to_menu: Flag indicating whether the action should also
        #    be added to the menu. Defaults to True.
        # type add_to_menu: bool
        #
        # param add_to_toolbar: Flag indicating whether the action should also
        #    be added to the toolbar. Defaults to True.
        # type add_to_toolbar: bool
        #
        # param status_tip: Optional text to show in a popup when mouse pointer
        #    hovers over the action.
        # type status_tip: str
        #
        # param parent: Parent widget for the new action. Defaults None.
        # type parent: QWidget
        #
        # param whats_this: Optional text to show in the status bar when the
        #    mouse pointer hovers over the action.
        #
        # returns: The action that was created. Note that the action is also
        #    added to self.actions list.
        # rtype: QAction

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.setText(text)
        action.setObjectName(name)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            self.toolbar.addAction(action)

        if add_to_menu:
            self.iface.addPluginToMenu(self.toolBarName,action)

        self.actions.append(action)

        return action

    #########################################################################
    # FONCTION initGui()                                                    #
    #########################################################################
    def initGui(self):
        # Create the menu entries and toolbar icons inside the QGIS GUI.
        #---------------------------------------------------------------
        icon_path = getThemeIcon("pictoinondation.png")

        self.add_action(
            icon_path,
            text = self.tr(u'Extraction des zones immergées'),
            name = u'Extraction des zones immergées',
            callback = self.run,
            parent = self.iface.mainWindow())
        return

    #########################################################################
    # FONCTION unload()                                                     #
    #########################################################################
    def unload(self):
        # Removes the plugin menu item and icon from QGIS GUI.
        #-----------------------------------------------------
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u"&Cerema Cart'Eau"),
                action)
            self.iface.removeToolBarIcon(action)
        # Remove the toolbar
        self.menu.deleteLater()
        self.toolbar.deleteLater()
        del self.toolbar
        return

    #########################################################################
    # FONCTION initIhm()                                                    #
    #########################################################################
    def initIhm(self):
        self.dlg.mess.clear()

        self.dlg.label_18.setVisible(True)
        self.dlg.label_13.setVisible(True)
        self.dlg.label_filter.setVisible(True)
        self.dlg.btValider.setVisible(True)
        self.dlg.btFilter.setVisible(True)
        self.dlg.btVectoriser.setVisible(True)

        # L'IHM est adaptée à la configuration "QGIS"
        self.dlg.seuilTamiser.setText('250')
        self.dlg.rbTamiser4.setChecked(True)
        if self.conf.rbQGIS.isChecked():
            self.dlg.lseuilTamiser.setVisible(True)
            self.dlg.seuilTamiser.setVisible(True)
            self.dlg.gBTamiser.setVisible(True)
            self.dlg.lconnTamiser.setVisible(True)
            self.dlg.rbTamiser4.setVisible(True)
            self.dlg.rbTamiser8.setVisible(True)

            self.dlg.lseuilCMR.setVisible(False)
            self.dlg.seuilCMR.setVisible(False)

        # L'IHM est adaptée à la configuration "OTB"
        self.dlg.seuilCMR.setText('1')
        if self.conf.rbOTB.isChecked() :
            self.dlg.lseuilCMR.setVisible(True)
            self.dlg.seuilCMR.setVisible(True)

            self.dlg.lseuilTamiser.setVisible(False)
            self.dlg.seuilTamiser.setVisible(False)
            self.dlg.gBTamiser.setVisible(False)
            self.dlg.lconnTamiser.setVisible(False)
            self.dlg.rbTamiser4.setVisible(False)
            self.dlg.rbTamiser8.setVisible(False)

        # L'IHM est adaptée à la configuration "Optique"
        if self.conf.rbOptique.isChecked():
            self.dlg.label_4.setVisible(True)
            self.dlg.label_5.setVisible(False)
            self.dlg.groupBox_optique.setVisible(True)
            self.dlg.groupBox_radar.setVisible(False)
            self.dlg.label_20.setVisible(False)
            self.dlg.label_21.setVisible(False)
            self.dlg.spinBoxRadius.setVisible(False)
            self.dlg.doubleSpinBoxLooks.setVisible(False)

        # L'IHM est adaptée à la configuration "Radar"
        if self.conf.rbRadar.isChecked() :
            self.dlg.label_4.setVisible(False)
            self.dlg.label_5.setVisible(True)
            self.dlg.groupBox_optique.setVisible(False)
            self.dlg.groupBox_radar.setVisible(True)
            self.dlg.label_20.setVisible(True)
            self.dlg.label_21.setVisible(True)
            self.dlg.spinBoxRadius.setVisible(True)
            self.dlg.doubleSpinBoxLooks.setVisible(True)

        self.dlg.rbComputeNdvi.setChecked(True)
        self.dlg.rbComputeNdwi2.setChecked(False)
        self.dlg.rbComputeNone.setChecked(False)
        self.dlg.rbDespeckLee.setChecked(False)
        self.dlg.rbDespeckGamma.setChecked(False)
        self.dlg.rbDespeckNone.setChecked(True)

        self.updateSeuil(self.seuil)
        self.updateSlider(self.seuil)

        # Activation et désativation de l'IHM à l'INIT
        if not self.dlg.rbSeuil.isChecked():
            self.dlg.label_19.setEnabled(False)
            self.dlg.delta.setEnabled(False)

        self.dlg.btValider.setEnabled(False)
        self.dlg.btFilter.setEnabled(False)
        self.dlg.btVectoriser.setEnabled(False)
        self.dlg.label_14.setEnabled(False)
        self.dlg.label_12.setEnabled(False)
        self.dlg.label_22.setEnabled(False)
        self.dlg.label_23.setEnabled(False)

        # Model pour ombré et grisée les texts
        # Dlg
        setStyleShadowQLabel(self.dlg.label_31)
        setStyleShadowQLabel(self.dlg.label_32)
        setStyleShadowQLabel(self.dlg.label_18)
        setStyleShadowQLabel(self.dlg.label_4)
        setStyleShadowQLabel(self.dlg.label_5)
        setStyleShadowQLabel(self.dlg.label_8)
        setStyleShadowQLabel(self.dlg.label_14)
        setStyleShadowQLabel(self.dlg.label_22)

        # Assb
        setStyleShadowQLabel(self.assb.label_29)
        setStyleShadowQLabel(self.assb.label_26)
        setStyleShadowQLabel(self.assb.label_31)

        # Conf
        setStyleShadowQLabel(self.conf.label_18)
        setStyleShadowQLabel(self.conf.label_21)
        setStyleShadowQLabel(self.conf.label_19)
        return

    #########################################################################
    # FONCTION lockGuiPart1()                                               #
    #########################################################################
    def lockGuiPart1(self):
        # On "gèle" l'interface pendant les traitements
        self.dlg.label_31.setEnabled(False)
        self.dlg.label_30.setEnabled(False)
        self.dlg.btAssembler.setEnabled(False)
        return

    #########################################################################
    # FONCTION unlockGuiPart1()                                             #
    #########################################################################
    def unlockGuiPart1(self):
        # Retour à la configuration normale de l'IHM
        self.dlg.label_31.setEnabled(True)
        self.dlg.label_30.setEnabled(True)
        self.dlg.btAssembler.setEnabled(True)
        return

    #########################################################################
    # FONCTION lockGuiPart2()                                               #
    #########################################################################
    def lockGuiPart2(self):
        # On "gèle" l'interface pendant les traitements
        self.dlg.label_32.setEnabled(False)
        self.dlg.label_35.setEnabled(False)
        self.dlg.clayer_dir_dest.setEnabled(False)
        self.dlg.btDel_dir_dest.setEnabled(False)
        self.dlg.btDir_dir_dest.setEnabled(False)
        self.dlg.label_18.setEnabled(False)
        self.dlg.label_17.setEnabled(False)
        self.dlg.clayer_raster.setEnabled(False)
        self.dlg.btDel_raster.setEnabled(False)
        self.dlg.btReload_raster.setEnabled(False)
        self.dlg.btDir_raster.setEnabled(False)
        return

    #########################################################################
    # FONCTION unlockGuiPart2()                                             #
    #########################################################################
    def unlockGuiPart2(self):
        # Retour à la configuration normale de l'IHM
        self.dlg.label_32.setEnabled(True)
        self.dlg.label_35.setEnabled(True)
        self.dlg.clayer_dir_dest.setEnabled(True)
        self.dlg.btDel_dir_dest.setEnabled(True)
        self.dlg.btDir_dir_dest.setEnabled(True)
        self.dlg.label_18.setEnabled(True)
        self.dlg.label_17.setEnabled(True)
        self.dlg.clayer_raster.setEnabled(True)
        self.dlg.btDel_raster.setEnabled(True)
        self.dlg.btReload_raster.setEnabled(True)
        self.dlg.btDir_raster.setEnabled(True)
        return

    #########################################################################
    # FONCTION lockGuiPart3()                                               #
    #########################################################################
    def lockGuiPart3(self):
        # On "gèle" l'interface pendant les traitements

        # L'IHM est adaptée à la configuration "Optique"
        self.dlg.label_4.setEnabled(False)
        self.dlg.label_9.setEnabled(False)
        self.dlg.rbComputeNdvi.setEnabled(False)
        self.dlg.rbComputeNdwi2.setEnabled(False)
        self.dlg.rbComputeNone.setEnabled(False)

        # L'IHM est adaptée à la configuration "Raster"
        self.dlg.label_5.setEnabled(False)
        self.dlg.rbDespeckLee.setEnabled(False)
        self.dlg.rbDespeckGamma.setEnabled(False)
        self.dlg.rbDespeckNone.setEnabled(False)
        self.dlg.spinBoxRadius.setEnabled(False)
        self.dlg.doubleSpinBoxLooks.setEnabled(False)

        self.dlg.label_8.setEnabled(False)
        self.dlg.label_15.setEnabled(False)
        self.dlg.seuilSlider.setEnabled(False)
        self.dlg.seuil.setEnabled(False)

        self.dlg.rbSeuil.setEnabled(False)
        self.dlg.delta.setEnabled(False)

        self.dlg.btSeuiller.setEnabled(False)
        self.dlg.btValider.setEnabled(False)
        return

    #########################################################################
    # FONCTION unlockGuiPart3()                                             #
    #########################################################################
    def unlockGuiPart3(self):
        # Retour à la configuration normale de l'IHM

        # L'IHM est adaptée à la configuration "Optique"
        self.dlg.label_4.setEnabled(True)
        self.dlg.label_9.setEnabled(True)
        self.dlg.rbComputeNdvi.setEnabled(True)
        self.dlg.rbComputeNdwi2.setEnabled(True)
        self.dlg.rbComputeNone.setEnabled(True)

        # L'IHM est adaptée à la configuration "Radar"
        self.dlg.label_5.setEnabled(True)
        self.dlg.rbDespeckLee.setEnabled(True)
        self.dlg.rbDespeckGamma.setEnabled(True)
        self.dlg.rbDespeckNone.setEnabled(True)
        self.dlg.spinBoxRadius.setEnabled(True)
        self.dlg.doubleSpinBoxLooks.setEnabled(True)

        self.dlg.label_8.setEnabled(True)
        self.dlg.label_15.setEnabled(True)
        self.dlg.seuilSlider.setEnabled(True)
        self.dlg.seuil.setEnabled(True)

        self.dlg.rbSeuil.setEnabled(True)
        self.dlg.delta.setEnabled(True)

        self.dlg.btSeuiller.setEnabled(True)
        self.dlg.btValider.setEnabled(True)
        return

    #########################################################################
    # FONCTION lockGuiPart4()                                               #
    #########################################################################
    def lockGuiPart4(self):
        # On "gèle" l'interface pendant les traitements
        self.dlg.label_14.setEnabled(False)
        self.dlg.label_12.setEnabled(False)
        self.dlg.btFilter.setEnabled(False)

        # L'IHM est adaptée à la configuration "QGIS"
        self.dlg.lseuilTamiser.setEnabled(False)
        self.dlg.seuilTamiser.setEnabled(False)
        self.dlg.gBTamiser.setEnabled(False)
        self.dlg.lconnTamiser.setEnabled(False)
        self.dlg.rbTamiser4.setEnabled(False)
        self.dlg.rbTamiser8.setEnabled(False)

        # L'IHM est adaptée à la configuration "OTB"
        self.dlg.lseuilCMR.setEnabled(False)
        self.dlg.seuilCMR.setEnabled(False)
        return

    #########################################################################
    # FONCTION unlockGuiPart4()                                             #
    #########################################################################
    def unlockGuiPart4(self):
        # Retour à la configuration normale de l'IHM
        self.dlg.label_14.setEnabled(True)
        self.dlg.label_12.setEnabled(True)
        self.dlg.btFilter.setEnabled(True)

        # L'IHM est adaptée à la configuration "QGIS"
        self.dlg.lseuilTamiser.setEnabled(True)
        self.dlg.seuilTamiser.setEnabled(True)
        self.dlg.gBTamiser.setEnabled(True)
        self.dlg.lconnTamiser.setEnabled(True)
        self.dlg.rbTamiser4.setEnabled(True)
        self.dlg.rbTamiser8.setEnabled(True)

        # L'IHM est adaptée à la configuration "OTB"
        self.dlg.lseuilCMR.setEnabled(True)
        self.dlg.seuilCMR.setEnabled(True)
        return

    #########################################################################
    # FONCTION lockGuiPart5()                                               #
    #########################################################################
    def lockGuiPart5(self):
        # On "gèle" l'interface pendant les traitements
        self.dlg.label_22.setEnabled(False)
        self.dlg.label_23.setEnabled(False)
        self.dlg.btVectoriser.setEnabled(False)
        return

    #########################################################################
    # FONCTION unlockGuiPart5()                                             #
    #########################################################################
    def unlockGuiPart5(self):
        # Retour à la configuration normale de l'IHM
        self.dlg.label_22.setEnabled(True)
        self.dlg.label_23.setEnabled(True)
        self.dlg.btVectoriser.setEnabled(True)
        return

    #########################################################################
    # FONCTION run()                                                        #
    #########################################################################
    def run(self):
        # Run method that performs all the real work
        #-------------------------------------------
        # Show the dialog
        # Initialisation de l'IHM
        self.initIhm()

        # Selecteur de couche raster
        self.dlg.clayer_raster.clear()
        layers = self.iface.legendInterface().layers()
        indexCoucheRaster = 0
        index = 0
        for layer in layers:
            if layer.type() == QgsMapLayer.RasterLayer and self.layersName != None:
                self.dlg.clayer_raster.addItem(layer.name())
                if 'raster' in self.layersName.keys() :
                    if layer.name() == self.layersName['raster']:
                        indexCoucheRaster = index
                index+=1
        self.dlg.clayer_raster.setCurrentIndex(indexCoucheRaster)

        # Selecteur de couche vecteur
        self.assb.clayer_vector.clear()
        layers = self.iface.legendInterface().layers()
        indexCoucheVector = 0
        index = 0
        for layer in layers:
            if layer.type() == QgsMapLayer.VectorLayer:
                self.assb.clayer_vector.addItem(layer.name())
                if 'emprise_zone' in self.layersName.keys() :
                    if layer.name() == self.layersName['emprise_zone']:
                        indexCoucheVector = index
                index+=1
        self.assb.clayer_vector.setCurrentIndex(indexCoucheVector)
        self.layersName['emprise_zone'] = self.assb.clayer_vector.currentText().replace('\\',os.sep)
        self.dlg.show()

        # Run the dialog event loop
        result = self.dlg.exec_()

        # See if OK was pressed
        if result:
            # Do something useful here - delete the line containing pass and
            # substitute with your code.
            pass
        return

    #########################################################################
    # FONCTION initScript()                                                 #
    #########################################################################
    def initScript(self):
        self.unlockGuiPart1()
        self.unlockGuiPart2()
        self.unlockGuiPart3()
        self.unlockGuiPart4()
        self.unlockGuiPart5()
        self.testRasterValMinValMax = True
        self.initIhm()
        self.layersName = {}
        self.reloadComboLayersRaster()
        self.reloadComboLayersVector()
        return

    #########################################################################
    # FONCTION seuillerClicked()                                            #
    #########################################################################
    def seuillerClicked(self):

        # On "gèle" l'IHM pendant le traitement de seuillage
        messInfo(self.dlg,unicode(u"-- Note: L'affichage de QGIS est 'figé' pendant tous les traitements.\nA la fin du process et pour des rasters de taille importante l'affichage des résultats peut prendre un certain temps...  ---" ).encode('latin 1'))
        messInfo(self.dlg,"")
        self.lockGuiPart1()
        self.lockGuiPart2()
        self.lockGuiPart4()
        self.lockGuiPart5()
        self.dlg.btValider.setEnabled(False)

        # Rasteur déja assemblé et selectionné
        ficRaster = self.dlg.clayer_raster.currentText().replace('\\',os.sep)
        self.dir_dest = self.dlg.clayer_dir_dest.currentText().replace('\\',os.sep)

        if ficRaster is None or ficRaster == "":
            QMessageBox.information(None,"Attention !!!",unicode(u"Le fichier raster est inexistant!").encode('latin 1'))
            messErreur(self.dlg,unicode(u"Aucun raster dans la liste.").encode('latin 1'))
            return

        li = layerList(self.iface)
        if self.fromActiveLayerRaster:
            layerRaster = li[ficRaster]
            self.dir_raster_src = os.path.dirname(unicode(layerRaster.dataProvider().dataSourceUri()))
        else:
            self.dir_raster_src = os.path.dirname(ficRaster)

        if not os.path.isdir(self.dir_dest):
            self.dir_dest = self.dir_raster_src

        # Chargement d'un raster d'entrée
        if self.fromActiveLayerRaster:
             self.layersName['raster'] = ficRaster
        else:
             self.layersName['raster'] = os.path.splitext(os.path.basename(ficRaster))[0]
        layerName = removeAccents(unicode(self.layersName['raster']))
        self.layersName['emprise'] = layerName + "_Emprise"
        
        # Creation des noms de fichiers de seuillage
        seuilStr = self.dlg.seuil.text()
        while seuilStr[0] == '0' and len(seuilStr) >= 2 and seuilStr[1] != '.' :
            seuilStr = seuilStr[1:]
        if '.' in seuilStr :
            while seuilStr[-1] == '0': 
                seuilStr = seuilStr[:len(seuilStr)-1]
            if  seuilStr[-1] == '.':           
                seuilStr = seuilStr[:len(seuilStr)-1]
        self.dlg.seuil.setText(seuilStr)
        
        otherFile = ""
        if self.conf.rbOptique.isChecked():
            # Bouton Optique est checked le nom du seuil est :
            if self.dlg.rbComputeNdvi.isChecked() :
                self.layersName['ndvi'] = layerName + "_NDVI"
                self.layersName['seuil'] = layerName + "_NDVI" + "_S"
                otherFile = self.layersName['ndvi']
            elif self.dlg.rbComputeNdwi2.isChecked() :
                self.layersName['ndwi2'] = layerName + "_NDWI2"
                self.layersName['seuil'] = layerName + "_NDWI2" + "_S"
                otherFile = self.layersName['ndwi2']
            else :
                self.layersName['seuil'] = layerName + "_S"
        else:
            # Bouton Radar est checked le nom du seuil est:
            radius = self.dlg.spinBoxRadius.value()
            if self.dlg.rbDespeckLee.isChecked() :
                self.layersName['lee'] = layerName + "_Lee" + str(radius)
                self.layersName['seuil'] = layerName + "_Lee" + str(radius) + "_S"
                otherFile = self.layersName['lee']
            elif self.dlg.rbDespeckGamma.isChecked() :
                self.layersName['gamma'] = layerName + "_Gamma" + str(radius)
                self.layersName['seuil'] = layerName + "_Gamma"+ str(radius) + "_S"
                otherFile = self.layersName['gamma']
            else :
                self.layersName['seuil'] = layerName + "_S"

        # Si le fichier seuillage existe dans Qgis, le supprimer
        seuilStr = self.dlg.seuil.text()   
        if float(seuilStr) == 0:
            seuilStr = '0'
        else:
            seuilStr.replace('.','_') 
        
        # Test si les seuils sont correctement renseigné
        if seuilStr in ('','+','-'):
            QMessageBox.information(None,"Attention !!!",unicode(u"Valeur de seuil incorrecte !").encode('latin 1'))
            self.dlg.seuil.setFocus()
        elif not self.seuilMin <= float(seuilStr) <= self.seuilMax :
            QMessageBox.information(None,"Attention !!!",u"Valeur de seuil  %s incorrecte ! la valeur doit être comprise entre %s et %s "%(str(seuilStr), str(self.seuilMin), str(self.seuilMax)))
            self.dlg.seuil.setFocus()
        else :
            self.seuilStr = seuilStr
            for elem in li:
                if elem == self.layersName['seuil']  + seuilStr or otherFile != "" and elem == otherFile :
                    QgsMapLayerRegistry.instance().removeMapLayer(li[elem].id())
            
            # Exécuter le seuillage
            newLayersName = runThresholding(self.iface, self.dlg, self.conf, self.layersName, self.dir_raster_src, self.dir_dest, ficRaster, self.seuilStr, self.fromActiveLayerRaster)
            
            # Mise à jour du nom du fichier seuillé en fonction du traitement ou du non traitement
            if newLayersName is not None :
                self.layersName = newLayersName
            if self.layersName['seuil'][len(self.layersName['seuil'])-2:] == "_S":
                self.layersName['seuil'] = self.layersName['seuil'][0:len(self.layersName['seuil'])-2]

        self.dlg.btValider.setEnabled(True)
        return

    #########################################################################
    # FONCTION validerSeuillageClicked()                                    #
    #########################################################################
    def validerSeuillageClicked(self):

        if self.conf.rbQGIS.isChecked():
            # L'IHM est adaptée à la configuration "QGIS"
            QMessageBox.information(None,u"Etape de filtrage",unicode(u"'Le bouton 'Filtrer' (Fonction  GDAL : 'gdal_sieve') permet de filtrer les zones d'eau.\n\n \
Si le résultat n'est pas satisfaisant, vous pouvez relancer un nouveau filtrage en ajustant le paramètre de filtrage et en réappuyant sur le bouton 'Filtrer' jusqu'à ce que le résultat vous convienne.\n\n \
Une fois le filtrage satisfaisant, le bouton 'Vectoriser' valide le filtrage et lance la vectorisation sur la base du dernier filtrage réalisé.\n\n \
Si vous ne souhaitez pas de filtrage appuyez directement sur le bouton 'Vectoriser'").encode('latin 1'))

            messInfo(self.dlg,(unicode(u"---> Lancez 'Filtrer' (fonction du seuil choisi) pour 'nettoyer' le masque de seuil des îlots et artefacts  ET/OU 'Vectoriser' pour poursuivre le traitement.  <---" )).encode('latin 1'))
            messInfo(self.dlg,"")

        if self.conf.rbOTB.isChecked():
            # L'IHM est adaptée à la configuration "OTB"
            QMessageBox.information(None,u"Etape de filtrage",unicode(u"Le bouton filtrer (Fonction  OTB : 'Classification Map Regularization') permet de filtrer les zones d'eau.\n\n \
Si le résultat n'est pas satisfaisant, vous pouvez relancer un nouveau filtrage en ajustant le paramètre de filtrage et en réappuyant sur le bouton 'Filtrer' jusqu'à ce que le résultat vous convienne.\n\n \
Une fois le filtrage satisfaisant, le bouton 'Vectoriser' valide le filtrage et lance la vectorisation sur la base du dernier filtrage réalisé.\n\n \
Si vous ne souhaitez pas de filtrage appuyez directement sur le bouton 'Vectoriser'").encode('latin 1'))

            messInfo(self.dlg,(unicode(u"---> Lancez 'Filtrer' (fonction du radius choisi) pour 'nettoyer' le masque de seuil des îlots et artefacts  ET/OU 'Vectoriser' pour poursuivre le traitement.  <---" )).encode('latin 1'))
            messInfo(self.dlg,"")

        # Fin étape de seuillage débloquer l'étape filter et bloquer l'étape de seuillage
        self.testRasterValMinValMax = False
        self.lockGuiPart3()
        self.unlockGuiPart4()
        self.unlockGuiPart5()
        return

    #########################################################################
    # FONCTION filtrerClicked()                                              #
    #########################################################################
    def filtrerClicked(self):

        # Creation des noms de fichiers de filtrage
        layerName = removeAccents(unicode(self.layersName['seuil']))
        if self.conf.rbOTB.isChecked():
            # Bouton OTB est checked le nom du filtre est :
            radiusStr = self.dlg.seuilCMR.text()
            self.layersName['filtre'] = layerName + '_FmR' + radiusStr
        else:
            # Bouton QGIS est checked le nom du filtre est :
            seuilTamiserStr = self.dlg.seuilTamiser.text()
            if self.dlg.rbTamiser4.isChecked() :
                connectivity = '4'
            else :
                connectivity = '8'
            self.layersName['filtre'] = layerName + '_Fsw' + seuilTamiserStr  + 'C' + connectivity

        # Etape de filtrage pour éliminer les artefacts et les zones d'eau à négliger
        runFilter(self.iface, self.dlg, self.conf, self.dir_dest, self.layersName['seuil'], self.layersName['filtre'])

        return

    #########################################################################
    # FONCTION vectoriserClicked()                                          #
    #########################################################################
    def vectoriserClicked(self):

        # Fin étape de filtrage  bloquer l'étape de filtrage
        self.lockGuiPart4()

        # Creation du vecteur final
        if 'filtre' in self.layersName.keys() :
            layerName = removeAccents(unicode(self.layersName['filtre']))
        else :
            self.layersName['filtre'] = ""
            layerName = removeAccents(unicode(self.layersName['seuil']))
            
        self.layersName['polygonize'] = layerName + "_Vect"
        self.layersName['eau'] = layerName + "_ZonesEau"

        # Vectorisé le fichier raster
        runVectorize(self.iface, self.dlg, self.assb, self.dir_dest, self.layersName, self.seuilStr)
        
        # Debloquer l'IHM
        self.unlockGuiPart1()
        self.unlockGuiPart2()
        self.unlockGuiPart3()
        self.unlockGuiPart4()
        self.unlockGuiPart5()
        self.dlg.btValider.setEnabled(False)
        self.dlg.btFilter.setEnabled(False)
        self.dlg.btVectoriser.setEnabled(False)
        self.dlg.label_14.setEnabled(False)
        self.dlg.label_12.setEnabled(False)
        self.dlg.label_22.setEnabled(False)
        self.dlg.label_23.setEnabled(False)
        
        self.testRasterValMinValMax = True
        return

    #########################################################################
    # FONCTION onrbSeuilChange()                                            #
    #########################################################################
    def onrbSeuilChange(self):
        if self.dlg.rbSeuil.isChecked():
            self.dlg.label_19.setEnabled(True)
            self.dlg.delta.setEnabled(True)
            self.dlg.delta.setText('0')
        else:
            self.dlg.label_19.setEnabled(False)
            self.dlg.delta.setEnabled(False)
            self.dlg.delta.setText('')
        return

    #########################################################################
    # FONCTION () onrbComputeIndexChange                                    #
    #########################################################################
    def onrbComputeIndexChange(self):
        if self.testRasterValMinValMax :
            if self.dlg.rbComputeNdvi.isChecked() or self.dlg.rbComputeNdwi2.isChecked() :
                self.seuilMin = -1.0
                self.seuilMax = +1.0
                self.seuil = 0.0
            else:
                self.updateSeuilMinMax(self.dlg.clayer_raster.currentText())
                self.seuil = 0 

            self.dlg.lSeuilMin.setText(str(self.seuilMin))
            self.dlg.seuilSlider.setMinimum(int(self.seuilMin * 10000))
            self.dlg.lSeuilMax.setText(str(self.seuilMax))
            self.dlg.seuilSlider.setMaximum(int(self.seuilMax * 10000))
            self.updateSeuil(self.seuil)
            self.updateSlider(self.seuil)
            
        return

    #########################################################################
    # FONCTION onrbcomputeNdviChange()                                      #
    #########################################################################
    def onrbcomputeNdviChange(self):
        if self.dlg.rbComputeNdvi.isChecked():
            self.dlg.rbComputeNdwi2.setChecked(False)
            self.dlg.rbComputeNone.setChecked(False)
        self.onrbComputeIndexChange()
        return

    #########################################################################
    # FONCTION onrbcomputeNdwi2Change()                                     #
    #########################################################################
    def onrbcomputeNdwi2Change(self):
        if self.dlg.rbComputeNdwi2.isChecked():
            self.dlg.rbComputeNdvi.setChecked(False)
            self.dlg.rbComputeNone.setChecked(False)
        self.onrbComputeIndexChange()
        return

    #########################################################################
    # FONCTION onrbcomputeNoneChange()                                      #
    #########################################################################
    def onrbcomputeNoneChange(self):
        if self.dlg.rbComputeNone.isChecked():
            self.dlg.rbComputeNdvi.setChecked(False)
            self.dlg.rbComputeNdwi2.setChecked(False)
        self.onrbComputeIndexChange()
        return

    #########################################################################
    # FONCTION onrbDespeckChange()                                          #
    #########################################################################
    def onrbDespeckChange(self):
        return

    #########################################################################
    # FONCTION onrbDespeckLeeChange()                                       #
    #########################################################################
    def onrbDespeckLeeChange(self):
        if self.dlg.rbDespeckLee.isChecked():
            self.dlg.rbDespeckGamma.setChecked(False)
            self.dlg.rbDespeckNone.setChecked(False)
            self.dlg.spinBoxRadius.setEnabled(True)
            self.dlg.doubleSpinBoxLooks.setEnabled(True)
            self.dlg.spinBoxRadius.setValue(3)
        self.onrbDespeckChange()
        return

    #########################################################################
    # FONCTION onrbDespeckGammaChange()                                     #
    #########################################################################
    def onrbDespeckGammaChange(self):
        if self.dlg.rbDespeckGamma.isChecked():
            self.dlg.rbDespeckLee.setChecked(False)
            self.dlg.rbDespeckNone.setChecked(False)
            self.dlg.spinBoxRadius.setEnabled(True)
            self.dlg.doubleSpinBoxLooks.setEnabled(True)
            self.dlg.spinBoxRadius.setValue(3)
        self.onrbDespeckChange()
        return

    #########################################################################
    # FONCTION onrbDespeckNoneChange()                                      #
    #########################################################################
    def onrbDespeckNoneChange(self):
        if self.dlg.rbDespeckNone.isChecked():
            self.dlg.rbDespeckLee.setChecked(False)
            self.dlg.rbDespeckGamma.setChecked(False)
            self.dlg.spinBoxRadius.setValue(0)
            self.dlg.spinBoxRadius.setEnabled(False)
            self.dlg.doubleSpinBoxLooks.setEnabled(False)
        self.onrbDespeckChange()
        return

    #########################################################################
    # FONCTION updateRasterPath()                                           #
    #########################################################################
    def updateRasterPath(self,value):
        if ('/' in value) or ('\\' in value) :
            self.fromActiveLayerRaster = False
        else :
            self.fromActiveLayerRaster = True

        self.updateSeuilMinMax(value)
        return

    #########################################################################
    # FONCTION updateAssembledPath()                                        #
    #########################################################################
    def updateAssembledPath(self,value):
        if ('/' in value) or ('\\' in value) :
            self.fromActiveLayerAssembled = False
        else :
            self.fromActiveLayerAssembled = True
        return

    #########################################################################
    # FONCTION updateVectorPath()                                           #
    #########################################################################
    def updateVectorPath(self,value):
        if ('/' in value) or ('\\' in value) :
            self.fromActiveLayerVector = False
            self.layersName['emprise_zone'] = os.path.splitext(os.path.basename(value))[0]
        else :
            self.fromActiveLayerVector = True
            if value is None :
                value = ""
            self.layersName['emprise_zone'] = value
        return

    #########################################################################
    # FONCTION updateSeuilMinMax()                                          #
    #########################################################################
    def updateSeuilMinMax(self, ficRaster):

        rasterPath = ""
        if self.fromActiveLayerRaster :
            li = layerList(self.iface)
            if ficRaster in li :
                layerRaster = li[ficRaster]
                rasterPath = unicode(layerRaster.dataProvider().dataSourceUri())
        else :
            rasterPath = ficRaster

        if self.conf.rbRadar.isChecked() or (self.conf.rbOptique.isChecked() and self.dlg.rbComputeNone.isChecked()) :
            if rasterPath != None and os.path.isfile(rasterPath) :

                # Recherche du min et max
                val_max, val_mini = getMinMaxValueBandImage(rasterPath,1)
                self.seuilMin = val_mini
                self.seuilMax = val_max
                if self.seuilMin > self.seuil :
                    self.seuil = val_mini + 0.001
                else :
                    self.seuil = 0.0
                
        elif self.conf.rbOptique.isChecked() and not self.dlg.rbComputeNone.isChecked():
            self.seuilMin = -1.0
            self.seuilMax = +1.0
            if self.dlg.rbComputeNdvi.isChecked():
                self.seuil = 0.0
            elif self.dlg.rbComputeNdwi2.isChecked():
                self.seuil = 0.0
            else :
                self.seuil = 0.0

        else :
            self.seuilMin = -10000
            self.seuilMax = +10000
            self.seuil = 0

        self.dlg.lSeuilMax.setText(str(self.seuilMax))
        self.dlg.seuilSlider.setMaximum(int(self.seuilMax * 10000))
        self.dlg.seuil.setText(str(self.seuil))
        self.dlg.lSeuilMin.setText(str(self.seuilMin))
        self.dlg.seuilSlider.setMinimum(int(self.seuilMin * 10000))
        self.updateSeuil(self.seuil)
        self.updateSlider(self.seuil)
        self.dlg.seuil.setText(str(self.seuil))
        return

    #########################################################################
    # FONCTION btDirDirDestClicked()                                        #
    #########################################################################
    def btDirDirDestClicked(self):
        dirDest = None
        dirDest = QFileDialog.getExistingDirectory(None,"",self.home, QFileDialog.ShowDirsOnly )
        dirDest = dirDest.replace("\\", os.sep)
        if dirDest:
            self.home = os.path.dirname(dirDest)
            self.dlg.clayer_dir_dest.addItem(dirDest)
            self.dlg.clayer_dir_dest.setCurrentIndex(self.dlg.clayer_dir_dest.findText(dirDest))
        return

    #########################################################################
    # FONCTION btDelDirDestClicked()                                        #
    #########################################################################
    def btDelDirDestClicked(self):
        index = self.dlg.clayer_dir_dest.currentIndex()
        self.dlg.clayer_dir_dest.removeItem(index)
        return

    #########################################################################
    # FONCTION reloadComboLayersRaster()                                    #
    #########################################################################
    def reloadComboLayersRaster(self):
        self.dlg.clayer_raster.clear()
        layers = self.iface.legendInterface().layers()
        for layer in layers:
            if QgsMapLayer != None and layer.type() == QgsMapLayer.RasterLayer:
                self.dlg.clayer_raster.addItem(layer.name())
        return

    #########################################################################
    # FONCTION btDirRasterClicked()                                         #
    #########################################################################
    def btDirRasterClicked(self):
        fic = QFileDialog.getOpenFileName(None,"",self.home,FORMAT_EXTENTION_SELECT)
        if fic:
            self.home = os.path.dirname(fic)
            self.dlg.clayer_raster.addItem(fic)
            self.dlg.clayer_raster.setCurrentIndex(self.dlg.clayer_raster.findText(fic))
        return

    #########################################################################
    # FONCTION btDelRasterClicked()                                         #
    #########################################################################
    def btDelRasterClicked(self):
        index = self.dlg.clayer_raster.currentIndex()
        self.dlg.clayer_raster.removeItem(index)
        return

    #########################################################################
    # FONCTION btDirVectorClicked()                                         #
    #########################################################################
    def btDirVectorClicked(self):
        fic = QFileDialog.getOpenFileName(None,"",self.home,"Fichier vecteur (*.shp *.SHP)")
        if fic:
            self.home = os.path.dirname(fic)
            self.assb.clayer_vector.addItem(fic)
            self.assb.clayer_vector.setCurrentIndex(self.assb.clayer_vector.findText(fic))
            self.updateVectorPath(self.assb.clayer_vector.currentText())
        return

    #########################################################################
    # FONCTION btDelVectorClicked()                                         #
    #########################################################################
    def btDelVectorClicked(self):
        index = self.assb.clayer_vector.currentIndex()
        self.assb.clayer_vector.removeItem(index)
        self.updateVectorPath(self.assb.clayer_vector.currentText())
        return

    #########################################################################
    # FONCTION reloadComboLayersVector()                                    #
    #########################################################################
    def reloadComboLayersVector(self):
        self.assb.clayer_vector.clear()
        layers = self.iface.legendInterface().layers()
        for layer in layers:
            if QgsMapLayer != None and layer.type() == QgsMapLayer.VectorLayer:
                self.assb.clayer_vector.addItem(layer.name())
                self.updateVectorPath(self.assb.clayer_vector.currentText())
        return

    #########################################################################
    # FONCTION btDirDirSrcClicked()                                         #
    #########################################################################
    def btDirDirSrcClicked(self):
        dirSrc = None
        dirSrc = QFileDialog.getExistingDirectory(None,"",self.home, QFileDialog.ShowDirsOnly )
        dirSrc = dirSrc.replace("\\", os.sep)
        if dirSrc:
            self.home = os.path.dirname(dirSrc)
            self.assb.clayer_dir_src.addItem(dirSrc)
        return

    #########################################################################
    # FONCTION btDelDirSrcClicked()                                         #
    #########################################################################
    def btDelDirSrcClicked(self):
        index = self.assb.clayer_dir_src.currentIndex()
        self.assb.clayer_dir_src.removeItem(index)
        return

    #########################################################################
    # FONCTION btDelAssembledClicked()                                      #
    #########################################################################
    def btDelAssembledClicked(self):
        index = self.assb.clayer_assembled.currentIndex()
        self.assb.clayer_assembled.removeItem(index)
        return

    #########################################################################
    # FONCTION btDirAssembledClicked()                                      #
    #########################################################################
    def btDirAssembledClicked(self):
        fic = QFileDialog.getSaveFileName(None,"",self.home,FORMAT_EXTENTION_ASSEMBLE)
        if fic:
            self.home = os.path.dirname(fic)
            self.assb.clayer_assembled.addItem(fic)
            self.assb.clayer_assembled.setCurrentIndex(self.assb.clayer_assembled.findText(fic))
        return

    #########################################################################
    # FONCTION reloadComboLayersAssembled()                                 #
    #########################################################################
    def reloadComboLayersAssembled(self):
        self.assb.clayer_assembled.clear()
        layers = self.iface.legendInterface().layers()
        for layer in layers:
            if QgsMapLayer != None and layer.type() == QgsMapLayer.RasterLayer:
                self.assb.clayer_assembled.addItem(layer.name())
        return

    #########################################################################
    # FONCTION btAboutClicked()                                             #
    #########################################################################
    def btAboutClicked(self):
        messageAbout1 = unicode(u" Plugin Cart'Eau V1.0\n Extraction des zones immergées. \n").encode('latin 1')
        messageAbout2 = unicode(u"\n Copyright (©) CEREMA 2018.\n All rights reserved.\n\n").encode('latin 1')
        messageAbout3 = unicode(u"Christelle.Bosc@cerema.fr").encode('latin 1')
        QMessageBox.information(None,"Information :", messageAbout1 + messageAbout2 + messageAbout3)
        return

    #########################################################################
    # FONCTION btInfoClicked()                                              #
    #########################################################################
    def btInfoClicked(self):
        messageInfo = geUserManuel()
        QMessageBox.information(None,"Information :", messageInfo)
        return

    #########################################################################
    # FONCTION btConfigurationClicked()                                     #
    #########################################################################
    def btConfigurationClicked(self):
        self.conf.Qqis = self.conf.rbQGIS.isChecked()
        self.conf.OTB = self.conf.rbOTB.isChecked()
        self.conf.Optique = self.conf.rbOptique.isChecked()
        self.conf.Radar = self.conf.rbRadar.isChecked()
        self.conf.idxRed = self.conf.cbRed.currentIndex()
        self.conf.idxGreen = self.conf.cbGreen.currentIndex()
        self.conf.idxBlue = self.conf.cbBlue.currentIndex()
        self.conf.idxNIR = self.conf.cbNIR.currentIndex()
        self.conf.exec_()
        return

    #########################################################################
    # FONCTION cancelConfClicked()                                          #
    #########################################################################
    def cancelConfClicked(self) :
        self.conf.rbQGIS.setChecked(self.conf.Qqis)
        self.conf.rbOTB.setChecked(self.conf.OTB)
        self.conf.rbOptique.setChecked(self.conf.Optique)
        self.conf.rbRadar.setChecked(self.conf.Radar)
        self.conf.cbRed.setCurrentIndex(self.conf.idxRed)
        self.conf.cbGreen.setCurrentIndex(self.conf.idxGreen)
        self.conf.cbBlue.setCurrentIndex(self.conf.idxBlue)
        self.conf.cbNIR.setCurrentIndex(self.conf.idxNIR)
        return

    #########################################################################
    # FONCTION closeConfClicked()                                           #
    #########################################################################
    def closeConfClicked(self) :

        if self.conf.rbRadar.isChecked() :
            if self.conf.rbQGIS.isChecked() :
                self. dlg.rbDespeckNone.setChecked(True)
                self.dlg.rbDespeckLee.setChecked(False)
                self.dlg.rbDespeckGamma.setChecked(False)
                self.dlg.rbDespeckLee.setEnabled(False)
                self.dlg.rbDespeckGamma.setEnabled(False)
                self.dlg.spinBoxRadius.setEnabled(False)
                self.dlg.doubleSpinBoxLooks.setEnabled(False)
                self.dlg.label_20.setEnabled(False)
                self.dlg.label_21.setEnabled(False)
            else :
                self. dlg.rbDespeckNone.setChecked(True)
                self.dlg.rbDespeckLee.setChecked(True)
                self.dlg.rbDespeckGamma.setChecked(True)
                self.dlg.rbDespeckLee.setEnabled(True)
                self.dlg.rbDespeckGamma.setEnabled(True)
                self.dlg.spinBoxRadius.setEnabled(True)
                self.dlg.doubleSpinBoxLooks.setEnabled(True)
                self.dlg.label_20.setEnabled(True)
                self.dlg.label_21.setEnabled(True)

            self.updateSeuilMinMax(self.dlg.clayer_raster.currentText())
        else :
            self.dlg.rbDespeckLee.setEnabled(True)
            self.dlg.rbDespeckGamma.setEnabled(True)
            self.dlg.spinBoxRadius.setEnabled(True)
            self.dlg.doubleSpinBoxLooks.setEnabled(True)
            self.dlg.label_20.setEnabled(True)
            self.dlg.label_21.setEnabled(True)
            self.onrbComputeIndexChange()
        return

    #########################################################################
    # FONCTION btAssemblerClicked()                                         #
    #########################################################################
    def btAssemblerClicked(self):
        self.assb.exec_()
        return

    #########################################################################
    # FONCTION cancelAssemblyClicked()                                      #
    #########################################################################
    def cancelAssemblyClicked(self) :
        return

    #########################################################################
    # FONCTION closeAssemblyClicked()                                       #
    #########################################################################
    def closeAssemblyClicked(self) :

        # Demande d'assemblage
        #---------------------
        rasterAssembly = runAssemble(self.iface, self.dlg, self.conf, self.assb, self.fromActiveLayerVector, self.fromActiveLayerAssembled)

        if rasterAssembly != "" and os.path.isfile(rasterAssembly) :

            # Chargement du fichier raster assemblé dans QGis
            file_name = os.path.splitext(os.path.basename(rasterAssembly))[0]
            layer = QgsRasterLayer(rasterAssembly, file_name)
            QgsMapLayerRegistry.instance().addMapLayer(layer)

            # Ajour du fichier raster assemblé dans le selecteur de fichier raster
            self.reloadComboLayersRaster()
            self.dlg.clayer_raster.setCurrentIndex(self.dlg.clayer_raster.findText(file_name))

            # Sauvegarde de la couche emprise_zone
            ficVector = self.assb.clayer_vector.currentText().replace('\\',os.sep)
            if self.fromActiveLayerVector :
                self.layersName['emprise_zone'] = ficVector
            else:
                self.layersName['emprise_zone'] = os.path.splitext(os.path.basename(ficVector))[0]
        return

    #########################################################################
    # FONCTION updateSeuil()                                                #
    #########################################################################
    def updateSeuil(self,value):
      
        seuilStr = str(value)
        while seuilStr[0] == '0' and len(seuilStr) >= 2 and seuilStr[1] != '.' :
            seuilStr = seuilStr[1:]
        if '.' in seuilStr :
            while seuilStr[-1] == '0': 
                seuilStr = seuilStr[:len(seuilStr)-1]
            if  seuilStr[-1] == '.':           
                seuilStr = seuilStr[:len(seuilStr)-1]
        self.dlg.seuil.setText(seuilStr)
         
        return

    #########################################################################
    # FONCTION updateSlider()                                               #
    #########################################################################
    def updateSlider(self,value):
        if self.testRasterValMinValMax :
            if value not in('','-','.'):
                try:
                    float(value)
                except:
                    QMessageBox.information(None,"Attention !!!","Valeur de seuil %s format incorrecte !"%(str(value)))
                    self.seuil = 0
                    self.dlg.seuilSlider.setValue(0)
                    self.dlg.seuil.setText("0")
                    return

                self.dlg.seuilSlider.setValue(float(value) * 10000.0)
        return

    #########################################################################
    # FONCTION updateConfBand()                                             #
    #########################################################################
    def updateConfBand(self,value, index):
        self.conf.channelOrderDic[index] = int(value.replace('Bande ',''))
        return

    #########################################################################
    # FONCTION onSeuilTamiserChange()                                       #
    #########################################################################
    def onSeuilTamiserChange(self,value):
        if value =='+' or value == '-':
            self.dlg.seuilTamiser.setText("")
            return
        if value not in('','.'):
            try:
                int(value)
            except:
                QMessageBox.information(None,"Attention !!!","Valeur de seuil incorrecte !")
                self.dlg.seuilTamiser.setText("")
                return
            if not (0 <= int(value)<10000):
                QMessageBox.information(None,"Attention !!!","Valeur de seuil incorrecte !")
                self.dlg.seuilTamiser.setText("")
                return
        return

    #########################################################################
    # FONCTION onSeuilCMRChange()                                           #
    #########################################################################
    def onSeuilCMRChange(self,value):
        if value == '+' or value == '-':
            self.dlg.seuilCMR.setText("")
            return
        if value not in('','.'):
            try:
                int(value)
            except:
                QMessageBox.information(None,"Attention !!!","Valeur de seuil incorrecte !")
                self.dlg.seuilCMR.setText("")
                return
            if not (0 <= int(value) <= 30):
                QMessageBox.information(None,"Attention !!!","Valeur de seuil incorrecte !")
                self.dlg.seuilCMR.setText("")
                return
        return

    #########################################################################
    # FONCTION onDeltaChange()                                              #
    #########################################################################
    def onDeltaChange(self,value):
        if value == '+' or value == '-':
            self.dlg.delta.setText("")
            return
        if value not in ('','.'):
            try:
                float(value)
            except:
                QMessageBox.information(None,"Attention !!!","Valeur de delta incorrecte !")
                self.dlg.delta.setText("")
                return
            if  self.conf.rbOptique.isChecked() and (self.dlg.rbComputeNdvi.isChecked() or self.dlg.rbComputeNdwi2.isChecked()) :
                if not -1 <= float(self.dlg.seuil.text())-float(value) <= +1 or not -1 <= float(self.dlg.seuil.text())+float(value) <= +1:
                    QMessageBox.information(None,"Attention !!!","Valeur de delta incorrecte, -1 <= seuil+/-delta <=1 !")
                    self.dlg.delta.setText("0")
                else:
                    if float(value) != 0:
                        if float(value) > 0 and len(value.strip()) > 4:
                            self.dlg.delta.setText(value[0:4])
        return

    #########################################################################
    # FONCTION infoOTBmessageBox()                                          #
    #########################################################################
    def infoOTBmessageBox(self):
        rep1winOTB = "C:\\OSGEO4W64\\bin"
        rep2winOTB = "C:\\OSGeo4W64\\apps\\orfeotoolbox\\applications"
        rep1linOTB = "/usr/local/bin"
        rep2linOTB = "/usr/local/lib/otb/applications"
        mess1 = unicode(u"Vérifiez que les fonctionnalités de OTB sont activées dans QGIS.\n --> Onglet traitement - Options - Prestataires de services - Boîte à outils Orfeo. \
        \n Les répertoires : - Répertoire d'outil en ligne de commande OTB - et - Répertoire des applications OTB - doivent être renseignés.").encode('latin 1')
        mess2 = unicode(u"\nExemple pour windows:\nRépertoire d'outil en ligne de commande OTB: " + rep1winOTB + u"\nRépertoire des applications OTB: " + rep2winOTB).encode('latin 1')
        mess3 = unicode(u"\nExemple pour linux:\nRépertoire d'outil en ligne de commande OTB: " + rep1linOTB + u"\nRépertoire des applications OTB: " + rep2linOTB).encode('latin 1')
        QMessageBox.information(None,"Attention !!!", mess1 + mess2 + mess3)
        return

    #########################################################################
    # FONCTION onrbQGISChange()                                             #
    #########################################################################
    def onrbQGISChange(self):
        if self.conf.rbQGIS.isChecked():
            self.dlg.lseuilTamiser.setVisible(True)
            self.dlg.seuilTamiser.setVisible(True)
            self.dlg.gBTamiser.setVisible(True)
            self.dlg.lconnTamiser.setVisible(True)
            self.dlg.rbTamiser4.setVisible(True)
            self.dlg.rbTamiser8.setVisible(True)
            self.dlg.lseuilCMR.setVisible(False)
            self.dlg.seuilCMR.setVisible(False)
        else :
            self.conf.rbOTB.setChecked(True)
        return

    #########################################################################
    # FONCTION onrbOTBChange()                                              #
    #########################################################################
    def onrbOTBChange(self):
        if self.conf.rbOTB.isChecked():
            self.dlg.lseuilTamiser.setVisible(False)
            self.dlg.seuilTamiser.setVisible(False)
            self.dlg.gBTamiser.setVisible(False)
            self.dlg.lconnTamiser.setVisible(False)
            self.dlg.rbTamiser4.setVisible(False)
            self.dlg.rbTamiser8.setVisible(False)
            self.dlg.lseuilCMR.setVisible(True)
            self.dlg.seuilCMR.setVisible(True)

            self.infoOTBmessageBox()
        else:
            self.conf.rbQGIS.setChecked(True)
        return

    #########################################################################
    # FONCTION onrbOptiqueChange()                                          #
    #########################################################################
    def onrbOptiqueChange(self):
        if self.conf.rbOptique.isChecked():
            self.conf.label_20.setEnabled(True)
            self.conf.label_19.setEnabled(True)
            self.conf.label_1.setEnabled(True)
            self.conf.label_2.setEnabled(True)
            self.conf.label_3.setEnabled(True)
            self.conf.label_4.setEnabled(True)
            self.conf.cbRed.setEnabled(True)
            self.conf.cbGreen.setEnabled(True)
            self.conf.cbBlue.setEnabled(True)
            self.conf.cbNIR.setEnabled(True)
            self.dlg.label_4.setVisible(True)
            self.dlg.label_5.setVisible(False)
            self.dlg.groupBox_optique.setVisible(True)
            self.dlg.groupBox_radar.setVisible(False)
            self.dlg.label_20.setVisible(False)
            self.dlg.label_21.setVisible(False)
            self.dlg.spinBoxRadius.setVisible(False)
            self.dlg.doubleSpinBoxLooks.setVisible(False)
        else :
            self.conf.rbRadar.setChecked(True)
        return

    #########################################################################
    # FONCTION onrbRadarChange()                                            #
    #########################################################################
    def onrbRadarChange(self):
        if self.conf.rbRadar.isChecked():
            self.conf.label_20.setEnabled(False)
            self.conf.label_19.setEnabled(False)
            self.conf.label_1.setEnabled(False)
            self.conf.label_2.setEnabled(False)
            self.conf.label_3.setEnabled(False)
            self.conf.label_4.setEnabled(False)
            self.conf.cbRed.setEnabled(False)
            self.conf.cbGreen.setEnabled(False)
            self.conf.cbBlue.setEnabled(False)
            self.conf.cbNIR.setEnabled(False)
            self.dlg.label_4.setVisible(False)
            self.dlg.label_5.setVisible(True)
            self.dlg.groupBox_optique.setVisible(False)
            self.dlg.groupBox_radar.setVisible(True)
            self.dlg.label_20.setVisible(True)
            self.dlg.label_21.setVisible(True)
            self.dlg.spinBoxRadius.setVisible(True)
            self.dlg.doubleSpinBoxLooks.setVisible(True)
        else:
            self.conf.rbOptique.setChecked(True)
        return

    #########################################################################
    # FONCTION quit()                                                       #
    #########################################################################
    def quit(self):
        self.dlg.mess.clear()
        self.testRasterValMinValMax = True
        self.unlockGuiPart1()
        self.unlockGuiPart2()
        self.unlockGuiPart3()
        self.unlockGuiPart4()
        self.unlockGuiPart5()
        self.dlg.close()
        return
