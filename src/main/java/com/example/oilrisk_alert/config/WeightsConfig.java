package com.example.oilrisk_alert.config;

import lombok.Data;
import org.springframework.stereotype.Component;

@Data
@Component
public class WeightsConfig {

    private double supplyDemand = 1.0;
    private double macro = 1.0;
    private double financial = 1.0;
    private double geopolitical = 1.0;
    private double sentiment = 1.0;

    public double getWeight(String category) {
        return switch (category) {
            case "SUPPLY_DEMAND" -> supplyDemand;
            case "MACRO" -> macro;
            case "FINANCIAL" -> financial;
            case "GEOPOLITICAL" -> geopolitical;
            case "SENTIMENT" -> sentiment;
            default -> 1.0;
        };
    }

    public static String getCategoryZh(String category) {
        return switch (category) {
            case "SUPPLY_DEMAND" -> "供需";
            case "MACRO" -> "宏观经济";
            case "FINANCIAL" -> "金融市场";
            case "GEOPOLITICAL" -> "地缘政治";
            case "SENTIMENT" -> "市场情绪";
            default -> category;
        };
    }
}
