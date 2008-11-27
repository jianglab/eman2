#!/usr/bin/env python
#
# Author: David Woolford 11/10/08 (woolford@bcm.edu)
# Copyright (c) 2000-2008 Baylor College of Medicine
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
#

from emform import EMFormModule,ParamTable
from emdatastorage import ParamDef
from PyQt4 import QtGui,QtCore
from EMAN2db import db_check_dict, db_open_dict,db_remove_dict,db_list_dicts,db_close_dict
from EMAN2 import EMData,get_file_tag,EMAN2Ctf,num_cpus,memory_stats,check_files_are_2d_images,check_files_are_em_images
import os
import copy
from emapplication import EMProgressDialogModule
from e2boxer import EMBoxerModule
from e2ctf import pspec_and_ctf_fit,GUIctfModule,write_e2ctf_output,get_gui_arg_img_sets
import subprocess
from pyemtbx.boxertools import set_idd_image_entry, TrimBox
import weakref

class EmptyObject:
	'''
	This just because I need an object I can assign attributes to, and object() doesn't seem to work
	'''
	def __init__(self):
		pass
	
	

class WorkFlowTask(QtCore.QObject):
	def __init__(self,application):
		QtCore.QObject.__init__(self)
		self.application = weakref.ref(application)
		self.window_title = "Set me please"
		self.preferred_size = (480,640)
	
	def run_form(self):
		self.form = EMFormModule(self.get_params(),self.application())
		self.form.qt_widget.resize(*self.preferred_size)
		self.form.setWindowTitle(self.window_title)
		self.application().show_specific(self.form)
		QtCore.QObject.connect(self.form,QtCore.SIGNAL("emform_ok"),self.on_form_ok)
		QtCore.QObject.connect(self.form,QtCore.SIGNAL("emform_cancel"),self.on_form_cancel)
		QtCore.QObject.connect(self.form,QtCore.SIGNAL("emform_close"),self.on_form_close)
		
	def on_form_ok(self,params):
		for k,v in params.items():
			self.write_db_entry(k,v)
			
		self.application().close_specific(self.form)
		self.form = None
	
		self.emit(QtCore.SIGNAL("task_idle"))
		
	def on_form_cancel(self):
		self.application().close_specific(self.form)
		self.form = None

		self.emit(QtCore.SIGNAL("task_idle"))
	
	def on_form_close(self):
		self.emit(QtCore.SIGNAL("task_idle"))

	def closeEvent(self,event):
		self.application().close_specific(self.form)
		#self.emit(QtCore.SIGNAL("task_idle")
		
	def write_db_entry(self,key,value):
		'''
		Call this function if you need to
		'''
		db = db_open_dict("bdb:project")
		if key == "global.apix":
			db["global.apix"] = value
		elif key == "global.microscope_voltage":
			db["global.microscope_voltage"] = value
		elif key == "global.microscope_cs":
			db["global.microscope_cs"] = value
		elif key == "global.memory_available":
			#mem = memory_stats()
			#if value > mem[0]:
				#print "error, memory usage is beyond the total amount available"
			#else:
			# we're avoiding validation because users have peculiar reasons some times
			db["global.memory_available"] = value
		elif key == "global.num_cpus":
			#n = num_cpus()
			#if value > n:
				#print "error, num_cpus more than the available cpus"
			#else:
			#  we're avoiding validation because users have peculiar reasons some times
			db["global.num_cpus"] = value
		else:
			pass
		
		db_close_dict("bdb:project")
	def get_wd(self):
		'''
		Get the working directory, originally introduced to provide a centralized mechanism for accessing the working directory,
		specificially for the purpose of spawning processes. Could be used more generally, however.
		'''
		return os.getcwd()

	def run_task(self,program,options,string_args,bool_args,additional_args=[],temp_file_name="e2workflow_tmp.txt"):
		'''
		splits the task over the available processors
		example-
		program="e2ctf.py"
		options is an object with the filenames, all string args and all bool_args as attributes 
		string_args=["
		bool_args=["
		additional_args=["--auto_db,--auto_fit"]
		temp_file_name = "etctf_auto_tmp.txt"
		'''
		project_db = db_open_dict("bdb:project")
		ncpu = project_db.get("global.num_cpus",dfl=num_cpus())
		cf = float(len(options.filenames))/float(ncpu) # common factor
		for n in range(ncpu):
			b = int(n*cf)
			t = int(n+1*cf)
			if n == (ncpu-1):
				t = len(options.filenames) # just make sure of it, round off error could 
			
			if b == t:
				continue # it's okay this happens when there are more cpus than there are filenames	
			filenames = options.filenames[b:t]
								
			args = [program]
	
			for name in filenames:
				args.append(name)
			
			for string in string_args:
				args.append("--"+string+"="+str(getattr(options,string)))

			# okay the user can't currently change these, but in future the option might be there
			for string in bool_args:
				# these are all booleans so the following works:
				if getattr(options,string):
					args.append("--"+string)
					
			for arg in additional_args:
				args.append(arg)
			#print "command is ",program
			#for i in args: print i
			
			#print args
			file = open(temp_file_name,"w+")
			process = subprocess.Popen(args,stdout=file,stderr=subprocess.STDOUT)
			print "started process",process.pid
			self.emit(QtCore.SIGNAL("process_started"),process.pid)
			
		db_close_dict("bdb:project")

class ParticleWorkFlowTask(WorkFlowTask):
	'''
	Enncapsulates some functionality  common to the particle based work flow tasks
	Such task should inherit from this class, not the the WorkFlowTask
	'''
	def __init__(self,application):
		WorkFlowTask.__init__(self,application)
		
	def get_particle_db_names(self,strip_ptcls=True):
		'''
		returns a list of particle databases in the project
		for instance if these dbs files exist in the particle bdb directory:
		image_001_ptcls.bdb
		image_1000_a_ptcls.bdb
		image_001_ctf.bdbs
		then this function will return [ image_001, image_1000_a]
		Note the if strip_ptcls is False then the return list would instead be [ image_001_ptcls, image_1000_a_ptcls]
		If there are no such dbs then an empty list is returned
		'''
		if os.path.exists("particles/EMAN2DB"):
			dbs = db_list_dicts("bdb:particles#")
			ptcl_dbs = []
			for db in dbs:
				db_strip = get_file_tag(db)
				if len(db_strip) > 5:
					if db_strip[-6:] == "_ptcls":
						if strip_ptcls:
							ptcl_dbs.append(db_strip[:-6])
						else:
							ptcl_dbs.append(db_strip)
			return ptcl_dbs
		else: return []

	def get_particle_and_project_names(self):
		'''
		
		'''
		ptcl_dbs = self.get_particle_db_names()
		
		project_db = db_open_dict("bdb:project")
		project_files = project_db.get("global.micrograph_ccd_filenames",dfl=[])
		for name in project_files:
			stripped = get_file_tag(name)
			if stripped not in ptcl_dbs:
				ptcl_dbs.append(stripped)
		db_close_dict("bdb:project")
		return ptcl_dbs
	
	def get_num_particles(self,project_files_names):
		ptcl_dbs = self.get_particle_db_names()
		vals = []
		for name in project_files_names:
			name_strip = get_file_tag(name)
			if name_strip in ptcl_dbs:
				db_name = "bdb:particles#"+name_strip+"_ptcls"
				if db_check_dict(db_name):
					db = db_open_dict(db_name)
					vals.append(db["maxrec"]+1)
					db_close_dict(db_name)
				else:
					vals.append("")
			else:
				vals.append("")
		return vals
	
	def get_particle_dims(self,particle_file_names):
		if not os.path.exists("particles/EMAN2DB"):
			vals = [ "" for i in range(len(particle_file_names))]
			return vals
		else:
			vals = []
			for name in particle_file_names:
				name_strip = get_file_tag(name)
				db_name = "bdb:particles#"+name_strip+"_ptcls"
				if db_check_dict(db_name):
					db = db_open_dict(db_name)
					hdr = db.get_header(0)
					vals.append(str(hdr["nx"])+'x'+str(hdr["ny"])+'x'+str(hdr["nz"]))
					db_close_dict(db_name)
				else: vals.append("")
			return vals
		
	def get_particle_dims_direct(self,file_names):
		'''
		Iterates through the given names opening the bdb:particles#name
		and returning the dimensions as string e.g. 128x128x1, in a list
		You can use this function if the file_names are exactly those that exist in the particles BDB
		otherwise use get_particle_dims
		'''
		vals = []
		for name in file_names:
			db_name = "bdb:particles#"+name
			if db_check_dict(db_name):
				db = db_open_dict(db_name)
				hdr = db.get_header(0)
				vals.append(str(hdr["nx"])+'x'+str(hdr["ny"])+'x'+str(hdr["nz"]))
				db_close_dict(db_name)
			else: vals.append("No data")
		return vals

	def get_num_particles_direct(self,file_names):
		'''
		Iterates through the given names opening the bdb:particles#name
		and returning the number of particles in each db, in a list. If for some reason the dictionary doesn't exist will
		return a -1 in the list instead
		You can use this function if the file_names are exactly those that exist in the particles BDB
		otherwise use get_num_particles
		'''
		vals = []
		for name in file_names:
			db_name = "bdb:particles#"+name
			if db_check_dict(db_name):
				db = db_open_dict(db_name)
				vals.append(db["maxrec"]+1)
				db_close_dict(db_name)
			else:
				vals.append(-1)
		return vals

	def get_project_particle_param_table(self):
		'''
		Use the names in the global.micrograph_ccd_filenames to build a table showing the corresponding and  current number of boxed particles in the particles directory, and also lists their dimensions
		Puts the information in a ParamTable.
		'''
		project_db = db_open_dict("bdb:project")	
		particle_file_names = project_db.get("global.micrograph_ccd_filenames",dfl=[])
		
		return self.__make_particle_param_table(particle_file_names)
	
	def pet_particle_param_table(self):
		'''
		Inspects the particle databases in the particles directory, gathering their names, number of particles and dimenions. Puts the information in a ParamTable.
		'''
		particle_file_names = self.get_particle_db_names(strip_ptcls=True)
		
		return self.__make_particle_param_table(particle_file_names)
	
	def __make_particle_param_table(self,particle_file_names):
		'''
		Functionality used in two places (directly above)
		'''
		
		num_boxes = self.get_num_particles(particle_file_names)
		dimensions = self.get_particle_dims(particle_file_names)
		
		pnames = ParamDef(name="global.micrograph_ccd_filenames",vartype="stringlist",desc_short="File names",desc_long="The raw data from which particles will be extracted and ultimately refined to produce a reconstruction",property=None,defaultunits=None,choices=particle_file_names)
		pboxes = ParamDef(name="Num boxes",vartype="intlist",desc_short="Particles",desc_long="The number of box images stored for this image in the database",property=None,defaultunits=None,choices=num_boxes)
		pdims = ParamDef(name="Dimensions",vartype="stringlist",desc_short="Dimensions",desc_long="The dimensions of the particle images",property=None,defaultunits=None,choices=dimensions)
		
		p = ParamTable(name="filenames",desc_short="Choose images to box",desc_long="")
		p.append(pnames)
		p.append(pboxes)
		p.append(pdims)
		
		return p
		

class ParticleReportTask(ParticleWorkFlowTask):
	
	documentation_string = "This tool is for displaying the particles that are currently associated with this project. You can add particles to the project by importing them or by using e2boxer."
	
	def __init__(self,application):
		ParticleWorkFlowTask.__init__(self,application)
		self.window_title = "Project particles"

	def get_params(self):
		params = []
		
		params.append(ParamDef(name="blurb",vartype="text",desc_short="",desc_long="",property=None,defaultunits=ParticleReportTask.documentation_string,choices=None))
		
	   	p = self.pet_particle_param_table()
		params.append(p)  
		
		return params


class ParticleImportTask(ParticleWorkFlowTask):	
	documentation_string = "Use this tool for importing particle images into the particle directory in the project database. Files that you import in this way will be automatically added the list of particle files in the project."
	
	def __init__(self,application):
		ParticleWorkFlowTask.__init__(self,application)
		self.window_title = "Import particles"

	def get_params(self):
		params = []
		project_db = db_open_dict("bdb:project")
		params.append(ParamDef(name="blurb",vartype="text",desc_short="Description",desc_long="",property=None,defaultunits=ParticleImportTask.documentation_string,choices=None))
		params.append(ParamDef(name="import_particle_files",vartype="url",desc_short="Imported particles",desc_long="A list of particle files that have been or will be imported into this project",property=None,defaultunits=[],choices=[]))
		db_close_dict("bdb:project")
		return params


	def write_db_entry(self,k,v):
		if k == "import_particle_files":
			# first make sure that the file tags that will correspond to the imported file names do not conflict with names in the project files
			project_db = db_open_dict("bdb:project")
			project_file_names = project_db.get("global.micrograph_ccd_filenames",dfl=[])
			pfnt = [ get_file_tag(name) for name in project_file_names]
			
			for name in v:
				if get_file_tag(name) in pfnt:
					print "error, you can't import particles that have the same file name as one of the project files - the problem is with:",get_file_tag(name)
					db_close_dict("bdb:project")
					return
			# now check to see if there are duplicated filetags in the incoming list
			# Actually the url form widget may have already dealt with this?
			nt = [ get_file_tag(name) for name in v]
			for name in v:
				if nt.count(get_file_tag(name)) > 1:
					print "error, you can't import particles that have the same file names! The problem is with:",get_file_tag(name)
					db_close_dict("bdb:project")
					return
			
			# now check to see if there isn't already an entry in the particle directory that corresponds to this name
			particle_dbs = self.get_particle_db_names()
			for name in v:
				if get_file_tag(name) in particle_dbs:
					print "error, you can't import particles that already have entries in the particle database! The problem is with:",get_file_tag(name)
					db_close_dict("bdb:project")
					return
			# okay if we make it here we're fine, import that particles
			progress = EMProgressDialogModule(self.application(),"Importing files into database...", "Abort import", 0, len(v),None)
			progress.qt_widget.show()
#			self.application().show_specific(progress)
			read_header_only = True
			a= EMData()
			cancelled_dbs = []
			for i,name in enumerate(v):
				progress.qt_widget.setValue(i)
				self.application().processEvents()
				if os.path.exists(name) or db_check_dict(name):
					
					try:
						a.read_image(name,0,read_header_only)
					except:
						print "error,",name,"is not a valid image. Ignoring"
						continue
					
					tag = get_file_tag(name)
					db_name = "bdb:particles#"+tag+"_ptcls"
					imgs = EMData().read_images(name)
					cancelled_dbs.append(db_name)
					for img in imgs: img.write_image(db_name,-1)
				else:
					print "error,",name,"doesn't exist. Ignoring"
					
				if progress.qt_widget.wasCanceled():
					cancelled = True
					for db_name in cancelled_dbs:
						db_remove_dict(db_name)
					break
			
					
			progress.qt_widget.setValue(len(v))
			#self.application().close_specific(progress)
			progress.qt_widget.close()
				
			
			db_close_dict("bdb:project")

class E2BoxerTask(ParticleWorkFlowTask):
	'''
	Provides some common functions for the e2boxer tasks
	'''
	def __init__(self,application):
		ParticleWorkFlowTask.__init__(self,application)
		
	def get_e2boxer_boxes_and_project_particles_table(self):
		
		p = self.get_project_particle_param_table() # now p is a ParamTable with rows for as many files as there in the project
		# also, p contains columns with filename | particle number | particle dimensions
		 
		project_db = db_open_dict("bdb:project")	
		project_names = project_db.get("global.micrograph_ccd_filenames",dfl=[])
		
		
		nboxes,dimensions = self.__get_e2boxer_data(project_names)
		pboxes = ParamDef(name="Num boxes",vartype="intlist",desc_short="Boxes in DB",desc_long="The number of boxes stored for this image in the database",property=None,defaultunits=None,choices=nboxes)
		pdims = ParamDef(name="DB Box Dims",vartype="stringlist",desc_short="Dims in DB",desc_long="The dimensions boxes",property=None,defaultunits=None,choices=dimensions)
		
		p.append(pboxes)
		p.append(pdims)
		return p
	
	def get_project_files_that_have_db_boxes_in_table(self):
		project_db = db_open_dict("bdb:project")	
		project_names = project_db.get("global.micrograph_ccd_filenames",dfl=[])
		
		flat_boxes = self.get_num_particles(project_names)
		flat_dims = self.get_particle_dims(project_names)
		
		
		db_boxes,db_dims = self.__get_e2boxer_data(project_names)
		
		
		
		for i in range(len(db_dims)-1,-1,-1):
			if db_boxes[i] == "":
				for data in [project_names,flat_boxes,flat_dims,db_boxes,db_dims]:
					data.pop(i)
		
		
		pnames = ParamDef(name="global.micrograph_ccd_filenames",vartype="stringlist",desc_short="File names",desc_long="The raw data from which particles will be extracted and ultimately refined to produce a reconstruction",property=None,defaultunits=None,choices=project_names)
		pboxes = ParamDef(name="Num boxes",vartype="intlist",desc_short="Particles",desc_long="The number of box images stored for this image in the database",property=None,defaultunits=None,choices=flat_boxes)
		pdims = ParamDef(name="Dimensions",vartype="stringlist",desc_short="Dimensions",desc_long="The dimensions of the particle images",property=None,defaultunits=None,choices=flat_dims)
		pdbboxes = ParamDef(name="Num boxes",vartype="intlist",desc_short="Boxes in DB",desc_long="The number of boxes stored for this image in the database",property=None,defaultunits=None,choices=db_boxes)
		pdvdims = ParamDef(name="DB Box Dims",vartype="stringlist",desc_short="Dims in DB",desc_long="The dimensions boxes",property=None,defaultunits=None,choices=db_dims)
		
		p = ParamTable(name="filenames",desc_short="Choose images to box",desc_long="")
		p.append(pnames)
		p.append(pboxes)
		p.append(pdbboxes)
		p.append(pdvdims)
		
		return p,len(db_dims)
		
	def __get_e2boxer_data(self,project_names):
		
		db_name = "bdb:e2boxer.cache"		
		box_maps = {}
		if db_check_dict(db_name):
			e2boxer_db = db_open_dict(db_name)
			for name in e2boxer_db.keys():
				d = e2boxer_db[name]
				if not isinstance(d,dict): continue
				if not d.has_key("e2boxer_image_name"): # this is the test, if something else has this key then we're screwed.
					continue
				name = d["e2boxer_image_name"]
				if not name in project_names: continue
				dim = ""
				nbox = 0
				for key in ["auto_boxes","manual_boxes","reference_boxes"]:
					if d.has_key(key):
						boxes = d[key]
						if boxes != None:
							nbox += len(boxes)
							if dim == "" and len(boxes) > 0:
								box = boxes[0]
								dim = str(box.xsize) + "x"+str(box.ysize)
				
				if nbox == 0: nbox = "" # just so it appears as nothin in the interface			
				box_maps[name] = [dim,nbox]
		
		nboxes = []
		dimensions = []
		print project_names
		for name in project_names:
			if box_maps.has_key(name):
				dimensions.append(box_maps[name][0])
				nboxes.append(box_maps[name][1])
			else:
				dimensions.append("")
				nboxes.append("")
				
		return nboxes,dimensions


class E2BoxerAutoTask(E2BoxerTask):
	documentation_string = "Select the images you wish to run autoboxing on and hit OK.\nThis will cause the workflow to spawn processes based on the available CPUs.\nData will be autoboxed using the current autoboxer in the database, which is placed there by e2boxer."
	warning_string = "\n\n\nNOTE: This feature is currently disabled as there is no autoboxing information in the EMAN database. You can fix this situation by using e2boxer to interactively box a few images first"
	
	def __init__(self,application):
		E2BoxerTask.__init__(self,application)
		self.window_title = "e2boxer auto"
		self.boxer_module = None # this will actually point to an EMBoxerModule, potentially

	def get_params(self):
		params = []
		
		
		db_name = "bdb:e2boxer.cache"
		fail = False
		if db_check_dict(db_name):
			db = db_open_dict(db_name)
			if not db.has_key("current_autoboxer"): fail = True
		else:
			fail = True
			
		if fail:
			params.append(ParamDef(name="blurb",vartype="text",desc_short="Using e2boxer",desc_long="",property=None,defaultunits=E2BoxerAutoTask.documentation_string+E2BoxerAutoTask.warning_string,choices=None))
		else:
			params.append(ParamDef(name="blurb",vartype="text",desc_short="Using e2boxer",desc_long="",property=None,defaultunits=E2BoxerAutoTask.documentation_string,choices=None))
			p = self.get_e2boxer_boxes_and_project_particles_table()
			params.append(p)
	
#		boxer_project_db = db_open_dict("bdb:e2boxer.project")
#		pbox = ParamDef(name="boxsize",vartype="int",desc_short="Box size",desc_long="An integer value",property=None,defaultunits=boxer_project_db.get("working_boxsize",dfl=128),choices=[])
		
#		pfo = ParamDef(name="force",vartype="boolean",desc_short="Force overwrite",desc_long="Whether or not to force overwrite files that already exist",property=None,defaultunits=False,choices=None)
#		pwc = ParamDef(name="write_coord_files",vartype="boolean",desc_short="Write box db files",desc_long="Whether or not box db files should be written",property=None,defaultunits=False,choices=None)
#		pwb = ParamDef(name="write_box_images",vartype="boolean",desc_short="Write box image files",desc_long="Whether or not box images should be written",property=None,defaultunits=False,choices=None)
#		pn =  ParamDef(name="normproc",vartype="string",desc_short="Normalize images",desc_long="How the output box images should be normalized",property=None,defaultunits="normalize.edgemean",choices=["normalize","normalize.edgemean","none"])
#		pop = ParamDef(name="outformat",vartype="string",desc_short="Output image format",desc_long="The format of the output box images",property=None,defaultunits="bdb",choices=["bdb","img","hdf"])
#		params.append([pbox,pfo])
#		params.append([pwc,pwb])
#		params.append(pn)
#		params.append(pop)
		return params
			
	def on_form_ok(self,params):
		for k,v in params.items():
			self.write_db_entry(k,v)
			
		if not params.has_key("filenames") or len(params["filenames"]) == 0:
			self.emit(QtCore.SIGNAL("task_idle"))
			self.application().close_specific(self.form)
			self.form = None
			return
	
		else:
			options = EmptyObject()
			for k,v in params.items():
				setattr(options,k,v)
			
			string_args = []
			bool_args = []
			additional_args = ["--method=Swarm", "--auto=db"]
			temp_file_name = "e2boxer_autobox_stdout.txt"
			self.run_task("e2boxer.py",options,string_args,bool_args,additional_args,temp_file_name)
			self.emit(QtCore.SIGNAL("task_idle"))
			self.application().close_specific(self.form)
			self.form = None

	def write_db_entry(self,key,value):
		if key == "boxsize":
			boxer_project_db = db_open_dict("bdb:e2boxer.project")
			boxer_project_db["working_boxsize"] = value
			db_close_dict("bdb:e2boxer.project")
		else:
			pass
	

class E2BoxerGuiTask(E2BoxerTask):	
	documentation_string = "Select the images you want to box, enter your boxsize, and hit ok to launch e2boxer. Choose from the list of images and hit ok. This will lauch e2boxer and automatically load the selected images for boxing. Alternatively you may choose the auto_db option to execute automated boxing using information stored in the e2boxer database."
	
	def __init__(self,application):
		E2BoxerTask.__init__(self,application)
		self.window_title = "e2boxer interface"
		self.boxer_module = None # this will actually point to an EMBoxerModule, potentially

	def get_params(self):
		params = []
		params.append(ParamDef(name="blurb",vartype="text",desc_short="Using e2boxer",desc_long="",property=None,defaultunits=E2BoxerGuiTask.documentation_string,choices=None))
		
		p = self.get_e2boxer_boxes_and_project_particles_table()
		params.append(p)
		boxer_project_db = db_open_dict("bdb:e2boxer.project")
		params.append(ParamDef(name="boxsize",vartype="int",desc_short="Box size",desc_long="An integer value",property=None,defaultunits=boxer_project_db.get("working_boxsize",dfl=128),choices=[]))
		return params
			
	def on_form_ok(self,params):
		for k,v in params.items():
			self.write_db_entry(k,v)
			
		if not params.has_key("filenames") or len(params["filenames"]) == 0:
			self.emit(QtCore.SIGNAL("task_idle"))
			self.application().close_specific(self.form)
			self.form = None
			return

		else:
			options = EmptyObject()
			for key in params.keys():
				setattr(options,key,params[key])
			options.running_mode = "gui"
			options.method = "Swarm"
			
			
			self.boxer_module = EMBoxerModule(self.application(),options)
			self.emit(QtCore.SIGNAL("gui_running"),"Boxer",self.boxer_module) # The controlled program should intercept this signal and keep the E2BoxerTask instance in memory, else signals emitted internally in boxer won't work
			
			QtCore.QObject.connect(self.boxer_module, QtCore.SIGNAL("module_idle"), self.on_boxer_idle)
			QtCore.QObject.connect(self.boxer_module, QtCore.SIGNAL("module_closed"), self.on_boxer_closed)
			self.application().close_specific(self.form)
			self.boxer_module.show_guis()
			self.form = None
			
	def on_form_close(self):
		# this is to avoid a task_idle signal, which would be incorrect if e2boxer is running
		if self.boxer_module == None:
			self.emit(QtCore.SIGNAL("task_idle"))
		else: pass
	
	def on_boxer_closed(self): 
		if self.boxer_module != None:
			self.boxer_module = None
			self.emit(QtCore.SIGNAL("gui_exit"))
	
	def on_boxer_idle(self):
		'''
		Presently this means boxer did stuff but never opened any guis, so it's safe just to emit the signal
		'''
		print "boxer idle"
		self.boxer_module = None
		self.emit(QtCore.SIGNAL("gui_exit"))

	def write_db_entry(self,key,value):
		if key == "boxsize":
			boxer_project_db = db_open_dict("bdb:e2boxer.project")
			boxer_project_db["working_boxsize"] = value
			db_close_dict("bdb:e2boxer.project")
		else:
			pass

class E2BoxerOutputTask(E2BoxerTask):	
	documentation_string = "Select the images you wish to generate output for, enter the box size and normalization etc, and then hit OK.\nThis will cause the workflow to spawn output writing processes using the available CPUs. Note that the bdb option is the preferred output format, in this mode output particles are written directly to the EMAN project database."
	warning_string = "\n\n\nNOTE: There are no boxes currently stored in the database. To rectify this situation use e2boxer to interactively box your images, or alternatively used autoboxing information stored in the database to autobox your images."
	def __init__(self,application):
		E2BoxerTask.__init__(self,application)
		self.window_title = "e2boxer output"
	
	def get_params(self):
		params = []
		
		p,n = self.get_project_files_that_have_db_boxes_in_table()
		if n == 0:
			params.append(ParamDef(name="blurb",vartype="text",desc_short="Using e2boxer",desc_long="",property=None,defaultunits=E2BoxerOutputTask.documentation_string+E2BoxerOutputTask.warning_string,choices=None))
		else:
			params.append(ParamDef(name="blurb",vartype="text",desc_short="Using e2boxer",desc_long="",property=None,defaultunits=E2BoxerOutputTask.documentation_string,choices=None))
			params.append(p)
			self.add_general_params(params)
	
#		boxer_project_db = db_open_dict("bdb:e2boxer.project")
#		params.append(ParamDef(name="boxsize",vartype="int",desc_short="Box size",desc_long="An integer value",property=None,defaultunits=boxer_project_db.get("working_boxsize",dfl=128),choices=[]))
		return params
	
	def add_general_params(self,params):
		'''
		Functionality used in several places
		'''
		boxer_project_db = db_open_dict("bdb:e2boxer.project")
		pbox = ParamDef(name="boxsize",vartype="int",desc_short="Box size",desc_long="An integer value",property=None,defaultunits=boxer_project_db.get("working_boxsize",dfl=128),choices=[])	
		pfo = ParamDef(name="force",vartype="boolean",desc_short="Force overwrite",desc_long="Whether or not to force overwrite files that already exist",property=None,defaultunits=False,choices=None)
		pwc = ParamDef(name="write_coord_files",vartype="boolean",desc_short="Write box db files",desc_long="Whether or not box db files should be written",property=None,defaultunits=False,choices=None)
		pwb = ParamDef(name="write_box_images",vartype="boolean",desc_short="Write box image files",desc_long="Whether or not box images should be written",property=None,defaultunits=True,choices=None)
		pn =  ParamDef(name="normproc",vartype="string",desc_short="Normalize images",desc_long="How the output box images should be normalized",property=None,defaultunits="normalize.edgemean",choices=["normalize","normalize.edgemean","none"])
		pop = ParamDef(name="outformat",vartype="string",desc_short="Output image format",desc_long="The format of the output box images",property=None,defaultunits="bdb",choices=["bdb","img","hdf"])
		params.append([pbox,pfo])
		params.append([pwc,pwb])
		params.append(pn)
		params.append(pop)
		
			
	def on_form_ok(self,params):
		for k,v in params.items():
			self.write_db_entry(k,v)
			
		if not params.has_key("filenames") or len(params["filenames"]) == 0:
			self.emit(QtCore.SIGNAL("task_idle"))
			self.application().close_specific(self.form)
			self.form = None
			return
	
		else:
			options = EmptyObject()
			for k,v in params.items():
				setattr(options,k,v)
				
			options.just_output=True # this is implicit, it has to happen
			
			string_args = ["normproc","outformat","boxsize"]
			bool_args = ["force","write_coord_files","write_box_images","just_output"]
			additional_args = ["--method=Swarm", "--auto=db"]
			temp_file_name = "e2boxer_autobox_stdout.txt"
			self.run_task("e2boxer.py",options,string_args,bool_args,additional_args,temp_file_name)
			self.emit(QtCore.SIGNAL("task_idle"))
			self.application().close_specific(self.form)
			self.form = None
#	
	def write_db_entry(self,key,value):
		if key == "boxsize":
			boxer_project_db = db_open_dict("bdb:e2boxer.project")
			boxer_project_db["working_boxsize"] = value
			db_close_dict("bdb:e2boxer.project")
		else:
			pass

class E2BoxerOutputTaskGeneral(E2BoxerOutputTask):
	documentation_string = "Write me"
	def __init__(self,application):
		E2BoxerOutputTask.__init__(self,application)
		
	def get_params(self):
		params = []
		params.append(ParamDef(name="blurb",vartype="text",desc_short="Using e2boxer",desc_long="",property=None,defaultunits=E2BoxerOutputTaskGeneral.documentation_string,choices=None))
		
		p = self.get_e2boxer_boxes_table(project_check=False)
		params.append(p)
		
		self.add_general_params(params)
	
#		boxer_project_db = db_open_dict("bdb:e2boxer.project")
#		params.append(ParamDef(name="boxsize",vartype="int",desc_short="Box size",desc_long="An integer value",property=None,defaultunits=boxer_project_db.get("working_boxsize",dfl=128),choices=[]))
		return params
	
	def get_e2boxer_boxes_table(self,project_check=True):
		db_name = "bdb:e2boxer.cache"
		p = ParamTable(name="filenames",desc_short="Current boxes generated by e2boxer",desc_long="")
		names = []
		nboxes = []
		dimensions = []
		
		if project_check:
			project_db = db_open_dict("bdb:project")	
			project_names = project_db.get("global.micrograph_ccd_filenames",dfl=[])
		
		if db_check_dict(db_name):
			e2boxer_db = db_open_dict(db_name)
			for name in e2boxer_db.keys():
				d = e2boxer_db[name]
				if not isinstance(d,dict): continue
				if not d.has_key("e2boxer_image_name"): # this is the test, if something else has this key then we're screwed.
					continue

				name = d["e2boxer_image_name"]
				if project_check:
					if not name in project_names: continue
				names.append(name)
				
				dim = ""
				nbox = 0
				for key in ["auto_boxes","manual_boxes","reference_boxes"]:
					if d.has_key(key):
						boxes = d[key]
						nbox += len(boxes)
						print len(boxes)
						if dim == "" and len(boxes) > 0:
							box = boxes[0]
							dim = str(box.xsize) + "x"+str(box.ysize)
							
							
				nboxes.append(nbox)
				dimensions.append(dim)
			
		print "names are",names
		print "boxes are",nboxes
		print "dims are",dimensions
		
		pnames = ParamDef(name="Filenames",vartype="stringlist",desc_short="File names",desc_long="The filenames",property=None,defaultunits=None,choices=names)
		pboxes = ParamDef(name="Num boxes",vartype="intlist",desc_short="Boxes in DB",desc_long="The number of boxes stored for this image in the database",property=None,defaultunits=None,choices=nboxes)
		pdims = ParamDef(name="Dimensions",vartype="stringlist",desc_short="Dimensions",desc_long="The dimensions boxes",property=None,defaultunits=None,choices=dimensions)
		
		p = ParamTable(name="filenames",desc_short="Choose images to box",desc_long="")
		p.append(pnames)
		p.append(pboxes)
		p.append(pdims)
		return p

class E2BoxerGeneralTask(WorkFlowTask):
	documentation_string = "You can run e2boxer on whichever images you like using this tool. If there is a current autoboxer in the EMAN2 database then you will also be able to execute automated boxing"
	auto_documentation_string = "Choose the images that you want to run automated boxing on using the current autoboxer in the EMAN2 database"
	def __init__(self,application):
		WorkFlowTask.__init__(self,application)
		self.window_title = "Boxer"
		self.form2 = None
		self.boxer_module = None
		
	def get_params(self):
		
		params = []
		params.append(ParamDef(name="blurb",vartype="text",desc_short="",desc_long="",property=None,defaultunits=E2BoxerGeneralTask.documentation_string,choices=None))
		
		
		params.append(ParamDef(name="filenames",vartype="url",desc_short="File names",desc_long="The files you wish to box",property=None,defaultunits=[],choices=[]))
		
		boxer_project_db = db_open_dict("bdb:e2boxer.project")
		params.append(ParamDef(name="boxsize",vartype="int",desc_short="Box size",desc_long="An integer value",property=None,defaultunits=boxer_project_db.get("working_boxsize",dfl=128),choices=[]))
		params.append(ParamDef(name="method",vartype="choice",desc_short="Boxing mode",desc_long="Currently only one mode is supported, but this could change",property=None,defaultunits="Swarm",choices=["Swarm"]))
		
		
		boxer_cache_db = db_open_dict("bdb:e2boxer.cache")
		if boxer_cache_db.has_key("current_autoboxer"):
			running_mode_options = ["gui","auto_db"]
		else:
			running_mode_options = ["gui"]
		params.append(ParamDef(name="running_mode",vartype="choice",desc_short="Boxing mode",desc_long="Whether to load the GUI or run automatic boxing based on information stored in the database",property=None,defaultunits="gui",choices=running_mode_options))
		return params

	def get_auto_params(self,params):
		
		
		try: filenames = params["filenames"]
		except: filenames = []
		try: boxsize = params["boxsize"]
		except: boxsize = 128
		fo = False
		wc = False
		wb = True
		norm = "normalize.edgemean"
		output = "hdf"
	
		params = []
		params.append(ParamDef(name="blurb",vartype="text",desc_short="",desc_long="",property=None,defaultunits=E2BoxerGeneralTask.auto_documentation_string,choices=None))
		
		params.append(ParamDef(name="filenames",vartype="url",desc_short="File names",desc_long="The files you wish to box",property=None,defaultunits=filenames,choices=[]))
		pbox = ParamDef(name="boxsize",vartype="int",desc_short="Box size",desc_long="The output box size",property=None,defaultunits=boxsize,choices=None)
		pfo = ParamDef(name="force",vartype="boolean",desc_short="Force overwrite",desc_long="Whether or not to force overwrite files that already exist",property=None,defaultunits=fo,choices=None)
		pwc = ParamDef(name="write_coord_files",vartype="boolean",desc_short="Write box db files",desc_long="Whether or not box db files should be written",property=None,defaultunits=wc,choices=None)
		pwb = ParamDef(name="write_box_images",vartype="boolean",desc_short="Write box image files",desc_long="Whether or not box images should be written",property=None,defaultunits=wb,choices=None)
		pn =  ParamDef(name="normproc",vartype="string",desc_short="Normalize images",desc_long="How the output box images should be normalized",property=None,defaultunits="normalize.edgmean",choices=["normalize","normalize.edgemean","none"])
		pop = ParamDef(name="outformat",vartype="string",desc_short="Output image format",desc_long="The format of the output box images",property=None,defaultunits="bdb",choices=["bdb","img","hdf"])
		params.append([pbox,pfo])
		params.append([pwc,pwb])
		params.append(pn)
		params.append(pop)
		return params

	def on_form_ok(self,params):
		
		for k,v in params.items():
			self.write_db_entry(k,v)
		
		filenames_ok = True
		if len(params["filenames"]) == 0: filenames_ok = False
		else:
			fine,message = check_files_are_2d_images(params["filenames"])
			if not fine:
				filenames_ok = False
#				message_box = QtGui.QMessageBox()
#				message_box.setText(message)
#				message_box.show()
#				return
#				
			# if this is true we can't do anything, just kill the form. Yes their could be other ways to act here, but this is the simplest option
		if not filenames_ok:
			self.application().close_specific(self.form)
			self.form = None
		
			self.emit(QtCore.SIGNAL("task_idle"))
		else:
			if params["running_mode"] == "gui":
				options = EmptyObject()
				options.running_mode = "gui"
				options.method = params["method"] # this always be "Swarm" but it could change
				options.filenames = params["filenames"]
				options.boxsize = params["boxsize"]
				
				
				
				self.boxer_module = EMBoxerModule(self.application(),options)
				self.emit(QtCore.SIGNAL("gui_running"),"Boxer",self.boxer_module) # The controlled program should intercept this signal and keep the E2BoxerTask instance in memory, else signals emitted internally in boxer won't work
				
				QtCore.QObject.connect(self.boxer_module, QtCore.SIGNAL("module_idle"), self.on_boxer_idle)
				QtCore.QObject.connect(self.boxer_module, QtCore.SIGNAL("module_closed"), self.on_boxer_closed)
				
				self.boxer_module.show_guis()
				self.application().close_specific(self.form)
				self.form = None
				
			elif params["running_mode"] == "auto_db":
				self.run_second_form(params)
				
				
	
	def on_form_close(self):
		# this is to avoid a task_idle signal, which would be incorrect if e2boxer or the seconf form is running
		if self.form2 == None and self.boxer_module == None:
			self.emit(QtCore.SIGNAL("task_idle"))
		else: pass
				
	def run_second_form(self,params):
		self.form2 = EMFormModule(self.get_auto_params(params),self.application)
		self.form2.qt_widget.resize(480,640)
		self.form2.setWindowTitle("Automated Boxing")
		self.application().show_specific(self.form2)
		QtCore.QObject.connect(self.form2,QtCore.SIGNAL("emform_ok"),self.on_form_2_ok)
		QtCore.QObject.connect(self.form2,QtCore.SIGNAL("emform_cancel"),self.on_form_2_cancel)
		QtCore.QObject.connect(self.form2,QtCore.SIGNAL("emform_close"),self.on_form_2_close)
	
		self.application().close_specific(self.form)
		self.form = None # have to this now or the form close function will emit "task_idle"
		
	
	def on_form_2_ok(self,params):
		filenames_ok = True
		if len(params["filenames"]) == 0: filenames_ok = False
		else:
			fine,message = check_files_are_2d_images(params["filenames"])
			if not fine:
				filenames_ok = False
#				message_box = QtGui.QMessageBox()
#				message_box.setText(message)
#				message_box.show()
#				return
#				
			# if this is true we can't do anything, just kill the form. Yes their could be other ways to act here, but this is the simplest option
		if not filenames_ok:
			self.application().close_specific(self.form2)
			self.form2 = None
		
			self.emit(QtCore.SIGNAL("task_idle"))
		else:
			options = EmptyObject()
			for k,v in params.items():
				setattr(options,k,v)
			
			string_args = ["normproc","outformat","boxsize"]
			bool_args = ["force","write_coord_files","write_box_images"]
			additional_args = ["--method=Swarm", "--auto=db"]
			temp_file_name = "e2boxer_autobox_stdout.txt"
			self.run_task("e2boxer.py",options,string_args,bool_args,additional_args,temp_file_name)
			
			self.emit(QtCore.SIGNAL("task_idle"))
			self.application().close_specific(self.form2)
			self.form2 = None
			
	def on_form_2_cancel(self):
		self.application().close_specific(self.form2)
		self.form2 = None
		self.emit(QtCore.SIGNAL("task_idle"))
	
	def on_form_2_close(self):
		self.form2 = None
		self.emit(QtCore.SIGNAL("task_idle"))
		
	def write_db_entry(self,k,v):
		if k == "boxsize" and v > 0:
			boxer_project_db = db_open_dict("bdb:e2boxer.project")
			boxer_project_db["working_boxsize"] = v
	
	
	def on_boxer_closed(self): 
		if self.boxer_module != None:
			self.boxer_module = None
			self.emit(QtCore.SIGNAL("gui_exit"))
	
	def on_boxer_idle(self):
		'''
		Presently this means boxer did stuff but never opened any guis, so it's safe just to emit the signal
		'''
		print "boxer idle"
		self.boxer_module = None
		self.emit(QtCore.SIGNAL("gui_exit"))
		
class E2CTFWorkFlowTask(ParticleWorkFlowTask):
	def __init__(self,application):
		ParticleWorkFlowTask.__init__(self,application)

	def get_ctf_param_table(self,particle_file_names=None,no_particles=False):
		'''
		particle_files_names should be the return variable of self.get_particle_db_names(strip_ptcls=False), or get_ctf_project_names
		'''
		if particle_file_names == None: # just left this here in case anyone is wandering what to do
			particle_file_names = self.get_particle_db_names(strip_ptcls=False)
		
		defocus,dfdiff,dfang,bfactor = self.get_ctf_info(particle_file_names)
		
		pnames = ParamDef(name="micrograph_ccd_filenames",vartype="stringlist",desc_short="File names",desc_long="The raw data from which particles will be extracted and ultimately refined to produce a reconstruction",property=None,defaultunits=None,choices=particle_file_names)
		pdefocus = ParamDef(name="Defocus",vartype="floatlist",desc_short="Defocus",desc_long="Estimated defocus of the microscope",property=None,defaultunits=None,choices=defocus)
		pbfactor = ParamDef(name="Bfactor",vartype="floatlist",desc_short="B factor",desc_long="Estimated B factor of the microscope",property=None,defaultunits=None,choices=bfactor)
		num_phase,num_wiener,num_particles = self.get_ctf_particle_info(particle_file_names)
		pboxes = ParamDef(name="Num boxes",vartype="intlist",desc_short="Particles",desc_long="The number of particles stored for this image in the database",property=None,defaultunits=None,choices=num_particles)
		pwiener = ParamDef(name="Num wiener",vartype="intlist",desc_short="Phase flipped",desc_long="The number of Wiener filter particles stored for this image in the database",property=None,defaultunits=None,choices=num_phase)
		pphase = ParamDef(name="Num phase",vartype="intlist",desc_short="Wienered",desc_long="The number of phase flipped particles stored for this image in the database",property=None,defaultunits=None,choices=num_wiener)
		
		p = ParamTable(name="filenames",desc_short="Current CTF parameters",desc_long="")
		
		p.append(pnames)
		if not no_particles: p.append(pboxes)
		p.append(pwiener)
		p.append(pphase)
		p.append(pdefocus)
		p.append(pbfactor)
		
		return p
	
	def get_ctf_info(self,particle_file_names):
		if db_check_dict("bdb:e2ctf.parms"):
			defocus = []
			dfdiff = []
			dfang = []
			bfactor = []
			ctf_db = db_open_dict("bdb:e2ctf.parms")
			for name in particle_file_names:
				try:
					vals = ctf_db[name][0]
					ctf = EMAN2Ctf()
					ctf.from_string(vals)
					vals = [ctf.defocus,ctf.dfdiff,ctf.dfang,ctf.bfactor]
				except:
					vals = ["","","",""]  # only need 4 at the moment
					
				defocus.append(vals[0])
				dfdiff.append(vals[1])
				dfang.append(vals[2])
				bfactor.append(vals[3])
				
			db_close_dict("bdb:e2ctf.parms")

			return defocus,dfdiff,dfang,bfactor
	
		else:
			dummy = ["" for i in range(len(particle_file_names))]
			return dummy,dummy,dummy,dummy
	def get_ctf_particle_info(self,particle_file_names):
		'''
		Returns three string lists containing entries correpsonding to the number of phase corrected, wiener correct, and regular particles in the database
		
		You could call this function with the names of the particle images in the bdb particles directory, i.e. all pariticle file names would
		look like
		img_001_ptcls
		img_003_ptcls
		And these would correspond to entries in the particles database, ie the following bdb entries would exist and contain particles
		bdb:particles#:img_001_ptcls
		bdb:particles#:img_003_ptcls
		
		But you might also call it with the filenames from the e2ctf.parms directory
		
		'''
		phase = []
		wiener = []
		particles = []
		
		for name in particle_file_names:
			particle_db_name = "bdb:particles#"+name
			wiener_ptcl_db_name = particle_db_name + "_ctf_wiener"
			flip_ptcl_db_name = particle_db_name + "_ctf_flip"
			d = {}
			d[particle_db_name] = particles
			d[wiener_ptcl_db_name] = wiener
			d[flip_ptcl_db_name] = phase
			
			for db_name,data_list in d.items():
				if db_check_dict(db_name):
					particle_db = db_open_dict(db_name)
					if particle_db.has_key("maxrec"): 
						data_list.append(particle_db["maxrec"]+1)
					else: data_list.append("")
					db_close_dict(db_name)
				else: data_list.append("")
		
		return phase,wiener,particles
#		else:
#			print "no db for particles"
#			dummy = [-1 for i in range(len(particle_file_names))]
#			return dummy,dummy,dummy
		
		
		
	def get_ctf_project_names(self):
		'''
		Inspects the e2ctf.parms database for any images that have ctf parameters
		'''
		if db_check_dict("bdb:e2ctf.parms"):
			ctf_parms_db = db_open_dict("bdb:e2ctf.parms")
			vals = ctf_parms_db.keys()
			#print vals
			if vals == None: vals = []
			db_close_dict("bdb:e2ctf.parms")
			return vals
		else:
			print "empty, empty"
			return []
		
	def get_names_with_parms(self):
		'''
		opens the e2ctf.parms directory and returns all a list of lists like this:
		[[db_name_key, real_image_name],....]
		eg
		[[neg_001,neg_001.hdf],[ptcls_01,bdb:particles#ptcls_01_ptcls],...] etc
		e2ctf is responsible for making sure the last data entry for each image is the original image name (this was first enforced by d.woolford)
		'''
		parms_db = db_open_dict("bdb:e2ctf.parms")
		
		ret = []
		for key,data in parms_db.items():
			ret.append([key,data[-1]]) # parms[-1] should be the original filename
				
		return ret
		
class E2CTFGeneralTask(E2CTFWorkFlowTask):
	documentation_string = "Fill me in"
	def __init__(self,application):
		E2CTFWorkFlowTask.__init__(self,application)
		self.window_title = "e2ctf"
		self.preferred_size = (480,200)
		
		
	def get_params(self):
		params = []		
#		params.append(ParamDef(name="blurb",vartype="text",desc_short="",desc_long="",property=None,defaultunits=E2CTFGeneralTask.documentation_string,choices=None))
		
		params.append(ParamDef(name="running_mode",vartype="choice",desc_short="Choose your running mode",desc_long="There are three CTF related task which are generally run in order",property=None,defaultunits="auto",choices=["auto params", "interactively fine tune", "write output"]))
		
		return params

	def on_form_ok(self,params):
		if params["running_mode"] == "auto params":
			self.emit(QtCore.SIGNAL("replace_task"),E2CTFAutoFitTaskGeneral,"ctf auto fit")
			self.application().close_specific(self.form)
			self.form = None
		elif params["running_mode"] == "interactively fine tune":
			self.emit(QtCore.SIGNAL("replace_task"),E2CTFGuiTaskGeneral,"fine tune ctf")
			self.application().close_specific(self.form)
			self.form = None
		elif params["running_mode"] == "write output":
			self.emit(QtCore.SIGNAL("replace_task"),E2CTFOutputTaskGeneral,"ctf output")
			self.application().close_specific(self.form)
			self.form = None	
		else:
			self.application().close_specific(self.form)
			self.form = None
			self.emit(QtCore.SIGNAL("task_idle"))
			
	def write_db_entry(self,key,value):
		pass

class E2CTFAutoFitTask(E2CTFWorkFlowTask):	
	documentation_string = "Use this tool to use e2ctf to generate ctf parameters for the particles located in the project particle directory"
	
	def __init__(self,application):
		E2CTFWorkFlowTask.__init__(self,application)
		self.window_title = "e2ctf auto fit"

	def get_params(self):
		params = []		
		params.append(ParamDef(name="blurb",vartype="text",desc_short="",desc_long="",property=None,defaultunits=E2CTFAutoFitTask.documentation_string,choices=None))
		
		params.append(self.get_ctf_param_table(self.get_particle_db_names(strip_ptcls=False)))
		self.add_general_params(params)

		return params
	
	def add_general_params(self,params):
		project_db = db_open_dict("bdb:project")
		ctf_misc_db = db_open_dict("bdb:e2ctf.misc")
		papix = ParamDef(name="global.apix",vartype="float",desc_short="A/pix for project",desc_long="The physical distance represented by the pixel spacing",property=None,defaultunits=project_db.get("global.apix",dfl=1.1),choices=None)
		pvolt = ParamDef(name="global.microscope_voltage",vartype="float",desc_short="Microscope voltage",desc_long="The operating voltage of the microscope",property=None,defaultunits=project_db.get("global.microscope_voltage",dfl=300),choices=None)
		pcs = ParamDef(name="global.microscope_cs",vartype="float",desc_short="Microscope Cs",desc_long="Microscope spherical aberration constant",property=None,defaultunits=project_db.get("global.microscope_cs",dfl=2.0),choices=None)
		pac = ParamDef(name="working_ac",vartype="float",desc_short="Amplitude contrast",desc_long="The amplitude contrast constant. It is recommended that this value is identical in all of your images.",property=None,defaultunits=ctf_misc_db.get("working_ac",dfl=10),choices=None)
		pos = ParamDef(name="working_oversamp",vartype="int",desc_short="Oversampling",desc_long="If greater than 1, oversampling by this amount will be used when images are being phase flipped and Wiener filtered.",property=None,defaultunits=ctf_misc_db.get("working_oversamp",dfl=1),choices=None)
		pncp = ParamDef(name="global.num_cpus",vartype="int",desc_short="Number of CPUs",desc_long="Number of CPUS available for the project to use",property=None,defaultunits=project_db.get("global.num_cpus",dfl=num_cpus()),choices=None)
		mem = memory_stats()
		
		params.append([papix,pvolt,pcs])
		params.append([pac,pos,pncp])

		db_close_dict("bdb:project")
	
	def get_default_ctf_options(self,params):
		'''
		These are the options required to run pspec_and_ctf_fit in e2ctf.py
		'''
		
		if not params.has_key("filenames") and len(params["filenames"]) == 0:
			print "there is an internal error. You are asking for the default ctf options but there are no filenames" # this shouldn't happen
			return None
		
		filenames = params["filenames"]
		
		boxsize = None
		db_file_names = []
		for i,name in enumerate(filenames):
			db_name="bdb:particles#"+name
			db_file_names.append(db_name)
			if not db_check_dict(db_name):
				print "error, can't particle entry doesn't exist for",name,"aborting."
				return None
			
			if boxsize == None:
				db = db_open_dict(db_name)
				hdr = db.get_header(0)
				boxsize = hdr["nx"] # no consideration is given for non square images
				db_close_dict(db_name)
			else:
				db = db_open_dict(db_name)
				hdr = db.get_header(0)
				db_close_dict(db_name)
				if boxsize != hdr["nx"]: # no consideration is given for non square images
					print "error, can't run e2ctf on images with different box sizes. Specifically, I can not deduce the bgmask option for the group"
					return None
		
		if boxsize == None or boxsize < 2:
			print "error, boxsize is less than 2"
			return None
		
		
		options = EmptyObject()
		options.bgmask = boxsize/2
		options.filenames = db_file_names
		self.append_general_options(options,params)
	
		return options
	
	def append_general_options(self,options,params):
		'''
		This is done in more than one place hence this function
		'''
		
		options.nosmooth = False
		options.nonorm = False
		options.autohp = False
		options.invert = False
		options.oversamp = params["working_oversamp"]
		options.ac = params["working_ac"]
		options.apix = params["global.apix"]
		options.cs = params["global.microscope_cs"]
		options.voltage = params["global.microscope_voltage"]
		
	def on_form_ok(self,params):
		for k,v in params.items():
			self.write_db_entry(k,v)
		
		options = self.get_default_ctf_options(params)
		if options != None:
			
			string_args = ["bgmask","oversamp","ac","apix","cs","voltage"]
			bool_args = ["nosmooth","nonorm","autohp","invert"]
			additional_args = ["--auto_fit"]
			temp_file_name = "e2ctf_autofit_stdout.txt"
			self.run_task("e2ctf.py",options,string_args,bool_args,additional_args,temp_file_name)
			
			self.application().close_specific(self.form)
			self.emit(QtCore.SIGNAL("task_idle"))
			
		else:
			self.application().close_specific(self.form)
			self.emit(QtCore.SIGNAL("task_idle"))
		
	def on_form_close(self):
		# this is to avoid a task_idle signal, which would be incorrect if e2boxer is running
		self.emit(QtCore.SIGNAL("task_idle"))

	def write_db_entry(self,key,value):
		if key == "working_ac":
			ctf_misc_db = db_open_dict("bdb:e2ctf.misc")
			ctf_misc_db["working_ac"] = value
			db_close_dict("bdb:e2ctf.misc")
		elif key == "working_oversamp":
			ctf_misc_db = db_open_dict("bdb:e2ctf.misc")
			ctf_misc_db["working_oversamp"] = value
			db_close_dict("bdb:e2ctf.misc")
		else:
			# there are some general parameters that need writing:
			WorkFlowTask.write_db_entry(self,key,value)
			
class E2CTFAutoFitTaskGeneral(E2CTFAutoFitTask):
	'''
	This one has a generic url browser to get the input file names as opposed to the more rigid project based one
	'''
	documentation_string = "Use this tool to use e2ctf to generate ctf parameters for the particles located anywhere on disk"
	
	def __init__(self,application):
		E2CTFAutoFitTask.__init__(self,application)
		self.window_title = "e2ctf auto fit"
		self.file_check = True
	def get_params(self):
		params = []		
		params.append(ParamDef(name="blurb",vartype="text",desc_short="",desc_long="",property=None,defaultunits=E2CTFAutoFitTask.documentation_string,choices=None))
		
		params.append(ParamDef(name="filenames",vartype="url",desc_short="File names",desc_long="The names of the particle files you want to generate automated ctf parameters for",property=None,defaultunits=[],choices=[]))
		
		self.add_general_params(params)

		db_close_dict("bdb:project")
		return params
	
	def get_default_ctf_options(self,params):
		'''
		These are the options required to run pspec_and_ctf_fit in e2ctf.py
		'''
		
		if not params.has_key("filenames") and len(params["filenames"]) == 0:
			print "there is an internal error. You are asking for the default ctf options but there are no filenames" # this shouldn't happen
			return None
		
		filenames = params["filenames"]
		fine,message = check_files_are_em_images(filenames)
		
		if not fine:
			print message
			return None
		
		boxsize = None
		db_file_names = []
		for i,name in enumerate(filenames):
			a = EMData()
			a.read_image(name,0,True)
			if boxsize == None:
				boxsize = a.get_attr("nx") # no consideration is given for non square images
			elif boxsize != a.get_attr("nx"): # no consideration is given for non square images
					print "error, can't run e2ctf on images with different box sizes." # Specifically, I can not deduce the bgmask option for the group"
					return None
		
		if boxsize == None or boxsize < 2:
			print "error, boxsize is less than 2"
			return None
		
		options = EmptyObject()
		options.bgmask = boxsize/2
		options.filenames = filenames
		self.append_general_options(options,params)
		return options

class E2CTFOutputTask(E2CTFWorkFlowTask):	
	documentation_string = "Use this tool to use e2ctf to generate ctf parameters for the particles located in the project particle directory"
	
	def __init__(self,application):
		E2CTFWorkFlowTask.__init__(self,application)
		self.window_title = "e2ctf management"

	def get_params(self):
		params = []		
		params.append(ParamDef(name="blurb",vartype="text",desc_short="",desc_long="",property=None,defaultunits=E2CTFOutputTask.documentation_string,choices=None))
		
		params.append(self.get_ctf_param_table(self.get_particle_db_names(strip_ptcls=False)))
		
		pwiener = ParamDef(name="wiener",vartype="boolean",desc_short="Wiener + phase flip",desc_long="Wiener filter your particle images using parameters in the database. Phase flipping will also occur",property=None,defaultunits=False,choices=None)
		pphase = ParamDef(name="phaseflip",vartype="boolean",desc_short="Phase flip",desc_long="Phase flip your particle images using parameters in the database",property=None,defaultunits=False,choices=None)
		
		params.append([pphase,pwiener])
		return params

	def get_default_ctf_options(self,params):
		'''
		These are the options required to run pspec_and_ctf_fit in e2ctf.py, works in e2workflow
		'''
		
		if not params.has_key("filenames") and len(params["filenames"]) == 0:
			print "there is an internal error. You are asking for the default ctf options but there are no filenames to deduce the bgmask option from" # this shouldn't happen
			return None
		
		
		options = EmptyObject()
	
		filenames = params["filenames"]
#
		db_file_names = []
		for i,name in enumerate(filenames):
			db_name="bdb:particles#"+name
			db_file_names.append(db_name)
			if not db_check_dict(db_name):
				print "error, can't particle entry doesn't exist for",name,"aborting."
				return None
		options.filenames = db_file_names
		options.wiener = params["wiener"]
		options.phaseflip = params["phaseflip"]
#		
		return options
	
	def on_form_ok(self,params):
		for k,v in params.items():
			self.write_db_entry(k,v)

		options = self.get_default_ctf_options(params)
		if options != None and len(options.filenames) > 0 and (options.wiener or options.phaseflip):

			string_args = []
			bool_args = ["wiener","phaseflip"]
			additional_args = []
			temp_file_name = "e2ctf_output_stdout.txt"
			self.run_task("e2ctf.py",options,string_args,bool_args,additional_args,temp_file_name)
			

			self.application().close_specific(self.form)
			self.emit(QtCore.SIGNAL("task_idle"))
		else:
			self.application().close_specific(self.form)
			self.emit(QtCore.SIGNAL("task_idle"))
	
	def on_ctf_closed(self):
		self.emit(QtCore.SIGNAL("gui_exit")) #
		
	def on_form_close(self):
		# this is to avoid a task_idle signal, which would be incorrect if e2boxer is running
		self.emit(QtCore.SIGNAL("task_idle"))

class E2CTFOutputTaskGeneral(E2CTFOutputTask):
	''' This one uses the names in the e2ctf.parms to generate it's table of options, not the particles in the particles directory
	'''
	documentation_string = "Write me"
	
	def __init__(self,application):
		E2CTFOutputTask.__init__(self,application)
		self.window_title = "e2ctf management"

	def get_params(self):
		params = []		
		params.append(ParamDef(name="blurb",vartype="text",desc_short="",desc_long="",property=None,defaultunits=E2CTFOutputTaskGeneral.documentation_string,choices=None))
		
		names = self.get_names_with_parms()
		n = [l[0] for l in names]
		params.append(self.get_ctf_param_table(n,no_particles=True))
		
		pwiener = ParamDef(name="wiener",vartype="boolean",desc_short="Wiener + phase flip",desc_long="Wiener filter your particle images using parameters in the database. Phase flipping will also occur",property=None,defaultunits=False,choices=None)
		pphase = ParamDef(name="phaseflip",vartype="boolean",desc_short="Phase flip",desc_long="Phase flip your particle images using parameters in the database",property=None,defaultunits=False,choices=None)
		
		params.append([pphase,pwiener])
		return params
	
	def get_ctf_options(self,params):
		'''
		This is a way to get the ctf optiosn if one is using the "alternate" path, which means just in the context of general use of e2ctf (not the workflow)
		'''
		options = EmptyObject()

		selected_filenames = params["filenames"]
		
		filenames = []
		names = self.get_names_with_parms()
		for name in names:
			if name[0] in selected_filenames:
				filenames.append(name[1])
		options.filenames = filenames

		options.wiener = params["wiener"]
		options.phaseflip = params["phaseflip"]
#		
		return options

	def on_form_ok(self,params):
		for k,v in params.items():
			self.write_db_entry(k,v)

		options = self.get_ctf_options(params)
		if options != None and len(options.filenames) > 0 and (options.wiener or options.phaseflip):
			
			string_args = []
			bool_args = ["wiener","phaseflip"]
			additional_args = []
			temp_file_name = "e2ctf_output_stdout.txt"
			print "running task"
			self.run_task("e2ctf.py",options,string_args,bool_args,additional_args,temp_file_name)
			

			self.application().close_specific(self.form)
			self.emit(QtCore.SIGNAL("task_idle"))
		else:
			self.application().close_specific(self.form)
			self.emit(QtCore.SIGNAL("task_idle"))
	
class E2CTFGuiTask(E2CTFWorkFlowTask):	
	documentation_string = "Use this tool to use e2ctf to generate ctf parameters for the particles located in the project particle directory"
	
	def __init__(self,application):
		E2CTFWorkFlowTask.__init__(self,application)
		self.window_title = "e2ctf management"
		self.gui = None # will eventually be a e2ctf gui

	def get_params(self):
		params = []		
		params.append(ParamDef(name="blurb",vartype="text",desc_short="",desc_long="",property=None,defaultunits=E2CTFGuiTask.documentation_string,choices=None))
		
		params.append(self.get_ctf_param_table(self.get_particle_db_names(strip_ptcls=False)))
		return params
	
	def get_default_ctf_options(self,params):
		'''
		These are the options required to run pspec_and_ctf_fit in e2ctf.py
		'''
		
		if not params.has_key("filenames") and len(params["filenames"]) == 0:
			print "There are no filenames" # this shouldn't happen
			return None
		
		
		options = EmptyObject()
		filenames = params["filenames"]
#
		db_file_names = []
		for i,name in enumerate(filenames):
			db_name="bdb:particles#"+name
			db_file_names.append(db_name)
			if not db_check_dict(db_name):
				print "No project particles entry exists for",name,"aborting."
				return None
		options.filenames = db_file_names
#		
		return options

	
	def on_form_ok(self,params):
		for k,v in params.items():
			self.write_db_entry(k,v)

		options = self.get_default_ctf_options(params)
		if options != None and len(options.filenames) > 0:
			
			img_sets = get_gui_arg_img_sets(options.filenames)
		
			
			self.gui=GUIctfModule(self.application(),img_sets)
			self.emit(QtCore.SIGNAL("gui_running"), "CTF", self.gui) # so the desktop can prepare some space!
			self.application().close_specific(self.form)
			QtCore.QObject.connect(self.gui,QtCore.SIGNAL("module_closed"), self.on_ctf_closed)
			self.gui.show_guis()
		else:
			self.application().close_specific(self.form)
			self.emit(QtCore.SIGNAL("task_idle"))
	
	def on_ctf_closed(self):
		if self.gui != None:
			self.gui = None
			self.emit(QtCore.SIGNAL("gui_exit")) #
		
	def on_form_close(self):
		# this is to avoid a task_idle signal, which would be incorrect if e2boxer is running
		if self.gui == None:
			self.emit(QtCore.SIGNAL("task_idle"))
		else: pass
		
class E2CTFGuiTaskGeneral(E2CTFGuiTask):
	''' This one uses the names in the e2ctf.parms to generate it's table of options, not the particles in the particles directory
	'''
	documentation_string = "Write me"
	def __init__(self,application):
		E2CTFGuiTask.__init__(self,application)

	def get_params(self):
		params = []		
		params.append(ParamDef(name="blurb",vartype="text",desc_short="",desc_long="",property=None,defaultunits=E2CTFGuiTaskGeneral.documentation_string,choices=None))
		
		names = self.get_names_with_parms()
		n = [l[0] for l in names]
		params.append(self.get_ctf_param_table(n))
		return params
	
	def get_default_ctf_options(self,params):
		'''
		These are the options required to run pspec_and_ctf_fit in e2ctf.py
		'''
		
		if not params.has_key("filenames") and len(params["filenames"]) == 0:
			print "There are no filenames" # this shouldn't happen
			return None
		
		
		options = EmptyObject()

		selected_filenames = params["filenames"]
		
		filenames = []
		names = self.get_names_with_parms()
		for name in names:
			if name[0] in selected_filenames:
				filenames.append(name[1])
		options.filenames = filenames
#		
		return options

class CTFReportTask(E2CTFWorkFlowTask):
	
	documentation_string = "This tool is for displaying the currently determined CTF parameters for the particles located in the project particle directory."
	
	def __init__(self,application):
		E2CTFWorkFlowTask.__init__(self,application)
		self.window_title = "Project particles"

	def get_params(self):
		params = []
		params.append(ParamDef(name="blurb",vartype="text",desc_short="",desc_long="",property=None,defaultunits=CTFReportTask.documentation_string,choices=None))
		
		params.append(self.get_ctf_param_table(self.get_ctf_project_names()))
		return params

	def write_db_entry(self,key,value):
		pass


class MicrographCCDImportTask(WorkFlowTask):	
	documentation_string = "Use this tool for importing flat files into the raw_data directory in the project database. Files that you import in this way will be automatically added the list of files in the project."
	
	def __init__(self,application):
		WorkFlowTask.__init__(self,application)
		self.window_title = "Import micrographs"
		self.thumb_shrink = -1
	def get_params(self):
		params = []
		project_db = db_open_dict("bdb:project")
		params.append(ParamDef(name="blurb",vartype="text",desc_short="Importing image data",desc_long="",property=None,defaultunits=MicrographCCDImportTask.documentation_string,choices=None))
		params.append(ParamDef(name="import_micrograph_ccd_files",vartype="url",desc_short="File names",desc_long="The raw data from which particles will be extracted and ultimately refined to produce a reconstruction",property=None,defaultunits=[],choices=[]))
		pinvert = ParamDef(name="invert",vartype="boolean",desc_short="Invert",desc_long="Tick this if you want eman2 to invert your images while importing",property=None,defaultunits=False,choices=None)
		pxray = ParamDef(name="xraypixel",vartype="boolean",desc_short="X-ray pixel",desc_long="Tick this if you want eman2 to automatically filter out X-ray pixels while importing",property=None,defaultunits=False,choices=None)
		pthumbnail = ParamDef(name="thumbs",vartype="boolean",desc_short="Thumbnails",desc_long="Tick this if you want eman2 to automatically generate thumbnails for your images. This will save time at later stages in the project",property=None,defaultunits=True,choices=None)
		
		params.append([pinvert,pxray,pthumbnail])
		
		db_close_dict("bdb:project")
		return params
	
	def on_form_ok(self,params):
		for k,v in params.items():
			if k == "import_micrograph_ccd_files":
				self.do_import(params)
			else:
				self.write_db_entry(k,v)
		
		
		
		
		self.application().close_specific(self.form)
		self.form = None
	
		self.emit(QtCore.SIGNAL("task_idle"))

	def do_import(self,params):
		filenames = params["import_micrograph_ccd_files"]
		
			
		no_dir_names = [get_file_tag(name) for name in filenames]
		
		for name in filenames:
			if name.find("bdb:rawdata#") != -1:
				print "you can't import files that are already in the project raw data directory,",name,"is invalid"
				return
		
		for name in no_dir_names:
			if no_dir_names.count(name) > 1:
				print "you can't use images with the same name (",name,")"
				return
		
		project_db = db_open_dict("bdb:project")
		
		current_project_files = project_db.get("global.micrograph_ccd_filenames",dfl=[])
		cpft = [get_file_tag(file) for file in current_project_files]
		
		# get the number of process operation - the progress dialog reflects image copying and image processing operations
		num_processing_operations = 2 # there is atleast a copy and a disk write
		if params["invert"]: num_processing_operations += 1
		if params["xraypixel"]: num_processing_operations += 1
		if params["thumbs"]:num_processing_operations += 1
		
		
		# now add the files to db (if they don't already exist
		progress = EMProgressDialogModule(self.application(),"Importing files into database...", "Abort import", 0, len(filenames)*num_processing_operations,None)
		progress.qt_widget.show()
		i = 0
		cancelled = False # if the user cancels the import then we must act
		cancelled_dbs = []
		for name in filenames:
			
			tag = get_file_tag(name)
			if tag in cpft:
				print "can't import images have identical tags to those already in the database"
				continue
			
			
			db_name = "bdb:raw_data#"+tag
			if db_check_dict(db_name):
				print "there is already a raw_data database entry for",tag
				continue
			else:
				e = EMData()
				e.read_image(name,0)
				i += 1
				progress.qt_widget.setValue(i)	
				self.application().processEvents()
				e.set_attr("disk_file_name",name)
				
				if params["invert"]:
					e.mult(-1)
					i += 1
					progress.qt_widget.setValue(i)
					self.application().processEvents()
				
				if params["xraypixel"]:
					e.process_inplace("threshold.clampminmax.nsigma",{"nsigma":4,"tomean":True})
					i += 1
					progress.qt_widget.setValue(i)
					self.application().processEvents()
				
				e.write_image(db_name,0)
				cancelled_dbs.append(db_name)
				i += 1
				progress.qt_widget.setValue(i)
				self.application().processEvents()
				current_project_files.append(db_name)
				
				if params["thumbs"]:
					shrink = self.get_thumb_shrink(e.get_xsize(),e.get_ysize())
					thumb = e.process("math.meanshrink",{"n":shrink})
					set_idd_image_entry(db_name,"image_thumb",thumb) # boxer uses the full name
					i += 1
					progress.qt_widget.setValue(i)
					self.application().processEvents()
					
				if progress.qt_widget.wasCanceled():
					cancelled = True
					for data_db in cancelled_dbs: # policy here is to remove only the raw data dbs - the e2boxer thumbnails are tiny and I don't have time...
						db_remove_dict(data_db)
					break
			
				
		progress.qt_widget.setValue(len(filenames))
		progress.qt_widget.close()
		
		if not cancelled:
			project_db["global.micrograph_ccd_filenames"] = current_project_files
			db_close_dict("bdb:project")
		
	def get_thumb_shrink(self,nx,ny):
		if self.thumb_shrink == -1:
			shrink = 1
			inx =  nx/2
			iny =  ny/2
			while ( inx >= 128 and iny >= 128):
				inx /= 2
				iny /= 2
				shrink *= 2
		
			self.thumb_shrink=shrink
		
		return self.thumb_shrink
			
	def on_import_cancel(self):
		print "canceled"
		
	
class MicrographCCDTask(WorkFlowTask):
	
	documentation_string = "This is a list of micrographs or CCD frames that you choose to associate with this project. You can add and remove file names by editing the text entries directly and or by using the browse and clear buttons. In addition to being able to specify images that are stored on your hard drive in the usual way, you can also choose images from EMAN2 style databases."
	
	
	def __init__(self,application):
		WorkFlowTask.__init__(self,application)
		self.window_title = "Project micrographs"

	def get_params(self):
		params = []
		project_db = db_open_dict("bdb:project")
		params.append(ParamDef(name="blurb",vartype="text",desc_short="Raw image data",desc_long="",property=None,defaultunits=MicrographCCDTask.documentation_string,choices=None))
		params.append(ParamDef(name="global.micrograph_ccd_filenames",vartype="url",desc_short="File names",desc_long="The raw data from which particles will be extracted and ultimately refined to produce a reconstruction",property=None,defaultunits=project_db.get("global.micrograph_ccd_filenames",dfl=[]),choices=[]))
		
		db_close_dict("bdb:project")
		return params

	def write_db_entry(self,key,value):
		if key == "global.micrograph_ccd_filenames":
			if value != None:
				stipped_input = [get_file_tag(name) for name in value]
				for name in stipped_input:
					if stipped_input.count(name) > 1:
						print "you can't use images with the same file tag (",name,")"
						return

				new_names = []
		
				# now just update the static list of project file names
				e = EMData()
				read_header_only = True
				for i,name in enumerate(value):
					
					if os.path.exists(name) or db_check_dict(name):
						try:
							a = e.read_image(name,0,read_header_only)
						except: continue
						
						new_names.append(name)
						
				project_db = db_open_dict("bdb:project")
				project_db["global.micrograph_ccd_filenames"] = new_names
				db_close_dict("bdb:project")
		else:
			print "unknown key:",key,"this object is",self
					


class RunE2BoxerTask(WorkFlowTask):
	'''
	A generalized form for running e2boxer tasks
	'''
	

class SPRInitTask(WorkFlowTask):
	'''
	A class that manages the initialization component of a Single Particle
	Reconstruction workflow
	'''
	
	# stolen from wikipedia
	documentation_string = "In physics, in the area of microscopy, single particle reconstruction is a technique in which large numbers of images (10,000 - 1,000,000) of ostensibly identical individual molecules or macromolecular assemblies are combined to produce a 3 dimensional reconstruction. This is a complementary technique to crystallography of biological molecules. As molecules/assembies become larger, it becomes more difficult to prepare high resolution crystals. For single particle reconstruction, the opposite is true. Larger objects actually improve the resolution of the final structure. In single particle reconstruction, the molecules/assemblies in solution are prepared in a thin layer of vitreous (glassy) ice, then imaged on an electron cryomicroscope (see Transmission electron microscopy). Images of individual molecules/assemblies are then selected from the micrograph and then a complex series of algorithms is applied to produce a full volumetric reconstruction of the molecule/assembly. In the 1990s this technique was limited to roughly 2 nm resolution, providing only gross features of the objects being studied. However, recent improvements in both microscope technology as well as available computational capabilities now make 0.5 nm resolution possible."
	
	def __init__(self,application):
		WorkFlowTask.__init__(self,application)
		self.window_title = "Project information"
	def get_params(self):
		params = []
		project_db = db_open_dict("bdb:project")
		#params.append(ParamDef(name="global.micrograph_ccd_filenames",vartype="url",desc_short="File names",desc_long="The raw data from which particles will be extracted and ultimately refined to produce a reconstruction",property=None,defaultunits=db_entry("global.micrograph_ccd_filenames","bdb:project",[]),choices=[]))
		params.append(ParamDef(name="blurb",vartype="text",desc_short="SPR",desc_long="Information regarding this task",property=None,defaultunits=SPRInitTask.documentation_string,choices=None))
		
		papix = ParamDef(name="global.apix",vartype="float",desc_short="A/pix for project",desc_long="The physical distance represented by the pixel spacing",property=None,defaultunits=project_db.get("global.apix",dfl=1.1),choices=None)
		pvolt = ParamDef(name="global.microscope_voltage",vartype="float",desc_short="Microscope voltage",desc_long="The operating voltage of the microscope",property=None,defaultunits=project_db.get("global.microscope_voltage",dfl=300),choices=None)
		pcs = ParamDef(name="global.microscope_cs",vartype="float",desc_short="Microscope Cs",desc_long="Microscope spherical aberration constant",property=None,defaultunits=project_db.get("global.microscope_cs",dfl=2.0),choices=None)
		pncp = ParamDef(name="global.num_cpus",vartype="int",desc_short="Number of CPUs",desc_long="Number of CPUS available for the project to use",property=None,defaultunits=project_db.get("global.num_cpus",dfl=num_cpus()),choices=None)
		mem = memory_stats()
		pmem = ParamDef(name="global.memory_available",vartype="float",desc_short="Memory usage ("+str(mem[0])+ " Gb total)",desc_long="The total amount of system memory you want to make available to the project in gigabytes",property=None,defaultunits=project_db.get("global.memory_available",dfl=mem[1]),choices=None)
		params.append(papix)
		params.append(pvolt)
		params.append(pcs)
		params.append(pncp)
		params.append(pmem)
		db_close_dict("bdb:project")
		return params

	def write_db_entry(self,key,value):
		WorkFlowTask.write_db_entry(self,key,value)
		
		
if __name__ == '__main__':
	
	from emapplication import EMStandAloneApplication
	em_app = EMStandAloneApplication()
	sprinit = SPRInitTask(em_app)
	window = sprinit.run_form() 
	
	#em_app.show()
	em_app.execute()	