# classgsm.py
from enum import Enum


class ExlEnum(str, Enum):
    @classmethod
    def list(cls):
        return list(map(lambda c: c.value, cls))

    def __str__(self) -> str:
        return str.__str__(self)


class EnumLower(ExlEnum):
    def _generate_next_value_(name, start, count, last_values):
        return f"{str(name).lower()}"


class EnumUpper(ExlEnum):
    def _generate_next_value_(name, start, count, last_values):
        return f"{str(name).upper()}"


class TableGSM(ExlEnum):
  TABLE = "eri_gsm"
  DATEID = "DATE_ID"
  CELL = "GERANCELL"
  ERBS = "BSC"
  AVAILABILITY = "Availability"
  INTERFERENCEULICMBAND4BAND5 = "Interference_UL_ICM_Band4_Band5"
  CALLSETUPSUCCESSRATE = "Call_Setup_Success_Rate"
  SDCCHDROPRATE = "SDCCH_Drop_Rate"
  CALLDROPRATE = "Call_Drop_Rate"
  HOSUCCESSRATE = "HO_Success_Rate"
  HOATTEMPTS = "HO_attempts"
  HOUTRANSUCCESSRATE = "HO_UTRAN_Success_Rate"
  HOUTRANATTEMPTS = "HO_Utran_Attempts"
  HOUTRANSUCCESS = "HO_Utran_Success"
  HOUTRANCHANNEL = "HO_Utran_Channel"
  TBFDROPRATE = "TbfDrop_Rate"
  VOICETRAFFIC = "Voice_Traffic"
  TRAFFICMB = "Traffic_Mb"
  DLEGRPSTHROUGHPUT = "DL_EGRPS_Throughput"
  ULEGRPSTHROUGHPUT = "UL_EGRPS_Throughput"
  RANDOMACCESSSUCCESSRATE = "Random_Access_Success_Rate"
  HOREVERSION = "HO_Reversion"
  SDCCHDROPREASONLOWSS = "SDCCH_Drop_Reason_Low_SS"
  SDCCHDROPREASONQUALITY = "SDCCH_Drop_Reason_Quality"
  SDCCHDROPREASONEXCESSIVETA = "SDCCH_Drop_Reason_Excessive_TA"
  SDCCHDROPREASONOTHER = "SDCCH_Drop_Reason_Other"
  SDCCHCONGEST = "SDCCH_Congest"
  TCHDROPREASONLOWSS = "TCH_Drop_Reason_Low_SS"
  TCHDROPREASONBADQUALITY = "TCH_Drop_Reason_Bad_Quality"
  TCHDROPREASONSUDDENLYLOSTCONNECTION = "TCH_Drop_Reason_Suddenly_Lost_Connection"
  TCHDROPREASONEXCESSIVETA = "TCH_Drop_Reason_Excessive_TA"
  TCHDROPREASONOTHER = "TCH_Drop_Reason_Other"
