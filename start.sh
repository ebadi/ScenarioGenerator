#!/bin/bash

PARAMETERS="--input simplePedestrian.json --steps 12 --des-forward-right  140  -1  --seed 28 --speed-max-noise 3 --pos-noise-range-xz 3 3 --color-noise-range-rgb 50 50 50 --time-max-noise 3 --weather-noise-range 0.2 0.2 0.2 0.2 0.2"

python3 ScenarioGenerator.py --action random $PARAMETERS
# python3 ScenarioGenerator.py --action powell $PARAMETERS
# python3 ScenarioGenerator.py --action differential_evolution $PARAMETERS



