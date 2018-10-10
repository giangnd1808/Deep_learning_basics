#!/usr/bin/env python

from __future__ import division

import rospy
import math
import threading
import tf
import time
import matplotlib.pyplot as plt
import numpy as np

from geometry_msgs.msg import Twist,Pose2D
from nav_msgs.msg import Odometry
from std_msgs.msg import String
from sympy import Symbol, Derivative

class coord(object):
    def __init__(self):
        self._event = threading.Event()
        self.x = None
        self.y = None
        self.theta = None
        self.theta_c = None

    def __call__(self, msg):
        self.x = msg.pose.pose.position.x
        self.y = msg.pose.pose.position.y
        quaternion = (msg.pose.pose.orientation.x,msg.pose.pose.orientation.y,msg.pose.pose.orientation.z,msg.pose.pose.orientation.w)
        euler = tf.transformations.euler_from_quaternion(quaternion)
        roll = euler[0]
        pitch = euler[1]
        yaw = euler[2]
        self.theta = math.degrees(yaw)
        self.theta_c = self.theta
        if self.theta >= 0:
          self.theta = self.theta
        else:
          self.theta = 360 + self.theta          
        self._event.set()

    def get_msg(self, timeout=None):
        self._event.wait(timeout)
        return self.x,self.y,self.theta,self.theta_c

class speed(object):
    def __init__(self):
        self._event = threading.Event()
        self.vx = None
        self.wt = None

    def __call__(self, msg):
        self.vx = msg.twist.twist.linear.x
        self.wt = msg.twist.twist.angular.z
        self._event.set()

    def get_msg(self, timeout=None):
        self._event.wait(timeout)
        return self.vx,self.wt

def path_planning(t,mode):
    '''x = t/3
    y = t*t*t/(7*7*7)
    x_dot = 1/3
    y_dot = (3*t*t)/(7*7*7)'''

    '''x = 3*math.sin((t*math.pi)/8)
    y = -3 + 3*math.cos((t*math.pi)/8)
    x_dot = ((3*math.pi)/8)*math.cos((t*math.pi)/8)
    y_dot = ((-3*math.pi)/8)*math.sin((t*math.pi)/8)'''

    '''x = 0
    y = -t
    x_dot = 0
    y_dot = -1'''

    '''x = t
    y = 2*math.sin((t*math.pi)/8)
    x_dot = 1
    y_dot = (math.pi/4)*math.cos((t*math.pi)/8)'''

    x = -2 + 2*math.cos((t*math.pi)/10)
    y = 2*math.sin((t*math.pi)/5)
    x_dot = -((2*math.pi)/10)*math.sin((t*math.pi)/10)
    y_dot = ((2*math.pi)/5)*math.cos((t*math.pi)/5)

    r_t = math.sqrt(x*x+y*y)
    if r_t == 0:
        r_t = 0.000001
    #r_dot = abs(x*x_dot+y*y_dot)/(r_t)
    #r_dot = (2*math.pi*3)/16
    r_dot = math.sqrt(x_dot*x_dot+y_dot*y_dot)
    theta_t = math.degrees(math.atan2(y_dot,x_dot))

    if mode == "r_dot":
        return r_dot
    elif mode == "x_axis":
        return x
    elif mode == "y_axis":
        return y
    elif mode == "r_t":
        return r_t
    elif mode == "theta_t":
        return theta_t

def trajectory_gen():
    total_time = 20
    sampling_rate = 0.25
    x_t,y_t = [],[]
    r_t,r_dot = [],[]
    theta_t = []
    for i in range(int(total_time/sampling_rate)):
        x_t.append(path_planning(i*sampling_rate,"x_axis"))
        y_t.append(path_planning(i*sampling_rate,"y_axis"))
        r_t.append(path_planning(i*sampling_rate,"r_t"))
        r_dot.append(path_planning(i*sampling_rate,"r_dot"))
        theta_t.append(path_planning(i*sampling_rate,"theta_t"))
    return x_t,y_t,r_t,r_dot,theta_t,total_time,sampling_rate

def trajectory_track(r_dot,r_t,theta_t,r_act,theta_ch,r_old_er,theta_int_er,theta_old_er):
    Kp_ln, Kd_ln = 3,1
    r_er = r_t - r_act
    r_diff_er = r_er - r_old_er
    PID_ln = r_dot - 0.3*abs((Kp_ln*r_er + Kd_ln*r_diff_er)/(Kp_ln*4+Kd_ln*2))
    r_old_er = r_er

    Kp_ang, Kd_ang, Ki_ang = 5,0.8,0.3
    theta_er = math.radians(theta_t - theta_ch)
    if abs(theta_er) > math.pi:
        if theta_er > 0:
            theta_er = -math.radians(360 - abs(theta_t) - abs(theta_ch))
        else:
            theta_er = math.radians(360 - abs(theta_t) - abs(theta_ch))
    '''if abs(theta_er) < 0.1:
        theta_int_er = 0'''
    theta_diff_er = theta_er - theta_old_er
    theta_int_er = theta_er + theta_int_er
    PID_wt = ((Kp_ang*theta_er)/math.pi + (Kd_ang*theta_diff_er)/(0.5*math.pi) + (Ki_ang*theta_int_er)/(6*math.pi))
    print theta_er,theta_t,theta_ch
    theta_old_er = theta_er

    return PID_ln,r_old_er,PID_wt,theta_int_er,theta_old_er

def plotting(x_t,x_act,y_t,y_act,r_t,r_now,theta_t,theta_now,vx_act,r_dot):
    plt.figure(1)
    plt.subplot(211)
    plt.plot(x_t,'r')
    plt.plot(x_act,'g')
    plt.ylabel('X-axis')

    plt.subplot(212)
    plt.plot(y_t,'r')
    plt.plot(y_act,'g')
    plt.ylabel('Y-axis')

    plt.figure(2)
    plt.subplot(211)
    plt.plot(r_t,'r')
    plt.plot(r_now,'g')
    plt.ylabel('R-axis')

    plt.subplot(212)
    plt.plot(theta_t,'r')
    plt.plot(theta_now,'g')
    plt.ylabel('theta-axis')

    plt.figure(3)
    plt.subplot(211)
    plt.plot(vx_act,'g')
    plt.plot(r_dot,'r')
    plt.ylabel('R-vel')


    plt.show()

if __name__ == '__main__':

    rospy.init_node('mobile_base_nodelet_manager', anonymous=True)

    pub = rospy.Publisher('/mobile_base/commands/velocity',Twist,queue_size=1)
    twist = Twist()

    x_t,y_t,r_t,r_dot,theta_t,total_time,sampling_rate  = trajectory_gen()
    rate = rospy.Rate(1/sampling_rate)

    r_old_er,theta_int_er,theta_old_er,dev_int_er,dev_old_er,count = 0,0,0,0,0,0
    x_act,y_act = [],[]
    vx_act,vy_act = [],[]
    r_now,theta_now = [],[]

    pose = coord()
    rospy.Subscriber("/odom",Odometry,pose)
    x_r,y_r,theta_r,theta_ch = pose.get_msg()

    while not rospy.is_shutdown():
        while abs(theta_t[0] - theta_ch) > 1:
            pose = coord()
            rospy.Subscriber("/odom",Odometry,pose)
            x_r,y_r,theta_r,theta_ch = pose.get_msg()

            Kp_ang, Kd_ang, Ki_ang = 6,2,0
            theta_er = math.radians(theta_t[0] - theta_ch)
            if abs(theta_er) > math.pi:
                if theta_er > 0:
                    theta_er = -math.radians(360 - abs(theta_t[0]) - abs(theta_ch))
                else:
                    theta_er = math.radians(360 - abs(theta_t[0]) - abs(theta_ch))
            theta_diff_er = theta_er - theta_old_er
            PID_wt = ((Kp_ang*theta_er)/math.pi + (Kd_ang*theta_diff_er)/(0.5*math.pi))
            theta_old_er = theta_er

            twist.linear.x = 0
            twist.angular.z = PID_wt
            pub.publish(twist)
            rate.sleep()

        count,theta_old_er,PID_wt,theta_diff_er,theta_er = 0,0,0,0,0

        twist.linear.x = 0
        twist.angular.z = 0
        pub.publish(twist)
        rate.sleep()

        print 'oky',theta_t[0],theta_ch

        while(1):
            if count < int(total_time/sampling_rate):

                pose = coord()
                rospy.Subscriber("/odom",Odometry,pose)
                x_r,y_r,theta_r,theta_ch = pose.get_msg()

                r_act = math.sqrt(x_r*x_r+y_r*y_r)
                x_act.append(x_r)
                y_act.append(y_r)
                r_now.append(r_act)
                theta_now.append(theta_ch)
            
                vx,r_old_er,wt,theta_int_er,theta_old_er = trajectory_track(r_dot[count],r_t[count],theta_t[count],r_act,theta_ch,r_old_er,theta_int_er,theta_old_er)
                #print r_dot[count],vx,r_t[count],r_act,theta_t[count],theta_r
                vx_act.append(vx)

                twist.linear.x = vx
                twist.angular.z = wt
                pub.publish(twist)
                rate.sleep()
            else:
                print'hooray'
                plotting(x_t,x_act,y_t,y_act,r_t,r_now,theta_t,theta_now,vx_act,r_dot)
                break
            count = count+1
        break

        