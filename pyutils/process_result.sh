#!/bin/bash
while read line
do
    echo $line | cut -d \: -f 1 >> ../name.data
done < ../result.json
