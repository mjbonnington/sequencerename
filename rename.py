#!/usr/bin/python

# rename.py
#
# Mike Bonnington <mjbonnington@gmail.com>
# (c) 2014-2019
#
# Functions for renaming and renumbering.


import re


def replaceTextRE(
	origName, 
	findStr, 
	replaceStr, 
	ignoreCase=False, 
	regex=True, 
	quiet=True):
	""" Find and replace using regular expressions.
	"""
	try:
		# If findStr is not designated as regex, escape all special characters
		if not regex:
			findStr = re.escape(findStr)

		if ignoreCase:
			pattern = re.compile(r"(?i)%s" %findStr)
		else:
			pattern = re.compile(r"%s" %findStr)

		# Perform replacement and return new name if input is valid
		if findStr:
			newName = pattern.sub(replaceStr, origName)
			return newName

		else:
			if not quiet:
				print("Warning: No search string specified.")
			return origName

	except:
		if not quiet:
			print("Warning: Regular expression is invalid.")


def renumber(
	numLs, 
	start=1, 
	step=1, 
	padding=4, 
	preserve=True, 
	autopad=True):
	""" Renumber objects.
	"""
	newNumLs = []

	# Calculate padding automatically...
	if autopad:

		if preserve:
			maxNum = max(numLs)
		else:
			maxNum = start + (step*(len(numLs)-1))

		padding = len(str(maxNum))

	# Regenerate lists
	index = start

	if preserve:
		for num in numLs:
			newNumInt = int(str(num).zfill(padding))
			newNumLs.append(newNumInt)

	else:
		for num in numLs:
			newNumInt = int(str(index).zfill(padding))
			newNumLs.append(newNumInt)
			index += step

	return newNumLs, padding
