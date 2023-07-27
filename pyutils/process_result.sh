#!/bin/bash
while read line
do
    echo $line | cut -d \: -f 1 >> name.data
done < result.json

while read line
do
    cat logs.data | grep "(${line})" > ${line}.testlog
done < name.data
