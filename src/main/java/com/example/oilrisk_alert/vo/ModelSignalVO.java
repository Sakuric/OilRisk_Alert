package com.example.oilrisk_alert.vo;

import lombok.Data;

@Data
public class ModelSignalVO {
    private double lstmPredPrice;
    private String lstmDirection;
    private double lstmUpProb;
    private double xgbRiskScore;
    private double stackingReturnPct;
    private String stackingRiskZone;
    private String date;
}
