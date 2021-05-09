FROM python:3.7.7-slim-stretch as base

RUN apt-get update \
    && apt-get -y install git python3-pip python3-dev tzdata \
      libffi-dev protobuf-compiler libprotobuf-dev udev \
    && rm -rf /var/lib/apt/lists/*

ENV WHEEL_DIR=/svc/wheels

COPY requirements.txt /
RUN pip3 install wheel \
  && pip3 wheel --requirement /requirements.txt --wheel-dir=${WHEEL_DIR}

FROM python:3.7.7-slim-stretch as prod

COPY --from=base /svc /svc

RUN apt-get update \
    && apt-get -y install doxygen kmod latexmk libusb-1.0.0 network-manager python3-pip texlive-fonts-extra texlive-latex-recommended unzip wireless-tools wget \
    && rm -rf /var/lib/apt/lists/* \
    && pip3 install --no-index /svc/wheels/* \
    && rm -rf /svc

# Yocto builds glibc in /lib by default. Ethercat binary is linked to it
RUN ln -s /lib64/ld-linux-x86-64.so.2 /lib

ENV PATH="/opt/etherlab/bin:${PATH}"

