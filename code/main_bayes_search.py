# --------- Main script: Bayes Search of Hyperparameters ------------------ #

import sys
import numpy as np
import tensorflow as tf
import pandas as pd
import time
import os
from os.path import dirname as up

from skopt import gp_minimize, dump
from ann.helpers import *
from ann.neural_network import *
from ann.train import *

deep_cal_dir = up(os.getcwd())

# --------------------- Logging stuff ------------------------------------- #

logger = logging.getLogger("bayes_hyper_opt")
logger.setLevel(logging.INFO)
fh = logging.FileHandler("logs/bayes_hyper_opt.log")    
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
logger.addHandler(fh)

logger.info("PROGRAM START")
logger.debug("Python version" + sys.version)
logger.debug("Tensorflow version" + tf.__version__)

# --------------------- Configuration ------------------------------------- #

# Labeled data configuration
train_filename = deep_cal_dir + '/data/heston/training_data.csv'
validation_filename = deep_cal_dir + '/data/heston/validation_data.csv'
feature_cols = [ _ for _ in range(7)]
label_cols = [7]

# Training configuration
random_seed = 2018
nb_epochs = 20

# Search space
space = [(1,12), 
         (1,12),
         (1,12),
         (1,12),
         (-7.0, -2.0),
         (5,12),
         (0.25,1.0)
        ]

# Gaussian optimization parameters
n_calls = 100
n_random_starts = 33
acq_func = 'EIps'
n_jobs = -1
verbose = True
random_state = random_seed + 1

# ------------------------------- Preprocessing --------------------------- #

# Read training and validation data named tuples into memory.
logger.info("Importing and normalizing input labeled data.")
train_tuple = load_labeled_csv(train_filename, feature_cols, label_cols)
validation_tuple = load_labeled_csv(validation_filename, feature_cols, label_cols)

# Normalize training and validation data by training statistics
train_mean = np.mean(train_tuple.features, axis=0)
train_std = np.std(train_tuple.features, axis=0)

train_tuple.features -= train_mean
train_tuple.features /= train_std

validation_tuple.features -= train_mean
validation_tuple.features /= train_std

logger.info('Finished import and normalization of input data.')

# ------------------------------- Optimisation ---------------------------- #

def train_bayes(params):
    """
    Wrapper around train function to serve as objective function for Gaussian
    optimization in scikit-optimize routine gp_minimize.

    Arguments:
    ----------
        params: list, shape=[nb_layers + 2,]
        List of search space dimensions. Entries have to be tuples 
        (lower_bound, upper_bound) for Reals or Integers.

    Returns:
    --------
        tbd

    """
    # Translate params into format understood by train function
    layer_sizes = (2**np.array(params[:4])).tolist()
    learning_rate = 10**params[4]
    mini_batch_size = 2**params[5]
    pkeep = 1
    hyper_params = [layer_sizes, learning_rate, mini_batch_size, pkeep]
    hyper_param_str = make_hyper_param_str(hyper_params)

    # Call train function
    tic = time.time()
    logger.info('Start training for ' + hyper_param_str)
    log_df, best_error = train(train_tuple, validation_tuple, hyper_params, 
                               nb_epochs, random_seed, verbose=True)
    elapsed_time = time.time() - tic
    logger.info('Finished training in %i s.' %elapsed_time)

    # Writing Pandas log file to csv file on disk.
    logger.info('Writing pandas DF log to disk.')
    log_df.to_csv(hyper_param_str + '/log_file.csv')
    
    return best_error, elapsed_time

# Gaussian optimisation
logger.info('Running Gaussian optimisation with %i calls, %i random starts and \
            %s as acquisition function.' % (n_calls,n_random_starts,acq_func))


res_gp = gp_minimize(train_bayes, space, 
                    n_calls=n_calls, 
                    n_random_starts=n_random_starts, 
                    acq_func=acq_func, 
                    n_jobs=n_jobs, 
                    verbose=verbose, 
                    random_state=random_state
                    )

logger.info('Gaussian optimisation finished. Now saving results to disk.')

dump(res_gp, 'bayes.gz')

logger.info('Optimisation finished. DONE.')
