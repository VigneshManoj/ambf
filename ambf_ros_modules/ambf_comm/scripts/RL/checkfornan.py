import gym
from gym import spaces
import numpy as np
import time
from stable_baselines.ddpg.policies import MlpPolicy
from ambf_comm import AmbfEnv
from stable_baselines import DDPG
from stable_baselines.common.vec_env import DummyVecEnv, VecCheckNan
from stable_baselines.common.noise import NormalActionNoise, OrnsteinUhlenbeckActionNoise, AdaptiveParamNoiseSpec

ENV_NAME = 'psm/baselink'

# Get the environment and extract the number of actions.
env = AmbfEnv()
time.sleep(10)

env.make(ENV_NAME)
time.sleep(10)

env.reset()
i = 0
# the noise objects for DDPG
# print("actions space ", np.abs(env.action_space.low), np.abs(env.action_space.high))
n_actions = env.action_space.shape[0]
param_noise = None
action_noise = OrnsteinUhlenbeckActionNoise(mean=np.zeros(n_actions), sigma=float(0.5) * np.ones(n_actions))

# Create environment
# env = DummyVecEnv([lambda:AmbfEnv()])
env = DummyVecEnv([lambda: env])
env = VecCheckNan(env, raise_exception=True)

# Instantiate the agent
model = DDPG(MlpPolicy, env)

# Train the agent
model.learn(total_timesteps=int(2e5))  # this will crash explaining that the invalid value originated from the environment.