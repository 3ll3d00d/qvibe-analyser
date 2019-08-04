#!/bin/bash
for ui in $(ls *.ui)
do
    echo "Compiling ${ui}"
    /home/matt/.local/share/virtualenvs/qvibe-analyser-d2Oe_ZNQ/bin/pyuic5 "${ui}" -o "${ui%.ui}.py"
done