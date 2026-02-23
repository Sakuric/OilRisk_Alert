package com.example.oilrisk_alert.vo;

import lombok.Data;

import java.math.BigDecimal;

@Data
public class FactorVO {
    private String name;
    private String nameZh;
    private BigDecimal shap;
    private String category;
}
