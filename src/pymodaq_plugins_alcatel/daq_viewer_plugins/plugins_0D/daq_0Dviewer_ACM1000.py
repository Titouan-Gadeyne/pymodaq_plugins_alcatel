import numpy as np
from pymodaq.utils.daq_utils import ThreadCommand
from pymodaq.utils.data import DataFromPlugins, DataToExport
from pymodaq.control_modules.viewer_utility_classes import DAQ_Viewer_base, comon_parameters, main
from pymodaq.utils.parameter import Parameter

import pylablib as pylablib
from pylablib.devices.Pfeiffer import TPG260


class ACM1000(TPG260): # This class inherits from the Pfeiffer TPG260 class from pylablib
    pass


class DAQ_0DViewer_ACM1000(DAQ_Viewer_base):
    """ 
    Instrument plugin class for the Alcatel ACM 1000 gauge controller.

    Compatible instruments: 
    -----------
    - Alcatel ACM 1000 

    Tested with: 
    -----------
    - Alcatel ACM 1000 controller (itself connected to Alcatel ACC 1009 gauges)
    - PyMoDAQ version 4.0.8
    - Windows 10 ver. 21H2

    Installation instructions:
    -----------
    - No drivers from Alcatel are required.
    - Your PC should have serial ports (COM ports) to connect the controller.
      On Windows 10 you may need to install a driver to create virtual COM ports.

    Attributes:
    -----------
    controller: object
        The particular object that allow the communication with the hardware, in general a python wrapper around the
         hardware library.
    """
    ports = pylablib.list_backend_resources("serial")
    if ports:
        default_port = ports[0]
    else:
        default_port = 'None'


    params = comon_parameters+[
        {'title': 'Available ports', 'name': 'available_ports', 'type': 'list', 'values': ports, 'readonly': True},
        {'title': 'Selected port', 'name': 'selected_port', 'type': 'str', 'value': default_port}
        ]

    def ini_attributes(self):

        self.controller: ACM1000(self.settings['selected_port']) # init controller by trying to connect to the port selected by default


    def commit_settings(self, param: Parameter):
        """Apply the consequences of a change of value in the detector settings

        Parameters
        ----------
        param: Parameter
            A given parameter (within detector_settings) whose value has been changed by the user
        """

        if param.name() == 'selected_port': # if the selected COM port was changed, try to connect to it
           self.controller = ACM1000(param.value())  


    def ini_detector(self, controller=None):
        """Detector communication initialization

        Parameters
        ----------
        controller: (object)
            custom object of a PyMoDAQ plugin (Slave case). None if only one actuator/detector by controller
            (Master case)

        Returns
        -------
        info: str
        initialized: bool
            False if initialization failed otherwise True
        """

        raise NotImplemented  # TODO when writing your own plugin remove this line and modify the one below
        self.ini_detector_init(old_controller=controller,
                               new_controller=PythonWrapperOfYourInstrument())

        # TODO for your custom plugin (optional) initialize viewers panel with the future type of data
        self.dte_signal_temp.emit(DataToExport(name='myplugin',
                                               data=[DataFromPlugins(name='Mock1',
                                                                    data=[np.array([0]), np.array([0])],
                                                                    dim='Data0D',
                                                                    labels=['Mock1', 'label2'])]))

        info = "Whatever info you want to log"
        initialized = self.controller.a_method_or_atttribute_to_check_if_init()  # TODO
        return info, initialized

    def close(self):
        """Terminate the communication protocol"""
        ## TODO for your custom plugin
        raise NotImplemented  # when writing your own plugin remove this line
        #  self.controller.your_method_to_terminate_the_communication()  # when writing your own plugin replace this line

    def grab_data(self, Naverage=1, **kwargs):
        """Start a grab from the detector

        Parameters
        ----------
        Naverage: int
            Number of hardware averaging (if hardware averaging is possible, self.hardware_averaging should be set to
            True in class preamble and you should code this implementation)
        kwargs: dict
            others optionals arguments
        """
        ## TODO for your custom plugin: you should choose EITHER the synchrone or the asynchrone version following

        # synchrone version (blocking function)
        raise NotImplemented  # when writing your own plugin remove this line
        data_tot = self.controller.your_method_to_start_a_grab_snap()
        self.dte_signal.emit(DataToExport(name='myplugin',
                                          data=[DataFromPlugins(name='Mock1', data=data_tot,
                                                                dim='Data0D', labels=['dat0', 'data1'])]))
        #########################################################

        # asynchrone version (non-blocking function with callback)
        raise NotImplemented  # when writing your own plugin remove this line
        self.controller.your_method_to_start_a_grab_snap(self.callback)  # when writing your own plugin replace this line
        #########################################################


    def callback(self):
        """optional asynchrone method called when the detector has finished its acquisition of data"""
        data_tot = self.controller.your_method_to_get_data_from_buffer()
        self.dte_signal.emit(DataToExport(name='myplugin',
                                          data=[DataFromPlugins(name='Mock1', data=data_tot,
                                                                dim='Data0D', labels=['dat0', 'data1'])]))

    def stop(self):
        """Stop the current grab hardware wise if necessary"""
        ## TODO for your custom plugin
        raise NotImplemented  # when writing your own plugin remove this line
        self.controller.your_method_to_stop_acquisition()  # when writing your own plugin replace this line
        self.emit_status(ThreadCommand('Update_Status', ['Some info you want to log']))
        ##############################
        return ''


if __name__ == '__main__':
    main(__file__)
