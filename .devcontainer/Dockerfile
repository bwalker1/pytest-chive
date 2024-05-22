FROM blwalker/devcon as env
WORKDIR /tmp
ENV MAMBA_ROOT_PREFIX=/opt/conda
ENV CONDA_PKGS_DIRS=/opt/conda/pkgs
SHELL ["bash", "-lc"] 
RUN --mount=type=cache,target=/opt/conda/pkgs \
    --mount=type=bind,source=environment.yml,target=environment.yml \
    eval "$(micromamba shell hook --shell bash)" && \
    micromamba activate && \
    micromamba install -n base -y -f environment.yml git openssh python=3.12 -c conda-forge 


FROM blwalker/devcon as dev
COPY --from=env --chmod=777 /opt/conda /opt/conda
USER vscode
SHELL ["bash", "-lc"] 
ENV MAMBA_ROOT_PREFIX=/opt/conda
RUN /usr/local/bin/micromamba shell init --shell=bash && \
    echo 'export PATH=/workspaces/chive:$PATH' >> /home/vscode/.bashrc && \
    echo 'micromamba activate' >> /home/vscode/.bashrc


FROM dev as repo
USER root
SHELL ["bash", "-lc"] 
ENV MAMBA_ROOT_PREFIX=/opt/conda
ENV CONDA_PKGS_DIRS=/opt/conda/pkgs
WORKDIR /tmp/chive
COPY . /tmp/chive/
RUN eval "$(micromamba shell hook --shell bash)" && \
    micromamba activate && \
    pip install /tmp/chive


FROM dev
COPY --from=repo --chmod=777 /opt/conda /opt/conda
WORKDIR /workspaces/chive
#ENTRYPOINT ["bash", "-lc"]
USER vscode