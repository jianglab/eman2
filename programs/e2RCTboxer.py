#!/usr/bin/env python
#
# Author: John Flanagan (jfflanag@bcm.edu)
# Copyright (c) 2000-2006 Baylor College of Medicine


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
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  2111-1307 USA
#
#
from EMAN2 import *
from optparse import OptionParser
from PyQt4 import QtCore
from emapplication import EMApp
from emimagemx import EMImageMXWidget
from emimage2d import EMImage2DWidget
from pyemtbx.boxertools import BigImageCache
from emrctstrategy import Strategy2IMGMan, Strategy2IMGPair
from emrctboxergui import ControlPannel
import os, sys, itertools

EMBOXERRCT_DB = "bdb:emboxerrct"

def main():
	progname = os.path.basename(sys.argv[0])
	usage = """%prog [options] <image> <image2>....
This is a tilted - untilted particle particle picker, for use in RCT particle picking
"""

	parser = OptionParser(usage=usage,version=EMANVERSION)
	parser.add_option("--boxsize","-B",type="int",help="Box size in pixels",default=-1)
	parser.add_option("--slow","-S",action="store_true",help="High performace",default=False)
	parser.add_option("--verbose", "-v", dest="verbose", action="store", metavar="n", type="int", default=0, help="verbose level [0-9], higner number means higher level of verboseness")


	# Options need to be accessible, anywhere
	global options
	(options, args) = parser.parse_args()
	
	logid=E2init(sys.argv)
	
	# The RCT DB needs to be accessible, anywhere
	global rctdb 
	rctdb = db_open_dict(EMBOXERRCT_DB)
	
	# Get and set the boxsize
	cache_box_size = True
	if options.boxsize == -1:
		cache_box_size = False
		options.boxsize = rctdb.get("box_size",dfl=128)
	if cache_box_size: rctdb["box_size"] = options.boxsize
	
		
	# Open Application, setup rct object, and run
	application = EMApp()
	rctboxer = RCTboxer(application, options.boxsize)	# Initialize the boxer
	rctboxer.load_untilt_image(args[0])			# Load the untilted image
	rctboxer.load_tilt_image(args[1])			# Load the tilted image
	rctboxer.init_control_pannel_tools()			# Initialize control pannel tools, this needs to be done last as loaded data maybe be used
	application.execute()
	
	# Clean up
	E2end(logid)
	rctdb.close_Dict(EMBOXERRCT_DB)

class RCTboxer:
	'''
	The is the main command and control center for the RCT particle picker.
	This object acts as a mediator for MainWin objects and follows the mediator pattern
	'''
	def __init__(self, application, boxsize):
		self.boxsize = boxsize
		self.parent_window = application
		self.strategy = None
		
		self.widgetlist = []
		self.windowlist = []
		self.init_particles_window()
		self.init_main_window()
		self.init_tilted_window()
		self.init_control_pannel()
		
		EMBox.set_box_color("untilted",[0,0,1])
		EMBox.set_box_color("tilted",[0,1,0])
	
	########################  Client functions ############################################
	
	# initialize the picked particles window
	def init_particles_window(self):
		self.particles_window = ParticlesWindow(self)
		self.parent_window.show_specific(self.particles_window.window)
		self.widgetlist.append(self.particles_window.window)
		
	# initialize tilited and untilted windows, if desired for tilted windows can be easily added
	def init_main_window(self):
		self.untilt_win = MainWin(self, "untilted")
		self.untilt_win.show_mainwin()
		self.widgetlist.append(self.untilt_win.window)
		self.windowlist.append(self.untilt_win)
		self.particles_window.addlist("untilted")
		
	def load_untilt_image(self, filename):
		self.untilt_win.load_image(filename)
		
	def init_tilted_window(self):
		self.tilt_win = MainWin(self, "tilted")
		self.tilt_win.show_mainwin()
		self.widgetlist.append(self.tilt_win.window)
		self.windowlist.append(self.tilt_win)
		self.particles_window.addlist("tilted")
		
	def load_tilt_image(self, filename):
		self.tilt_win.load_image(filename)
	
	# handle pick events comming from the MainWin objects, and then send commands to the MainWin objects in responce (Mediator pattern)
	
	def init_control_pannel(self):
		self.control_window = ControlPannel(self)
		self.parent_window.show_specific(self.control_window)
		self.widgetlist.append(self.control_window)
	
	def init_control_pannel_tools(self):
		self.control_window.configure_tools()
	
	############################ Functions to support Mediator ####################################
	
	def set_strategy(self, strategy):
		self.strategy = strategy(self)
		
	def handle_pick_event(self, caller, x=0, y=0):
		if not self.strategy.pickevent(caller, x, y): return False
		return True
		
	def handle_unpick_event(self, caller, box_num):
		if not self.strategy.unpickevent(caller, box_num): return False
		return True
	
	def handle_move_event(self):
		if not self.strategy.moveevent(): return False
		return True
		
	def update_particles(self, particles, idx):
		self.particles_window.update_particles(particles, idx)
		
	def configure_strategy(self, caller):
		if self.strategy != None:
			self.strategy.configure_strategy(caller)
		
	def handle_strategy_signal(self, signal):
		self.strategy.handle_strategy_signal(signal)
			
class ParticlesWindow:
	def __init__(self, rctwidget):
		self.rctwidget = rctwidget
		self.window=EMImageMXWidget(application=self.rctwidget.parent_window)
		self.window.set_display_values(["tilt","PImg#"])
		self.window.desktop_hint = "rotor" # this is to make it work in the desktop
		self.window.set_mouse_mode("App")
		self.window.setWindowTitle("Particles")
		self.window.optimally_resize()
		self.connect_signals()
		self.listsofparts = []
		self.numlists = 0
		self.closed = False
	
	def addlist(self, name):
		data = []
		data.append(name)
		data.append(0)
		data.append([])
		self.listsofparts.append(data)
		self.numlists = len(self.listsofparts)
		
	def update_particles(self, particles, idx):
		#print self.listsofparts[idx][0]
		# reset the relevent list of particles
		self.listsofparts[idx][1] = len(particles)
		self.listsofparts[idx][2] = particles
		
		# get the number of lists and the minimum number of particles in a given list..
		listlength = 100000000000000	# It would be nice to have something elegant like Math.Inf, but sometime python can be a PoS
		for lst in self.listsofparts:
			listlength = min(listlength, lst[1])
		#print listlength
		
		i = 0
		self.totparts = []
		for part in xrange(listlength):	
			for lst in xrange(self.numlists):
				self.listsofparts[lst][2][part].set_attr("tilt", self.listsofparts[lst][0])
				self.listsofparts[lst][2][part].set_attr("PImg#", part)
				self.totparts.append(self.listsofparts[lst][2][part])
				i += 1	

		if self.totparts != []:	
			self.window.set_data(self.totparts)
			self.window.updateGL()
			
	def connect_signals(self):
		QtCore.QObject.connect(self.window,QtCore.SIGNAL("mx_image_selected"),self.box_selected)
		QtCore.QObject.connect(self.window,QtCore.SIGNAL("mx_mousedrag"),self.box_moved)
		QtCore.QObject.connect(self.window,QtCore.SIGNAL("mx_mouseup"),self.box_released)
		QtCore.QObject.connect(self.window,QtCore.SIGNAL("mx_boxdeleted"),self.box_image_deleted)
		QtCore.QObject.connect(self.window,QtCore.SIGNAL("module_closed"),self.module_closed)
			
	def box_selected(self,event,lc):
		if lc == None or lc[0] == None: return
		self.moving_box_data = [event.x(),event.y(),lc[0]]
	
	def box_moved(self,event,scale):
		winidx = self.moving_box_data[2] % self.numlists
		ppidx = int(self.moving_box_data[2]/self.numlists)
		if self.moving_box_data:
			dx = 0.2*(event.x() - self.moving_box_data[0])
			dy = 0.2*(self.moving_box_data[1] - event.y())
			self.rctwidget.windowlist[winidx].boxes.move_box(ppidx,dx,dy)
			self.rctwidget.windowlist[winidx].update_mainwin()
			self.rctwidget.windowlist[winidx].update_particles()
		
	def box_released(self, event,lc):
		pass
		
	def box_image_deleted(self,event,lc):
		if lc == None or lc[0] == None: return
		
		#delete all particle pairs
		ppidx = int(lc[0]/self.numlists)
		for i,window in enumerate(self.rctwidget.windowlist):
			window.boxes.remove_box(ppidx,self.rctwidget.boxsize)
			window.update_mainwin()
			window.update_particles()
		
	def module_closed(self):
		pass
		#if not self.closed:
			#print "Saving particles"
			#self.rctwidget.control_window.on_write()
			#self.closed = True
			
class MainWin:
	'''
	This is an encapulation of the main micrograph windows, tilted and untilted.
	'''
	def __init__(self, rctwidget, name):
		self.name = name
		self.filename = None
		self.rctwidget = rctwidget
		self.window = EMImage2DWidget(application=self.rctwidget.parent_window)
		self.boxes = EMBoxList()
		self.window.set_mouse_mode(0)
		self.connect_signals()
		self.moving = None
		self.data = None
		self.win_xsize = 0
		self.win_ysize = 0
		
	def connect_signals(self):
		QtCore.QObject.connect(self.window,QtCore.SIGNAL("mousedown"),self.mouse_down)
		QtCore.QObject.connect(self.window,QtCore.SIGNAL("mousedrag"),self.mouse_drag)
		QtCore.QObject.connect(self.window,QtCore.SIGNAL("mouseup")  ,self.mouse_up  )
		QtCore.QObject.connect(self.window,QtCore.SIGNAL("keypress"),self.key_press)
		QtCore.QObject.connect(self.window,QtCore.SIGNAL("mousewheel"),self.mouse_wheel)
		QtCore.QObject.connect(self.window,QtCore.SIGNAL("mousemove"),self.mouse_move)
		QtCore.QObject.connect(self.window,QtCore.SIGNAL("module_closed"),self.module_closed)
	
	def paint_mask(self,v1x,v1y,v2x,v2y,v3x,v3y,v4x,v4y):
		self.boxes.add_mask(0,0,v1x,v1y,self.win_xsize,0,v2x,v2y,self.win_xsize,self.win_ysize,v3x,v3y,0,self.win_ysize,v4x,v4y)
		
	def load_image(self, filename):
		self.filename = filename
		self.data=BigImageCache.get_object(filename).get_image(use_alternate=True)
		self.window.set_data(self.data, filename)
		self.window.force_display_update()
		self.window.optimally_resize()
		self.load_database()
		self.win_xsize = self.window.data.get_xsize()
		self.win_ysize = self.window.data.get_ysize()
		
	def reload_image(self, data, newfilename, mainonly=True):
		self.window.set_data(data, self.filename)
		self.window.force_display_update()
		if mainonly == False:
			self.filename = newfilename
			
		self.win_xsize = self.window.data.get_xsize()
		self.win_ysize = self.window.data.get_ysize()
		
	def load_database(self):
		self.boxes.set_boxes_db(name=self.name, entry=self.filename)	# set the name and entry of the db, the name reprents the window, and the entry, each instance of the window
		if(self.boxes.load_boxes_from_db()):				# load boxes from db
			self.window.set_shapes(self.boxes.get_box_shapes(self.rctwidget.boxsize))
			self.window.updateGL()
			self.update_particles()					# Load particles in particles window
		
	def show_mainwin(self):
		self.rctwidget.parent_window.show_specific(self.window)
	
	def update_mainwin(self):
		self.window.set_shapes(self.boxes.get_box_shapes(self.rctwidget.boxsize))
		self.window.updateGL()
		
	def mouse_down(self, event):
		#print window.parentobj.test
		m = self.window.scr_to_img((event.x(),event.y()))
		box_num = self.boxes.detect_collision(m[0],m[1],self.rctwidget.boxsize)
		if(box_num == -1):
			if event.modifiers()&QtCore.Qt.ShiftModifier: return 	# the user tried to delete nothing	
			if not self.rctwidget.handle_pick_event(self, m[0], m[1]): return
			box_num = self.boxes.append_box(m[0],m[1])
			self.moving=[m,box_num]
		else:
			if event.modifiers()&QtCore.Qt.ShiftModifier:
				if not self.rctwidget.handle_unpick_event(self, box_num): return	# The unpick failed
				self.boxes.remove_box(box_num, self.rctwidget.boxsize)
				self.moving=[m,box_num]	# This is just to say that we have changes something
			else:
				self.moving=[m,box_num]
		
	def mouse_drag(self, event):
		if self.moving != None:
			m=self.window.scr_to_img((event.x(),event.y()))
			oldm = self.moving[0]
			if not self.rctwidget.handle_move_event(): return	# The move failed
			self.boxes.move_box(self.moving[1],m[0]-oldm[0],m[1]-oldm[1])
			self.moving[0] = m
			self.window.update_shapes(self.boxes.get_box_shapes(self.rctwidget.boxsize))
			self.window.updateGL()
			if options.slow:
				self.update_particles()	# slows things down too much
		
	def mouse_up(self, event):
		if self.moving != None:
			self.update_mainwin()
			self.update_particles()
		self.moving=None
		
	def key_press(self, event):
		print "Main keypress"
		
	def mouse_wheel(self, event):
		print "Main mouse_wheel"
		
	def mouse_move(self, event):
		pass
		
	def module_closed(self):
		self.boxes.close_db()
		#print "Main module closed"
	
	def update_particles(self):
		self.rctwidget.update_particles(self.boxes.get_particle_images(self.filename,self.rctwidget.boxsize),self.boxes.objectidx)

class EMBoxList:
	'''
	This is a container for the EMBox objects, this class follows the compiste pattern
	'''
	OBJECTIDX = 0
	def __init__(self):
		self.box_type = "manual"	# This is to set a default box type
		self.entry = None		# this is to say that we haven't setup a database yet
		self.shape_string = "rect"	# This is to set the box shape
		self.boxlist = []		# A list containg all the box objects
		self.shapelist = []		# A list containing all the box shape objects (there is one box shape object to 1 box object, in the future I will make the box object store the shape object, this is just some crap code I inherited)
		self.labellist = []		# A list of label objects
		self.boxpopulation = 0		# The number of boxes stored in the list
		self.objectidx = EMBoxList.OBJECTIDX	# The index of the current object
		self.fontsize = 60.0
		EMBoxList.OBJECTIDX += 1
		self.mask = None
	
	def add_mask(self, vo1x, vo1y, vi1x, vi1y, vo2x, vo2y, vi2x, vi2y, vo3x, vo3y, vi3x, vi3y, vo4x, vo4y, vi4x, vi4y):
		from emshape import EMShape
		self.mask = EMShape(["mask",0,0,0, vo1x, vo1y, vi1x, vi1y, vo2x, vo2y, vi2x, vi2y, vo3x, vo3y, vi3x, vi3y, vo4x, vo4y, vi4x, vi4y])
	
	def set_boxes_db(self, name = "boxlist", entry="default.mrc"):
		self.entry = entry
		self.box_type = name
		self.db = db_open_dict("bdb:e2boxercache"+"#boxes"+name)	#db for data in this window
		
	def close_db(self):
		db_close_dict(self.db)
		
	def load_boxes_from_db(self):
		data = self.db[self.entry]

		if data != None:
			for box in data:
				self.append_box(box[0],box[1],box[2])
			return True
		return False
				
	def save_boxes_to_db(self):
		self.db[self.entry] = [[box.x,box.y,box.type] for box in self.boxlist]
	
	def get_particle_images(self,image_name,box_size):
		return [box.get_image(image_name,box_size,"normalize.edgemean") for box in self.boxlist]
		
	def append_box(self,x,y,score=0.0):
		''' appeds a box to a list of boxes in the composite'''
		self.boxlist.append(EMBox(x,y,self.box_type,score))
		self.shapelist.append(None)	# cache for shape objects
		self.labellist.append(None)	# Cahce for label objects
		self.save_boxes_to_db()		# This is not the greatest way of doing things as the list should be appended, not rewritten
		self.boxpopulation += 1
		return len(self.boxlist)-1
	
	def remove_box(self,idx,box_size):
		self.shapelist.pop(idx)	# Hmmmm.....
		self.labellist.pop(idx) # Hmmmm.....
		self.boxlist.pop(idx)
		# Relabel boxes
		for i in range(len(self.labellist)):
			self.labellist[i] = self.boxlist[i].get_label(i,self.fontsize,box_size)
			
		self.boxpopulation -= 1
		self.save_boxes_to_db()		# This is not the greatest way of doing things as the list should be appended, not rewritten
	
	def clear_boxes(self):
		for i in xrange(len(self.boxlist)-1,-1,-1):
			self.boxlist.pop(i)
			self.shapelist.pop(i)
			self.labellist.pop(i)
			
	def move_box(self,i,dx,dy):
		self.boxlist[i].move(dx,dy)
		self.shapelist[i] = None
		self.labellist[i] = None
		self.save_boxes_to_db()		# This is not the greatest way of doing things as the list should be appended, not rewritten
		
	def get_box_shapes(self,box_size):
		d = {}
		for i in range(len(self.boxlist)):
			if self.shapelist[i] == None:
				shape = self.boxlist[i].get_shape(self.shape_string,box_size)
				self.shapelist[i] = shape
			d[i] = self.shapelist[i]
		
		lsize = len(self.boxlist)
		for i in range(len(self.labellist)):
			if self.labellist[i] == None:
				label = self.boxlist[i].get_label(i,self.fontsize,box_size)
				self.labellist[i] = label
			d[i+lsize] = self.labellist[i]
			
		# Add a mask if requested
		if self.mask != None:
			d[2*lsize] = self.mask
		
		return d
		
	def reset_shapes(self):
		self.shapelist = [None for i in range(len(self.boxlist))]
		self.labellist = [None for i in range(len(self.boxlist))]
		
	def reset_images(self):
		for box in self.boxlist: box.reset_image()
		
	def write_particles(self,input_file_name,out_file_name,box_size,normproc=None):
		db_remove_dict(out_file_name)	# Delete any old data
		for i,box in enumerate(self.boxlist):
			image = box.get_image(input_file_name,box_size)
			if str(normproc) != "None": image.process_inplace(normproc)
			image.write_image(out_file_name,i)
	
	def detect_collision(self,x,y,box_size):
		for i, box in enumerate(self.boxlist):
			if box.collision(x,y,box_size):
				return i
		
		return -1
	
class EMBox:
	'''
	A basic encapsulation of a box - it has a central coordinate, a type attribute which can be
	customized for specific boxes, and a score attribute, which could be useful to a particular
	tool.
	Also has convenient functions for moving, getting the associated box image, etc
	'''
	BOX_COLORS = {}
	def __init__(self,x,y,type,score=0.0):
		self.x = x # central x coordinate
		self.y = y # central y coordinate
		self.type = type # type can be customized
		self.score = score # can be some kind of score, such as correlation
		self.image = None # an image
	
	def set_box_color(box_type,box_color,force=False):
		'''
		static - use this function to register a box color with a particular EMBox.type attribute
		This is critical - if you don't register your unique box type using this function you'll
		get a runttime error
		@param box_type a string such as "manual" or "swarm_auto", or "swarm_ref", etc
		@param box_color an RGB list [R,G,B] (floats)
		@param force something you'd set to True if you want to force the overwrite of the old color (previously stored)
		'''
		if not force and EMBox.BOX_COLORS.has_key(box_type):
			# this is just to make sure there are no conflicts - if someone is resetting a color they 
			# should know what they're doing
			raise RuntimeError("Error, attempt to set a color key (%s) that already existed" %box_type)
		EMBox.BOX_COLORS[box_type] = box_color
		
	set_box_color = staticmethod(set_box_color)
	
	def get_image(self,image_name,box_size,norm=None):
		if self.image == None or self.image.get_xsize() != box_size or self.image.get_ysize() != box_size:
			global BigImageCache
			data=BigImageCache.get_object(image_name).get_image(use_alternate=True) # use alternate is a red herring
			r = Region(self.x-box_size/2,self.y-box_size/2,box_size,box_size)
			self.image = data.get_clip(r)
			if norm != None:
				self.image.process_inplace(norm)
				
			self.image.set_attr("ptcl_source_coord",[self.x,self.y])
			self.image.set_attr("ptcl_source_image",image_name)
			
		return self.image
		
	def move(self,dx,dy):
		self.x += dx
		self.y += dy
		self.image = None
		
	def get_shape(self,shape_string,box_size):
		if EMBox.BOX_COLORS.has_key(self.type):
			r,g,b = EMBox.BOX_COLORS[self.type]
		else:
			r,g,b = 1.0,0.42,0.71 # hot pink, apparently ;)
		from emshape import EMShape
		shape = EMShape([shape_string,r,g,b,self.x-box_size/2,self.y-box_size/2,self.x+box_size/2,self.y+box_size/2,2.0])
		return shape
	
	def reset_image(self): self.image = None
	
	def get_label(self, text, size, box_size):
		from emshape import EMShape
		label = EMShape(["label",1,1,1,self.x-box_size/2,self.y+box_size/2+10,str(text),size,2.0])
		return label
		
	def collision(self,x,y,box_size):
		if x-box_size/2 < self.x and x+box_size/2 > self.x and y-box_size/2 < self.y and y+box_size/2 > self.y: return True
		else: return False
	
if __name__ == "__main__":
	main()
