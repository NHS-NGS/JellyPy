#!/usr/bin/python
"""
 
 Script to compare the variants in two vcf files, to ensure the 
 variants are the same. Everythig is compared but data in the 
 info field


 Kim Brugger (10 Jan 2018), contact: kim@brugger.dk
"""

import sys
import argparse
import pprint
pp = pprint.PrettyPrinter(indent=4)

import pysam



def handle_error( error, exit_on_error = False):
    """ Print the error, and if flag is set exits

    Args:
       error (str): error string to print
       exit_on_error (bool): default false, if true terminates the program after printing the error 

    """
    print( "{}".format(error))

    if ( exit_on_error ):
        exit(10)



def next_vcf_rec( vcf_handle ):
    """ reads next vcf record, or returns none

    Args:
      vcf_handle (obj): pysam vcf handle

    """
    try:
        vcf_rec = vcf_handle.next()
        return vcf_rec
    except:
        return None


def compare_vcfs( vcf_file1, vcf_file2, exit_on_error = False):
    """ compare variants and sample information in two vcfs to ensure their integrity
    
    Args:
       vcf_file1 (str): filename of vcf file nr 1
       vcf_file2 (str): filename of vcf file nr 2
       exit_on_error (bool): print error and exit program on first found error
    
    Returns:
       list of disconcodant variants
    """

    vcf1 = pysam.VariantFile( vcf_file1 )
    vcf2 = pysam.VariantFile( vcf_file2 )

    vcf1_samples = vcf1.header.samples
    vcf2_samples = vcf2.header.samples

    vcf1_rec = vcf1.next()
    vcf2_rec = vcf2.next()
            

    if ( list(vcf1_samples) != list(vcf2_samples) ):
        error  = "Sample name differs. VCF1: [{}], VCF2: [{}]".format(",".join(list(vcf1_samples)), ",".join(list(vcf2_samples)))
#        errors = handle_error( error, errors, exit_on_error  )

    while ( vcf1_rec is not None and vcf2_rec is not None ):

        error_string= "{type}\n[%s]\n[%s]" % (vcf1_rec, vcf2_rec)
#        print error_string
        errors = []
        # Check on the various fields and append to the error list that is printed later on.
        if ( vcf1_rec.chrom != vcf2_rec.chrom ):
            errors.append('chromosome')

        if ( vcf1_rec.pos != vcf2_rec.pos ):
            errors.append('chromosome')

        if ( vcf1_rec.id != vcf2_rec.id ):
            errors.append('ID')

        if ( vcf1_rec.alts != vcf2_rec.alts ):
            errors.append('Alts')

        # Some odd rounding errors and making strings into float bug,
        # so as long as the qual score is with in +/- 1 I am happy
        # with it.
        if ( abs(vcf1_rec.qual - vcf2_rec.qual) > 1 ):
        if ( vcf1_rec.qual != vcf2_rec.qual ):
            errors.append('qual')

        if ( vcf1_rec.filter != vcf2_rec.filter ):
            errors.append('filter')

        if ( list(vcf1_rec.format) != list(vcf2_rec.format) ):
            errors.append('format')

        for sample in vcf1_samples:
            if ( vcf1_rec.samples[ sample] != vcf2_rec.samples[ sample] ):
                errors.append('sample {}'.format( sample ))

        if (errors ):
            errors = handle_error( error_string.format( type="Error(s) on: {}".format( ", ".join(errors))), exit_on_error  )

            
        # Track the positions in the vcf files so one does not come ahead of the other 
        if ( vcf1_rec.pos > vcf2_rec.pos ):
            vcf2_rec = next_vcf_rec(vcf2 )
        elif( vcf1_rec.pos < vcf2_rec.pos ):
            vcf1_rec = next_vcf_rec( vcf1 )
        else:
            vcf1_rec = next_vcf_rec( vcf1 )
            vcf2_rec = next_vcf_rec( vcf2 )

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='vcf_integrity_check: checks the variants and sample information in two vcf files are identical ')

    parser.add_argument('-e', '--exit-on-error', action="store_true", default=False,  help="exit on first error observed, defualt FALSE")
    parser.add_argument('vcf_file', metavar='vcf-file', nargs=2,   help="vcf files compare")

    args = parser.parse_args()


    vcf1 = args.vcf_file[ 0 ]
    vcf2 = args.vcf_file[ 1 ]

    compare_vcfs( vcf1, vcf2, args.exit_on_error)

