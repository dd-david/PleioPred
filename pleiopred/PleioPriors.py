#!/usr/bin/env python

### generate prior file from h5py file directly ###
### generate_h2_pT generates two prior files from the results of LDSC and a fixed annotation file ###
### generate_h2_from_user generates one prior file from the user provided prior file ###
import h5py
import os
from collections import Counter
from collections import defaultdict
import datetime
import math
from argparse import ArgumentParser
from os.path import isfile, isdir, join
from sys import exit
import numpy as np


def generate_prior_bi(h5py_file1, h5py_file2, LDSC_results_file1, LDSC_results_file2, output_anno_h2, output_ld_h2, ):
    ### load the fixed input file ###
    ## Note: gonna take huge memory!!! Probably need to optimize this part, for example, read in .gz files directly ##
    # h5py_file1 = pdict['h5py_file1']
    # LDSC_results_file1 = pdict['LDSC_results_file1']
    # h5py_file2 = pdict['h5py_file2']
    # LDSC_results_file2 = pdict['LDSC_results_file2']
    # output_anno_h2 = pdict['output_anno_h2']
    # output_ld_h2 = pdict['output_ld_h2']
    h5f1 = h5py.File('ref/AnnotMatrix/baseline.h5','r')
    baseline = h5f1['annot'][:]
    h5f1.close()

    if annotation_flag=='tier0':
        h5f1 = h5py.File('ref/AnnotMatrix/tier0.h5','r')
        tier = h5f1['annot'][:]
        h5f1.close()
    elif annotation_flag=='tier1':
        h5f1 = h5py.File('ref/AnnotMatrix/tier1.h5','r')
        tier = h5f1['annot'][:]
        h5f1.close()
    elif annotation_flag=='tier2':
        h5f1 = h5py.File('ref/AnnotMatrix/tier2.h5','r')
        tier = h5f1['annot'][:]
        h5f1.close()
    elif annotation_flag=='tier3':
        h5f1 = h5py.File('ref/AnnotMatrix/tier3.h5','r')
        tier = h5f1['annot'][:]
        h5f1.close()
    else:
        exit("Illegal tier name!")
    annot = np.concatenate((baseline,tier),axis=1)

#    h5f1 = h5py.File('ref/Misc/GC1_GS7_Baseline53.h5','r')
#    annot = h5f1['annot'][:]
#    h5f1.close()
    h5f2 = h5py.File('ref/AnnotMatrix/1000G_SNP_info.h5','r')
    snp_chr = h5f2['snp_chr'][:]
    h5f2.close()
    ### get the snp list from h5py ###
    chromosomes_list = ['chrom_%d'%(x) for x in range(1,23)]

    df1 = h5py.File(h5py_file1,'r')
    cord_data_g1 = df1['cord_data']
    df2 = h5py.File(h5py_file2,'r')
    cord_data_g2 = df2['cord_data']
    chr_list = list(set(cord_data_g1.keys()) & set(cord_data_g2.keys()))
    SNPids = []
    for chrom_str in chromosomes_list:
        if chrom_str in chr_list:
            print 'Working on %s'%chrom_str
            print 'Sorting disease 1'
            g1 = cord_data_g1[chrom_str]
            snp_stds1 = g1['snp_stds_ref'][...]
            snp_stds1 = snp_stds1.flatten()
            ok_snps_filter1 = snp_stds1>0
            ok_snps_filter1 = ok_snps_filter1.flatten()
            sids1 = g1['sids'][...]
            sids1 = sids1[ok_snps_filter1]

            print 'Sorting disease 2'
            g2 = cord_data_g2[chrom_str]
            snp_stds2 = g2['snp_stds_ref'][...]
            snp_stds2 = snp_stds2.flatten()
            ok_snps_filter2 = snp_stds2>0
            ok_snps_filter2 = ok_snps_filter2.flatten()
            sids2 = g2['sids'][...]
            sids2 = sids2[ok_snps_filter2]

            print 'Extracting SNPs shared by both disease 1 and 2'
            ind1 = np.in1d(sids1,sids2)
            ind2 = np.in1d(sids2,sids1)
            sids_shared1 = sids1[ind1]
            sids_shared2 = sids2[ind2]
            if len(sids_shared1)!=len(sids_shared2):
                print 'Something wrong with the SNP list in validation data, please check any possible duplication!'
            SNPids = np.append(SNPids,sids_shared1)

    num_snps = len(SNPids)
    ### overlap with SNP in annot files ###
    stt1 = np.in1d(snp_chr[:,2],SNPids)
    ant1 = annot[stt1]
    snp_chr1 = snp_chr[stt1]
    ### check order ###
    if sum(snp_chr1[:,2]==SNPids)==len(SNPids):
        print 'Good!'
    else:
        print 'Shit happens, sorting ant1 to have the same order as SNPids'
        O1 = np.argsort(snp_chr1[:,2])
        O2 = np.argsort(SNPids)
        O3 = np.argsort(O2)
        ant1 = ant1[O1][O3]

    ### load LDSC results ###
    LD_results1 = np.genfromtxt(LDSC_results_file1,dtype=None,names=True)
    LD_results2 = np.genfromtxt(LDSC_results_file2,dtype=None,names=True)
    
    tau0_1 = LD_results1['Coefficient']
    tau0_2 = LD_results2['Coefficient']
    ### get heritability  ###
    sig2_0_1 = np.dot(ant1,tau0_1)
    sig2_0_2 = np.dot(ant1,tau0_2)
    ### adjust for minus terms ###
    sig2_0_1[sig2_0_1<0] = np.repeat(min(sig2_0_1[sig2_0_1>0]),np.sum(sig2_0_1<0))
    np.sum(sig2_0_1)
    sig2_0_2[sig2_0_2<0] = np.repeat(min(sig2_0_2[sig2_0_2>0]),np.sum(sig2_0_2<0))
    np.sum(sig2_0_2)
    
    ### save prior file (h2) ###
    h2_out = []
    for i in range(len(sig2_0_1)):
        h2_out.append(str(snp_chr1[:,0][i])+' '+str(snp_chr1[:,2][i])+' '+str(sig2_0_1[i])+' '+str(sig2_0_2[i])+'\n')
    ff = open(output_anno_h2,"w")
    ff.writelines(h2_out)
    ff.close()

    h2_out = []
    for i in range(len(sig2_0_1)):
        h2_out.append(str(snp_chr1[:,0][i])+' '+str(snp_chr1[:,2][i])+' '+str(1.0)+' '+str(1.0)+'\n')
    ff = open(output_ld_h2,"w")
    ff.writelines(h2_out)
    ff.close()

    print 'h2 prior file with annotations saved at ' + output_anno_h2
    print 'h2 prior file without annotations saved at ' + output_ld_h2
    print 'Suggested LD radius: ' + str(math.ceil(num_snps/3000.0)) 
    return math.ceil(num_snps/3000.0)

def main(pdict):
  print(pdict)
  generate_prior_bi(pdict) 

if __name__ == '__main__':
  args = get_argparser().parse_args()
  main(process_args(args))
