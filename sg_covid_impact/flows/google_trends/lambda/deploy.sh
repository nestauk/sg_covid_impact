#!/bin/bash

# Build image to build python deps in
docker build -t awslambdabuilder .

# Build python deps
docker run -v $(pwd):/out -it awslambdabuilder

# Copy package to s3 
aws s3 cp lambda-deploy-package.zip s3://nesta-test

# Update lambda function
aws lambda update-function-code --function-name query-google-trends --s3-bucket nesta-test --s3-key lambda-deploy-package.zip
