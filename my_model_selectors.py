import math
import statistics
import warnings

import numpy as np
from hmmlearn.hmm import GaussianHMM
from sklearn.model_selection import KFold
from asl_utils import combine_sequences


class ModelSelector(object):
    '''
    base class for model selection (strategy design pattern)
    '''

    def __init__(self, all_word_sequences: dict, all_word_Xlengths: dict, this_word: str,
                 n_constant=3,
                 min_n_components=2, max_n_components=10,
                 random_state=14, verbose=False):
        self.words = all_word_sequences
        self.hwords = all_word_Xlengths
        self.sequences = all_word_sequences[this_word]
        self.X, self.lengths = all_word_Xlengths[this_word]
        self.this_word = this_word
        self.n_constant = n_constant
        self.min_n_components = min_n_components
        self.max_n_components = max_n_components
        self.random_state = random_state
        self.verbose = verbose

    def select(self):
        raise NotImplementedError

    def base_model(self, num_states):
        # with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=DeprecationWarning)
        # warnings.filterwarnings("ignore", category=RuntimeWarning)
        try:
            hmm_model = GaussianHMM(n_components=num_states, covariance_type="diag", n_iter=1000,
                                    random_state=self.random_state, verbose=False).fit(self.X, self.lengths)
            if self.verbose:
                print("model created for {} with {} states".format(self.this_word, num_states))
            return hmm_model
        except:
            if self.verbose:
                print("failure on {} with {} states".format(self.this_word, num_states))
            return None


class SelectorConstant(ModelSelector):
    """ select the model with value self.n_constant

    """

    def select(self):
        """ select based on n_constant value

        :return: GaussianHMM object
        """
        best_num_components = self.n_constant
        return self.base_model(best_num_components)


class SelectorBIC(ModelSelector):
    """ select the model with the lowest Baysian Information Criterion(BIC) score

    http://www2.imm.dtu.dk/courses/02433/doc/ch6_slides.pdf
    Bayesian information criteria: BIC = -2 * logL + p * logN

    N: number of data points
    p: number of parameters
    Assume 
        # of features = d
        # of HMM states = n
    Then
    p = 
        # of probabilities in transition matrix + 
        # of probabilities in initial distribution + 
        # of Gaussian mean + 
        # of Gaussian variance 
      = 
        n*(n-1) + (n-1) + 2*d*n
    """

    def select(self):
        """ select the best model for self.this_word based on
        BIC score for n between self.min_n_components and self.max_n_components

        :return: GaussianHMM object
        """
        warnings.filterwarnings("ignore", category=DeprecationWarning)

        # TODO implement model selection based on BIC scores
        all_n_components = []
        all_scores = [] # Store each BIC value
        N, d = self.X.shape
        for n_components in range(self.min_n_components, self.max_n_components+1):
            try:
                model = self.base_model(n_components)
                logL = model.score(self.X, self.lengths)
                bic = -2 * logL + (n_components*(n_components-1) + (n_components-1) + 2*d*n_components) * np.log(N)
                all_scores.append(bic)
                all_n_components.append(n_components)
            except:
                # eliminate non-viable models from consideration
                pass

        best_num_components = all_n_components[np.argmin(all_scores)] if all_scores else self.n_constant
        return self.base_model(best_num_components)


class SelectorDIC(ModelSelector):
    ''' select best model based on Discriminative Information Criterion

    Biem, Alain. "A model selection criterion for classification: Application to hmm topology optimization."
    Document Analysis and Recognition, 2003. Proceedings. Seventh International Conference on. IEEE, 2003.
    http://citeseerx.ist.psu.edu/viewdoc/download?doi=10.1.1.58.6208&rep=rep1&type=pdf
    DIC = log(P(X(i)) - 1/(M-1)SUM(log(P(X(all but i))
    '''

    def select(self):
        warnings.filterwarnings("ignore", category=DeprecationWarning)

        # TODO implement model selection based on DIC scores
        all_n_components = []
        all_logLs = [] 
        sum_logL = 0
        for n_components in range(self.min_n_components, self.max_n_components+1):
            try:
                model = self.base_model(n_components)
                logL = model.score(self.X, self.lengths)
                sum_logL += logL
                all_logLs.append(logL)
                all_n_components.append(n_components)
            except:
                # eliminate non-viable models from consideration
                pass

        M = len(all_n_components)-1 # It's actually M-1 value, not M
        if M > 1:
            all_scores = [] # Store each DIC value
            for logL in all_logLs:
                dic = logL - (sum_logL-logL) / M
                all_scores.append(dic)
            best_num_components = all_n_components[np.argmax(all_scores)]
        elif M == 1:
            best_num_components = all_n_components[0]
        else:
            best_num_components = self.n_constant

        return self.base_model(best_num_components)


class SelectorCV(ModelSelector):
    ''' select best model based on average log Likelihood of cross-validation folds

    '''

    def select(self):
        warnings.filterwarnings("ignore", category=DeprecationWarning)

        # TODO implement model selection using CV

        all_n_components = []
        split_method = KFold()
        all_scores = [] # Store each CV value
        for n_components in range(self.min_n_components, self.max_n_components+1):
            try:
                if len(self.sequences) > 2: # Check if there are enough data to split
                    scores = []
                    for cv_train_idx, cv_test_idx in split_method.split(self.sequences):
                        # Prepare training sequences
                        self.X, self.lengths = combine_sequences(cv_train_idx, self.sequences)
                        # Prepare testing sequences
                        X_test, lengths_test = combine_sequences(cv_test_idx, self.sequences)
                        model = self.base_model(n_components)
                        scores.append(model.score(X_test, lengths_test))
                    all_scores.append(np.mean(scores))
                else:
                    model = self.base_model(n_components)
                    all_scores.append(model.score(self.X, self.lengths))
                all_n_components.append(n_components)
            except:
                # eliminate non-viable models from consideration
                pass

        best_num_components = all_n_components[np.argmax(all_scores)] if all_scores else self.n_constant
        return self.base_model(best_num_components)
