




































































































































































































































































































































































































































































































































































































































































































































































































































































'''0
		#  I am not sure whether what follows is correct.  This part should be recalculated upon restart
		Blockdata["accumulatepw"] = [[],[]]
		ndata = len(projdata)
		for i in range(ndata):
			if(i<first_procid):  iproc = 0 #  This points to correct procid
			else:                iproc = 1
			Blockdata["accumulatepw"][iproc].append([0.0]*200)
		'''












"""1
		#  Inverted Gaussian mask
		invg = model_gauss(Tracker["constants"]["radius"],nx,nx)
		invg /= invg[nx//2,nx//2]
		invg = model_blank(nx,nx,1,1.0) - invg
		"""





'''2
		if(myid == 0):  ndata = EMUtil.get_image_count(partstack)
		else:           ndata = 0
		ndata = bcast_number_to_all(ndata)
		if( ndata < Blockdata["nproc"]):
			if(myid<ndata):
				image_start = myid
				image_end   = myid+1
			else:
				image_start = 0
				image_end   = 1
		else:
			image_start, image_end = MPI_start_end(ndata, Blockdata["nproc"], myid)
		#data = EMData.read_images(stack, range(image_start, image_end))
		if(myid == 0):
			params = read_text_row( paramsname )
			params = [params[i][j]  for i in range(len(params))   for j in range(5)]
		else:           params = [0.0]*(5*ndata)
		params = bcast_list_to_all(params, myid, source_node=Blockdata["main_node"])
		params = [[params[i*5+j] for j in range(5)] for i in range(ndata)]
		'''




















'''3
			if doac:
				if(i<first_procid):  iproc = 0 #  This points to correct procid
				else:                iproc = 1
				Blockdata["accumulatepw"][iproc].append(sig[nv:]+[0.0])  # add zero at the end so for the full size nothing is added.
			'''






















"""4
				for k in range(6,nv):
					tsd.set_value_at(k,i,1.0/(tsd.get_value_at(k,i)/tocp[i]))  # Already inverted
				qt = tsd.get_value_at(6,i)
				for k in range(1,6):
					tsd.set_value_at(k,i,qt)
				"""









































'''5
	particles_on_node = []
	parms_on_node     = []
	for i in range( group_start, group_end ):
		particles_on_node += lpartids[group_reference[i][2]:group_reference[i][3]+1]  #  +1 is on account of python idiosyncrasies
		parms_on_node     += partstack[group_reference[i][2]:group_reference[i][3]+1]


	Blockdata["nima_per_cpu"][procid] = len(particles_on_node)
	#ZZprint("groups_on_thread  ",Blockdata["myid"],procid, Tracker["groups_on_thread"][procid])
	#ZZprint("  particles  ",Blockdata["myid"],Blockdata["nima_per_cpu"][procid],len(parms_on_node))
	'''
"""6
            17            28            57            84    5
            18            14            85            98    6
            19            15            99           113    7
            25            20           114           133    8
            29             9           134           142    9

	"""






































































'''7
		if preshift:
			data[im] = fshift(original_data[im], sx, sy)
			sx = 0.0
			sy = 0.0
		'''










































































































































"""8
	if(Tracker["delta"] == 15.0):  refang = read_text_row("refang15.txt")
	elif(Tracker["delta"] == 7.5):  refang = read_text_row("refang7p5.txt")
	elif(Tracker["delta"] == 3.75):  refang = read_text_row("refang3p75.txt")
	elif(Tracker["delta"] == 1.875):  refang = read_text_row("refang1p875.txt")
	elif(Tracker["delta"] == 0.9375):  refang = read_text_row("refang0p9375.txt")
	elif(Tracker["delta"] == 0.46875):  refang = read_text_row("refang0p46875.txt")
	"""







































































































'''9
			if( method == "DIRECT" ):
				#dss = fshift(ds, xx+sxs, yy+sys)
				dss = fshift(ds, xx+sxs, yy+sys)
				dss.set_attr("is_complex",0)
			else:
				dss = fft(fshift(ds, x+sxs, yy+sys))
				dss,kb = prepi(dss)
			'''



























"""10
	tvol, tweight, trol = recons3d_4nnstruct_MPI(myid = Blockdata["subgroup_myid"], main_node = Blockdata["nodes"][procid], prjlist = data, \
											paramstructure = newparams, refang = refang, delta = Tracker["delta"], CTF = Tracker["constants"]["CTF"],\
											upweighted = False, mpi_comm = mpi_comm, \
											target_size = (2*Tracker["nxinit"]+3), avgnorm = Tracker["avgvaradj"][procid], norm_per_particle = norm_per_particle)
	"""

































































































































































































































































































































'''11
def getangc5(p1,p2):
	from utilities import getfvec
	from math import acos, degrees
	n1 = getfvec(p1[0],p1[1])
	n2 = getfvec(p1[0]+72.,p1[1])
	n3 = getfvec(p1[0]-72.,p1[1])
	n4 = getfvec(p2[0],p2[1])
	return degrees(min(acos(max(min((n1[0]*n4[0]+n1[1]*n4[1]+n1[2]*n4[2]),1.0),-1.0)),\
	acos(max(min((n2[0]*n4[0]+n2[1]*n4[1]+n2[2]*n4[2]),1.0),-1.0)),acos(max(min((n3[0]*n4[0]+n3[1]*n4[1]+n3[2]*n4[2]),1.0),-1.0))))

def difangc5(n4,p1):
	from utilities import getfvec
	from math import acos, degrees
	n1 = getfvec(p1[0],p1[1])
	n2 = getfvec(p1[0]+72.,p1[1])
	n3 = getfvec(p1[0]-72.,p1[1])
	#n4 = getfvec(p2[0],p2[1])
	return degrees(min(acos(max(min((n1[0]*n4[0]+n1[1]*n4[1]+n1[2]*n4[2]),1.0),-1.0)),\
	acos(max(min((n2[0]*n4[0]+n2[1]*n4[1]+n2[2]*n4[2]),1.0),-1.0)),acos(max(min((n3[0]*n4[0]+n3[1]*n4[1]+n3[2]*n4[2]),1.0),-1.0))))
'''


































'''12
def XNumrinit_local(first_ring, last_ring, skip=1, mode="F"):
	"""This function calculates the necessary information for the 2D 
	   polar interpolation. For each ring, three elements are recorded:
	   numr[i*3]:  Radius of this ring
	   numr[i*3+1]: Total number of samples of all inner rings+1
	   		(Or, the beginning point of this ring)
	   numr[i*3+2]: Number of samples of this ring. This number is an 
	   		FFT-friendly power of the 2.
			
	   "F" means a full circle interpolation
	   "H" means a half circle interpolation
	"""
	MAXFFT = 32768
	from math import pi
	skip = 1

	if (mode == 'f' or mode == 'F'): dpi = 2*pi
	else:                            dpi = pi
	numr = []
	lcirc = 1
	for k in range(first_ring, last_ring+1, skip):
		numr.append(k)
		jp = int(dpi * k+0.5)
		ip = 2**(log2(jp)+1)  # two times oversample each ring
		if (k+skip <= last_ring and jp > ip+ip//2): ip=min(MAXFFT,2*ip)
		if (k+skip  > last_ring and jp > ip+ip//5): ip=min(MAXFFT,2*ip)

		numr.append(lcirc)
		numr.append(ip)
		lcirc += ip

	return  numr
'''




































'''13
	if(Blockdata["myid"] <3):
		for kl in range(0,ndat,ndat/2):
			for m in range(0,len(data[kl]),len(data[kl])/3):  sxprint(" DNORM  ",Blockdata["myid"],kl,m, Util.innerproduct(data[kl][m],data[kl][m],mask))
	'''



























































































































































































































'''14
	if(Blockdata["myid"] <3):
		for kl in range(0,ndat,ndat/2):
			for m in range(0,len(data[kl]),len(data[kl])/3):  sxprint(" DNORM  ",Blockdata["myid"],kl,m, Util.innerproduct(data[kl][m],data[kl][m],mask))
	'''









































































































































































































































































































































































































































































"""15
	if Blockdata["bckgnoise"] :
		oneover = []
		nnx = Blockdata["bckgnoise"][0].get_xsize()
		for i in range(len(Blockdata["bckgnoise"])):
			temp = [0.0]*nnx
			for k in range(nnx):
				if( Blockdata["bckgnoise"][i].get_value_at(k) > 0.0):  temp[k] = 1.0/sqrt(Blockdata["bckgnoise"][i].get_value_at(k))
			oneover.append(temp)
		del temp

	accumulatepw = [None]*nima
	norm_per_particle = [None]*nima
	"""































































"""16
		if Blockdata["bckgnoise"]:
			temp = Blockdata["bckgnoise"][dataimage.get_attr("particle_group")]
			bckgn = Util.unroll1dpw(Tracker["nxinit"],Tracker["nxinit"], [temp[i] for i in range(temp.get_xsize())])
		else:
			bckgn = Util.unroll1dpw(Tracker["nxinit"],Tracker["nxinit"], [1.0]*600)
		bckgnoise = bckgn.copy()
		for j in range(Tracker["nxinit"]//2+1,Tracker["nxinit"]):  bckgn[0,j] = bckgn[0,Tracker["nxinit"]-j]
		"""
































































"""17
			lina = np.argsort(xod1)
			xod1 = xod1[lina[::-1]]  # This sorts in reverse order
			xod2 = xod2[lina[::-1]]  # This sorts in reverse order
			np.exp(xod1, out=xod1)
			xod1 /= np.sum(xod1)
			cumprob = 0.0
			lit = len(xod1)
			for j in range(len(xod1)):
				cumprob += xod1[j]
				if(cumprob > Tracker["constants"]["ccfpercentage"]):
					lit = j+1
					break
			"""


















































"""18
			xod1 -= xod1[0]

			lina = np.argwhere(xod1 > Tracker["constants"]["expthreshold"])
			xod1 = xod1[lina]
			xod2 = xod2[lina]
			np.exp(xod1, out=xod1)
			xod1 /= np.sum(xod1)
			cumprob = 0.0
			lit = len(xod1)
			for j in range(len(xod1)):
				cumprob += xod1[j]
				if(cumprob > Tracker["constants"]["ccfpercentage"]):
					lit = j+1
					break
			"""
















































































































"""19
		np.exp(cod1, out=cod1)
		cod1 /= np.sum(cod1)
		cumprob = 0.0
		for j in range(len(cod1)):
			cumprob += cod1[j]
			if(cumprob > Tracker["constants"]["ccfpercentage"]):
				lit = j+1
				break
		"""



















"""20
	# norm correction ---- calc the norm correction per particle
	snormcorr = 0.0
	for kl in range(nima):
		norm_per_particle[kl] = sqrt(norm_per_particle[kl]*2.0)*oldparams[kl][7]/Tracker["avgvaradj"][procid]
		snormcorr            += norm_per_particle[kl]
	Tracker["avgvaradj"][procid] = snormcorr
	mpi_barrier(MPI_COMM_WORLD)
	#  Compute avgvaradj
	Tracker["avgvaradj"][procid] = mpi_reduce( Tracker["avgvaradj"][procid], 1, MPI_FLOAT, MPI_SUM, Blockdata["main_node"], MPI_COMM_WORLD )
	if(Blockdata["myid"] == Blockdata["main_node"]):
		Tracker["avgvaradj"][procid] = float(Tracker["avgvaradj"][procid])/Tracker["nima_per_chunk"][procid]
	else:  Tracker["avgvaradj"][procid] = 0.0
	Tracker["avgvaradj"][procid] = bcast_number_to_all(Tracker["avgvaradj"][procid], Blockdata["main_node"])
	mpi_barrier(MPI_COMM_WORLD)

	#  Compute statistics of smear -----------------
	smax = -1000000
	smin = 1000000
	sava = 0.0
	svar = 0.0
	snum = 0
	for kl in range(nima):
		j = len(newpar[kl][2])
		snum += 1
		sava += float(j)
		svar += j*float(j)
		smax = max(smax, j)
		smin = min(smin, j)
	snum = mpi_reduce(snum, 1, MPI_INT, MPI_SUM, Blockdata["main_node"], MPI_COMM_WORLD)
	sava = mpi_reduce(sava, 1, MPI_FLOAT, MPI_SUM, Blockdata["main_node"], MPI_COMM_WORLD)
	svar = mpi_reduce(svar, 1, MPI_FLOAT, MPI_SUM, Blockdata["main_node"], MPI_COMM_WORLD)
	smax = mpi_reduce(smax, 1, MPI_INT, MPI_MAX, Blockdata["main_node"], MPI_COMM_WORLD)
	smin = mpi_reduce(smin, 1, MPI_INT, MPI_MIN, Blockdata["main_node"], MPI_COMM_WORLD)
	if( Blockdata["myid"] == 0 ):
		from math import sqrt
		sava = float(sava)/snum
		svar = sqrt(max(0.0,(float(svar) - snum*sava**2)/(snum -1)))
		line = strftime("%Y-%m-%d_%H:%M:%S", localtime()) + " =>"
		sxprint(line, "Smear stat  (number of images, ave, sumsq, min, max)):  %7d    %12.3g   %12.3g  %7d  %7d"%(snum,sava,svar,smin,smax))
	"""










































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































"""21
	Number of images :     82     410   20.0%          1.3min          0.8min
	Number of images :    164     410   40.0%          3.0min          1.8min
	Number of images :    246     410   60.0%          5.7min          3.1min
	Number of images :    328     410   80.0%          8.8min          4.4min
	#  Projection and equdist take 50% time, so on the whole run of the program one could
	#    reduce time from 311 to 233, (6h to 4h) if this time was totally eliminated.
	"""

































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































"""22
	Number of images :     82     410   20.0%          1.3min          0.8min
	Number of images :    164     410   40.0%          3.0min          1.8min
	Number of images :    246     410   60.0%          5.7min          3.1min
	Number of images :    328     410   80.0%          8.8min          4.4min
	#  Projection and equdist take 50% time, so on the whole run of the program one could
	#    reduce time from 311 to 233, (6h to 4h) if this time was totally eliminated.
	"""




















































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































"""23
	Number of images :     82     410   20.0%          1.3min          0.8min
	Number of images :    164     410   40.0%          3.0min          1.8min
	Number of images :    246     410   60.0%          5.7min          3.1min
	Number of images :    328     410   80.0%          8.8min          4.4min
	#  Projection and equdist take 50% time, so on the whole run of the program one could
	#    reduce time from 311 to 233, (6h to 4h) if this time was totally eliminated.
	"""












































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































"""24
	Number of images :     82     410   20.0%          1.3min          0.8min
	Number of images :    164     410   40.0%          3.0min          1.8min
	Number of images :    246     410   60.0%          5.7min          3.1min
	Number of images :    328     410   80.0%          8.8min          4.4min
	#  Projection and equdist take 50% time, so on the whole run of the program one could
	#    reduce time from 311 to 233, (6h to 4h) if this time was totally eliminated.
	"""






























































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































"""25
			if(Blockdata["myid"] == Blockdata["main_node"]):
				fff = read_text_file(os.path.join(initdir,"driver_%03d.txt"%(Tracker["mainiteration"])))
			else:
				fff = []
			fff = bcast_list_to_all(fff, Blockdata["myid"], source_node=Blockdata["main_node"])
			keepgoing = AI_continuation(fff)
			"""

































































































































































































































