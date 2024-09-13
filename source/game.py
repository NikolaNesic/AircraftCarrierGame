try:
	import framework32 as framework
except:
	import framework64 as framework

import math

# -------------------------------------------------------
#	game parameters
# -------------------------------------------------------

class Params(object):
	class Ship(object):
		LINEAR_SPEED = 0.5
		ANGULAR_SPEED = 0.5

	class Aircraft(object):
		LINEAR_SPEED = 2.0
		ANGULAR_SPEED = 2.5
		FLIGHT_TIME = 7.0
		REFUEL_TIME = 2.0


# -------------------------------------------------------
#	Basic Vector2 class
# -------------------------------------------------------

class Vector2(object):

	def __init__(self, *args):
		if not args:
			self.x = self.y = 0.0
		elif len(args) == 1:
			self.x, self.y = args[0].x, args[0].y
		else:
			self.x, self.y = args

	def __add__(self, other):
		return Vector2(self.x + other.x, self.y + other.y)

	def __sub__(self, other):
		return Vector2(self.x - other.x, self.y - other.y)

	def __mul__(self, coef):
		return Vector2(self.x * coef, self.y * coef)


# -------------------------------------------------------
#	Simple ship logic
# -------------------------------------------------------

class Plane(object):
	def __init__(self):
		self._model = None
		self._position = None
		self._angle = 0.0
		self._speed = 0.0
		self._speed_multiplier = 0.0
		self._launch_time = 0.0
		self._airborne = False
		self._refuel_timer = 0.0
		self._landing_target_reached = False
		self._deck_reached = False
		self._started_landing = 0.0

	def deinit(self):
		assert self._model
		framework.destroyModel(self._model)
		self._model = None
		self._position = None
		self._angle = 0.0
		self._speed = 0.0
		self._speed_multiplier = 0.0
		self._launch_time = 0.0
		self._airborne = False
		self._refuel_timer = 0.0
		self._landing_target_reached = False
		self._deck_reached = False
		self._started_landing = 0.0

class Ship(object):

	def __init__(self):
		self._model = None
		self._position = None
		self._angle = 0.0
		self._input = None
		self._num_of_planes = 5
		self._current_target = [False, None]
		self._planes = [ Plane(), Plane(), Plane(), Plane(), Plane()]
		self._last_plane_launched = 0.0
		self._landing_deck_available = True
		self._deck_cooldown = 0.5
		self._current_time = 2.0 # if lower there is a bit of delay at the start of the game
		self._last_plane_landed = float('inf')
		self._max_landing_time = 9.0

	def init(self):
		assert not self._model
		self._model = framework.createShipModel()
		self._position = Vector2()
		self._angle = 0.0
		self._input = {
			framework.Keys.FORWARD: False,
			framework.Keys.BACKWARD: False,
			framework.Keys.LEFT: False,
			framework.Keys.RIGHT: False
		}
		framework.placeGoalModel(10, 0)

	def deinit(self):
		assert self._model
		framework.destroyModel(self._model)
		self._model = None
		for i in self._planes:
			if i._model != None:
				i.deinit()
		self._position = None
		self._angle = 0.0
		self._input = None
		self._num_of_planes = 5
		self._current_target = [False, None]
		framework.placeGoalModel(10, 0)
		self._last_plane_launched = 0.0
		self._landing_deck_available = True
		self._deck_cooldown = 0.5
		self._current_time = 2.0
		self._last_plane_landed = float('inf')
		self._max_landing_time = 9.0

	def update(self, dt):
		linearSpeed = 0.0
		angularSpeed = 0.0

		if self._input[framework.Keys.FORWARD]:
			linearSpeed = Params.Ship.LINEAR_SPEED
		elif self._input[framework.Keys.BACKWARD]:
			linearSpeed = -Params.Ship.LINEAR_SPEED

		if linearSpeed != 0.0:
			if self._input[framework.Keys.LEFT]:
				angularSpeed = math.copysign(Params.Ship.ANGULAR_SPEED, linearSpeed)
			elif self._input[framework.Keys.RIGHT]:
				angularSpeed = -math.copysign(Params.Ship.ANGULAR_SPEED, linearSpeed)

		self._angle = self._angle + angularSpeed * dt
		self._position = self._position + Vector2(math.cos(self._angle), math.sin(self._angle)) * linearSpeed * dt
		framework.placeModel(self._model, self._position.x, self._position.y, self._angle)
		# planes update
		self._current_time += dt
		for current_plane in self._planes:
			if current_plane._airborne:
				if self._current_time - current_plane._launch_time < Params.Aircraft.FLIGHT_TIME: # check if flight time has elapsed
					if current_plane._speed < Params.Aircraft.LINEAR_SPEED:
						# start taking off
						direction_to_ship, distance_from_ship = self.calculate_direction_and_distance(self._position, current_plane._position)
						if distance_from_ship < 0.7 and current_plane._speed < Params.Aircraft.LINEAR_SPEED: # distance i gauged as the flight deck
							current_plane._speed_multiplier = 0.01 + 2*distance_from_ship / 0.7
							current_plane._speed = Params.Aircraft.LINEAR_SPEED * current_plane._speed_multiplier
							self.update_plane_position(current_plane, dt, angle_diff=0, taking_off=True, linearSpeed=linearSpeed)
							if current_plane._speed > Params.Aircraft.LINEAR_SPEED:
								current_plane._speed = Params.Aircraft.LINEAR_SPEED # to ensure last tick doesn't go over top speed
					else:
						# max speed reached now go to the target
						circle_distance = 0.75
						direction_to_target, distance_from_target = self.calculate_direction_and_distance(self._current_target[1], current_plane._position)
						if distance_from_target > circle_distance:
							angle_diff = self.calculate_angle_difference(direction_to_target, distance_from_target, current_plane._angle)
							self.update_plane_position(current_plane, dt, angle_diff, going_to_target=True, circle_distance=circle_distance, distance_from_target=distance_from_target)
						else:
						# start actual circling
							angle_diff = self.calculate_angle_difference(direction_to_target, distance_from_target, current_plane._angle, circle=True)
							self.update_plane_position(current_plane, dt, angle_diff)
				else:
					# flight time expired go back to the ship. i added 3 approach points at the back, fourth one is the beggining of the flight deck
					landing_approach_left = Vector2(self._position.x - math.cos(self._angle - math.pi/10)*2.5, self._position.y - math.sin(self._angle - math.pi/10)*2.5)
					landing_approach_right = Vector2(self._position.x - math.cos(self._angle + math.pi/10)*2.5, self._position.y - math.sin(self._angle + math.pi/10)*2.5)
					landing_approach_center = Vector2(self._position.x - math.cos(self._angle)*2.5, self._position.y - math.sin(self._angle)*2.5)
					landing_deck_start = Vector2(self._position.x - math.cos(self._angle)*0.6, self._position.y - math.sin(self._angle)*0.6)

					direction_to_left, distance_from_left = self.calculate_direction_and_distance(landing_approach_left, current_plane._position)
					direction_to_right, distance_from_right = self.calculate_direction_and_distance(landing_approach_right, current_plane._position)
					direction_to_center, distance_from_center = self.calculate_direction_and_distance(landing_approach_center, current_plane._position)
					direction_to_landing_deck, distance_from_landing_deck = self.calculate_direction_and_distance(landing_deck_start, current_plane._position)

					# choose an approach point based on the plane position
					distance_from_approach = min(distance_from_left, distance_from_right, distance_from_center)
					if distance_from_approach == distance_from_left:
						landing_target = landing_approach_left
						direction_to_approach = direction_to_left
					elif distance_from_approach == distance_from_right:
						landing_target = landing_approach_right
						direction_to_approach = direction_to_right	
					else:
						landing_target = landing_approach_center
						direction_to_approach = direction_to_center

					# go towards the chosen approach point
					if distance_from_approach > 0 and not current_plane._landing_target_reached and not current_plane._deck_reached:
						if current_plane._speed < Params.Aircraft.LINEAR_SPEED: # speed up again if landing was canceled
							current_plane._speed += 0.05
						angle_diff = self.calculate_angle_difference(direction_to_approach, distance_from_approach, current_plane._angle)
						self.update_plane_position(current_plane, dt, angle_diff)
					# plane is going towards landing deck only after it is considered ready to be landed on
					if self.destination_reached(current_plane._position, landing_target) and self._landing_deck_available:
						self._landing_deck_available = False
						current_plane._landing_target_reached = True
						current_plane._started_landing = self._current_time
					# go towards the beggining of the flight deck
					if current_plane._landing_target_reached and not current_plane._deck_reached:
						if self._current_time - current_plane._started_landing > self._max_landing_time: # if landing lasts more go back and free up a landing_deck
							self.cancel_landing(current_plane)
						else:
							angle_diff = self.calculate_angle_difference(direction_to_landing_deck, distance_from_landing_deck, current_plane._angle)
							self.update_plane_position(current_plane, dt, angle_diff)
							if current_plane._speed > 0.6*Params.Aircraft.LINEAR_SPEED: # first slowdown after passing an approach point
								current_plane._speed -= 0.05
							else:
								current_plane._speed = 0.6*Params.Aircraft.LINEAR_SPEED
					if self.destination_reached(current_plane._position, landing_deck_start):
						current_plane._deck_reached = True
					# start landing
					if current_plane._deck_reached:
						if self._current_time - current_plane._started_landing > self._max_landing_time: # if landing lasts more go back and free up a landing_deck
							self.cancel_landing(current_plane)
						else:
							direction_to_ship, distance_from_ship = self.calculate_direction_and_distance(self._position, current_plane._position)
							# added a bit of prediction when landing based on theoretical materials formulae: position = position + velocity * distanceBetweenTargetAndPursuer / MAX_VELOCITY
							direction_to_ship_predicted, distance_from_ship_predicted = self.calculate_direction_and_distance(self._position + Vector2(math.cos(self._angle), math.sin(self._angle)) * linearSpeed * dt * distance_from_ship.__mul__(1/Params.Ship.LINEAR_SPEED), current_plane._position)
							angle_diff = self.calculate_angle_difference(direction_to_ship_predicted, distance_from_ship_predicted, current_plane._angle)
							self.update_plane_position(current_plane, dt, angle_diff)
							if current_plane._speed > 1.4*Params.Ship.LINEAR_SPEED: # second slowdown before landing
								current_plane._speed -= 0.05
							else:
								current_plane._speed = 1.4*Params.Ship.LINEAR_SPEED
					if self.destination_reached(current_plane._position, self._position) and current_plane._deck_reached: # can also add angle check here to make sure they just land from the back
					# plane landed
						self.land_a_plane(current_plane)
						self._last_plane_landed = self._current_time
					if self._current_time - self._last_plane_landed > self._deck_cooldown: # just to add a bit of cooldown to the landing area
						self._landing_deck_available = True
						self._last_plane_landed = float('inf')
							
	def calculate_direction_and_distance(self, vector1, vector2):
		direction = vector1.__sub__(vector2) # substracting vectors
		distance = math.sqrt(direction.x**2 + direction.y**2) # getting magnitude
		return direction, distance

	def calculate_angle_difference(self, direction_to_target, distance_from_target, angle, circle=False):
		if circle:
			target_angle = math.atan2(direction_to_target.y, direction_to_target.x) + math.pi/2 # for simple circling just added 90' to an angle 
		else:
			normalized_direction = direction_to_target * (1 / distance_from_target) # conversion to unit vector for consistentcy
			target_angle = math.atan2(normalized_direction.y, normalized_direction.x) # getting angle based on tg(angle)=opposite_side/adjacent_side
		angle_difference = target_angle - angle # angle adjustment
		angle_difference = (angle_difference + math.pi) % (2 * math.pi) - math.pi  # normalisation of the angle difference
		return angle_difference
	
	def destination_reached(self, plane, destination):
		if round(plane.x, 1) == round(destination.x, 1) and round(plane.y, 1) == round(destination.y, 1):
			return True
		else:
			return False

	def update_plane_position(self, plane, dt, angle_diff, taking_off=False, going_to_target=False, linearSpeed=0, circle_distance=0, distance_from_target=0):
		if taking_off:
			plane._angle = self._angle
			plane._position += Vector2(math.cos(plane._angle), math.sin(plane._angle)) * plane._speed * dt + Vector2(math.cos(self._angle), math.sin(self._angle)) * linearSpeed * dt
			framework.placeModel(plane._model, plane._position.x, plane._position.y, plane._angle)
		elif going_to_target:
			if circle_distance*1.5 > distance_from_target > circle_distance: # added this just to start circling eariler, looks better for low angular speeds now
				plane._angle += math.copysign(min(Params.Aircraft.ANGULAR_SPEED * dt, abs(math.atan2(distance_from_target, circle_distance))), angle_diff + abs(math.atan2(distance_from_target, circle_distance)))
			else:
				plane._angle += math.copysign(min(Params.Aircraft.ANGULAR_SPEED * dt, abs(angle_diff)), angle_diff)
			plane._position += Vector2(math.cos(plane._angle), math.sin(plane._angle)) * plane._speed * dt
			framework.placeModel(plane._model, plane._position.x, plane._position.y, plane._angle)
		else:
			plane._angle += math.copysign(min(Params.Aircraft.ANGULAR_SPEED * dt, abs(angle_diff)), angle_diff)
			plane._position += Vector2(math.cos(plane._angle), math.sin(plane._angle)) * plane._speed * dt
			framework.placeModel(plane._model, plane._position.x, plane._position.y, plane._angle)
	
	def cancel_landing(self, plane):
		plane._landing_target_reached = False
		plane._deck_reached = False
		self._last_plane_landed = self._current_time
		plane._started_landing = 0.0
	
	def keyPressed(self, key):
		self._input[key] = True

	def keyReleased(self, key):
		self._input[key] = False

	def mouseClicked(self, x, y, isLeftButton):
		# TODO: placeholder, remove it and implement aircarfts logic
		if isLeftButton:
			framework.placeGoalModel(x, y)
			print(x, y)
			self._current_target = [True, Vector2(x, y)]
		else:
			if self._current_target[0]:
				self.launch_a_plane()
			else:
				print("no target")

	def launch_a_plane(self):
		if self._current_time - self._last_plane_launched < self._deck_cooldown:
			print("Last plane still launching")
			return
		for i in range(len(self._planes)):
			if not self._planes[i]._airborne and (self._current_time - self._planes[i]._refuel_timer > Params.Aircraft.REFUEL_TIME):
				model = framework.createAircraftModel()
				framework.placeModel(model, self._position.x, self._position.y, self._angle)
				current_angle = self._angle
				self._planes[i]._model = model
				self._planes[i]._position = Vector2(self._position.x, self._position.y)
				self._planes[i]._angle = current_angle
				self._planes[i]._launch_time = self._current_time
				self._planes[i]._airborne = True
				print("Plane: ", i, " is launched")
				self._num_of_planes -= 1
				self._last_plane_launched = self._current_time
				break
	
	def land_a_plane(self, plane):
		framework.destroyModel(plane._model)
		plane._model = None
		plane._position = None
		plane._angle = 0.0
		plane._speed = 0.0
		plane._speed_multiplier = 0.0
		plane._launch_time = 0.0
		plane._airborne = False
		plane._refuel_timer = self._current_time
		plane._landing_target_reached = False
		plane._deck_reached = False
		plane._started_landing = 0.0
		print("Plane: ", self._num_of_planes, " has landed")
		self._num_of_planes += 1
# -------------------------------------------------------
#	game public interface
# -------------------------------------------------------

class Game(object):

	def __init__(self):
		self._ship = Ship()

	def init(self):
		self._ship.init()

	def deinit(self):
		self._ship.deinit()

	def update(self, dt):
		self._ship.update(dt)

	def keyPressed(self, key):
		self._ship.keyPressed(key)

	def keyReleased(self, key):
		self._ship.keyReleased(key)

	def mouseClicked(self, x, y, isLeftButton):
		self._ship.mouseClicked(x, y, isLeftButton)


# -------------------------------------------------------
#	finally we can run our game!
# -------------------------------------------------------

if __name__ == '__main__':
	framework.runGame(Game())
