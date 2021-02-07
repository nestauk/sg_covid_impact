#!/bin/sh

cd $(dirname $0)/..

# Install if not existent
(npm list http-server > /dev/null) || npm install http-server

# Run if not running
(netstat -a -n -o | grep 8080 > /dev/null) || npx http-server --cors -p 8080
