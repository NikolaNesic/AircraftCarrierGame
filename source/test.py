aSpeed = math.copysign(Params.Aircraft.ANGULAR_SPEED, i._speed)
i._angle = i._angle + aSpeed * dt
i._position = i._position + Vector2(math.cos(i._angle), math.sin(i._angle)) * i._speed * dt
framework.placeModel(i._model, i._position.x, i._position.y, i._angle)
#start circling of a plane