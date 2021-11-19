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
import verbose
from pprint import pprint

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
		# self.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)

		# Restore widget state
		self.restoreWidgetState(self.ui.splitter, "splitterSizes")
		self.ui.taskList_treeWidget.header().restoreState(self.settings.value("taskView")) #.toByteArray())

		self.tasks = []  # This will hold a list of dicts, to store task data
		self.rename_count = 0
		self.total_count = 0

		self.last_dir = None
		self.expert_mode = False

		# Set up about dialog
		about = lambda: self.about(
			app_name=cfg['window_title'], 
			app_version="v" + os.getenv('REZ_IC_SEQRENAME_VERSION'), 
			description="A tool for batch renaming and renumbering sequences of files.\n", 
			credits="Developer: Mike Bonnington", 
			icon=self.iconTint(cfg['icon']), 
		)

		# Define colours
		# self.col = {}  # Already declared in ui_template.py
		self.col['ready'] = QtGui.QColor('#63b2b2') #'#99c696'
		self.col['null'] = QtGui.QColor('#5c616c')
		self.col['done'] = QtGui.QColor('#6897c8')
		self.col['error'] = QtGui.QColor('#e96168')

		# Define status icons & tint with colours defined above
		self.icon = {}
		for status in ['ready', 'null', 'done', 'error']:
			self.icon[status] = self.iconSet('status-icon-%s.png' % status, tintNormal=self.col[status])

		# Add tool button icons
		self.ui.add_toolButton.setIcon(self.iconSet('add.svg'))
		self.ui.remove_toolButton.setIcon(self.iconSet('remove.svg'))
		self.ui.clear_toolButton.setIcon(self.iconSet('clear.svg'))
		self.ui.fill_toolButton.setIcon(self.iconSet('edit-find-replace.svg'))
		self.ui.about_toolButton.setIcon(self.iconSet('help-about.svg'))

		# Connect signals & slots
		self.ui.taskList_treeWidget.itemSelectionChanged.connect(self.update_toolbar_ui)
		self.ui.taskList_treeWidget.itemDoubleClicked.connect(self.expand_task)

		updateTaskListViewStatus = lambda: self.update_task_view(update_status=True)  # Lambda function for PyQt5 compatibility, default keyword argument not supported
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

		self.ui.remove_toolButton.clicked.connect(self.remove_selected_tasks)
		self.ui.clear_toolButton.clicked.connect(self.clear_task_list)
		self.ui.rename_pushButton.clicked.connect(self.perform_file_rename)
		self.ui.cancel_pushButton.clicked.connect(self.cancel_rename)
		self.ui.about_toolButton.clicked.connect(about)

		# Set up context menus
		self.addContextMenu(self.ui.add_toolButton, "Directory...", self.addDirectory)
		self.addContextMenu(self.ui.add_toolButton, "Sequence...", self.addSequence)

		self.addContextMenu(self.ui.fill_toolButton, "Copy filename prefix to 'Find' field", self.load_find_str)
		self.addContextMenu(self.ui.fill_toolButton, "Copy filename prefix to 'Replace' field", self.load_replace_str)

		# # Set up keyboard shortcuts
		# self.shortcutExpertMode = QtWidgets.QShortcut(self)
		# self.shortcutExpertMode.setKey('Ctrl+Shift+E')
		# self.shortcutExpertMode.activated.connect(self.toggle_hidden_columns)

		# Set input validators
		alphanumeric_filename_validator = QtGui.QRegExpValidator(QtCore.QRegExp(r'[\w\.-]+'), self.ui.replace_comboBox)
		self.ui.replace_comboBox.setValidator(alphanumeric_filename_validator)

		alphanumeric_ext_validator = QtGui.QRegExpValidator(QtCore.QRegExp(r'[\w]+'), self.ui.ext_lineEdit)
		self.ui.ext_lineEdit.setValidator(alphanumeric_ext_validator)

		# Get current dir in which to rename files, and update widget if
		# running as standalone app
		if __name__ == "__main__":
			self.update_task_list_dir(os.getcwd())

		self.update_toolbar_ui()
		self.toggle_hidden_columns()
		self.ui.rename_pushButton.show()
		self.ui.cancel_pushButton.hide()
		self.ui.rename_progressBar.hide()


	def update_toolbar_ui(self):
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
		if self.get_child_items(self.ui.taskList_treeWidget):
			self.ui.clear_toolButton.setEnabled(True)
		else:
			self.ui.clear_toolButton.setEnabled(False)


	def toggle_hidden_columns(self):
		"""Toggle visiblity of columns in the task list view."""

		self.expert_mode = not self.expert_mode
		#columns = ['Task', 'Prefix', 'Frames', 'Extension']
		columns = ['Task', 'Count']

		for column in columns:
			self.ui.taskList_treeWidget.setColumnHidden(self.header(column), self.expert_mode)


	def header(self, text):
		"""Return the column number for the specified header text."""

		for col in range(self.ui.taskList_treeWidget.columnCount()):
			if text == self.ui.taskList_treeWidget.headerItem().text(col):
				return col

		return -1


	def get_task_id(self, item):
		"""Return the ID for the specified task item."""

		return int(item.text(self.header('Task')))


	def get_child_items(self, widget):
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
		"""Decide from which directory to start browsing."""

		if self.last_dir:
			browseDir = self.last_dir
		elif os.getenv('IC_MAYA_RENDERS_DIR') is not None:
			browseDir = os.environ['IC_MAYA_RENDERS_DIR']
		else:
			browseDir = os.getcwd()

		return browseDir


	def addDirectory(self):
		"""Open a dialog to select a folder from which to add files."""

		dirname = self.folderDialog(self.getBrowseDir())
		if dirname:
			dirname = os_wrapper.absolute_path(dirname)
			self.last_dir = dirname
			self.update_task_list_dir(dirname)


	def addSequence(self):
		"""Open a dialog to select files to add."""

		filename = self.fileDialog(self.getBrowseDir())
		if filename:
			filename = os_wrapper.absolute_path(filename)
			self.last_dir = os.path.dirname(filename)
			self.update_task_list_file(filename)


	def update_task_list_dir(self, dirpath):
		"""Update task list with detected file sequences in given directory.

		Pre-existing tasks will not be added, to avoid duplication.
		"""
		bases = sequence.getBases(dirpath, delimiter="")

		for base in bases:
			path, prefix, fr_range, ext, num_frames = sequence.getSequence(dirpath, base, delimiter="", ignorePadding=False)
			self.create_task(path, prefix, fr_range, ext, num_frames)

		self.update_task_view()


	def update_task_list_file(self, filepath):
		"""Update task list with detected file sequence given a file path.

		Pre-existing tasks will not be added, to avoid duplication.
		"""
		if os.path.isfile(filepath):
			path, prefix, fr_range, ext, num_frames = sequence.detectSeq(filepath, delimiter="", ignorePadding=False)
			self.create_task(path, prefix, fr_range, ext, num_frames)
			self.update_task_view()


	def remove_selected_tasks(self):
		"""Remove selected items from the task list."""

		indices = [self.get_task_id(item) for item in self.ui.taskList_treeWidget.selectedItems()]

		# Reverse order so indices do not change during operation
		indices.sort(reverse=True)

		for i in indices:
			verbose.detail("Removing task id %d" % i)
			self.tasks.pop(i)

		self.update_task_view()


	def clear_task_list(self):
		"""Clear the task list."""

		self.tasks = []
		self.update_task_view()


	def create_task(self, path, prefix, frames, ext, count, status=""):
		"""Create a new task.

		Don't create a new task if a matching item already exists. Only update
		the existing task if the frame range differs.
		"""

		# Check if matching item already exists
		for item in self.tasks:
			if item['path'] == path \
			and item['prefix'] == prefix \
			and item['ext'] == ext:
				if item['frames'] == frames:
					verbose.detail("Task item already exists.")
				else:
					verbose.detail("Task item already exists but frame ranges differ. Updating item with new frame range.")
					item['frames'] = frames
					item['count'] = count
				return

		# Create new item
		new_item = {
			'path': path, 
			'prefix': prefix, 
			'frames': frames, 
			'ext': ext, 
			'count': count, 
			'status': status, 
		}
		self.tasks.append(new_item)


	def create_task_group_item(self, path):
		"""Create a task group item.

		If a matching item already exists return that, otherwise create the
		new item and return it.

		Arguments:
			path (str) -- path to a folder containing file sequences.
		"""
		root = self.ui.taskList_treeWidget.invisibleRootItem()
		child_count = root.childCount()

		# Check if matching item already exists
		for i in range(child_count):
			item = root.child(i)
			if item.text(0) == path:
				# verbose.detail("Task group already exists.")
				return item

		new_item = QtWidgets.QTreeWidgetItem(self.ui.taskList_treeWidget)
		new_item.setText(0, path)
		new_item.setIcon(0, self.iconSet('folder-open.svg'))
		new_item.setFirstColumnSpanned(True)
		new_item.setFlags(new_item.flags() & ~QtCore.Qt.ItemIsSelectable)
		return new_item


	def get_tree_item(self, parent, task_id=None):
		"""Return the tree widget item identified by 'task_id' belonging to
		'parent'.

		If it doesn't exist, return a new item.
		If 'itemID' is not specified, return a list of all the child items.
		"""
		child_count = parent.childCount()

		# Return list of children
		if task_id is None:
			items = []
			for i in range(child_count):
				items.append(parent.child(i))
			return items

		# Return specified child
		else:
			for i in range(child_count):
				item = parent.child(i)
				if int(item.text(self.header('Task'))) == task_id:
					return item

			# Return a new item
			return QtWidgets.QTreeWidgetItem(parent)


	# def set_task_status(self, task_id, status):
	# 	"""Update the status of a task."""

	# 	self.tasks[task_id] = status
	# 	item = self.get_tree_item(task_id)
	# 	item.setText(self.header('Status'), status)

	# 	if status =="Nothing to change":
	# 		task_item.setIcon(self.header('Status'), self.icon['null'])
	# 		task_item.setForeground(self.header('Status'), self.col['null'])

	# 		task_item.setBackground(self.header('After'), QtGui.QBrush())
	# 		task_item.setForeground(self.header('After'), self.col['null'])

	# 	elif status == "Ready":
	# 		task_item.setIcon(self.header('Status'), self.icon['ready'])
	# 		task_item.setForeground(self.header('Status'), self.col['ready'])

	# 		task_item.setBackground(self.header('After'), QtGui.QBrush())
	# 		task_item.setForeground(self.header('After'), self.col['ready'])

	# 	elif status == "Complete":
	# 		item.setIcon(self.header('Status'), self.icon['done'])
	# 		item.setForeground(self.header('Status'), self.col['done'])

	# 		item.setBackground(self.header("After"), QtGui.QBrush())
	# 		item.setForeground(self.header("After"), self.col['null'])

	# 	elif status == "Output filename conflict":
	# 		item.setIcon(self.header('Status'), self.icon['error'])
	# 		item.setForeground(self.header('Status'), self.col['error'])

	# 		item.setBackground(self.header('After'), self.col['error'])
	# 		item.setForeground(self.header('After'), self.col['highlighted-text'])

	# 	else:  # General error
	# 		item.setIcon(self.header('Status'), self.icon['error'])
	# 		item.setForeground(self.header('Status'), self.col['error'])

	# 		item.setBackground(self.header("After"), QtGui.QBrush())
	# 		item.setForeground(self.header("After"), self.col['error'])


	# def updateTaskItem(self, index, status, path, prefix, fr_range, ext, num_frames):
	# 	"""Update the task item at a given index."""

	# 	root = self.ui.taskList_treeWidget.invisibleRootItem()
	# 	child_count = root.childCount()
	# 	index = int(index)

	# 	# Check if matching item already exists
	# 	if index in list(range(child_count)):
	# 		item = root.child(index)
	# 		item.setText(self.header('Status'), status)
	# 		if status == "Complete":
	# 			item.setIcon(self.header('Status'), self.icon['done'])
	# 			item.setForeground(self.header('Status'), self.col['done'])

	# 			item.setBackground(self.header("After"), QtGui.QBrush())
	# 			item.setForeground(self.header("After"), self.col['null'])
	# 		else:
	# 			item.setIcon(self.header('Status'), self.icon['error'])
	# 			item.setForeground(self.header('Status'), self.col['error'])

	# 			item.setBackground(self.header("After"), QtGui.QBrush())
	# 			item.setForeground(self.header("After"), self.col['error'])

	# 		item.setText(self.header("Path"), path)
	# 		item.setText(self.header("Prefix"), prefix)
	# 		item.setText(self.header("Frames"), fr_range)
	# 		item.setText(self.header("Extension"), ext)
	# 		item.setText(self.header("Count"), str(num_frames))
	# 		return item

	# 	else:
	# 		return None


	# def updateTaskListView(self, updateStatus=True):
	# 	"""Populate the rename list tree view widget with entries."""

	# 	rename_count = 0
	# 	total_count = 0

	# 	# Get find & replace options
	# 	findStr = self.ui.find_comboBox.currentText()
	# 	replaceStr = self.ui.replace_comboBox.currentText()
	# 	ignoreCase = self.getCheckBoxValue(self.ui.ignoreCase_checkBox)
	# 	regex = self.getCheckBoxValue(self.ui.regex_checkBox)

	# 	# Get renumbering options
	# 	start = self.ui.start_spinBox.value()
	# 	step = self.ui.step_spinBox.value()
	# 	padding = self.ui.padding_spinBox.value()
	# 	preserve = self.getCheckBoxValue(self.ui.preserveNumbering_checkBox)
	# 	autopad = self.getCheckBoxValue(self.ui.autoPadding_checkBox)

	# 	# Get extension options
	# 	changeExt = self.getCheckBoxValue(self.ui.ext_checkBox)
	# 	root = self.ui.taskList_treeWidget.invisibleRootItem()
	# 	child_count = root.childCount()

	# 	# task_items = []
	# 	# for i in range(root.childCount()):
	# 	# 	item = root.child(i)
	# 	# 	for j in range(item.childCount()):
	# 	# 		task_items.append(root.child(j))

	# 	# for i, item in enumerate(task_items):
	# 	for i in range(child_count):
	# 		item = root.child(i)

	# 		prefix = item.text(self.header("Prefix"))
	# 		fr_range = item.text(self.header("Frames"))
	# 		ext = item.text(self.header("Extension"))
	# 		num_frames = int(item.text(self.header("Count")))

	# 		item.setText(self.header("Task"), str(i))

	# 		# Add entries
	# 		if fr_range:
	# 			file = "%s[%s]%s" % (prefix, fr_range, ext)
	# 		else:
	# 			file = "%s%s" % (prefix, ext)
	# 		item.setText(self.header("Before"), file)

	# 		if changeExt and self.ui.ext_lineEdit.text():
	# 			newExt = ".%s" % self.ui.ext_lineEdit.text()
	# 		else:
	# 			newExt = ext

	# 		renamedPrefix = rename.replaceTextRE(prefix, findStr, replaceStr, ignoreCase, regex)
	# 		if fr_range:  # If sequence
	# 			numLs = sequence.numList(fr_range)
	# 			renumberedLs, padding = rename.renumber(numLs, start, step, padding, preserve, autopad)
	# 			renumberedRange = sequence.numRange(renumberedLs, padding)
	# 			renamedFile = "%s[%s]%s" % (renamedPrefix, renumberedRange, newExt)
	# 		else:
	# 			renamedFile = "%s%s" % (renamedPrefix, newExt)
	# 		item.setText(self.header("After"), renamedFile)

	# 		# Set icon to indicate status
	# 		if updateStatus:
	# 			if file == renamedFile:
	# 				item.setText(self.header('Status'), "Nothing to change")
	# 				item.setIcon(self.header('Status'), self.icon['null'])
	# 				item.setForeground(self.header('Status'), self.col['null'])

	# 				item.setBackground(self.header("After"), QtGui.QBrush())
	# 				item.setForeground(self.header("After"), self.col['null'])

	# 			else:
	# 				item.setText(self.header('Status'), "Ready")
	# 				item.setIcon(self.header('Status'), self.icon['ready'])
	# 				item.setForeground(self.header('Status'), self.col['ready'])

	# 				item.setBackground(self.header("After"), QtGui.QBrush())
	# 				item.setForeground(self.header("After"), self.col['ready'])

	# 				rename_count += num_frames

	# 		total_count += num_frames

	# 	# Resize columns
	# 	# if task_items:
	# 	if child_count:
	# 		for col in range(self.ui.taskList_treeWidget.columnCount()):
	# 			self.ui.taskList_treeWidget.resizeColumnToContents(col)

	# 	conflicts = self.check_for_conflicts()

	# 	self.update_toolbar_ui()  # Update UI

	# 	# Update button text
	# 	if rename_count:
	# 		self.ui.rename_progressBar.setMaximum(rename_count)
	# 		if rename_count == 1:
	# 			self.ui.rename_pushButton.setText("Rename 1 file")
	# 		else:
	# 			self.ui.rename_pushButton.setText("Rename %d files" % rename_count)

	# 	else:
	# 		self.ui.rename_pushButton.setText("Rename")

	# 	# Enable or disable button
	# 	if rename_count and not conflicts:
	# 		self.ui.rename_pushButton.setEnabled(True)
	# 	else:
	# 		self.ui.rename_pushButton.setEnabled(False)


	def update_tasks(self, update_status=True):
		"""Update the task list when the inputs are changed"""

		self.rename_count = 0
		self.total_count = 0

		# Get find & replace options
		find_str = self.ui.find_comboBox.currentText()
		replace_str = self.ui.replace_comboBox.currentText()
		ignore_case = self.getCheckBoxValue(self.ui.ignoreCase_checkBox)
		regex = self.getCheckBoxValue(self.ui.regex_checkBox)

		# Get renumbering options
		start = self.ui.start_spinBox.value()
		step = self.ui.step_spinBox.value()
		padding = self.ui.padding_spinBox.value()
		preserve = self.getCheckBoxValue(self.ui.preserveNumbering_checkBox)
		autopad = self.getCheckBoxValue(self.ui.autoPadding_checkBox)

		# Get extension options
		change_ext = self.getCheckBoxValue(self.ui.ext_checkBox)
		ext_to_change = self.ui.ext_lineEdit.text()

		for item in self.tasks:

			if item['frames']:
				file = "%s[%s]%s" % (item['prefix'], item['frames'], item['ext'])
			else:
				file = "%s%s" % (item['prefix'], item['ext'])
			item['before'] = file

			if change_ext and ext_to_change:
				new_ext = ".%s" % ext_to_change
			else:
				new_ext = item['ext']

			renamed_prefix = rename.replaceTextRE(item['prefix'], find_str, replace_str, ignore_case, regex)
			if item['frames']:  # If sequence
				num_list = sequence.numList(item['frames'])
				renumbered_list, padding = rename.renumber(num_list, start, step, padding, preserve, autopad)
				renumbered_range = sequence.numRange(renumbered_list, padding)
				renamed_file = "%s[%s]%s" % (renamed_prefix, renumbered_range, new_ext)
			else:
				renamed_file = "%s%s" % (renamed_prefix, new_ext)
			item['after'] = renamed_file

			if update_status:
				if file == renamed_file:
					item['status'] = "Nothing to change"
				else:
					item['status'] = "Ready"
					self.rename_count += item['count']

			self.total_count += item['count']

		conflicts = self.check_for_conflicts()

		# Update button text
		if self.rename_count:
			self.ui.rename_progressBar.setMaximum(self.rename_count)
			if self.rename_count == 1:
				self.ui.rename_pushButton.setText("Rename 1 file")
			else:
				self.ui.rename_pushButton.setText("Rename %d files" % self.rename_count)

		else:
			self.ui.rename_pushButton.setText("Rename")

		# Enable or disable button
		if self.rename_count and not conflicts:
			self.ui.rename_pushButton.setEnabled(True)
		else:
			self.ui.rename_pushButton.setEnabled(False)

		# pprint(self.tasks)


	def update_task_view(self, update_status=True):
		"""Populate the task list tree widget with entries."""

		self.update_tasks(update_status)

		self.ui.taskList_treeWidget.clear()
		root = self.ui.taskList_treeWidget.invisibleRootItem()
		child_count = root.childCount()

		for i, item in enumerate(self.tasks):
			group_item = self.create_task_group_item(item['path'])
			group_item.setExpanded(True)

			task_item = QtWidgets.QTreeWidgetItem(group_item)
			task_item.setText(self.header('Task'), str(i))
			task_item.setText(self.header('Count'), str(item['count']))
			task_item.setText(self.header('Before'), item['before'])
			task_item.setText(self.header('After'), item['after'])

			# Set icon to indicate status
			if update_status:
				# self.set_task_status(i, item['status'])

				task_item.setText(self.header('Status'), item['status'])

				if item['status'] =="Nothing to change":
					task_item.setIcon(self.header('Status'), self.icon['null'])
					task_item.setForeground(self.header('Status'), self.col['null'])

					task_item.setBackground(self.header('After'), QtGui.QBrush())
					task_item.setForeground(self.header('After'), self.col['null'])

				elif item['status'] == "Ready":
					task_item.setIcon(self.header('Status'), self.icon['ready'])
					task_item.setForeground(self.header('Status'), self.col['ready'])

					task_item.setBackground(self.header('After'), QtGui.QBrush())
					task_item.setForeground(self.header('After'), self.col['ready'])

				elif item['status'] == "Complete":
					task_item.setIcon(self.header('Status'), self.icon['done'])
					task_item.setForeground(self.header('Status'), self.col['done'])

					task_item.setBackground(self.header("After"), QtGui.QBrush())
					task_item.setForeground(self.header("After"), self.col['null'])

				elif item['status'] == "Output filename conflict":
					task_item.setIcon(self.header('Status'), self.icon['error'])
					task_item.setForeground(self.header('Status'), self.col['error'])

					task_item.setBackground(self.header('After'), self.col['error'])
					task_item.setForeground(self.header('After'), self.col['highlighted-text'])

				else:  # General error
					task_item.setIcon(self.header('Status'), self.icon['error'])
					task_item.setForeground(self.header('Status'), self.col['error'])

					task_item.setBackground(self.header("After"), QtGui.QBrush())
					task_item.setForeground(self.header("After"), self.col['error'])

		# Resize columns
		if self.total_count:
			# self.ui.taskList_treeWidget.header().resizeSection(0, 200)
			# for col in range(self.ui.taskList_treeWidget.columnCount()):
			for col in [self.header('Before'), self.header('After'), self.header('Count')]:
				self.ui.taskList_treeWidget.resizeColumnToContents(col)
		else:
			msg = "Add sequences to rename by dragging and dropping files or folders on to this window, or use the 'Add' button."
			group_item = self.create_task_group_item(msg)
			group_item.setBackground(0, self.col['warning-bg'])
			group_item.setForeground(0, self.col['warning-text'])
			group_item.setIcon(0, self.iconSet('add.svg', tintNormal=self.col['warning-text']))

		self.update_toolbar_ui()  # Update UI


	def expand_task(self, item, column):
		"""Open a new view showing the individual frames in a sequence.

		This is shown when an item is double-clicked.
		"""
		# self.get_task_id(item)
		src_file_list = sequence.expandSeq(item.text(self.header('Path')), item.text(self.header('Before')))
		dst_file_list = sequence.expandSeq(item.text(self.header('Path')), item.text(self.header('After')))

		try:
			self.taskFrameViewUI.display(src_file_list, dst_file_list)
		except AttributeError:
			self.taskFrameViewUI = frameview.dialog(self)
			self.taskFrameViewUI.display(src_file_list, dst_file_list)


	def check_for_conflicts(self):
		"""Check for conflicts in renamed files."""

		# children = []
		outputs = []
		# root = self.ui.taskList_treeWidget.invisibleRootItem()
		# for i in range(root.childCount()):
		# 	children.append(root.child(i))
		# 	outpath = "%s/%s" % (root.child(i).text(self.header('Path')), root.child(i).text(self.header('After')))
		# 	outputs.append(outpath.lower())

		for item in self.tasks:
			outpath = os.path.normpath(os.path.join(item['path'], item['after']))
			outputs.append(outpath.lower())

		# Find duplicate outputs
		conflicts = set([x for x in outputs if outputs.count(x) > 1])

		# Highlight duplicates in list view
		for item in self.tasks:
			outpath = os.path.normpath(os.path.join(item['path'], item['after']))
			if outpath.lower() in conflicts:
				item['status'] = "Output filename conflict"

		# # Highlight duplicates in list view
		# for item in children:
		# 	outpath = "%s/%s" % (item.text(self.header('Path')), item.text(self.header('After')))
		# 	if outpath.lower() in conflicts:
		# 		item.setText(self.header('Status'), "Output filename conflict")
		# 		item.setIcon(self.header('Status'), self.icon['error'])
		# 		item.setForeground(self.header('Status'), self.col['error'])

		# 		item.setBackground(self.header('After'), self.col['error'])
		# 		item.setForeground(self.header('After'), self.col['highlighted-text'])

		# # Check for conflicts with existing files on disk
		# for item in children:
		# 	for file in sequence.expandSeq(item.text(self.header('Path')), item.text(self.header('After'))):
		# 		if not item.text(self.header('Before')) == item.text(self.header('After')):
		# 			if os.path.isfile(file):
		# 				item.setText(self.header('Status'), "File exists error")
		# 				item.setIcon(self.header('Status'), self.icon['error'])
		# 				item.setForeground(self.header('Status'), self.col['error'])

		# self.ui.taskList_treeWidget.resizeColumnToContents(self.header('Status'))

		if len(conflicts):
			verbose.warning("%d rename conflict(s) found." % len(conflicts))

		return len(conflicts)


	def load_find_str(self, item=None, column=0):
		"""Copy the selected file name prefix to the 'Find' text field."""

		if not item:
			item = self.ui.taskList_treeWidget.selectedItems()[-1]

		text = self.tasks[self.get_task_id(item)]['prefix']

		if self.ui.find_comboBox.findText(text) == -1:
			self.ui.find_comboBox.insertItem(0, text)
		self.ui.find_comboBox.setCurrentIndex(self.ui.find_comboBox.findText(text))


	def load_replace_str(self, item=None, column=0):
		"""Copy the selected file name prefix to the 'Replace' text field.

		Non-alphanumeric characters will be replaced with underscores.
		"""
		if not item:
			item = self.ui.taskList_treeWidget.selectedItems()[-1]

		text = self.tasks[self.get_task_id(item)]['prefix']
		text = os_wrapper.sanitize(text, pattern=r'[^\w\.-]', replace='_')

		if self.ui.replace_comboBox.findText(text) == -1:
			self.ui.replace_comboBox.insertItem(0, text)
		self.ui.replace_comboBox.setCurrentIndex(self.ui.replace_comboBox.findText(text))


	def perform_file_rename(self):
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
		# for i in range(child_count):
		# 	item = root.child(i)
		# 	if item.text(self.header('Status')) == "Ready":
		# 		items_to_process.append(item)
		for i, item in enumerate(self.tasks):
			if item['status'] == "Ready":
				item['id'] = i  # Hack
				items_to_process.append(item)

		# Initialise worker thread, connect signals & slots, start processing
		self.workerThread = BatchRenameThread(
			items_to_process, 
			ignore_errors=self.getCheckBoxValue(self.ui.ignoreErrors_checkBox))
		self.workerThread.printError.connect(verbose.error)
		# self.workerThread.printError.connect(self.error)
		self.workerThread.printMessage.connect(verbose.message)
		self.workerThread.printProgress.connect(verbose.progress)
		self.workerThread.updateProgressBar.connect(self.update_progress_bar)
		self.workerThread.taskCompleted.connect(self.task_completed)
		self.workerThread.finished.connect(self.rename_completed)
		self.workerThread.start()


	# def error(self, message):
	# 	"""Print an error message to stdout.

	# 	Use ANSI escape sequences to colour the text red.
	# 	"""
	# 	print('\033[38;5;197m' + "ERROR: " + message + '\033[0m')


	@QtCore.Slot(int)
	def update_progress_bar(self, value):
		"""Update progress bar."""

		self.ui.rename_progressBar.setValue(value)


	@QtCore.Slot(tuple)
	def task_completed(self, new_task):
		"""Update task in list view."""

		#print(new_task)
		task_id, status, filepath = new_task
		if os.path.isfile(filepath):
			path, prefix, fr_range, ext, num_frames = sequence.detectSeq(filepath, delimiter="", ignorePadding=False)
			# self.updateTaskItem(task_id, status, path, prefix, fr_range, ext, num_frames)
			# self.updateTaskListView(updateStatus=False)
			self.create_task(path, prefix, fr_range, ext, num_frames, status)
			self.update_task_view(update_status=False)


	def rename_completed(self):
		"""Function to execute when the rename operation finishes."""

		verbose.message("Batch rename job completed.")

		self.ui.rename_pushButton.show()
		self.ui.cancel_pushButton.hide()
		self.ui.rename_progressBar.hide()


	def cancel_rename(self):
		"""Stop the rename operation.

		TODO: need to clean up incomplete tasks
		"""
		verbose.message("Aborting rename job.")
		self.workerThread.terminate()  # Enclose in try/except?

		# self.ui.taskList_treeWidget.resizeColumnToContents(self.header('Status'))


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

				verbose.detail("Dropped '%s' on to window." % fname)

				if os.path.isdir(fname):
					self.update_task_list_dir(fname)
				elif os.path.isfile(fname):
					self.update_task_list_file(fname)
		else:
			e.ignore()


	def hideEvent(self, event):
		"""Event handler for when window is hidden."""

		self.save()  # Save settings
		self.storeWindow()  # Store window geometry
		self.storeWidgetState(self.ui.splitter, "splitterSizes")  # Store splitter size state
		self.settings.setValue("taskView", self.ui.taskList_treeWidget.header().saveState())

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

		# task_id = item.text(0)
		# task_status = item.text(1)
		# # task_count = item.text(2)
		# task_before = item.text(3)
		# task_after = item.text(4)
		# task_path = item.text(5)
		task_id = item['id']
		task_status = item['status']
		# task_count = item['count']
		task_before = item['before']
		task_after = item['after']
		task_path = item['path']

		src_file_list = sequence.expandSeq(task_path, task_before)
		dst_file_list = sequence.expandSeq(task_path, task_after)

		# Only go ahead and rename if the operation will make changes
		# if task_status == "Ready":
		self.printMessage.emit("%s: Rename '%s' to '%s'" % (task_id, task_before, task_after))
		self.printMessage.emit("Renaming 0%")

		for i in range(len(src_file_list)):
			success, msg = os_wrapper.rename(src_file_list[i], dst_file_list[i], quiet=True)
			if success:
				last_index = i
				progress = (float(i)/float(len(src_file_list)))*100
				self.printProgress.emit("Renaming %d%%" % progress)
			else:
				errors += 1
				self.printError.emit(msg)
				if not self.ignore_errors:  # Task stopped due to error
					return task_id, "Interrupted", src_file_list[-1]

			self.files_processed += 1
			self.updateProgressBar.emit(self.files_processed)

		if errors == 0:  # Task completed successfully
			self.printProgress.emit("Renaming 100%")
			return task_id, "Complete", dst_file_list[i]

		else:  # Task completed with errors, which were ignored
			if errors == 1:
				error_str = "1 error"
			else:
				error_str = "%d errors" % errors
			self.printMessage.emit("Task generated %s." % error_str)
			return task_id, error_str, dst_file_list[last_index] #src_file_list[-1]

		# else:  # Task skipped
		# 	self.printMessage.emit("%s: Rename task skipped." % task_id)
		# 	return task_id, "Nothing to change", "" #src_file_list[0]

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
	try:
		QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_ShareOpenGLContexts)
	except AttributeError:
		pass

	main_app = QtWidgets.QApplication(sys.argv)
	main_window = SequenceRenameApp()
	main_window.show()
	sys.exit(main_app.exec_())
