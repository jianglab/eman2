#!/usr/bin/env python

#
# Author: Steven Ludtke, 10/29/2008 (sludtke@bcm.edu)
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
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  2111-1307 USA
#
#

# e2ctf.py  10/29/2008 Steven Ludtke
# This is a program for determining CTF parameters and (optionally) phase flipping images

from EMAN2 import *
from optparse import OptionParser
from math import *
import time
import os
import sys

debug=False

def main():
	global debug
	progname = os.path.basename(sys.argv[0])
	usage = """%prog [options] <input stack/image> ...
	
Various CTF-related operations on images. Input particles should be unmasked and unfiltered. A minimum of ~20% padding around the
particles is required for background extraction, even if this brings the edge of another particle into the box in some cases.
Particles should be reasonably well centered. Can also optionally phase flip and Wiener filter particles. Wiener filtration comes
after phase-flipping, so if phase flipping is performed Wiener filtered particles will also be phase-flipped. Note that both
operations are performed on oversampled images if specified."""

	parser = OptionParser(usage=usage,version=EMANVERSION)

	parser.add_option("--gui",action="store_true",help="Start the GUI for interactive fitting",default=False)
	parser.add_option("--bgmask",type="int",help="Compute the background power spectrum from the edge of the image, specify a mask radius in pixels which would largely mask out the particles",default=0)
	parser.add_option("--apix",type="float",help="Angstroms per pixel for all images",default=0)
	parser.add_option("--voltage",type="float",help="Microscope voltage in KV",default=0)
	parser.add_option("--cs",type="float",help="Microscope Cs (spherical aberation)",default=0)
	parser.add_option("--ac",type="float",help="Amplitude contrast (percentage, default=10)",default=10)
	parser.add_option("--nonorm",action="store_true",help="Suppress per image real-space normalization",default=False)
	parser.add_option("--smooth",action="store_true",help="Smooth the background (running-average of the log) and adjust it at the zeroes of the CTF",default=False)
	parser.add_option("--phaseflip",action="store_true",help="Perform phase flipping after CTF determination and writes to specified file.",default=False)
	parser.add_option("--wiener",action="store_true",help="Wiener filter (optionally phaseflipped) particles.",default=False)
	parser.add_option("--oversamp",type="int",help="Oversampling factor",default=1)
	parser.add_option("--debug",action="store_true",default=False)

	(options, args) = parser.parse_args()
	if len(args)<1 : parser.error("Input image required")

	if options.voltage==0 : parser.error("Please specify voltage")
	if options.cs==0 : parser.error("Please specify Cs")
	if options.apix==0 : parser.error("Please specify A/Pix")
		
	debug=options.debug

#	if options.oversamp>1 : options.apix/=float(options.oversamp)

	img_sets=[]

	project=db_open_dict("bdb:project")
	parms=db_open_dict("bdb:e2ctf.parms")
	

	for filename in args:
		name=get_file_tag(filename)

		# compute the power spectra
		if debug : print "Processing ",filename
		im_1d,bg_1d,im_2d,bg_2d=powspec_with_bg(filename,radius=options.bgmask,edgenorm=not options.nonorm,oversamp=options.oversamp)
		ds=1.0/(options.apix*im_2d.get_ysize())
		if options.smooth : bg_1d=smooth_bg(bg_1d,ds)

		Util.save_data(0,ds,bg_1d,"ctf.bgb4.txt")
		
		# Fit the CTF parameters
		if debug : print "Fit CTF"
		ctf=ctf_fit(im_1d,bg_1d,im_2d,bg_2d,options.voltage,options.cs,options.ac,options.apix,bgadj=options.smooth)
		parms[name]=ctf.to_string()

		if debug:
			Util.save_data(0,ds,im_1d,"ctf.fg.txt")
			Util.save_data(0,ds,bg_1d,"ctf.bg.txt")
			Util.save_data(0,ds,ctf.snr,"ctf.snr.txt")
			
		img_sets.append((filename,ctf,im_1d,bg_1d,im_2d,bg_2d))

	if options.gui :
		gui=GUIctf(img_sets)
		gui.run()

	if debug : print "Phase flipping / Wiener filtration"
	if options.phaseflip or options.wiener:
		for filename in args:
			if debug: print "Processing ",filename

			if options.phaseflip: phaseout="bdb:ctf.flip."+name
			else: phaseout=None
		
			if options.wiener: wienerout="bdb:ctf.wiener."+name
			else : wienerout=None

			if phaseout : print "Phase image out: ",phaseout,"\t",
			if wienerout : print "Wiener image out: ",wienerout,
			print ""
			ctf=EMAN2Ctf()
			ctf.from_string(parms[name])
			process_stack(filename,phaseout,wienerout,not options.nonorm,options.oversamp,ctf)

def process_stack(stackfile,phaseflip=None,wiener=None,edgenorm=True,oversamp=1,default_ctf=None):
	"""Will phase-flip and/or Wiener filter particles in a file based on their stored CTF parameters.
	phaseflip should be the path for writing the phase-flipped particles
	wiener should be the path for writing the Wiener filtered (and possibly phase-flipped) particles
	oversamp will oversample as part of the processing, ostensibly permitting phase-flipping on a wider range of defocus values
	"""
	
	im=EMData(stackfile,0)
	ys=im.get_ysize()*oversamp
	ys2=im.get_ysize()
	n=EMUtil.get_image_count(stackfile)
	lctf=None
	
	
	for i in range(n):
		im1=EMData(stackfile,i)
		try: ctf=im1["ctf"]
		except : ctf=default_ctf
		
		if edgenorm : im1.process_inplace("normalize.edgemean")
		if oversamp>1 :
			im1.clip_inplace(Region(-(ys2*(oversamp-1)/2),-(ys2*(oversamp-1)/2),ys,ys))
		
		fft1=im1.do_fft()
			
		if phaseflip :
			if not lctf or not lctf.equal(ctf):
				flipim=fft1.copy()
				ctf.compute_2d_complex(flipim,Ctf.CtfType.CTF_SIGN)
			fft1.mult(flipim)
			out=fft1.do_ift()
			out["ctf"]=ctf
			out.clip_inplace(Region(int(ys2*(oversamp-1)/2.0),int(ys2*(oversamp-1)/2.0),ys2,ys2))
			out.write_image(phaseflip,i)

		if wiener :
			if not lctf or not lctf.equal(ctf):
				wienerim=fft1.copy()
				ctf.compute_2d_complex(wienerim,Ctf.CtfType.CTF_WIENER_FILTER)
#				print wienerim.get_attr_dict()
				display(wienerim)
#				print ctf.to_string()
#				plot(ctf.background)
#				plot(ctf.snr)
#				plot(ctf.compute_1d(ys,Ctf.CtfType.CTF_WIENER_FILTER))
			fft1.mult(wienerim)
			out=fft1.do_ift()
			out["ctf"]=ctf
			out.clip_inplace(Region(int(ys2*(oversamp-1)/2.0),int(ys2*(oversamp-1)/2.0),ys2,ys2))
			out.write_image(wiener,i)
			
		lctf=ctf



def powspec(stackfile,mask=None,edgenorm=True,):
	"""This routine will read the images from the specified file, optionally edgenormalize,
	optionally apply a mask then compute the average
	2-D power spectrum for the stack. Results returned as a 2-D FFT intensity/0 image"""
	
	n=EMUtil.get_image_count(stackfile)
	
	for i in range(n):
		im=EMData(stackfile,i)
		if edgenorm : im.process_inplace("normalize.edgemean")
		if mask : im*=mask
		imf=im.do_fft()
		imf.ri2inten()
		if i==0: av=imf
		else: av+=imf
	
	av/=(float(n)*av.get_ysize()*av.get_ysize())
	av.set_value_at(0,0,0.0)
#	av.process_inplace("xform.fourierorigin.tocenter")
	
	av.set_complex(1)
	av.set_attr("is_intensity", 1)
	return av

masks={}		# mask cache for background/foreground masking
def powspec_with_bg(stackfile,radius=0,edgenorm=True,oversamp=1):
	"""This routine will read the images from the specified file, optionally edgenormalize,
	then apply a gaussian mask with the specified radius then compute the average 2-D power 
	spectrum for the stack. It will also compute the average 2-D power spectrum using 1-mask + edge 
	apotization to get an appoximate 'background' power spectrum. 2-D results returned as a 2-D FFT 
	intensity/0 image. 1-D results returned as a list of floats.
	
	returns a 4-tuple with spectra for (1d particle,1d background,2d particle,2d background)
	"""
	
	global masks
	
	im=EMData(stackfile,0)
	ys=im.get_ysize()*oversamp
	ys2=im.get_ysize()
	n=EMUtil.get_image_count(stackfile)
	
	# set up the inner and outer Gaussian masks
	try:
		mask1,ratio1,mask2,ratio2=masks[(ys,radius)]
	except:
		mask1=EMData(ys2,ys2,1)
		mask1.to_one()
		mask1.process_inplace("mask.gaussian",{"outer_radius":radius})
		mask2=mask1.copy()*-1+1
#		mask1.process_inplace("mask.decayedge2d",{"width":4})
		mask2.process_inplace("mask.decayedge2d",{"width":4})
		mask1.clip_inplace(Region(-(ys2*(oversamp-1)/2),-(ys2*(oversamp-1)/2),ys,ys))
		mask2.clip_inplace(Region(-(ys2*(oversamp-1)/2),-(ys2*(oversamp-1)/2),ys,ys))
		ratio1=mask1.get_attr("square_sum")/(ys*ys)	#/1.035
		ratio2=mask2.get_attr("square_sum")/(ys*ys)
		masks[(ys,radius)]=(mask1,ratio1,mask2,ratio2)
	
	for i in range(n):
		im1=EMData(stackfile,i)
		
		if edgenorm : im1.process_inplace("normalize.edgemean")
		if oversamp>1 :
			im1.clip_inplace(Region(-(ys2*(oversamp-1)/2),-(ys2*(oversamp-1)/2),ys,ys))
		
		im2=im1.copy()

		im1*=mask1
		imf=im1.do_fft()
		imf.ri2inten()
		if i==0: av1=imf
		else: av1+=imf
	
		im2*=mask2
		imf=im2.do_fft()
		imf.ri2inten()
		if i==0: av2=imf
		else: av2+=imf
		
	
	av1/=(float(n)*av1.get_ysize()*av1.get_ysize()*ratio1)
	av1.set_value_at(0,0,0.0)
	av1.set_complex(1)
	av1.set_attr("is_intensity", 1)

	av2/=(float(n)*av2.get_ysize()*av2.get_ysize()*ratio2)
	av2.set_value_at(0,0,0.0)
	av2.set_complex(1)
	av2.set_attr("is_intensity", 1)

	av1_1d=av1.calc_radial_dist(av1.get_ysize()/2,0.0,1.0,1)
	av2_1d=av2.calc_radial_dist(av2.get_ysize()/2,0.0,1.0,1)

	return (av1_1d,av2_1d,av1,av2)


def bgedge2d(stackfile,width):
	"""This routine will read the images from the specified file, and compute the average
	2-D power spectrum computed using boxes taken from the edge of the image. Returns the
	1-D power spectrum as a list of floats. This is not presently used in e2ctf since it
	produces a heavily downsampled background curve, and is provided only for experimentation."""
	
	n=EMUtil.get_image_count(stackfile)
	av=None
	
	for i in range(n):
		im=EMData(stackfile,i)
		
		xs=im.get_xsize()		# x size of image
		xst=int(floor(xs/ceil(xs/width)))	# step to use so we cover xs with width sized blocks
		
		# Build a list of all boxes around the edge
		boxl=[]
		for x in range(0,xs-xst/2,xst): 
			boxl.append((x,0))
			boxl.append((x,xs-xst))
		for y in range(xst,xs-3*xst/2,xst):
			boxl.append((0,y))
			boxl.append((xs-xst,y))
			
		for b in boxl:
			r=im.get_clip(Region(b[0],b[1],width,width))
			imf=r.do_fft()
			imf.ri2inten()
			if av : av+=imf
			else: av=imf
	
	av/=(n*len(boxl)*width*width)
	av.set_value_at(0,0,0.0)

	av.set_complex(1)
	av.set_attr("is_intensity", 1)
	return av

def smooth_bg(curve,ds):
	"""Smooths a background curve by doing a running average of the log of the curve, ignoring the first few points"""
	
	first=int(.02/ds)	# start at 1/50 1/A
	if first<2 : first=2

	return curve[:first]+[pow(curve[i-1]*curve[i]*curve[i+1],.33333) for i in range(first,len(curve)-2)]+[curve[-2],curve[-1]]
#	return curve[:first]+[pow(curve[i-2]*curve[i-1]*curve[i]*curve[i+1]*curve[i+2],.2) for i in range(first,len(curve)-2)]+[curve[-2],curve[-1]]


def snr_safe(s,n) :
	if s<=0 or n<=0 : return 0.0
	return (s-n)/n

def ctf_fit(im_1d,bg_1d,im_2d,bg_2d,voltage,cs,ac,apix,bgadj=0):
	"""Determines CTF parameters given power spectra produced by powspec_with_bg()
	The bgadj option will result in adjusting the bg_1d curve to better match the zeroes
	of the CTF (in which case bg_1d is modified in place)."""
	# defocus estimation
	global debug
	
	ys=im_2d.get_ysize()
	ds=1.0/(apix*ys)
	
	ctf=EMAN2Ctf()
	ctf.from_dict({"defocus":1.0,"voltage":voltage,"cs":cs,"ampcont":ac,"apix":apix,"dsbg":ds,"background":bg_1d})
	
	
	if debug: dfout=file("ctf.df.txt","w")
	dfbest1=(0,-1.0e20)
	for dfi in range(5,128):			# loop over defocus
		ac=10
		df=dfi/20.0
		ctf.defocus=df
		ctf.ampcont=ac
		cc=ctf.compute_1d(ys,Ctf.CtfType.CTF_AMP)
		st=.04/ds
		norm=0
		for fz in range(len(cc)): 
			if cc[fz]<0 : break
	
		tot,totr=0,0
		for s in range(int(st),ys/2): 
			tot+=(cc[s]**2)*(im_1d[s]-bg_1d[s])
			totr+=cc[s]**4
		#for s in range(int(ys/2)): tot+=(cc[s*ctf.CTFOS]**2)*ps1d[-1][s]/norm
		#for s in range(int(fz/ctf.CTFOS),ys/2): tot+=(cc[s*ctf.CTFOS]**2)*ps1d[-1][s]
		#for s in range(int(fz/ctf.CTFOS),ys/2): tot+=(cc[s*ctf.CTFOS]**2)*snr[s]
		tot/=sqrt(totr)
		#tot/=totr
		if tot>dfbest1[1] : dfbest1=(df,tot)
		try :dfout.write("%1.2f\t%g\n"%(df,tot))
		except : pass
	
	
	
	
	#out=file("bg1d2.txt","w")
	#for a,b in enumerate(bg2): out.write("%1.4f\t%1.5f\n"%(a*ds,b))
	#out.close()

	dfbest=dfbest1
	for dfi in range(-10,10):			# loop over defocus
		df=dfi/100.0+dfbest1[0]
		ctf.defocus=df
		cc=ctf.compute_1d(ys,Ctf.CtfType.CTF_AMP)
		st=.04/ds
		norm=0
		for fz in range(len(cc)): 
			#norm+=cc[fz]**2
			if cc[fz]<0 : break
	
		tot,totr=0,0
		for s in range(int(st),ys/2): 
			tot+=(cc[s]**2)*(im_1d[s]-bg_1d[s])
			totr+=cc[s]**4
		
		tot/=sqrt(totr)
		if tot>dfbest[1] : 
			dfbest=(df,tot)
		if debug : dfout.write("%1.2f\t%g\n"%(df,tot))

	ctf.defocus=dfbest1[0]
	cc=ctf.compute_1d(ys,Ctf.CtfType.CTF_AMP)
	Util.save_data(0,ds,cc,"ctf.ctf.txt")

	if bgadj:
		# now we try to construct a better background based on the CTF zeroes being zero
		bg2=bg_1d[:]
		last=0,1.0
		for x in range(1,len(bg2)-1) : 
			if cc[x]*cc[x+1]<0 :
				# we search +-1 point from the zero for the minimum
				cur=(x,min(im_1d[x]/bg_1d[x],im_1d[x-1]/bg_1d[x-1],im_1d[x+1]/bg_1d[x+1]))
				# once we have a pair of zeros we adjust the background values between
				for xx in range(last[0],cur[0]):
					w=(xx-last[0])/float(cur[0]-last[0])
					bg_1d[xx]=bg2[xx]*(cur[1]*w+last[1]*(1.0-w))
#					print xx,"\t",(cur[1]*w+last[1]*(1.0-w)) #,"\t",cur[1],last[1]
				last=cur
		# cover the area from the last zero crossing to the end of the curve
		for xx in range(last[0],len(bg2)):
			bg_1d[xx]=bg2[xx]*last[1]

	
	ctf.snr=[snr_safe(im_1d[i],bg_1d[i]) for i in range(len(im_1d))]
	ctf.defocus=dfbest[0]

	if 1 : print "Best DF = ",dfbest[0]

	return ctf

try:
	from PyQt4 import QtCore, QtGui, QtOpenGL
	from PyQt4.QtCore import Qt
	from valslider import ValSlider
except:
	print "Warning: PyQt4 must be installed to use the --gui option"
	class dummy:
		pass
	class QWidget:
		"A dummy class for use when Qt not installed"
		def __init__(self,parent):
			print "Qt4 has not been loaded"
	QtGui=dummy()
	QtGui.QWidget=QWidget


class GUIctf(QtGui.QWidget):
	def __init__(self,data):
		"""Implements the CTF fitting dialog using various EMImage and EMPlot2D widgets
		input is a list of (filename,ctf,im_1d,bg_1d,im_2d,bg_2d)
		"""
		try:
			from emimage import EMImageModule
		except:
			print "Cannot import EMAN image GUI objects (emimage,etc.)"
			sys.exit(1)
#		try:
		from emplot2d import EMPlot2DModule
		from emapplication import EMStandAloneApplication
		#except:
			#print "Cannot import EMAN plot GUI objects (is matplotlib installed?)"
			#sys.exit(1)
		
		self.app=EMStandAloneApplication()
		
		QtGui.QWidget.__init__(self,None)
		
		self.data=data
				
		try: self.guiim=EMImageModule(data[0][4],application=self.app)
		except: self.guiim=EMImageModule(application=self.app)
		self.guiplot=EMPlot2DModule(application=self.app)
		
		im_qt_target = self.application.get_qt_emitter(self.guiim)
		plot_qt_target = self.application.get_qt_emitter(self.guiplot)
		
		self.guiim.connect(im_qt_target,QtCore.SIGNAL("mousedown"),self.imgmousedown)
		self.guiim.connect(im_qt_target,QtCore.SIGNAL("mousedrag"),self.imgmousedrag)
		self.guiim.connect(im_qt_target,QtCore.SIGNAL("mouseup")  ,self.imgmouseup)
		self.guiplot.connect(plot_qt_target,QtCore.SIGNAL("mousedown"),self.plotmousedown)
		
		self.guiim.mmode="app"

		# This object is itself a widget we need to set up
		self.hbl = QtGui.QHBoxLayout(self)
		self.hbl.setMargin(0)
		self.hbl.setSpacing(6)
		self.hbl.setObjectName("hbl")
		
		# plot list
		self.setlist=QtGui.QListWidget(self)
		self.setlist.setSizePolicy(QtGui.QSizePolicy.Preferred,QtGui.QSizePolicy.Expanding)
		self.hbl.addWidget(self.setlist)
		
		self.vbl = QtGui.QVBoxLayout()
		self.vbl.setMargin(0)
		self.vbl.setSpacing(6)
		self.vbl.setObjectName("vbl")
		self.hbl.addLayout(self.vbl)
		
		#self.samp = ValSlider(self,(0,5.0),"Amp:",0)
		#self.vbl.addWidget(self.samp)
		
		self.sdefocus=ValSlider(self,(0,5.0),"Defocus:",0)
		self.vbl.addWidget(self.sdefocus)
		
		self.sbfactor=ValSlider(self,(0,500),"B factor:",0)
		self.vbl.addWidget(self.sbfactor)
		
		self.sampcont=ValSlider(self,(0,500),"% AC",0)
		self.vbl.addWidget(self.sampcont)
		
		self.sapix=ValSlider(self,(.2,10),"A/Pix:",2)
		self.vbl.addWidget(self.sapix)
		
		self.svoltage=ValSlider(self,(0,500),"Voltage (kV):",0)
		self.vbl.addWidget(self.svoltage)
		
		self.scs=ValSlider(self,(0,500),"Cs (mm):",0)
		self.vbl.addWidget(self.scs)

		QtCore.QObject.connect(self.sdefocus, QtCore.SIGNAL("valueChanged"), self.newCTF)
		QtCore.QObject.connect(self.sbfactor, QtCore.SIGNAL("valueChanged"), self.newCTF)
		QtCore.QObject.connect(self.sapix, QtCore.SIGNAL("valueChanged"), self.newCTF)
		QtCore.QObject.connect(self.sampcont, QtCore.SIGNAL("valueChanged"), self.newCTF)
		QtCore.QObject.connect(self.svoltage, QtCore.SIGNAL("valueChanged"), self.newCTF)
		QtCore.QObject.connect(self.scs, QtCore.SIGNAL("valueChanged"), self.newCTF)
		QtCore.QObject.connect(self.setlist,QtCore.SIGNAL("currentRowChanged(int)"),self.newSet)

		self.update_data()
		
		self.app.show() # should probably be name "show_all"
		self.show() # this is the troublesome part.... this Widget has to be a module and should register itsefl with the application
		self.app.execute()
		
	def newData(self,data):
		self.data=data
		self.update_data()
		
	def update_data(self):
		"""This will make sure the various widgets properly show the current data sets"""
		self.setlist.clear()
		for i,j in enumerate(self.data):
			self.setlist.addItem(j[0])
			l=len(self.data)

	def newSet(self,val):
		self.sdefocus.setValue(self.data[val][1].defocus)
		self.sbfactor.setValue(self.data[val][1].bfactor)
		self.sapix.setValue(self.data[val][1].apix)
		self.sampcont.setValue(self.data[val][1].ampcont)
		self.svoltage.setValue(self.data[val][1].voltage)
		self.scs.setValue(self.data[val][1].scs)
		
		self.guiim.set_data(self.data[val][4])
		self.curset=val

	def newCTF(self) :
		self.data[self.curset][1].defocus=self.sdefocus.value
		self.data[self.curset][1].bfactor=self.bfactor.value
		self.data[self.curset][1].apix=self.apix.value
		self.data[self.curset][1].ampcont=self.ampcont.value
		self.data[self.curset][1].voltage=self.voltage.value
		self.data[self.curset][1].scs=self.scs.value
#		self.update_data()

	def imgmousedown(self,event) :
		m=self.guiim.scrtoimg((event.x(),event.y()))
		#self.guiim.add_shape("cen",["rect",.9,.9,.4,x0,y0,x0+2,y0+2,1.0])
		
	def imgmousedrag(self,event) :
		m=self.guiim.scrtoimg((event.x(),event.y()))
		
		# box deletion when shift held down
		#if event.modifiers()&Qt.ShiftModifier:
			#for i,j in enumerate(self.boxes):
		
	def imgmouseup(self,event) :
		m=self.guiim.scrtoimg((event.x(),event.y()))
	
	def plotmousedown(self,event) :
		m=self.guiim.scrtoimg((event.x(),event.y()))
	
	def run(self):
		"""If you make your own application outside of this object, you are free to use
		your own local app.exec_(). This is a convenience for ctf-only programs."""
		self.app.exec_()
		
#		E2saveappwin("boxer","imagegeom",self.guiim)
#		try:
#			E2setappval("boxer","imcontrol",self.guiim.inspector.isVisible())
#			if self.guiim.inspector.isVisible() : E2saveappwin("boxer","imcontrolgeom",self.guiim.inspector)
#		except : E2setappval("boxer","imcontrol",False)
		
		return


if __name__ == "__main__":
	main()
