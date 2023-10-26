from pylablib.core.utils import py3
from pylablib.core.devio import comm_backend, interface

class AlcatelError(comm_backend.DeviceError):
    """Generic Alcatel device error"""

class AlcatelBackendError(AlcatelError,comm_backend.DeviceBackendError):
    """Generic Alcatel backend communication error"""

class ACM1000(comm_backend.ICommBackendWrapper):
    """
    Alcatel ACM1000 six-port gauge controller.
    This class is a modification on the pylablib wrapper for the Pfeiffer TPG260 gauge.

    Args:
        conn: serial connection parameters (usually port or a tuple containing port and baudrate)
    """
    Error=AlcatelError

    def __init__(self, conn):
        instr=comm_backend.new_backend(conn,"serial",term_read="\r\n",term_write="",defaults={"serial":("COM1",9600)},reraise_error=AlcatelBackendError)
        comm_backend.ICommBackendWrapper.__init__(self,instr)
        gmux=([1,2,3,4,5,6],)
        self._add_status_variable("pressure",lambda channel: self.get_pressure(channel,status_error=False),ignore_error=(AlcatelError,),mux=gmux,priority=5)
        self._add_status_variable("channel_status",self.get_channel_status,mux=gmux,priority=5)
        self._add_status_variable("units",self.get_units)
        self._add_status_variable("enabled",self.is_enabled,priority=2)
        self._add_info_variable("gauge_kind",self.get_gauge_kind,mux=gmux)
        if self.test_connection() == False:
            raise

    def test_connection(self):
        try:
            self.query("BAU")
        except self.instr.Error:
            self.close()
            return False
        return True
    
    def comm(self, msg):
        """Send a command to the device"""
        self.instr.write(msg+"\r\n")
        rsp=self.instr.readline()
        if len(rsp)==1:
            if rsp[:1]==b"\x15":
                raise AlcatelError("command '{}' resulted in negative acknowledgement from the device".format(msg))
            elif rsp[:1]==b"\x06":
                return
        raise AlcatelError("command '{}' resulted in an unexpected acknowledgement from the device: {}".format(msg,rsp))
    
    def _parse_value(self, value, data_type):
        if data_type in ["str","raw"]:
            return value
        if data_type=="int":
            return int(value)
        if data_type=="float":
            return float(value)
        raise ValueError("unrecognized data type: {}".format(data_type))
    
    def query(self, msg, data_type="str"):
        """Send a query to the device and return the reply"""
        self.comm(msg)
        self.instr.write(b"\05")
        res=py3.as_str(self.instr.readline())
        if data_type=="raw":
            return res
        res=[v.strip() for v in res.strip().split(",")]
        if not isinstance(data_type,(tuple,list)):
            data_type=[data_type]*len(res)
        if len(data_type)!=len(res):
            raise ValueError("supplied datatypes {} have different length from the results {}".format(data_type,res))
        res=[self._parse_value(v,dt) for (v,dt) in zip(res,data_type)]
        return res[0] if len(res)==1 else res
    
    _p_channel=interface.EnumParameterClass("channel",[1,2,3,4,5,6])
    _p_unit=interface.EnumParameterClass("units",{"mbar":0,"torr":1,"pa":2})
    @interface.use_parameters(_returns="units")
    def get_units(self):
        """Get device units for indication/reading (``"mbar"``, ``"torr"``, or ``"pa"``)"""
        return self.query("UNI","int")
    
    def to_Pa(self, value, units=None):
        """
        Convert value in the given units to Pa.

        If `units` is ``None``, use the current display units.
        """
        units=units or self.get_units()
        conv_factor={"mbar":1E2,"torr":133.322,"pa":1}
        return value*conv_factor[units]
    
    def from_Pa(self, value, units=None):
        """
        Convert value in the given units from Pa.

        If `units` is ``None``, use the current display units.
        """
        units=units or self.get_units()
        conv_factor={"mbar":1E2,"torr":133.322,"pa":1}
        return value/conv_factor[units]

    def is_enabled(self, channel=1):
        """
        Check if the gauge at the given channel is enabled.
        
        If the gauge cannot be turned on/off (e.g., not connected), return ``None``.
        """
        return self.query("SEN",["int","int","int","int","int","int"])[channel-1]

    def enable(self, channel=1):
        """
        Turn ON the sensor at the given channel
        The ON/OFF status of a channel cannot be changed if there is no sensor connected to it.
        """
        if self.get_channel_status(channel) != 'no_sensor':
            vals=[0,0,0,0,0,0]
            vals[channel-1] = 2
            return self.query("SEN,{},{},{},{},{},{}".format(*vals),["int","int","int","int","int","int"])[channel-1]
        
    def disable(self, channel=1):
        """
        Turn OFF the sensor at the given channel
        The ON/OFF status of a channel cannot be changed if there is no sensor connected to it.
        """
        if self.get_channel_status(channel) != 'no_sensor':
            vals=[0,0,0,0,0,0]
            vals[channel-1] = 1
            return self.query("SEN,{},{},{},{},{},{}".format(*vals),["int","int","int","int","int","int"])[channel-1]
        
    @interface.use_parameters
    def enable_sensors(self, channel=1):
        """
        Turn ON all connected sensors.
        """
        for channel in [1,2,3,4,5,6]:
            self.enable(channel)
    
    _p_gstat=interface.EnumParameterClass("gauge_status",{"ok":0,"under":1,"over":2,"sensor_error":3,"sensor_off":4,"no_sensor":5,"id_error":6})
    @interface.use_parameters(_returns="gauge_status")
    def get_channel_status(self, channel=1):
        """
        Get channel status.

        Can be ``"ok"``, ``"under"`` (underrange), ``"over"`` (overrange), ``"sensor_error"``, ``"sensor_off"``, ``"no_sensor"``, or ``"id_error"``.
        """
        return self.query("PR{}".format(channel),["int","float"])[0]

    @interface.use_parameters
    def get_pressure(self, channel=1, display_units=False, status_error=False):
        """
        Get pressure at a given channel.
        
        If ``display_units==False``, return result in Pa; otherwise, use display units obtained using :meth:`get_units`.
        If ``status_error==True`` and the channel status is not ``"ok"``, raise and error; otherwise, return ``None``.
        """
        stat, press=self.query("PR{}".format(channel),["int","float"])
        if stat!=0 and status_error:
            if status_error:
                raise AlcatelError("pressure reading error: status {} ({})".format(stat,self._p_gstat.i(stat)))
        if not display_units:
            press=self.to_Pa(press)
        return press

    @interface.use_parameters
    def get_gauge_kind(self, channel=1):
        return self.query("TID",["str","str","str","str","str","str"])[channel-1]
    
    def _parse_errors(self, errs):
        if not isinstance(errs,list):
            errs=[errs]
        err_codes={0:"no_error",1:"watchdog",2:"task_fail",3:"eprom",4:"ram",5:"eeprom",6:"display",7:"adconv",
            9:"gauge_1_err",10:"gauge_1_id_err",11:"gauge_2_err",12:"gauge-2_id_err"}
        return [err_codes.get(er,er) for er in sorted(errs)]