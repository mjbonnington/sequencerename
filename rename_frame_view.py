#!/usr/bin/python

# rename_frame_view.py
#
# Mike Bonnington <mike.bonnington@gps-ldn.com>
# (c) 2018-2019
#
# Sequence Rename Tool
# A popup UI to display an expanded view of all the individual files in a
# sequence, before and after the rename operation.


from Qt import QtCore, QtWidgets

# Import custom modules
import ui_template as UI


# ----------------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------------

cfg = {}

# Set window title and object names
cfg['window_title'] = "Frame View"
cfg['window_object'] = "frameViewUI"

# Set the UI and the stylesheet
cfg['ui_file'] = "rename_frame_view_ui.ui"
cfg['stylesheet'] = "style.qss"  # Set to None to use the parent app's stylesheet

# Other options
cfg['store_window_geometry'] = True


# ----------------------------------------------------------------------------
# Main dialog class
# ----------------------------------------------------------------------------

class dialog(QtWidgets.QDialog, UI.TemplateUI):
	""" Main dialog class.
	"""
	def __init__(self, parent=None):
		super(dialog, self).__init__(parent)
		self.parent = parent

		self.setupUI(**cfg)

		# Set window flags
		self.setWindowFlags(QtCore.Qt.Dialog)


	def display(self, src_file_list, dst_file_list):
		""" Display the dialog.
		"""
		self.ui.frameList_treeWidget.clear()

		for row in range(len(src_file_list)):
			item = QtWidgets.QTreeWidgetItem(self.ui.frameList_treeWidget)
			item.setText(0, src_file_list[row])
			item.setText(1, dst_file_list[row])

		for col in range(self.ui.frameList_treeWidget.columnCount()):
			self.ui.frameList_treeWidget.resizeColumnToContents(col)

		return self.exec_()


	def hideEvent(self, event):
		""" Event handler for when window is hidden.
		"""
		self.storeWindow()  # Store window geometry
