#!/usr/bin/env python
# Muyuan Chen 2023-09
from EMAN2 import *
import numpy as np
from scipy.spatial import KDTree
import scipy.sparse as scipysparse
from Bio.PDB import *
import protein_constant as e2pc

floattype=np.float32
if "CUDA_VISIBLE_DEVICES" not in os.environ:
	# so we can decide which gpu to use with environmental variable
	os.environ["CUDA_VISIBLE_DEVICES"]='0' 
	
os.environ["TF_FORCE_GPU_ALLOW_GROWTH"]='true' 
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2' #### reduce log output
import tensorflow as tf

def get_info(atom, getstr=False, include_id=False):
	if getstr:
		ret="{}_{:05d}_{}".format(*get_info(atom, getstr=False, include_id=include_id))
	else:
		ret=(atom.parent.parent.id, atom.parent.id[1], atom.parent.resname)
		if include_id:
			ret+=(atom.id,)
	
	return ret
		
def build_decoder(p0, options):
	kinit=tf.keras.initializers.RandomNormal(0,1e-5)

	layers=[
		# tf.keras.layers.Dense(64, activation="relu"),
		tf.keras.layers.Dense(128, activation="relu"),
		tf.keras.layers.Dense(256, activation="relu"),
		tf.keras.layers.Dropout(.1),
		tf.keras.layers.Dense(512, activation="relu"),
		tf.keras.layers.Dropout(.2),
		# tf.keras.layers.BatchNormalization(),
		tf.keras.layers.Dense(np.prod(p0.shape), activation="linear", kernel_initializer=kinit),
		tf.keras.layers.Reshape(p0.shape),
		]
	
	x0=tf.keras.Input(shape=(options.nmid))
	
	y0=x0
	for l in layers:
		y0=l(y0)
	y0=y0+p0
	model=tf.keras.Model(x0, y0)
	
	return model
	
def calc_bond(pout, bond):
	
	px=tf.gather(pout, bond[:,0], axis=1)[:,:,:3]
	py=tf.gather(pout, bond[:,1], axis=1)[:,:,:3]
	dst=tf.math.sqrt(tf.nn.relu(tf.reduce_sum((px-py)**2, axis=2)))
	return dst
	
def calc_angle(pout, ang):
	
	p0=tf.gather(pout, ang[:,0], axis=1)[:,:,:3]
	p1=tf.gather(pout, ang[:,1], axis=1)[:,:,:3]
	p2=tf.gather(pout, ang[:,2], axis=1)[:,:,:3]
	b0=p0-p1
	b1=p2-p1
	ang=tf.reduce_sum(b0*b1, axis=2)
	n0=tf.linalg.norm(b0, axis=2)*tf.linalg.norm(b1, axis=2)
	ang=tf.math.divide_no_nan(ang, n0)
	ang=tf.minimum(tf.maximum(ang, -0.999),.999)
	ang=tf.math.acos(ang)*180/np.pi

	return ang
		
def calc_dihedral_tf(pt):
	## pt.shape: (batch, bonds, 4, 3)
	a=pt[:,:,1:]-pt[:,:,:-1]
	v1=tf.linalg.cross(a[:,:,0], a[:,:,1])
	n1=tf.math.sqrt(tf.reduce_sum(v1*v1, axis=2))[:,:,None]
	v1=tf.math.divide_no_nan(v1, n1)

	v2=tf.linalg.cross(a[:,:,1], a[:,:,2])
	n2=tf.math.sqrt(tf.reduce_sum(v2*v2, axis=2))[:,:,None]
	v2=tf.math.divide_no_nan(v2, n2)

	sgn=tf.sign(tf.reduce_sum(v1*a[:,:,2], axis=2))
	sgn=sgn+tf.cast(sgn==0, np.float32)
	cs=tf.reduce_sum(v1*v2, axis=2)
	n3=tf.math.sqrt(tf.reduce_sum(v1*v1, axis=2)*tf.reduce_sum(v2*v2, axis=2))
	cos=tf.math.divide_no_nan(cs, n3)
	cos=tf.minimum(tf.maximum(cos, -.99999),.99999)
	sin=tf.sqrt(1-cos**2)*sgn
	deg=tf.math.atan2(sin,cos)*180/np.pi
	return deg 


def eval_rama(phi, psi, options):
	ang=tf.stack([phi,psi], axis=0)*np.pi/180
	ang=tf.transpose(ang,(1,2,0))
	# print(ang.shape)
	ret=tf.zeros((ang.shape[0],ang.shape[1]), dtype=floattype)
	for typ in options.dih_type:
		gr=e2pc.ramachandran[typ]
		ang1=ang
		ang1=tf.reshape(ang1,(-1, ang1.shape[2]))[:,None,:]
		d=ang1-gr[:,:2]
		d=tf.reduce_sum(d**2, axis=2)

		d=tf.exp(-d*abs(gr[:,3])[None,:]*20)
		d=d*gr[:,2][None,:]
		zp=tf.reduce_sum(d, axis=1)
		zp=tf.math.exp(zp-10)-np.exp(-10)
		zp=tf.reshape(zp, ret.shape)
		ret+=zp*options.dih_type[typ]

	return 1-ret
	
def calc_rot_mat_tf(p3):
	v=p3[:,0]-p3[:,1]
	tt=tf.math.atan2(v[:,2],v[:,1])
	rota=tf.stack([
		[tf.ones_like(tt), tf.zeros_like(tt),tf.zeros_like(tt)],
		[tf.zeros_like(tt), tf.cos(tt), -tf.sin(tt)],
		[tf.zeros_like(tt),tf.sin(tt), tf.cos(tt)]])
	# print(rota.shape)
	rota=tf.transpose(rota,(2,0,1))
	vr=tf.matmul(v[:,None,:], rota)
	# print(v.shape, rota.shape, vr.shape)
	aa=tf.math.atan2(vr[:,0,1], vr[:,0,0])
	rotb=tf.stack([
		[tf.cos(aa), -tf.sin(aa), tf.zeros_like(aa)],
		[tf.sin(aa), tf.cos(aa),tf.zeros_like(aa)],
		[tf.zeros_like(aa), tf.zeros_like(aa), tf.ones_like(aa)]])
	rotb=tf.transpose(rotb,(2,0,1))
	# print(rota.shape, rotb.shape)
	rot=tf.matmul(rota, rotb)
	# print(rot.shape)
	rot=rot[:,:,::-1]
	
	v1=p3[:,2]-p3[:,1]
	p0=tf.matmul(v1[:,None,:], rot)
	# print(v1.shape, rot.shape, p0.shape)
	tt=-tf.math.atan2(p0[:,0,0], p0[:,0,1])
	rotc=tf.stack([
		[tf.cos(tt), -tf.sin(tt), tf.zeros_like(tt)], 
		[tf.sin(tt), tf.cos(tt), tf.zeros_like(tt)],
		[tf.zeros_like(tt), tf.zeros_like(tt), tf.ones_like(tt)]])
	rotc=tf.transpose(rotc,(2,0,1))
	# print(rotc.shape, m1.shape)
	rotd=tf.matmul(rot,rotc)
	# print(rotd.shape)
	return rotd

def calc_clashid(pts, options,  pad=40):
	tree=KDTree(pts)
	vdwr=options.vdwr_h 
	nnb=options.clash_nb
	d,pnb=tree.query(pts, pad+nnb)

	clashid=[]
	for i, nb0 in enumerate(pnb):
		nb=nb0[~np.isin(nb0, options.connect_all[i])].astype(int)

		d=np.linalg.norm(pts[i]-pts[nb], axis=1)
		d0=vdwr[nb]+vdwr[i]
		vid=np.argsort(d-d0)[:nnb]
		clashid.append(np.array(nb)[vid])

	clashid=np.array(clashid)
	return clashid


def compile_chi_matrix(idx_dih_chi):	
	chi_n_type=[]
	chi_n_inverseid=[]
	chi_n_matrix=[]
	for ci in range(4):
		c=e2pc.residue_rotamer[ci]
		
		key=list(c.keys())
		ck=np.array([e2pc.restype_3_to_index[k] for k in key])
		chi_n_type.append(ck)
		
		iid=np.zeros(20, dtype=int)-1
		iid[ck]=np.arange(len(ck))
		chi_n_inverseid.append(iid)
		
		mat=np.array([c[k] for k in key], dtype=floattype)
		chi_n_matrix.append(mat)
		
	chi_idx=[]
	chi_mat=[]
	for chin in range(4):
		ii=np.where(np.isin(idx_dih_chi[:,4], chi_n_type[chin]))[0]
		ii=ii.reshape((-1,chin+1))
		
		ii_res=idx_dih_chi[ii[:,0],4]
		ii_res=chi_n_inverseid[chin][ii_res]
		ii_mat=chi_n_matrix[chin][ii_res]
		ii_mat=ii_mat.reshape(ii_mat.shape[0], -1, chin*2+3)
		chi_idx.append(ii)
		chi_mat.append(ii_mat)
		
	return chi_idx, chi_mat

def get_rama_types(atoms, idx_rama):
	atom_pos=np.array([a.get_coord() for a in atoms])
	resid=[get_info(a,True) for a in atoms]
	ci,resid=np.unique(resid, return_inverse=True)
	
	#### trans vs cis PRO
	ia=idx_rama[:,4]
	ri=[atoms[i].get_parent().get_resname() for i in ia]

	proid=np.where([r=='PRO' for r in ri])[0]
	transpro=[]
	cispro=[]
	# proid
	aid=idx_rama[proid]
	ctpro=[]
	for ip, i in enumerate(aid):
		a0=atoms[i[0]]
		a=atoms[i[3]]
		r0=np.where(resid==resid[i[0]])[0]
		ca0=[j for j in r0 if atoms[j].id=='CA'][0]
		c=[ca0, i[0], i[1], i[2]]
		p=tf.gather(atom_pos[None,...], c, axis=1)
		d=calc_dihedral_tf(p[None,:])
		d=float(d)
		d=np.cos(np.deg2rad(d))
		if d>0:
			# print(a.parent.full_id, d)
			cispro.append(proid[ip])
		else:
			transpro.append(proid[ip])
			
	#### compile all rama types
	rescls=np.zeros(len(idx_rama))
	rescls[np.array([r=='ILE' or r=='VAL' for r in ri])]=3

	ia=idx_rama[:,7]
	ri1=[atoms[i].get_parent().get_resname() for i in ia]
	rescls[np.array([r=='PRO' for r in ri1])]=4
	rescls[np.array([r=='GLY' for r in ri])]=1
	# rescls[np.array([r=='PRO' for r in ri])]=2
	rescls[transpro]=2
	rescls[cispro]=5

	dih_type={"general":(rescls==0).astype(floattype),
			"gly":(rescls==1).astype(floattype),
			"protrans":(rescls==2).astype(floattype),
			"procis":(rescls==5).astype(floattype),
			"ile":(rescls==3).astype(floattype),
			"prepro":(rescls==4).astype(floattype),
			}
	return dih_type
	

def get_rotamer_angle(atoms, nchi=0):
	resid=[get_info(a,True) for a in atoms]
	ci,resid=np.unique(resid, return_inverse=True)
	ca_res=[c[-3:] for c in ci]
	
	rotmat_idx=np.zeros(len(atoms),dtype=int)-1	
	rot_axis=[]
	nci=0
	for ii in np.unique(resid):
		res=ca_res[ii]
		if res not in e2pc.chi_angles_atoms:
			continue
		chi=e2pc.chi_angles_atoms[res]
		if len(chi)>nchi:
			chi=chi[nchi]
			nc=nchi
			nci+=1
		else:
			continue

		ia=np.where(resid==ii)[0]
		aname={atoms[i].get_id():i for i in ia}
		at_full=[a[0] for a in e2pc.rigid_group_atom_positions[res]]
		if not np.all([a in aname for a in at_full if a!='']):
			## residue do not have all atoms 
			continue

		# print(res, ia)
		chid=[aname[a] for a in chi]
		chi_group=[a[0] for a in e2pc.rigid_group_atom_positions[res] if a[1]>3+nc]
		chi_group=[aname[a] for a in chi_group]

		rotmat_idx[chi_group]=len(rot_axis)
		rot_axis.append([chid[1], chid[2]])


	rot_axis=np.array(rot_axis)
	rotmat_idx[rotmat_idx==-1]=len(rot_axis)
	return rot_axis, rotmat_idx


# @tf.function(experimental_relax_shapes=True)
def rotate_sidechain_one(args):
	
	pp, tt=args
	pp=pp[None,:]
	# print(pp.shape,  tt.shape)
	px=tf.gather(pp[:,:,:3], params_sidechain["rot_axis"], axis=1)[0]
	# print(pp.shape, px.shape, tt.shape)

	axi=px[:,1,:]-px[:,0,:]
	axn=tf.math.sqrt(tf.reduce_sum(axi*axi, axis=1))[:,None]
	axi=tf.math.divide_no_nan(axi,axn)

	a = tf.cos(tt / 2.0)
	bcd=-tf.sin(tt / 2.0)[:,None]*axi
	b,c,d=bcd[:,0],bcd[:,1],bcd[:,2]
	aa, bb, cc, dd = a * a, b * b, c * c, d * d
	bc, ad, ac, ab, bd, cd = b * c, a * d, a * c, a * b, b * d, c * d
	mat=[[aa + bb - cc - dd, 2 * (bc + ad), 2 * (bd - ac)],
		[2 * (bc - ad), aa + cc - bb - dd, 2 * (cd + ab)],
		[2 * (bd + ac), 2 * (cd - ab), aa + dd - bb - cc]]
	mat=tf.transpose(tf.stack(mat), (2,0,1))

	axc=0.5*(px[:,1,:]+px[:,0,:])[:,None,:]
	trans=-tf.matmul(axc, mat)+axc
	mat=tf.concat([mat, trans], axis=1)
	mat=tf.reshape(mat, (pp.shape[0], -1, 4,3))

	eye=tf.eye(4,3)[None,None,:,:]
	eye=tf.repeat(eye, pp.shape[0], axis=0)
	mat=tf.concat([mat, eye], axis=1)
	
	
	allmat=tf.gather(mat, params_sidechain["rotmat_idx"], axis=1)
	pout_trans=tf.concat([pp[:,:,:3], tf.zeros_like(pp[:,:,:1])+1], axis=-1)
	pout_rot=tf.matmul(pout_trans[:,:,None,:], allmat)[:,:,0,:]
	return pout_rot[0]
	
def rotate_sidechain(pout, rot_axis, theta, rotmat_idx):
	global params_sidechain
	params_sidechain={
		"rot_axis": rot_axis,
		"rotmat_idx": rotmat_idx
		}
	
	assert theta.shape[0]<100
	# print("@@@@@@@",pout.shape, theta.shape)
	
	# rt=tf.vectorized_map(rotate_sidechain_one, (pout, theta))
	rt=[]
	for i in range(pout.shape[0]):
		rt.append(rotate_sidechain_one((pout[i], theta[i])))
		
	rt=tf.stack(rt, axis=0)
	# print(rt.shape)
	return rt

# 
# def rotate_sidechain1(pout, rot_axis, theta, rotmat_idx):
# 	rtax=tf.gather(pout[:,:,:3], rot_axis, axis=1)
# 	px=tf.reshape(rtax, (-1,2,3))
# 	tt=tf.reshape(theta, -1)
# 
# 	axi=px[:,1,:]-px[:,0,:]
# 	axn=tf.math.sqrt(tf.reduce_sum(axi*axi, axis=1))[:,None]
# 	axi=tf.math.divide_no_nan(axi,axn)
# 
# 	a = tf.cos(tt / 2.0)
# 	bcd=-tf.sin(tt / 2.0)[:,None]*axi
# 	b,c,d=bcd[:,0],bcd[:,1],bcd[:,2]
# 	aa, bb, cc, dd = a * a, b * b, c * c, d * d
# 	bc, ad, ac, ab, bd, cd = b * c, a * d, a * c, a * b, b * d, c * d
# 	mat=[[aa + bb - cc - dd, 2 * (bc + ad), 2 * (bd - ac)],
# 		[2 * (bc - ad), aa + cc - bb - dd, 2 * (cd + ab)],
# 		[2 * (bd + ac), 2 * (cd - ab), aa + dd - bb - cc]]
# 	mat=tf.transpose(tf.stack(mat), (2,0,1))
# 
# 	axc=0.5*(px[:,1,:]+px[:,0,:])[:,None,:]
# 	trans=-tf.matmul(axc, mat)+axc
# 	mat=tf.concat([mat, trans], axis=1)
# 	mat=tf.reshape(mat, (pout.shape[0], -1, 4,3))
# 
# 	eye=tf.eye(4,3)[None,None,:,:]
# 	eye=tf.repeat(eye, pout.shape[0], axis=0)
# 	mat=tf.concat([mat, eye], axis=1)
# 	
# 	
# 	allmat=tf.gather(mat, rotmat_idx, axis=1)
# 	pout_trans=tf.concat([pout[:,:,:3], tf.zeros_like(pout[:,:,:1])+1], axis=-1)
# 	pout_rot=tf.matmul(pout_trans[:,:,None,:], allmat)[:,:,0,:]
# 	return pout_rot

def compile_hydrogen(pdb):
	atoms=list(pdb.get_atoms())
	residue=list(pdb.get_residues())	
	atom_dict={a:i for i,a in enumerate(atoms)}
	resid=[str(get_info(a)) for a in atoms]
	resid, idx=np.unique(resid, return_index=True)
	
	h_ref=[]
	h_offset=[]
	h_label=[]
	for i,r in enumerate(residue):
		adict=r.child_dict
		res=r.resname
		if res not in e2pc.hydrogen_position:
			continue
		hp=e2pc.hydrogen_position[res]
		for h in hp:
			if h[0]=='H':
				if i==0: continue
				r0=residue[i-1]
				if r0.parent!=r.parent or r.id[1]!=r0.id[1]+1:
					continue
					
				at0=r0.child_dict
				ad=[adict['N'], at0['C'], at0['O']]
			
			else:
				try:
					ad=[adict[k] for k in h[1:4]]
				except:
					print(res, h)
					continue
				
			ad=[atom_dict[k] for k in ad]
			h_ref.append(ad)
			h_offset.append(h[4:])
			h_label.append([h[0], r,i])
			
	h_ref=np.array(h_ref, dtype=int)
	h_offset=np.array(h_offset, dtype=floattype)
	h_info=(h_label, h_ref, h_offset)
	return h_info
	
def add_h(atom_pos, h_info):
	h_label, h_ref, h_offset=h_info
	v=tf.gather(atom_pos, h_ref, axis=1)
	vs=tf.reshape(v, (-1,3,3))
	m=calc_rot_mat_tf(vs)
	m=tf.transpose(m, (0,2,1))
	m=tf.reshape(m, (atom_pos.shape[0], -1, 3,3))
	h=tf.matmul(h_offset[None, :,None,:],m)[:,:,0]
	hpos=h+v[:,:,0]

	atom_pos_h=tf.concat([atom_pos, hpos], axis=1)

	return atom_pos_h
	
def get_h_rotation_axis(atoms, bonds, h_ref):
	h_rot=[]
	for i,h in enumerate(h_ref):
		nbd=np.logical_or(bonds[:,0]==h[0], bonds[:,1]==h[0])
		if np.sum(nbd)==1:
			## only rotate atoms connecting to one non-h atoms
			h_rot.append([i, h[0], h[1]])
			
	h_rot=np.array(h_rot)
	_, hi=np.unique(h_rot[:,1], return_index=True)
	
	rotmat_idxh=np.zeros(len(atoms)+len(h_ref),dtype=int)-1
	rot_axish=[]

	for i in hi:
		hj=h_rot[h_rot[:,1]==h_rot[i,1], 0].copy()
		hj=hj+len(atoms)
		rotmat_idxh[hj]=len(rot_axish)
		rot_axish.append(h_rot[i,1:].copy())
		
	rot_axish=np.array(rot_axish)
	rotmat_idxh[rotmat_idxh==-1]=len(rot_axish)
	return rot_axish, rotmat_idxh


def calc_atom_pos(conf, model, theta_all, options, training=False, addh=False, theta_h=[]):

	pout=model(conf,training=training)
	pout_rot=pout[:,:,:3]
	for ii in range(4):
		theta=theta_all[ii][None,:]
		theta=tf.repeat(theta, conf.shape[0], axis=0)
		# print("#####", pout_rot.shape, conf.shape,theta.shape)
		pout_rot=rotate_sidechain(pout_rot, options.rot_axis[ii], theta, options.rotmat_idx[ii])

	pout=tf.concat([pout_rot, pout[:,:,3:]], axis=-1)
	atom_pos=(pout[:,:,:3]*[1,-1,-1]+0.5)*options.apix*options.maxboxsz
	
	if addh:
		atom_pos=add_h(atom_pos,options.h_info)
		if len(theta_h)!=0:
			atom_pos=rotate_sidechain(atom_pos, options.rot_axish, theta_h[None,:], options.rotmat_idxh)
		
	return atom_pos
	
def eval_chem(model, theta_all, theta_h, options):

	etc="Evaluating current model...\n  "
	conf=np.zeros((1,options.nmid), dtype=floattype)+1
	atom_pos=calc_atom_pos(conf, model, theta_all, options)
	

	bond_len=calc_bond(atom_pos, options.bonds[:,:2].astype(int))
	bond_df=(bond_len-options.bonds[:,2])/options.bonds[:,3]
	bond_outlier=np.sum(abs(bond_df)-options.nstd_bond>0)
	etc+=f"{bond_outlier} bond, "

	ang_val=calc_angle(atom_pos, options.angle[:,:3].astype(int))
	ang_df=(ang_val-options.angle[:,3])/options.angle[:,4]
	ang_outlier=np.sum(abs(ang_df)-options.nstd_angle>0)
	etc+=f"{ang_outlier} angle, "

	pt=tf.gather(atom_pos, options.idx_dih_rama, axis=1)
	phi=calc_dihedral_tf(pt[:,:,:4])
	psi=calc_dihedral_tf(pt[:,:,4:])
	rama=eval_rama(phi, psi, options)
	etc+="{}, {} Rama,".format(np.sum(rama>options.rama_thr0), np.sum(rama>options.rama_thr1))
	
	pt=tf.gather(atom_pos, options.idx_dih_plane, axis=1)
	rot=calc_dihedral_tf(pt)
	rot=tf.sin(rot*np.pi/180.)
	rot=tf.maximum(0, abs(rot)-options.thr_plane)
	plane_score=np.sum(rot>0)

	pt=tf.gather(atom_pos, options.idx_dih_piptide, axis=1)
	rot=calc_dihedral_tf(pt)
	rot=tf.sin(rot*np.pi/180.)
	rot=tf.maximum(0, abs(rot)-options.thr_piptide)
	plane_score+=np.sum(rot>0)
	etc+=" {} planarity,".format(plane_score)
	
	rotout=[]
	for chin in range(4):
		ii=options.chi_idx[chin].T.flatten()
		ii_mat=options.chi_mat[chin][None,...]

		ii=options.idx_dih_chi[ii][:,:4]
		pt=tf.gather(atom_pos, ii, axis=1)
		dih=calc_dihedral_tf(pt)%360
		dih=tf.reshape(dih, (atom_pos.shape[0], chin+1, -1))
		dih=tf.transpose(dih, (0,2,1))

		d=dih[:,:,None,:]-ii_mat[:,:,:,:chin+1]
		d=d/ii_mat[:,:,:,chin+1:chin*2+2]
		d=tf.reduce_sum(d**2, axis=-1)

		d=tf.exp(-d)*ii_mat[:,:,:,-1]
		d=tf.reduce_sum(d, axis=-1)
		d=tf.maximum(0,d-.05)

		rotout.append(np.sum(d<0.5/100))
		
	etc+=" {} rotamer outlier.".format(np.sum(rotout))
	
	atom_pos=add_h(atom_pos,options.h_info)
	arot=rotate_sidechain(atom_pos, options.rot_axish, theta_h[None,:], options.rotmat_idxh)
	
	tree=KDTree(arot[0])
	clashid=calc_clashid(arot[0].numpy(), options, pad=60)
	vdw_radius=tf.gather(options.vdwr_h, clashid)+options.vdwr_h[:,None]
	
	atomdic={'H':0,'C':1,'N':2,'O':3,'S':4,'M':9,'P':9}
	atype=np.array([atomdic[a.id[0]] for a in options.atoms])
	atype=np.append(atype, np.zeros(len(options.h_info[0]), dtype=int))
	ii=np.arange(len(clashid))
	ii=np.repeat(ii[:,None], clashid.shape[1], axis=1)
	ab=atype[clashid]*10+atype[ii]
	clash_omask=np.logical_or(ab==3, ab==30)
	clash_omask=clash_omask.astype(floattype)*.4
	
	options.clashid=clashid
	options.vdw_radius=vdw_radius
	options.clash_omask=clash_omask
	
	clash=find_clash(arot, options)
	# c=tf.reduce_sum(tf.sign(clash))/2
	etc+=" {} clashing atoms".format(np.sum(clash.numpy()>0)//2)
	return etc
	
def find_clash(atom_pos, options, relu=True):
	
	pc=tf.gather(atom_pos, options.clashid, axis=1)
	pc=pc-atom_pos[:,:,None, :]
	pc=tf.math.sqrt(tf.reduce_sum(pc*pc, axis=3))

	clash=options.vdw_radius-pc-options.vdroverlap
	clash=tf.maximum(0,clash)

	clash=clash-options.clash_omask
	if relu:
		clash=tf.maximum(0,clash)
	return clash
	
def optimize_h(atom_pos, options, npos=24):
	step=np.pi*2/npos
	tt=np.arange(0, np.pi*2, step)
	tt=np.repeat(tt[:,None], len(options.rot_axish), axis=1).astype(floattype)
	ap=tf.repeat(atom_pos, len(tt), axis=0)
	arot=rotate_sidechain(ap, options.rot_axish, tt, options.rotmat_idxh)
	
	pc=tf.gather(arot, options.clashid, axis=1)
	pc=pc-arot[:,:,None, :]
	pc=tf.math.sqrt(tf.reduce_sum(pc*pc, axis=3))

	clash=options.vdw_radius-pc-options.vdroverlap
	clash=tf.maximum(0,clash)

	clash=clash-options.clash_omask
	clash=clash.numpy()
	clash=clash+(clash>0)
	ncl=np.array([np.sum(clash[:,options.rotmat_idxh==i], axis=(1,2)) for i in range(len(options.rot_axish))])
	
	ti=np.argmin(ncl, axis=1)
	theta_h=tt[ti, np.arange(len(tt[0]))].copy()
	return theta_h

def fix_bad_rotamer(chin, model, theta_all, theta_h, options):
	
	conf=np.zeros((1,options.nmid), dtype=floattype)+1
	atom_pos=calc_atom_pos(conf, model, theta_all, options)
	atoms=options.atoms
	
	ii=options.chi_idx[chin].T.flatten()
	ii_mat=options.chi_mat[chin][None,...]

	ii=options.idx_dih_chi[ii][:,:4]
	pt=tf.gather(atom_pos, ii, axis=1)
	dih=calc_dihedral_tf(pt)%360
	dih=tf.reshape(dih, (atom_pos.shape[0], chin+1, -1))
	dih=tf.transpose(dih, (0,2,1))

	d=dih[:,:,None,:]-ii_mat[:,:,:,:chin+1]
	d=d/ii_mat[:,:,:,chin+1:chin*2+2]
	d=tf.reduce_sum(d**2, axis=-1)

	d=tf.exp(-d)*ii_mat[:,:,:,-1]
	d=tf.reduce_sum(d, axis=-1)
	d=tf.maximum(0,d-.05)
	
	rota_id=ii[:,1]
	
	rid=np.where(d[0]<0.005)[0]
	dih=dih[0].numpy()

	if len(rid)>0:
		for ii in range(chin+1):
			ir=options.rot_axis[ii][:,0]
			keys=[get_info(atoms[i])[:-1] for i in rota_id[rid]]
			dic={get_info(atoms[r])[:-1]:i for i,r in enumerate(ir)}
			ir=np.array([dic[k] for k in keys])
			theta_all[ii][ir]=0
	
	print(f"  n chi = {chin}, ", end='')
	if len(rid)==0:
		print("no outlier")
		return
	else:
		print(f"{len(rid)} rotamer outliers")
		at=[get_info(atoms[i]) for i in rota_id[rid]]

	clash_allrot=[]
	for rotai in range(ii_mat.shape[2]):
		
		rota_target=ii_mat[0,rid,rotai,:chin+1]
		rota_cur=dih[rid,:chin+1]
		ddr=rota_cur-rota_target

		for ii in range(chin+1):
			ir=options.rot_axis[ii][:,0]
			keys=[get_info(atoms[i])[:-1] for i in rota_id[rid]]
			dic={get_info(atoms[r])[:-1]:i for i,r in enumerate(ir)}
			ir=np.array([dic[k] for k in keys])
			theta_all[ii][ir]=np.deg2rad(ddr[:,ii])

		atom_pos=calc_atom_pos(conf, model, theta_all, options, addh=True, theta_h=theta_h)
		clash=find_clash(atom_pos, options)
		clash=clash[0].numpy()
		
		at0=[str(get_info(a)) for a in atoms]
		at1=[str(a) for a in at]
		rid_atoms=[np.where(np.isin(at0,a))[0] for a in at1]
		rid_clash=np.array([np.sum(clash[i]>0)+np.sum(clash[i]) for i in rid_atoms])
		
		clash_allrot.append(rid_clash)
		# print(rotai, np.sum(rid_clash),end='\r')

	clash_allrot=np.array(clash_allrot)
	rotai=np.argmin(clash_allrot,axis=0)
	clashzero=np.min(clash_allrot, axis=0)<2.
	rota_target=ii_mat[0,rid,rotai,:chin+1]
	rota_cur=dih[rid,:chin+1]
	ddr=rota_cur-rota_target
	print("    keeping {} rotamer changes does not introduce clashes".format(np.sum(clashzero)))
	ddr[~clashzero]=0
	for ii in range(chin+1):
		ir=options.rot_axis[ii][:,0]
		keys=[get_info(atoms[i])[:-1] for i in rota_id[rid]]
		dic={get_info(atoms[r])[:-1]:i for i,r in enumerate(ir)}
		ir=np.array([dic[k] for k in keys])
		theta_all[ii][ir]=np.deg2rad(ddr[:,ii])
    

def refine_backbone(model, theta_all, theta_h, options, optimizer, niter=100, training=True):
	cost=[] 
	wts=model.trainable_variables
	
	for itr in range(niter):
		with tf.GradientTape() as gt:
			conf=tf.zeros((2,options.nmid), dtype=floattype)+1
			atom_pos=calc_atom_pos(conf, model, theta_all, options, training=training)
			lossetc=0

			######
			bond_len=calc_bond(atom_pos, options.bonds[:,:2].astype(int))
			bond_df=(bond_len-options.bonds[:,2])/options.bonds[:,3]
			bond_score=tf.reduce_mean(tf.exp(-5*bond_df**2))
			bond_outlier=tf.reduce_mean(tf.maximum(0,abs(bond_df)-options.nstd_bond))*1000*20
			lossetc+=bond_score
			lossetc+=bond_outlier

			######
			ang_val=calc_angle(atom_pos, options.angle[:,:3].astype(int))
			ang_df=(ang_val-options.angle[:,3])/options.angle[:,4]
			ang_score=1-tf.reduce_mean(tf.exp(-8*ang_df**2))
			ang_outlier=tf.reduce_mean(tf.maximum(0,abs(ang_df)-options.nstd_angle))*1000*20
			lossetc+=ang_score
			lossetc+=ang_outlier

			######
			pt=tf.gather(atom_pos, options.idx_dih_rama, axis=1)
			phi=calc_dihedral_tf(pt[:,:,:4])
			psi=calc_dihedral_tf(pt[:,:,4:])
			rama=eval_rama(phi, psi, options)
			rama_score=tf.reduce_mean(rama)*.1
			rama_outlier=tf.reduce_mean(tf.maximum(0,rama-options.rama_thr0))*500
			rama_outlier+=tf.reduce_mean(tf.maximum(0,rama-options.rama_thr1))*1000*1000*1
			lossetc+=rama_score
			lossetc+=rama_outlier
			
			##########
			pt=tf.gather(atom_pos, options.idx_dih_plane, axis=1)
			rot=calc_dihedral_tf(pt)
			rot=tf.sin(rot*np.pi/180.)
			rot=tf.maximum(0, abs(rot)-options.thr_plane)
			plane_score=tf.reduce_mean(rot)*1000
			
			pt=tf.gather(atom_pos, options.idx_dih_piptide, axis=1)
			rot=calc_dihedral_tf(pt)
			rot=tf.sin(rot*np.pi/180.)
			rot=tf.maximum(0, abs(rot)-options.thr_piptide)
			plane_score+=tf.reduce_mean(rot)*1000
			
			lossetc+=plane_score            
			
			##########
			rota_out=[]
			for chin in range(4):
				ii=options.chi_idx[chin].T.flatten()
				ii_mat=options.chi_mat[chin][None,...]

				ii=options.idx_dih_chi[ii][:,:4]
				pt=tf.gather(atom_pos, ii, axis=1)
				dih=calc_dihedral_tf(pt)%360
				dih=tf.reshape(dih, (atom_pos.shape[0], chin+1, -1))
				dih=tf.transpose(dih, (0,2,1))

				d=dih[:,:,None,:]-ii_mat[:,:,:,:chin+1]
				d=d/ii_mat[:,:,:,chin+1:chin*2+2]
				d=tf.reduce_sum(d**2, axis=-1)

				d=tf.exp(-d)*ii_mat[:,:,:,-1]
				d=tf.reduce_sum(d, axis=-1)
				d=tf.maximum(0,d-.05)

				rota_out.append(d)

			rota_out=1-tf.concat(rota_out, axis=1)            
			rota_score=tf.reduce_mean(rota_out)*5

			r1=tf.maximum(0, rota_out-99/100.)
			# r2=tf.maximum(0, rota_out-98/100.)
			rota_outlier=tf.reduce_mean(r1)*5000
			# rota_outlier+=tf.reduce_mean(r2)*10

			lossetc+=rota_score
			lossetc+=rota_outlier
				
			atom_pos=add_h(atom_pos,options.h_info)
			tt=tf.repeat(theta_h[None,:], conf.shape[0], axis=0)
			arot=rotate_sidechain(atom_pos, options.rot_axish, tt, options.rotmat_idxh)
			clash=find_clash(arot, options, relu=False)
			clash0=tf.maximum(0,clash)
			clash1=tf.maximum(0,clash+options.vdroverlap-0.3)*1e-5
			clash_score=(tf.reduce_sum(tf.sign(clash0)*.1+clash0+clash1))/conf.shape[0]/2.*5.
			# c=tf.reduce_sum(tf.sign(clash))
			lossetc+=clash_score
			l=lossetc


		assert np.isnan(l.numpy())==False
		nclash=np.sum(clash.numpy()>0)//2
		
		grad=gt.gradient(l, wts)
		optimizer.apply_gradients(zip(grad, wts))
		etc=""
		etc+=f", bond {bond_score:.3f},{bond_outlier:.3f}"
		etc+=f", angle {ang_score:.3f},{ang_outlier:.3f}"
		etc+=f", rama {rama_score:.3f},{rama_outlier:.3f}"
		etc+=f", clash {clash_score:.3f},{nclash:d}"
		etc+=f", rota {rota_score:.3f},{rota_outlier:.3f}"
		etc+=f", plane {plane_score:.3f}"


		print("{}/{}\t{:.3f}{}".format(len(cost), niter, l, etc), end='\r')


		cost.append(l)  
	print()
	return cost
	
def save_model_pdb(model, theta_all, theta_h, options, fname):
	
	conf=np.zeros((1,options.nmid), dtype=floattype)+1
	atom_pos=calc_atom_pos(conf, model, theta_all, options, addh=True, theta_h=theta_h)

	if options.model.endswith(".cif"):
		pdbpar = MMCIFParser( QUIET = True) 
	else:
		pdbpar = PDBParser( QUIET = True) 
	pdbh = pdbpar.get_structure("model",options.model)
	
	residue=list(pdbh.get_residues())
	for r in residue:
		d=list(r.child_dict)
		for a in d:
			if a[0]=='H':
				r.detach_child(a)
				
	atoms0=list(pdbh.get_atoms())
	for i,a in enumerate(atoms0):
		a.set_coord(atom_pos[0,i].numpy())

	res1=list(pdbh.get_residues())
	h=atom_pos[0, options.npt_noh:].numpy()
	for ii,hl in enumerate(options.h_info[0]):
		a=Atom.Atom(hl[0], h[ii], 50, 1, ' ', hl[0], atoms0[-1].serial_number+ii+1, element='H')
		i=hl[2]
		a.set_parent(res1[i])
		res1[i].add(a)
		
		
	if options.model.endswith(".cif"):
		io=MMCIFIO()
		fname+=".cif"
	else:
		io=PDBIO()
		fname+=".pdb"
		
	io.set_structure(pdbh)
	io.save(fname)
	print(f"model saved to {fname}")
    
def main():
	
	usage="""
	GMM based model refinement.
	
	"""
	parser = EMArgumentParser(usage=usage,version=EMANVERSION)
	parser.add_argument("--path", type=str,help="folder generated by e2gmm_compile_model", default=None)
	parser.add_argument("--model", type=str,help="alternative pdb model. default is model_input in path.", default=None)
	parser.add_argument("--niter", type=str, help="number of iteration for loose and tight constraints. default is 5,10",default="5,10")
	parser.add_argument("--ppid", type=int, help="Set the PID of the parent process, used for cross platform PPID",default=-1)

	(options, args) = parser.parse_args()
	logid=E2init(sys.argv,options.ppid)
	
	path=options.path
	if options.model==None:
		if os.path.isfile(f"{path}/model_input.pdb"):
			options.model=f"{path}/model_input.pdb"
		else:
			options.model=f"{path}/model_input.cif"
	
	options.maxboxsz=raw_boxsz=128
	options.apix=apix=1
	options.batchsz=32
	options.nmid=4
	niter=[int(i) for i in options.niter.split(',')]
	
	
	if options.model.endswith(".cif"):
		pdbpar = MMCIFParser( QUIET = True) 
	else:
		pdbpar = PDBParser( QUIET = True) 
	pdb = pdbpar.get_structure("model",options.model)
	residue=list(pdb.get_residues())
	for r in residue:
		d=list(r.child_dict)
		for a in d:
			if a[0]=='H':
				r.detach_child(a)
	atoms=options.atoms=list(pdb.get_atoms())
	atom_pos=np.array([a.get_coord() for a in atoms])
	
	print(f"Input model: {options.model}")
	print(f"  {len(residue)} residues, {len(atoms)} atoms.")
	
	print("Initializing...")
	p=atom_pos.copy()
	pts=np.zeros((len(p),5))
	p=p/options.maxboxsz/options.apix-0.5
	p[:,1:]*=-1; pts[:,:3]=p[:,:3]
	pts[:,3]=.5; pts[:,4]=1
	
	gen_model_full=build_decoder(pts, options)
	conf=tf.zeros((2,4), dtype=floattype)+1.
	pout=gen_model_full(conf)
	atom_pos=(pout[:,:,:3]*[1,-1,-1]+0.5)*options.apix*options.maxboxsz
	
	##########################################
	idx_rama=np.loadtxt(f"{path}/model_rama_angle.txt").astype(int)
	options.bonds=bonds=np.loadtxt(f"{path}/model_bond.txt").astype(floattype)
	options.angle=np.loadtxt(f"{path}/model_angle.txt").astype(floattype)
	vdwr=np.loadtxt(f"{path}/model_vdwr.txt").astype(floattype)
	options.idx_dih_rama=np.loadtxt(f"{path}/model_rama_angle.txt").astype(int)
	options.idx_dih_plane=np.loadtxt(f"{path}/model_dih_plane.txt").astype(int)
	options.idx_dih_piptide=np.loadtxt(f"{path}/model_dih_piptide.txt").astype(int)
	options.idx_dih_chi=np.loadtxt(f"{path}/model_dih_chi.txt").astype(int)
		
	##########################################
	options.thr_plane=np.sin(10*np.pi/180)
	options.thr_piptide=np.sin(30*np.pi/180)
	options.clash_nb=128 ## number of neighbors to compute clash
	options.nstd_bond=4.5
	options.nstd_angle=4.5
	options.vdroverlap=0.6
	ramalevel=[0.0005,0.02]
	options.rama_thr0=1-ramalevel[1]*1.1
	options.rama_thr1=1-ramalevel[0]*2	
	
	
	##########################################
	print("Compiling Ramachandran types...")
	options.dih_type=dih_type=get_rama_types(atoms, idx_rama)
	rt={"general":"General","gly":"GLY","protrans":"trans-PRO","procis":"cis-PRO","ile":"ILE/VAL","prepro":"pre-PRO"}
	for k in dih_type:
		print(f"  Ramachandran type {rt[k]:<10}:  {int(np.sum(dih_type[k]))} residues.")


	##########################################
	print("Compiling rotamers...")
	options.chi_idx, options.chi_mat=compile_chi_matrix(options.idx_dih_chi)
		
	rot_axis=[]
	rotmat_idx=[]
	for i in range(4):
		ra, ri=get_rotamer_angle(atoms, i)    
		rot_axis.append(ra)
		rotmat_idx.append(ri)
		
	options.rot_axis=rot_axis
	options.rotmat_idx=rotmat_idx
	for i,m in enumerate(options.chi_mat):
		print(f"  rotamer chi = {i}, matrix shape: {m.shape}, total {len(rot_axis[i])} angles")
		
	### additional rotation for each chi angle
	theta_all=[np.zeros(len(rot_axis[ii]), dtype=floattype) for ii in range(4)]	
	
	
	##########################################
	print("Adding hydrogen...")
	options.h_info=compile_hydrogen(pdb)
	h_label, h_ref, h_offset=options.h_info
	options.npt_noh=npt_noh=len(atoms)
	options.npt_h=npt_h=len(h_label)
	print(f"  {npt_noh} non-H atoms. Adding {npt_h} H")
	atom_pos=add_h(atom_pos, options.h_info)
	
	#### bonds between H and non-H
	hb=np.array([np.arange(npt_h)+npt_noh, h_ref[:,0], np.zeros(npt_h), np.zeros(npt_h)], dtype=floattype).T
	ah=atom_pos[0].numpy()
	d=np.linalg.norm(ah[hb[:,0].astype(int)]-ah[hb[:,1].astype(int)], axis=1)
	hb[:,2]=d
	hb[:,3]=0.02
	bonds_h=np.vstack([bonds, hb])
	
	#### vdw radius of H
	lbs=["{}_{}".format(h[1].resname,h[0]) for h in h_label]
	vdwh=np.array([e2pc.get_vdw_radius(i) for i in lbs])
	options.vdwr_h=np.append(vdwr, vdwh).astype(floattype)
		
	#### dihedral rotationfor H
	options.rot_axish, options.rotmat_idxh=get_h_rotation_axis(atoms, bonds, h_ref)
	print(f"  total {len(options.rot_axish)} angles for H rotation")
	
	theta_h=np.zeros(len(options.rot_axish), dtype=floattype)
	
	conf=np.zeros((3,options.nmid), dtype=floattype)+1
	atom_pos=calc_atom_pos(conf, gen_model_full, theta_all, options, addh=False)
	
	save_model_pdb(gen_model_full, theta_all, theta_h, options, f"{path}/model_00")
	
	##########################################
	print("Finding clashing atoms...")
	#### bond connectivity 
	maxlen=3
	npt=npt_h+npt_noh
	bd=bonds_h[:,:2].astype(int)
	bonds_matrix=scipysparse.csr_matrix((np.ones(len(bd)), (bd[:,0], bd[:,1])), shape=(npt,npt))

	d = scipysparse.csgraph.dijkstra(bonds_matrix, directed=False, limit=maxlen)
	options.connect_all=[np.where(i<=maxlen)[0] for i in d]
	
	# tree=KDTree(atom_pos[0])
	clashid=calc_clashid(atom_pos[0].numpy(), options, pad=60)
	
	
	##########################################
	etc=eval_chem(gen_model_full, theta_all, theta_h, options)
	print(etc)
	
	print("Optimizing H rotation...")
	conf=np.zeros((1,options.nmid), dtype=floattype)+1
	atom_pos=calc_atom_pos(conf, gen_model_full, theta_all, options, addh=True)
	theta_h=optimize_h(atom_pos, options, npos=24)
	
	etc=eval_chem(gen_model_full, theta_all, theta_h, options)
	print(etc)
	
	print("Fixing bad rotamers....")
	for chin in range(4):
		fix_bad_rotamer(chin, gen_model_full, theta_all, theta_h, options)
	
	atom_pos=calc_atom_pos(conf, gen_model_full, theta_all, options, addh=True)
	theta_h=optimize_h(atom_pos, options, npos=24)
	etc=eval_chem(gen_model_full, theta_all, theta_h, options)
	print(etc)
	save_model_pdb(gen_model_full, theta_all, theta_h, options, f"{path}/model_01")
	
	learnrate=1e-6
	# learnrate=0
	##########################################
	print("Start full refinemnet....")
	opt=tf.keras.optimizers.Adam(learning_rate=learnrate)
	for itr in range(niter[0]):
		print("iteration ",itr)
		cost=refine_backbone(gen_model_full, theta_all, theta_h, options, opt, niter=100, training=False)
		etc=eval_chem(gen_model_full, theta_all, theta_h, options)
		print(etc)
		
	# options.nstd_bond=4.5
	# options.nstd_angle=4.5
	options.vdroverlap=0.25
	etc=eval_chem(gen_model_full, theta_all, theta_h, options)
	print("Tightening constraints...")
	opt=tf.keras.optimizers.Adam(learning_rate=learnrate)
	for itr in range(niter[1]):
		print("iteration ",itr)
		cost=refine_backbone(gen_model_full, theta_all, theta_h, options, opt, niter=100, training=True)
		atom_pos=calc_atom_pos(conf, gen_model_full, theta_all, options, addh=True)
		theta_h=optimize_h(atom_pos, options, npos=24)
		etc=eval_chem(gen_model_full, theta_all, theta_h, options)
		print(etc)

	##########################################
	cost=refine_backbone(gen_model_full, theta_all, theta_h, options, opt, niter=100, training=False)
	etc=eval_chem(gen_model_full, theta_all, theta_h, options)
	print(etc)
# 	
	save_model_pdb(gen_model_full, theta_all, theta_h, options, f"{path}/model_02")

	E2end(logid)
	
if __name__ == '__main__':
	main()
	
