#!/usr/bin/env python
from __future__ import print_function
from __future__ import division

import os
import platform

e2real = os.path.join(os.path.abspath(os.path.dirname(__file__)), "e2_real.py")
try:
	if platform.system()=="Linux" and os.getenv("DISPLAY")==None: raise Exception
	os.execlp("ipython","ipython","-i","--gui=qt5",e2real)
except:
	print("Warning: No DISPLAY available, running in non-GUI mode.")
	os.execlp("ipython","ipython","-i",e2real)
