package com.example.oilrisk_alert.service;

import com.example.oilrisk_alert.vo.CollectResultVO;
import com.example.oilrisk_alert.vo.SystemStatusVO;

import java.util.List;
import java.util.Map;

public interface SystemStatusService {

    /**
     * 获取系统状态（采集状态、数据日期等）
     */
    SystemStatusVO getSystemStatus();

    /**
     * 手动触发全量采集 + 推理
     */
    CollectResultVO triggerCollection();

    /**
     * 查询采集日志
     */
    List<Map<String, Object>> getCollectionLogs(int limit);
}
