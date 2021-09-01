from scipy import optimize
import random

def powell(simulation, des_forward, des_right, steps):
    empty_vec = []
    for k in range(0, 1000):
        empty_vec.append(0)
    simulation.execute(empty_vec, des_forward=des_forward, des_right=des_right, steps=steps) # just to find the number_of_noise

    noise_vector = []
    bound_vector = []
    for k in range(0, simulation.number_of_noise + 1):
        noise_vector.append(0)
        bound_vector.append((-1, 1))
    result = optimize.minimize(simulation.execute, noise_vector, method="Powell", args=(des_forward, des_right, steps), bounds=bound_vector)
    print(result)


def random_sim(simulation, des_forward, des_right, steps):
    empty_vec = []
    for k in range(0, 1000):
        empty_vec.append(0)
    simulation.execute(empty_vec, des_forward=des_forward, des_right=des_right, steps=steps) # just to find the number_of_noise

    best_result = 1000
    best_vec = []
    for j in range(0,212):
        noise_vector = []
        bound_vector = []
        for k in range(0, simulation.number_of_noise + 1):
            noise_vector.append(random.uniform(-1, 1))
            bound_vector.append((-1, 1))
        result = simulation.execute(noise_vector, des_forward=des_forward, des_right=des_right, steps=steps)
        if result < best_result :
            best_result = result
            best_vec = noise_vector
    print(best_result, best_vec)
