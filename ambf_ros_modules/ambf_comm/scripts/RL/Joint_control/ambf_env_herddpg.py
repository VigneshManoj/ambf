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
#     \author    <amunawar@wpi.edu>
#     \author    Adnan Munawar
#     \version   0.1
# */
# //==============================================================================
from ambf_client import Client
from gym import spaces
import numpy as np
import copy
import time
import gym
from gym.utils import seeding
from ambf_world import World
from ambf_object import Object
from numpy import linalg as LA
# from psmIK import compute_IK, test_ik
from psmFK import compute_FK
# from PyKDL import Vector, Rotation, Frame, dot
from transformations import euler_from_matrix


class Observation:
    def __init__(self):
        self.state = {
            'observation': np.zeros(14),
            'achieved_goal': np.zeros(6),
            'desired_goal': np.zeros(6)
        }
        self.dist = 0
        self.reward = 0.0
        self.prev_reward = 0.0
        self.cur_reward = 0.0
        self.is_done = False
        self.info = {}
        self.sim_step_no = 0

    def cur_observation(self):
        return self.state, self.reward, self.is_done, self.info


class AmbfEnv(gym.GoalEnv):
    def __init__(self):
        super(AmbfEnv, self).__init__()
        self.obj_handle = Object
        self.world_handle = World
        self.ambf_client = Client()
        self.ambf_client.connect()
        time.sleep(5)
        self.ambf_client.create_objs_from_rostopics()
        self.seed()
        self.n_skip_steps = 5
        self.enable_step_throttling = False
        self.action = []
        self.obs = Observation()
        self.initial_pos = copy.deepcopy(self.obs.cur_observation()[0])
        # self.previous_cartesian_pos = np.zeros((1, 3))
        # self.previous_joint_pos = np.array([0., 0., 0.1, 0., 0., 0., 0.])
        self.cmd_joint_pos = np.zeros(7)

        # Action Limit values: Z-> +-0.5 || X, Y-> +-0.05
        # State limit values: Z-> -0.04 || X, Y -> +-0.1
        self.n_actions = 3
        self.action_lims_low = np.array([-0.05, -0.05, -0.05])
        self.action_lims_high = np.array([0.05, 0.05, 0.05])
        self.action_space = spaces.Box(low=-1, high=1, shape=(self.n_actions,), dtype="float32")
        self.observation_space = spaces.Dict(dict(
            desired_goal=spaces.Box(-np.inf, np.inf, shape=self.initial_pos['achieved_goal'].shape, dtype='float32'),
            achieved_goal=spaces.Box(-np.inf, np.inf, shape=self.initial_pos['achieved_goal'].shape, dtype='float32'),
            observation=spaces.Box(-np.inf, np.inf, shape=self.initial_pos['observation'].shape, dtype='float32'),
        ))
        # self.observation_space = spaces.Box(-100, 100, shape=(13,))
        # self.states_lims_low = np.array([-1.605, -0.93556, -0.002444, -3.0456, -3.0414, -3.0481, -3.0498])
        # self.states_lims_high = np.array([1.5994, 0.94249, 0.24001, 3.0485, 3.0528, 3.0376, 3.0399])
        # self.observation_space = spaces.Box(self.states_lims_low, self.states_lims_high, shape=(13,),dtype=np.float32)
        self.joints_to_control = np.array(['baselink-yawlink', 'yawlink-pitchbacklink',
                                           'pitchendlink-maininsertionlink', 'maininsertionlink-toolrolllink',
                                           'toolrolllink-toolpitchlink', 'toolpitchlink-toolgripper1link',
                                           'toolpitchlink-toolgripper2link'])
        #
        # self.goal_state = [0.0, 0.0, -0.15, -1.57, 0, -3.138]
        self.target_range = 0.05
        self.goal = self._sample_goal()
        # self.goal = np.around(self.np_random.uniform(-0.15, 0.15, size=6), decimals=4)
        self.prev_sim_step = 0
        self.error_threshold = 0.01
        self.count_for_print = 0

    def skip_sim_steps(self, num):
        self.n_skip_steps = num
        self.world_handle.set_num_step_skips(num)

    def set_throttling_enable(self, check):
        self.enable_step_throttling = check
        self.world_handle.enable_throttling(check)

    def make(self, a_name):
        self.obj_handle = self.ambf_client.get_obj_handle(a_name)
        # self.base_handle = self.ambf_client.get_obj_handle('SampleObj')
        self.world_handle = self.ambf_client.get_world_handle()
        self.world_handle.enable_throttling(self.enable_step_throttling)
        self.world_handle.set_num_step_skips(self.n_skip_steps)
        time.sleep(5)
        if self.obj_handle is None or self.world_handle is None:
            raise Exception

    def seed(self, seed=None):
        self.np_random, seed = seeding.np_random(seed)
        return [seed]

    def reset(self):
        # Function to reset the model
        # action = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        # observation, _, _, _ = self.step(action)
        # Sets the initial position of PSM
        self.set_initial_pos_func()
        # Updates the observation to the initialized position
        observation = self.read_joint_pos_func()
        # Samples a goal
        self.goal = self._sample_goal()
        return observation
        # return self.initial_pos

    def set_initial_pos_func(self):
        for joint_idx, jt_name in enumerate(self.joints_to_control):
            if joint_idx == 2:
                self.obj_handle.set_joint_pos(jt_name, 0.1)
            else:
                self.obj_handle.set_joint_pos(jt_name, 0)
        time.sleep(0.5)

    def read_joint_pos_func(self):
        joint_pos = np.zeros(7)
        initial_state_vel = np.zeros(7)
        for joint_idx, jt_name in enumerate(self.joints_to_control):
            joint_pos[joint_idx] = self.obj_handle.get_joint_pos(jt_name)
            initial_state_vel[joint_idx] = self.obj_handle.get_joint_vel(jt_name)

        updated_state, _, _, _ = self._update_observation(joint_pos, initial_state_vel)
        return updated_state

    def step(self, action):
        assert len(action) == 3
        # Counter for printing position, action and reward
        self.count_for_print += 1
        # Initialization of variables
        current_joint_pos = np.zeros(7)
        new_state_joint_pos = np.zeros(7)
        state_vel = np.zeros(7)
        # Reading current joint positions of PSM as current state
        # for joint_idx, jt_name in enumerate(self.joints_to_control):
        #     current_joint_pos[joint_idx] = self.obj_handle.get_joint_pos(jt_name)
        # print("type of actions ", type(action))
        # Scaling the action from (-1, 1) to (-0.1, 0.1)
        action = [0.05 * x for x in action]
        action = np.clip(action, self.action_lims_low, self.action_lims_high)
        # check_boundary_flag, action_limit = check_boundary_condition(current_joint_pos)
        # # Clipping action between the action limits
        # if check_boundary_flag == 1:
        #     action = np.clip(action_limit, self.action_lims_high)
        # elif check_boundary_flag == 2:
        #     action = np.clip(action, self.action_lims_low, action_limit)
        # else:
        #     action = np.clip(action, self.action_lims_low, self.action_lims_high)
        # Take the action from current state to reach the new state
        for joint_idx, jt_name in enumerate(self.joints_to_control):
            current_joint_pos[joint_idx] = self.obj_handle.get_joint_pos(jt_name)
            state_vel[joint_idx] = self.obj_handle.get_joint_vel(jt_name)
            if joint_idx < 3:
                new_state_joint_pos[joint_idx] = np.add(current_joint_pos[joint_idx], action[joint_idx])
        # print("diff", current_joint_pos-self.previous_joint_pos)
        # Ensure the new state is within valid joint positions, if invalid then stay at the joint limit position
        desired_joint_pos = self.limit_joint_pos(new_state_joint_pos)
        # Counter to avoid getting stuck in while loop because of very small errors in positions
        count_for_joint_pos = 0
        # Ensures that PSM joints reach the desired joint positions
        while True:
            reached_joint_pos = np.zeros(7)
            for joint_idx, jt_name in enumerate(self.joints_to_control):
                self.obj_handle.set_joint_pos(jt_name, desired_joint_pos[joint_idx])
                reached_joint_pos[joint_idx] = self.obj_handle.get_joint_pos(jt_name)

            error_in_pos = np.around(np.subtract(desired_joint_pos, reached_joint_pos), decimals=3)
            # print("error ", error_in_pos)
            count_for_joint_pos += 1
            # if np.all(np.abs(error_in_pos) <= self.error_threshold):
            if np.all(np.abs(error_in_pos) <= self.error_threshold) or count_for_joint_pos > 25:
                break

        # Update state, reward, done flag and world values in the code
        updated_state, rewards, done, info = self._update_observation(desired_joint_pos, state_vel)
        self.world_handle.update()
        # fk_tip = compute_FK(desired_joint_pos)
        # xyz_cartesian_pos = fk_tip[0:3, 3].reshape((1, 3))
        # self.previous_cartesian_pos = xyz_cartesian_pos
        if self.count_for_print % 10000 == 0:
            print("count ", self.count_for_print, "Action is ", action, " new pos after action ",
                  updated_state)
            print("Reward is ", rewards)

        # self.previous_joint_pos = desired_joint_pos

        return updated_state, rewards, done, info

    def invalid_cartesian_pos(self, cart_pos):
        # State limit values: Z-> -0.04 || X, Y -> +-0.1
        # print("joint pos ", joint_pos)
        check_cart_val = np.all((-0.2 <= cart_pos[0, 0] <= 0.2) and (-0.17 <= cart_pos[0, 1] <= 0.13)
                                and (-0.02 < cart_pos[0, 2] < -0.005))
        # print("check val is ", check_val)
        if check_cart_val:
            return False
        else:
            return True

    def limit_joint_pos(self, joint_pos):
        # self.states_lims_low = np.array([-1.605, -0.93556, -0.002444, -3.0456, -3.0414, -3.0481, -3.0498])
        # self.states_lims_high = np.array([1.5994, 0.94249, 0.24001, 3.0485, 3.0528, 3.0376, 3.0399])
        # Note: Joint 5 and 6, joint pos = 0, 0 is closed jaw and 0.5, 0.5 is open
        limit_joint_values = np.zeros(len(joint_pos))
        joint_lower_limit = np.array([-0.5, -0.4, 0.1, -1.5, -1.5, -1.5, -1.5])
        joint_upper_limit = np.array([0.5, 0.4, 0.24, 1.5, 1.5, 1.5, 1.5])
        for joint_idx in range(len(joint_pos)):
            limit_joint_values[joint_idx] = np.clip(joint_pos[joint_idx], joint_lower_limit[joint_idx],
                                                    joint_upper_limit[joint_idx])

        return limit_joint_values

    # def check_boundary_condition(self, joint_pos)
    #     if joint_pos == -1.45

    def render(self, mode):
        print(' I am {} Ironman'.format(mode))

    def _update_observation(self, state, state_vel):
        if self.enable_step_throttling:
            step_jump = 0
            while step_jump < self.n_skip_steps:
                step_jump = self.obj_handle.get_sim_step() - self.prev_sim_step
                time.sleep(0.00001)
            self.prev_sim_step = self.obj_handle.get_sim_step()
            if step_jump > self.n_skip_steps:
                print('WARN: Jumped {} steps, Default skip limit {} Steps'.format(step_jump, self.n_skip_steps))
        else:
            cur_sim_step = self.obj_handle.get_sim_step()
            step_jump = cur_sim_step - self.prev_sim_step
            self.prev_sim_step = cur_sim_step

        # Find the tip position and rotation by computing forward kinematics (not being used currently)
        fk_tip = compute_FK(state)
        cartesian_pos = fk_tip[0:3, 3]
        achieved_rot = np.array(euler_from_matrix(fk_tip[0:3, 0:3], axes='szyx')).reshape((3, 1))
        # Combine tip position and rotation to a single numpy array as achieved goal
        achieved_goal = np.asarray(np.concatenate((cartesian_pos.copy(), achieved_rot.copy()), axis=0)).reshape(-1)
        # Verify function to compute velocity (currently using Nathaniel's implementation)
        # state_vel = np.random.uniform(0.0, 0.75, (1, 7))
        # print("state vel is ", state_vel)
        # Combine the current state positions and velocity into a single array as observation
        observation = np.concatenate((state, state_vel), axis=None)
        # Update the observation dictionary
        self.obs.state.update(observation=observation.copy(), achieved_goal=achieved_goal.copy(),
                              desired_goal=self.goal.copy())
        # Update info
        self.obs.info = self._update_info()
        # Compute the reward
        self.obs.reward = self.compute_reward(self.obs.state['achieved_goal'], self.goal, self.obs.info)
        self.obs.is_done = self._check_if_done()

        # Return the values to step function
        return self.obs.state, self.obs.reward, self.obs.is_done, self.obs.info

    def compute_reward(self, achieved_goal, goal, info):
        # prev_dist = self.obs.dist
        # reward = (prev_dist - cur_dist) - 4 * action_penalty
        # Find the distance between goal and achieved goal
        cur_dist = LA.norm(np.subtract(goal[0:3], achieved_goal[0:3]))

        # action_penalty = np.sum(np.square(action))
        # done = False
        # Continuous reward
        # reward = round(1 - float(abs(cur_dist)/0.3)*0.5, 5)
        # Sparse reward
        if abs(cur_dist) < 0.01:
            reward = 1
            # done = True
            # self.reset()
        else:
            reward = -1
        # reward = -(prev_dist - cur_dist)
        # print("Cur dist ", cur_dist)
        self.obs.dist = cur_dist
        return reward

    def _sample_goal(self):
        # Samples new goal positions and ensures its within the workspace of PSM
        # observation = self.read_joint_pos_func()
        # rand_val_pos = np.around(np.add(observation['achieved_goal'][0:3],
        #                                 self.np_random.uniform(-self.target_range, self.target_range, size=3)),
        #                          decimals=4)
        # Cartesian limits [-0.1388084, 0.1318971] [-0.1318971, 0.1388084] [-0.1935, -0.04766373]
        # for joint limits (-0.8, 0.8), (-0.8, 0.8), (0.1, 0.24)
        rand_val_pos = self.np_random.uniform(-0.1, 0.1, size=3)
        rand_val_pos[0] = np.around(np.clip(rand_val_pos[0], -0.1, 0.09), decimals=4)
        rand_val_pos[1] = np.around(np.clip(rand_val_pos[1], -0.08, 0.08), decimals=4)
        rand_val_pos[2] = np.around(np.clip(rand_val_pos[2], -0.20, -0.08), decimals=4)
        rand_val_angle = self.np_random.uniform(-1.5, 1.5, size=3)
        # rand_val_angle[0] = np.clip(rand_val_angle[0], -0.15, 0.15)
        # rand_val_angle[1] = np.clip(rand_val_angle[1], -0.15, 0.15)
        # rand_val_angle[2] = np.clip(rand_val_angle[2], -0.15, 0.15)
        goal = np.concatenate((rand_val_pos, rand_val_angle), axis=None)
        return goal.copy()

    def _check_if_done(self):
        if abs(self.obs.dist) < 0.01:
            return True
        else:
            return False

    def _update_info(self):
        info = {
            # 'is_success': self._is_success(observation['achieved_goal'], observation['desired_goal']),
            'is_success': self._is_success(),
            }
        return info

    def _is_success(self):
        if abs(self.obs.dist) < 0.01:
            return True
        else:
            return False

    """
    Original Invalid pos
        def invalid_joint_pos(self, joint_pos):
        # self.states_lims_low = np.array([-1.605, -0.93556, -0.002444, -3.0456, -3.0414, -3.0481, -3.0498])
        # self.states_lims_high = np.array([1.5994, 0.94249, 0.24001, 3.0485, 3.0528, 3.0376, 3.0399])
        # Note: Joint 5 and 6, joint pos = 0, 0 is closed jaw and 0.5, 0.5 is open
        check_joint_val = np.all((-1.45 <= joint_pos[0] <= 1.45) and (-0.93556 <= joint_pos[1] <= 0.94249)
                                 and (0.075 <= joint_pos[2] <= 0.24001) and (-3.0456 <= joint_pos[3] <= 3.0485)
                                 and (-3.0414 <= joint_pos[4] <= 3.0528) and (-3.0481 <= joint_pos[5] <= 3.0376)
                                 and (-3.0498 <= joint_pos[5] <= 3.0399))
        # print("check val is ", check_val)
        if check_joint_val:
            return False
        else:
            return True

        def invalid_joint_pos(self, joint_pos):
        # self.states_lims_low = np.array([-1.605, -0.93556, -0.002444, -3.0456, -3.0414, -3.0481, -3.0498])
        # self.states_lims_high = np.array([1.5994, 0.94249, 0.24001, 3.0485, 3.0528, 3.0376, 3.0399])
        # Note: Joint 5 and 6, joint pos = 0, 0 is closed jaw and 0.5, 0.5 is open
        check_joint_val = np.all((-1.0 <= joint_pos[0] <= 1.0) and (-0.8 <= joint_pos[1] <= 0.8)
                                 and (0.1 <= joint_pos[2] <= 0.24001) and (-3.0456 <= joint_pos[3] <= 3.0485)
                                 and (-3.0414 <= joint_pos[4] <= 3.0528) and (-3.0481 <= joint_pos[5] <= 3.0376)
                                 and (-3.0498 <= joint_pos[5] <= 3.0399))
        # print("check val is ", check_val)
        if check_joint_val:
            return False
        else:
            return True
    """