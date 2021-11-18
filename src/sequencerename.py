#!/usr/bin/python

# sequencerename.py
#
# Mike Bonnington <mjbonnington@gmail.com>
# (c) 2016-2021
#
# Sequence Rename Tool
# A UI for batch renaming and renumbering sequences of files.
#
# TODO: Use unified dialog & methods for Maya advanced rename tools.
# TODO: Use pyseq or fileseq instead of custom sequence.py library.


import os
import re
import sys

from Qt import QtCore, QtGui, QtWidgets
import ui_template as UI

# Import custom modules
import frameview
import os_wrapper
import rename
import sequence


# ----------------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------------

cfg = {}

# Set window title and object names
cfg['window_object'] = "seqRenameUI"
cfg['window_title'] = "Sequence Rename"

# Set the UI and the stylesheet
cfg['ui_file'] = os.path.join(os.path.dirname(__file__), 'forms', 'sequencerename.ui')
cfg['stylesheet'] = 'style.qss'
cfg['icon'] = 'icon-rename.png'

# Other options
prefs_location = os.getenv('IC_USERPREFSDIR', os.path.expanduser('~/.sequencerename'))
if not os.path.isdir(prefs_location):
	os.makedirs(prefs_location)
cfg['prefs_file'] = os.path.join(prefs_location, 'sequencerename_prefs.json')
cfg['store_window_geometry'] = True

# ----------------------------------------------------------------------------
# Begin main application class
# ----------------------------------------------------------------------------

class SequenceRenameApp(QtWidgets.QMainWindow, UI.TemplateUI):
	"""Sequence Rename Tool application class."""

	def __init__(self, parent=None):
		super(SequenceRenameApp, self).__init__(parent)
		self.parent = parent

		self.setupUI(**cfg)
		self.conformFormLayoutLabels(self.ui.sidebar_frame)

		# Set window icon, flags and other Qt attributes
		# self.setWindowIcon(self.iconSet(cfg['icon'], tintNormal=False))
		self.setWindowFlags(QtCore.Qt.Window)
		#self.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)

		# Restore splitter size state
		self.restoreWidgetState(self.ui.splitter, "splitterSizes")
		# try:
		# 	self.ui.splitter.restoreState(self.settings.value("splitterSizes")) #.toByteArray())
		# except:
		# 	pass

		# Set up about dialog
		about = lambda: self.about(
			app_name=cfg['window_title'], 
			app_version="v" + os.getenv('REZ_IC_SEQRENAME_VERSION'), 
			description="A tool for batch renaming and renumbering sequences of files.\n", 
			credits="Developer: Mike Bonnington", 
			icon=self.iconTint(cfg['icon']), 
		)

		# Set up keyboard shortcuts
		self.shortcutExpertMode = QtWidgets.QShortcut(self)
		self.shortcutExpertMode.setKey('Ctrl+Shift+E')
		self.shortcutExpertMode.activated.connect(self.toggleHiddenColumns)

		# Connect signals & slots
		self.ui.taskList_treeWidget.itemSelectionChanged.connect(self.updateToolbarUI)
		self.ui.taskList_treeWidget.itemDoubleClicked.connect(self.expandTask)

		updateTaskListViewStatus = lambda: self.updateTaskListView(updateStatus=True)  # Lambda function for PyQt5 compatibility, default keyword argument not supported
		self.ui.find_comboBox.editTextChanged.connect(updateTaskListViewStatus)
		self.ui.replace_comboBox.editTextChanged.connect(updateTaskListViewStatus)
		self.ui.ignoreCase_checkBox.stateChanged.connect(updateTaskListViewStatus)
		self.ui.regex_checkBox.stateChanged.connect(updateTaskListViewStatus)
		self.ui.preserveNumbering_checkBox.stateChanged.connect(updateTaskListViewStatus)
		self.ui.start_spinBox.valueChanged.connect(updateTaskListViewStatus)
		self.ui.step_spinBox.valueChanged.connect(updateTaskListViewStatus)
		self.ui.autoPadding_checkBox.stateChanged.connect(updateTaskListViewStatus)
		self.ui.padding_spinBox.valueChanged.connect(updateTaskListViewStatus)
		self.ui.ext_checkBox.stateChanged.connect(updateTaskListViewStatus)
		self.ui.ext_lineEdit.textChanged.connect(updateTaskListViewStatus)

		self.ui.remove_toolButton.clicked.connect(self.removeSelection)
		self.ui.clear_toolButton.clicked.connect(self.clearTaskList)
		self.ui.rename_pushButton.clicked.connect(self.performFileRename)
		self.ui.cancel_pushButton.clicked.connect(self.cancelRename)
		self.ui.about_toolButton.clicked.connect(about)

		# Context menus
		self.addContextMenu(self.ui.add_toolButton, "Directory...", self.addDirectory)
		self.addContextMenu(self.ui.add_toolButton, "Sequence...", self.addSequence)

		self.addContextMenu(self.ui.fill_toolButton, "Copy filename prefix to 'Find' field", self.loadFindStr)
		self.addContextMenu(self.ui.fill_toolButton, "Copy filename prefix to 'Replace' field", self.loadReplaceStr)

		# Add tool button icons
		self.ui.add_toolButton.setIcon(self.iconSet('add.svg'))
		self.ui.remove_toolButton.setIcon(self.iconSet('remove.svg'))
		self.ui.clear_toolButton.setIcon(self.iconSet('clear.svg'))
		self.ui.fill_toolButton.setIcon(self.iconSet('edit-find-replace.svg'))
		self.ui.about_toolButton.setIcon(self.iconSet('help-about.svg'))

		# Define colours
		# self.col = {}  # Already declared in ui_template.py
		self.col['ready'] = QtGui.QColor('#99c696')
		self.col['null'] = QtGui.QColor('#5c616c')
		self.col['done'] = QtGui.QColor('#6897c8')
		self.col['error'] = QtGui.QColor('#e96168')

		# Define status icons & tint with colours defined above
		self.icon = {}
		for status in ['ready', 'null', 'done', 'error']:
			self.icon[status] = self.iconSet('status-icon-%s.png' % status, tintNormal=self.col[status])
		# self.icon['ready'] = self.iconSet('status-icon-ready.png', tintNormal=self.col['ready'])
		# self.icon['null'] = self.iconSet('status-icon-null.png', tintNormal=self.col['null'])
		# self.icon['done'] = self.iconSet('status-icon-done.png', tintNormal=self.col['done'])
		# self.icon['error'] = self.iconSet('status-icon-error.png', tintNormal=self.col['error'])

		# Set input validators
		alphanumeric_filename_validator = QtGui.QRegExpValidator(QtCore.QRegExp(r'[\w\.-]+'), self.ui.replace_comboBox)
		self.ui.replace_comboBox.setValidator(alphanumeric_filename_validator)

		alphanumeric_ext_validator = QtGui.QRegExpValidator(QtCore.QRegExp(r'[\w]+'), self.ui.ext_lineEdit)
		self.ui.ext_lineEdit.setValidator(alphanumeric_ext_validator)

		self.lastDir = None
		self.expertMode = False

		# Get current dir in which to rename files, and update widget if
		# running as standalone app
		if __name__ == "__main__":
			self.updateTaskListDir(os.getcwd())

		self.updateToolbarUI()
		self.toggleHiddenColumns()
		self.ui.rename_pushButton.show()
		self.ui.cancel_pushButton.hide()
		self.ui.rename_progressBar.hide()


	def updateToolbarUI(self):
		"""Update the toolbar UI based on the current selection."""

		# No items selected...
		if len(self.ui.taskList_treeWidget.selectedItems()) == 0:
			self.ui.remove_toolButton.setEnabled(False)
			self.ui.fill_toolButton.setEnabled(False)

		# One item selected...
		elif len(self.ui.taskList_treeWidget.selectedItems()) == 1:
			self.ui.remove_toolButton.setEnabled(True)
			self.ui.fill_toolButton.setEnabled(True)

		# More than one item selected...
		else:
			self.ui.remove_toolButton.setEnabled(True)
			self.ui.fill_toolButton.setEnabled(False)

		# List is empty...
		if self.getChildItems(self.ui.taskList_treeWidget):
			self.ui.clear_toolButton.setEnabled(True)
		else:
			self.ui.clear_toolButton.setEnabled(False)


	def toggleHiddenColumns(self):
		"""Toggle visiblity of columns in the task list view."""

		self.expertMode = not self.expertMode
		columns = ['Task', 'Prefix', 'Frames', 'Extension']

		for column in columns:
			self.ui.taskList_treeWidget.setColumnHidden(self.header(column), self.expertMode)


	def header(self, text):
		"""Return the column number for the specified header text."""

		for col in range(self.ui.taskList_treeWidget.columnCount()):
			if text == self.ui.taskList_treeWidget.headerItem().text(col):
				return col

		return -1


	def getChildItems(self, widget):
		"""Return all top-level child items of the specified widget."""

		items = []
		root = widget.invisibleRootItem()

		for i in range(root.childCount()):
			items.append(root.child(i))

		if items:
			return items
		else:
			return None


	def getBrowseDir(self):
		"""Decide which directory to start browsing from."""

		if self.lastDir:
			browseDir = self.lastDir
		elif os.environ.get('IC_MAYA_RENDERS_DIR') is not None:
			browseDir = os.environ['IC_MAYA_RENDERS_DIR']
		else:
			browseDir = os.getcwd()

		return browseDir


	def addDirectory(self):
		"""Open a dialog to select a folder to add files from."""

		dirname = self.folderDialog(self.getBrowseDir())
		if dirname:
			dirname = os_wrapper.absolute_path(dirname)
			self.lastDir = dirname
			self.updateTaskListDir(dirname)


	def addSequence(self):
		"""Open a dialog to select files to add."""

		filename = self.fileDialog(self.getBrowseDir())
		if filename:
			filename = os_wrapper.absolute_path(filename)
			self.lastDir = os.path.dirname(filename)
			self.updateTaskListFile(filename)


	def updateTaskListDir(self, dirpath):
		"""Update task list with detected file sequences in given directory.

		Pre-existing tasks will not be added, to avoid duplication.
		"""
		bases = sequence.getBases(dirpath, delimiter="")

		for base in bases:
			path, prefix, fr_range, ext, num_frames = sequence.getSequence(dirpath, base, delimiter="", ignorePadding=False)
			self.createTaskItem(path, prefix, fr_range, ext, num_frames)

		self.updateTaskListView()


	def updateTaskListFile(self, filepath):
		"""Update task list with detected file sequence given a file path.

		Pre-existing tasks will not be added, to avoid duplication.
		"""
		if os.path.isfile(filepath):
			path, prefix, fr_range, ext, num_frames = sequence.detectSeq(filepath, delimiter="", ignorePadding=False)
			self.createTaskItem(path, prefix, fr_range, ext, num_frames)
			self.updateTaskListView()


	def removeSelection(self):
		"""Remove selected items from the task list."""

		for item in self.ui.taskList_treeWidget.selectedItems():
			index = self.ui.taskList_treeWidget.indexOfTopLevelItem(item)
			self.ui.taskList_treeWidget.takeTopLevelItem(index)

		self.updateTaskListView()


	def clearTaskList(self):
		"""Clear the task list."""

		self.ui.taskList_treeWidget.clear()
		self.updateToolbarUI()


	def createTaskItem(self, path, prefix, fr_range, ext, num_frames):
		"""Create a new task item.

		But only if a matching item doesn't already exist.
		"""
		root = self.ui.taskList_treeWidget.invisibleRootItem()
		child_count = root.childCount()

		# Check if matching item already exists
		for i in range(child_count):
			item = root.child(i)
			if item.text(self.header("Path")) == path and \
			   item.text(self.header("Prefix")) == prefix and \
			   item.text(self.header("Extension")) == ext:
				if item.text(self.header("Frames")) == fr_range:
					print("Task item already exists.")
				else:
					print("Task item already exists but frame ranges differ. Updating item with new frame range.")
					item.setText(self.header("Frames"), fr_range)
					item.setText(self.header("Count"), str(num_frames))
				return item

		new_item = QtWidgets.QTreeWidgetItem(self.ui.taskList_treeWidget)
		new_item.setText(self.header("Path"), path)
		new_item.setText(self.header("Prefix"), prefix)
		new_item.setText(self.header("Frames"), fr_range)
		new_item.setText(self.header("Extension"), ext)
		new_item.setText(self.header("Count"), str(num_frames))
		return new_item


	def updateTaskItem(self, index, status, path, prefix, fr_range, ext, num_frames):
		"""Update the task item at a given index."""

		root = self.ui.taskList_treeWidget.invisibleRootItem()
		child_count = root.childCount()
		index = int(index)

		# Check if matching item already exists
		if index in list(range(child_count)):
			item = root.child(index)
			item.setText(self.header("Status"), status)
			if status == "Complete":
				item.setIcon(self.header("Status"), self.icon['done'])
				item.setForeground(self.header("Status"), self.col['done'])

				item.setBackground(self.header("After"), QtGui.QBrush())
				item.setForeground(self.header("After"), self.col['null'])
			else:
				item.setIcon(self.header("Status"), self.icon['error'])
				item.setForeground(self.header("Status"), self.col['error'])

				item.setBackground(self.header("After"), QtGui.QBrush())
				item.setForeground(self.header("After"), self.col['error'])

			item.setText(self.header("Path"), path)
			item.setText(self.header("Prefix"), prefix)
			item.setText(self.header("Frames"), fr_range)
			item.setText(self.header("Extension"), ext)
			item.setText(self.header("Count"), str(num_frames))
			return item

		else:
			return None


	def updateTaskListView(self, updateStatus=True):
		"""Populate the rename list tree view widget with entries."""

		rename_count = 0
		total_count = 0

		# Get find & replace options
		findStr = self.ui.find_comboBox.currentText()
		replaceStr = self.ui.replace_comboBox.currentText()
		ignoreCase = self.getCheckBoxValue(self.ui.ignoreCase_checkBox)
		regex = self.getCheckBoxValue(self.ui.regex_checkBox)

		# Get renumbering options
		start = self.ui.start_spinBox.value()
		step = self.ui.step_spinBox.value()
		padding = self.ui.padding_spinBox.value()
		preserve = self.getCheckBoxValue(self.ui.preserveNumbering_checkBox)
		autopad = self.getCheckBoxValue(self.ui.autoPadding_checkBox)

		# Get extension options
		changeExt = self.getCheckBoxValue(self.ui.ext_checkBox)
		root = self.ui.taskList_treeWidget.invisibleRootItem()
		child_count = root.childCount()

		for i in range(child_count):
			item = root.child(i)

			prefix = item.text(self.header("Prefix"))
			fr_range = item.text(self.header("Frames"))
			ext = item.text(self.header("Extension"))
			num_frames = int(item.text(self.header("Count")))

			item.setText(self.header("Task"), str(i))

			# Add entries
			if fr_range:
				file = "%s[%s]%s" % (prefix, fr_range, ext)
			else:
				file = "%s%s" % (prefix, ext)
			item.setText(self.header("Before"), file)

			if changeExt and self.ui.ext_lineEdit.text():
				newExt = ".%s" % self.ui.ext_lineEdit.text()
			else:
				newExt = ext

			renamedPrefix = rename.replaceTextRE(prefix, findStr, replaceStr, ignoreCase, regex)
			if fr_range:  # If sequence
				numLs = sequence.numList(fr_range)
				renumberedLs, padding = rename.renumber(numLs, start, step, padding, preserve, autopad)
				renumberedRange = sequence.numRange(renumberedLs, padding)
				renamedFile = "%s[%s]%s" % (renamedPrefix, renumberedRange, newExt)
			else:
				renamedFile = "%s%s" % (renamedPrefix, newExt)
			item.setText(self.header("After"), renamedFile)

			# Set icon to indicate status
			if updateStatus:
				if file == renamedFile:
					item.setText(self.header("Status"), "Nothing to change")
					item.setIcon(self.header("Status"), self.icon['null'])
					item.setForeground(self.header("Status"), self.col['null'])

					item.setBackground(self.header("After"), QtGui.QBrush())
					item.setForeground(self.header("After"), self.col['null'])

				else:
					item.setText(self.header("Status"), "Ready")
					item.setIcon(self.header("Status"), self.icon['ready'])
					item.setForeground(self.header("Status"), self.col['ready'])

					item.setBackground(self.header("After"), QtGui.QBrush())
					item.setForeground(self.header("After"), self.col['ready'])

					rename_count += num_frames

			total_count += num_frames

		# Resize columns
		if child_count:
			for col in range(self.ui.taskList_treeWidget.columnCount()):
				self.ui.taskList_treeWidget.resizeColumnToContents(col)

		conflicts = self.checkConflicts()

		self.updateToolbarUI()  # Update UI

		# Update button text
		if rename_count:
			self.ui.rename_progressBar.setMaximum(rename_count)
			if rename_count == 1:
				self.ui.rename_pushButton.setText("Rename 1 file")
			else:
				self.ui.rename_pushButton.setText("Rename %d files" % rename_count)

		else:
			self.ui.rename_pushButton.setText("Rename")

		# Enable or disable button
		if rename_count and not conflicts:
			self.ui.rename_pushButton.setEnabled(True)
		else:
			self.ui.rename_pushButton.setEnabled(False)


	def expandTask(self, item, column):
		"""Open a new view showing the individual frames in a sequence.

		This is shown when an item is double-clicked.
		"""
		src_fileLs = sequence.expandSeq(item.text(self.header("Path")), item.text(self.header("Before")))
		dst_fileLs = sequence.expandSeq(item.text(self.header("Path")), item.text(self.header("After")))

		try:
			self.taskFrameViewUI.display(src_fileLs, dst_fileLs)
		except AttributeError:
			self.taskFrameViewUI = frameview.dialog(self)
			self.taskFrameViewUI.display(src_fileLs, dst_fileLs)


	def checkConflicts(self):
		"""Check for conflicts in renamed files.

		TODO: rewrite this?
		"""
		children = []
		outputs = []
		root = self.ui.taskList_treeWidget.invisibleRootItem()
		for i in range(root.childCount()):
			children.append(root.child(i))
			outpath = "%s/%s" % (root.child(i).text(self.header("Path")), root.child(i).text(self.header("After")))
			outputs.append(outpath.lower())

		# Find duplicate outputs
		conflicts = set([x for x in outputs if outputs.count(x) > 1])

		# Highlight duplicates in list view
		for item in children:
			outpath = "%s/%s" % (item.text(self.header("Path")), item.text(self.header("After")))
			if outpath.lower() in conflicts:
				item.setText(self.header("Status"), "Output filename conflict")
				item.setIcon(self.header("Status"), self.icon['error'])
				item.setForeground(self.header("Status"), self.col['error'])

				item.setBackground(self.header("After"), self.col['error'])
				item.setForeground(self.header("After"), self.col['highlighted-text'])

		# # Check for conflicts with existing files on disk
		# for item in children:
		# 	for file in sequence.expandSeq(item.text(self.header("Path")), item.text(self.header("After"))):
		# 		if not item.text(self.header("Before")) == item.text(self.header("After")):
		# 			if os.path.isfile(file):
		# 				item.setText(self.header("Status"), "File exists error")
		# 				item.setIcon(self.header("Status"), self.icon['error'])
		# 				item.setForeground(self.header("Status"), self.col['error'])

		self.ui.taskList_treeWidget.resizeColumnToContents(self.header("Status"))

		if len(conflicts):
			print("Warning: %d rename conflict(s) found." % len(conflicts))

		return len(conflicts)


	def loadFindStr(self, item=None, column=0):
		"""Copy the selected file name prefix to the 'Find' text field."""

		if not item:
			item = self.ui.taskList_treeWidget.selectedItems()[0]

		text = item.text(self.header("Prefix"))

		if self.ui.find_comboBox.findText(text) == -1:
			self.ui.find_comboBox.insertItem(0, text)
		self.ui.find_comboBox.setCurrentIndex(self.ui.find_comboBox.findText(text))


	def loadReplaceStr(self, item=None, column=0):
		"""Copy the selected file name prefix to the 'Replace' text field.

		Non-alphanumeric characters will be replaced with underscores.
		"""
		if not item:
			item = self.ui.taskList_treeWidget.selectedItems()[0]

		text = item.text(self.header("Prefix"))
		text = os_wrapper.sanitize(text, pattern=r'[^\w\.-]', replace='_')

		if self.ui.replace_comboBox.findText(text) == -1:
			self.ui.replace_comboBox.insertItem(0, text)
		self.ui.replace_comboBox.setCurrentIndex(self.ui.replace_comboBox.findText(text))


	def performFileRename(self):
		"""Perform the file rename operation(s)."""

		self.save()  # Save settings

		root = self.ui.taskList_treeWidget.invisibleRootItem()
		child_count = root.childCount()

		self.ui.rename_pushButton.hide()
		self.ui.cancel_pushButton.show()
		self.ui.rename_progressBar.show()
		self.ui.rename_progressBar.setValue(0)

		# Generate list of tasks for processing
		items_to_process = []
		for i in range(child_count):
			item = root.child(i)
			if item.text(self.header("Status")) == "Ready":
				items_to_process.append(item)

		# Initialise worker thread, connect signals & slots, start processing
		self.workerThread = BatchRenameThread(
			items_to_process, 
			ignore_errors=self.getCheckBoxValue(self.ui.ignoreErrors_checkBox))
		# self.workerThread.printError.connect(verbose.error)
		self.workerThread.printError.connect(self.error)
		# self.workerThread.printMessage.connect(verbose.message)
		# self.workerThread.printProgress.connect(verbose.progress)
		self.workerThread.updateProgressBar.connect(self.updateProgressBar)
		self.workerThread.taskCompleted.connect(self.taskCompleted)
		self.workerThread.finished.connect(self.renameCompleted)
		self.workerThread.start()


	def error(self, message):
		"""Print an error message to stdout.

		Use ANSI escape sequences to colour the text red.
		"""
		print('\033[38;5;197m' + "ERROR: " + message + '\033[0m')


	@QtCore.Slot(int)
	def updateProgressBar(self, value):
		"""Update progress bar."""

		self.ui.rename_progressBar.setValue(value)


	@QtCore.Slot(tuple)
	def taskCompleted(self, new_task):
		"""Update task in list view."""

		#print(new_task)
		task_id, status, filepath = new_task
		if os.path.isfile(filepath):
			path, prefix, fr_range, ext, num_frames = sequence.detectSeq(filepath, delimiter="", ignorePadding=False)
			self.updateTaskItem(task_id, status, path, prefix, fr_range, ext, num_frames)
			self.updateTaskListView(updateStatus=False)


	def renameCompleted(self):
		"""Function to execute when the rename operation finishes."""

		print("Batch rename job completed.")

		self.ui.rename_pushButton.show()
		self.ui.cancel_pushButton.hide()
		self.ui.rename_progressBar.hide()


	def cancelRename(self):
		"""Stop the rename operation.

		TODO: need to clean up incomplete tasks
		"""
		print("Aborting rename job.")
		self.workerThread.terminate()  # Enclose in try/except?

		self.ui.taskList_treeWidget.resizeColumnToContents(self.header("Status"))


	def dragEnterEvent(self, e):
		if e.mimeData().hasUrls:
			e.accept()
		else:
			e.ignore()


	def dragMoveEvent(self, e):
		if e.mimeData().hasUrls:
			e.accept()
		else:
			e.ignore()


	def dropEvent(self, e):
		"""Event handler for files dropped on to the widget."""

		if e.mimeData().hasUrls:
			e.setDropAction(QtCore.Qt.CopyAction)
			e.accept()
			for url in e.mimeData().urls():
				fname = str(url.toLocalFile())

			print("Dropped '%s' on to window." % fname)

			if os.path.isdir(fname):
				self.updateTaskListDir(fname)
			elif os.path.isfile(fname):
				self.updateTaskListFile(fname)
		else:
			e.ignore()


	def hideEvent(self, event):
		"""Event handler for when window is hidden."""

		self.save()  # Save settings
		self.storeWindow()  # Store window geometry
		self.storeWidgetState(self.ui.splitter, "splitterSizes")  # Store splitter size state

# ----------------------------------------------------------------------------
# End main application class
# ============================================================================
# Begin worker thread class
# ----------------------------------------------------------------------------

class BatchRenameThread(QtCore.QThread):
	"""Worker thread class."""

	printError = QtCore.Signal(str)
	printMessage = QtCore.Signal(str)
	printProgress = QtCore.Signal(str)
	updateProgressBar = QtCore.Signal(int)
	taskCompleted = QtCore.Signal(tuple)

	def __init__(self, tasks, ignore_errors=True):
		QtCore.QThread.__init__(self)
		self.tasks = tasks
		self.ignore_errors = ignore_errors
		self.files_processed = 0


	def __del__(self):
		self.wait()


	def run(self):
		for item in self.tasks:
			new_task = self._rename_task(item)
			self.taskCompleted.emit(new_task)


	def _rename_task(self, item):
		"""Perform the file rename operation(s).

		Return a tuple containing the following items:
		- the index of the task being processed;
		- the status of the task;
		- a filename to be processed as a new task.
		"""
		errors = 0
		last_index = 0

		task_id = item.text(0)
		task_status = item.text(1)
		# task_count = item.text(2)
		task_before = item.text(3)
		task_after = item.text(4)
		task_path = item.text(5)

		src_fileLs = sequence.expandSeq(task_path, task_before)
		dst_fileLs = sequence.expandSeq(task_path, task_after)

		# Only go ahead and rename if the operation will make changes
		# if task_status == "Ready":
		self.printMessage.emit("%s: Rename '%s' to '%s'" % (task_id, task_before, task_after))
		self.printMessage.emit("Renaming 0%")

		for i in range(len(src_fileLs)):
			success, msg = os_wrapper.rename(src_fileLs[i], dst_fileLs[i], quiet=True)
			if success:
				last_index = i
				progress = (i/len(src_fileLs))*100
				self.printProgress.emit("Renaming %d%%" % progress)
			else:
				errors += 1
				self.printError.emit(msg)
				if not self.ignore_errors:  # Task stopped due to error
					return task_id, "Interrupted", src_fileLs[-1]

			self.files_processed += 1
			self.updateProgressBar.emit(self.files_processed)

		if errors == 0:  # Task completed successfully
			self.printProgress.emit("Renaming 100%")
			return task_id, "Complete", dst_fileLs[i]

		else:  # Task completed with errors, which were ignored
			if errors == 1:
				error_str = "1 error"
			else:
				error_str = "%d errors" % errors
			self.printMessage.emit("Task generated %s." % error_str)
			return task_id, error_str, dst_fileLs[last_index] #src_fileLs[-1]

		# else:  # Task skipped
		# 	self.printMessage.emit("%s: Rename task skipped." % task_id)
		# 	return task_id, "Nothing to change", "" #src_fileLs[0]

# ----------------------------------------------------------------------------
# End worker thread class
# ============================================================================
# Run functions
# ----------------------------------------------------------------------------

def run(session):
	"""Run inside host app."""

	try:  # Show the UI
		session.seqRenameUI.show()
	except:  # Create the UI
		session.seqRenameUI = SequenceRenameApp(parent=UI._main_window())
		session.seqRenameUI.show()


# Run as standalone app
if __name__ == "__main__":
	main_app = QtWidgets.QApplication(sys.argv)
	main_window = SequenceRenameApp()
	main_window.show()
	sys.exit(main_app.exec_())
