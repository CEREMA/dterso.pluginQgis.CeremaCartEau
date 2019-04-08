# -*- coding: utf-8 -*-
"""
/***************************************************************************
 traitement
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
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *
from qgis.gui import *
from osgeo import gdal, ogr,osr
import os
import time

from qgis.core import QgsRasterLayer
from PyQt4.QtCore import QFileInfo

from tools import *
from processingRaster import *
from assembly import *
    
#########################################################################
# FONCTION unloadAllLayers()                                            #
#########################################################################
def unloadAllLayers(iface):
    groups = iface.legendInterface().groups()
    for group in groups:
        iface.legendInterface().removeGroup(0)
    for i in iface.legendInterface().layers():
        QgsMapLayerRegistry.instance().removeMapLayer(i.id())

#########################################################################
# FONCTION loadRaster()                                                 #
#########################################################################
def loadRaster(dlg, path, layerName):	
    # Chargement d'un raster dans QGIS
    layer = QgsRasterLayer(path, layerName)
    if not layer.isValid():
        messErreur(dlg,unicode(layerName + u" ne peut pas être chargé.").encode('latin 1'))
        return
    QgsMapLayerRegistry.instance().addMapLayer(layer)   
    messInfo(dlg,unicode(u"Le fichier raster " + layerName + u" a été correctement chargé.").encode('latin 1'))
    messInfo(dlg,"")
    ContrastEnhancement = QgsContrastEnhancement.StretchToMinimumMaximum
    layer.setContrastEnhancement(ContrastEnhancement,QgsRaster.ContrastEnhancementCumulativeCut)
    layer.triggerRepaint()          
    return layer

#########################################################################
# FONCTION loadShapeFromDir()                                           #
#########################################################################    
def loadShapeFromDir(dlg, path, layerName):
    # Chargement d'un fichier Shape dans QGIS
    layer = QgsVectorLayer(path, layerName, "ogr")
    if not layer.isValid():
        messErreur(dlg,unicode(layerName+u" ne peut pas être chargé.").encode('latin 1'))
        return
    QgsMapLayerRegistry.instance().addMapLayer(layer)
    layer.triggerRepaint() 
    return layer

#########################################################################
# FONCTION geUserManuel()                                               #
#########################################################################    
def geUserManuel():
    TEXT_USER_MANUAL = "Ce plugin Qgis Cart'Eau a été développé dans le cadre d'un projet API pour le Symsagel (Syndicat Mixte de Gestion des Eaux du Bassin de la Lys), pour détecter les zones en eau à partir d'images satellites et fournir un vecteur de contour des zones en eau extrait des images en sortie. \
    \n\nLa méthode repose sur le principe de seuillage radiométrique (seuil maximum pour tous les cas sauf pour le NDWI2). \
    \n\nLe plugin permet de traiter des images satellites optique ou radar (à déterminer dans l'onglet Configuration). \
    \n\n\nLe plugin présente également en option: \
    \n\n- une étape permettant de rechercher une ou plusieurs images disponibles sur une emprise géographique fournie et de les assembler. Cette étape est utile pour assembler des imagettes issues d'une même image afin de reconstituer l'image source (cas des images Pléiades livrées par IGN). Il est déconseillé de l'utiliser pour des acquisitions différentes. \
    \n\n- une étape de prétraitement des images pour faciliter l'extraction des zones en eau : calcul d'indices radiométriques pour les images optiques (NDVi, NDWI2), ou despeckle pour les images radar (NB : les images radar se sont ni orthorectifiées ni calibrées dans ce plugin. Cela peut être fait auparavant dans SNAP) \
    \n\n- une étape de filtrage permettant de filtrer les zones en eau constituées de pixels isolés. \
    \n\nDeux outils peuvent être mobilisés grâce à l'onglet Configuration : les outils OTB ou Qgis. La configuration OTB est indipensable pour l'étape de Despeckle pour les images Radar. Sinon, les 2 configurations sont possibles dans les autres cas. Ce qui diffère ce sont les calculs d'indices (calculatrice raster QGIS et BandMath OTB) et les filtres (filtre gdal_sieve en configuation Qgis et filtre majoritaire en configuration OTB)"
    return TEXT_USER_MANUAL 
    
#########################################################################
# FONCTION runAssemble()                                                #
#########################################################################        
def runAssemble(iface, dlg, conf, assb, fromActiveLayerVector, fromActiveLayerAssembled):

    #  Choix du filtre sur les extensions       
    if  conf.rbOptique.isChecked() :
        ext_list = EXT_IMAGES_LIST
    else :
        ext_list = EXT_IMAGES_LIST  
        
    li = layerList(iface)
   
    # Test la liste des répertoires sources
    repRasterAssemblyList = []
    nbRep = assb.clayer_dir_src.count()
    
    if nbRep == 0:
        QMessageBox.information(None,u"Attention !!!",unicode(u"La liste des répertoires de recherche des rasteurs est vide!").encode('latin 1'))
        return ""
        
    for repIndex in range(nbRep):
        rep = assb.clayer_dir_src.itemText(repIndex)
        rep = rep.replace('\\',os.sep)
        if not os.path.isdir(rep):
            QMessageBox.information(None,u"Attention !!!",unicode(u"Le répertoire %s est inexistant ou incorrect !"%(rep)).encode('latin 1'))
            return ""
        else :
            repRasterAssemblyList.append(rep)

    # Selection du vecteur d'emprise        
    empriseZone = ""
    ficVector = assb.clayer_vector.currentText().replace('\\',os.sep)

    if ficVector == "":
        QMessageBox.information(None,u"Attention !!!",unicode(u"Le fichier vecteur d'emprise est inexistant ou non défini !").encode('latin 1'))
        return ""
        
    if fromActiveLayerVector and (ficVector in li) :
        layerVector = li[ficVector]
        empriseZone = unicode(layerVector.dataProvider().dataSourceUri()).split("|")[0]
    else:
        empriseZone = ficVector
         
    # verification du vecteur    
    if not os.path.isfile(empriseZone) :
        messErreur(dlg,unicode(u" Le fichier d'emprise %s ne peut pas être chargé, fichier inexistant ou incorrect."%(ficVector)).encode('latin 1'))
        QMessageBox.information(None,u"Attention !!!",unicode(u"Le fichier vecteur d'emprise est inexistant ou incorrect !").encode('latin 1'))
        return ""    

    # Selection du raster resultat de fusion
    ficAssembled = assb.clayer_assembled.currentText()
    rasterAssembly = ""
    
    if fromActiveLayerAssembled:
        if ficAssembled in li :
            layerRaster = li[ficAssembled]
            rasterAssembly = unicode(layerRaster.dataProvider().dataSourceUri())
        else :
            QMessageBox.information(None,"Attention !!!",unicode(u"Le raster assemblé " + ficAssembled + u" n'existe pas (ou plus) dans la liste des couches disponibles. Vérifiez réininitialisé la liste des couches d'entrée ou selectionner un fichier raster de sortie.").encode('latin 1'))        
            messErreur(dlg,unicode(u"Le raster " + ficAssembled + u" n'existe pas dans la liste des rasters de destination.").encode('latin 1'))
            return ""      
    else: 
        rasterAssembly = ficAssembled
    extension_input_raster = os.path.splitext(os.path.basename(rasterAssembly))[1]
    
    # verification du nom du fichier raster
    if rasterAssembly == "" :
        QMessageBox.information(None,"Attention !!!",unicode(u"Le fichier raster est inexistant ou incorrect ou le format n'est pas supporté par le plugin !").encode('latin 1'))
        return ""
   
    if os.path.isfile(rasterAssembly) :
        messErreur(dlg,unicode(u" Le fichier d'assemblage %s existe déjà, définir un autre nom de fichier."%(rasterAssembly)).encode('latin 1'))
        return ""
    
    # Assemblage des rasters
    messInfo(dlg,(unicode(u"Assemblage des rasters des répertoires séléctionnés en cours..." )).encode('latin 1'))
    messInfo(dlg,"")
    
    if assembleRasters(dlg, empriseZone, repRasterAssemblyList, ext_list, rasterAssembly) < 0 :
        messErreur(dlg,(unicode(u"Erreur l'assemblage des rasters a échoué" )).encode('latin 1'))
    else :
        messInfo(dlg,(unicode(u"Assemblage des rasters terminé" )).encode('latin 1'))
        messInfo(dlg,"")
           
    return rasterAssembly
    
#########################################################################
# FONCTION runThresholding()                                            #
#########################################################################        
def runThresholding(iface, dlg, conf, layersName, dir_raster_src, dir_dest, ficRaster, seuilStr, fromActiveLayerRaster):

    # Recuperation du chemin compler du fichier raster source
    if fromActiveLayerRaster:
            if ficRaster == "":
                QMessageBox.information(None,"Attention !!!",unicode(u"Le fichier raster est inexistant ou incorrect ou le foramt n'est pas supporté par le plugin !").encode('latin 1'))
                return 
    else:
        if os.path.isfile(ficRaster):
            try:
                dir_raster_src.decode('ascii')
                dir_dest.decode('ascii')
            except:
                QMessageBox.information(None,"Attention !!!",unicode(u"Certaines fonctions comme gdal_polygonize n'acceptent pas les dossiers avec des caractères accentués. Le chemin d'accès au fichier raster n'est pas valable.").encode('latin 1'))
                return 
            if platform.system() == "Linux" and conf.rbOTB.isChecked():
                try:
                    ficRaster.decode('ascii')
                except:
                    QMessageBox.information(None,"Attention !!!",unicode(u"Certaines fonctions comme Band Math (OTB) n'acceptent pas les caractères accentués. Le nom du raster n'est pas valable.").encode('latin 1'))
                    return 
        else :
            QMessageBox.information(None,"Attention !!!",unicode(u"Le fichier raster est inexistant ou incorrect ou le foramt n'est pas supporté par le plugin !").encode('latin 1'))
            return 

    if dlg.rbSeuil.isChecked():
            if dlg.delta.text() in ('','+','-') or float(dlg.delta.text()) == 0:
                QMessageBox.information(None,"Attention !!!", unicode(u"Valeur de delta incorrecte !").encode('latin 1'))
                dlg.delta.setFocus()
                return 
                    
    # On lance le seuillage
    messInfo(dlg,(unicode(u"Seuillage en cours..." )).encode('latin 1'))
    messInfo(dlg,"")
    
    canvas = iface.mapCanvas()
    legend = iface.legendInterface()
    li = layerList(iface)
    
    # Nom du fichier raster
    if fromActiveLayerRaster:
        if ficRaster in li :
            layerRaster = li[ficRaster]
            rasterAssembly = unicode(layerRaster.dataProvider().dataSourceUri())
        else :
            QMessageBox.information(None,"Attention !!!",unicode(ficRaster + u" n'existe plus dans la liste des couches disponible. Vérifiez réininitialisé la liste des couches d'entrée.").encode('latin 1'))        
            messErreur(dlg,unicode(ficRaster + u" n'existe plus dans la liste.").encode('latin 1'))
            return       
        
    else: 
        rasterAssembly = ficRaster
    extension_input_raster = os.path.splitext(os.path.basename(rasterAssembly))[1]  
    messInfo(dlg,(unicode(u"Raster en entrée: " + layersName['raster'] )).encode('latin 1'))  
    
    li = layerList(iface)
    canvas.refresh()
    
    # Variables
    global start_time
    raster = None

    # récupération du nom de base pour les fichiers temporaires et du répertoire de travail
    if fromActiveLayerRaster:
        if layersName['raster'] in li:
            raster = li[layersName['raster']]          
    else: 
        raster = loadRaster(dlg,ficRaster,layersName['raster'])    
    
    if not raster:
        messErreur(dlg,unicode(u"Le raster ne peut pas être chargé.").encode('latin 1'))    
        return 
          
    start_time = time.time()
        
    legend.setLayerVisible(raster, True)
        
    # Création d'une couche vectorielle sur l'emprise du raster
    # Va permettre d'éliminer ultérieurement les bords du cadre lors de la recherche des contours
            
    LayerRasterExtendName = layersName['emprise']
    LayerRasterExtendPath = dir_dest + os.sep + LayerRasterExtendName + EXT_VECTOR
    
    if os.path.exists(LayerRasterExtendPath):
        try:
            os.remove(LayerRasterExtendPath)
        except: 
            QMessageBox.information(None,"Attention !!!",unicode(LayerRasterExtendPath + u" ne peut pas être effacé. Vérifiez que le fichier n'est pas verrouillé par un autre utilisateur ou que le fichier peut être effacé manuellement (droits d'écriture sur le répertoire).").encode('latin 1'))
            messErreur(dlg,unicode(LayerRasterExtendPath + u" ne peut pas être effacé.").encode('latin 1')) 
            return   
    
    messInfo(dlg,unicode(u"Création de la couche: " + LayerRasterExtendName + ".").encode('latin 1'))
    messInfo(dlg,"")

    crs = raster.crs()
    crsWkt = crs.toWkt()
    layerExtend = QgsVectorLayer("Polygon?crs=" + crsWkt, LayerRasterExtendName, "memory")
    
    if not layerExtend.isValid():
        messErreur(dlg,unicode(LayerRasterExtendPath + u" ne peut pas être chargé.").encode('latin 1'))
        return    
    
    QgsMapLayerRegistry.instance().addMapLayer(layerExtend)

    li = layerList(iface)
    symbols = li[LayerRasterExtendName].rendererV2().symbols()
    symbol = symbols[0]
    symbol.setColor(QColor.fromRgb(0,0,255))
    symbol.setAlpha(0.4) 
    
    provider = li[LayerRasterExtendName].dataProvider()
       
    fields = QgsFields()

    fields.append( QgsField( "HEIGHT", QVariant.Double ) )
    fields.append( QgsField( "WIDTH", QVariant.Double ) )

    for f in fields:
        provider.addAttributes([f])

    writer = QgsVectorFileWriter(LayerRasterExtendPath, "CP1250", fields, QGis.WKBPolygon, crs, FORMAT_VECT)
    
    if writer.hasError() != QgsVectorFileWriter.NoError:
        messErreur(dlg,unicode(LayerRasterExtendPath + u" ne peut pas être créé.").encode('latin 1'))      
        return 
        
    li[LayerRasterExtendName].startEditing()
     
    extent = raster.extent()
    minx = extent.xMinimum()
    miny = extent.yMinimum()
    maxx = extent.xMaximum()
    maxy = extent.yMaximum()
    height = raster.height()
    width = raster.width()
    cntx = minx + ( width / 2.0 )
    cnty = miny + ( height / 2.0 )
    area = width * height
    perim = ( 2 * width ) + (2 * height )
    rect = [ QgsPoint( minx, miny ),
             QgsPoint( minx, maxy ),
             QgsPoint( maxx, maxy ),
             QgsPoint( maxx, miny ),
             QgsPoint( minx, miny ) ]
    geometry = QgsGeometry().fromPolygon( [ rect ] )
    feat = QgsFeature()
    feat.setGeometry( geometry )
    feat.setAttributes( [ height,width ] )
    writer.addFeature( feat )    
    provider.addFeatures([feat])
    del writer
        
    li[LayerRasterExtendName].commitChanges()

    legend.setLayerVisible(li[LayerRasterExtendName], False)
    legend.refreshLayerSymbology(li[LayerRasterExtendName])
    li[LayerRasterExtendName].triggerRepaint() 
    canvas.refresh()
    rasterTreatName = ""
    
    # Cas du traitement d'une image optique     
    if conf.rbOptique.isChecked():
    
        # Calcul du NDVI
        if dlg.rbComputeNdvi.isChecked():
            rasterTreatName = layersName['ndvi']
            dir_raster_treat = dir_dest        
            layer = computeNdvi(iface, dlg, conf, dir_raster_src, dir_dest, layersName["raster"], layersName["ndvi"], extension_input_raster)       
            if layer is None :
                return None
            QgsMapLayerRegistry.instance().addMapLayer(layer)
            legend.setLayerVisible(layer, False)
            extension_input_raster = EXT_RASTER    
        
        # Calcul du NDWI2
        elif dlg.rbComputeNdwi2.isChecked():
            rasterTreatName = layersName['ndwi2']
            dir_raster_treat = dir_dest          
            layer = computeNdwi2(iface, dlg, conf, dir_raster_src, dir_dest, layersName["raster"], layersName["ndwi2"], extension_input_raster)       
            if layer is None :
                return None 
            QgsMapLayerRegistry.instance().addMapLayer(layer)
            legend.setLayerVisible(layer, False)
            extension_input_raster = EXT_RASTER
            
        else:
            rasterTreatName = layersName['raster']
            dir_raster_treat = dir_raster_src
     
    # Cas du traitement d'une image radar
    elif conf.rbRadar.isChecked():    
        
        # Despeckele Lee
        if dlg.rbDespeckLee.isChecked():
            rasterTreatName = layersName['lee']
            dir_raster_treat = dir_dest          
            layer = despeckeleLee(iface, dlg, conf, dir_raster_src, dir_dest, layersName["raster"], layersName["lee"], extension_input_raster)       
            if layer is None :
                return None
            QgsMapLayerRegistry.instance().addMapLayer(layer)
            legend.setLayerVisible(layer, False)
            extension_input_raster = EXT_RASTER
        
        # Despeckele Gamma
        elif dlg.rbDespeckGamma.isChecked():
            rasterTreatName = layersName['gamma']
            dir_raster_treat = dir_dest
            layer = despeckeleGamma(iface, dlg, conf, dir_raster_src, dir_dest, layersName["raster"], layersName["gamma"], extension_input_raster)       
            if layer is None :
                return None
            QgsMapLayerRegistry.instance().addMapLayer(layer)
            legend.setLayerVisible(layer, False)
            extension_input_raster = EXT_RASTER
            
        else:
            rasterTreatName = layersName['raster']
            dir_raster_treat = dir_raster_src
            
    li = layerList(iface)
    
    # Calcul du masque d'eau à partir du seuil estimé
    layers_list = computeMaskThreshold(iface, dlg, conf, dir_raster_treat, dir_dest, rasterTreatName, layersName['seuil'], seuilStr, extension_input_raster)
    if layers_list is None:
        return None

    # Informations de style
    for layer in layers_list :
        QgsMapLayerRegistry.instance().addMapLayer(layer)    
        layer.setDrawingStyle('SingleBandPseudoColor')
        fcn = QgsColorRampShader()
        fcn.setColorRampType(QgsColorRampShader.EXACT)
        lst = [QgsColorRampShader.ColorRampItem(1, QColor(QColor(0,0,255)))]
        fcn.setColorRampItemList(lst)
        shader = QgsRasterShader()
        shader.setRasterShaderFunction(fcn)
        renderer = QgsSingleBandPseudoColorRenderer(layer.dataProvider(),1, shader)
        if renderer:
            layer.setRenderer(renderer)
            if layer.renderer():
                layer.renderer().setOpacity(0.5)
        layer.triggerRepaint()
        legend.setLayerVisible(layer, False) 
        
    li = layerList(iface)
    messInfo(dlg,"Temps de calcul:  " + str(round(time.time() - start_time)) + " secondes.")
    messInfo(dlg,"") 
    
    global start_timeVect
    start_timeVect = time.time()    
         
    legend.setLayerVisible(li[layersName['raster']], False)
    layerSeuilName = layersName['seuil'] + seuilStr
    legend.setLayerVisible(li[layerSeuilName], True)
    li[layersName['raster']].triggerRepaint() 
    canvas.refresh() 
    extent = li[layersName['raster']].extent()
    canvas.setExtent(extent)
    
    # Retour avec le bon nom du fichier seuillé
    layersName['seuil'] = layerSeuilName
    
    return layersName

#########################################################################
# FONCTION runFilter()                                                  #
#########################################################################
def runFilter(iface, dlg, conf, dir_dest, rasterSeuilName, rasterFilterName):

    # Passage des parametres pour le filtrage
    layer = filterRaster(iface, dlg, conf, dir_dest, rasterSeuilName, rasterFilterName)

    if layer != None :
        # Informations de style
        canvas = iface.mapCanvas()
        renderer = canvas.mapRenderer()
        legend = iface.legendInterface() 
    
        QgsMapLayerRegistry.instance().addMapLayer(layer)
        layer.setDrawingStyle('SingleBandPseudoColor')
        fcn = QgsColorRampShader()
        fcn.setColorRampType(QgsColorRampShader.EXACT)
        lst = [QgsColorRampShader.ColorRampItem(1, QColor(QColor(255,177,67)))]
        fcn.setColorRampItemList(lst)
        shader = QgsRasterShader()
        shader.setRasterShaderFunction(fcn)
        renderer = QgsSingleBandPseudoColorRenderer(layer.dataProvider(),1, shader)
        if renderer:
            layer.setRenderer(renderer)
            if layer.renderer():
                layer.renderer().setOpacity(0.5)
                
        layer.triggerRepaint()
        legend.setLayerVisible(layer, True)   
        canvas.refresh()

        messInfo(dlg,(unicode(u"---> Lancez 'Filtrer' (fonction du radius choisi) pour appliquer un nouveau filtrage ou  'Vectoriser' pour poursuivre le traitement.  <---" )).encode('latin 1'))
        messInfo(dlg,"")    
        QMessageBox.information(None,u"Traitement de filtrage",unicode(u" Filtrage terminé.          " ).encode('latin 1')) 
    return 
    
#########################################################################
# FONCTION runVectorize()                                               #
#########################################################################    
def runVectorize(iface, dlg, assb, dir_dest, layersName, seuilStr):
    # Les paramètres du filtre (on peut le relancer) sont validés
    li = layerList(iface)
    dlg.btFilter.setEnabled(False)  
    
    if layersName['filtre'] in li:
        rasterToPolygonizeName = layersName['filtre']
    else:
        if layersName['seuil'] in li:
            rasterToPolygonizeName = layersName['seuil']
        else:
            messErreur(dlg,unicode(u"Pas de couche raster à vectoriser.").encode('latin 1')) 
            return 
            
    # Polygonisation        
    layer = polygonizeRaster(iface ,dlg, dir_dest, rasterToPolygonizeName, layersName['polygonize'])
    
    if layer != None :
        canvas = iface.mapCanvas()
        legend = iface.legendInterface()  
    
        # Informations de style
        symbols = layer.rendererV2().symbols()
        symbol = symbols[0]
        symbol.setColor(QColor.fromRgb(207,224,222))
        symbol.setAlpha(0.2)    
        legend.setLayerVisible(layer, True)
        legend.refreshLayerSymbology(layer)
        layer.triggerRepaint() 
        
        legend.setCurrentLayer(layer)
        canvas.refresh()        
                    
        # Mise a jour de la couche vecteur crée dans Qgqis                            
        if layersName['filtre'] in li:
            if layersName['seuil'] + seuilStr in li:
                legend.setLayerVisible(li[layersName['seuil'] + seuilStr], False) 
        else:
            if layersName['seuil'] + seuilStr in li:
                legend.setLayerVisible(li[layersName['seuil'] + seuilStr], True)         
            
        extent = li[layersName['raster']].extent()
        canvas.setExtent(extent)   
    
    messInfo(dlg,"Temps de vectorisation:  " + str(round(time.time() - start_timeVect)) + " secondes.")
    messInfo(dlg,"")      
    
    # Pour les zones d'eau on poursuit directement en vectorisant toutes les parcelles inondées après filtrage s'il y a lieu (pas de sélection manuelle de chaque parcelle...)
    extractPolygonesWaterZones(iface, dlg, assb, dir_dest, layersName)
    
    return    

#########################################################################
# FONCTION extractPolygonesWaterZones()                                            #
#########################################################################    
def extractPolygonesWaterZones(iface, dlg, assb, dir_dest, layersName):
    # Acte II: Nous avons enfin notre shape (type géométrique: polygone)
    # On poursuit le traitement jusqu'à l'extraction des zones en eau
    canvas = iface.mapCanvas()
    legend = iface.legendInterface()  
    li = layerList(iface)
           
    layer = None       
    if u'Vectorisé' in li:  
        layer = li[u'Vectorisé']
        legend.setLayerVisible(li[u"Vectorisé"], False)
    if 'Vectorized' in li:  
        layer = li['Vectorized']
        legend.setLayerVisible(li["Vectorized"], False)
    if 'Output layer' in li:  
        layer = li['Output layer']
        legend.setLayerVisible(li["Output layer"], False)
    if layersName['polygonize'] + EXT_VECTOR in li:  
        layer = li[layersName['polygonize'] + EXT_VECTOR]                  
        legend.setLayerVisible(li[layersName['polygonize'] + EXT_VECTOR], False)  
    if layersName['filtre'] in li:
        legend.setLayerVisible(li[layersName['filtre']], False)        
             
    layerWaterName = layersName['eau']
    layerWaterPath = dir_dest + os.sep + layerWaterName + EXT_VECTOR
    
    if os.path.exists(layerWaterPath):
        try:
            os.remove(layerWaterPath)
        except: 
            QMessageBox.information(None,"Attention !!!", unicode(layerWaterPath + " ne peut pas être effacé. Vérifiez que le fichier n'est pas verrouillé par un autre utilisateur ou que le fichier peut être effacé manuellement (droits d'écriture sur le répertoire).").encode('latin 1'))         
            messErreur(dlg, unicode(layerWaterPath + u" ne peut pas être effacé.").encode('latin 1')) 
            return    
    
    messInfo(dlg,unicode(u"Création de la couche: " + layerWaterName + ".").encode('latin 1'))
    messInfo(dlg,"")
            
    if layer is None :
        messErreur(dlg,unicode(layerWaterName + u" ne peut pas être chargé.").encode('latin 1')) 
        return

    crs = layer.crs()
    crsWkt = crs.toWkt()    
    layerWater = QgsVectorLayer("Polygon?crs=" + crsWkt, layerWaterName, "memory")
    
    if layerWater:
        QgsMapLayerRegistry.instance().addMapLayer(layerWater)
    else:
        messErreur(dlg,unicode(layerWaterName + u" ne peut pas être chargé.").encode('latin 1')) 
        return        

    li = layerList(iface)
    symbols = li[layerWaterName].rendererV2().symbols()
    symbol = symbols[0]
    symbol.setColor(QColor.fromRgb(0,0,255))
    
    provider = li[layerWaterName].dataProvider()
       
    fields = layer.pendingFields()
    wfields = QgsFields()
    for f in fields:
        provider.addAttributes([QgsField(f.name(), f.type())])
        wfields.append(QgsField(f.name(), f.type()))
        
    writer = QgsVectorFileWriter(layerWaterPath, "CP1250", wfields, QGis.WKBPolygon, crs, FORMAT_VECT)
    
    if writer.hasError() != QgsVectorFileWriter.NoError:
        messErreur(dlg,unicode(layerWaterPath+u" ne peut pas être créé.").encode('latin 1'))      
        return
    
    li[layerWaterName].startEditing() 
    
    # Zones d'eau on récupère tous les polygones
    for elem in layer.getFeatures():
        if elem['DN'] == 1:
            messInfo(dlg, "----> Ajout du polygone de Fid: " + str(elem.id()))
            geom = elem.geometry()                                             
            feature = QgsFeature(fields)
            feature.setGeometry(geom)
            feature.setAttributes(elem.attributes())
            provider.addFeatures([feature])
            writer.addFeature(feature) 

    del writer
        
    li[layerWaterName].commitChanges()

    legend.setLayerVisible(li[layerWaterName], False)
    legend.refreshLayerSymbology(li[layerWaterName])
    li[layerWaterName].triggerRepaint() 
    canvas.refresh()
             
    legend.setLayerVisible(li[layersName['seuil']], False) 
    li[layersName['seuil']].triggerRepaint() 
    
    # Nous avons les poygones des zones immergées le traitement s'arrête ici
    legend.setLayerVisible(li[layerWaterName], True)
    li[layerWaterName].triggerRepaint() 
    
    canvas.refresh()
    extent = li[layerWaterName].extent()
    canvas.setExtent(extent)         

    messInfo(dlg,"Temps total de traitement:  " + str(round(time.time() - start_time)) + " secondes.")
    messInfo(dlg,"")     
    
    endTreatment(iface, dlg, assb, layersName)   
    
    return

#########################################################################
# FONCTION endTreatment()                                               #
#########################################################################
def endTreatment(iface, dlg, assb, layersName):

    canvas = iface.mapCanvas()
    legend = iface.legendInterface()
    li = layerList(iface)

    messInfo(dlg,(unicode(u"Traitement terminé.")).encode('latin 1'))
    messInfo(dlg,(unicode(u"Note: Le rafraîchissement de l'écran en fin de traitement peut prendre un certain temps (fonction de la taille du raster).")).encode('latin 1'))
    messInfo(dlg,"---------------------------------------------------------------------------------------------------")        
    canvas.refresh()
                
    layerRasterName = layersName['raster']                
    legend.setLayerVisible(li[layerRasterName], True)
    li[layerRasterName].triggerRepaint() 
    extent = li[layerRasterName].extent()
    canvas.setExtent(extent)    

    # Liste des rasteurs
    dlg.clayer_raster.clear()
    layers = legend.layers()
    index = 0
    indexCoucheRaster = 0
    
    for layer in layers:
        if layer.type() == QgsMapLayer.RasterLayer:
            dlg.clayer_raster.addItem(layer.name())
            if layer.name() == layerRasterName:
                indexCoucheRaster = index
            index+=1
    dlg.clayer_raster.setCurrentIndex(indexCoucheRaster)  
    
    # Liste vecteurs
    assb.clayer_vector.clear()
    layers = legend.layers()
    index = 0
    indexCoucheVector = 0
    for layer in layers:
        if layer.type() == QgsMapLayer.VectorLayer:
            assb.clayer_vector.addItem(layer.name())
            if 'emprise_zone' in layersName.keys() :
                if layer.name() == layersName['emprise_zone']:
                    indexCoucheVector = index
            index+=1
    assb.clayer_vector.setCurrentIndex(indexCoucheVector)  

    return