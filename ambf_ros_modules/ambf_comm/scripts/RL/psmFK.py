import numpy as np
from utilities import *

# THIS IS THE FK FOR THE PSM MOUNTED WITH THE LARGE NEEDLE DRIVER TOOL. THIS IS THE
# SAME KINEMATIC CONFIGURATION FOUND IN THE DVRK MANUAL. NOTE, JUST LIKE A FAULT IN THE
# MTM's DH PARAMETERS IN THE MANUAL, THERE IS A FAULT IN THE PSM's DH AS WELL. BASED ON
# THE FRAME ATTACHMENT IN THE DVRK MANUAL THE CORRECT DH CAN FOUND IN THIS FILE

# ALSO, NOTICE THAT AT HOME CONFIGURATION THE TIP OF THE PSM HAS THE FOLLOWING
# ROTATION OFFSET W.R.T THE BASE. THIS IS IMPORTANT FOR IK PURPOSES.
# R_7_0 = [ 0,  1,  0 ]
#       = [ 1,  0,  0 ]
#       = [ 0,  0, -1 ]
# Basically, x_7 is along y_0, y_7 is along x_0 and z_7 is along -z_0.

# You need to provide a list of joint positions. If the list is less that the number of joint
# i.e. the robot has 6 joints, but only provide 3 joints. The FK till the 3+1 link will be provided
def compute_FK(joint_pos):
    j = [0, 0, 0, 0, 0, 0, 0]
    for i in range(len(joint_pos)):
        j[i] = joint_pos[i]

    # The last frame is fixed

    # PSM DH Params
    link1 = DH(alpha=PI_2, a=0, theta=j[0], d=0, offset=PI_2)
    link2 = DH(alpha=-PI_2, a=0, theta=j[1], d=0, offset=-PI_2)
    link3 = DH(alpha=PI_2, a=0, theta=0, d=j[2], offset=-0.4318, type='P')
    link4 = DH(alpha=0, a=0, theta=j[3], d=0.4162, offset=0)
    link5 = DH(alpha=-PI_2, a=0, theta=j[4], d=0, offset=-PI_2)
    link6 = DH(alpha=-PI_2, a=0.0091, theta=j[5], d=0, offset=-PI_2)
    link7 = DH(alpha=-PI_2, a=0, theta=0, d=0.0102, offset=PI_2)

    T_1_0 = link1.get_trans()
    T_2_1 = link2.get_trans()
    T_3_2 = link3.get_trans()
    T_4_3 = link4.get_trans()
    T_5_4 = link5.get_trans()
    T_6_5 = link6.get_trans()
    T_7_6 = link7.get_trans()

    T_2_0 = np.matmul(T_1_0, T_2_1)
    T_3_0 = np.matmul(T_2_0, T_3_2)
    T_4_0 = np.matmul(T_3_0, T_4_3)
    T_5_0 = np.matmul(T_4_0, T_5_4)
    T_6_0 = np.matmul(T_5_0, T_6_5)
    T_7_0 = np.matmul(T_6_0, T_7_6)

    # print("RETURNING FK FOR LINK ", len(joint_pos))

    if len(joint_pos) == 1:
        return T_1_0

    elif len(joint_pos) == 2:
        return T_2_0

    elif len(joint_pos) == 3:
        return T_3_0

    elif len(joint_pos) == 4:
        return T_4_0

    elif len(joint_pos) == 5:
        return T_5_0

    elif len(joint_pos) == 6:
        return T_6_0

    elif len(joint_pos) == 7:
        return T_7_0


class DH:
    def __init__(self, alpha, a, theta, d, offset, type='R'):
        self.alpha = alpha
        self.a = a
        self.theta = theta
        self.d = d
        self.offset = offset
        self.type = type

    def mat_from_dh(self, alpha, a, theta, d, offset, type):
        ca = np.cos(alpha)
        sa = np.sin(alpha)
        if type == 'R':
            theta = theta + offset
        elif type == 'P':
            d = d + offset
        else:
            assert type == 'P' and type == 'R'

        ct = np.cos(theta)
        st = np.sin(theta)
        mat = np.mat([
            [ct     , -st     ,  0 ,  a],
            [st * ca,  ct * ca, -sa, -d * sa],
            [st * sa,  ct * sa,  ca,  d * ca],
            [0      ,  0      ,  0 ,  1]
        ])
        return mat

    def get_trans(self):
        return self.mat_from_dh(self.alpha, self.a, self.theta, self.d, self.offset, self.type)


T_7_0 = compute_FK([-0.5, 0, 0.2, 0, 0, 0])
#
# print T_7_0
# print "\n AFTER ROUNDING \n"
# print(round_mat(T_7_0, 4, 4, 3))

if __name__ == "__main__":
    max_x = 0.
    max_y = 0.
    max_z = -2.
    min_x = 0.
    min_y = 0.
    min_z = 0.
    while True:
        for joint_1 in np.arange(-0.4, 0.4, 0.025):
            for joint_2 in np.arange(-0.3, 0.3, 0.025):
                for joint_3 in np.arange(0.075, 0.24, 0.025):
                    T_7_0 = compute_FK([joint_1, joint_2, joint_3, 0, 0, 0])

                    if T_7_0[0:3, 3][0] > max_x:
                        max_x = T_7_0[0:3, 3][0]
                    elif T_7_0[0:3, 3][1] > max_y:
                        max_y = T_7_0[0:3, 3][1]
                    elif T_7_0[0:3, 3][2] > max_z:
                        max_z = T_7_0[0:3, 3][2]
                    if T_7_0[0:3, 3][0] < min_x:
                        min_x = T_7_0[0:3, 3][0]
                    elif T_7_0[0:3, 3][1] < min_y:
                        min_y = T_7_0[0:3, 3][1]
                    elif T_7_0[0:3, 3][2] < min_z:
                        min_z = T_7_0[0:3, 3][2]
                    else:
                        pass
                    # print(T_7_0[0:3, 3])
        print("Max and min vals are ", max_x, max_y, max_z, min_x, min_y, min_z)

        # T_7_0 = compute_FK([-0.5, 0, 0.2, 0, 0, 0])
        # print(T_7_0[0:3, 3])


