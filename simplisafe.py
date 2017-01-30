import json
import sys
import uuid
import argparse
import logging

import requests

LOGIN_URL = 'https://simplisafe.com/mobile/login/'
LOGOUT_URL = 'https://simplisafe.com/mobile/logout'
LOCATIONS_URL = 'https://simplisafe.com/mobile/$UID$/locations'
DASHBOARD_URL = 'https://simplisafe.com/mobile/$UID$/sid/$LID$/dashboard'
EVENTS_URL = 'https://simplisafe.com/mobile/$UID$/sid/$LID$/events'
STATE_URL = 'https://simplisafe.com/mobile/$UID$/sid/$LID$/set-state'
ALL_STATES = {}

_LOGGER = logging.getLogger(__name__)


class SimpliSafe():

    def __init__(self, username, password, debug=False):

        # Initialize variables
        self.session = None
        self.debug = False
        self.state = None
        self.uid = None
        self.location = None
        self.username = username
        self.password = password
        self.temperature = None
        self.co = None
        self.flood = None
        self.fire = None

        # Create a requests session to persist the cookies
        self.session = requests.session()

        self.get_location()

        # If we got debug passed, we'll print out diagnostics.
        if debug:
            self.debug = True

    def set_state(self, state):
        self.login()

        if state not in ('home', 'away', 'off'):
            error = "State must be 'home', 'away', or 'off'. You tried '%s'." % state
            _LOGGER.error(error)

        state_data = {
            'state': state,
            'mobile': '1',
            'no_persist': '0',
            'XDEBUG_SESSION_START': 'session_name',
        }

        if self.debug:
            print("Setting System State To: %s" % state)

        URL = STATE_URL.replace('$UID$', self.uid)
        URL = URL.replace('$LID$', self.location)
        response = self.session.post(URL, data=state_data)
        response_object = json.loads(response.text)

        if self.debug:
            print("Set State Response: %s" % response.text)

        result_codes = {
            '2': 'off',
            '4': 'home',
            '5': 'away',
        }
        result_code = response_object['result']
        self.state = result_codes[str(result_code)]
        return result_codes[str(result_code)]

        self.logout()

    def get_state(self):
        return self.state

    def get_id(self):
        return self.uid

    def get_dashboard(self):
        self.login()

        if not self.uid:
            error = "You tried to get dashboard without first having a User ID set."
            _LOGGER.error(error)

        if not self.location:
            error = "You tried to get dashboard without first having a location set."
            _LOGGER.error(error)

        dashboard_data = {
            'no_persist': '0',
            'XDEBUG_SESSION_START': 'session_name',
        }

        URL = DASHBOARD_URL.replace('$UID$', self.uid)
        URL = URL.replace('$LID$', self.location)
        response = self.session.post(URL, data=dashboard_data)
        json_state = json.loads(response.text)
        monitoring_sensors = json_state.get("location").get("monitoring")
        self.temp = monitoring_sensors.get("freeze").get("temp")
        self.co = monitoring_sensors.get("recent_co").get("text")
        self.flood = monitoring_sensors.get("recent_flood").get("text")
        self.fire = monitoring_sensors.get("recent_fire").get("text")
        self.alarm = monitoring_sensors.get("recent_alarm").get("text")

        if self.debug:
            print("Dashboard Response: %s" % response.text)

        self.logout()

    def get_location(self):
        self.login()

        if not self.uid:
            error = "You tried to get location without first having a User ID set."
            _LOGGER.error(error)

        location_data = {
            'no_persist': '0',
            'XDEBUG_SESSION_START': 'session_name',
        }

        URL = LOCATIONS_URL.replace('$UID$', self.uid)
        response = self.session.post(URL, data=location_data)
        response_object = json.loads(response.text)

        if self.debug:
            print("Location Response: %s" % response.text)

        locations = response_object['locations']
        self.location = list(locations)[0]
        self.state = locations[self.location]['system_state']

        self.logout()

    def get_events(self):
        self.login()

        if not self.uid:
            error = "You tried to get events without first having a User ID set."
            _LOGGER.error(error)

        event_data = {
            'no_persist': '0',
            'XDEBUG_SESSION_START': 'session_name',
        }

        URL = EVENTS_URL.replace('$UID$', self.uid)
        response = self.session.post(URL, data=event_data)
        response_object = json.loads(response.text)

        if self.debug:
            print("Event Response: %s" % response.text)

        #locations = response_object['locations']
        #self.location = list(locations)[0]
        #self.state = locations[self.location]['system_state']

        self.logout()

    def login(self):

        if not self.username or not self.password:
            _LOGGER.error("You must provide a username and password.")

        login_data = {
            'name': self.username,
            'pass': self.password,
            'device_name': 'My iPhone',
            'device_uuid': str(uuid.uuid1()),
            'version': '1100',
            'no_persist': '1',
            'XDEBUG_SESSION_START': 'session_name',
        }

        response = self.session.post(LOGIN_URL, data=login_data)
        response_object = json.loads(response.text)

        if self.debug:
            print("Login Response: %s" % response.text)

        self.session_id = response_object['session']
        self.uid = response_object['uid']

    def logout(self):

        response = self.session.post(LOGOUT_URL)

        if self.debug:
            print("Logout Response: %s" % response.text)

if __name__ == "__main__":

    parser = argparse.ArgumentParser()

    parser.add_argument('--username', help='Username', required=True)
    parser.add_argument('--password', help='Password', required=True)
    parser.add_argument('--state', help='Alarm State', required=False)
    parser.add_argument('--debug', help='Output debugging',
                        required=False, default=False, action="store_true")
    parser.add_argument('--dashboard', help='Display dashboard',
                        required=False, default=False, action="store_true")

    args = vars(parser.parse_args())

    if args['state'] is not None:
        if args['state'] not in ('Off', 'Away', 'Home'):
            sys.exit("State must be Off, Away, or Home")

    s = SimpliSafe(args['username'], args['password'], args['debug'])

    s.login()
    s.get_location()
    s.get_dashboard()
    s.get_events()
    if args['state'] is not None:
        s.set_state(args['state'].lower())

    print("System State: %s" % s.get_state())
    if args['dashboard'] is not None:
        print("Temp: " + s.temp)
        print("CO: " + s.co)
        print("Fire: " + s.fire)
        print("Flood: " + s.flood)
        print("Alarm: " + s.alarm)
    s.logout()
