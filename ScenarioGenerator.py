#!/usr/bin/env python3

"""
Credits
This work is done by Infotiv AB under VALU3S project. This project has received funding from the ECSEL Joint Undertaking (JU) under grant agreement No 876852. The JU receives support from the European Union’s Horizon 2020 research and innovation programme and Austria, Czech Republic, Germany, Ireland, Italy, Portugal, Spain, Sweden, Turkey. The project is currently maintained by Hamid Ebadi.
"""
import argparse
from Simulation import *
from modules.differential_evolution import *
from modules.basic_minimize import *
from modules.genetic_algorithm_minimize import *
import csv

logging.basicConfig(level=logging.INFO)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Scenario generator from scenarios that are created by SVL Visual Editor')
    parser.add_argument('-i', '--input', required=True, type=str, help="SVL Visual Editor json file")
    parser.add_argument("--action", required=True, type=str, help="mode of operation (replay only runs a scenario with the given noise vector), for scenario generation several optimization strategies are supported (differential_evolution, powell, genetic_algorithm, random)")
    parser.add_argument("--vector", required=False, type=float, nargs="+", help="Noise Vector for scenario replay")
    parser.add_argument('--des-forward-right', required=False, type=float, nargs=2, help="destination from ego vehicle")
    parser.add_argument('--seed', required=False,  type=int, nargs=1, help="random number generator seed")
    parser.add_argument('--steps', required=False,  type=int, nargs=1, help="duration of a scenario")
    parser.add_argument('--pos-noise-range-xz', required=False,  type=float, nargs=2, help="the scale/range of noise for x,z position values")
    parser.add_argument('--color-noise-range-rgb', required=False,  type=float, nargs=3, help="the scale/range of noise for r,g,b color values")
    parser.add_argument('--weather-noise-range', required=False,  type=float, nargs=5, help="the scale/range of noise for rain, fog, wetness, cloudiness and damage values")
    parser.add_argument('--time-max-noise', required=False,  type=float, nargs=1, help="the scale/range of noise for time value")
    parser.add_argument('--speed-max-noise', required=False,  type=float, nargs=1, help="the scale/range of noise for speed value")
    args = parser.parse_args()

    if args.seed:
        random.seed(args.seed[0])

    if args.steps:
        steps= args.steps[0]

    if args.pos_noise_range_xz:
        x_max_noise = args.pos_noise_range_xz[0]
        z_max_noise = args.pos_noise_range_xz[1]

    if args.color_noise_range_rgb:
        r_max_noise = args.color_noise_range_rgb[0]
        g_max_noise = args.color_noise_range_rgb[1]
        b_max_noise = args.color_noise_range_rgb[2]

    if args.weather_noise_range:
        rain_max_noise = args.weather_noise_range[0]
        fog_max_noise = args.weather_noise_range[1]
        wetness_max_noise = args.weather_noise_range[2]
        cloudiness_max_noise = args.weather_noise_range[3]
        damage_max_noise = args.weather_noise_range[4]

    if args.time_max_noise:
        time_max_noise = args.time_max_noise[0]

    if args.speed_max_noise:
        speed_max_noise = args.speed_max_noise[0]

    if args.des_forward_right:
        des_forward = args.des_forward_right[0]
        des_right = args.des_forward_right[1]

    simulation = Simulation(sim_host="127.0.0.1", sim_port=8181,
                            x_max_noise=x_max_noise, z_max_noise=z_max_noise,
                            r_max_noise=r_max_noise, g_max_noise=g_max_noise, b_max_noise=b_max_noise,
                            rain_max_noise=rain_max_noise, fog_max_noise=fog_max_noise,
                            wetness_max_noise=wetness_max_noise, cloudiness_max_noise=cloudiness_max_noise,
                            damage_max_noise=damage_max_noise,
                            time_max_noise=time_max_noise,
                            speed_max_noise=speed_max_noise,
                            json_file=args.input)

    restart_apollo()
    if args.action =='replay':
        if args.vector:
            nv = args.vector
        else:
            nv =[]
            for k in range(0, 1000):
                nv.append(0)
        e = simulation.execute(nv, des_forward=des_forward, des_right=des_right, steps=steps)
        logging.info("Evaluation {} ".format(e))
    elif args.action =='differential_evolution':
        differential_evolution(simulation, des_forward=des_forward, des_right=des_right, steps=steps)
    elif args.action =='powell':
        powell(simulation, des_forward=des_forward, des_right=des_right, steps=steps)
    elif args.action =='random':
        random_sim(simulation, des_forward=des_forward, des_right=des_right, steps=steps)
    elif args.action =='genetic_algorithm':
        genetic_algorithm(simulation, des_forward=des_forward, des_right=des_right, steps=steps)

    logging.info(simulation.report)

    f = open("report.json", "w")
    f.write(json.dumps(simulation.report))
    f.close()

    f = open("report.csv", "w")
    writer = csv.DictWriter(
        f, fieldnames=["execution_id", "journey_distance", "num_collisions", "total_distance_from_ego", "noise_vec"])
    writer.writeheader()

    for k in simulation.report:
        simulation.report[k]["execution_id"] = k
        writer.writerow(simulation.report[k])
    f.close()