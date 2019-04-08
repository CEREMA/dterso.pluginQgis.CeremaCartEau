# -*- coding: utf-8 -*-
"""
/***************************************************************************
processingRaster
                                 A QGIS plugin
 Cart'Eau. Plugin Cerema.
                              -------------------
        begin                : 2018-07-27
        modification         : 
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
import platform
import processing

from tools import *
from qgis.analysis import QgsRasterCalculator, QgsRasterCalculatorEntry, QgsGeometryAnalyzer, QgsOverlayAnalyzer

#########################################################################
# FONCTION computeNdvi()                                                #
#########################################################################
def computeNdvi(iface, dlg, conf, dir_raster_src, dir_dest, rasterName, ndviName, extension_input_raster):   
    li = layerList(iface)
    
    messInfo(dlg,"Calcul du NDVI.")
    messInfo(dlg,"")
    
    rasterPath = dir_raster_src + os.sep + rasterName + extension_input_raster
    ndviPath = dir_dest + os.sep + ndviName + EXT_RASTER
    
    # Test si c'est une image multibande
    cols, rows, bands = getGeometryImage(rasterPath)
    if bands < 4 :
        QMessageBox.information(None,"Attention !!!",unicode(ndviPath+u" ne peut pas être créé. L'image raster d'entrée n'a pas un nombre de bande suffisant.").encode('latin 1'))         
        messErreur(dlg,unicode(ndviPath+u" ne peut pas être créé.").encode('latin 1')) 
        return None
        
    # selection des bandes pour le calcul du NDVI
    num_channel_red = 0
    num_channel_nir = 0
    d = conf.channelOrderDic
    key = "Red"
    if key in conf.channelOrderDic.keys():
        num_channel_red = int(conf.channelOrderDic[key])
    key = "NIR"    
    if key in conf.channelOrderDic.keys():
        num_channel_nir = int(conf.channelOrderDic[key])
        
    if (num_channel_red == 0 or num_channel_nir == 0):
        QMessageBox.information(None,"Attention !!!",unicode(ndviPath+u" ne peut pas être créé. NDVI needs Red and NIR channels to be computed).").encode('latin 1'))         
        messErreur(dlg,unicode(ndviPath+u" ne peut pas être créé.").encode('latin 1')) 
        return None 
    
    # Suppression du fichier de sortie si il existe 
    if os.path.exists(ndviPath):
        try:
            os.remove(ndviPath)            
        except: 
            QMessageBox.information(None,"Attention !!!",unicode(ndviPath+u" ne peut pas être effacé. Vérifiez que le fichier n'est pas verrouillé par un autre utilisateur ou que le fichier peut être effacé manuellement (droits d'écriture sur le répertoire).").encode('latin 1'))         
            messErreur(dlg,unicode(ndviPath+u" ne peut pas être effacé.").encode('latin 1')) 
            return None     

    # Calcul
    if conf.rbOTB.isChecked():    
        # Calculatrice raster OTB                        
        try:
            expression = '(im1b%s - im1b%s)/(im1b%s + im1b%s)' %(str(num_channel_nir), str(num_channel_red), str(num_channel_nir), str(num_channel_red))
            processing.runalg('otb:bandmath', rasterPath, '128',expression, ndviPath)
        except:
            messErreur(dlg,"Erreur de traitement sur otb:bandmath.")
            return None         
    else: 
        # Calculatrice raster QGIS
        entries = []
        
        raster = li[rasterName]
        extent = raster.extent()
        height = raster.height()
        width = raster.width()        

        b_red = QgsRasterCalculatorEntry()
        b_red.ref = 'b@%s' %(str(num_channel_red))
        b_red.raster = raster
        b_red.bandNumber = num_channel_red
        entries.append(b_red)

        b_nir = QgsRasterCalculatorEntry()
        b_nir.ref = 'b@%s' %(str(num_channel_nir))
        b_nir.raster = raster
        b_nir.bandNumber = num_channel_nir
        entries.append(b_nir)
                                 
        expression =  '(b@%s - b@%s)/(b@%s + b@%s)' %(str(num_channel_nir), str(num_channel_red), str(num_channel_nir), str(num_channel_red))      
        calc = QgsRasterCalculator( expression, ndviPath, FORMAT_IMA, extent, width, height, entries )

        ret = calc.processCalculation()   
           
        if ret != 0:
            QMessageBox.information(None,"Attention !!!",unicode(u" Erreur d'exécution, cela peut être du à une insuffisance mémoire, image trop volumineuse.").encode('latin 1'))        
            messErreur(dlg,u"Erreur lors du lancement de QgsRasterCalculator.")       
            return None
            
    if os.path.exists(ndviPath):
        ndvi = QgsRasterLayer(ndviPath, ndviName)
    else:
        QMessageBox.information(None,"Attention !!!",unicode(ndviPath+u" n'a pas été créé. Vérifiez que le fichier n'est pas verrouillé par un autre utilisateur ou que le fichier peut être effacé manuellement (droits d'écriture sur le répertoire).").encode('latin 1'))        
        messErreur(dlg,unicode(ndviPath+u" n'a pas été créé.").encode('latin 1'))
        return None             
        
    if not ndvi.isValid():
        messErreur(dlg,unicode(ndviPath+u" ne peut pas être chargé.").encode('latin 1'))
        return None         

    return ndvi

#########################################################################
# FONCTION computeNdwi2()                                               #
#########################################################################
def computeNdwi2(iface, dlg, conf, dir_raster_src, dir_dest, rasterName, ndwi2Name, extension_input_raster): 
    li = layerList(iface)
    
    messInfo(dlg,"Calcul du NDWI2.")
    messInfo(dlg,"")
    
    rasterPath = dir_raster_src + os.sep + rasterName + extension_input_raster
    ndwi2Path = dir_dest + os.sep + ndwi2Name + EXT_RASTER
    
    # Test si c'est une image multibande
    cols, rows, bands = getGeometryImage(rasterPath)
    if bands < 4 :
        QMessageBox.information(None,"Attention !!!",unicode(ndwi2Path+u" ne peut pas être créé. L'image rasterraster d'entrée  n'a pas un nombre de bande suffisant.").encode('latin 1'))         
        messErreur(dlg,unicode(ndwi2Path+u" ne peut pas être créé.").encode('latin 1')) 
        return None
        
    # Selection des bandes pour le calcul du NDWI2
    num_channel_green = 0
    num_channel_nir = 0
    d = conf.channelOrderDic
    key = "Green"
    if key in conf.channelOrderDic.keys():
        num_channel_green = int(conf.channelOrderDic[key])
    key = "NIR"    
    if key in conf.channelOrderDic.keys():
        num_channel_nir = int(conf.channelOrderDic[key])
        
    if (num_channel_green == 0 or num_channel_nir == 0):
        QMessageBox.information(None,"Attention !!!",unicode(ndviPath+u" ne peut pas être créé. NDVI needs Green and NIR channels to be computed).").encode('latin 1'))         
        messErreur(dlg,unicode(ndviPath+u" ne peut pas être créé.").encode('latin 1')) 
        return None  
    
    # Suppression du fichier de sortie si il existe 
    if os.path.exists(ndwi2Path):
        try:
            os.remove(ndwi2Path)            
        except: 
            QMessageBox.information(None,"Attention !!!",unicode(ndwi2Path + u" ne peut pas être effacé. Vérifiez que le fichier n'est pas verrouillé par un autre utilisateur ou que le fichier peut être effacé manuellement (droits d'écriture sur le répertoire).").encode('latin 1'))         
            messErreur(dlg,unicode(ndwi2Path + u" ne peut pas être effacé.").encode('latin 1')) 
            return None     

    # Calcul
    if conf.rbOTB.isChecked():    
        # Calculatrice raster OTB                        
        try:
            expression = '(im1b%s - im1b%s)/(im1b%s + im1b%s)' %(str(num_channel_green), str(num_channel_nir), str(num_channel_green), str(num_channel_nir))
            processing.runalg('otb:bandmath', rasterPath, '128',expression, ndwi2Path)
        except:
            messErreur(dlg,u"Erreur de traitement sur otb:bandmath.")
            return None         
    else: 
        # Calculatrice raster QGIS
        entries = []
        
        raster = li[rasterName]
        extent = raster.extent()
        height = raster.height()
        width = raster.width()        

        b_green = QgsRasterCalculatorEntry()
        b_green.ref = 'b@%s' %(str(num_channel_green))
        b_green.raster = raster
        b_green.bandNumber = num_channel_green
        entries.append(b_green)

        b_nir = QgsRasterCalculatorEntry()
        b_nir.ref = 'b@%s' %(str(num_channel_nir))
        b_nir.raster = raster
        b_nir.bandNumber = num_channel_nir
        entries.append(b_nir)
                                 
        expression =  '(b@%s - b@%s)/(b@%s + b@%s)' %(str(num_channel_green), str(num_channel_nir), str(num_channel_green), str(num_channel_nir))
        calc = QgsRasterCalculator( expression, ndwi2Path, FORMAT_IMA, extent, width, height, entries )

        ret = calc.processCalculation()   
           
        if ret != 0:
            QMessageBox.information(None,"Attention !!!",unicode(u" Erreur d'exécution, cela peut être du à une insuffisance mémoire, image trop volumineuse.").encode('latin 1'))
            messErreur(dlg,"Erreur lors du lancement de QgsRasterCalculator.")       
            return None
            
    if os.path.exists(ndwi2Path):
        ndwi2 = QgsRasterLayer(ndwi2Path, ndwi2Name)
    else:
        QMessageBox.information(None,"Attention !!!",unicode(ndwi2Path + u" n'a pas été créé. Vérifiez que le fichier n'est pas verrouillé par un autre utilisateur ou que le fichier peut être effacé manuellement (droits d'écriture sur le répertoire).").encode('latin 1'))        
        messErreur(dlg,unicode(ndwi2Path + u" n'a pas été créé.").encode('latin 1'))
        return None             
        
    if not ndwi2.isValid():
        messErreur(dlg,unicode(ndwi2Path + u" ne peut pas être chargé.").encode('latin 1'))
        return None         

    return ndwi2

#########################################################################
# FONCTION despeckeleLee()                                              #
#########################################################################
def despeckeleLee(iface, dlg, conf, dir_raster_src, dir_dest, rasterName, leeName, extension_input_raster): 
    li = layerList(iface)
    
    messInfo(dlg,"Calcul du despeckele Lee.")
    messInfo(dlg,"")
    
    rasterPath = dir_raster_src + os.sep + rasterName + extension_input_raster
    leePath = dir_dest + os.sep + leeName + EXT_RASTER
    radius = dlg.spinBoxRadius.value()
    nb_looks = dlg.doubleSpinBoxLooks.value()
        
    # Suppression du fichier de sortie si il existe 
    if os.path.exists(leePath):
        try:
            os.remove(leePath)            
        except: 
            QMessageBox.information(None,"Attention !!!",unicode(leePath+u" ne peut pas être effacé. Vérifiez que le fichier n'est pas verrouillé par un autre utilisateur ou que le fichier peut être effacé manuellement (droits d'écriture sur le répertoire).").encode('latin 1'))         
            messErreur(dlg,unicode(leePath+u" ne peut pas être effacé.").encode('latin 1')) 
            return None     

    # Calcul
    if conf.rbOTB.isChecked():    
        # Despeckele Lee par  OTB       
        try:
            processing.runalg('otb:despecklelee', rasterPath, '128', 0, radius, nb_looks, leePath)
        except:
            messErreur(dlg,u"Erreur de traitement sur otb:despeckle.")
            return None         
    else: 
        # Despeckele Lee par GRASS
        entries = []
        
        raster = li[rasterName]
        extent = raster.extent()
        height = raster.height()
        width = raster.width()   

        try:
            # En attente de faire fonctionner le despeckle avec GRASS !!!
            print("DEBUG  lancement grass:despeckle Lee")
            processing.runalg('grass7:i.despeckle', rasterPath, 'lee', radius, nb_looks, leePath)
            print("DEBUG  fin grass:despeckle Lee")
        except:
            messErreur(dlg,"Erreur de traitement sur grass:despeckle.")
            return None    
 
    if os.path.exists(leePath):
        lee = QgsRasterLayer(leePath, leeName)
    else:
        QMessageBox.information(None,"Attention !!!",unicode(leePath+u" n'a pas été créé. Vérifiez que le fichier n'est pas verrouillé par un autre utilisateur ou que le fichier peut être effacé manuellement (droits d'écriture sur le répertoire).").encode('latin 1'))        
        messErreur(dlg,unicode(leePath+u" n'a pas été créé.").encode('latin 1'))
        return None             
        
    if not lee.isValid():
        messErreur(dlg,unicode(leePath+u" ne peut pas être chargé.").encode('latin 1'))
        return None         

    return lee

#########################################################################
# FONCTION despeckeleGamma()                                            #
#########################################################################
def despeckeleGamma(iface, dlg, conf, dir_raster_src, dir_dest, rasterName, gammaName, extension_input_raster):  
    li = layerList(iface)
    
    messInfo(dlg,"Calcul du despeckele Gamma.")
    messInfo(dlg,"")
    
    rasterPath = dir_raster_src + os.sep + rasterName + extension_input_raster
    gammaPath = dir_dest + os.sep + gammaName + EXT_RASTER
    radius = dlg.spinBoxRadius.value()
    nb_looks = dlg.doubleSpinBoxLooks.value()
    
    # Suppression du fichier de sortie si il existe    
    if os.path.exists(gammaPath):
        try:
            os.remove(gammaPath)            
        except: 
            QMessageBox.information(None,"Attention !!!",unicode(gammaPath + u" ne peut pas être effacé. Vérifiez que le fichier n'est pas verrouillé par un autre utilisateur ou que le fichier peut être effacé manuellement (droits d'écriture sur le répertoire).").encode('latin 1'))         
            messErreur(dlg,unicode(gammaPath + u" ne peut pas être effacé.").encode('latin 1')) 
            return None     

    # Calcul
    if conf.rbOTB.isChecked():    
        # Despeckele Gamma par OTB
        try:
            processing.runalg('otb:despecklegammamap', rasterPath, '128', 0, radius, nb_looks, gammaPath)
        except:
            messErreur(dlg,"Erreur de traitement sur otb:despeckle.")
            return None         
    else: 
        # Despeckele Gamma par GRASS
        entries = []
        
        raster = li[rasterName]
        extent = raster.extent()
        height = raster.height()
        width = raster.width()
        
        try:
            # En attente de faire fonctionner le despeckle avec GRASS !!!
            print("DEBUG  lancement grass:despeckle Gamma")
            processing.runalg('grass:i.despeckle', rasterPath, 'gamma', radius, nb_looks, gammaPath)
            print("DEBUG  fin grass:despeckle Gamma")
        except:
            messErreur(dlg,u"Erreur de traitement sur grass:despeckle.")
            return None   
            
    if os.path.exists(gammaPath):
        gamma = QgsRasterLayer(gammaPath, gammaName)
    else:
        QMessageBox.information(None,"Attention !!!",unicode(gammaPath + u" n'a pas été créé. Vérifiez que le fichier n'est pas verrouillé par un autre utilisateur ou que le fichier peut être effacé manuellement (droits d'écriture sur le répertoire).").encode('latin 1'))        
        messErreur(dlg,unicode(gammaPath + u" n'a pas été créé.").encode('latin 1'))
        return None             
        
    if not gamma.isValid():
        messErreur(dlg,unicode(gammaPath + u" ne peut pas être chargé.").encode('latin 1'))
        return None         

    return gamma
    
#########################################################################
# FONCTION computeMaskThreshold()                                       #
#########################################################################    
def computeMaskThreshold(iface, dlg, conf, dir_raster_treat, dir_dest, rasterTreatName, rasterSeuilName, seuilStr, extension_input_raster):
    canvas = iface.mapCanvas()
    renderer = canvas.mapRenderer()
    legend = iface.legendInterface()  
    
    # Calcul du masque d'eau fonction du seuil choisi        
    delta = dlg.delta.text()
    seuil = float(seuilStr)
    if not dlg.rbSeuil.isChecked():
        delta = 0
        values_seuil_list = [0]
    else:
        delta = float(delta)
        values_seuil_list = [-1, 0, +1]        
                        
    messInfo(dlg,"Seuil: " + seuilStr)
    messInfo(dlg,"")  

    if dlg.rbComputeNdvi.isChecked():
        direction = True
    elif dlg.rbComputeNdwi2.isChecked():    
        direction = False
    else:
        direction = True
        
    if direction :
        direction_operator_str = "<"   # Operateur inferieur
    else :    
        direction_operator_str = ">"   # Operateur superieur
        
    if conf.rbOTB.isChecked(): 
        # Calculatrice OTB                                
        init = 41253
    else:
        # Calculatrice QGIS
        init = 32526    

    masks_list = []        
    for i in values_seuil_list:
        newSeuil = seuil + i*delta
        
        if float(newSeuil) == 0:
            newSeuilStr = '0'
            newSeuil10Str = '0'
        else:
            newSeuilStr = str(newSeuil)
            newSeuil10Str = str(newSeuil*10)
            while newSeuilStr[0] == '0' and len(newSeuilStr) >= 2 and newSeuilStr[1] != '.' :
                newSeuilStr = newSeuilStr[1:]
            if '.' in newSeuilStr :
                while newSeuilStr[-1] == '0': 
                    newSeuilStr = newSeuilStr[:len(newSeuilStr)-1]
                if  newSeuilStr[-1] == '.':           
                    newSeuilStr = newSeuilStr[:len(newSeuilStr)-1]
            
        if newSeuil != init:
            init = newSeuil
            
            if delta == 0:
                layerSeuilName = rasterSeuilName + seuilStr
            else:
                layerSeuilName = rasterSeuilName + newSeuilStr
                    
            layerSeuilPath = dir_dest + os.sep + layerSeuilName + EXT_RASTER
                        
            if os.path.exists(layerSeuilPath):
                try:
                    os.remove(layerSeuilPath)
                except: 
                    QMessageBox.information(None,"Attention !!!",unicode(layerSeuilPath + u" ne peut pas être effacé. Vérifiez que le fichier n'est pas verrouillé par un autre utilisateur ou que le fichier peut être effacé manuellement (droits d'écriture sur le répertoire).").encode('latin 1'))                    
                    messErreur(dlg,unicode(layerSeuilPath + u" ne peut pas être effacé.").encode('latin 1')) 
                    return None                
        
            messInfo(dlg, u"Calcul du masque 'Eau' avec le seuil: " + newSeuilStr)
            messInfo(dlg,"")
            
            # Calculatrice OTB 
            if conf.rbOTB.isChecked():
                rasterTreatPath = dir_raster_treat + os.sep + rasterTreatName + extension_input_raster            
                try:
                    processing.runalg('otb:bandmath', rasterTreatPath, '128','im1b1' + direction_operator_str + newSeuilStr + '?1:2',layerSeuilPath)                                                             
                except:                                        
                    messErreur(dlg,u"Erreur lors du lancement de otb:bandmath.")
                       
                if os.path.exists(layerSeuilPath):
                    pass
                else:
                    # Si vous êtes observateur même calcul mais syntaxe différente... l'un ou l'autre peut fonctionner (ou plus important ne pas fonctionner) 
                    # On tente notre chance avec cette syntaxe
                    try:
                        processing.runalg('otb:bandmath', rasterTreatPath, '128','if(im1b1' + direction_operator_str + newSeuilStr + ',1,2)' ,layerSeuilPath) 
                    except:                    
                        messErreur(dlg,u"Erreur lors du lancement de otb:bandmath.")
                        return None
            # Fin OTB
            
            # Calculatrice QGIS             
            else:
                entries = []
                li = layerList(iface)
                raster = li[rasterTreatName]         
                extent = raster.extent()
                height = raster.height()
                width = raster.width()                    

                s1 = QgsRasterCalculatorEntry()
                s1.ref = 's@1'
                s1.raster = raster
                s1.bandNumber = 1
                entries.append(s1)                        
    
                if platform.system()=="Linux":
                    # Bug calculatrice raster sous linux
                    calc = QgsRasterCalculator( '(10*s@1' + direction_operator_str + newSeuil10Str + ')', layerSeuilPath, FORMAT_IMA, extent, width, height, entries )
                    
                else:
                    calc = QgsRasterCalculator( '(s@1' + direction_operator_str + newSeuilStr + ')', layerSeuilPath, FORMAT_IMA, extent, width, height, entries )
                
                ret = calc.processCalculation()   
                if ret != 0:
                    QMessageBox.information(None,"Attention !!!",unicode(u" Erreur d'exécution, cela peut être du à une insuffisance mémoire, image trop volumineuse.").encode('latin 1'))
                    messErreur(dlg,u"Erreur de traitement sur QgsRasterCalculator.")              
                    return None

            # Fin QGIS  
            
            if os.path.exists(layerSeuilPath):
                mask = QgsRasterLayer(layerSeuilPath, layerSeuilName)
            else:
                QMessageBox.information(None,"Attention !!!", unicode(layerSeuilPath + u" n'a pas été créé. Vérifiez que le fichier n'est pas verrouillé par un autre utilisateur ou que le fichier peut être effacé manuellement (droits d'écriture sur le répertoire).").encode('latin 1'))                      
                messErreur(dlg,unicode(layerSeuilPath + u" n'a pas été créé.").encode('latin 1'))
                return None
          
            if not mask.isValid():
                messErreur(dlg,unicode(layerSeuilPath + u" ne peut pas être chargé.").encode('latin 1'))
                return None                         
                
            # Add list pour return
            masks_list.append(mask)     
    
    return masks_list

#########################################################################
# FONCTION filterRaster()                                               #
#########################################################################
def filterRaster(iface, dlg, conf, dir_dest, rasterSeuilName, rasterFilterName):
    # Filtre que l'on propose pour éliminer les zones d'eau mineures 
    li = layerList(iface)    
    
    layerSeuil = li[rasterSeuilName]
    layerSeuilPath = dir_dest + os.sep + rasterSeuilName + EXT_RASTER
    layerFiltreIlotsPath = dir_dest + os.sep + rasterFilterName + EXT_RASTER
        
    for elem in li:
        if elem == rasterFilterName:
            QgsMapLayerRegistry.instance().removeMapLayer(li[elem].id())
                    
    if os.path.exists(layerFiltreIlotsPath):
        try:
            os.remove(layerFiltreIlotsPath)
        except: 
            QMessageBox.information(None,"Attention !!!", unicode(layerFiltreIlotsPath + u" ne peut pas être effacé. Vérifiez que le fichier n'est pas verrouillé par un autre utilisateur ou que le fichier peut être effacé manuellement (droits d'écriture sur le répertoire).").encode('latin 1'))         
            messErreur(dlg,unicode(layerFiltreIlotsPath + u" ne peut pas être effacé.").encode('latin 1')) 
            return None          
            
    # Filtrage OTB 
    if conf.rbOTB.isChecked(): 

        seuilCMR = dlg.seuilCMR.text()
        if seuilCMR == '':
            QMessageBox.information(None,u"Attention !!!","Valeur de radius incorrecte !")
            return None   
        try: 
            seuilCMR = int(seuilCMR)
        except:
            QMessageBox.information(None,u"Attention !!!","Valeur de radius incorrecte !")
            return None
        if not 0 <= int(seuilCMR) <= 30:
            QMessageBox.information(None,u"Attention !!!","Valeur de radius incorrecte !")
            return None
 
        messInfo(dlg,u"Lancement du filtre 'Classification Map Regularization' sur le raster: " + rasterSeuilName)
        messInfo(dlg,"Radius: " + str(seuilCMR))
        messInfo(dlg,"")

        try:
            versionQgis = QGis.QGIS_VERSION
            if versionQgis[0:4] == "2.18" :
                # Cas d'appel a la fonction OTB classificationmapregularization en version QGis 2.18
                processing.runalg('otb:classificationmapregularization', layerSeuilPath, seuilCMR, True, 0, 0, False, 0, 128, layerFiltreIlotsPath)
            else :
                # Cas d'appel a la fonction OTB classificationmapregularization en version QGis 2.16
                processing.runalg('otb:classificationmapregularization', layerSeuilPath, seuilCMR, True, 0, 0, 128, layerFiltreIlotsPath)
        except:
            messErreur(dlg,u"Erreur de traitement par (filtre Classification Map Regularization) de %s !!!" %(layerFiltreIlotsPath)) 
            return None
    # Fin OTB
            
    # Filtrage QGIS (Gdal)            
    else:
    
        seuilTamiser = dlg.seuilTamiser.text()
        if seuilTamiser == '':
            QMessageBox.information(None,u"Attention !!!","Valeur de seuil incorrecte !")
            return None
        try: 
            seuilTamiser = int(seuilTamiser)
        except:
            QMessageBox.information(None,u"Attention !!!","Valeur de seuil incorrecte !")
            return None
        if not 0 <= int(seuilTamiser) < 10000:
            QMessageBox.information(None,u"Attention !!!","Valeur de seuil incorrecte !")
            return None
            
        if dlg.rbTamiser4.isChecked():
            conn = 0
        else:
            conn = 1
            
        messInfo(dlg,u"Lancement du filtrage sur le raster: " + rasterSeuilName)
        messInfo(dlg,"Seuil: " + str(seuilTamiser))
        messInfo(dlg,"")
        
        try:
            processing.runalg('gdalogr:sieve', layerSeuil,seuilTamiser,conn,layerFiltreIlotsPath)
        except:
            messErreur(dlg,u"Erreur de traitement par gdalogr:sieve (filtre) de %s !!!"%(layerFiltreIlotsPath))
            return None
    # Fin QGIS
    
    if os.path.exists(layerFiltreIlotsPath):
        layer = QgsRasterLayer(layerFiltreIlotsPath, rasterFilterName)
    else:
        QMessageBox.information(None,u"Attention !!!",unicode(layerFiltreIlotsPath + u" n'a pas été créé. Vérifiez que le fichier n'est pas verrouillé par un autre utilisateur ou que le fichier peut être effacé manuellement (droits d'écriture sur le répertoire).").encode('latin 1'))     
        messErreur(dlg,unicode(layerFiltreIlotsPath + u" n'a pas été créé.").encode('latin 1'))
        return None
    
    if not layer.isValid():
        messErreur(dlg,unicode(layerFiltreIlotsPath + u" ne peut pas être chargé.").encode('latin 1'))
        return None
    
    return layer

#########################################################################
# FONCTION polygonizeRaster()                                           #
#########################################################################
def polygonizeRaster(iface, dlg, dir_dest, rasterToPolygonizeName, vectorPolygonName):
    # Fonction de vectorisation
    li = layerList(iface)
    
    rasterToPolygonize = li[rasterToPolygonizeName]
                        
    messInfo(dlg,"Vectorisation du raster: " + rasterToPolygonizeName)
    messInfo(dlg,"")    
    
    outputVectorPath = dir_dest + os.sep + vectorPolygonName + EXT_VECTOR
              
    if os.path.exists(outputVectorPath):
        try:
            os.remove(outputVectorPath)
        except:            
            QMessageBox.information(None,"Attention !!!",unicode(outputVectorPath + u" ne peut pas être effacé. Vérifiez que le fichier n'est pas verrouillé par un autre utilisateur ou que le fichier peut être effacé manuellement.").encode('latin 1'))
            messErreur(dlg,unicode(outputVectorPath  + u" ne peut pas être effacé.").encode('latin 1')) 
            return None
        
    if rasterToPolygonize:
        try:
            processing.runandload('gdalogr:polygonize', rasterToPolygonize,'DN',  outputVectorPath)
        except:
            messErreur(dlg,unicode(u"Erreur pendant l'exécution de gdalogr:polygonize.").encode('latin 1')) 
            return None
    else:
        messErreur(dlg,u"fin de traitement sur gdalogr:polygonize, " + rasterToPolygonizeName + " n'est pas valide.")
        return None
        
    layer = None
    for elem in li:
        if elem in (u'Vectorisé', 'Vectorized', 'Output layer' ,vectorPolygonName + EXT_VECTOR):
            layer = li[elem]    
    
    if not layer:
         messErreur(dlg,unicode(u"fin de traitement sur gdalogr:polygonize. Vérifiez que vous avez bien les droits d'écriture sur le répertoire: " + dir_dest).encode('latin 1'))       
         return None
        
    messInfo(dlg,"Fin vectorisation du raster: " + rasterToPolygonizeName)
    messInfo(dlg,"") 
    
    return layer
    