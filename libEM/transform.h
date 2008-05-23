/**
 * $Id$
 */

/*
 * Author: Steven Ludtke, 04/10/2003 (sludtke@bcm.edu)
 * Copyright (c) 2000-2006 Baylor College of Medicine
 * 
 * This software is issued under a joint BSD/GNU license. You may use the
 * source code in this file under either license. However, note that the
 * complete EMAN2 and SPARX software packages have some GPL dependencies,
 * so you are responsible for compliance with the licenses of these packages
 * if you opt to use BSD licensing. The warranty disclaimer below holds
 * in either instance.
 * 
 * This complete copyright notice must be included in any revised version of the
 * source code. Additional authorship citations may be added, but existing
 * author citations must be preserved.
 * 
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 2 of the License, or
 * (at your option) any later version.
 * 
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
 * GNU General Public License for more details.
 * 
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, write to the Free Software
 * Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
 * 
 * */

#ifndef eman__transform_h__
#define eman__transform_h__ 1

#include "vec3.h"
#include "emobject.h"
//#include <vector>
//#include <map>
//#include <string>

using std::string;
using std::map;
using std::vector;

namespace EMAN
{
	/** @file transform.h
	 *   These are  a collection of transformation tools: rotation, translation,
	 *            and construction of symmetric objects
         *  @author Philip Baldwin and Steve Ludtke
	 *    <Philip.Baldwin@uth.tmc.edu>
	 *	Transform defines a transformation, which can be rotation,
         *         translation, scale, and their combinations.
	 *
	 *  @date $Date: 2005/04/04 17:41pm
	 *
	 *  @see Phil's article
	 *
	 * Internally a transformation is stored in a 4x4 matrix.
	 *         a b c d
	 *         e f g h           R        v
	 *  M=     j k m n    =      vpre     1    , where R is 3by3, v is 3by1
	 *         p q r 1
	 *  The standard computer graphics convention is identical to ours after setting vpre to 
	 *     zero and can be found in many
	 *    references including Frackowiak et al; Human Brain Function
	 *
	 *
	 * The left-top 3x3 submatrix
	 *
	 *        a b c
	 *   R =  e f g
	 *        j k m
	 *
	 * provides rotation, scaling and skewing (not yet implimented).
	 *
	 * The cumulative translation is stored in (d, h, n).
	 * We put the post-translation into (p, q, r), since it is convenient
	 *   to carry along at times. When matrices are multiplied or printed, these
	 *   are hidden to the user. They can only be found by applying the post_translation
	 *    method, and these elements are non-zero. Otherwise the post-translation method returns
	 *         the cumulative translationmlb
	 *
	 * If rotations need to be found
	 *    around alternate origins, then brief calculations need to be performed
	 * Pre and Post Translations should be kept as separate vectors
	 *
	 * a matrix  R is called orthogonal if
	 *           R * transpose(R) = 1.
	 * All Real Orthogonal Matrices have eigenvalues with unit modulus and determinant
	 *  therefore equal to  "\pm 1"
	 * @ingroup tested3c 
     */
    
	class Transform3D
	{
	public:
		static const float ERR_LIMIT;
		enum EulerType
		{
			UNKNOWN,
			EMAN,
			IMAGIC,
			SPIN,
			QUATERNION,
			SGIROT,
			SPIDER,
			MRC,
			XYZ,
			MATRIX
		};
		
		// C1
		Transform3D();

		// copy constructor
	    Transform3D( const Transform3D& rhs );

	     // C2   
		Transform3D(float az,float alt, float phi); // EMAN by default


		//  C3  Usual Constructor: Post Trans, after appying Rot
		Transform3D(float az, float alt, float phi, const Vec3f& posttrans);
 
		// C4
		Transform3D(EulerType euler_type, float a1, float a2, float a3) ; // only EMAN: az alt phi
								                            // SPIDER     phi theta psi
		
		// C5   First apply pretrans: Then rotation
		Transform3D(EulerType euler_type, const Dict& rotation);
		

		// C6   First apply pretrans: Then rotation: Then posttrans
		Transform3D(const Vec3f & pretrans, float az, float alt, float phi,  const Vec3f& posttrans);

		Transform3D(float m11, float m12, float m13,
					float m21, float m22, float m23,
					float m31, float m32, float m33);

		~ Transform3D();  // COmega   Deconstructor


		void apply_scale(float scale);
		void set_scale(float scale);
		void orthogonalize();	// reorthogonalize the matrix
		void transpose();	// create the transpose in place

		void set_rotation(float az, float alt,float phi);
		void set_rotation(EulerType euler_type, float a1, float a2, float a3); // just SPIDER and EMAN
		
		void set_rotation(float m11, float m12, float m13,
                                     float m21, float m22, float m23,
			             float m31, float m32, float m33);

		void set_rotation(EulerType euler_type, const Dict &rotation );
		

		/** returns a rotation that maps a pair of unit vectors, a,b to a second  pair A,B
		 * @param eahat, ebhat, eAhat, eBhat are all unit vectors
		 * @return  a transform3D rotation
		 */
		void set_rotation(const Vec3f & eahat, const Vec3f & ebhat,
		                                    const Vec3f & eAhat, const Vec3f & eBhat); 


		/** returns the magnitude of the rotation
		*/
		float get_mag() const;
		/** returns the spin-axis (or finger) of the rotation
		*/
		Vec3f get_finger() const;
		Vec3f get_pretrans( int flag=0) const; // flag=1 => all trans is pre
		Vec3f get_posttrans(int flag=0) const; // flag=1 => all trans is post
 		Vec3f get_center() const;
		Vec3f get_matrix3_col(int i) const;
		Vec3f get_matrix3_row(int i) const;
        Vec3f transform(Vec3f & v3f) const ; // This applies the full tranform to the vec
        Vec3f rotate(Vec3f & v3f) const ;  // This just applies the rotation to the vec
		
		Transform3D inverseUsingAngs() const;
		Transform3D inverse() const;
					
		Dict get_rotation(EulerType euler_type=EMAN) const;

		void printme() const {
			for (int i=0; i<3; i++) {
				printf("%6.15f\t%6.15f\t%6.15f\t%6.1f\n",
					   matrix[i][0],matrix[i][1],matrix[i][2],matrix[i][3]);
			}
			printf("%6.3f\t%6.3f\t%6.3f\t%6.3f\n",0.0,0.0,0.0,1.0);
			printf("\n");
		}

		inline float at(int r,int c) const { return matrix[r][c]; }
		void set(int r, int c, float value) { matrix[r][c] = value; }
		float * operator[] (int i);
		const float * operator[] (int i) const;
		
		static int get_nsym(const string & sym);
		Transform3D get_sym(const string & sym, int n) const;
		void set_center(const Vec3f & center);
		void set_pretrans(const Vec3f & pretrans); // flag=1 means count all translation as pre
		void set_pretrans(float dx, float dy, float dz);
		void set_pretrans(float dx, float dy);
		void set_posttrans(const Vec3f & posttrans);// flag=1 means count all translation as post
		void set_posttrans(float dx, float dy, float dz);
		void set_posttrans(float dx, float dy);

		float get_scale() const;   

		void to_identity();
        bool is_identity();

		/** Convert a list of euler angles to a vector of Transform3D objects.
		 *
		 *	@param[in] eulertype The type of Euler angles that is being passed in.
		 *	@param[in] angles A flat vector of angles.
		 *
		 *	@return Vector of pointers to Transform3D objects.
		 */
		static vector<Transform3D*>
			angles2tfvec(EulerType eulertype, const vector<float> angles);

		void dsaw_zero_hack(){
			for (int j=0; j<4; ++j) {
				for (int i=0; i<4; i++) {
				if ( fabs(matrix[j][i]) < 0.000001 )
					matrix[j][i] = 0.0;
				}
			}
			
		}

	private:
		enum SymType
		{      CSYM,
			DSYM,
			TET_SYM,
			ICOS_SYM,
			OCT_SYM,
			ISYM,
			UNKNOWN_SYM
		};

		void init();

		static SymType get_sym_type(const string & symname);

		float matrix[4][4];

		static map<string, int> symmetry_map;
	}; // ends Class

	Transform3D operator*(const Transform3D & M1, const Transform3D & M2);
	Vec3f operator*(const Vec3f & v    , const Transform3D & M);
	Vec3f operator*(const Transform3D & M, const Vec3f & v    );
	
	/** Symmetry3D - A base class for 3D Symmetry objects.
	* Objects of this type must provide delimiters for the asymmetric unit (get_delimiters), and
	* must also provide all of the rotational symmetric operations (get_sym(int n)). They must also
	* provide the total number of unique symmetric operations with get_nsym (except in helical symmetry).
	* get_delimiter returns a dictionary with "alt_max" and "az_max" keys, which correspond to the
	* encompassing azimuth and altitude angles of the asymmetric unit. These can be interpreted in a
	* relatively straight forward fashion when dealing with C and D symmetries to demarcate the asymmetric
	* unit, however when dealing with Platonic symmetries the asymmetric unit is not so trivial.
	* see http://blake.bcm.edu/emanwiki/EMAN2/Symmetry for figures and description of what we're doing
	* here, for all the symmetries, and look in the comments of the PlatonicSym classes themselves.
	* It inherits from a factory base, making it amenable to incorporation in EMAN2 style factories
	* @author David Woolford
	* @date Feb 2008
	*/
	class Symmetry3D : public FactoryBase
	{
		public:
		Symmetry3D() {};
		virtual  ~Symmetry3D() {};
		
		/** Every Symmetry3D object must return a dictionary containing the delimiters
		 * that define its asymmetric unit (this is not strictly true in the case of the PlatonicSym class)
		 * @param inc_mirror whether or not the mirror part of the asymmetric unit should be included in the consideration
		 * @return a dictionary containing atleast "alt_max" and "az_max"
		*/
		virtual Dict get_delimiters(const bool inc_mirror=false) const = 0;
		
		/** Every Symmetry3D object must provide access to the full set of its symmetry operators
		 * via this function
		 * @param n the symmetry operator number
		 * @return a Transform3D object describing the symmetry operation
		 */
		virtual Transform3D get_sym(int n) const = 0;
		
		/** The total number of unique symmetry operations that will be return by this object when
		 * a calling program access Symmetry3D::get_sym. However in the case of HSym, this is really something else.
		 */
		virtual int get_nsym() const = 0;
		
		/**This functionality is only relevant to platonic symmetries. But it could
		 * grow into functionality for the other symmetries.
		 */
		virtual float get_az_alignment_offset() const { return 0.0; }
		
		
		
		/** A function that is used to determine if this is a platonic symmetry object
		 * This function is only virtually overloaded by the PlatonicSym symmetry, which returns true, not false
		 * @return false - indicating that this is not a platonic symmetry object
		 */
		virtual bool is_platonic_sym() const { return false; }
		
		/** A function that is used to determine if this is a Helical symmetry object
		 * This function is only virtually overloaded by the HSym symmetry, which returns true, not false
		 * @return false - indicating that this is not a helical symmetry object
		 */
		virtual bool is_h_sym() const { return false; }
		
		/** A function that is used to determine if this is a c symmetry object
		 * This function is only virtually overloaded by the CSym object, which returns true
		 * @return false - indicating that this is not a helical symmetry object
		 */
		virtual bool is_c_sym() const { return false; }
		
		/** A function that is used to determine if this is a d symmetry object
		 * This function is only virtually overloaded by the DSym object, which returns true
		 * @return false - indicating that this is not a helical symmetry object
		 */
		virtual bool is_d_sym() const { return false; }
		
		/** A function that is used to determine if this is the tetrahedral symmetry object
		 * This function is only virtually overloaded by the TetSym object, which returns true
		 * @return false - indicating that this is not a tetrahedral symmetry object
		 */
		virtual bool is_tet_sym() const { return false; }
		
		
		
		/** The Symmetry3D object must return the maximum degree of symmetry it exhibits about any one axis.
		 * This function is only called in the AsymmUnitOrientationGenerator.
		 */
		virtual int get_max_csym() const = 0;
		
		/** The Symmetry3D object must be capable of returning an ordered list of points on the unit
		 * sphere that define its asymmetric unit (with mirror considerations). The list can
		 * be any length, and must be constructed carefully. If the list consists of points A B and C,
		 * then arcs on the unit sphere connecting A to B, then B to C, then C to A must define the
		 * asymmetric unit (with or without its mirror portion). i.e. it is a cyclic list, on any
		 * length
		 * @param inc_mirror whether or not to include the mirror portion of the asymmetric unit
		 * @return a vector or points which define a cyclic set of great arcs on the unit sphere. Each point may be connected to the point that proceeds it, and the last point may be connected to the first point, and this demarcates the asymmetric unit.
		*/
		virtual vector<Vec3f> get_asym_unit_points(bool) const = 0;
		/** Ask the Symmetry3D object to generate a set of orientations in its asymmetric unit
		 * using an OrientationGenerator constructed from the given parameters (using a Factory).
		 * This is reminiscent of the strategy design pattern
		 * @param generatorname the string name of the OrientationGenerator, as accessed for the OrientationGenerator factory
		 * @param parms the parameters handed to OrientationGenerator::set_params after initial construction
		 * @return a set of orientations in the unit spher
		*/
		vector<Transform3D> gen_orientations(const string& generatorname="eman", const Dict& parms=Dict());
		
		/** A function to be used when generating orientations over portion of the unit sphere
		 * defined by parameters returned by get_delimiters. In platonic symmetry altitude and azimuth
		 * alone are not enough to correctly demarcate the asymmetric unit. See the get_delimiters comments.
		 * @param altitude the EMAN style altitude of the 3D orientation in degrees 
		 * @param azimuth the EMAN style azimuth of the 3D orientation in degrees
		 * @param inc_mirror whether or not to include orientations if they are in the mirror portion of the asymmetric unit
		 * @return true or false, depending on whether or not the orientation is within the asymmetric unit
		 */
		virtual bool is_in_asym_unit(const float& altitude, const float& azimuth, const bool inc_mirror) const = 0;

		/** A function that will reduce an orientation, as characterized by Euler anges, into a specific asymmetric unit.
		* Default behavior is to map the given orientation into the default asymmetric unit of the symmetry (n=0). This 
		* is a concrete implementation that works for all symmetries, relying on a concrete instance of the get_asym_unit_triangles
		* function
		* @param t3d a transform3D characterizing an orientation
		* @param n the number of the asymmetric unit you wish to map the given orientation into. There is a strong relationship between n and to Symmetry3D::get_sym
		* @return the orientation the specified asymmetric unit (by default this is the default asymmetric unit of the symmetry)
		* @ingroup tested3c 
		*/
		virtual Transform3D reduce(const Transform3D& t3d, int n=0) const;
		
		
		/** A function that will determine in which asymmetric unit a given orientation resides 
		 * The asymmetric unit 'number' will depend entirely on the order in which different symmetry operations are return by the
		 * Symmetry3D::get_sym function
		 * @param t3d a transform3D characterizing an orientation
		 * @return the asymmetric unit number the the orientation is in
		 */
		virtual int in_which_asym_unit(const Transform3D& t3d) const;
		
		/** Get triangles that precisely occlude the projection area of the default asymmetric unit. This will be used
		 * for collision detection in Symmetry3D::reduce
		 * @param inc_mirror whether to include the mirror portion of the asymmetric unit
		*/
		virtual vector<vector<Vec3f> > get_asym_unit_triangles(bool inc_mirror) const = 0;
	};
	
	/** An encapsulation of cyclic 3D symmetry
	 * @author David Woolford (based on previous work by Phil Baldwin and Steve Ludtke)
	 * @date Feb 2008
	 */
	class CSym : public Symmetry3D
	{
		public:
		CSym() {};
		virtual  ~CSym() {};
		
		/** Factory support function NEW
		 * @return a newly instantiated class of this type
		 */
		static Symmetry3D *NEW()
		{
			return new CSym();
		}
		
		/** Return CSym::NAME
		 * @return the unique name of this class
		 */
		virtual string get_name() const { return NAME; }

		/** Get a description
		 * @return a clear desciption of this class
		 */
		virtual string get_desc() const { return "C symmetry support"; }
		
		/** Get a dictionary containing the permissable parameters of this class
		 * @return a dictionary containing the permissable parameters of this class
		 */
		virtual TypeDict get_param_types() const
		{
			TypeDict d;
			d.put("nsym", EMObject::INT, "The symmetry number");
			return d;
		}
		
		/** Get the altitude and phi angle of the c symmetry, which depends on nysm.
		 * The "alt_max" value in the return dicts is 180 or 90 degrees, depending inc_mirror
		 * The "az_max" is 360/nsym degrees.
		 * @param inc_mirror whether or not to include the part of the asymmetric unit which contains the mirror projections of the other half
		 * @return a dictionary containing the keys "alt_max" and "az_max"
		 * @exception InvalidValueException if nsym is less than or equal to zero
		 */
		virtual Dict get_delimiters(const bool inc_mirror=false) const;
		
		/** Provides access to the complete set of rotational symmetry operations associated with this symmetry.
		 * Rotational symmetry operations for C symmetry are always about the z-axis (in the EMAN convention), and
		 * therefore the only non zero return angle is azimuth. Specifically, it is n*360/nsym degrees.
		 * @param n the rotational symmetry operation number. If n is greater than nsym we take n modulo nsym 
		 * @return a transform3d containing the correct rotational symmetric operation.
		 * @exception InvalidValueException if nsym is less than or equal to zero
		 */
		virtual Transform3D get_sym(int n) const;

		/** Gets the total number of unique roational symmetry operations associated with this symmetry
		* For C symmetry, this is simply nsym
		* @return the degree of of cyclic symmetry (nsym)
		*/
		virtual int get_nsym() const { return params["nsym"]; };
		
		
		/** Gets the maximum symmetry of this object. This is used by OrientationGenerators, and is
		 * probably not something a general user would utilize.
		 * @return the degree of of cyclic symmetry (nsym) - this is the maximum symmetry
		 */
		virtual int get_max_csym() const { return params["nsym"]; }
		
		/// The name of this class - used to access it from factories etc. Should be "c"
		static const string NAME;
		
		/** @param inc_mirror whether or not to include the mirror portion of the asymmetric unit
		 * @return a cyclic set of points which can be connected using great arcs on the unit sphere
		 * to demarcate the asymmetric unit. The last should may be connected to the first.
		 */
		virtual vector<Vec3f> get_asym_unit_points(bool inc_mirror = false) const;
		
		/** A function to be used when generating orientations over portion of the unit sphere
		 * defined by parameters returned by get_delimiters. In platonic symmetry altitude and azimuth
		 * alone are not enough to correctly demarcate the asymmetric unit. See the get_delimiters comments.
		 * @param altitude the EMAN style altitude of the 3D orientation in degrees 
		 * @param azimuth the EMAN style azimuth of the 3D orientation in degrees
		 * @param inc_mirror whether or not to include orientations if they are in the mirror portion of the asymmetric unit
		 * @return true or false, depending on whether or not the orientation is within the asymmetric unit
		 */
		virtual bool is_in_asym_unit(const float& altitude, const float& azimuth, const bool inc_mirror) const;
		
		/** Returns true - this is indeed a c symmetry object
		 * @return true - indicating that this is a c symmetry object
		 */
		virtual bool is_c_sym() const { return  true; }
		
		
		/** Get triangles that precisely occlude the projection area of the default asymmetric unit. This is used
		 * for collision detection in Symmetry3D::reduce
		 * @param inc_mirror whether to include the mirror portion of the asymmetric unit
		 */
		virtual vector<vector<Vec3f> > get_asym_unit_triangles(bool inc_mirror) const;
		

// PRB see here
// 		virtual Transform3D reduce(const Transform3D& t3d, int n=0);
	};
	
	/** An encapsulation of dihedral 3D symmetry
	 * @author David Woolford (based on previous work by Phil Baldwin and Steve Ludtke)
	 * @date Feb 2008
	 */
	class DSym : public Symmetry3D
	{
		public:
		DSym() {};
		virtual  ~DSym() {};
		
		/** Factory support function NEW
		 * @return a newly instantiated class of this type
		 */
		static Symmetry3D *NEW()
		{
			return new DSym();
		}
		
		/** Return DSym::NAME
		 * @return the unique name of this class
		 */
		virtual string get_name() const { return NAME; }
		
		/** Get a description
		 * @return a clear desciption of this class
		 */
		virtual string get_desc() const { return "D symmetry support"; }
		
		/** Get a dictionary containing the permissable parameters of this class
		 * @return a dictionary containing the permissable parameters of this class
		 */
		virtual TypeDict get_param_types() const
		{
			TypeDict d;
			d.put("nsym", EMObject::INT, "The symmetry number");
			return d;
		}
		
		/** Get the altitude and phi angle of the d symmetry, which depends on nysm.
		 * The "alt_max" is always 90 degrees
		 * The "az_max" is 360/nsym degrees of 180/nsym, depending the inc_mirror argument
		 * @param inc_mirror whether or not to include the part of the asymmetric unit which contains the mirror projections of the other half
		 * @return a dictionary containing the keys "alt_max" and "az_max"
		 * @exception InvalidValueException if nsym is less than or equal to zero
		 */
		virtual Dict get_delimiters(const bool inc_mirror=false) const;
		
		/** Provides access to the complete set of rotational symmetry operations associated with this symmetry.
		 * The first half symmetry operations returned by this function are all about the z axis (i.e. only azimuth
		 * is non zero. The second half of the symmetry operations are replicas of the first half, except that they
		 * have an additional 180 degree rotation about x (in EMAN terms, the altitude angle is 180).
		 * @param n the rotational symmetry operation number. If n is greater than nsym we take n modulo nsym 
		 * @return a transform3d containing the correct rotational symmetric operation.
		 * @exception InvalidValueException if nsym is less than or equal to zero
		 */
		virtual Transform3D get_sym(int n) const;
		
		/** Gets the total number of unique roational symmetry operations associated with this symmetry
		 * For D symmetry, this is simply 2*nsym
		 * @return two times nsym
		 */
		virtual int get_nsym() const { return 2*(int)params["nsym"]; };
		
		
		/** Gets the maximum symmetry of this object. This is used by OrientationGenerators, and is
		 * probably not something a general user would utilize.
		 * @return nsym - this is the maximum symmetry about a given any axis for D symmetry
		 */
		virtual int get_max_csym() const { return params["nsym"]; }
		
		/** @param inc_mirror whether or not to include the mirror portion of the asymmetric unit
		 * @return a cyclic set of points which can be connected using great arcs on the unit sphere
		 * to demarcate the asymmetric unit. The last should may be connected to the first.
		 */
		virtual vector<Vec3f> get_asym_unit_points(bool inc_mirror = false) const;
		
		/** A function to be used when generating orientations over portion of the unit sphere
		 * defined by parameters returned by get_delimiters. In platonic symmetry altitude and azimuth
		 * alone are not enough to correctly demarcate the asymmetric unit. See the get_delimiters comments.
		 * @param altitude the EMAN style altitude of the 3D orientation in degrees 
		 * @param azimuth the EMAN style azimuth of the 3D orientation in degrees
		 * @param inc_mirror whether or not to include orientations if they are in the mirror portion of the asymmetric unit
		 * @return true or false, depending on whether or not the orientation is within the asymmetric unit
		 */
		virtual bool is_in_asym_unit(const float& altitude, const float& azimuth, const bool inc_mirror) const;
		
		/// The name of this class - used to access it from factories etc. Should be "d"
		static const string NAME;
		
		/** Returns true - this is indeed a c symmetry object
		 * @return true - indicating that this is a c symmetry object
		 */
		virtual bool is_d_sym() const { return  true; }
		
		/** Get triangles that precisely occlude the projection area of the default asymmetric unit. This is used
		 * for collision detection in Symmetry3D::reduce
		 * @param inc_mirror whether to include the mirror portion of the asymmetric unit
		 */
		virtual vector<vector<Vec3f> > get_asym_unit_triangles(bool inc_mirror) const;
	};
	
	/** An encapsulation of helical 3D symmetry
	 * @author David Woolford (based on previous work by Phil Baldwin and Steve Ludtke)
	 * @date Feb 2008
	 */
	class HSym : public Symmetry3D
	{
		public:
			HSym() {};
			virtual  ~HSym() {};
		
			/** Factory support function NEW
			 * @return a newly instantiated class of this type
			 */
			static Symmetry3D *NEW()
			{
				return new HSym();
			}
		
			/** Return HSym::NAME
			 * @return the unique name of this class
			 */
			virtual string get_name() const { return NAME; }

			/** Get a description
			 * @return a clear desciption of this class
			 */
			virtual string get_desc() const { return "H symmetry support"; }
		
			/** Get a dictionary containing the permissable parameters of this class
			 * Of all the symmetries, helical has the most options. This is because
			 * different approaches have to taken in regard to defining an asymmetric unit
			 * and to returning the set of rotational and translational symmetry operations
			 * @return a dictionary containing the permissable parameters of this class
			 */
			virtual TypeDict get_param_types() const
			{
				TypeDict d;
				d.put("nsym", EMObject::INT, "The symmetry number of the helix, around the equator.");
				d.put("equator_range", EMObject::FLOAT, "The amount altitude angles are allowed to vary above and below the equator. Default is 5");
				d.put("dz", EMObject::FLOAT, "The translational distance (along z) between succesive identical subunits in angstrom (default a/pix is 1)");
				d.put("daz", EMObject::FLOAT, "The rotational angle (about z) between successive identical subunits in degrees");
				d.put("apix", EMObject::FLOAT, "Angstrom per pixel, default is one.");
				return d;
			}
		
			/** Get the altitude and phi angle of the d symmetry, which depends on nysm.
			* The "alt_max" is always 90 + the "equator_range" variable in the internally stored params
			* The "alt_min" veriable is always 90.
			* The "az_max" is always 360/nsym degrees
			* Helical symmetry argument is the only symmetry not to act on the inc_mirror argument. The current policy
			* is the orientation generator using this symmetry should make its own accomodation for the inclusion of
			* mirror orientations if the symmetry is helical (hence the presence of the is_h_sym function in 
			* the Symmetry3D class). 
			* @param inc_mirror this parameter is not specifically acted upon in this class
			* @return a dictionary containing the keys "alt_max" and "az_max" and "alt_min"
			* @exception InvalidValueException if nsym is less than or equal to zero
			*/
			virtual Dict get_delimiters(const bool inc_mirror=false) const;
		
			
			/** Provides access to the complete set of rotational and translational symmetry operations
			 * associated with helical symmetry. This symmetry operations are generated in a straightforward
			 * way from the parameters of this class, specifically the return Transform3D object has an 
			 * azimuth of n times the "d_az" (as specified in the parameters of this class), and has a post
			 * translation of "dz" in the z direction.
			 * @param n the helical symmetry operation number.
			 * @return a transform3d containing the correct rotational and translational symmetry operation.
			 */
			virtual Transform3D get_sym(int n) const;
	
			/** For symmetries in general this function is supposed to return the number
			 * of unique symmetric operations that can be applied for the given Symmetry3D object.
			 * However, for helical symmetry it is possible that the there are infinitely many
			 * symmetric operations. So there is no general answer to return here. So,
			 * as a hack,  the answer returned is the number of rotional steps
			 * (as specified by the "d_az" paramater) that can be applied before surpassing 360 degrees.
			 * @return the number of symmetric rotations that can be applied without going beyond 360 degrees
			 * @exception InvalidValueException if d_az (as stored internally in parms) is less than or equal to zero
			 */
			virtual int get_nsym() const {
				float daz = params.set_default("daz",0.0f);
				if ( daz <= 0 ) throw InvalidValueException(daz,"Error, you must specify a positive non zero d_az");
				return static_cast<int>(360.0/daz);
			};
			
			/** Gets the maximum cylcic symmetry exhibited by this object. This is used by OrientationGenerators, and is
			 * probably not something a general user would utilize.
			 * @return nsym - this is the symmetry of the helix
			 */
			virtual int get_max_csym() const { return params["nsym"]; }
		
			/// The name of this class - used to access it from factories etc. Should be "h"
			static const string NAME;
			
			/** Determines whether or not this Symmetry3D is the helical type - returns true
			* @return true - indicating that this is a helical symmetry object
			*/
			virtual bool is_h_sym() const { return true; }
			
			/** A function to be used when generating orientations over portion of the unit sphere
			 * defined by parameters returned by get_delimiters. In platonic symmetry altitude and azimuth
			 * alone are not enough to correctly demarcate the asymmetric unit. See the get_delimiters comments.
			 * @param altitude the EMAN style altitude of the 3D orientation in degrees 
			 * @param azimuth the EMAN style azimuth of the 3D orientation in degrees
			 * @param inc_mirror whether or not to include orientations if they are in the mirror portion of the asymmetric unit
			 * @return true or false, depending on whether or not the orientation is within the asymmetric unit
			 */
			virtual bool is_in_asym_unit(const float& altitude, const float& azimuth, const bool inc_mirror) const;
			
			/** @param inc_mirror whether or not to include the mirror portion of the asymmetric unit
			 * @return a cyclic set of points which can be connected using great arcs on the unit sphere
			 * to demarcate the asymmetric unit. The last should may be connected to the first.
			 */
			virtual vector<Vec3f> get_asym_unit_points(bool inc_mirror = false) const;
			
			/** Get triangles that precisely occlude the projection area of the default asymmetric unit. This is used
			 * for collision detection in Symmetry3D::reduce
			 * @param inc_mirror whether to include the mirror portion of the asymmetric unit
			 */
			virtual vector<vector<Vec3f> > get_asym_unit_triangles(bool inc_mirror) const;
	};
	
	/** A base (or parent) class for the Platonic symmetries. It cannot be instantieted on its own.
	 * Doctor Phil says:
	 * "see www.math.utah.edu/~alfeld/math/polyhedra/polyhedra.html for pictures of platonic solids"
	 * Also, see http://blake.bcm.edu/emanwiki/EMAN2/Symmetry for a good pictorial description of what's going on here
	 * This class has a fundamental role to play in terms of the Platonic symmetries that derive from it.
	 * It is based heavily on the manuscript  Baldwin and Penczek, 2007. The Transform Class in SPARX and
	 * EMAN2. JSB 157(250-261), where the important angles of the asymmetric units in Platonic solids are 
	 * described. The MOST IMPORTANT THING TO NOTE is anything that derives from this class must call init()
	 * in its constructor. However, because it is unlikey that any class will inherit from this one seeing 
	 * as the set of Platonic symmetries is finite.
	 * @author David Woolford (based on previous work by Phil Baldwin and Steve Ludtke)
	 * @date Feb 2008
	 */
	class PlatonicSym : public Symmetry3D
	{
		public:
		PlatonicSym() {};
		virtual  ~PlatonicSym() {};
		
		/** Get a dictionary containing the permissable parameters of this class
		 * Platonic symmetries actually have no parameters.
		 * @return a dictionary containing the permissable parameters of this class  ( which is none)
		 */
		virtual TypeDict get_param_types() const
		{
			TypeDict d;
			return d;
		}
		
		/** Returns the range of altitude and azimuth angles which encompass
		 * the asymmetric unit of the Platonic symmetry (and more). As a general
		 * rule you may generate your orientations evenly over the range altitude
		 * range as accessed by "alt_max" key in the return dictionary, and over
		 * the azimuth range as accessed by the "az_max", but your must call
		 * the function is_in_asym_unit as you do it, to accomodate for orientations
		 * in the range that are actually beyond the asymmetric unit. See 
		 * http://blake.bcm.edu/emanwiki/EMAN2/Symmetry for pictures and descriptions.
		 * If the inc_mirror is true, the return "az_max" key is twice as large as if not,
		 * but only if the platonic symmetry is Icos or Oct. If the symmetry is Tet, the
		 * mirror considerations are taken into account in is_in_asym_unit. This is a bit
		 * of a design flaw, but it works.
		 * @param inc_mirror whether or not to consider the mirror portion of the asymmetric unit (only changes the return values if the symmetry is Icos or Oct)
		 * @return a dictionary containing the "az_max" and "alt_max" keys which define angles, in degrees
		 */
		virtual Dict get_delimiters(const bool inc_mirror=false) const;
		
		/** A function to be used when generating orientations over portion of the unit sphere
		 * defined by parameters returned by get_delimiters. altitude and azimuth alone are not
		 * enough to correctly demarcate the asymmetric unit. See the get_delimiters comments.
		 * @param altitude the EMAN style altitude of the 3D orientation in degrees 
		 * @param azimuth the EMAN style azimuth of the 3D orientation in degrees
		 * @param inc_mirror whether or not to include orientations if they are in the mirror portion of the asymmetric unit
		 * @return true or false, depending on whether or not the orientation is within the asymmetric unit
		*/
		virtual bool is_in_asym_unit(const float& altitude, const float& azimuth, const bool inc_mirror) const;
		
		/** Determines whether or not this Symmetry3D is the platonic type - returns true
		 * @return true - indicating that this is a platonic symmetry object
		 */
		virtual bool is_platonic_sym() const { return true; }
		
		protected:
		/// A dictionary that stores important angles, in radians
		Dict platonic_params;

		/** Init - Called to initialize platonic_params, should be called in the constructor of all
		 * Platonic solids that derive from this. This function generates the important angles
		 * of the platonic symmetries which is dependent only on the function get_max_csym ( which
		 * must be defined in all classes that inherit from this class)
		 */
		void init();
		
		/** Returns the lower bound of the asymmetric unit, as dependent on azimuth, and on alpha -
		 * alpha is alt_max for icos and oct, but may be alt_max/2.0 for tet depending on mirror
		 * symmetry etc
		 * @param azimuth an EMAN style 3D azimuth angle, in radians
		 * @param alpha an EMAN style altitude angle that helps to define arcs on the unit sphere. See Baldwin and Penczek, 2007. The Transform Class in SPARX and EMAN2. JSB 157(250-261) where the angle alpha is described
		 * @return the altitude corresponding to the lower bound for the given azimuth, in radians
		 */
		float platonic_alt_lower_bound(const float& azimuth, const float& alpha) const;
		
		/** @param inc_mirror whether or not to include the mirror portion of the asymmetric unit
		 * @return a cyclic set of points which can be connected using great arcs on the unit sphere
		 * to demarcate the asymmetric unit. The last should may be connected to the first.
		 */
		virtual vector<Vec3f> get_asym_unit_points(bool inc_mirror = false) const;
		
		/** Get triangles that precisely occlude the projection area of the default asymmetric unit. This is used
		 * for collision detection in Symmetry3D::reduce
		 * @param inc_mirror whether to include the mirror portion of the asymmetric unit
		 */
		virtual vector<vector<Vec3f> > get_asym_unit_triangles(bool inc_mirror) const;
	};
	
	/** An encapsulation of tetrahedral symmetry
	 * Doctor Phil has this to say about tetrahedral symmetry:
	 * " Each Platonic Solid has 2E symmetry elements.
	 *	 The tetrahedron has n=m=3; F=4, E=6=nF/2, V=4=nF/m.
	 *   It is composed of four triangles."
	 * @author David Woolford (based on previous work by Phil Baldwin and Steve Ludtke)
	 * @date Feb 2008
	*/
	class TetrahedralSym : public PlatonicSym
	{
		public:
		/** Constructor calls PlatonicSym::init
		*/
		TetrahedralSym()  {init();}
		virtual  ~TetrahedralSym() {}
		
		/** Factory support function NEW
		 * @return a newly instantiated class of this type
		 */
		static Symmetry3D *NEW()
		{
			return new TetrahedralSym();
		}
		
		/** Return TetrahedralSym::NAME
		 * @return the unique name of this class
		 */
		virtual string get_name() const { return NAME; }


		/** Get a description
		 * @return a clear desciption of this class
		 */
		virtual string get_desc() const { return "Tetrahedral symmetry support"; }

		/** Gets the maximum symmetry of this object. This is used by OrientationGenerators, and is
		 * probably not something a general user would utilize.
		 * @return for tetrahedral symmetry, this number is 3
		 */
		virtual int get_max_csym() const { return 3; }
		
		/** This function provides access to the unique rotational symmetries of a tetrahedron.
		 * In this implementation, the tetrahedral symmetry group has a face along the z-axis. In all, there are
		 * 12 (accessed by get_nysm) unique rotational symmetric operations for the tetrahedron. 
		 * In the terminology defined Append A (titled Symmetry Elements) in the manuscript  Baldwin and Penczek, 2007.
		  * The Transform Class in SPARX and EMAN2. JSB 157(250-261), Doctor Phil has this to say:
		 * "B^3=A^3=1;  BABA=1; implies   A^2=BAB, ABA=B^2 , AB^2A = B^2AB^2 and
		 *  12 words with at most a single A
		 *  1 B BB  A  BA AB BBA BAB ABB BBAB BABB BBABB
		 *  at most one A is necessary"
		 * @param n the symmetric operation number
		 * @return a transform3d containing the correct rotational symmetry operation.
		*/
		virtual Transform3D get_sym(int n) const;
		
		/** In tetrahedral symmetry special consideration must be taken when generating orientations 
		 * in the asymmetric unit. This function is a specialization of the functionality in 
		 * PlatonicSym::is_in_asym_unit
		 * @param altitude the EMAN style altitude of the 3D orientation in degrees 
		 * @param azimuth the EMAN style azimuth of the 3D orientation in degrees
		 * @param inc_mirror whether or not to include orientations if they are in the mirror portion of the asymmetric unit
		 * @return true or false, depending on whether or not the orientation is within the asymmetric unit
		 */
		virtual bool is_in_asym_unit(const float& altitude, const float& azimuth, const bool inc_mirror) const;
		
		/** Gets the total number of unique roational symmetry operations associated with this symmetry
		 * For tetrahedral symmetry symmetry, this is 12
		 * @return 12
		 */
		virtual int get_nsym() const { return 12; };
		
		/** Get the azimuth alignment offset required to ensure that orientations align correctly
		 * with symmetric axes of the tetrahedron. This offset is directly related to the way
		 * the symmetric operations are generated by get_sym. All orientations generated as a 
		 * result of using the delimiters supplied by this class should by offset by this azimuth
		 * to ensure proper alignment with tetrahedral objects in EMAN2
		 */
		virtual float get_az_alignment_offset() const;
		
		/// The name of this class - used to access it from factories etc. Should be "tet"
		static const string NAME;
		
		/** @param inc_mirror whether or not to include the mirror portion of the asymmetric unit
		 * @return a cyclic set of points which can be connected using great arcs on the unit sphere
		 * to demarcate the asymmetric unit. The last should may be connected to the first.
		 */
		virtual vector<Vec3f> get_asym_unit_points(bool inc_mirror = false) const;
		
		/** A function that is used to determine if this is the tetrahedral symmetry object
		 * @return true - indicating that this is not a tetrahedral symmetry object
		 */
		virtual bool is_tet_sym() const { return true; }
		
		
	};
	
	/** An encapsulation of octahedral symmetry
	* Doctor Phil has this to say about the octahedral symmetry:
	* "Each Platonic Solid has 2E symmetry elements.
	* "A cube has   m=3, n=4, F=6 E=12=nF/2, V=8=nF/m,since vertices shared by 3 squares;
	*  It is composed of 6 squares.
	*  An octahedron has   m=4, n=3, F=8 E=12=nF/2, V=6=nF/m,since vertices shared by 4 triangles"
	 * @author David Woolford (based on previous work by Phil Baldwin and Steve Ludtke)
	 * @date Feb 2008
	*/
	
	class OctahedralSym : public PlatonicSym
	{
		public:
		/** Constructor calls PlatonicSym::init
		*/
		OctahedralSym()  {init();}
		virtual  ~OctahedralSym() {}
		
		/** Factory support function NEW
		 * @return a newly instantiated class of this type
		 */
		static Symmetry3D *NEW()
		{
			return new OctahedralSym();
		}
		
		/** Return OctahedralSym::NAME
		 * @return the unique name of this class
		 */
		virtual string get_name() const { return NAME; };

		/** Get a description
		 * @return a clear desciption of this class
		 */
		virtual string get_desc() const { return "Octahedral symmetry support"; }

		/** Gets the maximum symmetry of this object. This is used by OrientationGenerators, and is
		 * probably not something a general user would utilize.
		 * @return for octahedral symmetry, this number is 4
		 */
		virtual int get_max_csym() const { return 4; }
		
		/** This function provides access to the unique rotational symmetries of an octahedron.
		 * We have placed the octahedral symmetry group with a face along the z-axis. In all, there are
		 * 24 (accessed by get_nysm) unique rotational symmetric operations for the octahedron. 
		 * In the terminology defined Append A (titled Symmetry Elements) in the manuscript  Baldwin and Penczek, 2007.
		 * The Transform Class in SPARX and EMAN2. JSB 157(250-261), Doctor Phil has this to say:
		 * "B^4=A^3=1;  BABA=1; implies   AA=BAB, ABA=B^3 , AB^2A = BBBABBB and
		 *  20 words with at most a single A
		 *  1 B BB BBB A  BA AB BBA BAB ABB BBBA BBAB BABB ABBB BBBAB BBABB BABBB 
		 *  BBBABB BBABBB BBBABBB 
		 *  also ABBBA is distinct yields 4 more words
		 *  ABBBA BABBBA BBABBBA BBBABBBA
		 *  for a total of 24 words
		 *  Note A BBB A BBB A  reduces to BBABB
		 *  and B A BBB A is the same as A BBB A BBB etc."
		 * @param n the symmetric operation number. 
		 * @return a transform3d containing the correct rotational symmetry operation.
		 */
		virtual Transform3D get_sym(int n) const;
		
		/** Gets the total number of unique roational symmetry operations associated with this symmetry
		 * For octahedral symmetry this is 24
		 * @return 24
		 */
		virtual int get_nsym() const { return 24; };
		
		/// The name of this class - used to access it from factories etc. Should be "oct"
		static const string NAME;
	};
	
	/** An encapsulation of icosahedral symmetry
	* Doctor Phil has this to say about icosahedral symmetry:
	* "Each Platonic Solid has 2E symmetry elements.
	* An icosahedron has   m=5, n=3, F=20 E=30=nF/2, V=12=nF/m,since vertices shared by 5 triangles
	* It is composed of 20 triangles. E=3*20/2
	* A  dodecahedron has m=3, n=5   F=12 E=30  V=20
	* It is composed of 12 pentagons. E=5*12/2;   V= 5*12/3, since vertices shared by 3 pentagons"
	 * @author David Woolford (based on previous work by Phil Baldwin and Steve Ludtke)
	 * @date Feb 2008
	*/
	class IcosahedralSym : public PlatonicSym
	{
		public:
		/** Constructor calls PlatonicSym::init
		 */
		IcosahedralSym() {init(); }
		virtual  ~IcosahedralSym() { }
		
		/** Factory support function NEW
		 * @return a newly instantiated class of this type
		 */
		static Symmetry3D *NEW()
		{
			return new IcosahedralSym();
		}
			
		/** Return IcosahedralSym::NAME
		 * @return the unique name of this class
		 */
		virtual string get_name() const { return NAME; };
		
		/** Get a description
		 * @return a clear desciption of this class
		 */
		virtual string get_desc() const { return "Icosahedral symmetry support"; }
	
		/** Gets the maximum symmetry of this object. This is used by OrientationGenerators, and is
		 * probably not something a general user would utilize.
		 * @return for icosahedral symmetry, this number is 5
		 */
		virtual int get_max_csym() const { return 5; }// 5 is the greatest symmetry
		
		/** This function provides access to the unique rotational symmetries of an icosahedron.
		 * We have placed the icosahedral symmetry group with a face along the z-axis. In all, there are
		 * 60 (accessed by get_nysm) unique rotational symmetric operations for the icosahedron. 
		 * @param n the symmetric operation number. 
		 * @return a transform3d containing the correct rotational symmetry operation.
		 */
		virtual Transform3D get_sym(int n) const;
		
		/** Gets the total number of unique roational symmetry operations associated with this symmetry
		 * For icosahedral symmetry, this is 60
		 * @return 60
		 */
		virtual int get_nsym() const { return 60; };
		
		/** Get the azimuth alignment offset required to ensure that orientations align correctly
		 * with symmetric axes of the icosahedron. This offset is directly related to the way
		 * the symmetric operations are generated by get_sym. All orientations generated as a 
		 * result of using the delimiters supplied by this class should by offset by this azimuth
		 * to ensure proper alignment with tetrahedral objects in EMAN2
		 */
		virtual float get_az_alignment_offset() const;
		
		/// The name of this class - used to access it from factories etc. Should be "icos"
		static const string NAME;
	};
	/// A template specialization for the Symmetry3D factory. Adds all of the symmetries
	template <> Factory < Symmetry3D >::Factory();
	/// A template specialization for get - so people can call get with strings like "c1","d4" etc - this avoids have to use Dicts to specify the nsym
	template <> Symmetry3D* Factory < Symmetry3D >::get(const string & instancename);
	/// dump symmetries, useful for obtaining symmetry information
	void dump_symmetries();
	/// dump_symmetries_list, useful for obtaining symmetry information
	map<string, vector<string> > dump_symmetries_list();
	
	/** An orientation generator is a kind of class that will generate orientations for a given symmetry
	 * If one needs to generate orientations in the unit sphere, one simply uses the C1 symmetry.
	 * It inherits from a factory base, making it amenable to incorporation in EMAN2 style factories.
	 * Objects that inherit from this class must write a gen_orientations function, in addition to 
	 * fulfilling the responsibilities of the FactoryBase class
	 * @author David Woolford 
	 * @date Feb 2008
	 */
	class OrientationGenerator : public FactoryBase
	{
	public:
		OrientationGenerator() {};
		virtual ~OrientationGenerator() {};
		
		/** generate orientations given some symmetry type
		 * @param sym the symmetry which defines the interesting asymmetric unit
		 * @return a vector of Transform3D objects containing the generated set of orientations
		 */
		virtual vector<Transform3D> gen_orientations(const Symmetry3D* const sym) const  = 0;
		
		virtual TypeDict get_param_types() const
		{
			TypeDict d;
			d.put("phitoo", EMObject::FLOAT,  "Specifying a non zero value for this argument will cause phi rotations to be included. The value specified is the angular spacing of the phi rotations in degrees. The default for this value is 0, causing no extra phi rotations to be included.");
			d.put("random_phi", EMObject::BOOL,  "Causes the orientations to have a random phi. This occurs before the phitoo parameter is considered.");
			return d;
		}
		
		/** This functions adds one or more Transform3D objects to the vector v, depending
		 * on the parameters stored in the dictionary (which the inheriting class may
		 * include by initializing the typedict in get_param_types by calling 
		 *
		 * @code
		 * TypeDict d = OrientationGenerator::get_param_types();
		 * @endcode
		 *
		 * to initialize. If phitoo is no zero, this cause extra orientations to be included in phi (in steps of phitoo).
		 * If random_phi is true, the phi of the Transform3D object is randomized.
		 * This function is for internal convenience of child classes.
		 * @param v the vector to add Transform3D objects to
		 * @param az the azimuth to be used as a basis for generated Transform3D objects (in degrees)
		 * @param alt the altitude to be used as a basis for generated Transform3D objects (in degrees)
		 * @return and indication of success (true or false). False is only ever return if phitoo is less than 0.
		 */
		bool add_orientation(vector<Transform3D>& v, const float& az, const float& alt) const;
		
		
		
		/** This function gets the optimal value of the delta (or angular spacing) of the orientations
		* based on a desired total number of orientations (n). It does this using a bifurcation strategy,
		* calling get_orientations_tally (which must be supplied by the child class)
		* using the next best guess etc. The solution may not exist (simply  because the
		* orientation generation strategy does not contain it), so a best guess may be returned.
		*
		* The inheriting class must supply the get_orientations_tally function, which returns
		* the number of orientations generated (an int), for a given delta.
		*
		* @param sym the symmetry which defines the interesting asymmetric unit
		* @param n the desired number of orientations
		* @return the optimal value of delta to ensure as near to the desired number of orientations is generated
		*/
		float get_optimal_delta(const Symmetry3D* const sym, const int& n) const;

		/** This function returns how many orientations will be generated for a given delta (angular spacing)
		* It should general do this by simulating the function gen_orientations
		* @param sym the symmetry which defines the interesting asymmetric unit
		* @param delta the desired angular spacing of the orientations
		* @return the number of orientations that will be generated using these parameters
		*/
		virtual int get_orientations_tally(const Symmetry3D* const sym, const float& delta) const = 0;

	};
	
	
		
	 /** EmanOrientationGenerator generates orientations quasi-evenly distributed in the asymmetric unit.
	 * Historically, it is an adaptation of the method first used in EMAN1 and developed by Steve
	 * Ludtke. In EMAN2 it is more or less the same thing, but with more precise treatmeant of the
	 * platonic symmetries. In terms of approach, the altitude angles in the asymmetric unit are traversed
	 * constantly in steps of "prop" (a parameter of this class). However, the azimuth steps vary according
	 * to altitude, and this helps to achieve a more even distribution of orientations.
	 * @author David Woolford (based on previous work by Phil Baldwin and Steve Ludtke)
	 * @date Feb 2008
	 */
	class EmanOrientationGenerator : public OrientationGenerator
	{
	public:
		EmanOrientationGenerator() {};
		virtual  ~EmanOrientationGenerator() {};
		
		/** Factory support function NEW
		 * @return a newly instantiated class of this type
		 */
		static OrientationGenerator *NEW()
		{
			return new EmanOrientationGenerator();
		}
		
		/** Return 	"eman"
		 * @return the unique name of this class
		 */
		virtual string get_name() const { return NAME; }

		/** Get a description
		 * @return a clear desciption of this class
		 */
		virtual string get_desc() const { return "Generate orientations distributed quasi-uniformaly over the asymmetric unit using an altitude-proportional strategy"; }
		
		/** Get a dictionary containing the permissable parameters of this class
		 * @return a dictionary containing the permissable parameters of this class
		 * parameters are explained in the dictionary itself
		 */
		virtual TypeDict get_param_types() const
		{
			TypeDict d = OrientationGenerator::get_param_types();
			d.put("delta", EMObject::FLOAT, "The angular separation of orientations in degrees. This option is mutually exclusively of the n argument.");
			d.put("perturb", EMObject::BOOL, "Whether or not to perturb the generated orientations in a small local area, default is false.");
			d.put("n", EMObject::INT, "The number of orientations to generate. This option is mutually exclusively of the delta argument.Will attempt to get as close to the number specified as possible.");
			d.put("inc_mirror", EMObject::BOOL, "Indicates whether or not to include the mirror portion of the asymmetric unit. Default is false.");
			return d;
		}
		
		/** generate orientations given some symmetry type
		 * @param sym the symmetry which defines the interesting asymmetric unit
		 * @return a vector of Transform3D objects containing the set of evenly distributed orientations
		 */
		virtual vector<Transform3D> gen_orientations(const Symmetry3D* const sym) const;
		
		/// The name of this class - used to access it from factories etc. Should be "icos"
		static const string NAME;
	private:
		/** This function returns how many orientations will be generated for a given delta (angular spacing)
		 * It does this by simulated gen_orientations.
		 * @param sym the symmetry which defines the interesting asymmetric unit
		 * @param delta the desired angular spacing of the orientations
		 * @return the number of orientations that will be generated using these parameters
		 */
		virtual int get_orientations_tally(const Symmetry3D* const sym, const float& delta) const;
		
		
		/** Gets the optimum azimuth delta (angular step) for a given altitude, delta and 
		 * maximum symmetry. This function is important for the generation of evenly distributed
		 * orientations
		 * @param delta - the angular spacing of the altitude angles, this is usually the "delta" parameter
		 * @param altitude the altitude along which the azimuth is going to be varied
		 * @param maxcsym the maximum csym of the Symmetry3D object - this is usually Symmetry3D::get_max_csym
		 * @return the optimal azimuth angular spacing
		*/
		float get_az_delta(const float& delta,const float& altitude, const int maxcsym) const;
		
	};	
	
	/** Random Orientation Generator - carefully generates uniformly random orientations in any asymmetric unit.
	 *  For points distributed in the unit sphere, just use the CSym type with nysm = 1.
	 * (i.e. c1 symmetry)
	 * @author David Woolford
	 * @date March 2008
	 */
	class RandomOrientationGenerator : public OrientationGenerator
	{
		public:
		RandomOrientationGenerator() {}
		virtual ~RandomOrientationGenerator() {}
		
		/** Factory support function NEW
		* @return a newly instantiated class of this type
		*/
		static OrientationGenerator *NEW()
		{
			return new RandomOrientationGenerator();
		}
		
		/** Return 	"random"
		 * @return the unique name of this class
		 */
		virtual string get_name() const { return NAME; }

		/** Get a description
		 * @return a clear desciption of this class
		 */
		virtual string get_desc() const { return "Generate random orientations within an asymmetric unit"; }
		
		/** Get a dictionary containing the permissable parameters of this class
		 * @return a dictionary containing the permissable parameters of this class
		 * parameters are explained in the dictionary itself
		 */
		virtual TypeDict get_param_types() const
		{
			TypeDict d;
			d.put("n", EMObject::INT, "The number of orientations to generate.");
			d.put("inc_mirror", EMObject::BOOL, "Indicates whether or not to include the mirror portion of the asymmetric unit. Default is false.");
			return d;
		}
		
		/** Generate random orientations in the asymmetric unit of the symmetry
		 * @param sym the symmetry which defines the interesting asymmetric unit
		 * @return a vector of Transform3D objects containing the set of evenly distributed orientations
		 */
		virtual vector<Transform3D> gen_orientations(const Symmetry3D* const sym) const;
		
		/// The name of this class - used to access it from factories etc.
		static const string NAME;
		
		virtual int get_orientations_tally(const Symmetry3D* const sym, const float& delta) const { (void)sym; (void)delta; return 0; }
	};
	
	/**Sparx even orientation generator - see util_sparx.cpp - Util::even_angles(...)
	 * This orientation generator is based on work presented in Penczek et al., 1994 P.A. Penczek, R.A.
	 * Grassucci and J. Frank, The ribosome at improved resolution: new techniques for merging and 
	 * orientation refinement in 3D cryo-electron microscopy of biological particles, Ultramicroscopy 53 (1994).
	 * 
	 * This is a proportional approach very similar to the eman approach - the differences between these
	 * two approaches is mostly visible near altitude=0
	 *
	 * @author David Woolford (ported directly from Sparx utilities.py, which is written by Pawel Penczek)
	 * @date March 2008
	 */
	class EvenOrientationGenerator : public OrientationGenerator
	{
		public:
		EvenOrientationGenerator() {}
		virtual ~EvenOrientationGenerator() {}
		
		/** Factory support function NEW
			 * @return a newly instantiated class of this type
		 */
		static OrientationGenerator *NEW()
		{
			return new EvenOrientationGenerator();
		}
		
		
		/** Return 	"even"
			* @return the unique name of this class
		*/
		virtual string get_name() const { return NAME; }

		/** Get a description
		 * @return a clear desciption of this class
		 */
		virtual string get_desc() const { return "Generate quasi-evenly distributed orientations within an asymmetric unit using Penczek's (94) approach"; }
		
		/** Get a dictionary containing the permissable parameters of this class
		 * @return a dictionary containing the permissable parameters of this class
		 * parameters are explained in the dictionary itself
		 */
		virtual TypeDict get_param_types() const
		{
			TypeDict d = OrientationGenerator::get_param_types();
			d.put("delta", EMObject::FLOAT, "The angular separation of orientations in degrees. This option is mutually exclusively of the n argument.");
			d.put("inc_mirror", EMObject::BOOL, "Indicates whether or not to include the mirror portion of the asymmetric unit. Default is false.");
			d.put("n", EMObject::INT, "The number of orientations to generate. This option is mutually exclusively of the delta argument.Will attempt to get as close to the number specified as possible.");
			return d;
		}
		
		/** Generate even distributed orientations in the asymmetric unit of the symmetry
		 * @param sym the symmetry which defines the interesting asymmetric unit
		 * @return a vector of Transform3D objects containing the set of evenly distributed orientations
		 */
		virtual vector<Transform3D> gen_orientations(const Symmetry3D* const sym) const;
		
		/// The name of this class - used to access it from factories etc. Should be "icos"
		static const string NAME;
		private:
		/** This function returns how many orientations will be generated for a given delta (angular spacing)
		 * It does this by simulated gen_orientations.
		 * @param sym the symmetry which defines the interesting asymmetric unit
		 * @param delta the desired angular spacing of the orientations
		 * @return the number of orientations that will be generated using these parameters
		 */
		virtual int get_orientations_tally(const Symmetry3D* const sym, const float& delta) const;
	};
	
	/** Saff orientation generator - based on the work of Saff and Kuijlaars, 1997 E.B. Saff and A.B.J. Kuijlaars, Distributing many points on a sphere,
	 * Mathematical Intelligencer 19 (1997), pp. 5–11. This is a spiral based approach
	 * @author David Woolford (ported directly from Sparx utilities.py, which is written by Pawel Penczek)
	 * @date March 2008
	 */
	class SaffOrientationGenerator : public OrientationGenerator
	{
		public:
			SaffOrientationGenerator() {}
			virtual ~SaffOrientationGenerator() {}
		
			/** Factory support function NEW
			* @return a newly instantiated class of this type
			*/
			static OrientationGenerator *NEW()
			{
				return new SaffOrientationGenerator();
			}
			
			/** Return 	"saff"
			* @return the unique name of this class
			*/
			virtual string get_name() const { return NAME; }

			/** Get a description
			* @return a clear desciption of this class
			*/
			virtual string get_desc() const { return "Generate quasi-evenly distributed orientations within an asymmetric unit using a spiraling method attributed to Saff"; }
		
			/** Get a dictionary containing the permissable parameters of this class
			 * @return a dictionary containing the permissable parameters of this class
			 * parameters are explained in the dictionary itself
			 */
			virtual TypeDict get_param_types() const
			{
				TypeDict d = OrientationGenerator::get_param_types(); 
				d.put("n", EMObject::INT, "The number of orientations to generate. This option is mutually exclusively of the delta argument.Will attempt to get as close to the number specified as possible.");
				d.put("inc_mirror", EMObject::BOOL, "Indicates whether or not to include the mirror portion of the asymmetric unit. Default is false.");
				d.put("delta", EMObject::FLOAT, "The angular separation of orientations in degrees. This option is mutually exclusively of the n argument.");
				return d;
			}
		
			/** Generate Saff orientations in the asymmetric unit of the symmetry
			 * @param sym the symmetry which defines the interesting asymmetric unit
			 * @return a vector of Transform3D objects containing the set of evenly distributed orientations
			 */
			virtual vector<Transform3D> gen_orientations(const Symmetry3D* const sym) const;
			
			/// The name of this class - used to access it from factories etc. Should be "icos"
			static const string NAME;
		private:
			/** This function returns how many orientations will be generated for a given delta (angular spacing)
			 * It does this by simulated gen_orientations.
			 * @param sym the symmetry which defines the interesting asymmetric unit
			 * @param delta the desired angular spacing of the orientations
			 * @return the number of orientations that will be generated using these parameters
			 */
			virtual int get_orientations_tally(const Symmetry3D* const sym, const float& delta) const;
			
			// This was a function that paid special considerations to the overall algorithm in the
			// case of the Platonic symmetries, which have non trivial asymmetric units. But unfortunately
			// it was bug-prone, and the approach in place already seemed good enough
// 			vector<Transform3D> gen_platonic_orientations(const Symmetry3D* const sym, const float& delta) const;
	};
	
	
	/** Optimum orientation generator. Optimally distributes points on a unit sphere, then slices out
	 * a correctly sized asymmetric unit, depending on the symmetry type. The approach relies on an initial
	 * distribution of points on the unit sphere, which may be generated using any of the other orientation
	 * generators. By default, the Saff orientation generator is used.
	 *
	 * @author David Woolford 
	 * @date March 2008
	 */
	class OptimumOrientationGenerator : public OrientationGenerator
	{
		public:
			OptimumOrientationGenerator() {}
			virtual ~OptimumOrientationGenerator() {}
		
			/** Factory support function NEW
			 * @return a newly instantiated class of this type
			 */
			static OrientationGenerator *NEW()
			{
				return new OptimumOrientationGenerator();
			}
			
			/** Return 	"opt"
			 * @return the unique name of this class
			 */
			virtual string get_name() const { return NAME; }

			/** Get a description
			 * @return a clear desciption of this class
			 */
			virtual string get_desc() const { return "Generate optimally distributed orientations within an asymmetric using a basic optimization technique"; }
		
			/** Get a dictionary containing the permissable parameters of this class
			 * @return a dictionary containing the permissable parameters of this class
			 * parameters are explained in the dictionary itself
			 */
			virtual TypeDict get_param_types() const
			{
				TypeDict d = OrientationGenerator::get_param_types(); 
				d.put("n", EMObject::INT, "The number of orientations to generate. This option is mutually exclusively of the delta argument.Will attempt to get as close to the number specified as possible.");
				d.put("inc_mirror", EMObject::BOOL, "Indicates whether or not to include the mirror portion of the asymmetric unit. Default is false.");
				d.put("delta", EMObject::FLOAT, "The angular separation of orientations in degrees. This option is mutually exclusively of the n argument.");
				d.put("use", EMObject::STRING, "The orientation generation technique used to generate the initial distribution on the unit sphere.");
				return d;
			}
		
			/** Generate Saff orientations in the asymmetric unit of the symmetry
			 * @param sym the symmetry which defines the interesting asymmetric unit
			 * @return a vector of Transform3D objects containing the set of evenly distributed orientations
			 */
			virtual vector<Transform3D> gen_orientations(const Symmetry3D* const sym) const;
			
			/// The name of this class - used to access it from factories etc. Should be "icos"
			static const string NAME;
		private:
			/** This function returns how many orientations will be generated for a given delta (angular spacing)
			* It does this by simulated gen_orientations.
			* @param sym the symmetry which defines the interesting asymmetric unit
			* @param delta the desired angular spacing of the orientations
			* @return the number of orientations that will be generated using these parameters
			 */
			virtual int get_orientations_tally(const Symmetry3D* const sym, const float& delta) const;
			
			
			/// Optimize the distances in separating points on the unit sphere, as described by the
			/// the rotations in Transform3D objects.
			vector<Vec3f> optimize_distances(const vector<Transform3D>& v) const;
	};
	
	/// Template specialization for the OrientationGenerator class
	template <> Factory < OrientationGenerator >::Factory();
	/// Dumps useful information about the OrientationGenerator factory
	void dump_orientgens();
	/// Can be used to get useful information about the OrientationGenerator factory
	map<string, vector<string> > dump_orientgens_list();
	
}  // ends NameSpace EMAN



#endif


/* vim: set ts=4 noet: */
