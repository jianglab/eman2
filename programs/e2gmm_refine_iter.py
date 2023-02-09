#!/usr/bin/env python
# Muyuan Chen 2022-12
from EMAN2 import *
from EMAN2_utils import *
import numpy as np
from sklearn.cluster import KMeans

#def run(x):
	#print(x)
	
def main():

	usage=" "
	parser = EMArgumentParser(usage=usage,version=EMANVERSION)
	parser.add_argument("--path", type=str,help="path", default=None)
	parser.add_argument("--sym", type=str,help="sym", default="c1")
	parser.add_argument("--initpts", type=str,help="initial points as pdb", default=None)
	parser.add_argument("--niter", type=int,help="iteration", default=5)
	parser.add_argument("--startres", type=float,help="starting resolution", default=4)
	parser.add_argument("--minres", type=float,help="min resolution", default=25)
	parser.add_argument("--maxres", type=float,help="max resolution", default=-1)
	parser.add_argument("--npt", type=int,help="number of points", default=2000)
	parser.add_argument("--mask", type=str,help="mask file", default=None)
	parser.add_argument("--expandsym", type=str,help="symmetry expansion", default=None)
	parser.add_argument("--masksigma", action="store_true", default=False ,help="mask the sigma of Gaussian")
	parser.add_argument("--maskamp", action="store_true", default=False ,help="mask the amplitude of Gaussian")
	parser.add_argument("--maskpp", type=str,help="mask file", default=None)

	parser.add_argument("--startiter", type=int,help="start iter", default=1)
	parser.add_argument("--batchsize", type=int,help="number of particles in each batch", default=16)
	parser.add_argument("--chunksize", type=int,help="number of particles in each gmm_batch process", default=20000)
	
	parser.add_argument("--ppid", type=int, help="Set the PID of the parent process, used for cross platform PPID",default=-1)

	(options, args) = parser.parse_args()
	
	logid=E2init(sys.argv)
	fname=args[0]
	er=EMData(fname,0, True)
	oldpath=os.path.dirname(fname)
	
	c=[i for i in fname if i.isdigit()]
	itr=int(''.join(c[-2:]))
	print(f"refinement path {oldpath}, iteration {itr}.")
	res=options.startres
	
	if options.path==None: 
		path=options.path=num_path_new("gmm_")
		
		fsc=np.loadtxt(f"{oldpath}/fsc_masked_{itr:02d}.txt")
		np.savetxt(f"{path}/fsc_masked_00.txt", fsc)
		fsc=np.loadtxt(f"{oldpath}/fsc_maskedtight_{itr:02d}.txt")
		np.savetxt(f"{path}/fsc_maskedtight_00.txt", fsc)
		for ieo, eo in enumerate(["even", "odd"]):
			if os.path.isfile(f"{oldpath}/ptcls_{itr:02d}_{eo}.lst"):
				run(f"e2proclst.py {oldpath}/ptcls_{itr:02d}_{eo}.lst --create {path}/ptcls_00_{eo}.lst")
			else:
				run(f"e2proclst.py {oldpath}/ptcls_{itr:02d}.lst --create {path}/ptcls_00_{eo}.lst --getclass {ieo}")
				
			if options.expandsym:
				run(f"e2proclst.py {path}/ptcls_00_{eo}.lst --sym {options.expandsym}")
			run(f"e2proc3d.py {oldpath}/threed_{itr:02d}_{eo}.hdf {path}/threed_00_{eo}.hdf --process filter.lowpass.gauss:cutoff_freq={1./options.startres:.3f} --process normalize.edgemean")
	
	else:
		print(f"writing in existing path {options.path}")
		path=options.path
		
	
	if options.initpts:
		ext=options.initpts[-3:]
		if os.path.isfile(f"{options.initpts[:-4]}_even.{ext}"):
			print("using even/odd pdb")
			for ieo, eo in enumerate(["even", "odd"]):
				os.system(f"cp {options.initpts[:-4]}_{eo}.{ext} {path}/gmm_init_{eo}.{ext}")
		else:
			for ieo, eo in enumerate(["even", "odd"]):
				os.system("cp {} {}/gmm_init_{}.{}".format(options.initpts, path,eo,ext))
		
	options.cmd=' '.join(sys.argv)
	fm=f"{options.path}/0_gmm_params.json"
	js=js_open_dict(fm)
	js.update(vars(options))
	js.close()	

	etcpp=""
	if options.maskpp:
		etcpp+=" --mask {}".format(options.maskpp)
		
	for itr in range(options.startiter, options.startiter+options.niter):
		it0=itr-1
		
		for ieo, eo in enumerate(["even", "odd"]):

			run(f"e2project3d.py {path}/threed_{it0:02d}_{eo}.hdf --outfile {path}/projections_{eo}.hdf --orientgen=eman:delta=4 --parallel=thread:12")
			

			#else:
			if itr==options.startiter:
				
				if options.initpts:
					run(f"e2gmm_refine_new.py --ptclsin {path}/projections_{eo}.hdf --model {path}/gmm_init_{eo}.{ext} --maxres {res} --modelout {path}/model_{it0:02d}_{eo}.txt --niter 40 --trainmodel")
					
				else:
					run(f"e2segment3d.py {path}/threed_{it0:02d}_{eo}.hdf --pdb {path}/model_{it0:02d}_{eo}.pdb --process=segment.kmeans:nseg={options.npt}:thr=4")
					
					run(f"e2gmm_refine_new.py --ptclsin {path}/projections_{eo}.hdf --model {path}/model_{it0:02d}_{eo}.pdb --maxres {res} --modelout {path}/model_{it0:02d}_{eo}.txt --niter 40 --trainmodel")
		
			else:
				run(f"e2gmm_refine_new.py --ptclsin {path}/projections_{eo}.hdf --model {path}/model_{itr-2:02d}_{eo}.txt --maxres {res} --modelout {path}/model_{it0:02d}_{eo}.txt --niter 40 --trainmodel")
	
			pts=np.loadtxt(f"{path}/model_{it0:02d}_{eo}.txt")
			if options.mask:
				msk=EMData(options.mask)
				
				## read selected Gaussian from mask file
				m=msk.numpy().copy()
				if np.min(m)<1e3 and options.masksigma:
					m=(m*.75)+.25
				p=pts[:,:3].copy()
				p=p[:,::-1]
				p[:,:2]*=-1
				p=(p+.5)*msk["nx"]

				o=np.round(p).astype(int)
				v=m[o[:,0], o[:,1], o[:,2]]
				imsk=v.astype(float)
				if options.masksigma:
					iz=imsk==0
					imsk[iz]=1
					imsk=1./imsk
					imsk[iz]=0
					pts[:,4]=pts[:,4]*imsk
				elif options.maskamp:
					pts[:,3]=pts[:,3]*imsk
					
				np.savetxt(f"{path}/model_{it0:02d}_{eo}.txt", pts)
			
			run(f'e2gmm_batch.py "e2gmm_refine_new.py --model {path}/model_{it0:02d}_{eo}.txt  --ptclsin {path}/ptcls_{it0:02d}_{eo}.lst  --ptclsout {path}/ptcls_{itr:02d}_{eo}.lst --align --maxres {res} --minres {options.minres} --batchsz {options.batchsize}" --niter 0 --batch {options.chunksize}')
			
			run(f"e2spa_make3d.py --input {path}/ptcls_{itr:02d}_{eo}.lst --output {path}/threed_{itr:02d}_{eo}.hdf --parallel thread:32 --keep .9 --sym {options.sym}")
	   
			run(f"e2proc3d.py {path}/threed_{itr:02d}_{eo}.hdf {path}/threed_raw_{eo}.hdf")
			
			#run(f"e2proc3d.py {path}/threed_{itr:02d}_{eo}.hdf {path}/threed_{itr:02d}_{eo}.hdf --multfile mask_foc0_soft.hdf")
			
		run(f"e2refine_postprocess.py --even {path}/threed_{itr:02d}_even.hdf --res {res} --tophat localwiener --sym {options.sym} --thread 32 --setsf sf.txt --align  {etcpp}")
		
		fsc=np.loadtxt("{}/fsc_maskedtight_{:02d}.txt".format(options.path, itr))
		fi=fsc[:,1]<0.1
		nyq=2.0*er["apix_x"]
		try: 
			res=.9/fsc[fi, 0][0]
		except:
			print("resolution approaching Nyquist !?")
			res=nyq
		
		if options.maxres>0:res=max(res, options.maxres)
		if res<nyq: res=nyq
		
	E2end(logid)
	
	
if __name__ == '__main__':
	main()
	

