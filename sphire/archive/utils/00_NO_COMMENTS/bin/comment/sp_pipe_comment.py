









































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































'''0
	if args.generate_mask:
		sxprint(" ")
		sxprint("Generating mooon elimnated soft-edged 3D mask from the 3D binary volume corresponding to the specified molecular mass or density threshold with specified option parameters...")
		sxprint("  Soft-edge type : {}".format(args.edge_type ))
		gm_mask3d_moon_eliminated = None
		gm_bin3d_mol_mass_dilated = None
		gm_soft_edging_start_time = time()
		if args.edge_type == "cosine":
			# Use cosine soft-edged which is same as PostRefiner
			gm_binarize_threshold = 0.5
			if args.debug:
				sxprint("MRK_DEBUG: ")
				sxprint("MRK_DEBUG: Util.adaptive_mask()")
				sxprint("MRK_DEBUG:   gm_binarize_threshold  := {}".format(gm_binarize_threshold))
				sxprint("MRK_DEBUG:   args.gm_dilation       := {}".format(args.gm_dilation))
				sxprint("MRK_DEBUG:   args.gm_edge_width     := {}".format(args.gm_edge_width))
			gm_mask3d_moon_eliminated = Util.adaptive_mask(bin3d_mol_mass, gm_binarize_threshold, args.gm_dilation, args.gm_edge_width)
		elif args.edge_type == "gauss":
			gm_gauss_kernel_radius = args.gm_edge_width - args.gm_dilation
			gm_mask3d_moon_eliminated, gm_bin3d_mol_mass_dilated = mrk_sphere_gauss_edge(bin3d_mol_mass, args.gm_dilation, gm_gauss_kernel_radius, args.gm_edge_sigma, args.debug)
		else:
		sxprint("  Totally, {} soft-edging of 3D mask took {:7.2f} sec...".format(args.edge_type.upper(), time() - gm_soft_edging_start_time))
		
		if args.debug:
			if gm_bin3d_mol_mass_dilated is not None:
				gm_bin3d_mol_mass_dilated_file_path = os.path.join(args.output_directory, "mrkdebug{:02d}_gm_bin3d_mol_mass_dilated.hdf".format(debug_output_id))
				gm_bin3d_mol_mass_dilated.write_image(gm_bin3d_mol_mass_dilated_file_path)
				debug_output_id += 1
		
		gm_mask3d_moon_eliminated_file_path = os.path.join(args.output_directory, "{}_mask_moon_eliminated.hdf".format(args.outputs_root))
		sxprint(" ")
		sxprint("Saving moon eliminated 3D mask to {}...".format(gm_mask3d_moon_eliminated_file_path))
		gm_mask3d_moon_eliminated.write_image(gm_mask3d_moon_eliminated_file_path)
	'''	
'''1
	sxprint(" ")
	sxprint("Summary of processing...")
	sxprint("  Provided expected molecular mass [kDa]      : {}".format(args.mol_mass))
	"""
	sxprint("  Applied density threshold                   : {}".format(density_threshold))
	sxprint("  Computed molecular mass [kDa] of density    : {}".format(computed_mol_mass_from_density))
	sxprint("  Percentage of this molecular mass [kDa]     : {}".format(computed_mol_mass_from_density/args.mol_mass * 100))
	sxprint("  Computed volume [Voxels] of density         : {}".format(computed_vol_voxels_from_density))
	sxprint("  Percentage of this volume [Voxels]          : {}".format(computed_vol_voxels_from_density/computed_vol_voxels_from_mass * 100))
	"""
	sxprint("  Saved moon eliminated 3D reference to       : {}".format(ref3d_moon_eliminated_file_path))
	if args.generate_mask:
		sxprint("  Saved mooon elimnated soft-edged 3D mask to : {}".format(gm_mask3d_moon_eliminated_file_path))
	'''

































































































































































































































































































































































































