import os
import re
from structai import LLMAgent
from utils.logger import create_logger

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC
from sklearn.neighbors import KNeighborsClassifier
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LinearRegression
from sklearn.linear_model import Ridge
from sklearn.linear_model import Lasso
from sklearn.svm import SVR
from sklearn.ensemble import RandomForestRegressor
from sklearn.cluster import KMeans
from sklearn.cluster import DBSCAN
from sklearn.cluster import AgglomerativeClustering
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.metrics import confusion_matrix
from sklearn.metrics import classification_report
from sklearn.metrics import accuracy_score
from sklearn.metrics import mean_squared_error
from sklearn.metrics import r2_score
from sklearn.preprocessing import StandardScaler
from sklearn.preprocessing import MinMaxScaler
from sklearn.preprocessing import OneHotEncoder
from sklearn.impute import SimpleImputer
import matplotlib.pyplot as plt
import copy

system_prompt = """
You are an expert in <INPUT1>. You are good at data analysis and visualization.
Please complete the corresponding code according to user needs.
"""

query_prompt = """
Now we have data, which is pandas data, where data.head() is as follows:
<INPUT1>

We have imported the following functions, you can freely choose and use them, and finally use plt.show() to display.

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC
from sklearn.neighbors import KNeighborsClassifier
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LinearRegression
from sklearn.linear_model import Ridge
from sklearn.linear_model import Lasso
from sklearn.svm import SVR
from sklearn.ensemble import RandomForestRegressor
from sklearn.cluster import KMeans
from sklearn.cluster import DBSCAN
from sklearn.cluster import AgglomerativeClustering
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.metrics import confusion_matrix
from sklearn.metrics import classification_report
from sklearn.metrics import accuracy_score
from sklearn.metrics import mean_squared_error
from sklearn.metrics import r2_score
from sklearn.preprocessing import StandardScaler
from sklearn.preprocessing import MinMaxScaler
from sklearn.preprocessing import OneHotEncoder
from sklearn.impute import SimpleImputer
import matplotlib.pyplot as plt

When replying, please strictly follow the following rules:
1. Please implement three visualization functions based on clustering, classification, and regression models respectively.
2. Do not use plt.savefig() function, use plt.show() function.
3. Use the plt.title() function to explain the meaning of the visualization. 
Please use a sentence to describe the meaning of the different coordinates or curves in the image so that the meaning of the image can be understood at first glance.
Please include appropriate line breaks in the title to avoid title overflow or obstruction.
4. All functions end with return.

Example:
def clustering(data):
    ...
    return

def classification(data):
    ...
    return

def regression(data):
    ...
    return
"""

run_code = """

try:
    self.clustering_error = None
    clustering(copy.deepcopy(self.data))
    plt.tight_layout()
    plt.savefig(os.path.join(self.visualization_dir, 'clustering.png'), dpi=300)
    plt.close()
except Exception as e:
    self.clustering_error = str(e)
    print(f'[===ERROR===][clustering][{e}]')

try:
    self.classification_error = None
    classification(copy.deepcopy(self.data))
    plt.tight_layout()
    plt.savefig(os.path.join(self.visualization_dir, 'classification.png'), dpi=300)
    plt.close()
except Exception as e:
    self.classification_error = str(e)
    print(f'[===ERROR===][classification][{e}]')

try:
    self.regression_error = None
    regression(copy.deepcopy(self.data))
    plt.tight_layout()
    plt.savefig(os.path.join(self.visualization_dir, 'regression.png'), dpi=300)
    plt.close()
except Exception as e:
    self.regression_error = str(e)
    print(f'[===ERROR===][regression][{e}]')
"""


class DataAnalyst(LLMAgent):
    def __init__(self,
                save_dir: str,
                api_key = None,
                api_base = None,
                model_version = 'gpt-5.2',
                system_prompt = system_prompt,
                max_tokens = 4096,
                temperature = 0.8,
                http_client = None,
                headers = None,
                time_limit = 5*60,
                max_try = 1,
                use_responses_api = False,
                field = 'climate',
                max_code_try = 3
                ):
        super().__init__(api_key, api_base, model_version, system_prompt, max_tokens, temperature, http_client, headers, time_limit, max_try, use_responses_api)
        self.system_prompt = self.system_prompt.replace('<INPUT1>', field)
        self.field = field
        self.max_code_try = max_code_try

        self.logger = create_logger('DataAnalyst', os.path.join(save_dir, 'log'))
        self.data_path = os.path.join(save_dir, 'meta_analysis.csv')
        self.data = pd.read_csv(self.data_path).fillna(0)
        if 'Reference' in self.data.columns:
            self.data = self.data.drop(columns=['Reference'])
        self.logger.info(f'Loaded {self.data_path}, shape: {self.data.shape}')

        self.visualization_dir = os.path.join(save_dir, '4_visualization')
        os.makedirs(self.visualization_dir, exist_ok=True)

        self.clustering_error = None
        self.classification_error = None
        self.regression_error = None


    def split_functions(self, code_text):
        functions = re.findall(r'def.*?return', code_text, re.DOTALL)
        return functions

    def _run_code(self, code):
        code = code + run_code
        exec(code)

    def code_api(self, quey):
        code_str = self.safe_api(quey)
        functions = self.split_functions(code_str)
        functions = '\n\n'.join(functions)
        return functions


    def __call__(self):
        self.logger.info(f'Running data analysis and visualization')
        quey = query_prompt.replace('<INPUT1>', str(self.data.head()))
        code = self.code_api(quey)
        # print(code)
        self._run_code(code)
        external_prompt = ''
        if self.clustering_error is not None:
            external_prompt = external_prompt +  f"[===ERROR===][clustering][{self.clustering_error}]\n"
        if self.classification_error is not None:
            external_prompt = external_prompt +  f"[===ERROR===][classification][{self.classification_error}]\n"
        if self.regression_error is not None:
            external_prompt = external_prompt +  f"[===ERROR===][regression][{self.regression_error}]\n"

        if external_prompt == '':
            self.logger.info(f'All functions run successfully')
        else:
            for try_idx in range(self.max_code_try):
                self.logger.info(f'try {try_idx+1}/{self.max_code_try}')
                code = self.code_api(quey+'\n'+code+'\nThere is a bug:\n' + external_prompt + 'Please try a different way of analysis and visualization.')
                
                self._run_code(code)
                external_prompt = ''
                if self.clustering_error is not None:
                    external_prompt = external_prompt +  f"[===ERROR===][clustering][{self.clustering_error}]\n"
                if self.classification_error is not None:
                    external_prompt = external_prompt +  f"[===ERROR===][classification][{self.classification_error}]\n"
                if self.regression_error is not None:
                    external_prompt = external_prompt +  f"[===ERROR===][regression][{self.regression_error}]\n"
                if external_prompt == '':
                    self.logger.info(f'All functions run successfully')
                    break

                if try_idx == self.max_code_try-1:
                    self.logger.info(f'[===ERROR===][code][Failed]')


if __name__ == '__main__':
    save_dir = 'data/environment/2025_0402_170228'
    data_analyst = DataAnalyst(save_dir)
    data_analyst()
