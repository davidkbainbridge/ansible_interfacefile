#!/usr/bin/env python

import json
import os
import re
import sys
import shlex
import string
import ipaddress

# Regular expressions to identify comments and blank lines
comment = re.compile("^\s*#")
blank = re.compile("^\s*$")

#####
# Parsers
#
# Parses are methods that take the form 'parse_<keyword>', where the keyword
# is the first word on a line in file. The purpose of the parser is to
# evaluate the line tna update the interface model accordingly.
####

# Creates an interface definition in the model and sets the auto
# configuration to true
def parse_auto(data, current, words):
	if words[1] in data.keys():
		iface = data[words[1]]
	else:
		iface = {}

	iface["auto"] = "True"
	data[words[1]] = iface
	return words[1]

# Creates an interface definition in the model if one does not exist and
# sets the type and configuation method
def parse_iface(data, current, words):
	if words[1] in data.keys():
		iface = data[words[1]]
	else:
		iface = {}

	iface["type"] = words[2]
	iface["config"] = words[3]
	data[words[1]] = iface
	return words[1]

# Evaluates the address specification and either sets the address only or if the
# address is specified with network bits (mask) sets the network and netmask as
# well.
def parse_address(data, current, words):
	if current == "":
                raise SyntaxError("Attempt to add attribute '%s' without an interface" % words[0])

        if current in data.keys():
                iface = data[current]
        else:
                iface = {}

	if string.find(words[1], "/") != -1:
		parts = words[1].split('/')
		addr = ipaddress.ip_network(unicode(words[1], "UTF-8"), strict=False)
		iface["address"] = parts[0]
		iface["network"] = addr.network_address.exploded.encode('ascii','ignore')
		iface["netmask"] = addr.netmask.exploded.encode('ascii','ignore')
	else:
		iface["address"] = words[1]

	data[current] = iface
	return current

# Used to evaluate attributes and add a generic name / value pair to the interface
# model
def parse_add_attr(data, current, words):
	if current == "":
		raise SyntaxError("Attempt to add attribute '%s' without an interface" % words[0])

	if current in data.keys():
                iface = data[current]
        else:
                iface = {}

	iface[words[0]] = " ".join(words[1:])
        data[current] = iface
	return current

#####
# Writers
#
# Writers take the form of 'write_<keyword>` where keyword is an interface
# attribute. The role of the writer is to output the attribute to the
# output stream, i.e. the new interface file.
#####

# Writes a generic name / value pair indented
def write_attr(out, name, value):
	out.write("  %s %s\n" % (name, value))

# Writes an interface definition to the output stream
def write_iface(out, name, iface):
	if "auto" in iface.keys() and iface["auto"] == "True":
		out.write("auto %s\n" % (name))
	out.write("iface %s %s %s\n" % (name, iface["type"], iface["config"]))
	for attr in sorted(iface.keys(), key=lambda x:x in write_sort_order.keys() and write_sort_order[x] or 100):
		if attr in write_ignore:
			continue
		writer = "write_%s" % (attr)
		if writer in all_methods:
			globals()[writer](out, attr, iface[attr])
		else:
			write_attr(out, attr, iface[attr])
	out.write("\n")

# Writes the new interface file
def write(out, data):
	out.write("# This file describes the network interfaces available on your system\n")
	out.write("# and how to activate them. For more information, see interfaces(5).\n\n")
	# First to loopback
	for name, iface in data.items():
		if iface["config"] != "loopback":
			continue
		write_iface(out, name, iface)

	for iface in sorted(data.keys()):
		if data[iface]["config"] == "loopback":
			continue
		write_iface(out, iface, data[iface])

# The defaults for the netfile task
src_file = "/etc/network/interfaces"
dest_file = ""
state = "present"
name = ""
force = False
values = {
	"config": "manual",
	"type": "inet"
}

# read the argument string from the arguments file
args_file = sys.argv[1]
args_data = file(args_file).read()

# parse the task options
arguments = shlex.split(args_data)
for arg in arguments:
	# ignore any arguments without an equals in it
        if "=" in arg:
		(key, value) = arg.split("=")
        # if setting the time, the key 'time'
        # will contain the value we want to set the time to

        if key == "src":
		src_file = value
	elif key == "dest":
		dest_file = value
	elif key == "name":
		name = value
	elif key == "state":
		state = value
	elif key == "force":
		force = value.lower() in ['true', 't', 'yes', 'y']
	elif key[0] != '_':
		values[key] = value

# all methods is used to check if parser or writer methods exist
all_methods = dir()

# which attributes should be ignored and not be written as single
# attributes values against and interface
write_ignore = ["auto", "type", "config"]

# specifies the order in which attributes are written against an
# interface. Any attribute note in this list is sorted by default
# order after the attributes specified.
write_sort_order = {
		"address" :   1,
		"network" :   2,
		"netmask" :   3,
		"broadcast" : 4,
		"gateway" :   5
}

# Read and parse the specified interface file
file = open(src_file, "r")
ifaces = {}
current = "" # The current interface being parsed
for line in file.readlines():
	line = line.rstrip('\n')

	# Drop any comment of blank line
	if comment.match(line) or blank.match(line):
		continue

	# Parse the line
	words = line.split()
	parser = "parse_" + words[0].replace("-", "_")
	if parser in all_methods:
		current = globals()[parser](ifaces, current, words)
	else:
		current = parse_add_attr(ifaces, current, words)

file.close()

# Assume no change unless we discover otherwise
result = {
	"changed" : False
}

# if the interface specified and state is present then either add
# it to the model or replace it if it already exists.
if state == "query":
	if name in ifaces.keys():
		result["interface"] = ifaces[name]
		result["found"] = True
	else:
		result["found"] = False
elif state == "present":
	if name in ifaces.keys():
		have = ifaces[name]
		if cmp(have, values) != 0:
			ifaces[name] = values
			result["changed"] = True
	else:
		ifaces[name] = values
		result["changed"] = True


# if state is absent then remove it from the model
elif state == "absent" and name in ifaces.keys():
	del ifaces[name]
	result["changed"] = True

# Only write the output file if something has changed or if the
# task requests a forced write.
if force or result["changed"]:
	file = open(dest_file, "w+")
	write(file, ifaces)
	file.close()

# Output the task result
print json.dumps(result)
