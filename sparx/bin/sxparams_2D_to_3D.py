#!/usr/bin/env python
from __future__ import print_function
#
# Author: Wei Zhang, 01/22/2007 (Wei.zhang@uth.tmc.edu)
# Copyright (c) 2000-2006 The University of Texas - Houston Medical School
#
# This software is issued under a joint BSD/GNU license. You may use the
# source code in this file under either license. However, note that the
# complete EMAN2 and SPARX software packages have some GPL dependencies,
# so you are responsible for compliance with the licenses of these packages
# if you opt to use BSD licensing. The warranty disclaimer below holds
# in either instance.
#
# This complete copyright notice must be included in any revised version of the
# source code. Additional authorship citations may be added, but existing
# author citations must be preserved.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307 USA
#
#

import applications
import global_def
import optparse
import os
import sys
import utilities

def main():
	progname = os.path.basename( sys.argv[0] )
	usage = progname + "stack"
	parser = optparse.OptionParser(usage, version=global_def.SPARXVERSION)
	(options, args) = parser.parse_args(sys.argv[1:])

	if len(args) != 1:
    		print("usage: " + usage)
    		print("Please run '" + progname + " -h' for detailed options")
	else:
		if global_def.CACHE_DISABLE:
			utilities.disable_bdb_cache()
		global_def.BATCH = True
		applications.wrapper_params_2D_to_3D(args[0])
		global_def.BATCH = False     
			

if __name__=="__main__":
	main()
