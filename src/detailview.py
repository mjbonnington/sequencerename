#!/usr/bin/python

# detailview.py
#
# Mike Bonnington <mjbonnington@gmail.com>
# (c) 2018-2022
#
# Sequence Rename Tool Task Detail View
# A popup UI to display an expanded view of all the individual files in a
# sequence, before and after the rename operation, as well as an error log
# viewer.


import os

from Qt import QtCore, QtGui, QtWidgets
import ui_template as UI

# Import custom modules
import sequence


# ----------------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------------

cfg = {
	'window_object': "detailViewUI", 
	'window_title': "Detail View", 

	'ui_file': os.path.join(os.path.dirname(__file__), 'forms', 'detailview.ui'), 
	'stylesheet': None, 

	'store_window_geometry': True, 
}

# ----------------------------------------------------------------------------
# Main dialog class
# ----------------------------------------------------------------------------

class dialog(QtWidgets.QDialog, UI.TemplateUI):
	"""Main dialog class."""

	def __init__(self, parent=None):
		super(dialog, self).__init__(parent)
		self.parent = parent

		self.setupUI(**cfg)

		# Set window flags
		self.setWindowFlags(QtCore.Qt.Dialog)

		# Restore widget state
		self.restoreWidgetState(self.ui.splitter, "splitterSizes")


	def display(self, task_id, task):
		"""Display the dialog."""

		path = task['path']
		src_file_list = sequence.expandSeq(path, task['before'])
		dst_file_list = sequence.expandSeq(path, task['after'])
		try:
			log = "\n".join(task['log'])
		except KeyError:
			log = None

		self.setWindowTitle("%s: Task %d" % (cfg['window_title'], task_id))
		self.ui.path_lineEdit.setText(path)

		self.ui.frameList_treeWidget.clear()
		for row in range(len(src_file_list)):
			item = QtWidgets.QTreeWidgetItem(self.ui.frameList_treeWidget)
			item.setText(0, os.path.basename(src_file_list[row]))
			item.setText(1, os.path.basename(dst_file_list[row]))

		for col in range(self.ui.frameList_treeWidget.columnCount()):
			self.ui.frameList_treeWidget.resizeColumnToContents(col)

		self.ui.log_plainTextEdit.setFont(QtGui.QFont("Monospace"))
		if log:
			self.ui.log_plainTextEdit.setPlainText(log)
		else:
			self.ui.log_plainTextEdit.setPlainText("")

		return self.exec_()


	def hideEvent(self, event):
		"""Event handler for when window is hidden."""

		self.storeWindow()  # Store window geometry
		self.storeWidgetState(self.ui.splitter, "splitterSizes")  # Store splitter size state
