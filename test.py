import gym
import gym_flappy_bird
from stable_baselines.common.vec_env import DummyVecEnv

env = gym.make('flappy-bird-v0')
env = DummyVecEnv([lambda: env])
env.reset()

