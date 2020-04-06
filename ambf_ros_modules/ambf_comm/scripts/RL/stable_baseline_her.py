import os
import numpy as np
from stable_baselines import HER, DDPG
from stable_baselines.her import GoalSelectionStrategy, HERGoalEnvWrapper
from stable_baselines.common.noise import NormalActionNoise, OrnsteinUhlenbeckActionNoise, AdaptiveParamNoiseSpec
from ambf_comm import AmbfEnv
import time


def main(env):

    n_actions = env.action_space.shape[0]
    noise_std = 0.2
    action_noise = OrnsteinUhlenbeckActionNoise(mean=np.zeros(n_actions), sigma=noise_std * np.ones(n_actions))
    model_class = DDPG  # works also with SAC, DDPG and TD3

    kwargs = {
        'actor_lr': 1e-3,
        'critic_lr': 1e-3,
        'action_noise': action_noise,
        'nb_train_steps': 500,
        'nb_rollout_steps': 150,
        'nb_eval_steps': 500,
        'gamma': 0.95,
        'observation_range': (-3.05, 3.05),
        'random_exploration': 0.05,
        'tensorboard_log': "./ddpg_dvrk_tensorboard/"
    }

    # Available strategies (cf paper): future, final, episode, random
    model = HER('MlpPolicy', env, model_class, verbose=1, n_sampled_goal=4, goal_selection_strategy='future',
                buffer_size=int(1e6), batch_size=256, **kwargs)
    # model = HER('MlpPolicy', env, model_class, n_sampled_goal=4, goal_selection_strategy=goal_selection_strategy,
    #                                                 verbose=1, batch_size=64)
    env.reset()
    # Train the model
    model.learn(3000000, log_interval=10, tb_log_name="./ddpg_dvrk_tensorboard/")
    # model.save(os.path.join(logdir, "HERDDPG"))
    model.save("./her_robot_env")


def load_model(eval_env):

    # WARNING: you must pass an env
    # or wrap your environment with HERGoalEnvWrapper to use the predict method
    model = HER.load('./her_robot_env', env=eval_env)
    obs = eval_env.reset()
    for _ in range(1000):
        action, _ = model.predict(obs)
        obs, reward, done, _ = eval_env.step(action)
        if done:
            obs = eval_env.reset()


if __name__ == '__main__':

    ENV_NAME = 'psm/baselink'
    # Training
    env = AmbfEnv()
    time.sleep(5)
    env.make(ENV_NAME)
    env.reset()
    main(env=env)
    env.ambf_client.clean_up()
    # Evaluate learnt policy
    eval_env = AmbfEnv()
    time.sleep(5)
    eval_env.make(ENV_NAME)
    eval_env.reset()
    load_model(eval_env=eval_env)

