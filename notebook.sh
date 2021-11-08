#!/bin/bash
# Run this along with `ssh -L 7777:localhost:7777 <hostname>` locally

jupyter notebook --no-browser --port=7777
