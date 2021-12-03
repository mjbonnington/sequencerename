#!/usr/bin/python

# rename.py
#
# Mike Bonnington <mjbonnington@gmail.com>
# (c) 2014-2021
#
# Functions for renaming and renumbering.


import re


def replace_text(input_str, find_str, replace_str, 
	ignore_case=False, regex=True, quiet=True):
	"""Find and replace text in a string.

	Return the new text as a string.

	Arguments:
		input_str (str) -- the input text to modify
		find_str (str) -- the text to find in the input text
		replace_str (str) -- the text to replace the find text with
	Keyword arguments:
		ignore_case (bool) -- perform case-insensitive search if True
		regex (bool) -- interpret the find text string as a regular expression
		quiet (bool) -- don't print any output if True
	"""
	try:
		# If find_str is not designated as regex, escape all special characters
		if not regex:
			find_str = re.escape(find_str)

		if ignore_case:
			pattern = re.compile(r"(?i)%s" % find_str)
		else:
			pattern = re.compile(r"%s" % find_str)

		# Perform replacement and return new name if input is valid
		if find_str:
			new_name = pattern.sub(replace_str, input_str)
			return new_name

		else:
			if not quiet:
				print("Warning: No search string specified.")
			return input_str

	except:
		if not quiet:
			print("Warning: Regular expression is invalid.")


def renumber(num_list, 
	start=1, step=1, padding=4, 
	preserve=True, autopad=True):
	"""Renumber objects.

	Return a new list of integers, plus a padding value, as a tuple.

	Arguments:
		num_list (list) -- input list of integers
	Keyword arguments:
		start (int) -- start number for renumbering
		step (int) -- step / increment for renumbering
		padding (int) -- min number of digits for padding numbers
		preserve (bool) -- keep existing numerical values
		autopad (bool) -- calc the minimum padding for the number sequence
			e.g. 1-500 will need 3-digit padding, so will become 001-500
	"""
	new_num_list = []

	# Calculate padding automatically...
	if autopad:
		if preserve:
			max_num = max(num_list)
		else:
			max_num = start + (step*(len(num_list)-1))

		padding = len(str(max_num))

	# Regenerate lists
	index = start

	if preserve:
		for num in num_list:
			new_num_int = int(str(num).zfill(padding))
			new_num_list.append(new_num_int)

	else:
		for num in num_list:
			new_num_int = int(str(index).zfill(padding))
			new_num_list.append(new_num_int)
			index += step

	return new_num_list, padding
