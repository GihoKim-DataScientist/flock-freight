# 1) choose base container
# generally use the most recent tag

# base notebook, contains Jupyter and relevant tools
# See https://github.com/ucsd-ets/datahub-docker-stack/wiki/Stable-Tag 
# for a list of the most current containers we maintain
ARG BASE_CONTAINER=ucsdets/datahub-base-notebook:2022.3-stable

FROM $BASE_CONTAINER

LABEL maintainer="UC San Diego ITS/ETS <ets-consult@ucsd.edu>"

# 2) change to root to install packages
# USER root

# RUN apt-get -y install htop

# 3) install packages using notebook user
USER jovyan

# RUN conda install -y scikit-learn

# RUN pip install --no-cache-dir appnope==0.1.3 asttokens==2.2.0 backcall==0.2.0 businesstimedelta==1.0.1 convertdate==2.4.0 debugpy==1.6.4 decorator==5.1.1 entrypoints==0.4 executing==1.2.0 hijri-converter==2.2.4\
#     holidays==0.17.2 ipykernel==6.17.1 ipython==8.7.0 jedi==0.18.2 joblib==1.2.0 jupyter_client==7.4.7 jupyter_core==5.1.0 korean-lunar-calendar==0.3.1 matplotlib-inline==0.1.6\
#     nest-asyncio==1.5.6 numpy==1.23.5 packaging==21.3 pandas==1.5.2 parso==0.8.3 pexpect==4.8.0 pickleshare==0.7.5 platformdirs==2.5.4 postalcodes-ca==0.0.9 prompt-toolkit==3.0.33\
#     psutil==5.9.4 ptyprocess==0.7.0 pure-eval==0.2.2 Pygments==2.13.0 PyMeeus==0.5.11 pyparsing==3.0.9 python-dateutil==2.8.2 pytz==2022.6 pyzmq==24.0.1 scikit-learn==1.1.3 scipy==1.9.3\
#     six==1.16.0 sklearn==0.0.post1 stack-data==0.6.2 threadpoolctl==3.1.0 tornado==6.2 traitlets==5.6.0 wcwidth==0.2.5 xgboost==1.7.1

RUN pip install --no-cache-dir businesstimedelta==1.0.1 geopandas==0.12.2 holidays==0.17.2 numpy==1.19.2 pandas==1.1.3 postalcodes_ca==0.0.9 scikit_learn==1.2.2 xgboost==1.7.4

# Override command to disable running jupyter notebook at launch
CMD ["/bin/bash"]