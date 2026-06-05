export enum APIS {
    SETTING_9 = 'settings/calibration',
    GET_CALIB_DATA = 'settings/9/getsensorcalibration/',
    SEND_COUNT = 'settings/9/putnumberofsolutionsdone',
    GET_RESULT = 'settings/9/getcalibrationresult',
    START_PUMP = 'adhoc/start',
    UPDATE = 'settings/9/update',
    RESET_ALARM = 'system/reseterror',
    FLUSH = 'system/flush',
    FLUSH_RESULT = 'system/flush/getflushresult',
    TOPUP = 'system/topup',
    TOPUP_RESULT = 'system/topup/gettopupresult',
    USER_ERROR_RESET = 'system/useracknowledgement',
    SYSTEM_TYPE = 'settings/systemsetting',
    GET_GRAPH_DATA = 'historicalData',
    GETGUIDE = 'getGuideMediaList',
    SCREEN_SAVER = 'screensaverdata'
}