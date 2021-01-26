#!/bin/bash

source ~/.profile

pyenv local $PY_VER
pyenv virtualenv $PY_VER lambda
pyenv activate lambda

pip install -U pip

pip install --no-binary :all: -r requirements.txt

PYTHON_MINOR_VERSION=$(python3 -c "import sys; print(sys.version_info[1])")

# specify where the shared libraries will be stored
libdir="$VIRTUAL_ENV/lib/python3.$PYTHON_MINOR_VERSION/site-packages/lib/"
echo Library directory: $libdir
mkdir -p $libdir
# copy the libraries
cp -v /usr/lib64/atlas/*.so.3 $libdir
cp -v /usr/lib64/libquadmath.so.0 $libdir
cp -v /usr/lib64/libgfortran.so.3 $libdir
cp -v /usr/lib64/libpng.so.3 $libdir
cp -v /usr/lib64/libjpeg.so.62 $libdir
cp -v /usr/lib64/libtiff.so.5 $libdir

# make object files smaller
find $VIRTUAL_ENV/lib/python3.$PYTHON_MINOR_VERSION/site-packages/ -name "*.so*" | xargs strip -v

# compress site-packages content into mylambda.zip
cd $VIRTUAL_ENV/lib/python3.$PYTHON_MINOR_VERSION/site-packages/ 
zip -r -9 /lambda/lambda-deploy-package.zip *
cd /lambda

zip -ur lambda-deploy-package.zip lambda_function.py

mkdir -p /out
cp lambda-deploy-package.zip /out/.
