from pybulletgym.envs.scene_abstract import SingleRobotEmptyScene
from gym_mujoco_xml_env import PybulletMujocoXmlEnv
import gym, gym.spaces, gym.utils, gym.utils.seeding
import numpy as np
import os, sys

class PybulletInvertedPendulum(PybulletMujocoXmlEnv):
	swingup = False
	force_gain = 12 # TODO: Try to find out why we need to scale the force

	def __init__(self):
		PybulletMujocoXmlEnv.__init__(self, 'inverted_pendulum.xml', 'cart', action_dim=1, obs_dim=5)

	def create_single_player_scene(self):
		return SingleRobotEmptyScene(gravity=9.8, timestep=0.0165, frame_skip=1)

	def robot_specific_reset(self):
		self.pole = self.parts["pole"]
		self.slider = self.jdict["slider"]
		self.j1 = self.jdict["hinge"]
		u = self.np_random.uniform(low=-.1, high=.1)
		self.j1.reset_current_position( u if not self.swingup else 3.1415+u , 0)
		self.j1.set_motor_torque(0)

	def apply_action(self, a):
		#assert( np.isfinite(a).all() )
		if not np.isfinite(a).all():
			print("a is inf")
			a[0] = 0
		self.slider.set_motor_torque( self.force_gain * 100*float(np.clip(a[0], -1, +1)) )

	def calc_state(self):
		self.theta, theta_dot = self.j1.current_position()
		x, vx = self.slider.current_position()
		#assert( np.isfinite(x) )

		if not np.isfinite(x):
			print("x is inf")
			x = 0

		if not np.isfinite(vx):
			print("vx is inf")
			vx = 0

		if not np.isfinite(self.theta):
			print("theta is inf")
			self.theta = 0

		if not np.isfinite(theta_dot):
			print("theta_dot is inf")
			theta_dot = 0

		return np.array([
			x, vx,
			np.cos(self.theta), np.sin(self.theta), theta_dot
			])

	def _step(self, a):
		self.apply_action(a)
		self.scene.global_step()
		state = self.calc_state()  # sets self.pos_x self.pos_y
		vel_penalty = 0
		if self.swingup:
			reward = np.cos(self.theta)
			done = False
		else:
			reward = 1.0
			done = np.abs(self.theta) > .2
		self.rewards = [float(reward)]
		self.HUD(state, a, done)
		return state, sum(self.rewards), done, {}

	def camera_adjust(self):
		self.camera.move_and_look_at(0,1.2,1.0, 0,0,0.5)

class PybulletInvertedPendulumSwingup(PybulletInvertedPendulum):
	swingup = True
	force_gain = 2.2  # TODO: Try to find out why we need to scale the force

class PybulletInvertedDoublePendulum(PybulletMujocoXmlEnv):
	def __init__(self):
		PybulletMujocoXmlEnv.__init__(self, 'inverted_double_pendulum.xml', 'cart', action_dim=1, obs_dim=9)

	def create_single_player_scene(self):
		return SingleRobotEmptyScene(gravity=9.8, timestep=0.0165, frame_skip=1)

	def robot_specific_reset(self):
		self.pole2 = self.parts["pole2"]
		self.slider = self.jdict["slider"]
		self.j1 = self.jdict["hinge"]
		self.j2 = self.jdict["hinge2"]
		u = self.np_random.uniform(low=-.1, high=.1, size=[2])
		self.j1.reset_current_position(float(u[0]), 0)
		self.j2.reset_current_position(float(u[1]), 0)
		self.j1.set_motor_torque(0)
		self.j2.set_motor_torque(0)

	def apply_action(self, a):
		assert( np.isfinite(a).all() )
		force_gain = 0.78  # TODO: Try to find out why we need to scale the force
		self.slider.set_motor_torque( force_gain *200*float(np.clip(a[0], -1, +1)) )

	def calc_state(self):
		theta, theta_dot = self.j1.current_position()
		gamma, gamma_dot = self.j2.current_position()
		x, vx = self.slider.current_position()
		self.pos_x, _, self.pos_y = self.pole2.pose().xyz()
		assert( np.isfinite(x) )
		return np.array([
			x, vx,
			self.pos_x,
			np.cos(theta), np.sin(theta), theta_dot,
			np.cos(gamma), np.sin(gamma), gamma_dot,
			])

	def _step(self, a):
		self.apply_action(a)
		self.scene.global_step()
		state = self.calc_state()  # sets self.pos_x self.pos_y
		# upright position: 0.6 (one pole) + 0.6 (second pole) * 0.5 (middle of second pole) = 0.9
		# using <site> tag in original xml, upright position is 0.6 + 0.6 = 1.2, difference +0.3
		dist_penalty = 0.01 * self.pos_x ** 2 + (self.pos_y + 0.3 - 2) ** 2
		# v1, v2 = self.model.data.qvel[1:3]   TODO when this fixed https://github.com/bulletphysics/bullet3/issues/1040
		#vel_penalty = 1e-3 * v1**2 + 5e-3 * v2**2
		vel_penalty = 0
		alive_bonus = 10
		done = self.pos_y + 0.3 <= 1
		self.rewards = [float(alive_bonus), float(-dist_penalty), float(-vel_penalty)]
		self.HUD(state, a, done)
		return state, sum(self.rewards), done, {}

	def camera_adjust(self):
		self.camera.move_and_look_at(0,1.2,1.2, 0,0,0.5)
