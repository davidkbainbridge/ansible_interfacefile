#!/usr/bin/env python

import json
import os
import re
import sys
import shlex
import string
import ipaddress

comment = re.compile("^\s*#")
blank = re.compile("^\s*$")

def parse_auto(data, current, words):
	if words[1] in data.keys():
		iface = data[words[1]]
	else:
		iface = {}

	iface["auto"] = "True"
	data[words[1]] = iface
	return words[1]

def parse_iface(data, current, words):
	if words[1] in data.keys():
		iface = data[words[1]]
	else:
		iface = {}

	iface["type"] = words[2]
	iface["config"] = words[3]
	data[words[1]] = iface
	return words[1]

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

def write_attr(out, name, value):
	out.write("  %s %s\n" % (name, value))

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

all_methods = dir()
write_ignore = ["auto", "type", "config"]
write_sort_order = {
		"address" :   1,
		"network" :   2,
		"netmask" :   3,
		"broadcast" : 4,
		"gateway" :   5
}

file = open(src_file, "r")
ifaces = {}
current = ""
for line in file.readlines():
	line = line.rstrip('\n')
	if comment.match(line) or blank.match(line):
		continue
	words = line.split()
	parser = "parse_" + words[0].replace("-", "_")
	if parser in all_methods:
		current = globals()[parser](ifaces, current, words)
	else:
		current = parse_add_attr(ifaces, current, words)

file.close()

result = {
	"changed" : False
}
if state == "present":
	if name in ifaces.keys():
		have = ifaces[name]
		if cmp(have, values) != 0:
			ifaces[name] = values
			result["changed"] = True
	else:
		ifaces[name] = values
		result["changed"] = True


elif state == "absent" and name in ifaces.keys():
	del ifaces[name]
	result["changed"] = True

if force or result["changed"]:
	file = open(dest_file, "w+")
	write(file, ifaces)
	file.close()

print json.dumps(result)
