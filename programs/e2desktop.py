#!/usr/bin/env python

#
# Author: David Woolford 10/2008 (woolford@bcm.edu)
# Copyright (c) 2000-2006 Baylor College of Medicine
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
# Foundation, Inc., 59 Temple Place, Suite 330, Boston MA 02111-1307 USA
#

import PyQt4
from PyQt4 import QtCore, QtGui, QtOpenGL
from PyQt4.QtCore import Qt
#from OpenGL import GL,GLU,GLUT
from OpenGL.GL import *
from OpenGL.GLU import *

from OpenGL.GLUT import *
from valslider import ValSlider
from math import *
from EMAN2 import *
import EMAN2
import sys
import numpy

from weakref import WeakKeyDictionary
from pickle import dumps,loads
from PyQt4.QtCore import QTimer
import math

from emglobjects import Camera,EMGLProjectionViewMatrices
from e2boxer import EMBoxerModule
from embrowse import EMBrowserDialog
from emselector import EMSelectorDialog
from emapplication import EMApplication, EMQtWidgetModule
from emanimationutil import *
from emimageutil import EMEventRerouter
from emfloatingwidgets import *

class EMWindowNode:
	def __init__(self,parent):
		self.parent = parent
		self.children = []
		
	def attach_child(self,new_child):
		for child in self.children:
			if (child == new_child):
				print "error, can not attach the same child to the same parent more than once"
				return
		
		self.children.append(new_child)
		
	def detach_child(self,new_child):
		for i,child in enumerate(self.children):
			if (child == new_child):
				self.children.pop(i)
				return
			
		print "error, can not detach the child from a parent it doesn't belong to"
	
	def set_parent(self,parent):
		self.parent = parent
		
	def parent_width(self):
		return parent.width()
	
	def parent_height(self):
		return parent.height()
	
	def get_children(self):
		return self.children

	def emit(self,*args, **kargs):
		EMDesktop.main_widget.emit(*args,**kargs)
		
	def get_near_plane_dims(self):
		return EMDesktop.main_widget.get_near_plane_dims()
	
	def getStartZ(self):
		return EMDesktop.main_widget.getStartZ()
	
class EMRegion:
	def __init__(self,geometry=Region(0,0,0,0,0,0)):
		self.geometry = geometry
		
	def set_geometry(self,geometry):
		self.geometry = geometry
		
	def get_geometry(self): return self.geometry
	
	def width(self):
		return int(self.geometry.get_width())
	
	def height(self):
		return int(self.geometry.get_height())
		
	def depth(self):
		return int(self.geometry.get_depth())
	
	def set_width(self,v):
		self.geometry.set_width(v)
	
	def set_height(self,v):
		self.geometry.set_height(v)
		
	def set_depth(self,v):
		self.geometry.set_depth(v)
	
	def get_size(self):
		return self.geometry.get_size()
	
	def get_origin(self):
		return self.geometry.get_origin()
	
	def set_origin(self,v):
		return self.geometry.set_origin(v)
	
	def resize(self,width,height,depth=0):
		self.geometry.set_width(width)
		self.geometry.set_height(height)
		self.geometry.set_depth(depth)

class EMGLViewContainer(EMWindowNode,EMRegion):
	def __init__(self,parent,geometry=Region(0,0,0,0,0,0)):
		EMWindowNode.__init__(self,parent)
		EMRegion.__init__(self,geometry)
		self.current = None
		self.previous = None
		
		self.selected_object = None
		self.multi_selected_objects = [] # as grown using "ctrl-click" selection, for event master slave
		
		self.connections = []
		
	def draw(self):
		for child in self.children:
			glPushMatrix()
			glTranslate(*self.get_origin())
			child.draw()
			glPopMatrix()
	
	def updateGL(self):
		self.parent.updateGL()
		
	def resizeEvent(self, width, height):
		for child in self.children:
			child.set_update_P_inv()
	
	def mousePressEvent(self, event):
		for child in self.children:
			if ( child.isinwin(event.x(),EMDesktop.main_widget.viewport_height()-event.y()) ):
				child.mousePressEvent(event)
				self.updateGL()
				return True
		
		False
	
	def mouseMoveEvent(self, event):
		for child in self.children:
			if ( child.isinwin(event.x(),EMDesktop.main_widget.viewport_height()-event.y()) ):
				self.current = child
				if (self.current != self.previous ):
					if ( self.previous != None ):
						try: self.previous.leaveEvent()
						except: pass
				child.mouseMoveEvent(event)
				self.previous = child
				self.updateGL()
				return True
		
		return False
		
	def mouseReleaseEvent(self, event):
		for child in self.children:
			if ( child.isinwin(event.x(),EMDesktop.main_widget.viewport_height()-event.y()) ):
				child.mouseReleaseEvent(event)
				self.updateGL()
				return True
			
		return False
					
		
	def mouseDoubleClickEvent(self, event):
		for child in self.children:
			if ( child.isinwin(event.x(),EMDesktop.main_widget.viewport_height()-event.y()) ):
				child.mouseDoubleClickEvent(event)
				self.updateGL()
				return True
		return False
		
	def wheelEvent(self, event):
		
		for child in self.children:
			if ( child.isinwin(event.x(),EMDesktop.main_widget.viewport_height()-event.y()) ):
				child.wheelEvent(event)
				self.updateGL()
				return True
		
		return False

	def toolTipEvent(self, event):
		for child in self.children:
			if ( child.isinwin(event.x(),EMDesktop.main_widget.viewport_height()-event.y()) ):
				child.toolTipEvent(event)
				self.updateGL()
				QtGui.QToolTip.hideText()
				return True
		
		return False

	def keyPressEvent(self,event):
		for child in self.children:
			pos = EMDesktop.main_widget.mapFromGlobal(QtGui.QCursor.pos())
			if ( child.isinwin(pos.x(),EMDesktop.main_widget.viewport_height()-pos.y()) ):
				child.keyPressEvent(event)
				self.updateGL()
				return True
				#QtGui.QToolTip.hideText()

	def dragMoveEvent(self,event):
		print "received drag move event"
		
	def event(self,event):
		#print "event"
		#QtGui.QToolTip.hideText()
		if event.type() == QtCore.QEvent.MouseButtonPress: 
			self.mousePressEvent(event)
			return True
		elif event.type() == QtCore.QEvent.MouseButtonRelease:
			self.mouseReleaseEvent(event)
			return True
		elif event.type() == QtCore.QEvent.MouseMove: 
			self.mouseMoveEvent(event)
			return True
		elif event.type() == QtCore.QEvent.MouseButtonDblClick: 
			self.mouseDoubleClickEvent(event)
			return True
		elif event.type() == QtCore.QEvent.Wheel: 
			self.wheelEvent(event)
			return True
		elif event.type() == QtCore.QEvent.ToolTip: 
			self.toolTipEvent(event)
			return True
		elif event.type() == QtCore.QEvent.KeyPress: 
			self.keyPressEvent(event)
			return True
		else: 
			return False
			#return QtOpenGL.QGLWidget.event(self,event)

	def hoverEvent(self,event):
		#print "hoverEvent
		for child in self.children:
			if ( child.isinwin(event.x(),self.height()-event.y()) ):
				child.hoverEvent(event)
				return True
		
		return False
				#break
		#self.updateGL()

	def isinwin(self,x,y):
		for child in self.children:
			if child.isinwin(x,y) : return True
			
		return False
			
	def window_selected(self,object,event):
		'''
		Manages multiple selection. Acts on the control modifier
		'''
		
		if event.modifiers()&Qt.ControlModifier:
			
			if object in self.multi_selected_objects:
				# unselect the object
				object.set_selected(False)
				self.multi_selected_objects.remove(object)
				
				if self.selected_object == object:
					# be careful to make sure the selected object isn't dangling
					self.selected_object = None
				
				self.__update_slave_master_connections()
				return
			
			# if we made it hear the user is adding another selected window
			self.multi_selected_objects.append(object)
			object.set_selected(True)
			if self.selected_object == None:
				# if there was no selected object then automatically make this the selected object
				self.selected_object = object
			self.__update_slave_master_connections()
			return
			
		if object in self.multi_selected_objects: 
			# This is a nice way of allowing the selected object to change without losing the
			# selected groupd
			self.selected_object = object
			self.__update_slave_master_connections()
			return
		
		if self.selected_object == object: 
			# of course, nothing should happen
			return
		
		# if we made it hear then it's time to clear all the selections and establish a single
		# selected window
		for obj in self.multi_selected_objects: 
			obj.set_selected(False)
		
		self.selected_object = object
		self.selected_object.set_selected(True)
		self.multi_selected_objects = [object]
		self.__update_slave_master_connections()

	def __update_slave_master_connections(self):
		
		self.__clear_connections()
		if self.selected_object != None:
			if len(self.multi_selected_objects) > 1 :
				for object in self.multi_selected_objects:
					object.set_events_master(False)
					object.set_camera_slaved(True)
			
					
				self.selected_object.set_events_master(True)
				self.selected_object.set_camera_slaved(False)
			
				signals = self.selected_object.get_emit_signals_and_connections()
				
				for object in self.multi_selected_objects:
					if object != self.selected_object:
						signals_2 = object.get_emit_signals_and_connections()
						for sig in signals:
							try:
								QtCore.QObject.connect(EMDesktop.main_widget, QtCore.SIGNAL(sig), signals_2[sig])
								self.connections.append({sig:signals_2[sig]})
							except: 
								print "failed on",sig
								
	def __clear_connections(self):
		for c in self.connections:
			a = c.items()[0]
			QtCore.QObject.disconnect(EMDesktop.main_widget, QtCore.SIGNAL(a[0]), a[1])
		
		self.connections = []
		
class Translation:
	def __init__(self,child):
		self.child = child
		self.translation_animation = None
		self.p1 = None
		self.p2 = None
		
		self.translation = (0,0,0)
	def __del__(self):
		if self.translation_animation != None:
			self.translation_animation.set_animated(False) # this will cause the EMDesktop to stop animating
			self.translation_animation = None
	
	def animation_done_event(self,child):
		self.child.unlock_texture()
	
	def get_translation(self):
		return (self.x,self.y,self.z)
		
	def seed_translation_animation(self,p1,p2):
		self.translation = p1
		self.p1 = p1
		self.p2 = p2
		animation = TranslationAnimation(self,p1,p2)
		
		self.translation_animation = animation
		EMDesktop.main_widget.register_animatable(animation)
		self.child.lock_texture()
	
	def set_translation(self,translation):
		self.translation = translation
	
	def transform(self):
		if self.translation_animation != None and self.translation_animation.is_animated() :
			glTranslate(*self.translation)
			return True
		else:
			self.translation_animation = None 
			return False

class Rotation:
	def __init__(self,child,axis=[1,0,0]):
		self.child = child
		self.rotation_animation = None
		self.r1 = None
		self.r2 = None
		self.rotation = None
		self.axis = axis

	def __del__(self):
		if self.rotation_animation != None:
			self.rotation_animation.set_animated(False) # this will cause the EMDesktop to stop animating
			self.rotation_animation = None
	
	def animation_done_event(self,child):
		self.child.unlock_texture()
	
	def get_rotation(self):
		return self.rotation
		
	def seed_rotation_animation(self,r1,r2):
		self.rotation = r1
		self.r1 = r1
		self.r2 = r2
		animation = SingleValueIncrementAnimation(self,r1,r2)
		
		self.rotation_animation = animation
		EMDesktop.main_widget.register_animatable(animation)
		self.child.lock_texture()
	
	def set_animation_increment(self,value):
		self.rotation = value
	
	def transform(self):
		if self.rotation_animation != None and self.rotation_animation.is_animated() :
			glRotate(self.rotation,*self.axis)
			return True
		else:
			self.rotation_animation = None 
			return False

class Scale:
	def __init__(self,child):
		self.child = child
		self.rotation_animation = None
		self.r1 = None
		self.r2 = None
		self.rotation = None

	def __del__(self):
		if self.rotation_animation != None:
			self.rotation_animation.set_animated(False) # this will cause the EMDesktop to stop animating
			self.rotation_animation = None
	
	def animation_done_event(self,child):
		self.child.unlock_texture()
	
	def get_rotation(self):
		return self.rotation
		
	def seed_rotation_animation(self,r1,r2):
		self.rotation = r1
		self.r1 = r1
		self.r2 = r2
		animation = SingleValueIncrementAnimation(self,r1,r2)
		
		self.rotation_animation = animation
		EMDesktop.main_widget.register_animatable(animation)
		self.child.lock_texture()
	
	def set_animation_increment(self,value):
		self.rotation = value
	
	def transform(self):
		if self.rotation_animation != None and self.rotation_animation.is_animated() :
			glScale(self.rotation,self.rotation,1.0)
			return True
		else:
			self.rotation_animation = None 
			return False



class EMPlainDisplayFrame(EMGLViewContainer):
	count = 0
	def __init__(self,parent,geometry=Region(0,0,0,0,0,0)):
		EMGLViewContainer.__init__(self,parent,geometry)
		EMPlainDisplayFrame.count += 1
		self.first_draw = []
		self.transformers = []
		self.invisible_boundary = 20
		
		self.rows = 2
		self.columns = 2
		
		self.glbasicobjects = None
		#self.glbasicobjects.getCylinderDL()
		
		self.draw_grid = True
		self.window_selected_emit_signal = "display_frame_window_selected_"+str(EMPlainDisplayFrame.count)
		
		QtCore.QObject.connect(EMDesktop.main_widget, QtCore.SIGNAL(self.window_selected_emit_signal), self.window_selected)
		
	def num_rows(self):	return self.rows
	
	def num_cols(self): return self.columns
	
	def set_num_rows(self,rows): self.rows = rows
	def set_num_cols(self,cols): self.columns = cols
	
	def show_grid(self,val):
		#print "setting val",val
		self.draw_grid = val
	
	def apply_row_col(self,cols):
		if len(self.children) > self.rows*self.columns:
			print "can't do that, there are too many children"
			
		else:
			r = 0
			c = 0
			optimal_width = self.width()/self.columns
			optimal_height = self.height()/self.rows
			child_width = optimal_width-2*self.invisible_boundary
			child_height = optimal_height-2*self.invisible_boundary
			for i,child in enumerate(self.children):
				t = Translation(child)
				old_pos = child.get_position()
				new_pos = [ c*(optimal_width)+self.invisible_boundary,self.height()-(r+1)*(optimal_height)+self.invisible_boundary,0]
				trans = [ old_pos[j]-new_pos[j] for j in range(3)]
				
				t.seed_translation_animation(trans,(0,0,0))
				child.set_position(*new_pos)
				
				self.transformers[i].append(t)
				
				c += 1
				if c == self.columns:
					c = 0
					r += 1
				
				#size = child.get_lr_bt_nf()
				child.resize(child_width,child_height)
				
				#width_scale = child_width/float(size[1]-size[0])
				#if width_scale != 1:
					#s = XScale(child)
					#s.seed_rotation_animation(width_scale,1)
					#self.transformers[i].append(s)
				
				#height_scale = child_height/float(size[3]-size[2])
				#if height_scale !=1:
					#x = YScale(child)
					#s.seed_rotation_animation(height_scale,1)
					#self.transformers[i].append(s)
				#
				
				#
				##r.seed_rotation_animation(0,1)
				##self.transformers[len(self.transformers)-1].append(r)
				##t = Translation(child)
				##t.seed_translation_animation((0,0,-300),(0,0,0))
				##self.transformers[len(self.transformers)-1].append(t)
		
	def clear_all(self):
		for child in self.children:
			child.closeEvent(None)
			
		self.children = []
		self.transformers = []
		self.first_draw = [] # just for safety
	def print_info(self):
		
		print self.get_size(),self.get_origin()

	
	def draw(self):
		glPushMatrix()
		glTranslate(*self.get_origin())
		for i,child in enumerate(self.children):
			if child in self.first_draw:
				self.introduce_child(child)
			glPushMatrix()
			if self.transformers[i] != None: 
				for j,transformer in enumerate(self.transformers[i]):
					if transformer and not transformer.transform(): 
						self.transformers[i][j] = None
					
			child.draw()
			glPopMatrix()
		glPopMatrix()
		
		optimal_width = self.width()/self.columns
		optimal_height = self.height()/self.rows
		
		
		if self.draw_grid:
			if self.glbasicobjects == None:
				self.glbasicobjects = EMBasicOpenGLObjects()
				#FIXME USE DISPLAY LIST
			for row in range(self.rows+1):
				
				glPushMatrix()
				glTranslate(*self.get_origin())
				glTranslate(0,row*optimal_height,0)
				glRotate(90,0,1,0)
				glScaled(1.0,1.0,self.width())
				glCallList(self.glbasicobjects.getCylinderDL())
				glPopMatrix()
				
			for col in range(self.columns+1):
				
				glPushMatrix()
				glTranslate(*self.get_origin())
				glTranslate(col*optimal_width,0,0)
				glRotate(-90,1,0,0)
				glScaled(1.0,1.0,self.height())
				glCallList(self.glbasicobjects.getCylinderDL())
				glPopMatrix()

		self.first_draw = []
	
	def find_open_position(self,new_child):
		optimal_width = self.width()/self.columns
		optimal_height = self.height()/self.rows
		
		available = [i for i in range(self.columns*self.rows)]
		
		rm = []
		for child in self.children:
			if child == new_child: continue
			position = child.get_position()
			#print position
			left = position[0]
			right =  left + child.width_inc_border()
			
			x_min_idx = left/optimal_width
			x_max_idx = float(right)/optimal_width
			#print "x s", x_min_idx, x_max_idx
			if x_max_idx != int(x_max_idx): x_max_idx = ceil(x_max_idx) # this is usually the case
			x_max_idx = int(x_max_idx)
		
			bottom = position[1]
			top = bottom + child.height_inc_border()
			#print "lr bt",left,right,bottom,top
			#print "hieghts", child.height_inc_border(),optimal_height
			y_min_idx = bottom/optimal_height
			y_max_idx = float(top)/optimal_height
			#print y_max_idx
			if y_max_idx != int(y_max_idx): y_max_idx = ceil(y_max_idx) # this is usually the case
			y_max_idx = int(y_max_idx)
			#print "prior inversion",(y_min_idx,y_max_idx)
			# screen opposite axis adjustment
			y_min_idx = self.rows - y_min_idx
			y_max_idx = self.rows - y_max_idx
			
			#print (x_min_idx,x_max_idx),(y_min_idx,y_max_idx)
			for x in range(x_min_idx,x_max_idx):
				for y in range(y_max_idx,y_min_idx):
					idx = y*self.columns + x
					if idx not in rm:
						rm.append(idx)
						#print "appended",idx
					
		
		#print "removing",rm
		rm.sort()
		rm.reverse()
		for r in rm: available.pop(r)
		
		#print "available",available
		
		if len(available) == 0: return None
		else: return available[0]
				
	
	def introduce_child(self,child):
		position = self.find_open_position(child)
		#print "position is", position
		
		if position == None:
			#print "no position available"
			return
		
		optimal_width = self.width()/self.columns
		optimal_height = self.height()/self.rows

		child.resize(optimal_width-2*self.invisible_boundary,optimal_height-2*self.invisible_boundary)
		
		if position != 0: col = position % self.columns
		else: col = 0
		row = position / self.columns
		
		child.set_position(col*(optimal_width)+self.invisible_boundary,self.height()-(row+1)*(optimal_height)+self.invisible_boundary,0)
		#print "child position is", child.get_position()
		r = Scale(child)
		r.seed_rotation_animation(0,1)
		
		self.transformers[len(self.transformers)-1].append(r)
		t = Translation(child)
		t.seed_translation_animation((0,0,-300),(0,0,0))
		self.transformers[len(self.transformers)-1].append(t)
	
	def attach_child(self,child):
		#print "attached child", child
		if len(self.children) == self.rows*self.columns:
			print "too many children"
			child.closeEvent(None)
			return
		
		EMGLViewContainer.attach_child(self,child)
		child.set_window_selected_emit_signal( self.window_selected_emit_signal )
		self.transformers.append([])
		self.first_draw.append(child)
		
		
	def detach_child(self,new_child):
		for i,child in enumerate(self.children):
			if (child == new_child):
				self.children.pop(i)
				self.transformers.pop(i)
				#self.reset_scale_animation()
				return
			
		print "error, attempt to detach a child that didn't belong to this parent"

class EMFrame(EMWindowNode,EMRegion):
	'''
	EMFrame is a base class for windows that have a frame. The frame defines a 3D bounding box, and is defined
	in terms of its origin and its size in each dimension
	'''
	def __init__(self,parent,geometry=Region(0,0,0,0,0,0)):
		EMWindowNode.__init__(self,parent)
		EMRegion.__init__(self,geometry)
		self.children = []
	
	def draw(self):
		for child in self.children:
			glPushMatrix()
			child.draw()
			glPopMatrix()
	
	def mousePressEvent(self, event):
		#this could be optimized
		for i in self.children:
			if i.mousePressEvent(event): return True
	
	def mouseMoveEvent(self, event):
		#this could be optimized
		for i in self.children:
			if i.mouseMoveEvent(event): return True
		#EMDesktop.main_widget.updateGL()
	
		
	def mouseReleaseEvent(self, event):
		#this could be optimized
		for i in self.children:
			if i.mouseReleaseEvent(event): return True
	

	def mouseDoubleClickEvent(self, event):
		#this could be optimized
		for i in self.children:
			if i.mouseDoubleClickEvent(event): return True
		
		#EMDesktop.main_widget.updateGL()
	

	def wheelEvent(self, event):
		#this could be optimized
		for i in self.children:
			if i.wheelEvent(event): return True
	
	def keyPressEvent(self, event):
		#this could be optimized
		for i in self.children:
			i.keyPressEvent(event)
	
	def toolTipEvent(self, event):
		#this could be optimized
		for i in self.children:
			i.toolTipEvent(event)



class EMDesktopApplication(EMApplication):
	def __init__(self,target,qt_application_control=True):
		EMApplication.__init__(self,qt_application_control)
		self.target = target
		
		self.children = []
		
	
	def detach_child(self,child):
		for i,child_ in enumerate(self.children):
			if child_ == child:
				self.children.pop(i)
				return
	
		print "error, can't detach a child that doesn't belong to this",child
	
	def attach_child(self,child):
		for i in self.children:
			if i == child:
				print "error, can't attach the same child twice",child
				return
		
		self.children.append(child)
		#self.target.attach_gl_child(child,child.get_desktop_hint())
		
	def ensure_gl_context(self,child):
		EMDesktop.main_widget.context().makeCurrent()
		#pass
	
	def show(self):
		for i in self.children:
			self.target.attach_gl_child(child,child.get_desktop_hint())
		pass
	
	def close_specific(self,child,inspector_too=True):
		for i,child_ in enumerate(self.children):
			if child == child_:
				self.children.pop(i)
				self.target.detach_gl_child(child)
				if inspector_too:
					inspector = child.get_em_inspector()
					if inspector != None:
						self.close_specific(inspector,False)
				return

		print "couldn't close",child
		pass
	
	def hide_specific(self,child,inspector_too=True):
		#self.target.attach_gl_child(child,child.get_desktop_hint())
		pass
	
	def show_specific(self,child):
		self.target.attach_gl_child(child,child.get_desktop_hint())

	def close_child(self,child):
		pass
			
		print "error, attempt to close a child that did not belong to this application"
		
	def __call__( *args, **kwargs ):
		return QtGui.qApp

	def exec_loop( *args, **kwargs ):
		pass

	def get_qt_emitter(self,child):
		return EMDesktop.main_widget
			
	def get_qt_gl_updategl_target(self,child):
		return EMDesktop.main_widget

class EMDesktopFrame(EMFrame):
	image = None
	def __init__(self,parent,geometry=Region(0,0,0,0)):
		EMFrame.__init__(self,parent,geometry)
		self.display_frames = []
		
		EMDesktop.main_widget.register_resize_aware(self)
		
		self.left_side_bar = LeftSideWidgetBar(self)
		self.right_side_bar = RightSideWidgetBar(self)
		self.display_frame = EMPlainDisplayFrame(self)
		self.bottom_bar = BottomWidgetBar(self)
		
		self.attach_display_child(self.display_frame)
		self.attach_child(self.right_side_bar)
		self.attach_child(self.left_side_bar)
		self.attach_child(self.bottom_bar)
		# what is this?
		self.bgob2=ob2dimage(self,self.read_EMAN2_image())
		self.child_mappings = {}
		self.frame_dl = 0
		self.glbasicobjects = EMBasicOpenGLObjects()
		self.borderwidth=10.0
		
		self.type_name = None
	
	def __del__(self):
		if self.frame_dl:
			glDeleteLists(self.frame_dl,1)
			self.frame_dl = 0
	
	def get_type(self):
		return self.type_name
	
	def set_type(self,type_name):
		self.type_name = type_name
	
	def append_task_widget(self,task_widget):
		self.left_side_bar.attach_child(task_widget)
	
	def set_geometry(self,geometry):
		EMFrame.set_geometry(self,geometry)
		#try:
			#for child in self.children:
				#if isinstance(child,EMDesktopTaskWidget):
					#child.set_cam_pos(-self.parent.width()/2.0+child.width()/2.0,self.parent.height()/2.0-child.height()/2.0,0)
					
		#except: pass

	def updateGL(self):
		self.parent.updateGL()
	
	def attach_display_child(self,child):
		self.display_frames.append(child)
		EMWindowNode.attach_child(self,child)
	
	def get_display_child(self,idx=0):
		try: return self.display_frames[idx]
		except:
			print "warning, attempted to ask for a display child that did not exist"
			print "asked for child number ",idx,"but I have only",len(self.display_frames),"display children"
	
	def resize_gl(self):
	
		self.set_geometry(Region(0,0,int(EMDesktop.main_widget.viewport_width()),int(EMDesktop.main_widget.viewport_height())))
		if len(self.display_frames) != 0:
			width = int(EMDesktop.main_widget.viewport_width()-200)
			height = int(EMDesktop.main_widget.viewport_height())-50
			self.display_frames[0].set_geometry(Region(-width/2,-height/2,-20,width,height,100))
			
		if self.frame_dl:
			glDeleteLists(self.frame_dl,1)
			self.frame_dl = 0
			
		self.bgob2.refresh()
	
	def attach_gl_child(self,child,hint):
		for child_,t in self.child_mappings.items():
			if child_ == child: return
		
		if hint == "dialog" or hint == "inspector":
			self.left_side_bar.attach_child(child.get_gl_widget(EMDesktop.main_widget,EMDesktop.main_widget))
			self.child_mappings[child] = self.left_side_bar
		elif hint == "image" or hint == "plot":
			self.display_frame.attach_child(child.get_gl_widget(EMDesktop.main_widget,EMDesktop.main_widget))
			self.child_mappings[child] = self.display_frame
		elif hint == "rotor":
			self.right_side_bar.attach_child(child.get_gl_widget(EMDesktop.main_widget,EMDesktop.main_widget))
			self.child_mappings[child] = self.right_side_bar
		elif hint == "settings":
			self.bottom_bar.attach_child(child.get_gl_widget(EMDesktop.main_widget,EMDesktop.main_widget))
			self.child_mappings[child] = self.bottom_bar
		else:
			print "unsupported",hint
	
	def detach_gl_child(self,child):
		try:
			owner = self.child_mappings[child]
		except:
			print "owner doesn't exist for child",child
			return
			
		owner.detach_child(child.get_gl_widget(None,None))

	def draw_frame(self):
		if self.frame_dl == 0:
			#print self.appwidth/2.0,self.appheight/2.0,self.zopt
			self.glbasicobjects.getCylinderDL()
			self.glbasicobjects.getSphereDL()
			length = self.get_z_opt()
			self.frame_dl=glGenLists(1)
			glNewList(self.frame_dl,GL_COMPILE)
			glPushMatrix()
			glTranslatef(-self.width()/2.0-self.borderwidth,-self.height()/2.0-self.borderwidth,0.0)
			glScaled(self.borderwidth,self.borderwidth,length)
			glCallList(self.glbasicobjects.getCylinderDL())
			glPopMatrix()
			glPushMatrix()
			glTranslatef( self.width()/2.0+self.borderwidth,-self.height()/2.0-self.borderwidth,0.0)
			glScaled(self.borderwidth,self.borderwidth,length)
			glCallList(self.glbasicobjects.getCylinderDL())
			glPopMatrix()
			
			glPushMatrix()
			glTranslatef( self.width()/2.0+self.borderwidth, self.height()/2.0+self.borderwidth,0.0)
			glScaled(self.borderwidth,self.borderwidth,length)
			glCallList(self.glbasicobjects.getCylinderDL())
			glPopMatrix()
			
			glPushMatrix()
			glTranslatef(-self.width()/2.0-self.borderwidth, self.height()/2.0+self.borderwidth,0.0)
			glScaled(self.borderwidth,self.borderwidth,length)
			glCallList(self.glbasicobjects.getCylinderDL())
			glPopMatrix()
			
			glPushMatrix()
			#glTranslatef(0,0,0)
			glTranslate(-self.width()/2.0,self.height()/2.0+self.borderwidth,0)
			glRotate(90,0,1,0)
			
			glScaled(self.borderwidth,self.borderwidth,self.width())
			glCallList(self.glbasicobjects.getCylinderDL())
			glPopMatrix()
			
			glPushMatrix()
			#glTranslatef(0,0,0)
			glTranslate(-self.width()/2.0,-self.height()/2.0-self.borderwidth,0)
			glRotate(90,0,1,0)
			glScaled(self.borderwidth,self.borderwidth,self.width())
			glCallList(self.glbasicobjects.getCylinderDL())
			glPopMatrix()
			
			glPushMatrix()
			glTranslate(-self.width()/2.0-self.borderwidth,-self.height()/2.0-self.borderwidth,0)
			glScale(3*self.borderwidth,3*self.borderwidth,3*self.borderwidth)
			glCallList(self.glbasicobjects.getSphereDL())
			glPopMatrix()
			
			glPushMatrix()
			glTranslate(self.width()/2.0+self.borderwidth,self.height()/2.0+self.borderwidth,0)
			glScale(3*self.borderwidth,3*self.borderwidth,3*self.borderwidth)
			glCallList(self.glbasicobjects.getSphereDL())
			glPopMatrix()
			
			glPushMatrix()
			glTranslate(self.width()/2.0+self.borderwidth,-self.height()/2.0-self.borderwidth,0)
			glScale(3*self.borderwidth,3*self.borderwidth,3*self.borderwidth)
			glCallList(self.glbasicobjects.getSphereDL())
			glPopMatrix()
			
			glPushMatrix()
			glTranslate(-self.width()/2.0-self.borderwidth,self.height()/2.0+self.borderwidth,0)
			glScale(3*self.borderwidth,3*self.borderwidth,3*self.borderwidth)
			glCallList(self.glbasicobjects.getSphereDL())
			glPopMatrix()
			
			glEndList()
			
		if self.frame_dl == 0:
			print "error, frame display list failed to compile"
			exit(1)
		glColor(.9,.2,.8)
		## this is a nice light blue color (when lighting is on)
		## and is the default color of the frame
		glMaterial(GL_FRONT,GL_AMBIENT_AND_DIFFUSE,(.5,.5,.5,1.0))
		glMaterial(GL_FRONT,GL_SPECULAR,(.8,.8,.8,1.0))
		glMaterial(GL_FRONT,GL_SHININESS,1.0)
		glMaterial(GL_FRONT,GL_EMISSION,(0,0,0,1))
		glDisable(GL_TEXTURE_2D)
		glEnable(GL_LIGHTING)
		glCallList(self.frame_dl)
	
	
	def draw(self):
		#print EMDesktop.main_widget.context()
		glPushMatrix()
		self.draw_frame()
		glPopMatrix()
		
		#glEnable(GL_FOG)
		glPushMatrix()
		glScalef(self.height()/2.0,self.height()/2.0,1.0)
		self.bgob2.render()
		glPopMatrix()
		#glDisable(GL_FOG)

		glPushMatrix()
		glTranslatef(0.,0.,self.get_z_opt())
		EMFrame.draw(self)
		glPopMatrix()
		
	def read_EMAN2_image(self):
		#self.p = QtGui.QPixmap("EMAN2.0.big2.jpg")
		if EMDesktopFrame.image == None:
			appscreen = self.parent.get_app_screen()
			sysdesktop = self.parent.get_sys_desktop()
			if file_exists("galactic-stars.jpg"):
				EMDesktopFrame.image = QtGui.QPixmap("galactic-stars.jpg")
			else:	EMDesktopFrame.image = QtGui.QPixmap.grabWindow(appscreen.winId(),0.0,0.0,sysdesktop.width(),sysdesktop.height()-30)
		return EMDesktopFrame.image

	def get_time(self):
		return self.parent.get_time()

	def makeCurrent(self):
		self.parent.makeCurrent()

	def bindTexture(self,pixmap):
		return self.parent.bindTexture(pixmap)
		
	def get_z_opt(self):
		return self.parent.get_z_opt()

	def get_aspect(self):
		return self.parent.get_aspect()
	
	def closeEvent(self,event):
		print "should act on close event"

class EMDesktopScreenInfo:
	"""
	A class the figures out how many screen the user has, whether or they are running a virtual desktop etc.
	 
	"""
	
	def __init__(self):
		app=QtGui.QApplication.instance()
		sys_desktop = app.desktop()
		self.__num_screens = sys_desktop.numScreens()
		print "there are this many screens", self.__num_screens
		self.__screens = [] # This will be a list of QtCore.QGeometry objects
		
		print "there are",self.__num_screens,"screen is and the primary screen is", sys_desktop.primaryScreen()
		#if sys_desktop.isVirtualDesktop() or True:
			#print "user is running a virtual desktop"
			##print "now trying to figure out the dimensions of each desktop"
		if self.__num_screens == 1:
			app_screen = sys_desktop.screen(0)
			self.__screens.append(sys_desktop.screenGeometry(app_screen))
			print self.__screens
			print "there is only one screen its dimensions are",app_screen.width(),app_screen.height()
		else:
			x=0
			y=0
			for i in range( self.__num_screens):				
				geom = self.__screens.append(sys_desktop.availableGeometry(QtCore.QPoint(x,y)))
				print "\t  printing available geometry information it is",geom.left(),geom.right(),geom.top(),geom.bottom()
				print "\t geometry starts at",geom.left(),geom.top()," and has dimensions", geom.right()-geom.left()+1,geom.bottom()-geom.top()+1
				x = geom.right()+1
				y = geom.top()
		#else:
			#print "non virtual desktops are not yet supported"

	def get_num_screens():
		return self.__num_screens
	
	def get_screens():
		return self.__screens

def print_node_hierarchy(node):
	try: children = node.get_children()
	except : children = []
	if len(children) == 0:
		print ""
	else:
		for child in children:
			print child,
			print_node_hierarchy(child)

class EMDesktop(QtOpenGL.QGLWidget,EMEventRerouter,Animator,EMGLProjectionViewMatrices):
	main_widget = None
	"""An OpenGL windowing system, which can contain other EMAN2 widgets and 3-D objects.
	"""
	application = None
	
	def get_gl_context_parent(self):
		return self
	
	def __init__(self):
		Animator.__init__(self)
		EMGLProjectionViewMatrices.__init__(self)
		EMDesktop.main_widget = self
		fmt=QtOpenGL.QGLFormat()
		fmt.setDoubleBuffer(True)
		fmt.setSampleBuffers(True)
		QtOpenGL.QGLWidget.__init__(self,fmt)

		self.application = EMDesktopApplication(self,qt_application_control=False)
		if EMDesktop.application == None:
			EMDesktop.application = self.application
		
		self.setMinimumSize(400,400)
		
		self.modules = [] # a list of all the modules that currently exist
		self.app=QtGui.QApplication.instance()
		self.sysdesktop=self.app.desktop()
		self.appscreen=self.sysdesktop.screen(self.sysdesktop.primaryScreen())
		self.frame_dl = 0 # display list of the desktop frame
		self.fov = 35
		self.resize_aware_objects = []
		
		self.setMouseTracking(True)
		
		# this float widget has half of the screen (the left)
		self.task_widget = EMDesktopTaskWidget(self)
		self.desktop_frames = [EMDesktopFrame(self)]
		self.current_desktop_frame = self.desktop_frames[0]
		self.current_desktop_frame.append_task_widget(self.task_widget)
		EMEventRerouter.__init__(self,self.current_desktop_frame)
		
		#print_node_hierarchy(self.current_desktop_frame)
		#print fw1.width(),fw1.height()
		self.glbasicobjects = EMBasicOpenGLObjects()
		self.borderwidth=10.0
		self.cam = Camera()
		
		# resize finally so that the full screen is used
		self.show()
		self.move(0,0)
		self.resize(self.appscreen.size())
		
	def get_gl_context_parent(self): return self
		
	def emit(self,*args, **kargs):
		#print "i am emitting",args,kargs
		QtGui.QWidget.emit(self,*args,**kargs)
	def enable_timer(self):
		pass
	
	def attach_gl_child(self,child,hint):
		self.current_desktop_frame.attach_gl_child(child,hint)
		
	def detach_gl_child(self,child):
		self.current_desktop_frame.detach_gl_child(child)
	
	def add_browser_frame(self):
		if not self.establish_target_frame("browse"):
			return
		
		dialog = EMBrowserDialog(self,EMDesktop.application)
		em_qt_widget = EMQtWidgetModule(dialog,EMDesktop.application)
		EMDesktop.application.show_specific(em_qt_widget)
		self.browser_settings = EMBrowserSettings(self.current_desktop_frame.display_frame,self.application)

		
	def establish_target_frame(self,type_name):
		for frame in self.desktop_frames:
			if frame.get_type() == type_name:
				self.current_desktop_frame = frame
				EMEventRerouter.set_target(self,self.current_desktop_frame)
				print "that already exists"
				print "now animate change"
				return False
	
		target_frame = None
		if self.current_desktop_frame.get_type() == None:
			target_frame = self.current_desktop_frame
		else:
			self.current_desktop_frame.detach_child(self.task_widget)
			target_frame = EMDesktopFrame(self)
			target_frame.resize_gl()
			target_frame.append_task_widget(self.task_widget)
			self.desktop_frames.append(target_frame)
			self.current_desktop_frame = target_frame
		
		EMEventRerouter.set_target(self,self.current_desktop_frame)
		
		target_frame.set_type(type_name)
		
		return True
		
	def add_selector_frame(self):
		if not self.establish_target_frame("thumb"): return
		dialog = EMSelectorDialog(self,EMDesktop.application)
		em_qt_widget = EMQtWidgetModule(dialog,EMDesktop.application)
		EMDesktop.application.show_specific(em_qt_widget)
	
	def add_boxer_frame(self):
		if not self.establish_target_frame("boxer"): return
		
		boxer = EMBoxerModule(EMDesktop.application,[ "test_box_0.mrc","test_box_1.mrc","test_box_2.mrc","test_box_3.mrc"],[],128)
		
	def get_app_screen(self):
		return self.appscreen
	
	def get_sys_desktop(self):
		return self.sysdesktop
	
	def attach_module(self,module):
		self.modules.append(module)
	
	def register_resize_aware(self,resize_aware_object):
		self.resize_aware_objects.append(resize_aware_object)
		
	def deregister_resize_aware(self,resize_aware_object):
		for i,obj in enumerate(self.resize_aware_objects):
			if obj == resize_aware_object:
				self.resize_aware_objects.pop(i)
				return
			
		print "warning, can't deregister resize aware object",resize_aware_object
	
	
	def get_aspect(self):
		return float(self.width())/float(self.height())
	
	def get_z_opt(self):
		return (1.0/tan(self.get_fov()/2.0*pi/180.0))*self.height()/2
	
	def get_fov(self):
		return self.fov
	
	def get_depth_for_height(self, height):
		return 0
		# This function returns the width and height of the renderable 
		# area at the origin of the data volume
		depth = height/(2.0*tan(self.fov/2.0*pi/180.0))
		return depth
	
	def get_render_dims_at_depth(self, depth):
		return 0
		# This function returns the width and height of the renderable 
		# area at the origin of the data volume
		height = -2*tan(self.fov/2.0*pi/180.0)*(depth)
		width = self.aspect*height
		return [width,height]
	
		
	def initializeGL(self):
		glClearColor(0,0,0,0)
		glEnable(GL_NORMALIZE)
				
		glEnable(GL_LIGHTING)
		glEnable(GL_LIGHT0)
		glEnable(GL_DEPTH_TEST)
		glLightfv(GL_LIGHT0, GL_AMBIENT, [0.1, 0.1, 0.1, 1.0])
		glLightfv(GL_LIGHT0, GL_DIFFUSE, [1.0, 1.0, 1.0, 1.0])
		glLightfv(GL_LIGHT0, GL_SPECULAR, [1.0, 1.0, 1.0, 1.0])
		glLightfv(GL_LIGHT0, GL_POSITION, [0.1,.1,1.,1.])
		#glLightf(GL_LIGHT0, GL_CONSTANT_ATTENUATION, 1.5)
		#glLightf(GL_LIGHT0, GL_LINEAR_ATTENUATION, 0.5)
		#glLightf(GL_LIGHT0, GL_QUADRATIC_ATTENUATION, .2)
		#glEnable(GL_LIGHT1)
		#glLightfv(GL_LIGHT1, GL_AMBIENT, [0.1, 0.1, 0.1, 1.0])
		#glLightfv(GL_LIGHT1, GL_DIFFUSE, [1.0, 1.0, 1.0, 1.0])
		#glLightfv(GL_LIGHT1, GL_SPECULAR, [0.1, .1, .1, 1.0])
		#glLightfv(GL_LIGHT1, GL_POSITION, [-0.1,.1,1.,1.])
		#glLightf(GL_LIGHT1, GL_SPOT_DIRECTION, 45)
		#glLightfv(GL_LIGHT1, GL_SPOT_DIRECTION, [-0.1,.1,1.,0.])
			
		glLightModeli(GL_LIGHT_MODEL_LOCAL_VIEWER,GL_TRUE)

		glEnable(GL_NORMALIZE)
		#glEnable(GL_RESCALE_NORMAL)
		
		glFogi(GL_FOG_MODE,GL_EXP)
		glFogf(GL_FOG_DENSITY,0.00035)
		glFogf(GL_FOG_START,1.0)
		glFogf(GL_FOG_END,5.0)
		glFogfv(GL_FOG_COLOR,(0,0,0,1.0))
	
		glHint(GL_PERSPECTIVE_CORRECTION_HINT, GL_NICEST)
		glHint(GL_POLYGON_SMOOTH_HINT, GL_NICEST)
		glHint(GL_TEXTURE_COMPRESSION_HINT, GL_NICEST)
		
	
	def paintGL(self):
		glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
		#print glXGetCurrentContext(),glXGetCurrentDisplay()
		
		glMatrixMode(GL_MODELVIEW)
		glLoadIdentity()
		
		glPushMatrix()
		glEnable(GL_DEPTH_TEST)
		glTexEnvf(GL_TEXTURE_ENV, GL_TEXTURE_ENV_MODE, GL_REPLACE)
		#if (self.get_time() < 0):
			#z = self.get_z_opt() + float(self.get_time())/2.0*self.get_z_opt()
			##print z
			#glTranslatef(0.,0.,-z)
		#else:
			##print -2*self.zopt+0.1
		glTranslatef(0.,0.,-2*self.get_z_opt()+0.1)
		
		self.current_desktop_frame.draw()
		glPopMatrix()
		
	def update(self): self.updateGL()

	def resizeGL(self, width, height):
		#side = min(width, height)
		glViewport(0,0,self.width(),self.height())
		glMatrixMode(GL_PROJECTION)
		glLoadIdentity()
		
		self.zNear = self.get_z_opt()
		self.zFar = 2*self.get_z_opt()
		#self.startz = self.d - 2.0*self.zwidth
		#self.endz = self.d + 2.0*self.zwidth
		
		gluPerspective(self.fov,self.get_aspect(),self.zNear-500,self.zFar)
		
		glMatrixMode(GL_MODELVIEW)
		glLoadIdentity()
		
		self.set_projection_view_update()
		
		if self.frame_dl != 0:
			glDeleteLists(self.frame_dl,1)
			self.frame_dl = 0
		
		self.current_desktop_frame.set_geometry(Region(0,0,self.width(),self.height()))
		
		for obj in self.resize_aware_objects:
			obj.resize_gl()
			
	def load_orthographic(self):
		glMatrixMode(GL_PROJECTION)
		glLoadIdentity()
		self.aspect = float(self.width())/float(self.height())
		self.xwidth = self.aspect*self.yheight
		glOrtho(-self.xwidth/2.0,self.xwidth/2.0,-self.yheight/2.0,self.yheight/2.0,self.startz,self.endz)
		glMatrixMode(GL_MODELVIEW)
		
	def load_perspective(self):
		self.aspect = float(self.width())/float(self.height())
		
		glMatrixMode(GL_PROJECTION)
		glLoadIdentity()
		if self.startz < 0: self.startz = 1
		gluPerspective(self.fov,self.aspect,self.startz,self.endz)
		glMatrixMode(GL_MODELVIEW)
		
		
	def get_near_plane_dims(self):
		height = 2.0*self.zNear * tan(self.fov/2.0*pi/180.0)
		width = self.get_aspect() * height
		return [width,height]
		
	def getStartZ(self):
		return self.zNear

class EMBrowserSettings(object):
	def __new__(cls,parent,application):
		widget = EMBrowserSettingsInspector(parent)
		widget.show()
		widget.hide()
		#widget.resize(150,150)
		#gl_view = EMQtGLView(EMDesktop.main_widget,widget)
		module = EMQtWidgetModule(widget,application)
		application.show_specific(module)
		#desktop_task_widget = EM2DGLWindow(gl_view)
		return module
	
class EMBrowserSettingsInspector(QtGui.QWidget):
	def get_desktop_hint(self):
		return "settings"
	
	def __init__(self,target) :
		QtGui.QWidget.__init__(self,None)
		self.target=target
		
		
		self.vbl = QtGui.QVBoxLayout(self)
		self.vbl.setMargin(0)
		self.vbl.setSpacing(6)
		self.vbl.setObjectName("vboxlayout")

		self.hbl = QtGui.QHBoxLayout()
		self.hbl.setMargin(0)
		self.hbl.setSpacing(6)
		self.hbl.setObjectName("hboxlayout")
		self.vbl.addLayout(self.hbl)
		
		self.row_label = QtGui.QLabel("# rows")
		self.row_label.setAlignment(Qt.AlignRight|Qt.AlignVCenter)
		self.hbl.addWidget(self.row_label)
	
		self.row_size = QtGui.QSpinBox(self)
		self.row_size.setObjectName("row_size")
		self.row_size.setRange(1,10)
		self.row_size.setValue(int(self.target.num_rows()))
		QtCore.QObject.connect(self.row_size, QtCore.SIGNAL("valueChanged(int)"), target.set_num_rows)
		self.hbl.addWidget(self.row_size)
		
		
		self.hbl3 = QtGui.QHBoxLayout()
		self.hbl3.setMargin(0)
		self.hbl3.setSpacing(6)
		self.hbl3.setObjectName("hboxlayout3")
		self.vbl.addLayout(self.hbl3)
		
		self.col_label = QtGui.QLabel("# cols")
		self.col_label.setAlignment(Qt.AlignRight|Qt.AlignVCenter)
		self.hbl3.addWidget(self.col_label)
	
		self.col_size = QtGui.QSpinBox(self)
		self.col_size.setObjectName("col_size")
		self.col_size.setRange(1,10)
		self.col_size.setValue(int(self.target.num_cols()))
		QtCore.QObject.connect(self.col_size, QtCore.SIGNAL("valueChanged(int)"), target.set_num_cols)
		self.hbl3.addWidget(self.col_size)
		
		#self.hbl2 = QtGui.QHBoxLayout()
		#self.hbl2.setMargin(0)
		#self.hbl2.setSpacing(6)
		#self.hbl2.setObjectName("hboxlayout2")
		#self.vbl.addLayout(self.hbl2)
		
		self.apply_button = QtGui.QPushButton("apply")
		self.vbl.addWidget(self.apply_button)
		
		self.clear_button = QtGui.QPushButton("clear")
		self.vbl.addWidget(self.clear_button)
		
		self.show_grid = QtGui.QCheckBox("show grid")
		self.show_grid.setChecked(True)
		self.vbl.addWidget(self.show_grid)

		QtCore.QObject.connect(self.apply_button, QtCore.SIGNAL("clicked(bool)"), target.apply_row_col)
		QtCore.QObject.connect(self.clear_button, QtCore.SIGNAL("clicked(bool)"), target.clear_all)
		QtCore.QObject.connect(self.show_grid, QtCore.SIGNAL("toggled(bool)"), target.show_grid)
		
class EMDesktopTaskWidget(EMGLViewContainer):
	def __init__(self, parent):
		#print "init"
		EMGLViewContainer.__init__(self,parent)
		self.parent = parent
	
		self.init_flag = True
		
		self.desktop_task_widget = None
	
		self.glwidget = None
		self.widget = None
		
		self.animation = None
	
	def get_qt_context_parent(self):
		return EMDesktop.main_widget
	
	def get_gl_context_parent(self):
		return EMDesktop.main_widget

	def get_depth_for_height(self, height):
		try: 
			return EMDesktop.main_widget.get_depth_for_height(height)
		except:
			print "parent can't get height for depth"
			exit(1)
			#return 0
			
	def height(self):
		if self.desktop_task_widget != None: return self.desktop_task_widget.height() 
		return 0
		
	def width(self):
		if self.desktop_task_widget != None: return self.desktop_task_widget.width() 
		return 0
	
	def height_inc_border(self):
		if self.desktop_task_widget != None: return self.desktop_task_widget.height_inc_border() 
		return 0
		
	def width_inc_border(self):
		if self.desktop_task_widget != None: return self.desktop_task_widget.width_inc_border() 
		return 0
	
	def updateGL(self):
		try: self.parent.updateGL()
		except: pass
	
	def lock_texture(self):
		self.desktop_task_widget.lock_texture()
		
	def unlock_texture(self):
		self.desktop_task_widget.unlock_texture()
	
	def draw(self):
		if ( self.init_flag == True ):
			
			#gl_view.setQtWidget(self.qt_widget)
			
			#self.desktop_task_widget = EMGLViewQtWidget(EMDesktop.main_widget)
			self.widget = EMDesktopTaskWidget.EMDesktopTaskInspector(self)
			self.widget.show()
			self.widget.hide()
			self.widget.resize(150,150)
			gl_view = EMQtGLView(EMDesktop.main_widget,self.widget)
			self.desktop_task_widget = EM2DGLWindow(self,gl_view)
			
			
			self.init_flag = False
			self.attach_child(self.desktop_task_widget)
			#self.parent.i_initialized(self)
	
		for child in self.children:
			glPushMatrix()
			child.draw()
			glPopMatrix()
			
	def bindTexture(self,pixmap):
		return EMDesktop.main_widget.bindTexture(pixmap)
	
	def deleteTexture(self,val):
		return EMDesktop.main_widget.deleteTexture(val)
	
	def get_render_dims_at_depth(self, depth):
		try: return EMDesktop.main_widget.get_render_dims_at_depth(depth)
		except:
			print "parent can't get render dims at for depth"
			return

	def close(self):
		pass

	def add_browser(self):
		self.parent.add_browser_frame()
		
	def add_selector(self):
		self.parent.add_selector_frame()
		
	def add_boxer(self):
		self.parent.add_boxer_frame()

	class EMDesktopTaskInspector(QtGui.QWidget):
		def __init__(self,target) :
			QtGui.QWidget.__init__(self,None)
			self.target=target
			
			
			self.vbl = QtGui.QVBoxLayout(self)
			self.vbl.setMargin(0)
			self.vbl.setSpacing(6)
			self.vbl.setObjectName("vbl")
			
			self.hbl_buttons2 = QtGui.QHBoxLayout()
			
			self.tree_widget = QtGui.QTreeWidget(self)
			self.tree_widget_entries = []
			self.tree_widget_entries.append(QtGui.QTreeWidgetItem(QtCore.QStringList("Browse")))
			#self.tree_widget_entries.append(QtGui.QTreeWidgetItem(QtCore.QStringList("Thumb")))
			#self.tree_widget_entries.append(QtGui.QTreeWidgetItem(QtCore.QStringList("Box")))
			self.tree_widget.insertTopLevelItems(0,self.tree_widget_entries)
			self.tree_widget.setHeaderLabel("Choose a task")
			
			self.hbl_buttons2.addWidget(self.tree_widget)
			
			self.close = QtGui.QPushButton("Close")
			
			self.vbl.addLayout(self.hbl_buttons2)
			self.vbl.addWidget(self.close)
			
			QtCore.QObject.connect(self.tree_widget, QtCore.SIGNAL("itemDoubleClicked(QTreeWidgetItem*,int)"), self.tree_widget_double_click)
			QtCore.QObject.connect(self.close, QtCore.SIGNAL("clicked()"), self.target.close)
			
		def tree_widget_double_click(self,tree_item,i):
			task = tree_item.text(0)
			if task == "Browse":
				self.target.add_browser()
			if task == "Thumb":
				self.target.add_selector()
			elif task == "Box":
				self.target.add_boxer()
		
class ob2dimage:
	def __init__(self,target,pixmap):
		self.pixmap=pixmap
		self.target=target
		self.target.makeCurrent()
		self.texture_dl = 0
		self.itex=self.target.bindTexture(self.pixmap)
		self.refresh_flag = False
		
	def __del__(self):
		if self.texture_dl != 0: 
			glDeleteLists(self.texture_dl,1)
			self.texture_dl = 0
			
	def refresh(self):
		self.refresh_flag = True

	def __del__(self):
		target.deleteTexture(self.itex)

	def setWidget(self,widget,region=None):
		return

	def update(self):
		return
	
	def width(self):
		return self.pixmap.width()
	
	def height(self):
		return self.pixmap.height()
	
	def asp(self):
		return (1.0*self.width())/self.height()
	
	def render2(self):
		if not self.pixmap : return
		glPushMatrix()
		glScalef(self.pixmap.width()/2.0,self.pixmap.height()/2.0,1.0)
		glColor(1.0,1.0,1.0)
		glEnable(GL_TEXTURE_2D)
		glTexEnvf(GL_TEXTURE_ENV, GL_TEXTURE_ENV_MODE, GL_REPLACE)
		glBindTexture(GL_TEXTURE_2D,self.itex)
		glBegin(GL_QUADS)
		glTexCoord2f(0.,0.)
		glVertex(-1.0,-1.0)
		glTexCoord2f(.999,0.)
		glVertex( 1.0,-1.0)
		glTexCoord2f(.999,0.999)
		glVertex( 1.0, 1.0)
		glTexCoord2f(0.,.999)
		glVertex(-1.0, 1.0)
		glEnd()
		glPopMatrix()
		glDisable(GL_TEXTURE_2D)
	
	def render(self):
		if not self.pixmap : return
		if self.texture_dl == 0 or self.refresh_flag:
			if self.texture_dl != 0:
				glDeleteLists(self.texture_dl,1)
				self.texture_dl = 0
			
			self.texture_dl=glGenLists(1)
			
			if self.texture_dl == 0:
				return
			
			glNewList(self.texture_dl,GL_COMPILE)
	
			glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP)
			glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP)
			glTexEnvf(GL_TEXTURE_ENV, GL_TEXTURE_ENV_MODE, GL_REPLACE)
			glColor(1.0,1.0,1.0)
			glEnable(GL_TEXTURE_2D)
			glBindTexture(GL_TEXTURE_2D,self.itex)
			glBegin(GL_QUADS)
			glTexCoord2f(0.,0.)
			glVertex(-self.target.get_aspect(),-1.0)
			glTexCoord2f(.999,0.)
			glVertex( self.target.get_aspect(),-1.0)
			glTexCoord2f(.999,0.999)
			glVertex( self.target.get_aspect(), 1.0)
			glTexCoord2f(0.,.999)
			glVertex(-self.target.get_aspect(), 1.0)
			glEnd()
			glDisable(GL_TEXTURE_2D)
			glEndList()
		
		if self.texture_dl != 0: glCallList(self.texture_dl)
		#glPopMatrix()


class SideWidgetBar(EMGLViewContainer):
	def __init__(self,parent):
		EMGLViewContainer.__init__(self,parent)
		self.mouse_on = None
		self.previous_mouse_on = None
		self.active = None
		self.transformers = []
		
		EMDesktop.main_widget.register_resize_aware(self)
		
		self.browser_module = None
		
	def __del__(self):
		try: EMDesktop.main_widget.deregister_resize_aware(self)
		except: pass # this might happen at program
		
	def width(self):
		width = 0
		for child in self.children:
			if child.width_inc_border() > width:
				width = width
		
		return width
		
	def height(self):
		return EMDesktop.main_widget.viewport_height()
	
	
	
	def seed_scale_animation(self,i):
		t = self.transformers[i]
		if t.get_xy_scale() != 1.0:
			#if i == 0:
			seed_height = self.children[i].height_inc_border()
			below_height = 0
			for j in range(0,len(self.children)):
				if j != i: below_height += self.children[j].height_inc_border()
			
			
			to_height = EMDesktop.main_widget.viewport_height()-seed_height
			below_scale = to_height/float(below_height)
			
			if below_scale > 1.0: below_scale = 1.0
			
			#print "seed a scale event for ", i
			t.seed_scale_animation_event(1.0)
			for j in range(0,len(self.transformers)):
				if j != i: 
					#print "seed a scale event for ", j
					self.transformers[j].seed_scale_animation_event(below_scale)
					
	def resize_gl(self):
		self.reset_scale_animation()

	def reset_scale_animation(self):
		children_height = 0
		for child in self.children:
			children_height += child.height_inc_border()
			
		if children_height > EMDesktop.main_widget.viewport_height():
			scale = EMDesktop.main_widget.viewport_height()/float(children_height)
		else: scale = 1.0
		
		for t in self.transformers: 
			#print "resetting scale event for ", i
			#i += 1
			t.seed_scale_animation_event(scale)
			
	def mouseMoveEvent(self, event):
		intercept = False
		for i,child in enumerate(self.children):
			if ( child.isinwin(event.x(),EMDesktop.main_widget.viewport_height()-event.y()) ):
				#if self.animations[i] == None:
				intercept = True
				self.previous_mouse_on = self.mouse_on
				self.mouse_on = i
				self.active = i
				if self.transformers[i].is_animatable():
					t = self.transformers[i]
					#print "mouse entered a window"
					#print "seed a rotation event for ", i
					t.seed_rotation_animation_event(force_active=True)
					self.seed_scale_animation(i)
				
				if self.previous_mouse_on != None and self.previous_mouse_on != self.mouse_on:
					#print "mouse left a window and left another"
					t = self.transformers[self.previous_mouse_on]
					t.seed_rotation_animation_event(force_inactive=True)
					self.previous_mouse_on = None
				
				break
		
		
		
		if not intercept:
			if self.mouse_on != None:
				#print "moust left a window"
				t = self.transformers[self.mouse_on]
				t.seed_rotation_animation_event(force_inactive=True)
				self.mouse_on = None
				self.previous_mouse_on = None
				self.active = None
				self.reset_scale_animation()
				EMDesktop.main_widget.unlock_target()
		else:
			EMDesktop.main_widget.lock_target(self)
				
		return EMGLViewContainer.mouseMoveEvent(self,event) or intercept

	def detach_child(self,new_child):
		for i,child in enumerate(self.children):
			if (child == new_child):
				self.children.pop(i)
				self.transformers.pop(i)
				#self.reset_scale_animation()
				return
			
		print "error, attempt to detach a child that didn't belong to this parent"

class SideTransform:
	ACTIVE = 0
	INACTIVE = 1
	ANIMATED = 2
	def __init__(self,child):
		self.child = child
		self.rotation_animation = None
		self.scale_animation = None
		self.state = SideTransform.INACTIVE
		self.xy_scale = 1.0
		
		self.rotation = 0 # supply these yourself, probably
		self.default_rotation = 0 # supply these yourself, probably
		self.target_rotation = 0.0
	def __del__(self):
		if self.scale_animation != None:
			self.scale_animation.set_animated(False) # this will cause the EMDesktop to stop animating
			self.scale_animation = None
		
		if self.rotation_animation != None:
			self.rotation_animation.set_animated(False) # this will cause the EMDesktop to stop animating
			self.rotation_animation = None
	
	def animation_done_event(self,child):
		#print "del side transform"
		self.child.unlock_texture()

	def get_xy_scale(self):
		return self.xy_scale
	
	def set_xy_scale(self,xy_scale):
		self.xy_scale = xy_scale
	
	def set_rotation(self,rotation):
		self.rotation = rotation
	
	def seed_scale_animation_event(self,scale):
		if self.xy_scale == scale: return
		
		if self.scale_animation != None:
			self.scale_animation.set_animated(False) # this will cause the EMDesktop to stop animating
			self.scale_animation = None
		
		animation = XYScaleAnimation(self,self.xy_scale,scale)
		self.scale_animation = animation
		EMDesktop.main_widget.register_animatable(animation)
		self.child.lock_texture()
		
	def seed_rotation_animation_event(self,force_inactive=False,force_active=False):
		
		if self.state == SideTransform.ACTIVE:
			rot = [self.target_rotation,self.default_rotation]
		elif self.state == SideTransform.ANIMATED:
			c = self.rotation
			s = self.rotation_animation.get_start()
			if c < s: s = self.default_rotation
			elif c > s: s = self.target_rotation
			#else: print "I'm a bad programmer",c,s
			if force_inactive: s = self.default_rotation
			if force_active: s = self.target_rotation
			rot =  [c,s]
		elif self.state == SideTransform.INACTIVE:
			rot = [self.default_rotation,self.target_rotation]
			
		if self.rotation_animation != None:
			self.rotation_animation.set_animated(False) # this will cause the EMDesktop to stop animating
			self.rotation_animation = None

		
		#print "adding animation",rot
		animation = SingleAxisRotationAnimation(self,rot[0],rot[1],[0,1,0])
		self.rotation_animation = animation
		self.state =  SideTransform.ANIMATED
		EMDesktop.main_widget.register_animatable(animation)
		self.child.lock_texture()
		
	def is_animatable(self):
		if self.rotation_animation != None: return not self.rotation_animation.is_animated()
		elif self.state == SideTransform.ACTIVE:
			return False
		else: return True

	def transform(self):
		if self.rotation_animation != None and not self.rotation_animation.is_animated():
			end = self.rotation_animation.get_end()
			self.rotation_animation = None
			if end == self.target_rotation :
				self.state = SideTransform.ACTIVE
				self.rotation = self.target_rotation
			elif end == self.default_rotation:
				self.state = SideTransform.INACTIVE
		
		if self.scale_animation != None and not self.scale_animation.is_animated():
			self.scale_animation.set_animated(False) # this will cause the EMDesktop to stop animating
			self.scale_animation = None
		
		if self.rotation_animation == None:
			if self.rotation != self.default_rotation and self.rotation != self.target_rotation:
				self.rotation = self.default_rotation
		
	def draw(self):
		
		glPushMatrix()
		self.transform()
		self.child.draw()
		glPopMatrix()
		glTranslate(0,-self.xy_scale*self.child.height_inc_border(),0)


class BottomWidgetBar(SideWidgetBar):
	def __init__(self,parent):
		SideWidgetBar.__init__(self,parent)
		
	def draw(self):
		if len(self.children) != 1 : 
			#print len(self.children)
			return
		child = self.children[0]
		glPushMatrix()
		
		glTranslate(-child.width_inc_border()/2,-self.parent.height()/2.0+6,0)
		self.transformers[0].transform()
		child.draw()
		glPopMatrix()
		
	def attach_child(self,new_child):
		#print "attached child"
		self.transforms = []
		self.children = []
		self.transformers.append(BottomWidgetBar.BottomTransform(new_child))
		EMWindowNode.attach_child(self,new_child)
		self.reset_scale_animation()
		#print len(self.children)
		#print_node_hierarchy(self.parent)

	class BottomTransform(SideTransform):
		def __init__(self,child):
			SideTransform.__init__(self,child)
			self.rotation = -90
			self.default_rotation = -90
			self.target_rotation = 0
			
		def transform(self):
			SideTransform.transform(self)
			glRotate(self.rotation,1,0,0)
			
class RightSideWidgetBar(SideWidgetBar):
	def __init__(self,parent):
		SideWidgetBar.__init__(self,parent)
		
	
	def draw(self):
		glPushMatrix()
		glTranslate(self.parent.width()/2.0,self.parent.height()/2.0,0)
		for i,child in enumerate(self.children):
			glPushMatrix()
			self.transformers[i].transform()
			child.draw()
			glPopMatrix()
			#print child.height_inc_border(), child
			glTranslate(0,-self.transformers[i].get_xy_scale()*child.height_inc_border(),0)

		glPopMatrix()
		
	def attach_child(self,new_child):
		self.transformers.append(RightSideWidgetBar.RightSideTransform(new_child))
		EMWindowNode.attach_child(self,new_child)
		self.reset_scale_animation()
		#print_node_hierarchy(self.parent)

	class RightSideTransform(SideTransform):
		def __init__(self,child):
			SideTransform.__init__(self,child)
			self.rotation = -90
			self.default_rotation = -90
			self.target_rotation = 0
			
		def transform(self):
			SideTransform.transform(self)
			
			glTranslate(0,-self.xy_scale*self.child.height_inc_border(),0)
			glRotate(self.rotation,0,1,0)
			glTranslate(-self.xy_scale*self.child.width_inc_border(),0,0)
			glScale(self.xy_scale,self.xy_scale,1.0)
		
	

class LeftSideWidgetBar(SideWidgetBar):
	def __init__(self,parent):
		SideWidgetBar.__init__(self,parent)

	def draw(self):
		glPushMatrix()
		glTranslate(-self.parent.width()/2.0+6,self.parent.height()/2.0,0)
		for i,child in enumerate(self.children):
			glPushMatrix()
			self.transformers[i].transform()
			child.draw()
			glPopMatrix()
			glTranslate(0,-self.transformers[i].get_xy_scale()*child.height_inc_border(),0)

		glPopMatrix()
		
	def attach_child(self,new_child):
		self.transformers.append(LeftSideWidgetBar.LeftSideTransform(new_child))
		EMWindowNode.attach_child(self,new_child)
		self.reset_scale_animation()
		#print_node_hierarchy(self.parent)
		
	class LeftSideTransform(SideTransform):
		def __init__(self,child):
			SideTransform.__init__(self,child)
			self.rotation = 90
			self.default_rotation = 90

		def transform(self):
			SideTransform.transform(self)
			
			glTranslate(0,-self.xy_scale*self.child.height_inc_border(),0)
			glRotate(self.rotation,0,1,0)
			#glTranslate(self.xy_scale*self.child.width_inc_border()/2.0,0,0)
			glScale(self.xy_scale,self.xy_scale,1.0)

	
	

			
if __name__ == '__main__':
	app = QtGui.QApplication(sys.argv)
	window = EMDesktop()
#	window.showFullScreen()
	window.app.exec_()
