from tempfile import mkstemp
import sys

import requests


class OSC(object):
    """
    To manage the the OSM changes files
    """

    MINUTELY = 1
    HOURLY = 2
    DAYLY = 3

    replication_name = {
        1: "minute",
        2: "hour",
        3: "day"
    }

    def __init__(self):
        self._periodicty = self.HOURLY

    @property
    def periodicty(self):
        """
        Getter function for periodicity
        :return:
        """
        return self.periodicty

    @periodicty.setter
    def periodicty(self, value):
        """
        Replication periodicity setter

        :param value: value to set
        :return: None
        """
        self.periodicty = value

    def get_state(self):
        """
        Downloads the state from OSM replication system

        :return: Actual state as a str
        """

        r = requests.get(
            'http://planet.openstreetmap.org/replication/{}/state.txt'.format(
                self.replication_name[self._periodicty]
            )
        )
        return r.text.split('\n')[1].split('=')[1]

    def get_last(self):
        """
        Method that dowload the last osc file

        :return: None
        """

        state = self.get_state()

        # zero-pad state so it can be safely split.
        state = '000000000' + state
        path = '{0}/{1}/{2}'.format(state[-9:-6], state[-6:-3], state[-3:])
        stateurl = 'http://planet.openstreetmap.org/replication/{}/{}.osc.gz'.format(
            self.replication_name[self._periodicty],
            path
        )

        sys.stderr.write('downloading {0}...\n'.format(stateurl))
        # prepare a local file to store changes
        handle, filename = mkstemp(prefix='change-', suffix='.osc.gz')
        os.close(handle)

        with open(filename, "w") as f:
            resp = requests.get(stateurl)
            f.write(resp.content)
        sys.stderr.write('Done\n')
        # sys.stderr.write('extracting {0}...\n'.format(filename))
        # os.system('gunzip -f {0}'.format(filename))

        # knock off the ".gz" suffix and return
        return filename