from enum import Enum


class ExlEnum(str, Enum):
    @classmethod
    def list(cls):
        return list(map(lambda c: c.value, cls))

    def __str__(self) -> str:
        return str.__str__(self)


class LTEDailyGut(ExlEnum):
    DB_PATH = "database/database.db"
    TABLE = "eri_gut_lte"
    DATEID = "DATE_ID"
    ERBS = "SITEID"
    SITEID = "ERBS"
    NEID = "NEID"
    CELL = "EutranCell"
    AVAILABILITY = "Availability"
    RRC_SR = "RRC_SR"
    ERAB_SR = "ERAB_SR"
    SSSR = "SSSR"
    SAR = "SAR"
    S1_SIGNALING_SR = "S1_Signaling_SR"
    INTRA_HO_EXE_SR = "Intra_HO_Exe_SR"
    INTER_HO_EXE_SR = "Inter_HO_Exe_SR"
    DOWNLINK_TRAFF_VOLUME = "Downlink_Traff_Volume"
    UPLINK_TRAFF_VOLUME = "Uplink_Traff_Volume"
    TOTAL_TRAFF_VOLUME = "Total_Traff_Volume"
    PAYLOAD_TOTAL_GB = "Payload_Total(Gb)"
    DL_RESOURCE_BLOCK_UTILIZING_RATE = "DLResourceBlockUtilizingRate"
    UL_RESOURCE_BLOCK_UTILIZING_RATE = "ULResourceBlockUtilizingRate"
    LTE_PEAK_ACTIVE_DL_USERS = "LTE_Peak_Active_DL_Users"
    LTE_PEAK_ACTIVE_UL_USERS = "LTE_Peak_Active_UL_Users"
    UL_INT_PUSCH = "UL_INT_PUSCH"
    UL_INT_PUCCH = "UL_INT_PUCCH"
    CELL_DOWNLINK_AVERAGE_THROUGHPUT = "CellDownlinkAverageThroughput"
    CELL_UPLINK_AVERAGE_THROUGHPUT = "CellUplinkAverageThroughput"
    USER_DOWNLINK_AVERAGE_THROUGHPUT_MBPS = "User_Downlink_Average_Throughput_Mbps"
    USER_UPLINK_AVERAGE_THROUGHPUT_MBPS = "User_Uplink_Average_ThroughputMbps"
    SE_DAILY = "SE_DAILY"
    AVGCQI_NONHOM = "avgcqinonhom"
    CQI_GE_7 = "CQI>=7"
    CSFB_2G = "CSFB_2G"
    CSFB_3G = "CSFB_3G"
    CSFB_3G_SR = "CSFB_3G_SR"
    PAGING_SUCCES_RATE = "PagingSuccesRate"
    PAGING_DISCARD_RATE = "PagingDiscardRate"
    PM_ERAB_REL_ABNORMAL_ENB_ACT = "pmErabRelAbnormalEnbAct_"
    MAXIMUM_USER_NUMBER_RRC = "Maximum_User_Number_RRC"
    RRC_CONNECTED_USER = "RRC_Connected_User"
    PM_CELL_DOWN_TIME_AUTO = "pmCellDownTimeAuto_"
    PSHO_TO_UTRAN_EXE_SR = "PSHO_to_UTRAN_Exe_SR"
    IP_LATENCY = "IP_Latency"
    ACTIVE_USER = "Active_User"
    PM_CELL_DOWNTIME_MAN = "pmCellDowntimeMan_"
    ERAB_DROP_RATE = "Erab_Drop_Rate"
    PM_ERAB_REL_ABNORMAL_ENB_ACT_CDT = "pmErabRelAbnormalEnbActCdt_"
    PM_ERAB_REL_ABNORMAL_ENB_ACT_HO = "pmErabRelAbnormalEnbActHo_"
    PM_ERAB_REL_ABNORMAL_ENB_ACT_HPR = "pmErabRelAbnormalEnbActHpr_"
    PM_ERAB_REL_ABNORMAL_ENB_ACT_TN_FAIL = "pmErabRelAbnormalEnbActTnFail_"
    PM_ERAB_REL_ABNORMAL_ENB_ACT_UE_LOST = "pmErabRelAbnormalEnbActUeLost_"
    PM_BAD_COV_EVAL_REPORT = "pmBadCovEvalReport_"
    CQI_BH = "CQI_Bh"
    SE_BH = "SE_Bh"
