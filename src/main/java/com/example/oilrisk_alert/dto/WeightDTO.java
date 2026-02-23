package com.example.oilrisk_alert.dto;

import lombok.Data;

@Data
public class WeightDTO {
    private double supplyDemand;
    private double macro;
    private double financial;
    private double geopolitical;
    private double sentiment;
}
