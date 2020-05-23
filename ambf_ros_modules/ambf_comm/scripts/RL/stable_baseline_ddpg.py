#!/usr/bin/env python
# //==============================================================================
# /*
#     Software License Agreement (BSD License)
#     Copyright (c) 2019, AMBF
#     (www.aimlab.wpi.edu)

#     All rights reserved.

#     Redistribution and use in source and binary forms, with or without
#     modification, are permitted provided that the following conditions
#     are met:

#     * Redistributions of source code must retain the above copyright
#     notice, this list of conditions and the following disclaimer.

#     * Redistributions in binary form must reproduce the above
#     copyright notice, this list of conditions and the following
#     disclaimer in the documentation and/or other materials provided
#     with the distribution.

#     * Neither the name of authors nor the names of its contributors may
#     be used to endorse or promote products derived from this software
#     without specific prior written permission.

#     THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
#     "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
#     LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
#     FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
#     COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
#     INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
#     BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
#     LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
#     CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
#     LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
#     ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
#     POSSIBILITY OF SUCH DAMAGE.

#     \author    <http://www.aimlab.wpi.edu>
#     \author    <amunawar@wpi.edu>, <vvarier@wpi.edu>
#     \author    Adnan Munawar and Vignesh Manoj Varier
#     \version   0.1
# */
# //==============================================================================

from stable_baselines.ddpg.policies import MlpPolicy
import numpy as np
from stable_baselines import HER, DDPG
from stable_baselines.common.noise import NormalActionNoise, OrnsteinUhlenbeckActionNoise, AdaptiveParamNoiseSpec
from ambf_comm import AmbfEnv
import time
from stable_baselines.common.callbacks import CheckpointCallback


def main(env):
    # the noise objects for DDPG
    n_actions = env.action_space.shape[0]
    param_noise = None
    action_noise = OrnsteinUhlenbeckActionNoise(mean=np.zeros(n_actions), sigma=float(0.5) * np.ones(n_actions))

    model = DDPG(MlpPolicy, env, gamma=0.95, verbose=1, nb_train_steps=300, nb_rollout_steps=150,
                 param_noise=param_noise, batch_size=128, action_noise=action_noise, random_exploration=0.05,
                 normalize_observations=True, tensorboard_log="./ddpg_dvrk_tensorboard/", observation_range=(-1.5, 1.5),
                 critic_l2_reg=0.01)

    model.learn(total_timesteps=4000000, log_interval=100,
                callback=CheckpointCallback(save_freq=100000, save_path="./ddpg_dvrk_tensorboard/"))
    model.save("./ddpg_robot_env")

    # NOTE:
    # If continuing learning from previous checkpoint,
    # Comment above chunk of code {model=DDPG(''') till model.save("./her_robot_env")} and uncomment below lines:
    # Replace the XXXXX below with the largest number present in (rl_model_) directory ./ddpg_dvrk_tensorboard/
    # remaining_training_steps = 4000000 - XXXXX
    # model_log_dir = './ddpg_dvrk_tensorboard/rl_model_XXXXX_steps.zip'
    # model = DDPG.load(model_log_dir, env=env)
    # # Reset the model
    # env.reset()
    # model.learn(remaining_training_steps, log_interval=100,
    #             callback=CheckpointCallback(save_freq=100000, save_path="./ddpg_dvrk_tensorboard/"))
    # model.save("./ddpg_robot_env")


def load_model(eval_env):
    model = DDPG.load('./ddpg_robot_env', env=eval_env)
    count = 0
    step_num_arr = []
    for _ in range(20):
        number_steps = 0
        obs = eval_env.reset()
        for _ in range(400):
            action, _ = model.predict(obs)
            obs, reward, done, _ = eval_env.step(action)
            number_steps += 1
            if done:
                step_num_arr.append(number_steps)
                count += 1
                print("----------------It reached terminal state -------------------")
                break
    print("Robot reached the goal position successfully ", count, " times and the Average step count was ",
          np.average(np.array(step_num_arr)))

if __name__ == '__main__':

    ENV_NAME = 'psm/baselink'
    env_kwargs = {
        'action_space_limit': 0.05,
        'joints_to_control': np.array(['baselink-yawlink',
                                       'yawlink-pitchbacklink',
                                       'pitchendlink-maininsertionlink',
                                       'maininsertionlink-toolrolllink',
                                       'toolrolllink-toolpitchlink',
                                       'toolpitchlink-toolgripper1link',
                                       'toolpitchlink-toolgripper2link']),
        'goal_position_range': 0.05,
        'position_error_threshold': 0.01,
        'goal_error_margin': 0.0075,
        'joint_limits': {
                            'lower_limit': np.array([-0.2, -0.2, 0.1, -1.5, -1.5, -1.5, -1.5]),
                            'upper_limit': np.array([0.2, 0.2, 0.24, 1.5, 1.5, 1.5, 1.5])
                        },
        'workspace_limits': {
                                'lower_limit': np.array([-0.04, -0.03, -0.2]),
                                'upper_limit': np.array([0.03, 0.04, -0.091])
                            },
        'enable_step_throttling': False,
    }
    # Training
    ambf_env = AmbfEnv(**env_kwargs)
    time.sleep(5)
    ambf_env.make(ENV_NAME)
    ambf_env.reset()
    main(env=ambf_env)
    ambf_env.ambf_client.clean_up()
    # Evaluate learnt policy
    eval_env = AmbfEnv(**env_kwargs)
    time.sleep(5)
    eval_env.make(ENV_NAME)
    eval_env.reset()
    load_model(eval_env=eval_env)
    eval_env.ambf_client.clean_up()




