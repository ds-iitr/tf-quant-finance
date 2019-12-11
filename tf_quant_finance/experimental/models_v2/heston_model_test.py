# Copyright 2019 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Lint as: python2, python3
"""Tests for Heston Model."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import numpy as np
import tensorflow as tf

import tf_quant_finance as tff
from tf_quant_finance.experimental.models_v2 import heston_model
from tensorflow.python.framework import test_util  # pylint: disable=g-direct-tensorflow-import


@test_util.run_all_in_graph_and_eager_modes
class HestonModelTest(tf.test.TestCase):

  def test_volatility(self):
    """Tests volatility stays close to its mean for small vol of vol."""
    theta = 0.05
    process = heston_model.HestonModel(
        kappa=1.0, theta=theta, epsilon=0.00001,
        rho=-0.0, dtype=np.float64)
    years = 1.0
    times = np.linspace(0.0, years, 365 * years)
    num_samples = 2
    paths = process.sample_paths(
        times,
        time_step=0.01,
        num_samples=num_samples,
        initial_state=np.array([np.log(100), 0.045]),
        seed=None)
    # For small values of espsilon, volatility should stay close to theta
    volatility_trace = self.evaluate(paths)[..., 1]
    max_deviation = np.max(abs(volatility_trace[:, 50:] - theta))
    self.assertAlmostEqual(
        max_deviation, 0.0, places=2)

  def test_state(self):
    """Tests state behaves like GBM for small vol of vol."""
    theta = 1.0
    process = heston_model.HestonModel(
        kappa=1.0, theta=theta, epsilon=0.00001,
        rho=-0.0, dtype=np.float64)
    times = [0.0, 0.5, 1.0]
    num_samples = 1000
    start_value = 100
    paths = process.sample_paths(
        times,
        time_step=0.001,
        num_samples=num_samples,
        initial_state=np.array([np.log(start_value), 1.0]),
        seed=None)
    # For small values of espsilon, state should behave like Geometric
    # Brownian Motion with volatility `theta`.
    state_trace = self.evaluate(paths)[..., 0]
    # Starting point should be the same
    np.testing.assert_allclose(state_trace[:, 0], np.log(100), 1e-8)
    for i in (1, 2):
      # Mean and varianve of the approximating Geometric Brownian Motions
      gbm_mean = start_value
      gbm_std = start_value * np.sqrt((np.exp(times[i]) - 1))
      np.testing.assert_allclose(np.mean(np.exp(state_trace[:, i])),
                                 gbm_mean, 1.0)
      np.testing.assert_allclose(np.std(np.exp(state_trace[:, 1])),
                                 gbm_std, 2.0)

  def test_piecewise_and_dtype(self):
    """Tests that piecewise constant coefficients can be handled."""
    for dtype in (np.float32, np.float64):
      kappa = tff.math.piecewise.PiecewiseConstantFunc(
          jump_locations=[0.5], values=[1, 1.1], dtype=dtype)
      theta = tff.math.piecewise.PiecewiseConstantFunc(
          jump_locations=[0.5], values=[1, 0.9], dtype=dtype)
      epsilon = tff.math.piecewise.PiecewiseConstantFunc(
          jump_locations=[0.3], values=[0.1, 0.2], dtype=dtype)
      rho = tff.math.piecewise.PiecewiseConstantFunc(
          jump_locations=[0.5], values=[0.4, 0.6], dtype=dtype)
      process = heston_model.HestonModel(
          kappa=kappa, theta=theta, epsilon=epsilon,
          rho=rho, dtype=dtype)
      times = [0.1, 1.0]
      num_samples = 100
      initial_state = np.array([np.log(100), 0.045], dtype=dtype)
      paths = process.sample_paths(
          times,
          time_step=0.1,
          num_samples=num_samples,
          initial_state=initial_state,
          seed=None)
      paths = self.evaluate(paths)
      state_trace, volatility_trace = paths[..., 0], paths[..., 0]
      self.assertEqual(volatility_trace.dtype, dtype)
      self.assertEqual(state_trace.dtype, dtype)
      # Check drift and volatility calcuation
      self.assertAllClose(
          process.drift_fn()(times[0], initial_state),
          np.array([-0.0225, 0.955]))
      self.assertAllClose(
          process.volatility_fn()(times[0], initial_state),
          np.array([[0.21213203, 0.],
                    [0.00848528, 0.01944222]]))


if __name__ == '__main__':
  tf.test.main()
