




































































































"""0
def Plot(city, R, dist):
    # Plot
    Pt = [R[city[i]] for i in range(len(city))]
    Pt += [R[city[0]]]
    Pt = array(Pt)
    title('Total distance='+str(dist))
    plot(Pt[:,0], Pt[:,1], '-o')
    show()
"""











































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































"""1
						# we abandon randomize phase strategy
						frc_without_mask = fsc(map1, map2, 1)
						randomize_at     = -1.0
						for ifreq in xrange(1, len(frc_without_mask[1])): # always skip zero frequency
							if frc_without_mask[1][ifreq] < options.randomphasesafter:
								randomize_at = float(ifreq)
								break
						log_main.add("Phases are randomized after: %4.2f[A]"% (options.pixel_size/(randomize_at/map1.get_xsize())))
						frc_masked = fsc(map1*m, map2*m, 1)
						map1 = fft(Util.randomizedphasesafter(fft(map1), randomize_at))*m
						map2 = fft(Util.randomizedphasesafter(fft(map2), randomize_at))*m
						frc_random_masked = fsc(map1, map2, 1)
						fsc_true          = [frc_without_mask[0], [None]*len(frc_without_mask[0])]
						for i in xrange(len(fsc_true[1])):
							if i < (int(randomize_at) + 2):# move two pixels up
								fsc_true[1][i] = frc_masked[1][i]
							else:
								fsct = frc_masked[1][i]
								fscn = frc_random_masked[1][i]
								if (fscn > fsct): fsc_true[1][i]= 0.
								else: fsc_true[1][i]=(fsct-fscn)/(1.-fscn)
						else:
					"""
































































































































































































































































































































































































































