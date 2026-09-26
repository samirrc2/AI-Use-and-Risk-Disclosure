# hash:sha256:6c6ad5c8d95ca4781b2f2336c55be8c0a3372b3dbcf554ba22ff193d872d36d8
# Code Ocean capsule environment for "AI Use and Risk Disclosure by Investment Advisers".
# Reproduction is offline and deterministic; no API keys or network are required.
# Local development: use code/requirements.txt in a virtualenv instead.
FROM registry.codeocean.com/codeocean/py-r:python3.12.8-R4.4.2-JupyterLab4.3.5-RStudiorstudio-server-2024.12.1-563-ubuntu22.04

ARG DEBIAN_FRONTEND=noninteractive

RUN pip install -U --no-cache-dir \
    matplotlib==3.9.2 \
    numpy==2.2.6 \
    pandas==2.2.3 \
    pytest==8.3.3 \
    scipy==1.14.1 \
    statsmodels==0.14.4
