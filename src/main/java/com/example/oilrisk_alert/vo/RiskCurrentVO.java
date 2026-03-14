package com.example.oilrisk_alert.vo;

import lombok.Data;

import java.math.BigDecimal;
import java.util.List;

@Data
public class RiskCurrentVO {
    private BigDecimal riskIndex;
    private String riskLevel;
    private String date;
    private List<FactorVO> topFactors;

    // 实时因子采集扩展字段
    private String dataDate;    // 数据日期（采集数据对应的交易日）
    private String updatedAt;   // 最近一次推理时间
    private String dataSource;  // "realtime" | "historical"
}
