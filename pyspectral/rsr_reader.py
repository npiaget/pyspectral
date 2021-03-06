#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2014, 2015 Adam.Dybbroe

# Author(s):

#   Adam.Dybbroe <adam.dybbroe@smhi.se>
#   Panu Lahtinen <panu.lahtinen@fmi.fi>

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""Reading the spectral responses in the internal pyspectral hdf5 format"""

import ConfigParser
import os
import numpy as np
from glob import glob

import logging
LOG = logging.getLogger(__name__)

try:
    CONFIG_FILE = os.environ['PSP_CONFIG_FILE']
except KeyError:
    LOG.exception('Environment variable PSP_CONFIG_FILE not set!')
    raise

if not os.path.exists(CONFIG_FILE) or not os.path.isfile(CONFIG_FILE):
    raise IOError(str(CONFIG_FILE) + " pointed to by the environment " +
                  "variable PSP_CONFIG_FILE is not a file or does not exist!")


class RelativeSpectralResponse(object):

    """Container for the relative spectral response functions for various
    satellite imagers
    """

    def __init__(self, platform_name, instrument):
        self.platform_name = platform_name
        self.instrument = instrument
        self.filename = None
        self.rsr = {}
        self.description = "Unknown"
        self.band_names = None
        self.unit = '1e-6 m'
        self.si_scale = 1e-6  # How to scale the wavelengths to become SI unit

        conf = ConfigParser.ConfigParser()
        try:
            conf.read(CONFIG_FILE)
        except ConfigParser.NoSectionError:
            LOG.exception('Failed reading configuration file: %s',
                          str(CONFIG_FILE))
            raise

        options = {}
        for option, value in conf.items('general', raw=True):
            options[option] = value

        rsr_dir = options['rsr_dir']
        self.filename = os.path.join(rsr_dir, 'rsr_%s_%s.h5' %
                                     (instrument, platform_name))

        LOG.debug('Filename: %s', str(self.filename))

        if not os.path.exists(self.filename) or not os.path.isfile(self.filename):
            raise IOError('pyspectral RSR file does not exist! Filename = ' +
                          str(self.filename) +
                          '\nFiles matching instrument and satellite platform' +
                          ': ' +
                          str(glob(os.path.join(rsr_dir, '*%s*%s*.h5' %
                                                (instrument, platform_name)))))

        self.load()

    def load(self):
        """Read the internally formatet hdf5 relative spectral response data"""
        import h5py

        with h5py.File(self.filename, 'r') as h5f:
            self.band_names = h5f.attrs['band_names'].tolist()
            self.description = h5f.attrs['description']
            for bandname in self.band_names:
                self.rsr[bandname] = {}
                try:
                    num_of_det = h5f[bandname].attrs['number_of_detectors']
                except KeyError:
                    LOG.debug("No detectors found - assume only one...")
                    num_of_det = 1

                for i in range(1, num_of_det + 1):
                    dname = 'det-%d' % i
                    self.rsr[bandname][dname] = {}
                    try:
                        resp = h5f[bandname][dname]['response'][:]
                    except KeyError:
                        resp = h5f[bandname]['response'][:]

                    self.rsr[bandname][dname]['response'] = resp

                    try:
                        wvl = (h5f[bandname][dname]['wavelength'][:] *
                               h5f[bandname][dname][
                                   'wavelength'].attrs['scale'])
                    except KeyError:
                        wvl = (h5f[bandname]['wavelength'][:] *
                               h5f[bandname]['wavelength'].attrs['scale'])

                    # The wavelength is given in micro meters!
                    self.rsr[bandname][dname]['wavelength'] = wvl * 1e6

    def integral(self, bandname):
        """Calculate the integral of the spectral response function for each
        detector.
        """
        intg = {}
        for det in self.rsr[bandname].keys():
            wvl = self.rsr[bandname][det]['wavelength']
            resp = self.rsr[bandname][det]['response']
            intg[det] = np.trapz(resp, wvl)
        return intg


def main():
    """Main"""
    modis = RelativeSpectralResponse('EOS-Terra', 'modis')
    del(modis)

if __name__ == "__main__":
    main()
