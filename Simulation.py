import lgsvl
import json
import logging
import math
import random
import sys, traceback
import time
import docker

EGO_VEHICLE_ID = "8d60a6ac-65a4-4bc5-8fc5-870156b6608f" # HARDCODED value for Lincoln2017MKZ
MIN_DIST = 2
# Scaling formula : outX  = (( inX  - InRangeMin) / (InRangeMax - InRangeMin)) * (OutRangeMax - OutRangeMin) + OutRangeMin
def rescaled_noise(input=0, InRangeMin= -1, InRangeMax= +1, OutRangeMin=-1, OutRangeMax= +1):
    return  ((input - InRangeMin) / (InRangeMax - InRangeMin)) * (OutRangeMax - OutRangeMin) + OutRangeMin

def restart_apollo():
    env = [
        "PATH=/apollo/bazel-bin/modules/tools/visualizer:/apollo/bazel-bin/cyber/tools/cyber_launch:/apollo/bazel-bin/cyber/tools/cyber_service:/apollo/bazel-bin/cyber/tools/cyber_node:/apollo/bazel-bin/cyber/tools/cyber_channel:/apollo/bazel-bin/cyber/tools/cyber_monitor:/apollo/bazel-bin/cyber/tools/cyber_recorder:/apollo/bazel-bin/cyber/mainboard:/usr/local/cuda/bin:/opt/apollo/sysroot/bin:/usr/local/nvidia/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/apollo/scripts:/usr/local/qt5/bin"]
    client = docker.from_env()
    docklst = client.containers.list()
    logging.info(docklst)
    container = client.containers.get(docklst[0].name)
    logging.info(container)
    logging.info( container.exec_run("bootstrap_lgsvl.sh stop", environment=env))
    logging.info(container.exec_run("bootstrap_lgsvl.sh", environment=env))
    logging.info(container.exec_run("bridge.sh", environment=env, detach=True))
    time.sleep(4)


def connect_svl(sim_host, sim_port):
    time.sleep(0.1)
    try:
        s = lgsvl.Simulator(sim_host, sim_port)
        time.sleep(0.2)
        return s
    except:
        input("ERROR2 \n\n\n\nSVL connection problem: Fix the issue and press enter to continue")
        return connect_svl(sim_host, sim_port)

def rand_id(size=6, chars='ABCDEFGHIJKLMNOPQRSTUVWXYZ'):
    return ''.join(random.choice(chars) for _ in range(size))

class Simulation:
    def __init__(self, sim_host ="127.0.0.1" , sim_port=8181,
                 x_max_noise=-1, z_max_noise=-1,
                 r_max_noise=-1, g_max_noise=-1, b_max_noise=-1,
                 rain_max_noise=-1, fog_max_noise=-1, wetness_max_noise=-1, cloudiness_max_noise=-1, damage_max_noise=-1,
                 time_max_noise=-1,
                 speed_max_noise=-1,
                 json_file=''
                 ):
        self.exec_counter = 0
        self.sim_host = sim_host
        self.sim_port = sim_port
        self.sim = connect_svl(self.sim_host, self.sim_port)
        self.x_max_noise = x_max_noise
        self.z_max_noise = z_max_noise
        self.r_max_noise = r_max_noise
        self.g_max_noise = g_max_noise
        self.b_max_noise = b_max_noise
        self.rain_max_noise= rain_max_noise
        self.fog_max_noise = fog_max_noise
        self.wetness_max_noise = wetness_max_noise
        self.cloudiness_max_noise = cloudiness_max_noise
        self.damage_max_noise = damage_max_noise
        self.time_max_noise = time_max_noise
        self.speed_max_noise = speed_max_noise
        self.json_file = json_file
        self.report = {}
        self.crash_flag = 0
        self.modules = [
            'Localization',
            # 'Perception',
            'Transform',
            'Routing',
            'Prediction',
            'Planning',
            # 'Traffic Light',
            'Control'
        ]

    def reset_sim(self):
        self.data = json.load(open(self.json_file))
        self.data_prime = json.load(open(self.json_file))
        self.map_name = self.data['map']['name']
        if self.sim.current_scene == self.map_name:
            self.sim.reset()
        else:
            self.sim.load(self.map_name)

        self.agents = {}
        self.init_ego_state = lgsvl.AgentState()
        ego_indx = -1
        self.number_of_noise = -1
        self.num_collisions = 0
        self.total_distance_from_ego = 0

        if not self.data.get('environment'):
            self.data['environment'] = dict()
            self.data['environment'] = {
                    'rain': 0,
                    'fog':  0,
                    'wetness':  0,
                    'cloudiness':  0,
                    'damage': 0,
                    'time':12,
                }
            self.data_prime['environment'] = dict()
            self.data_prime['environment'] = {
                    'rain': 0,
                    'fog':  0,
                    'wetness':  0,
                    'cloudiness':  0,
                    'damage': 0,
                    'time':12,
                }

    def on_collision(self, agent1, agent2, contact):
        self.num_collisions = self.num_collisions + 1
        name1 = "STATIC OBSTACLE" if agent1 is None else agent1.name
        name2 = "STATIC OBSTACLE" if agent2 is None else agent2.name
        logging.info("{} collided with {} at {}".format(name1, name2, contact))

    def npc_euclidean_distance(self, npc1, npc2):
        return math.sqrt((npc1.x - npc2.x) ** 2 + (npc1.y - npc2.y) ** 2 + (npc1.z - npc2.z) ** 2)

    def evaluate_step(self):
        for i in self.agents:
            self.total_distance_from_ego = self.total_distance_from_ego - self.npc_euclidean_distance(self.agents[self.ego_indx].state.transform.position, self.agents[i].state.transform.position)

    def evaluate_journey(self):
        logging.info("evaluate_journey")
        self.journey_distance = self.npc_euclidean_distance(self.init_ego_state.transform.position, self.agents[self.ego_indx].transform.position)
        if self.journey_distance < MIN_DIST :
            # E0713 09:45:16.218106  1146 client.cc:99] [cyber_bridge]Client write failed, disconnectingsystem:9
            logging.info("journey_distance < MIN_DIST")
            raise Exception('MIN_DIST', 'journey_distance < MIN_DIST')
        else:
            return (-1)* self.journey_distance +  (- 500) * self.num_collisions +  self.total_distance_from_ego

    def NV(self, i):
        return self.noise_vector[i]

    def save_json(self, path):
        with open(path, 'w') as outfile:
            json.dump(self.data_prime, outfile)

    def initiate_simulator(self):
        # logging.info("data_prime {}".format(self.data_prime))
        for indx in range(0, len(self.data_prime['agents'])):
            logging.info("Agent index {}".format(indx))
            agent_variant =  self.data_prime['agents'][indx]['variant']
            agent_type =  self.data_prime['agents'][indx]['type']
            switcher = {
                3: lgsvl.AgentType.PEDESTRIAN,
                1: lgsvl.AgentType.EGO,
                2: lgsvl.AgentType.NPC,
            }
            logging.info("agent_type: {}".format(agent_type))
            agent_type_lgsvl = switcher.get(agent_type, None)

            if agent_type_lgsvl == lgsvl.AgentType.EGO:
                agent_pos_x =  self.data_prime['agents'][indx]['transform']['position']['x']
                agent_pos_z =  self.data_prime['agents'][indx]['transform']['position']['z']
                agent_pos_y =  self.data_prime['agents'][indx]['transform']['position']['y']
            else:
                agent_pos_x =  self.data_prime['agents'][indx]['transform']['position']['x']
                agent_pos_z =  self.data_prime['agents'][indx]['transform']['position']['z']
                agent_pos_y =  self.data_prime['agents'][indx]['transform']['position']['y']

            agent_rot_x =  self.data_prime['agents'][indx]['transform']['rotation']['x']
            agent_rot_y =  self.data_prime['agents'][indx]['transform']['rotation']['y']
            agent_rot_z =  self.data_prime['agents'][indx]['transform']['rotation']['z']

            try:
                agent_color_r =  self.data_prime['agents'][indx]['color']['r']
                agent_color_g =  self.data_prime['agents'][indx]['color']['g']
                agent_color_b =  self.data_prime['agents'][indx]['color']['b']
            except:
                agent_color_r = None
                agent_color_g = None
                agent_color_b = None

            agent_state = lgsvl.AgentState()
            agent_state.transform.position = lgsvl.Vector(agent_pos_x, agent_pos_y, agent_pos_z)
            agent_state.transform.rotation = lgsvl.Vector(agent_rot_x, agent_rot_y, agent_rot_z)
            agent_state.transform.color = lgsvl.Vector(agent_color_r, agent_color_g, agent_color_b)

            if agent_type_lgsvl == lgsvl.AgentType.EGO:
                ## Dirty hack to to use my own modular testing configuration
                ego_pos_x = agent_pos_x
                ego_pos_y = agent_pos_y
                ego_pos_z = agent_pos_z
                logging.info("ego_pos_x:{} ego_pos_z:{}".format(ego_pos_x, ego_pos_z))
                self.init_ego_state.transform.position = lgsvl.Vector(ego_pos_x, ego_pos_y, ego_pos_z)
                self.init_ego_state.transform.rotation = lgsvl.Vector(agent_rot_x, agent_rot_y, agent_rot_z)
                ego_indx = indx
                self.agents[ego_indx] = self.sim.add_agent(EGO_VEHICLE_ID, lgsvl.AgentType.EGO, self.init_ego_state )
            else:
                self.agents[indx] = self.sim.add_agent(agent_variant, agent_type_lgsvl, agent_state)

            agent_waypoints =  self.data_prime['agents'][indx].get('waypoints')
            if agent_waypoints:
                waypoints = []
                for wp_indx in range(1, len(agent_waypoints)):
                    logging.info("Way point index {}".format(wp_indx))

                    wp_pos_x = agent_waypoints[wp_indx]['position']['x']
                    wp_pos_y = agent_waypoints[wp_indx]['position']['y']
                    wp_pos_z = agent_waypoints[wp_indx]['position']['z']
                    wp_angle_x = agent_waypoints[wp_indx]['angle']['x']
                    wp_angle_y = agent_waypoints[wp_indx]['angle']['y']
                    wp_angle_z = agent_waypoints[wp_indx]['angle']['z']
                    wp_waittime = agent_waypoints[wp_indx]['waitTime']
                    wp_speed = agent_waypoints[wp_indx]['speed']
                    waypoints.append(lgsvl.DriveWaypoint(lgsvl.Vector(wp_pos_x, wp_pos_y, wp_pos_z), wp_speed, 0, 
                                                         lgsvl.Vector(wp_angle_x, wp_angle_y, wp_angle_z), 0, False,
                                                         0), )
                if len(waypoints) > 0:
                    self.agents[indx].follow(waypoints, loop=False)

        self.sim.weather = lgsvl.WeatherState(
            rain=self.data_prime['environment']['rain']
            , fog=self.data_prime['environment']['fog']
            , wetness=self.data_prime['environment']['wetness']
            , cloudiness=self.data_prime['environment']['cloudiness']
            , damage=self.data_prime['environment']['damage']
            )
        self.sim.set_time_of_day(self.data_prime['environment']['time'])

    def initiate_apollo(self, des_forward, des_right, bridge_host, bridge_port, dv_host, dv_vehicle, apollo_map):

        self.agents[self.ego_indx].on_collision(self.on_collision)
        self.agents[self.ego_indx].connect_bridge(bridge_host, bridge_port)
        self.dv = lgsvl.dreamview.Connection(self.sim, self.agents[self.ego_indx], dv_host)
        # self.dv.disable_module(self, 'Control')
        time.sleep(0.1)
        self.dv.disable_apollo()
        self.dv.set_hd_map(apollo_map)
        self.dv.set_vehicle(dv_vehicle)
        forward = lgsvl.utils.transform_to_forward(self.init_ego_state.transform)
        right = lgsvl.utils.transform_to_right(self.init_ego_state.transform)
        self.destination = self.init_ego_state.position + des_forward * forward + des_right * right

    def execute(self, noise_vec, des_forward, des_right, steps):
        self.exec_counter = self.exec_counter + 1
        logging.info("exec counter {}".format(self.exec_counter))
        time.sleep(7) ## ffmpeg is still working
        try:
            self.reset_sim()
            self.apply_noise(noise_vec)
            time.sleep(0.1)
            self.initiate_simulator()
            time.sleep(0.1)
            self.initiate_apollo(des_forward = des_forward, des_right= des_right, bridge_host= "127.0.0.1" , bridge_port = 9090, dv_host= "127.0.0.1", dv_vehicle= 'Lincoln2017MKZ_LGSVL', apollo_map= 'borregas_ave' )
            time.sleep(0.1)
            self.run(steps)
            time.sleep(0.1)
            res = self.evaluate_journey()

        # recovery routine
        except KeyError:
            self.crash_flag = self.crash_flag + 1
            self.sim.close()
            self.sim = connect_svl(self.sim_host, self.sim_port)
            logging.debug("UNRECOVERABLE EXCEPTION : Key errors")
            return 1000
        except Exception as e:
            self.crash_flag = self.crash_flag + 1
            logging.debug("RECOVERABLE EXCEPTION {} ".format(e))
            logging.debug("-" * 60)
            traceback.print_exc(file=sys.stdout)
            logging.debug("-" * 60)
            self.sim.close()
            if self.crash_flag > 2:
                input("ERROR1 \n\n\n\nRestart SVL/Apollo bridge and press enter to continue")
            restart_apollo()
            time.sleep(2)
            self.dv.reconnect()
            self.sim = connect_svl(self.sim_host, self.sim_port)
            time.sleep(2)
            return self.execute( noise_vec, des_forward, des_right, steps)

        filename = "results/" + str(res) + '_'  + str(self.journey_distance) + '_' + str(self.num_collisions)  + '_' + str(self.total_distance_from_ego) +  '_' + rand_id() + '.json'
        self.save_json(filename)
        logging.info("json stored in : {}".format(filename))

        self.report[self.exec_counter] = {"journey_distance": self.journey_distance, "num_collisions" :self.num_collisions, "total_distance_from_ego" : self.total_distance_from_ego, "noise_vec" : str(noise_vec)}
        self.crash_flag = 0

        return res


    def run(self, steps):
        #self.dv.enable_module(self, 'Control')
        self.dv.enable_apollo(dest_x=self.destination.x, dest_z=self.destination.z, modules=self.modules)
        logging.info("Apollo enabled")
        for s in range(1, steps):
            logging.info("Step: {}".format(s))
            self.sim.run(time_limit=1, time_scale=1)
            self.evaluate_step()

    def apply_noise(self, noise_vector):
        self.noise_vector = noise_vector
        i = 0
        logging.info("Noise Vector: {}".format(noise_vector))

        for indx in range(0,len(self.data['agents'])):
            logging.info("Agent index {}".format(indx))
            switcher = {
                3: lgsvl.AgentType.PEDESTRIAN,
                1: lgsvl.AgentType.EGO,
                2: lgsvl.AgentType.NPC,
            }
            logging.info("agent_type: {}".format(self.data['agents'][indx]['type']))
            agent_type_lgsvl = switcher.get(self.data['agents'][indx]['type'], None)
            if agent_type_lgsvl != lgsvl.AgentType.EGO:
                i += 1
                self.data_prime['agents'][indx]['transform']['position']['x'] = self.data['agents'][indx]['transform']['position']['x'] + rescaled_noise(input= self.NV(i), InRangeMin=-1, InRangeMax=+1, OutRangeMin =-1 * self.x_max_noise, OutRangeMax= 1 * self.x_max_noise)
                i += 1
                self.data_prime['agents'][indx]['transform']['position']['z'] = self.data['agents'][indx]['transform']['position']['z'] + rescaled_noise(input= self.NV(i), InRangeMin=-1, InRangeMax=+1, OutRangeMin= -1 * self.z_max_noise, OutRangeMax= 1 * self.z_max_noise)
                try:
                    i += 1
                    self.data_prime['agents'][indx]['color']['r'] = (self.data['agents'][indx]['color']['r'] + rescaled_noise(input =self.NV(i), InRangeMin=-1, InRangeMax=+1, OutRangeMin= -1 * self.r_max_noise, OutRangeMax= 1 * self.r_max_noise)) % 256
                    i += 1
                    self.data_prime['agents'][indx]['color']['r'] = (self.data['agents'][indx]['color']['g'] + rescaled_noise(input= self.NV(i), InRangeMin=-1, InRangeMax=+1, OutRangeMin= -1 * self.g_max_noise, OutRangeMax= 1 * self.g_max_noise)) % 256
                    i += 1
                    self.data_prime['agents'][indx]['color']['r'] = (self.data['agents'][indx]['color']['b'] + rescaled_noise(input= self.NV(i), InRangeMin=-1, InRangeMax=+1, OutRangeMin= -1 * self.b_max_noise, OutRangeMax= 1 * self.b_max_noise)) % 256
                except:
                    pass
            else:
                self.ego_indx = indx

            agent_waypoints = self.data['agents'][indx].get('waypoints')
            if agent_waypoints:
                waypoints = []
                for wp_indx in range(1, len(agent_waypoints)):
                    logging.info("Way point index {}".format(wp_indx))
                    i +=1
                    self.data_prime['agents'][indx]['waypoints'][wp_indx]['position']['x'] = self.data['agents'][indx]['waypoints'][wp_indx]['position']['x'] + rescaled_noise(input= self.NV(i), InRangeMin=-1, InRangeMax=+1, OutRangeMin =-1 * self.x_max_noise, OutRangeMax= 1 * self.x_max_noise)
                    i +=1
                    self.data_prime['agents'][indx]['waypoints'][wp_indx]['position']['z'] = self.data['agents'][indx]['waypoints'][wp_indx]['position']['z']  = agent_waypoints[wp_indx]['position']['z'] + rescaled_noise(input= self.NV(i), InRangeMin=-1, InRangeMax=+1, OutRangeMin= -1 * self.z_max_noise, OutRangeMax= 1 * self.z_max_noise)
                    i += 1
                    self.data_prime['agents'][indx]['waypoints'][wp_indx]['speed'] = self.data['agents'][indx]['waypoints'][wp_indx]['speed'] + rescaled_noise(input= self.NV(i), InRangeMin=-1, InRangeMax=+1, OutRangeMin= -1 * self.speed_max_noise, OutRangeMax= 1 * self.speed_max_noise)

            self.data_prime['environment'] = {
                    'rain': self.data['environment']['rain'] + rescaled_noise(input=self.NV(i + 1), InRangeMin=-1, InRangeMax=+1, OutRangeMin=-1 * self.rain_max_noise, OutRangeMax=1 * self.rain_max_noise) % 1,
                    'fog': self.data['environment']['fog'] + rescaled_noise(input=self.NV(i + 2), InRangeMin=-1, InRangeMax=+1, OutRangeMin=-1 * self.fog_max_noise, OutRangeMax=1 * self.fog_max_noise) % 1,
                    'wetness': self.data['environment']['wetness']+ rescaled_noise(input=self.NV(i + 3), InRangeMin=-1, InRangeMax=+1, OutRangeMin=-1 * self.wetness_max_noise, OutRangeMax=1 * self.wetness_max_noise) % 1,
                    'cloudiness': self.data['environment']['cloudiness']+ rescaled_noise(input=self.NV(i + 4), InRangeMin=-1, InRangeMax=+1,OutRangeMin=-1 * self.cloudiness_max_noise, OutRangeMax=1 * self.cloudiness_max_noise) % 1,
                    'damage': self.data['environment']['damage']+ rescaled_noise(input=self.NV(i + 5), InRangeMin=-1, InRangeMax=+1, OutRangeMin=-1 * self.damage_max_noise, OutRangeMax=1 * self.damage_max_noise) % 1,
                    'time': self.data['environment']['time'] + rescaled_noise(input=self.NV(i+6), InRangeMin=-1, InRangeMax=+1, OutRangeMin=-1 * self.time_max_noise, OutRangeMax=1 * self.time_max_noise) % 24
            }
            i += 6
        self.number_of_noise = i
        return i
