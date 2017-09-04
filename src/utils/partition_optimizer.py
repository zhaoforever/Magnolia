
import numpy as np
import pandas as pd


class PartitionOptimizer:
    class EnsurePopulation:
        def __init__(self, num_splits=2):
            self._num_splits = num_splits
        def __call__(self, **kwargs):
            return (np.unique(kwargs['x_new']).size == self._num_splits)

    class UnitStep:
        def __init__(self, random_state, stepsize=1, num_splits=2):
            self.stepsize = stepsize
            self._num_splits = num_splits
            self._rng = random_state
        def __call__(self, x):
            # self.stepsize = np.max([1, self.stepsize])
            return np.clip(x + self._rng.randint(-self.stepsize, self.stepsize + 1, size=x.size), 0, self._num_splits - 1)

    def __init__(self, category_populations, desired_fractions, random_state, logger):
        self._rng = random_state
        self._logger = logger
        self._category_populations = category_populations
        self._total_population = category_populations.sum()
        self._desired_fractions = desired_fractions
        self._actual_fractions = np.zeros_like(desired_fractions)
        self._number_of_splits = len(desired_fractions)
        self._accept_test = self.EnsurePopulation(num_splits=self._number_of_splits)
        self._initial_vector = self._create_initial_vector()

    def _create_initial_vector(self):
        vec = self._rng.randint(0, self._number_of_splits, size=self._category_populations.size)
        while not self._accept_test(x_new=vec):
            vec = self._rng.randint(0, self._number_of_splits, size=self._category_populations.size)
        return vec

    def _calculate_population_fractions(self, x):
        for i in range(self._number_of_splits):
            selected_category_populations = self._category_populations[x == i]
            self._actual_fractions[i] = selected_category_populations.sum()/self._total_population

    def _loss_function(self, x):
        self._calculate_population_fractions(x)
        return (np.abs(self._actual_fractions - self._desired_fractions)/self._desired_fractions).sum()

    def optimize(self, stepsize=1, **kwargs):
        take_step = self.UnitStep(self._rng, stepsize=stepsize, num_splits=self._number_of_splits)

        global_minimum_vec = self._initial_vector
        global_minimum_eval = self._loss_function(global_minimum_vec)
        global_minimum_streak = 0
        current_vec = global_minimum_vec
        current_eval = global_minimum_eval
        early_stopped = False

        for i in range(kwargs['niter']):
            current_vec = take_step(current_vec)
            while not self._accept_test(x_new=current_vec):
                current_vec = take_step(current_vec)
            current_eval = self._loss_function(current_vec)

            if current_eval < global_minimum_eval:
                global_minimum_eval = current_eval
                global_minimum_vec = current_vec
                global_minimum_streak = 0
            global_minimum_streak += 1

            if global_minimum_streak > kwargs['niter_success']:
                early_stopped = True
                self._logger.debug('Optimizer stopping early at {}'.format(i))
                break

        if not early_stopped:
            self._logger.debug('Optimizer finished all iterations ({})'.format(kwargs['niter']))

        self._calculate_population_fractions(global_minimum_vec)
        return global_minimum_vec, self._actual_fractions
