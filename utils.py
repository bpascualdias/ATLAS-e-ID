import tensorflow        as tf
import numpy             as np
import multiprocessing   as mp
import matplotlib.pyplot as plt
import os, sys, h5py, pickle, time
from   sklearn  import metrics, utils, preprocessing
from   tabulate import tabulate
from   skimage  import transform
from   plots_DG import valid_accuracy, plot_history, plot_distributions_DG, plot_ROC_curves, var_histogram
from   plots_KM import plot_distributions_KM, differential_plots

#import pandas as pd
#from   pandas.plotting import scatter_matrix
#from   copy       import deepcopy
#from   itertools  import accumulate


def find_bin(array,binning):

    binarized_bin_indices=list()
    for i in range(len(binning)-1):
        binarized_bin_indices.append( ((binning[i]<array) & (array<=binning[i+1])).astype(float) )
        #tmp_array = (binning[i]<array) & (array<binning[i+1])
        #print(tmp_array)
        pass

    #print(np.shape(binarized_bin_indices[0]))

    return binarized_bin_indices
#def find_bin(element,binning):
#
#    binNum=-1 # underflow and overflow
#    for i in range(len(binning)-1):
#        if binning[i]<element and element<binning[i+1]: binNum=i
#        pass
#
#    return binNum

def get_bin_indices(p_var,boundaries):
    bin_indices=list()
    #print("hi=",boundaries[0],np.where( p_var<boundaries[0] )[0])
    bin_indices.append (np.where( p_var<=boundaries[0] )[0])
    for idx in range(len(boundaries)-1):
        #print("lo, hi=",boundaries[idx],":",boundaries[idx+1])
        bin_indices.append (np.where( (boundaries[idx]<p_var) & (p_var<=boundaries[idx+1]) )[0])
        #bin_indices.append (np.where( (boundaries[idx]<=p_var) & (p_var<boundaries[idx+1]) & (isnan(p_var)) )[0])
        pass
    #print("lo=",boundaries[len(boundaries)-1],np.where( boundaries[len(boundaries)-1]<p_var )[0])
    bin_indices.append (np.where( boundaries[len(boundaries)-1]<p_var )[0])
    #print(len(bin_indices),len(boundaries))

    tmp_idx=0
    total=0
    #total=len(bin_indices[0])
    #print("hi=",boundaries[0],bin_indices[0],len(bin_indices[0]),total)

    debug=False
    for bin_idx in bin_indices:
        total+=len(bin_idx)

        if debug:
            if tmp_idx==0:
                print("hi=",boundaries[tmp_idx],bin_idx,len(bin_idx),total)
            elif tmp_idx==len(bin_indices)-1:
                print("lo=",boundaries[tmp_idx-1],bin_idx,len(bin_idx),total)
            else:
                print("lo,hi=[",boundaries[tmp_idx-1],",",boundaries[tmp_idx],"]",bin_idx,len(bin_idx),total)
                pass
            pass

        tmp_idx+=1
        pass
    total+=len(bin_indices[-1])
    #print("lo=",boundaries[-1],bin_indices[-1],len(bin_indices[-1]),total)

    return bin_indices

def getMaxContents(binContents):

    maxContents = np.full(len(binContents[0]),-1.)
    for i_bin in range(len(binContents[0])):
        for i in range(len(binContents)):
            if binContents[i][i_bin] > maxContents[i_bin]: maxContents[i_bin] = binContents[i][i_bin]
            pass
        pass
    #print("maxContens=",maxContents)

    return maxContents

#def generate_weights(train_data,train_labels,nClass,weight_type='none',ref_var='pt',output_dir='outputs/'):
def sample_weights(train_data,train_labels,nClass,weight_type,output_dir='outputs/',ref_var='pt'):
    if weight_type=="none": return None

    print("-------------------------------")
    print("generate_weights: sample weight mode \"",weight_type,"\" designated. Generating weights.",)
    print("-------------------------------\n")

    binning=[0,10,20,30,40,60,80,100,130,180,250,500]
    labels=['sig','bkg']
    colors=['blue','red']
    binContents=[0,0]
    if nClass==6:
        #below 2b implemented
        labels=['sig','chf','conv','hf','eg','lf']
        colors=['blue','orange','green','red','purple','brown']
        binContents=[0,0,0,0,0,0]
        pass

    variable=list()                          #only for specific label
    variable_array = train_data['p_et_calo'] #entire set
    if   ref_var=='eta'  : variable_array = train_data['p_eta']
    #elif ref_var=='pteta': variable_array = train_data['p_eta']

    for i_class in range(nClass):
        variable.append( variable_array[ train_labels==i_class ] )
        (binContents[i_class],bins,patches)=plt.hist(variable[i_class],bins=binning,weights=np.full(len(variable[i_class]),1/len(variable[i_class])),label=labels[i_class],histtype='step',facecolor=colors[i_class])
        #(binContents[i_class],bins,patches)=plt.hist(variable[i_class],bins=binning,weights=np.full(len(variable[i_class]),1/len(train_labels)),label=labels[i_class],histtype='step',facecolor=colors[i_class])
        pass

        if nClass>2: plt.yscale("log")
        plt.savefig(output_dir+'/'+ref_var+"_bfrReweighting.png")
    plt.clf() #clear figure

    weights=list() #KM: currently implemented for the 2-class case only
    if weight_type=="flattening":
        for i in range(nClass): weights.append(np.average(binContents[i])/binContents[i] )
    elif weight_type=="match2max": #shaping to whichever that has max in the corresponding bin
        #for i in range(nClass): print("bincontens[",i,"]=",binContents[i])
        maxContents = getMaxContents(binContents)#print(maxContents)
        for i in range(nClass): weights.append( maxContents/binContents[i] )
    elif weight_type=="match2b": #shaping sig to match the bkg, using pt,or any other designated variable
        for i in range(nClass-1): weights.append(binContents[nClass-1]/binContents[i])
        weights.append(np.ones(len(binContents[5])))
    elif weight_type=="match2s": #shaping bkg to match the sig, using pt,or any other designated variable
        weights.append(np.ones(len(binContents[0])))
        for i in range (1, nClass): weights.append(binContents[0]/binContents[i])
        pass

    #KM: to replce inf with 0
    for i in range(nClass): weights[i]=np.where(weights[i]==np.inf,0,weights[i]) #np.where(array1==0, 1, array1)

    debug=0
    if debug:
        tmp_i=0
        for weight in weights:
            print("weights[",labels[tmp_i],"]=",weight)
            tmp_i+=1
        #print(weights[0])
        #print(weights[1])
        pass

    #KM: Generates weights for all events
    #    This is not very efficient, to be improved

    #final_weights*=weights[train_labels][1]

    class_weight=list()
    for i in range(nClass): class_weight.append( np.full(len(variable_array),0,dtype=float) )
    final_weights= np.full(len(variable_array),0,dtype=float)
    #sig_weight=np.full(len(variable_array),0,dtype=float)
    #bkg_weight=np.full(len(variable_array),0,dtype=float)

    #To produce vectors of 0 or 1 for given pt ranges
    bin_indices0or1=find_bin(variable_array,binning)
    tmp_i=0 # pt bin index
    for vec01 in bin_indices0or1:
        #KM: this line is the most important to calculate the weights for al events
        for i in range(nClass): class_weight[i] += (vec01 * (train_labels==i) )* weights[i][tmp_i]
        #sig_weight += (vec01 * (train_labels==0) )* weights[0][tmp_i]
        #bkg_weight += (vec01 * (train_labels==1) )* weights[1][tmp_i]
        tmp_i+=1
        pass

    if debug:
        print()
        #print(sig_weight,"\n", bkg_weight)
        tmp_i=0
        for i in range(nClass):
            print("class_weight[",tmp_i,"]=",class_weight[i])
            tmp_i+=1
            pass
        #print("final_weights=",final_weights) #print(final_weights,final_weights.all()==1) # w
        print("train_labels=",train_labels)
        pass

    for i in range(nClass): final_weights+=class_weight[i]

    if debug:
        print("variable_array=",variable_array)
        print(final_weights, len(final_weights), "any element is zero?",final_weights.any()==0)
        pass

    #KM: below only for plotting
    for i_class in range(nClass):
        plt.hist(variable[i_class],bins=binning,weights=final_weights[ train_labels==i_class ],label=labels[i_class],histtype='step',facecolor=colors[i_class])
        #weights = final_weights[ train_labels==i_class ]/len(train_labels)
        #plt.hist(variable[i_class],bins=binning, weights=weights, label=labels[i_class],histtype='step',facecolor=colors[i_class])
        pass
    if nClass>2: plt.yscale("log")
    plt.savefig(output_dir+'/'+ref_var+"_aftReweighting.png")
    plt.clf() #clear plot

    return final_weights




#################################################################################
##### classifier.py functions ###################################################
#################################################################################


def get_dataset(host_name='lps', node_dir='', eta_region=''):
    if 'lps'    in host_name                   : node_dir = '/opt/tmp/godin/e-ID_data/presamples'
    if 'beluga' in host_name and node_dir == '': node_dir = '/project/def-arguinj/shared/e-ID_data'
    barrel_dir, midgap_dir, endcap_dir = [node_dir+'/'+folder for folder in ['0.0-1.3', '1.3-1.6', '1.6-2.5']]
    barrel_files = sorted([barrel_dir+'/'+h5_file for h5_file in os.listdir(barrel_dir) if 'e-ID_' in h5_file])
    midgap_files = sorted([midgap_dir+'/'+h5_file for h5_file in os.listdir(midgap_dir) if 'e-ID_' in h5_file])
    endcap_files = sorted([endcap_dir+'/'+h5_file for h5_file in os.listdir(barrel_dir) if 'e-ID_' in h5_file])
    data_files = [h5_file for pair in zip(barrel_files, midgap_files, endcap_files) for h5_file in pair]
    if eta_region in ['0.0-1.3', '0.0-1.3_old', '1.3-1.6', '1.6-2.5', '0.0-2.5']:
        folder = node_dir+'/'+eta_region
        data_files = sorted([folder+'/'+h5_file for h5_file in os.listdir(folder) if 'e-ID_' in h5_file])
    #for key, val in h5py.File(data_files[0], 'r').items(): print(key, val.shape)
    return data_files


def sample_histograms(valid_sample, valid_labels, train_sample, train_labels, sample_weight, output_dir):
    arguments  = [(valid_sample, valid_labels,     None     , output_dir, 'valid')]
    arguments += [(train_sample, train_labels, sample_weight, output_dir, 'train')]
    processes  = [mp.Process(target=var_histogram, args=arg+(var,)) for arg in arguments for var in ['pt','eta']]
    for job in processes: job.start()
    for job in processes: job.join()
    return sample_weight


def split_samples(valid_sample, valid_labels, train_sample, train_labels):
    #generate a different validation sample from training sample with downsampling
    valid_sample, valid_labels, extra_sample, extra_labels = downsampling(valid_sample, valid_labels)
    train_sample  = {key:np.concatenate([train_sample[key], extra_sample[key]]) for key in train_sample}
    train_labels  = np.concatenate([train_labels, extra_labels])
    sample_weight = match_distributions(train_sample, train_labels, valid_sample, valid_labels)
    return valid_sample, valid_labels, train_sample, train_labels, sample_weight


def get_class_weight(labels, bkg_ratio):
    n_e = len(labels); n_classes = max(labels) + 1
    if bkg_ratio == 0 and n_classes == 2: return None
    if bkg_ratio == 0 and n_classes != 2: bkg_ratio = 1
    ratios       = {**{0:1}, **{n:bkg_ratio for n in np.arange(1, n_classes)}}
    class_weight = {n:n_e/np.sum(labels==n)*ratios[n]/sum(ratios.values()) for n in np.arange(n_classes)}
    return class_weight


def get_sample_weight(sample, labels, weight_type=None, bkg_ratio=None, hist='2d', density=True):
    if weight_type not in ['bkg_ratio', 'flattening', 'match2s', 'match2b', 'match2max']: return None
    n_classes = max(labels)+1
    pt  =     sample['pt']  ;  pt_bins = [0, 10, 20, 30, 40, 60, 80, 100, 130, 180, 250, 500        ]
    #pt_bins = np.float_(np.arange(0,502,1))
    eta = abs(sample['eta']); eta_bins = [0, 0.1, 0.6, 0.8, 1.15, 1.37, 1.52, 1.81, 2.01, 2.37, 2.47]
    pt_bins [-1] = max( pt_bins[-1], max( pt)) + 1e-3
    eta_bins[-1] = max(eta_bins[-1], max(eta)) + 1e-3
    pt_bins  =  pt_bins[np.where( pt_bins<=min( pt))[0][-1]:np.where( pt_bins>=max( pt))[0][0]+1]
    eta_bins = eta_bins[np.where(eta_bins<=min(eta))[0][-1]:np.where(eta_bins>=max(eta))[0][0]+1]
    if hist == 'pt' : eta_bins = [eta_bins[0], eta_bins[-1]]
    if hist == 'eta':  pt_bins = [ pt_bins[0],  pt_bins[-1]]
    pt_ind   = np.digitize( pt,  pt_bins, right=False) -1
    eta_ind  = np.digitize(eta, eta_bins, right=False) -1
    hist_sig = np.histogram2d(pt[labels==0], eta[labels==0], bins=[pt_bins,eta_bins], density=density)[0]
    if density: hist_sig *= np.sum(labels==0)
    hist_sig = np.maximum(hist_sig, np.min(hist_sig[hist_sig!=0]))
    total_sig_array = []; total_bkg_array = []; hist_bkg_array = []
    for n in np.arange(1, n_classes):
        hist_bkg = np.histogram2d(pt[labels==n], eta[labels==n], bins=[pt_bins,eta_bins], density=density)[0]
        if density: hist_bkg *= np.sum(labels==n)
        hist_bkg = np.maximum(hist_bkg, np.min(hist_bkg[hist_bkg!=0]))
        ratio    = np.sum(hist_bkg)/np.sum(hist_sig) if bkg_ratio == None else bkg_ratio
        if   weight_type == 'bkg_ratio':
            total_sig = hist_sig * max(1, np.sum(hist_bkg)/np.sum(hist_sig)/ratio)
            total_bkg = hist_bkg * max(1, np.sum(hist_sig)/np.sum(hist_bkg)*ratio)
        elif weight_type == 'flattening':
            total_sig = np.ones(hist_sig.shape) * max(np.max(hist_sig), np.max(hist_bkg)/ratio)
            total_bkg = np.ones(hist_bkg.shape) * max(np.max(hist_bkg), np.max(hist_sig)*ratio)
        elif weight_type == 'match2s':
            total_sig = hist_sig * max(1, np.max(hist_bkg/hist_sig)/ratio)
            total_bkg = hist_sig * max(1, np.max(hist_bkg/hist_sig)/ratio) * ratio
        elif weight_type == 'match2b':
            total_sig = hist_bkg * max(1, np.max(hist_sig/hist_bkg)*ratio) / ratio
            total_bkg = hist_bkg * max(1, np.max(hist_sig/hist_bkg)*ratio)
        elif weight_type == 'match2max':
            total_sig = np.maximum(hist_sig, hist_bkg/ratio)
            total_bkg = np.maximum(hist_bkg, hist_sig*ratio)
        total_sig_array.append(total_sig[np.newaxis,...])
        total_bkg_array.append(total_bkg[np.newaxis,...])
        hist_bkg_array.append ( hist_bkg[np.newaxis,...])
    hist_sig_array  = hist_sig[np.newaxis,...]
    hist_bkg_array  = np.concatenate( hist_bkg_array, axis=0)
    total_sig_array = np.concatenate(total_sig_array, axis=0)
    total_bkg_array = np.concatenate(total_bkg_array, axis=0)
    total_sig_ratio = total_sig_array / np.max(total_sig_array, axis=0)
    total_sig_array = np.max(total_sig_array, axis=0)
    total_bkg_array = total_bkg_array / total_sig_ratio
    weights_array = np.concatenate([total_sig_array/hist_sig_array, total_bkg_array/hist_bkg_array])
    sample_weight = np.zeros(len(labels))
    for n in np.arange(n_classes):
        sample_weight = np.where(labels==n, weights_array[n,...][pt_ind, eta_ind], sample_weight)
    return sample_weight*len(labels)/np.sum(sample_weight)


def gen_weights(n_train, weight_idx, sample_weight):
    weights = np.zeros(np.diff(n_train)[0]); np.put(weights, weight_idx, sample_weight)
    return weights


def upsampling(sample, labels, bins, indices, hist_sig, hist_bkg, total_sig, total_bkg):
    new_sig = np.int_(np.around(total_sig)) - hist_sig
    new_bkg = np.int_(np.around(total_bkg)) - hist_bkg
    ind_sig = [np.where((indices==n) & (labels==0))[0] for n in np.arange(len(bins)-1)]
    ind_bkg = [np.where((indices==n) & (labels!=0))[0] for n in np.arange(len(bins)-1)]
    np.random.seed(0)
    ind_sig = [np.append(ind_sig[n], np.random.choice(ind_sig[n], new_sig[n],
               replace = len(ind_sig[n])<new_sig[n])) for n in np.arange(len(bins)-1)]
    ind_bkg = [np.append(ind_bkg[n], np.random.choice(ind_bkg[n], new_bkg[n],
               replace = len(ind_bkg[n])<new_bkg[n])) for n in np.arange(len(bins)-1)]
    indices = np.concatenate(ind_sig + ind_bkg); np.random.shuffle(indices)
    return {key:np.take(sample[key], indices, axis=0) for key in sample}, np.take(labels, indices)


def downsampling(sample, labels, bkg_ratio=None):
    pt = sample['p_et_calo']; bins = [0, 10, 20, 30, 40, 60, 80, 100, 130, 180, 250, 500]
    indices  = np.digitize(pt, bins, right=True) -1
    hist_sig = np.histogram(pt[labels==0], bins)[0]
    hist_bkg = np.histogram(pt[labels!=0], bins)[0]
    if bkg_ratio == None: bkg_ratio = np.sum(hist_bkg)/np.sum(hist_sig)
    total_sig = np.int_(np.around(np.minimum(hist_sig, hist_bkg/bkg_ratio)))
    total_bkg = np.int_(np.around(np.minimum(hist_bkg, hist_sig*bkg_ratio)))
    ind_sig   = [np.where((indices==n) & (labels==0))[0][:total_sig[n]] for n in np.arange(len(bins)-1)]
    ind_bkg   = [np.where((indices==n) & (labels!=0))[0][:total_bkg[n]] for n in np.arange(len(bins)-1)]
    valid_ind = np.concatenate(ind_sig+ind_bkg); np.random.seed(0); np.random.shuffle(valid_ind)
    train_ind = list(set(np.arange(len(pt))) - set(valid_ind))
    valid_sample = {key:np.take(sample[key], valid_ind, axis=0) for key in sample}
    valid_labels = np.take(labels, valid_ind)
    extra_sample = {key:np.take(sample[key], train_ind, axis=0) for key in sample}
    extra_labels = np.take(labels, train_ind)
    return valid_sample, valid_labels, extra_sample, extra_labels


def match_distributions(sample, labels, target_sample, target_labels):
    pt = sample['p_et_calo']; target_pt = target_sample['p_et_calo']
    bins = [0, 10, 20, 30, 40, 60, 80, 100, 130, 180, 250, 500]
    indices         = np.digitize(pt, bins, right=False) -1
    hist_sig        = np.histogram(       pt[labels==0]       , bins)[0]
    hist_bkg        = np.histogram(       pt[labels!=0]       , bins)[0]
    hist_sig_target = np.histogram(target_pt[target_labels==0], bins)[0]
    hist_bkg_target = np.histogram(target_pt[target_labels!=0], bins)[0]
    total_sig   = hist_sig_target * np.max(np.append(hist_sig/hist_sig_target, hist_bkg/hist_bkg_target))
    total_bkg   = hist_bkg_target * np.max(np.append(hist_sig/hist_sig_target, hist_bkg/hist_bkg_target))
    weights_sig = total_sig/hist_sig * len(labels)/np.sum(total_sig+total_bkg)
    weights_bkg = total_bkg/hist_bkg * len(labels)/np.sum(total_sig+total_bkg)
    return np.where(labels==0, weights_sig[indices], weights_bkg[indices])


def validation(output_dir, results_in, plotting, n_valid, data_files, inputs, valid_cuts, sep_bkg, diff_plots):
    print('\nLOADING VALIDATION RESULTS FROM', output_dir+'/'+results_in)
    valid_data = pickle.load(open(output_dir+'/'+results_in, 'rb'))
    if len(valid_data) > 1: sample, labels, probs   = valid_data
    else:                                  (probs,) = valid_data
    n_e = min(len(probs), int(n_valid[1]-n_valid[0]))
    if False or len(valid_data) == 1: #add variables to the results
        print('CLASSIFIER: loading valid sample', n_e, end=' --> ', flush=True)
        sample, labels = merge_samples(data_files, n_valid, inputs, n_tracks=5, n_classes=probs.shape[1],
                                       valid_cuts=valid_cuts, scaler=None)
        n_e = len(labels)
    sample, labels, probs = {key:sample[key][:n_e] for key in sample}, labels[:n_e], probs[:n_e]
    if False: #save the added variables to the results file
        print('Saving validation data to:', output_dir+'/'+'valid_data.pkl', '\n')
        pickle.dump((sample, labels, probs), open(output_dir+'/'+'valid_data.pkl','wb')); sys.exit()
    print('GENERATING PERFORMANCE RESULTS FOR', n_e, 'ELECTRONS', end=' -->', flush=True)
    #valid_cuts = '(labels==0) & (probs[:,0]<=0.05)'
    #valid_cuts = '(sample["p_et_calo"]  < 20)'
    #valid_cuts = '(sample["p_et_calo"] >= 20) & (sample["p_et_calo"] <= 80)'
    #valid_cuts = '(sample["p_et_calo"]  > 80)'
    cuts = n_e*[True] if valid_cuts == '' else eval(valid_cuts)
    sample, labels, probs = {key:sample[key][cuts] for key in sample}, labels[cuts], probs[cuts]
    if False: #generate calorimeter images
        layers = ['em_barrel_Lr0'  , 'em_barrel_Lr1_fine'  , 'em_barrel_Lr2', 'em_barrel_Lr3',
                  'tile_barrel_Lr1', 'tile_barrel_Lr2', 'tile_barrel_Lr3']
        from plots_DG import cal_images
        cal_images(sample, labels, layers, output_dir, mode='mean', soft=False)
    def text_line(n_cut): return ' ('+str(n_cut)+' selected = '+format(100*n_cut/n_e,'0.2f')+'%)'
    print(text_line(len(labels)) if len(labels) < n_e else '')
    valid_results(sample, labels, probs, [], None, output_dir, plotting, sep_bkg, diff_plots); print()
    if False: #plot distribution histograms
        sample_histograms(sample, labels, sample, labels, None, output_dir)


def make_sample(data_file, idx, input_data, n_tracks, n_classes, verbose='OFF', prefix='p_'):
    upsize_images = False; preprocess_images = False
    scalars, images, others = input_data.values()
    if verbose == 'ON':
        print('loading sample [', format(str(idx[0]),'>7s')+', '+format(str(idx[1]),'>7s'), end='] ')
        print('from', data_file.split('/')[-2]+'/'+data_file.split('/')[-1], end=' --> ', flush=True)
        start_time = time.time()
    with h5py.File(data_file, 'r') as data:
        sample = {key:data[key][idx[0]:idx[1]] for key in scalars+others}
        sample.update({'eta':sample['p_eta'], 'pt':sample['p_et_calo']})
        for key in set(images)-set('tracks_image'):
            try: sample[key] = data[key][idx[0]:idx[1]]
            except KeyError:
                if 'fine' in key: sample[key] = np.zeros((idx[1]-idx[0],)+(56,11))
                else            : sample[key] = np.zeros((idx[1]-idx[0],)+( 7,11))
        if 'tracks_image' in images:
            n_tracks    = min(n_tracks, data[prefix+'tracks'].shape[1])
            tracks_data = data[prefix+'tracks'][idx[0]:idx[1]][:,:n_tracks,:]
            tracks_data = np.concatenate((abs(tracks_data[...,0:5]), tracks_data[...,5:13]), axis=2)
            sample['tracks_image'] = tracks_data
    if tf.__version__ < '2.1.0':
        for key in set(sample)-set(others): sample[key] = np.float32(sample[key])
    if images == ['tracks_image']: sample['tracks_image'] = np.float32(sample['tracks_image'])
    if upsize_images:
        for key in images: sample[key] = resize_images(np.float32(sample[key]),target_shape=(56,11))
    labels = make_labels(sample, n_classes)
    if preprocess_images: sample = process_images(sample, images)
    if verbose == 'ON': print('(', '\b'+format(time.time() - start_time, '2.1f'), '\b'+' s)')
    return sample, labels


def make_labels(sample, n_classes):
    MC_type = sample['p_TruthType']; IFF_type = sample['p_iffTruth']
    if   n_classes == 2:
        labels = np.where(IFF_type <= 1                               , -1, IFF_type)
        labels = np.where(IFF_type == 2                               ,  0, labels  )
        return   np.where(IFF_type >= 3                               ,  1, labels  )
    elif n_classes == 6:
        labels = np.where(np.logical_or (IFF_type <= 1, IFF_type == 4), -1, IFF_type)
        labels = np.where(np.logical_or (IFF_type == 6, IFF_type == 7), -1, labels  )
        labels = np.where(IFF_type == 2                               ,  0, labels  )
        labels = np.where(IFF_type == 3                               ,  1, labels  )
        labels = np.where(IFF_type == 5                               ,  2, labels  )
        labels = np.where(np.logical_or (IFF_type == 8, IFF_type == 9),  3, labels  )
        labels = np.where(np.logical_and(IFF_type ==10,  MC_type == 4),  4, labels  )
        labels = np.where(np.logical_and(IFF_type ==10,  MC_type ==16),  4, labels  )
        labels = np.where(np.logical_and(IFF_type ==10,  MC_type ==17),  5, labels  )
        return   np.where(  labels == 10                              , -1, labels  )
    else: print('\nERROR:', n_classes, 'classes not supported -> exiting program\n'); sys.exit()


def batch_idx(data_files, batch_size, interval, weights=None, shuffle='OFF'):
    def return_idx(n_e, cum_batches, batch_size, index):
        file_index  = np.searchsorted(cum_batches, index, side='right')
        batch_index = index - np.append(0, cum_batches)[file_index]
        idx         = batch_index*batch_size; idx = [idx, min(idx+batch_size, n_e[file_index])]
        return file_index, idx
    n_e = [len(h5py.File(data_file,'r')['eventNumber']) for data_file in data_files]
    cum_batches = np.cumsum(np.int_(np.ceil(np.array(n_e)/batch_size)))
    indexes     = [return_idx(n_e, cum_batches, batch_size, index) for index in np.arange(cum_batches[-1])]
    cum_n_e     = np.cumsum(np.diff(list(zip(*indexes))[1]))
    n_e_index   = np.searchsorted(cum_n_e, [interval[0],interval[1]-1], side='right')
    batch_list  = [indexes[n] for n in np.arange(cum_batches[-1]) if n >= n_e_index[0] and n <= n_e_index[1]]
    cum_n_e     = [cum_n_e[n] for n in np.arange(cum_batches[-1]) if n >= n_e_index[0] and n <= n_e_index[1]]
    batch_list[ 0][1][0] = batch_list[ 0][1][1] + interval[0] - cum_n_e[ 0]
    batch_list[-1][1][1] = batch_list[-1][1][1] + interval[1] - cum_n_e[-1]
    if shuffle == 'ON': batch_list = utils.shuffle(batch_list, random_state=0)
    batch_dict = {batch_list.index(n):{'file':n[0], 'indices':n[1], 'weights':None} for n in batch_list}
    if np.all(weights) != None:
        weights = np.split(weights, np.cumsum(n_e))
        for n in batch_list: batch_dict[batch_list.index(n)]['weights'] = weights[n[0]][n[1][0]:n[1][1]]
    #for key in batch_dict: print(key, batch_dict[key])
    return batch_dict


def shuffle_sample(output_dir, data_files, index):
    features = list(set().union(*[h5py.File(data_file,'r').keys() for data_file in data_files])); print()
    for key in features:
        print('Merging e-ID_'+'{:=02}'.format(index)+'.h5 files for', format(key,'29s'), end='-->', flush=True)
        start_time = time.time()
        sample_list = []
        for h5_file in data_files[3*index:3*(index+1)]:
            try: sample_list += [h5py.File(h5_file,'r')[key]]
            except KeyError:
                n_e = len(h5py.File(h5_file,'r')['eventNumber'])
                if 'fine' in key: sample_list += [np.zeros((n_e,)+(56,11), dtype=np.int8)]
                else            : sample_list += [np.zeros((n_e,)+( 7,11), dtype=np.int8)]
        sample = np.concatenate(sample_list)
        file_name = 'e-ID_'+'{:=02}'.format(index)+'.h5'
        with h5py.File(output_dir+'/'+file_name, 'w' if key==features[0] else 'a') as data:
            shape = (len(sample),) + sample.shape[1:]
            data.create_dataset(key, shape, dtype='i4' if sample.dtype=='int32' else'f2')
            data[key][:] = utils.shuffle(sample, random_state=0)
        print(' (', '\b'+format(time.time() - start_time, '2.1f'), '\b'+' s)')


def merge_samples(data_files, idx, input_data, n_tracks, n_classes, cuts, scaler=None):
    batch_dict = batch_idx(data_files, np.diff(idx)[0], idx)
    sample, labels = zip(*[make_sample(data_files[batch_dict[key]['file']], batch_dict[key]['indices'],
                           input_data, n_tracks, n_classes, verbose='ON') for key in batch_dict])
    #inputs = {key:np.concatenate([n[key] for n in sample]) for key in sample[0]}
    inputs = {}
    for key in list(sample[0].keys()):
        inputs[key] = np.concatenate([n[key] for n in sample])
        for n in sample: n.pop(key)
    labels  = np.concatenate(labels)
    indices = np.where( np.logical_and(labels!=-1, eval(cuts) if cuts!='' else True) )[0]
    inputs, labels, _ = sample_cuts(inputs, labels, cuts=cuts, verbose='ON')
    if scaler != None: inputs = apply_scaler(inputs, input_data['scalars'], scaler, verbose='ON')
    else: print()
    return inputs, labels, indices


class Batch_Generator(tf.keras.utils.Sequence):
    def __init__(self, data_files, indexes, input_data, n_tracks, n_classes,
                 batch_size, cuts, scaler, weights=None, shuffle='OFF'):
        self.data_files = data_files; self.indexes    = indexes
        self.input_data = input_data; self.n_tracks   = n_tracks
        self.n_classes  = n_classes ; self.batch_size = batch_size
        self.cuts       = cuts      ; self.scaler     = scaler
        self.weights    = weights   ; self.shuffle    = shuffle
        self.batch_dict = batch_idx(self.data_files, self.batch_size, self.indexes, self.weights, self.shuffle)
    def __len__(self):
        return len(self.batch_dict) #number of batches per epoch
    def __getitem__(self, gen_index):
        file_index = self.batch_dict[gen_index]['file']
        file_idx   = self.batch_dict[gen_index]['indices']
        weights    = self.batch_dict[gen_index]['weights']
        data_file  = self.data_files[file_index]
        sample, labels = make_sample(data_file, file_idx, self.input_data, self.n_tracks, self.n_classes)
        sample, labels, weights = sample_cuts(sample, labels, weights, self.cuts)
        if len(labels) != 0:
            if self.scaler != None: sample = apply_scaler(sample, self.input_data['scalars'], self.scaler)
        return sample, labels, weights


def sample_cuts(sample, labels, weights=None, cuts='', verbose='OFF'):
    if np.sum(labels==-1) != 0:
        length = len(labels)
        sample = {key:sample[key][labels!=-1] for key in sample}
        if np.all(weights) != None: weights = weights[labels!=-1]
        labels = labels[labels!=-1]
        if verbose == 'ON':
            print('applying IFF labels cuts -->', format(len(labels),'8d'), 'e conserved', end='')
            print(' (' + format(100*len(labels)/length, '.2f') + ' %)')
    if cuts != '':
        length = len(labels)
        labels = labels[eval(cuts)]
        if np.all(weights) != None: weights = weights[eval(cuts)];
        sample = {key:sample[key][eval(cuts)] for key in sample}
        if verbose == 'ON':
            print('CLASSIFIER: applying features cuts -->', format(len(labels),'8d') ,'e conserved', end='')
            print(' ('+format(100*len(labels)/length,'.2f')+' %)\nCLASSIFIER: applied cuts:', cuts)
    return sample, labels, weights


def process_images(sample, image_list, n_tasks=16):
    def rotation(images, indices, return_dict):
        images = images[indices[0]:indices[1]].T
        #images  = abs(images)                               # negatives to positives
        #images -= np.minimum(0, np.min(images, axis=(0,1))) # shift to positive domain
        images = np.maximum(0, images)                       # clips negative values
        mean_1 = np.mean(images[:images.shape[0]//2   ], axis=(0,1))
        mean_2 = np.mean(images[ images.shape[0]//2:-1], axis=(0,1))
        return_dict[indices] = np.where(mean_1 > mean_2, images[::-1,::-1,:], images).T
    n_samples = len(sample['eventNumber'])
    idx_list  = [task*(n_samples//n_tasks) for task in np.arange(n_tasks)] + [n_samples]
    idx_list  = list( zip(idx_list[:-1], idx_list[1:]) ); start_time = time.time()
    print('CLASSIFIER: preprocessing images for best axis', end=' --> ', flush=True)
    for cal_image in [key for key in image_list if 'tracks' not in key]:
        images    = sample[cal_image]; manager = mp.Manager(); return_dict = manager.dict()
        processes = [mp.Process(target=rotation, args=(images, idx, return_dict)) for idx in idx_list]
        for job in processes: job.start()
        for job in processes: job.join()
        sample[cal_image] = np.concatenate([return_dict[idx] for idx in idx_list])
    print(' ('+format(time.time()-start_time,'.1f'), '\b'+' s)\n')
    return sample


def fit_scaler(sample, scalars, scaler_out):
    print('CLASSIFIER: fitting quantile transform to training scalars', end=' --> ', flush=True)
    start_time    = time.time()
    scalars_array = np.hstack([np.expand_dims(sample[key], axis=1) for key in scalars])
    scaler = preprocessing.QuantileTransformer(output_distribution='normal', n_quantiles=10000, random_state=0)
    scaler.fit(scalars_array) #scaler.fit_transform(scalars_array)
    print('(', '\b'+format(time.time() - start_time, '2.1f'), '\b'+' s)')
    print('CLASSIFIER: saving scalars scaler file in', scaler_out, '\n')
    pickle.dump(scaler, open(scaler_out, 'wb'))
    return scaler


def apply_scaler(sample, scalars, scaler, verbose='OFF'):
    if verbose == 'ON':
        start_time = time.time()
        print('CLASSIFIER: applying quantile transform to scalar features', end=' --> ', flush=True)
    scalars_array = scaler.transform(np.hstack([np.expand_dims(sample[key], axis=1) for key in scalars]))
    for n in np.arange(len(scalars)): sample[scalars[n]] = scalars_array[:,n]
    if verbose == 'ON': print('(', '\b'+format(time.time() - start_time, '2.1f'), '\b'+' s)\n')
    return sample


def fit_t_scaler(sample, scaler_out):
    print('CLASSIFIER: fitting quantile transform to training tracks', end='  --> ', flush=True)
    start_time    = time.time()
    tracks = sample['tracks_image']; tracks_shape = tracks.shape
    scaler = preprocessing.QuantileTransformer(output_distribution='normal', n_quantiles=10000, random_state=0)
    scaler.fit(np.reshape(tracks, (tracks_shape[0],-1))) #scaler.fit_transform(tracks_array)
    print('(', '\b'+format(time.time() - start_time, '2.1f'), '\b'+' s)')
    print('CLASSIFIER: saving tracks scaler file in', scaler_out, '\n')
    pickle.dump(scaler, open(scaler_out, 'wb'))
    return scaler


def apply_t_scaler(sample, scaler, verbose='OFF'):
    if verbose == 'ON':
        start_time = time.time()
        print('CLASSIFIER: applying robust transform to tracks features', end=' --> ', flush=True)
    tracks = sample['tracks_image']; tracks_shape = tracks.shape
    tracks = np.reshape(tracks, (tracks_shape[0],-1))
    tracks = scaler.transform(tracks)
    sample['tracks_image'] = np.reshape(tracks, tracks_shape)
    if verbose == 'ON': print('(', '\b'+format(time.time() - start_time, '2.1f'), '\b'+' s)\n')
    return sample


def sample_composition(sample):
    MC_type, IFF_type  = sample['p_TruthType']    , sample['p_iffTruth']
    MC_list, IFF_list  = np.arange(max(MC_type)+1), np.arange(max(IFF_type)+1)
    ratios = np.array([ [np.sum(MC_type[IFF_type==IFF]==MC) for MC in MC_list] for IFF in IFF_list ])
    IFF_sum, MC_sum = 100*np.sum(ratios, axis=0)/len(MC_type), 100*np.sum(ratios, axis=1)/len(MC_type)
    ratios = np.round(1e4*ratios/len(MC_type))/100
    MC_empty, IFF_empty = np.where(np.sum(ratios, axis=0)==0)[0], np.where(np.sum(ratios, axis=1)==0)[0]
    MC_list,  IFF_list  = list(set(MC_list)-set(MC_empty))      , list(set(IFF_list)-set(IFF_empty))
    print('IFF AND MC TRUTH CLASSIFIERS TRAINING SAMPLE COMPOSITION (', '\b'+str(len(MC_type)), 'e)')
    dash = (26+7*len(MC_list))*'-'
    print(dash, format('\n| IFF \ MC |','10s'), end='')
    for col in MC_list:
        print(format(col, '7.0f'), end='   |  Total  | \n' + dash + '\n' if col==MC_list[-1] else '')
    for row in IFF_list:
        print('|', format(row, '5.0f'), '   |', end='' )
        for col in MC_list:
            print(format(ratios[row,col], '7.0f' if ratios[row,col]==0 else '7.2f'), end='', flush=True)
        print('   |' + format(MC_sum[row], '7.2f')+ '  |')
        if row != IFF_list[-1]: print('|' + 10*' ' + '|' + (3+7*len(MC_list))*' ' + '|' + 9*' ' + '|')
    print(dash + '\n|   Total  |', end='')
    for col in MC_list: print(format(IFF_sum[col], '7.2f'), end='')
    print('   |  100 %  |\n' + dash + '\n')


def class_ratios(labels):
    def get_ratios(labels, n, return_dict): return_dict[n] = 100*np.sum(labels==n)/len(labels)
    manager   =  mp.Manager(); return_dict = manager.dict(); n_classes = max(labels) + 1
    processes = [mp.Process(target=get_ratios, args=(labels, n, return_dict)) for n in np.arange(n_classes)]
    for job in processes: job.start()
    for job in processes: job.join()
    return [return_dict[n] for n in np.arange(n_classes)]


def compo_matrix(valid_labels, train_labels=[], valid_probs=[]):
    valid_pred   = np.argmax(valid_probs, axis=1) if valid_probs != [] else valid_labels
    matrix       = metrics.confusion_matrix(valid_labels, valid_pred)
    matrix       = 100*matrix.T/matrix.sum(axis=1); n_classes = len(matrix)
    classes      = ['CLASS '+str(n) for n in np.arange(n_classes)]
    valid_ratios = class_ratios(valid_labels)
    train_ratios = class_ratios(train_labels) if train_labels != [] else n_classes*['n/a']
    if valid_probs == []:
        print('+---------------------------------------+\n| CLASS DISTRIBUTIONS'+19*' '+'|')
        headers = ['CLASS #', 'TRAIN (%)', 'VALID (%)']
        table   = zip(classes, train_ratios, valid_ratios)
        print(tabulate(table, headers=headers, tablefmt='psql', floatfmt=".2f"))
    else:
        if n_classes > 2:
            headers = ['CLASS #', 'TRAIN', 'VALID'] + classes
            table   = [classes] + [train_ratios] + [valid_ratios] + matrix.T.tolist()
            table   = list(map(list, zip(*table)))
            print_dict[2]  = '+'+31*'-'+'+'+35*'-'+12*(n_classes-3)*'-'+'+\n| CLASS DISTRIBUTIONS (%)'
            print_dict[2] += '       | VALID SAMPLE PREDICTIONS (%)      '+12*(n_classes-3)*' '+ '|\n'
        else:
            headers = ['CLASS #', 'TRAIN (%)', 'VALID (%)', 'ACC. (%)']
            table   = zip(classes, train_ratios, valid_ratios, matrix.diagonal())
            print_dict[2]  = '+----------------------------------------------------+\n'
            print_dict[2] += '| CLASS DISTRIBUTIONS AND VALID SAMPLE ACCURACIES    |\n'
        valid_accuracy = np.array(valid_ratios) @ np.array(matrix.diagonal())/100
        print_dict[2] += tabulate(table, headers=headers, tablefmt='psql', floatfmt=".2f")+'\n'
        print_dict[2] += 'VALIDATION SAMPLE ACCURACY: '+format(valid_accuracy,'.2f')+' %\n'


def cross_valid(valid_sample, valid_labels, scalars, output_dir, n_folds, data_files, n_valid,
                input_data, n_tracks, valid_cuts, model, generator='OFF', verbose=1):
    print('########################################################################'  )
    print('##### STARTING '+str(n_folds)+'-FOLD CROSS-VALIDATION ################################'  )
    print('########################################################################\n')
    n_classes    = max(valid_labels)+1
    valid_probs  = np.full(valid_labels.shape + (n_classes,), -1.)
    event_number = valid_sample['eventNumber']
    for fold_number in np.arange(1, n_folds+1):
        print('FOLD '+str(fold_number)+'/'+str(n_folds), 'EVALUATION')
        weight_file = output_dir+'/model_' +str(fold_number)+'.h5'
        scaler_file = output_dir+'/scaler_'+str(fold_number)+'.pkl'
        print('CLASSIFIER: loading pre-trained weights from', weight_file)
        model.load_weights(weight_file); start_time = time.time()
        indices =               np.where(event_number%n_folds==fold_number-1)[0]
        labels  =           valid_labels[event_number%n_folds==fold_number-1]
        sample  = {key:valid_sample[key][event_number%n_folds==fold_number-1] for key in valid_sample}
        if scalars != [] and os.path.isfile(scaler_file):
            print('CLASSIFIER: loading scalars scaler from', scaler_file)
            scaler = pickle.load(open(scaler_file, 'rb'))
            sample = apply_scaler(sample, scalars, scaler, verbose='ON')
        print('\033[FCLASSIFIER:', weight_file.split('/')[-1], 'class predictions for', len(labels), 'e')
        if generator == 'ON':
            valid_cuts = '(sample["eventNumber"]%'+str(n_folds)+'=='+str(fold_number-1)+')'
            valid_gen  = Batch_Generator(data_files, n_valid, input_data, n_tracks, n_classes,
                                         batch_size=20000, cuts=valid_cuts, scaler=scaler)
            probs = model.predict(valid_gen, workers=4, verbose=verbose)
        else: probs = model.predict(sample, batch_size=20000, verbose=verbose)
        print('FOLD '+str(fold_number)+'/'+str(n_folds)+' ACCURACY: ', end='')
        print(format(100*valid_accuracy(labels, probs), '.2f'), end='')
        print(' % (', '\b'+format(time.time() - start_time, '2.1f'), '\b'+' s)\n')
        #for n in np.arange(len(indices)): valid_probs[indices[n],:] = probs[n,:]
        for n in np.arange(n_classes): np.put(valid_probs[:,n], indices, probs[:,n])
    print('MERGING ALL FOLDS AND PREDICTING CLASSES ...')
    return valid_probs


def binarization(sample, labels, probs, class_1=['bkg'], class_0=[0], normalization=True, bkg_weights=True):
    from functools import reduce
    if class_1==['bkg'] or class_1==class_0: class_1 = set(np.arange(max(labels)+1)) - set(class_0)
    print_dict[1] += 'BINARIZATION: CLASS 0 = '+str(set(class_0))+' vs CLASS 1 = '+str(set(class_1))+'\n'
    ratios  = class_ratios(labels) if bkg_weights else (max(labels)+1)*[1]
    labels  = np.array([0 if label in class_0 else 1 if label in class_1 else -1 for label in labels])
    #print( probs[:,0].shape, probs[:,1:].shape, np.mean(probs,axis=1)[:,np.newaxis].shape ); sys.exit()
    #probs[:,1:] = np.where(probs[:,0][:,np.newaxis]>0.16, probs[:,1:]/np.mean(probs[:,1:],axis=1)[:,np.newaxis], probs[:,1:])
    probs_0 = reduce(np.add, [ratios[n]*probs[:,n] for n in class_0])[labels!=-1]
    probs_1 = reduce(np.add, [ratios[n]*probs[:,n] for n in class_1])[labels!=-1]
    sample  = {key:sample[key][labels!=-1] for key in sample}; labels = labels[labels!=-1]
    if normalization:
        probs_0 = np.where(probs_0!=probs_1, probs_0, 0.5)
        probs_1 = np.where(probs_0!=probs_1, probs_1, 0.5)
        probs   = (np.vstack([probs_0, probs_1])/(probs_0+probs_1)).T
    else: probs =  np.vstack([probs_0, probs_1]).T
    return sample, labels, probs


def bkg_separation(sample, labels, probs, bkg):
    if bkg == 'bkg': return sample, labels, probs
    print_dict[1] += 'BACKGROUND SEPARATION: CLASS 0 = {0} VS CLASS 1 = {'+str(bkg)+'}\n'
    multi_labels = make_labels(sample, n_classes=6)
    cuts = np.logical_or(multi_labels==0, multi_labels==bkg)
    return {key:sample[key][cuts] for key in sample}, labels[cuts], probs[cuts]


def print_performance(labels, probs, sig_eff=[90, 80, 70]):
    fpr, tpr, _ = metrics.roc_curve(labels, probs[:,0], pos_label=0)
    for val in sig_eff:
        print_dict[3] += 'BACKGROUND REJECTION AT '+str(val)+'%: '
        print_dict[3] += format(1/fpr[np.argwhere(tpr>=val/100)[0]][0],'>6.0f')+'\n'


def print_results(sample, labels, probs, plotting, output_dir, bkg, return_dict, separation=True):
    if max(labels) > 1: sample, labels, probs = binarization  (sample, labels, probs, [bkg])
    else              : sample, labels, probs = bkg_separation(sample, labels, probs,  bkg )
    if False: pickle.dump((sample,labels,probs), open(output_dir+'/'+'results_0_vs_'+str(bkg)+'.pkl','wb'))
    if plotting == 'ON':
        folder = output_dir+'/'+'class_0_vs_'+str(bkg)
        if not os.path.isdir(folder): os.mkdir(folder)
        arguments  = (sample, labels, probs, folder, separation and bkg=='bkg', bkg)
        processes  = [mp.Process(target=plot_distributions_DG, args=arguments)]
        arguments  = [(sample, labels, probs, ROC_type, folder) for ROC_type in [1,2,3]]
        processes += [mp.Process(target=plot_ROC_curves, args=arg) for arg in arguments]
        for job in processes: job.start()
        for job in processes: job.join()
    else:
        compo_matrix(labels, [], probs); print_performance(labels, probs)
    return_dict[bkg] = print_dict


def valid_results(sample, labels, probs, train_labels, training, output_dir, plotting, sep_bkg, diff_plots):
    global print_dict; print_dict = {n:'' for n in [1,2,3]}
    print(); compo_matrix(labels, train_labels, probs); print(print_dict[2])
    manager   = mp.Manager(); return_dict = manager.dict()
    bkg_list  = ['bkg'] + [1, 2, 3, 4, 5] if sep_bkg =='ON' else ['bkg']
    arguments = [(sample, labels, probs, plotting, output_dir, bkg, return_dict) for bkg in bkg_list]
    processes = [mp.Process(target=print_results, args=arg) for arg in arguments]
    if training != None: processes += [mp.Process(target=plot_history, args=(training, output_dir,))]
    for job in processes: job.start()
    for job in processes: job.join()
    if plotting=='OFF':
        for bkg in bkg_list: print("".join(list(return_dict[bkg].values())))
        return np.nan_to_num([int(return_dict[n][3].split()[-1]) for n in bkg_list]) # bkg_rej extraction
    # DIFFERENTIAL PLOTS
    if plotting == 'ON' and diff_plots:
        eta_boundaries  = [-1.6, -0.8, 0, 0.8, 1.6]
        pt_boundaries   = [10, 20, 30, 40, 60, 100, 200, 500]
        eta, pt         = sample['eta'], sample['pt']
        eta_bin_indices = get_bin_indices(eta, eta_boundaries)
        pt_bin_indices  = get_bin_indices(pt , pt_boundaries)
        plot_distributions_KM(labels, eta, 'eta', output_dir=output_dir)
        plot_distributions_KM(labels, pt , 'pt' , output_dir=output_dir)
        tmp_llh      = sample['p_LHValue']
        tmp_llh_pair = np.zeros(len(tmp_llh))
        prob_LLH     = np.stack((tmp_llh,tmp_llh_pair),axis=-1)
        print('\nEvaluating differential performance in eta')
        differential_plots(sample, labels, probs, eta_boundaries,
                           eta_bin_indices, varname='eta', output_dir=output_dir)
        print('\nEvaluating differential performance in pt')
        differential_plots(sample, labels, probs, pt_boundaries,
                           pt_bin_indices,  varname='pt',  output_dir=output_dir)
        differential_plots(sample, labels, prob_LLH   , pt_boundaries,
                           pt_bin_indices,  varname='pt',  output_dir=output_dir, evalLLH=True)


def verify_sample(sample):
    def scan(sample, batch_size, index, return_dict):
        idx1, idx2 = index*batch_size, (index+1)*batch_size
        return_dict[index] = sum([np.sum(np.isfinite(sample[key][idx1:idx2])==False) for key in sample])
    n_e = len(list(sample.values())[0]); start_time = time.time()
    print('\nSCANNING', n_e, 'ELECTRONS FOR ERRORS -->', end=' ', flush=True)
    for n in np.arange(min(12, mp.cpu_count()), 0, -1):
        if n_e % n == 0: n_tasks = n; batch_size = n_e//n_tasks; break
    manager   =  mp.Manager(); return_dict = manager.dict()
    processes = [mp.Process(target=scan, args=(sample, batch_size, index, return_dict))
                for index in np.arange(n_tasks)]
    for job in processes: job.start()
    for job in processes: job.join()
    print(sum(return_dict.values()), 'ERRORS FOUND', end=' ', flush=True)
    print('(', '\b'+format(time.time() - start_time, '2.1f'), '\b'+' s)\n')
    if sum(return_dict.values()) != 0:
        for key in sample: print(key, np.where(np.isfinite(sample[key])==False))


def NN_weights(image_shape, CNN_dict, FCN_neurons, n_classes):
    kernels = np.array(CNN_dict[image_shape]['kernels']); n_maps = CNN_dict[image_shape]['maps']
    K = [image_shape[2] if len(image_shape)==3 else 1] + n_maps + FCN_neurons + [n_classes]
    A = [np.prod([image_shape[n] + sum(1-kernels)[n] for n in [0,1]])]
    A = [np.prod(kernels[n]) for n in np.arange(len(n_maps))] + A + len(FCN_neurons)*[1]
    return sum([(K[l]*A[l]+1)*K[l+1] for l in np.arange(len(K)-1)])


def order_kernels(image_shape, n_maps, FCN_neurons, n_classes):
    x_dims  = [(x1,x2) for x1 in np.arange(1,image_shape[0]+1) for x2 in np.arange(1,image_shape[0]-x1+2)]
    y_dims  = [(y1,y2) for y1 in np.arange(1,image_shape[1]+1) for y2 in np.arange(1,image_shape[1]-y1+2)]
    par_tuple = []
    for kernels in [[(x[0],y[0]),(x[1],y[1])] for x in x_dims for y in y_dims]:
        CNN_dict   = {image_shape:{'maps':n_maps, 'kernels':kernels}}
        par_tuple += [(NN_weights(image_shape, CNN_dict, FCN_neurons, n_classes), kernels)]
    return sorted(par_tuple)[::-1]


def print_channels(sample, col=0, reverse=False):
    def getkey(item): return item[col]
    channel_dict= {301535:'Z -> ee+y 10-35'   , 301536:'Z -> mumu+y 10-35', 301899:'Z -> ee+y 35-70'   ,
                   301900:'Z -> ee+y 70-140'  , 301901:'Z -> ee+y 140'    , 301902:'Z -> mumu+y 35-70' ,
                   301903:'Z -> mumu+y 70-140', 301904:'Z -> mumu+y 140'  , 361020:'dijet JZ0W'        ,
                   361021:'dijet JZ1W'        , 361022:'dijet JZ2W'       , 361023:'dijet JZ3W'        ,
                   361024:'dijet JZ4W'        , 361025:'dijet JZ5W'       , 361026:'dijet JZ6W'        ,
                   361027:'dijet JZ7W'        , 361028:'dijet JZ8W'       , 361029:'dijet JZ9W'        ,
                   361100:'W+ -> ev'          , 361101:'W+ -> muv'        , 361102:'W+ -> tauv'        ,
                   361103:'W- -> ev'          , 361104:'W- -> muv'        , 361105:'W- -> tauv'        ,
                   361106:'Z -> ee'           , 361108:'Z -> tautau'      , 410470:'ttbar nonhad'      ,
                   410471:'ttbar allhad'      , 410644:'s top s-chan.'    , 410645:'s top s-chan.'     ,
                   410646:'s top Wt-chan.'    , 410647:'s top Wt-chan.'   , 410658:'s top t-chan.'     ,
                   410659:'s top t-chan.'     , 423099:'y+jets 8-17'      , 423100:'y+jets 17-35'      ,
                   423101:'y+jets 35-50'      , 423102:'y+jets 50-70'     , 423103:'y+jets 70-140'     ,
                   423104:'y+jets 140-280'    , 423105:'y+jets 280-500'   , 423106:'y+jets 500-800'    ,
                   423107:'y+jets 800-1000'   , 423108:'y+jets 1000-1500' , 423111:'y+jets 2500-3000'  ,
                   423112:'y+jets 3000'       , 423200:'direct:Jpsie3e3'  , 423201:'direct:Jpsie3e8'   ,
                   423202:'direct:Jpsie3e13'  , 423211:'np:bb -> Jpsie3e8', 423212:'np:bb -> Jpsie3e13',
                   423300:'JF17'              , 423301:'JF23'             , 423302:'JF35'              }
    channels = sample['mcChannelNumber']; headers = ['Channel', 'Process', 'Number']
    channels = sorted([[n, channel_dict[n], int(np.sum(channels==n))] for n in set(channels)], key=getkey)
    print(tabulate(channels[::-1] if reverse else channels, headers=headers, tablefmt='psql'))


def sample_analysis(sample, labels, scalars, scaler_file, output_dir):
    #for key in sample: print(key, sample[key].shape)
    #sys.exit()
    #verify_sample(sample); sys.exit()
    # CALORIMETER IMAGES
    from plots_DG import cal_images
    layers  = [ 'em_barrel_Lr0',   'em_barrel_Lr1',   'em_barrel_Lr2',   'em_barrel_Lr3',
                                   'tile_gap_Lr1'                                       ,
                'em_endcap_Lr0',   'em_endcap_Lr1',   'em_endcap_Lr2',   'em_endcap_Lr3',
               'lar_endcap_Lr0',  'lar_endcap_Lr1',  'lar_endcap_Lr2',  'lar_endcap_Lr3',
                                 'tile_barrel_Lr1', 'tile_barrel_Lr2', 'tile_barrel_Lr3']
    cal_images(sample, labels, layers, output_dir, mode='mean', soft=True)
    # TRACKS DISTRIBUTIONS
    #from plots_DG import plot_tracks
    #arguments = [(sample['tracks_image'], labels, key,) for key in ['efrac','deta','dphi','d0','z0']]
    #processes = [mp.Process(target=plot_tracks, args=arg) for arg in arguments]
    #for job in processes: job.start()
    #for job in processes: job.join()
    # SCALARS DISTRIBUTIONS
    #from plots_DG import plot_scalars
    #sample_trans = sample.copy()
    #sample_trans = apply_scaler(sample_trans, scalars, scaler_file)#[0]
    #for key in ['p_qd0Sig', 'p_sct_weight_charge']: plot_scalars(sample, sample_trans, key)


def feature_removal(scalars, images, groups, index):
    if   index <= 0: return scalars, images, 'none'
    elif index  > len(scalars+images+groups): sys.exit()
    elif index <= len(scalars+images):
        #removed_feature = (scalars+images)[index-1]
        removed_feature = dict(zip(np.arange(1, len(scalars+images)+1), scalars+images))[index]
        scalars_list    = list(set(scalars) - set([removed_feature]))
        images_list     = list(set(images ) - set([removed_feature]))
    elif index  > len(scalars+images):
        removed_feature = groups[index-1-len(scalars+images)]
        scalars_list    = list(set(scalars) - set(removed_feature))
        images_list     = list(set(images ) - set(removed_feature))
        removed_feature = 'group_'+str(index-len(scalars+images))
    scalars = [scalar for scalar in scalars if scalar in scalars_list]
    images  = [ image for  image in  images if  image in  images_list]
    return scalars, images, removed_feature


def feature_ranking(output_dir, results_out, scalars, images, eta_region, n_classes):
    ## Obtain dictionary with background rejection data
    data_dict = {}
    with open(results_out,'rb') as file_data:
        try:
            while True: data_dict.update(pickle.load(file_data))
        except EOFError: pass
    try: pickle.dump(data_dict, open(results_out,'wb'))
    except IOError: print('FILE ACCESS CONFLICT IN FEATURE RANKING --> SKIPPING FILE ACCESS\n')

    print('BACKGROUND REJECTION DICTIONARY:')
    for key in data_dict: print(format(key,'30s'), data_dict[key])

    class_name = {0 : 'class 0 vs All', 1 : 'class 0 vs 1', 2 : 'class 0 vs 2', 3 : 'class 0 vs 3', 4 : 'class 0 vs 4', 5 : 'class 0 vs 5',}
    colors = {'scalars' : 'tab:blue', 'images' : 'tab:orange', 'others' : 'tab:green'}

    ## Prepare dictionary mapping features names to LaTeX format
    LaTeX = {
            'p_Eratio'                     : r'$E_{ratio}$',
            'p_Reta'                       : r'$R_{\eta}$',
            'p_Rhad'                       : r'$R_{had}$',
            'p_Rphi'                       : r'$R_{\phi}$',
            'p_TRTPID'                     : r'TRTPID',
            'p_numberOfSCTHits'            : r'Nb of SCT hits',
            'p_ndof'                       : 'ndof',
            'p_dPOverP'                    : r'$\Delta p/p$',
            'p_deltaEta1'                  : r'$\Delta \eta_1$',
            'p_f1'                         : r'$f_1$',
            'p_f3'                         : r'$f_3$',
            'p_deltaPhiRescaled2'          : r'$\Delta \phi _{res}$',
            'p_weta2'                      : r'$w_{\eta 2}$',
            'p_d0'                         : r'$d_0$',
            'p_d0Sig'                      : r'$d_0/{\sigma(d_0)}$',
            'p_qd0Sig'                     : r'qd0Sig',
            'p_nTracks'                    : r'$n_{Tracks}$',
            'p_sct_weight_charge'          : r'sct wt charge',
            'p_eta'                        : r'$\eta$',
            'p_et_calo'                    : r'$p_t$',
            'p_EptRatio'                   : r'$E/p_T$',
            'p_EoverP'                     : r'$E/p$',
            'p_wtots1'                     : r'$w_{stot}$',
            'p_numberOfInnermostPixelHits' : r'$n_{Blayer}$'
        }

    ## Add features that don't have a Latex format as themselves
    for feature in scalars+images:
        if not feature in LaTeX:
            LaTeX[feature] = feature

    if 'none' in data_dict:
        # Obtain the data and calculate the ratio
        bkg_ratio = {}
        for feature in data_dict:
            if feature != 'none':
                bkg_ratio[feature] = data_dict['none']/data_dict[feature]
        # Plot the data
        for class_index in class_name:
            fig, ax = plt.subplots(figsize=(30/2.54, 20/2.54))
            ax.invert_yaxis()

            # Sort features in descending order of the ratio
            sorted_features = [f[0] for f in sorted(bkg_ratio.items(), key = lambda item: item[1][class_index], reverse=True)]

            # Plot each feature as a horizontal bar
            for feature in sorted_features:
                width = bkg_ratio[feature][class_index]
                if feature in scalars:
                    ax.barh(LaTeX[feature], width, height=0.8, capsize=5, color=colors['scalars'])
                elif feature in images:
                    ax.barh(LaTeX[feature], width, height=0.8, capsize=5, color=colors['images'])
                else:
                    ax.barh(feature, width, height=0.8, capsize=5, color=colors['others'])

            # Write the ratio in the middle of the bar
            for i in ax.patches:
                plt.text(i.get_width()/2, i.get_y()+0.4, str(round(i.get_width(),3)), ha='center', va='center', color ='white')

            # Red vertical line to highlight the threshold between good and bad variables:
            # Above this line, variables are important; under it, they are detrimental.
            plt.axvline(1, color='r', ls=':')

            # Finish the plot
            plot_title = f"Feature removal importance: {class_name[class_index]}\n {eta_region.split('-')[0]} < $\eta$ < {eta_region.split('-')[1]}, full background rejection at 70% = {data_dict['none'][class_index]}"
            # ax.legend(loc='lower right', prop={'size': 14})
            plt.title(plot_title, fontsize=18)
            ax.set_xlabel(r'$\frac{bkg\_rej\_full}{bkg\_rej}$', fontsize=18)
            ax.set_ylabel('Features', fontsize=18)
            plt.tight_layout()

            # Saving plot
            save_dir = output_dir[0:output_dir.rfind('/')]
            file_name = f"feature_ranking_{class_name[class_index].replace(' ', '_')}"
            try: plt.savefig(f'{save_dir}/{file_name}.pdf')
            except IOError:
                time.sleep(10) # Wait 10s then try again
                try: plt.savefig(f'{save_dir}/{file_name}.pdf')
                except IOError: print('FILE WRITING CONFLICT IN FEATURE RANKING --> SKIPPING FILE WRITING\n')

            # return fig, ax




#################################################################################
#####    presampler.py functions    #############################################
#################################################################################


def presample(h5_file, output_dir, batch_size, sum_e, images, tracks, scalars, integers, file_key, index):
    idx = index*batch_size, (index+1)*batch_size
    with h5py.File(h5_file, 'r') as data:
        images  = list(set(images)   & set(data[file_key]))
        tracks  = list(set(tracks)   & set(data[file_key]))
        scalars = list(set(scalars)  & set(data[file_key]))
        int_val = list(set(integers) & set(data[file_key]))
        sample = {key:data[file_key][key][idx[0]:idx[1]] for key in images+tracks+scalars+int_val}
    for key in images: sample[key] = sample[key]/(sample['p_e'][:, np.newaxis, np.newaxis])
    for key in ['em_barrel_Lr1', 'em_endcap_Lr1']:
        try: sample[key+'_fine'] = sample[key]
        except KeyError: pass
    for key in images        : sample[key] = resize_images(sample[key])
    for key in images+scalars: sample[key] = np.float16(np.clip(sample[key],-5e4,5e4))
    try: sample['p_TruthType']   = sample.pop('p_truthType')
    except KeyError: pass
    try: sample['p_TruthOrigin'] = sample.pop('p_truthOrigin')
    except KeyError: pass
    tracks_list = [np.expand_dims(get_tracks(sample, n, 50            ), axis=0) for n in np.arange(batch_size)]
    sample['tracks'] = np.concatenate(tracks_list)
    tracks_list = [np.expand_dims(get_tracks(sample, n, 20, 'p_'      ), axis=0) for n in np.arange(batch_size)]
    sample['p_tracks'] = np.concatenate(tracks_list)
    tracks_list = [np.expand_dims(get_tracks(sample, n, 20, 'p_', True), axis=0) for n in np.arange(batch_size)]
    tracks_list = np.concatenate(tracks_list)
    tracks_dict = {'p_mean_efrac'  :0 , 'p_mean_deta'   :1 , 'p_mean_dphi'   :2 , 'p_mean_d0'          :3 ,
                   'p_mean_z0'     :4 , 'p_mean_charge' :5 , 'p_mean_vertex' :6 , 'p_mean_chi2'        :7 ,
                   'p_mean_ndof'   :8 , 'p_mean_pixhits':9 , 'p_mean_scthits':10, 'p_mean_trthits'     :11,
                   'p_mean_sigmad0':12, 'p_qd0Sig'      :13, 'p_nTracks'     :14, 'p_sct_weight_charge':15}
    for key in tracks_dict:
        if np.any(tracks_list[:,tracks_dict[key]]!=0): sample[key] = tracks_list[:,tracks_dict[key]]
    for key in ['p_LHTight', 'p_LHMedium', 'p_LHLoose']: sample[key] = np.where(sample[key]==0, 1, 0)
    sample['true_m'] = np.float16(get_truth_m(sample))
    for key in tracks + ['p_truth_E', 'p_truth_e']:
        try: sample.pop(key)
        except KeyError: pass
    with h5py.File(output_dir+'/'+'e-ID_'+'{:=02}'.format(index)+'.h5', 'w' if sum_e==0 else 'a') as data:
        for key in sample:
            shape = (sum_e+batch_size,) + sample[key].shape[1:]
            if sum_e == 0:
                maxshape = (None,) + sample[key].shape[1:]; dtype = 'i4' if key in integers else 'f2'
                data.create_dataset(key, shape, dtype=dtype, maxshape=maxshape, chunks=shape)
            else: data[key].resize(shape)
        for key in sample: data[key][sum_e:sum_e+batch_size,...] = utils.shuffle(sample[key],random_state=0)


def resize_images(images_array, target_shape=(7,11)):
    if images_array.shape[1:] == target_shape: return images_array
    else: return transform.resize(images_array, ( (len(images_array),) + target_shape))


def get_tracks(sample, idx, max_tracks=20, p='', scalars=False):
    tracks_p    = np.cosh(sample[p+'tracks_eta'][idx]) * sample[p+'tracks_pt' ][idx]
    tracks_deta =         sample[p+'tracks_eta'][idx]  - sample[  'p_eta'     ][idx]
    tracks_dphi =         sample[p+'tracks_phi'][idx]  - sample[  'p_phi'     ][idx]
    tracks_d0   =         sample[p+'tracks_d0' ][idx]
    tracks_z0   =         sample[p+'tracks_z0' ][idx]
    tracks_dphi = np.where(tracks_dphi < -np.pi, tracks_dphi + 2*np.pi, tracks_dphi )
    tracks_dphi = np.where(tracks_dphi >  np.pi, tracks_dphi - 2*np.pi, tracks_dphi )
    tracks      = [tracks_p/sample['p_e'][idx], tracks_deta, tracks_dphi, tracks_d0, tracks_z0]
    p_tracks    = ['p_tracks_charge' , 'p_tracks_vertex' , 'p_tracks_chi2'   , 'p_tracks_ndof',
                   'p_tracks_pixhits', 'p_tracks_scthits', 'p_tracks_trthits', 'p_tracks_sigmad0']
    #if p == 'p_': tracks += [sample[key][idx] for key in p_tracks]
    if p == 'p_':
        for key in p_tracks:
            try: tracks += [sample[key][idx]]
            except KeyError: tracks += [np.zeros(sample['p_tracks_charge'][idx].shape)]
    tracks      = np.float16(np.vstack(tracks).T)
    tracks      = tracks[np.isfinite(np.sum(abs(tracks), axis=1))][:max_tracks,:]
    #tracks      = np.float16(np.clip(np.vstack(tracks).T,-5e4,5e4))[:max_tracks,:]
    if p == 'p_' and scalars:
        tracks_means       = np.mean(tracks,axis=0) if len(tracks)!=0 else tracks.shape[1]*[0]
        qd0Sig             = sample['p_charge'][idx] * sample['p_d0'][idx] / sample['p_sigmad0'][idx]
        if np.any(sample['p_tracks_scthits'][idx]!=0):
            sct_weight_charge  = sample['p_tracks_charge'][idx] @     sample['p_tracks_scthits'][idx]
            sct_weight_charge *= sample['p_charge'       ][idx] / sum(sample['p_tracks_scthits'][idx])
        else: sct_weight_charge = 0
        return np.concatenate([tracks_means, np.array([qd0Sig, len(tracks), sct_weight_charge])])
    else:
        return np.vstack([tracks, np.zeros((max(0, max_tracks-len(tracks)), tracks.shape[1]))])


def get_truth_m(sample, new=True, m_e=0.511, max_eta=4.9):
    truth_eta = np.float64(np.vectorize(min)(abs(sample['p_truth_eta']), max_eta))
    try:             truth_e = np.float64(sample['p_truth_E' ])
    except KeyError: truth_e = np.float64(sample['p_truth_e' ])
    truth_pt  = np.float64(sample['p_truth_pt'])
    truth_s   = truth_e**2 - (truth_pt*np.cosh(truth_eta))**2
    if new: return np.where(truth_eta == max_eta, -1, np.sqrt(np.vectorize(max)(m_e**2, truth_s)))
    else:   return np.where(truth_eta == max_eta, -1, np.sign(truth_s)*np.sqrt(abs(truth_s)) )


def merge_presamples(output_dir, output_file):
    h5_files = [h5_file for h5_file in os.listdir(output_dir) if 'e-ID_' in h5_file and '.h5' in h5_file]
    if len(h5_files) == 0: sys.exit()
    np.random.seed(0); np.random.shuffle(h5_files)
    idx = np.cumsum([len(h5py.File(output_dir+'/'+h5_file, 'r')['eventNumber']) for h5_file in h5_files])
    os.rename(output_dir+'/'+h5_files[0], output_dir+'/'+output_file)
    dataset = h5py.File(output_dir+'/'+output_file, 'a')
    GB_size = len(h5_files)*sum([np.float16(dataset[key]).nbytes for key in dataset])/(1024)**2/1e3
    print('MERGING DATA FILES (', '\b{:.1f}'.format(GB_size),'GB) IN:', end=' ')
    print('output/'+output_file, end=' .' if len(h5_files)>1 else '', flush=True); start_time = time.time()
    for key in dataset: dataset[key].resize((idx[-1],) + dataset[key].shape[1:])
    for h5_file in h5_files[1:]:
        data  = h5py.File(output_dir+'/'+h5_file, 'r')
        index = h5_files.index(h5_file)
        for key in dataset: dataset[key][idx[index-1]:idx[index]] = data[key]
        data.close(); os.remove(output_dir+'/'+h5_file)
        print('.', end='', flush=True)
    print(' (', '\b'+format(time.time() - start_time,'.1f'), '\b'+' s) -->', idx[-1], 'ELECTRONS COLLECTED\n')
