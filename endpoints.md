## /smsin/ endpoint (POST)
- split SMS into phone number & message
- lookup user by phone number (if !player, return error)
- retreive player info (name, timestamp, gamestate, etc)
- log input / interaction
- process input payload (if payload_error, return info via /smsout)
- update player game state (external datastore)
- return new prompt to player via /smsout

## /smsout/ endpoint (POST)
- lookup user by phone number & retreive game state
- prepare outgoing message
- send message
- log output / interaction

## /user/ endpoint (GET / POST / PATCH)
**GET**
  - lookup user from datastore using a provided 'id' - could be uid / phone / email / twitter handle, etc. (should be medium agnostic)
  - return user object

**POST**
  - create new user from JSON data
  - return new user object

**PATCH**
  - lookup user from firebase table
  - modify user using JSON data
  - return user object
