#!/usr/bin/env python
#--!-- coding: utf8 --!--
 



from qt import *
from enums import *

from enum import Enum
from lxml import etree as ET

from functions import *

class outlineModel(QAbstractItemModel):
    
    newStatuses = pyqtSignal()
    
    def __init__(self):
        QAbstractItemModel.__init__(self)
        
        self.rootItem = outlineItem(self, title="root")
        self.generateStatuses()
    
    def index(self, row, column, parent):
        
        if not self.hasIndex(row, column, parent):
            return QModelIndex()
        
        if not parent.isValid():
            parentItem = self.rootItem
        else:
            parentItem = parent.internalPointer()
            
        childItem = parentItem.child(row)
        if childItem:
            return self.createIndex(row, column, childItem)
        else:
            return QModelIndex()
    
    def indexFromItem(self, item, column=0):
        if item == self.rootItem:
            return None
        
        parent = item.parent()
        if not parent:
            parent = self.rootItem
        
        if len(parent.children()) == 0:
            return None
        
        #print(item.title(), [i.title() for i in parent.children()])
        
        row = parent.children().index(item)
        col = column
        return self.createIndex(row, col, item)
    
    def parent(self, index=QModelIndex()):
        if not index.isValid():
            return QModelIndex()
        
        childItem = index.internalPointer()
        parentItem = childItem.parent()
        
        if parentItem == self.rootItem:
            return QModelIndex()
        
        return self.createIndex(parentItem.row(), 0, parentItem)
    
    def rowCount(self, parent=QModelIndex()):
        if parent.column() > 0:
            return 0
        
        if not parent.isValid():
            parentItem = self.rootItem
        else:
            parentItem = parent.internalPointer()
            
        return parentItem.childCount()
    
    def columnCount(self, parent=QModelIndex()):
        if parent.isValid():
            return parent.internalPointer().columnCount()
        else:
            return self.rootItem.columnCount()
    
    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return QVariant()
        
        item = index.internalPointer()
        return item.data(index.column(), role)
    
    def setData(self, index, value, role=Qt.EditRole):
        item = index.internalPointer()
        item.setData(index.column(), value, role)
        
        if index.column() == Outline.status.value:
            self.generateStatuses()
        
        self.dataChanged.emit(index.sibling(index.row(), 0), 
                              index.sibling(index.row(), max([i.value for i in Outline])))
        return True
        
    
    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            if section == Outline.title.value:
                return "Titre"
            elif section == Outline.wordCount.value:
                return "Mots"
            elif section == Outline.goal.value:
                return "Goal"
            elif section == Outline.goalPercentage.value:
                return "%"
            else:
                return [i.name for i in Outline][section]
        
        elif role == Qt.SizeHintRole:
            if section == Outline.compile.value:
                return QSize(40, 30)
            elif section == Outline.goalPercentage.value:
                return QSize(100, 30)
            else:
                return QVariant()
        else:
            return QVariant()
        
        
        
        return True
    
    #################### DRAG AND DROP ########################
    # http://doc.qt.io/qt-5/model-view-programming.html#using-drag-and-drop-with-item-views
    
    def flags(self, index):
        #FIXME when dragging folders, sometimes flags is not called
        
        flags = QAbstractItemModel.flags(self, index) | Qt.ItemIsEditable 
        
        if index.isValid() and index.internalPointer().isFolder() and index.column() == 0:
            flags |= Qt.ItemIsDragEnabled | Qt.ItemIsDropEnabled 
            
        elif index.isValid() and index.column() == 0:
            flags |= Qt.ItemIsDragEnabled
            
        elif not index.isValid():
            flags |= Qt.ItemIsDropEnabled
        
        if index.isValid() and index.column() == Outline.compile.value:
            flags |= Qt.ItemIsUserCheckable
        
        if index.column() in [i.value for i in [Outline.wordCount, Outline.goalPercentage]]:
            flags &= ~ Qt.ItemIsEditable
        
        return flags
    
    def mimeTypes(self):
        return ["application/xml"]
    
    def mimeData(self, indexes):
        mimeData = QMimeData()
        encodedData = ""
        
        root = ET.Element("outlineItems")
        
        for index in indexes:
            if index.isValid() and index.column() == 0:
                item = ET.XML(index.internalPointer().toXML())
                root.append(item)
        
        encodedData = ET.tostring(root)
        
        mimeData.setData("application/xml", encodedData)
        return mimeData
    
    def supportedDropActions(self):
        
        return Qt.CopyAction | Qt.MoveAction
    
    #def canDropMimeData(self, data, action, row, column, parent):
        #if not data.hasFormat("application/xml"):
            #return False

        #if column > 0:
            #return False

        #return True
    
    def dropMimeData(self, data, action, row, column, parent):
        
        if action == Qt.IgnoreAction:
            return True  # What is that?
        
        if not data.hasFormat("application/xml"):
            return False
        
        if column > 0:
            column = 0
        
        if row != -1:
            beginRow = row
        elif parent.isValid():
            beginRow = self.rowCount(parent) + 1
        else:
            beginRow = self.rowCount() + 1
            
        encodedData = bytes(data.data("application/xml")).decode()
        
        root = ET.XML(encodedData)
        
        if root.tag != "outlineItems":
            return False
        
        items = []
        for child in root:
            if child.tag == "outlineItem":
                items.append(outlineItem(xml=ET.tostring(child)))
                
        if not items:
            return False
        
        return self.insertItems(items, beginRow, parent)
        
    ################# ADDING AND REMOVING #################
        
    def insertItem(self, item, row, parent=QModelIndex()):
        return self.insertItems([item], row, parent)
    
    def insertItems(self, items, row, parent=QModelIndex()):
        if not parent.isValid():
            parentItem = self.rootItem
        else:
            parentItem = parent.internalPointer()
            
        if parent.isValid() and parent.column() != 0:
            parent = parentItem.index()
            
        # Insert only if parent is folder
        if parentItem.isFolder():
            self.beginInsertRows(parent, row, row + len(items) - 1)
            
            for i in items:
                parentItem.insertChild(row + items.index(i), i)
            
            self.endInsertRows()
            
            return True
        
        else:
            return False
        
    def appendItem(self, item, parent=QModelIndex()):
        if not parent.isValid():
            parentItem = self.rootItem
        else:
            parentItem = parent.internalPointer()
        
        if parent.isValid() and parent.column() != 0:
            parent = parentItem.index()
        
        # If parent is folder, write into
        if parentItem.isFolder():
            self.insertItem(item, self.rowCount(parent), parent)
            
        # If parent is not folder, write next to
        else:
            self.insertItem(item, parent.row()+1, parent.parent())
        
    def removeIndex(self, index):
        item = index.internalPointer()
        self.removeRow(item.row(), index.parent())
            
    def removeRow(self, row, parent=QModelIndex()):
        return self.removeRows(row, 1, parent)
    
    def removeRows(self, row, count, parent=QModelIndex()):
        if not parent.isValid():
            parentItem = self.rootItem
        else:
            parentItem = parent.internalPointer()
            
        self.beginRemoveRows(parent, row, row + count - 1)
        for i in range(count):
            parentItem.removeChild(row)
            
        self.endRemoveRows()
        return True
    
    #def insertRow(self, row, item, parent=QModelIndex()):
        #self.beginInsertRows(parent, row, row)
        
        #if not parent.isValid():
            #parentItem = self.rootItem
        #else:
            #parentItem = parent.internalPointer()
            
        #parentItem.insertChild(row, item)
        
        #self.endInsertRows()
        
        
    ################# XML #################
    
    def saveToXML(self, xml):
        root = ET.XML(self.rootItem.toXML())
        ET.ElementTree(root).write(xml, encoding="UTF-8", xml_declaration=True, pretty_print=True)
    
    def loadFromXML(self, xml):
        #try:
            root = ET.parse(xml)
            self.rootItem = outlineItem(self, xml=ET.tostring(root))
            self.generateStatuses()
        #except:
            #print("N'arrive pas à ouvrir {}".format(xml))
            #return
        
        
    ################# DIVERS #################
        
    def generateStatuses(self, item=None):
        if item == None:
            self.statuses = [
                "TODO",
                "First draft",
                "Second draft",
                "Final"
                ]
            item = self.rootItem
        
        val = item.data(Outline.status.value)
        if val and not val in self.statuses:
            self.statuses.append(val)
            self.newStatuses.emit()
            
        for c in item.children():
            self.generateStatuses(c)
            
        
    
class outlineItem():
    
    def __init__(self, model=None, title="", type="folder", xml=None):
        
        self._data = {}
        self.childItems = []
        self._parent = None
        self._model = model
        
        if title: self._data[Outline.title] = title
        self._data[Outline.type] = type
        self._data[Outline.compile] = Qt.Checked
        if xml is not None:
            self.setFromXML(xml)
        
        
    def child(self, row):
        return self.childItems[row]
    
    def childCount(self):
        return len(self.childItems)
    
    def children(self):
        return self.childItems
    
    def columnCount(self):
        return len(Outline)
    
    def data(self, column, role=Qt.DisplayRole):
        
        #print("Data: ", column, role)
        
        if role == Qt.DisplayRole or role == Qt.EditRole:
            if column == Outline.compile.value:
                return self.data(column, Qt.CheckStateRole)
            
            elif Outline(column) in self._data:
                return self._data[Outline(column)]
            
            else:
                return None
            
        elif role == Qt.DecorationRole and column == Outline.title.value:
            if self.isFolder():
                return QIcon.fromTheme("folder")
            elif self.isScene():
                return QIcon.fromTheme("document-new")
            
        elif role == Qt.ForegroundRole:
            if self.isCompile() in [0, "0"]:
                return QBrush(Qt.gray)
            
        elif role == Qt.CheckStateRole and column == Outline.compile.value:
            return self._data[Outline(column)]
        
        elif role == Qt.FontRole:
            f = QFont()
            if column == Outline.wordCount.value and self.isFolder():
                f.setItalic(True)
            elif column == Outline.goal.value and self.isFolder() and self.data(Outline.setGoal) == None:
                f.setItalic(True)
            if self.isFolder():
                f.setBold(True)
            return f
    
    def setData(self, column, data, role=Qt.DisplayRole):
        if role not in [Qt.DisplayRole, Qt.EditRole, Qt.CheckStateRole]:
            print(column, column == Outline.text.value, data, role)
            return
        
        if column == Outline.text.value and self.isFolder():
            # Folder have no text
            return
            
        if column == Outline.goal.value:
            self._data[Outline.setGoal] = toInt(data) if toInt(data) > 0 else ""
            
        updateWordCount = False
        if column in [Outline.wordCount.value, Outline.goal.value, Outline.setGoal.value]:
            updateWordCount = not Outline(column) in self._data or self._data[Outline(column)] != data 
        
        self._data[Outline(column)] = data
        
        if column == Outline.text.value:
            wc = wordCount(data)
            self.setData(Outline.wordCount.value, wc)
        
        if updateWordCount:
            self.updateWordCount()
    
    def updateWordCount(self):
        if not self.isFolder():
            setGoal = toInt(self.data(Outline.setGoal.value))
            goal = toInt(self.data(Outline.goal.value))
        
            if goal != setGoal:
                self._data[Outline.goal] = setGoal
            if setGoal:
                wc = toInt(self.data(Outline.wordCount.value))
                self.setData(Outline.goalPercentage.value, wc / float(setGoal))
                
        else:
            wc = 0
            for c in self.children():
                wc += toInt(c.data(Outline.wordCount.value))
            self._data[Outline.wordCount] = wc
            
            setGoal = toInt(self.data(Outline.setGoal.value))
            goal = toInt(self.data(Outline.goal.value))
            
            if setGoal:
                if goal != setGoal:
                    self._data[Outline.goal] = setGoal
            else:
                goal = 0
                for c in self.children():
                    goal += toInt(c.data(Outline.goal.value))
                self._data[Outline.goal] = goal
            
            if goal:
                self.setData(Outline.goalPercentage.value, wc / float(goal))
                
        self.emitDataChanged()
        
        if self.parent():
            self.parent().updateWordCount()
    
    def row(self):
        if self.parent:
            return self.parent().childItems.index(self)
        
    def appendChild(self, child):
        self.insertChild(self.childCount(), child)
        
    def insertChild(self, row, child):
        self.childItems.insert(row, child)
        child._parent = self
        child.setModel(self._model)
        self.updateWordCount()
        
    def setModel(self, model):
        self._model = model
        for c in self.children():
            c.setModel(model)
        
    def index(self, column=0):
        if self._model:
            return self._model.indexFromItem(self, column)
        else:
            return QModelIndex()
        
    def emitDataChanged(self):
        idx = self.index()
        if idx and self._model:
            self._model.dataChanged.emit(idx, self.index(len(Outline)))
        
    def removeChild(self, row):
        self.childItems.pop(row)
        
    def parent(self):
        return self._parent
    
    def isFolder(self):
        return self._data[Outline.type] == "folder"
    
    def isCompile(self):
        return Outline.compile in self._data and self._data[Outline.compile]
    
    def title(self):
        if Outline.title in self._data:
            return self._data[Outline.title]
        else:
            return ""
    
    def path(self):
        if self.parent().parent():
            return "{} > {}".format(self.parent().path(), self.title())
        else:
            return self.title()
    
    def isScene(self):
        return self._data[Outline.type] == "scene"
    
    def level(self):
        if self.parent():
            return self.parent().level() + 1
        else:
            return -1
    
    def toXML(self):
        item = ET.Element("outlineItem")
        
        # We don't want to write some datas (computed)
        exclude = [Outline.goal, Outline.goalPercentage]
        # We want to force some data even if they're empty
        force = [Outline.compile]
        
        for attrib in Outline:
            if attrib in exclude: continue
            val = self.data(attrib.value)
            if val or attrib in force:
                item.set(attrib.name, str(val))
            
        for i in self.childItems:
            item.append(ET.XML(i.toXML()))
            
        return ET.tostring(item)
    
    def setFromXML(self, xml):
        root = ET.XML(xml)
        
        for k in root.attrib:
            if k in Outline.__members__:
                #if k == Outline.compile:
                    #self.setData(Outline.__members__[k].value, unicode(root.attrib[k]), Qt.CheckStateRole)
                #else:
                    self.setData(Outline.__members__[k].value, str(root.attrib[k]))
                
        for child in root:
            item = outlineItem(self._model, xml=ET.tostring(child))
            self.appendChild(item)