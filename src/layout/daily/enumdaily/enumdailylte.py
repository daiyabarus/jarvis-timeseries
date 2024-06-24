# enumdailylte.py
from enum import Enum


class ExlEnum(str, Enum):
    @classmethod
    def list(cls):
        return list(map(lambda c: c.value, cls))

    def __str__(self) -> str:
        return str.__str__(self)


class HeaderLTEDaily(ExlEnum):
    # Filter header
    DB_PATH = "database/database.db"
    DATEID = "Date"
    ERBS = "enodebname"
    CELL = "cellname"
    TABLE = "eri_lte"

    # Counter Header
    WEEK_TSEL = "Week TSEL"
    REGION = "Region"
    NENAME = "NEName"
    SITEID = "siteid"
    ENODEBID = "enodebid"
    LOCALCELLID = "localcellid"
    ENODEBID_LOCALCELLID = "enodebid_localcellid"
    BAND = "band"
    NEID = "neid"
    SITEID_SECTOR = "Siteid_Sector"
    CELLFDDTDD = "cellfddtdd"
    TYPE_BTS = "type_bts"
    SECTOR = "Sector"
    RADIO_NETWORK_AVAILABILITY_RATE = "Radio_Network_Availability_Rate(%)"
    RRC_SETUP_SR_SERVICE = "RRC_Setup_SR_Service(%)"
    ERAB_SETUP_SR_ALL = "ERAB_Setup_SR_All(%)"
    CALL_SETUP_SR = "Call_Setup_SR(%)"
    SERVICE_DROP_RATE = "Service_Drop_Rate(%)"
    INTRAFREQ_HO_OUT_SR = "IntraFreq_HO_Out_SR(%)"
    INTRAFREQ_HO_IN_SR = "IntraFreq_HO_In_SR(%)"
    INTER_FREQUENCY_HANDOVER_SR = "Inter-Frequency_Handover_SR(%)"
    CELL_DL_AVG_THROUGHPUT_MBPS = "Cell_DL_Avg_Throughput(Mbps)"
    CELL_UL_AVG_THROUGHPUT_MBPS = "Cell_UL_Avg_Throughput(Mbps)"
    USER_DL_AVG_THROUGHPUT_MBPS = "User_DL_Avg_Throughput(Mbps)"
    USER_UL_AVG_THROUGHPUT_MBPS = "User_UL_Avg_Throughput(Mbps)"
    CQI_AVERAGE_VER2_WITHOUT_256QAM = "CQI_Average_Ver2(Without 256 qam)"
    TDD_SE = "TDD SE"
    FDD_SE = "FDD SE"
    TOTAL_TRAFFIC_VOLUME_GB = "Total_Traffic_Volume(GB)"
    NEW_ACTIVE_USER = "New Active User"
    SUM_ACTIVE_USER_AVG = "Sum_Active_User_Avg"
    SUM_RRC_CONN_USER_AVG = "Sum_RRC_Conn_User_Avg(Avg_User_Number)"
    CSFB_EXECUTION_SR = "CSFB_Execution_SR(%)"
    CSFB_PREPARATION_SR = "CSFB_Preparation_SR(%)"
    RRC_USER = "RRC User"
    UPLINK_INTERFERENCE = "Uplink_Interference"
    TARGET1 = "Target1"
    TARGET2 = "Target2"
    TARGET3 = "Target3"
    TARGET4 = "Target4"
    CQI = "CQI"
    SE = "SE"
    PRB = "PRB"
