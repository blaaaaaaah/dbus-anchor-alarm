# Copyright (c) 2025 Thomas Dubois
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import sys
import os

sys.path.insert(1, os.path.join(sys.path[0], '..'))
from utils import AbstractTimerUtils

from anchor_alarm_model import AnchorAlarmState
from anchor_alarm_controller import AnchorAlarmController


class AbstractConnector(AbstractTimerUtils):
    def __init__(self, timer_provider, settings_provider):
        super().__init__(timer_provider)
        self._settings_provider = settings_provider

        self.controller = None

    def set_controller(self, controller:AnchorAlarmController):
        """Controller has :
            - trigger_anchor_down
            - trigger_chain_out
            - trigger_anchor_up
            - trigger_mute_alarm
        """

        self.controller = controller

    def on_state_changed(self, current_state:AnchorAlarmState):
        """Called by controller when state changed"""
        pass

    def update_state(self, current_state:AnchorAlarmState):
        """Called by controller every second with updated state"""
        pass

    def show_message(self, level, message):
        """Called by controller to show a specific error or info message"""
        pass
