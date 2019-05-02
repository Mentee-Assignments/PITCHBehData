#!/usr/bin/env python
import os
from glob import glob
import re
import pandas as pd
import numpy as np

# change directory to get the script to work the same as it does in the tests
script_path = os.path.dirname(os.path.realpath(__file__))
pitch_dir = os.path.dirname(os.path.dirname(script_path))

path = os.path.join(pitch_dir, 'Raw')
out_dir = os.path.join(pitch_dir, 'Bids')
beh = glob(os.path.join(path, 'Beh/*[DurationRT]*.txt'))
translation_dict = {'condition': {'E': 'Experimental', 'C': 'Control'}, 'run_id': {'A': '1', 'B': '2'}, 'session': {'1': 'Pre', '2': 'Post'}}

# rough draft
# Optionally match 'ALL'
pattern = re.compile(r"^.*$")#Raw/Beh/P(?P<subject_id>[0-9]{2})(?P<condition>[CE])(?P<session>[1-2])BOL_(?P<trial_type>[IncCogruetNal]+)_[InCorect]+_(?P<run_id>[AB])_[DurationRT]+.txt$")
beh_dict = {}
for filename in beh:
    res = re.search(pattern, filename)
    dict_key = '_'.join(res.groups()[:-1])
    if dict_key in beh_dict:
        beh_dict[dict_key].append(filename)
    else:
        beh_dict[dict_key] = [filename]

cond_pattern = re.compile(r"^.*beh/.*?([NCIa-z]*)_([ICa-z]*)_[A-Z]_[RTDa-z]*.txt$")
cond_dict = {}
for sub_stype_ses_run, fnames in beh_dict.items():
    for f in fnames:
        find_cond = re.search(cond_pattern, f)
        cond_corr = '_'.join(find_cond.groups())
        if sub_stype_ses_run in cond_dict:
            if cond_corr in cond_dict[sub_stype_ses_run]:
                cond_dict[sub_stype_ses_run][cond_corr].append(f)
            else:
                cond_dict[sub_stype_ses_run][cond_corr] = [f]
        else:
            cond_dict[sub_stype_ses_run] = {cond_corr: [f]}


def non_zero_file(fpath):
    return os.path.isfile(fpath) and os.path.getsize(fpath) > 0


headers = ['onset', 'duration', 'response_time', 'correct', 'trial_type']

for sub_stype_ses_run, fdict in cond_dict.items():
    run_df = pd.DataFrame(columns=headers)
    # make the output dataframe for this subject
    for cond_corr, fnames in fdict.items():
        fname_dict = {'Duration': None, 'RT': None}
        cond, corr = cond_corr.split('_')
        for fname in fnames:  # has RT and Duration file
            print(fname)
            if 'Duration' in fname:
                col_names = ['onset', 'duration', 'extra1', 'extra2']
                key = 'Duration'
            elif 'RT' in fname:
                col_names = ['onset', 'response_time', 'extra1', 'extra2']
                key = 'RT'
            else:
                print('something is wrong for {fname}'.format(fname=fname))
            if non_zero_file(fname):
                # load fname into pandas dataframe
                df_fname = pd.read_csv(fname, sep='       ', header=None)
                df_fname.columns = col_names
                df_fname.drop(labels=['extra1', 'extra2'], axis=1, inplace=True)
                fname_dict[key] = df_fname
                new_cols = ['trial_type', 'correct']
                cond_list = [cond_corr.lower() for _ in range(len(df_fname))]
                if corr == 'Correct':
                    int_corr = 1
                elif corr == 'Incorrect':
                    int_corr = 0
                else:
                    print('{fcorr} is neither correct nor incorrect'.format(fcorr=corr))
                corr_list = [int_corr for _ in range(len(df_fname))]
                # Add corr_list and cond_list to df_fname
                for lst, coln in zip([cond_list, corr_list], new_cols):
                    se = pd.Series(lst)
                    df_fname[coln] = se.values
        if fname_dict['Duration'] is not None:
            if fname_dict['RT'] is None:
                df_Nan = fname_dict['Duration'].copy()
                df_Nan.rename(index=str, columns={'duration': 'response_time'}, inplace=True)
                RT_list = [np.nan] * len(df_Nan)
                df_Nan['response_time'] = RT_list
                fname_dict['RT'] = df_Nan
            df_cond_corr = pd.merge(fname_dict['Duration'], fname_dict['RT'], on=['onset', 'correct', 'trial_type'])
            # Append the resulting df from the above operation to run_df
            run_df = run_df.append(df_cond_corr)
    run_df = run_df[headers]
    run_df.sort_values(by=['onset'], inplace=True)
    sub, stype, ses, run = sub_stype_ses_run.split('_')
    out_file_dir = os.path.join(os.getcwd(), 'Bids/sub-0{sub}/ses-{stype}{ses}/func/'.format(sub=sub, ses=ses, stype=stype))
    os.makedirs(out_file_dir, exist_ok=True)
    out_file = os.path.join(out_file_dir, 'sub-0{sub}_ses-{stype}{ses}_task-flanker_run-0{run}_events.tsv'.format(sub=sub, ses=ses, run=run, stype=stype))
    if not run_df.empty:
        run_df.to_csv(out_file, sep='\t', na_rep='NaN', index=False)
