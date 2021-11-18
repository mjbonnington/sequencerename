#!/usr/bin/python

# frameview.py
#
# Mike Bonnington <mjbonnington@gmail.com>
# (c) 2018-2021
#
# Sequence Rename Tool Frame View
# A popup UI to display an expanded view of all the individual files in a
# sequence, before and after the rename operation.


import os

from Qt import QtCore, QtWidgets
import ui_template as UI

# Import custom modules


# ----------------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------------

cfg = {}

# Set window title and object names
cfg['window_object'] = "frameViewUI"
cfg['window_title'] = "Frame View"

# Set the UI and the stylesheet
cfg['ui_file'] = os.path.join(os.path.dirname(__file__), 'forms', 'frameview.ui')
cfg['stylesheet'] = None

# Other options
cfg['store_window_geometry'] = True


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


	def display(self, src_file_list, dst_file_list):
		"""Display the dialog."""

		self.ui.frameList_treeWidget.clear()

		for row in range(len(src_file_list)):
			item = QtWidgets.QTreeWidgetItem(self.ui.frameList_treeWidget)
			item.setText(0, src_file_list[row])
			item.setText(1, dst_file_list[row])

		for col in range(self.ui.frameList_treeWidget.columnCount()):
			self.ui.frameList_treeWidget.resizeColumnToContents(col)

		return self.exec_()


	def hideEvent(self, event):
		"""Event handler for when window is hidden."""

		self.storeWindow()  # Store window geometry
