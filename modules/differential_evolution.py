from scipy import optimize

def differential_evolution(simulation, des_forward, des_right, steps):
    empty_vec = []
    for k in range(0, 1000):
        empty_vec.append(0)
    simulation.execute(empty_vec, des_forward=des_forward, des_right=des_right, steps=steps) # just to find the number_of_noise

    noise_vector = []
    bound_vector = []
    for k in range(0, simulation.number_of_noise + 1):
        noise_vector.append(0)
        bound_vector.append((-1, 1))
    result = optimize.differential_evolution(simulation.execute, bounds=bound_vector, args=(des_forward, des_right, steps), strategy='best1bin',
                                             maxiter=1000, popsize=15, tol=0.01, mutation=(0.5, 1), recombination=0.7,
                                             seed=None, callback=None, disp=False, polish=True, init='latinhypercube',
                                             atol=0, updating='immediate', workers=1, constraints=())
    print(result)

