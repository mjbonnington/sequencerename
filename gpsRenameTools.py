#!/usr/bin/python

# [GPS] Rename Tools
# v0.5.1
#
# Mike Bonnington <mike.bonnington@gps-ldn.com>
# (c) 2014-2016 Gramercy Park Studios
#
# Advanced renaming of objects.


import string, re, time
import maya.cmds as mc
import maya.mel as mel
import pymel.core as pm


class gpsRenameTools():

	def __init__(self):
		self.winTitle = "GPS Rename Tools"
		self.winName = "gpsRenameToolsWindow"
		self.gMainProgressBar = mel.eval('$tmp = $gMainProgressBar')

		# Presets for renaming - will add more as and when we think of them
		self.presetItemList = ["None", "Clean up mangled FBX node names", "Clean up copy & pasted nodes", "Remove trailing numbers"]


	def renameUnique(self, obj, newName):
		""" Rename object.
			Now takes pymel object, rather than string, as first argument.
			Perhaps this function should be moved to an external module?
		"""
		# Set flags for shape node renaming behaviour
		ignoreShape = False
		renameShapes = mc.radioCollection("renameShapes", query=True, select=True) # Re-write to pass in as attribute
		if not renameShapes == "renameShapesAuto":
			ignoreShape = True

		# Split new name string after the last pipe character - allows non-unique child objects to be renamed correctly
		newNameTuple = newName.rpartition("|")

		# Rename shape node(s) if applicable
		if renameShapes == "renameShapesForce":
			objName = str(obj) # Cast pymel object to string for the following code to work
			if mc.nodeType(objName) == "transform":
				shapeLs = mc.listRelatives(objName, shapes=True, fullPath=True)
				if shapeLs is not None:
					for shape in shapeLs:
						mc.rename(shape, newNameTuple[2] + "Shape")

		# Rename node
		try:
			obj.rename(newNameTuple[2], ignoreShape=ignoreShape)
		except RuntimeError:
			mc.warning("Cannot rename node: %s" %str(obj))
			return False


	def replaceTextRE(self):
		""" Find and replace using regular expressions.
		"""
		# Get options
		findStr = mc.textFieldGrp("findStr", query=True, text=True)
		replaceStr = mc.textFieldGrp("replaceStr", query=True, text=True)
		ignoreCase = mc.checkBox("ignoreCase", query=True, value=True)
		if ignoreCase:
			pattern = re.compile("(?i)" + findStr)
		else:
			pattern = re.compile(findStr)

		# Get current selection, or everything, depending on scope
		if mc.radioButtonGrp("scope", query=True, select=True) == 1:
			objLs = pm.ls(selection=True, long=True) # Changed to pymel version of ls to return objects instead of names
		else:
			objLs = pm.ls(long=True)

		if objLs:

			# Check input is valid
			if findStr:

				# Initialise progress bar and start clock
				mc.progressBar(self.gMainProgressBar, edit=True, beginProgress=True, isInterruptable=True, maxValue=len(objLs)) # Initialise progress bar
				startTime = time.time()

				for obj in objLs:
					newName = pattern.sub(replaceStr, str(obj))
					self.renameUnique(obj, newName)
					mc.progressBar(self.gMainProgressBar, edit=True, step=1, status="Renaming items") # Increment progress bar

				# Complete progress bar and print completion message
				mc.progressBar(self.gMainProgressBar, edit=True, endProgress=True) # Complete progress bar
				totalTime = time.time() - startTime;
				#print "Renamed %d items in %f seconds.\n" %(len(objLs), totalTime)

			else:
				mc.warning("No search string specified.")

		else:
			mc.warning("Nothing selected.")


	def renumber(self):
		""" Renumber objects. 
		"""
		# Get options
		preserve = mc.checkBox("preserve", query=True, value=True)
		start = mc.intSliderGrp("start", query=True, value=True)
		step = mc.intSliderGrp("step", query=True, value=True)
		autopad = mc.checkBox("autopad", query=True, value=True)

		# Get current selection, or everything, depending on scope
		if mc.radioButtonGrp("scope", query=True, select=True) == 1:
			selLs = pm.ls(selection=True) # Changed to pymel version of ls to return objects instead of names
		else:
			selLs = pm.ls()
		objLs = list(selLs)

		if selLs:

			# Initialise progress bar and start clock
			mc.progressBar(self.gMainProgressBar, edit=True, beginProgress=True, isInterruptable=True, maxValue=2*len(selLs)) # Initialise progress bar
			startTime = time.time()

			# Calculate padding automatically...
			if autopad:
				numLs = []

				if preserve:
					for obj in selLs:
						match = re.search("[0-9]*$", str(obj))
						currentNumStr = match.group()
						# Check if name has numeric suffix
						if currentNumStr:
							numLs.append(int(currentNumStr))

					if numLs:
						maxNum = max(numLs)
					else:
						mc.error("No numbering sequence detected, unable to calculate padding.")
				else:
					maxNum = start + (step*(len(selLs)-1))

				padding = len(str(maxNum))

			# ...or use user specified padding value
			else:
				padding = mc.intSliderGrp("padding", query=True, value=True)

			# Loop twice to prevent renumbering to a pre-existing number
			for i in range(2):
				index = start
				#objLs = pm.ls(selection=True) # Get selection again as names will have changed - no longer required as now copying object list at start of function

				if preserve:
					for obj in objLs:
						match = re.search("[0-9]*$", str(obj))
						currentNumStr = match.group()
						# Check if name has numeric suffix
						if currentNumStr:
							currentNumInt = int(currentNumStr) # Cast string to integer - looks pointless but otherwise padding can't be reduced
							newName = re.sub(currentNumStr+"$", str(currentNumInt).zfill(padding), str(obj))
							self.renameUnique(obj, newName)
							mc.progressBar(self.gMainProgressBar, edit=True, step=1, status="Renumbering items") # Increment progress bar
						elif not i: # Only print warning on first iteration
							mc.warning("%s has no numeric suffix, unable to renumber." %obj)
				else:
					for obj in objLs:
						newName = re.sub("[0-9]*$", str(index).zfill(padding), str(obj))
						self.renameUnique(obj, newName)
						index += step
						mc.progressBar(self.gMainProgressBar, edit=True, step=1, status="Renumbering items") # Increment progress bar

			# Complete progress bar and print completion message
			mc.progressBar(self.gMainProgressBar, edit=True, endProgress=True) # Complete progress bar
			totalTime = time.time() - startTime;
			#print "Renumbered %d items in %f seconds.\n" %(len(selLs), totalTime)

		else:
			mc.warning("Nothing selected.")


	def tglNumberingControls(self, option):
		mc.intSliderGrp("start", edit=True, enable=option)
		mc.intSliderGrp("step", edit=True, enable=option)


	def tglPaddingControls(self, option):
		mc.intSliderGrp("padding", edit=True, enable=option)


	def tglShapeNodeControls(self, option):
		mc.radioButton("renameShapesAuto", edit=True, select=True, enable=option)
		mc.radioButton("renameShapesForce", edit=True, enable=option)
		mc.radioButton("renameShapesOff", edit=True, enable=option)


	def fillPresets(self):
		preset = mc.optionMenuGrp("renamePresets", query=True, value=True)
		if preset == self.presetItemList[0]:
			mc.textFieldGrp("findStr", edit=True, text=r"")
			mc.textFieldGrp("replaceStr", edit=True, text=r"")
		elif preset == self.presetItemList[1]:
			mc.textFieldGrp("findStr", edit=True, text=r"(FBXASC\d{3})+")
			mc.textFieldGrp("replaceStr", edit=True, text=r"_")
		elif preset == self.presetItemList[2]:
			mc.textFieldGrp("findStr", edit=True, text=r"^(pasted__)+")
			mc.textFieldGrp("replaceStr", edit=True, text=r"")
		elif preset == self.presetItemList[3]:
			mc.textFieldGrp("findStr", edit=True, text=r"\d+$")
			mc.textFieldGrp("replaceStr", edit=True, text=r"")


	def UI(self):
		""" Create UI.
		"""
		# Check if UI window already exists
		if mc.window(self.winName, exists=True):
			mc.deleteUI(self.winName)

		# Create window
		mc.window(self.winName, title=self.winTitle, sizeable=False)

		# Create controls
		#setUITemplate -pushTemplate gpsToolsTemplate;
		mc.columnLayout("windowRoot")
		self.scopePanelUI("scopePanel", "windowRoot")
		self.findReplacePanelUI("findReplacePanel", "windowRoot")
		self.renumberPanelUI("renumberPanel", "windowRoot")
		self.advOptPanelUI("advOptPanel", "windowRoot", collapse=True)
		mc.separator(height=8, style="none")
		mc.rowLayout(numberOfColumns=1)
		mc.button(width=398, height=28, label="Close", command=lambda *args: mc.deleteUI(self.winName))
		#setUITemplate -popTemplate;

		mc.showWindow(self.winName)


	def scopePanelUI(self, name, parent, collapse=False):
		""" Create scope panel UI controls.
		"""
		mc.frameLayout(width=400, collapsable=True, cl=collapse, borderStyle="etchedIn", label="Scope")
		mc.columnLayout(name)

		mc.separator(height=4, style="none")
		mc.radioButtonGrp("scope", label="Scope: ", labelArray2=['Selection', 'Entire Scene'], numberOfRadioButtons=2, columnWidth3=[140, 78, 156], select=1, 	
		                  annotation="Choose whether to rename only the selected objects, or all nodes in the scene (use this option with care)", 
		                  onCommand1=lambda *args: self.tglShapeNodeControls(True), onCommand2=lambda *args: self.tglShapeNodeControls(False))

		mc.separator(height=4, style="none")
		mc.setParent(parent)


	def findReplacePanelUI(self, name, parent, collapse=False):
		""" Create find and replace panel UI controls.
		"""
		mc.frameLayout(width=400, collapsable=True, cl=collapse, borderStyle="etchedIn", label="Find and Replace")
		mc.columnLayout(name)

		mc.separator(height=4, style="none")
		mc.optionMenuGrp("renamePresets", label="Preset: ", changeCommand=lambda *args: self.fillPresets())
		for item in self.presetItemList:
			mc.menuItem(label=item)

		mc.separator(width=396, height=12, style="in")
		mc.textFieldGrp("findStr", label="Find: ")
		mc.textFieldGrp("replaceStr", label="Replace: ")

		mc.separator(height=8, style="none")
		mc.rowLayout(numberOfColumns=2, columnAttach2=["left", "left"], columnAlign2=["both", "both"], columnOffset2=[142, 8])
		mc.checkBox("ignoreCase", label="Ignore case", value=0)
		mc.setParent(name)

		mc.separator(height=4, style="none")
		mc.rowLayout(numberOfColumns=1, columnAttach1="left", columnAlign1="both", columnOffset1=142)
		mc.button(width=116, label="Replace Text", command=lambda *args: self.replaceTextRE())
		mc.setParent(name)

		mc.separator(height=4, style="none")
		mc.setParent(parent)


	def renumberPanelUI(self, name, parent, collapse=False):
		""" Create renumber panel UI controls.
		"""
		mc.frameLayout(width=400, collapsable=True, cl=collapse, borderStyle="etchedIn", label="Renumber")
		mc.columnLayout(name)
		mc.separator(height=4, style="none")
		mc.rowLayout(numberOfColumns=1, columnAttach1="left", columnAlign1="both", columnOffset1=142)
		mc.checkBox("preserve", label="Preserve current numbering", value=1, onCommand=lambda *args: self.tglNumberingControls(False), offCommand=lambda *args: self.tglNumberingControls(True))
		mc.setParent(name)
		mc.separator(height=4, style="none")
		mc.intSliderGrp("start", label="Start from: ", value=1, field=True, minValue=0, maxValue=50, fieldMinValue=0, fieldMaxValue=99999999, enable=False)
		mc.intSliderGrp("step", label="Step: ", value=1, field=True, minValue=1, maxValue=50, fieldMinValue=1, fieldMaxValue=99999999, enable=False)
		mc.separator(height=4, style="none")

		mc.rowLayout(numberOfColumns=1, columnAttach1="left", columnAlign1="both", columnOffset1=142)
		mc.checkBox("autopad", label="Auto padding", value=1, onCommand=lambda *args: self.tglPaddingControls(False), offCommand=lambda *args: self.tglPaddingControls(True))
		mc.setParent(name)
		mc.separator(height=4, style="none")
		mc.intSliderGrp("padding", label="Padding: ", value=4, field=True, minValue=1, maxValue=8, fieldMinValue=1, fieldMaxValue=16, enable=False)
		mc.separator(height=4, style="none")

		mc.rowLayout(numberOfColumns=1, columnAttach1="left", columnAlign1="both", columnOffset1=142)
		mc.button(width=116, label="Renumber", command=lambda *args: self.renumber())
		mc.setParent(name)
		mc.separator(height=4, style="none")
		mc.setParent(parent)


	def advOptPanelUI(self, name, parent, collapse=False):
		""" Create advanced options panel UI controls.
		"""
		mc.frameLayout(width=400, collapsable=True, cl=collapse, borderStyle="etchedIn", label="Advanced Options")
		mc.columnLayout(name)
		mc.separator(height=4, style="none")
		mc.rowLayout(numberOfColumns=1, columnAttach1="left", columnAlign1="both", columnOffset1=4)
		mc.text(label="When a transform node is renamed, Maya will automatically rename any shape nodes beneath it with the same prefix. This can cause shared shape nodes (i.e. instances) to end up with mangled names. Use this option to modify this behaviour.", wordWrap=True, align="left", font="smallObliqueLabelFont", width=392)
		mc.setParent(name)
		mc.separator(height=8, style="none")
		mc.rowLayout(numberOfColumns=1, columnAttach1="left", columnAlign1="both", columnOffset1=8)
		mc.columnLayout()
		mc.radioCollection("renameShapes")
		mc.radioButton("renameShapesAuto", label="Automatically rename shape nodes (Maya default)", select=True)
		mc.radioButton("renameShapesForce", label="Force renaming of shape nodes")
		mc.radioButton("renameShapesOff", label="Don't rename shape nodes")
		mc.setParent(name)
		mc.separator(height=8, style="none")
		mc.setParent(parent)

