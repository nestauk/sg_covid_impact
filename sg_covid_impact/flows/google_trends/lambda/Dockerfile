FROM amazonlinux:2018.03.0.20180827

RUN yum update -y && yum install -y gcc48 gcc48-c++ python3 python3-devel \
atlas-devel atlas-sse3-devel blas-devel lapack-devel zlib-devel libpng-devel \
libjpeg-turbo-devel zip freetype-devel findutils libtiff libtiff-devel \
libxml2-devel libxslt-devel lxml gcc-c++ git make build-essential libssl-dev zlib1g-dev \
libbz2-dev libreadline-dev libsqlite3-dev wget curl llvm libncurses5-dev \
libncursesw5-dev xz-utils tk-dev libffi-dev liblzma-dev python-openssl \
tar bzip2 bzip2-devel readline-devel openssl-devel libffi-devel


# Install pyenv and desired python version
RUN curl https://pyenv.run | bash
RUN echo "export PATH=\"/root/.pyenv/bin:\$PATH\"" >> /root/.profile
RUN echo "eval \"\$(pyenv init -)\"" >> /root/.profile
RUN echo "eval \"\$(pyenv virtualenv-init -)\"" >> /root/.profile
RUN echo export PY_VER=3.7.9 >> /root/.profile
SHELL ["/bin/bash", "--login", "-c"]
RUN pyenv install $PY_VER

# Copy scripts across
WORKDIR lambda
COPY lambda_function.py .
COPY requirements.txt .
COPY build_packages.sh /usr/bin/build_packages.sh

# Build lambda deployment zip file
CMD ["build_packages.sh"]

